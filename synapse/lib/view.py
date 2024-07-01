import shutil
import asyncio
import hashlib
import logging
import weakref
import itertools
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.scope as s_scope
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types
import synapse.lib.config as s_config
import synapse.lib.editor as s_editor
import synapse.lib.scrape as s_scrape
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.spooled as s_spooled
import synapse.lib.trigger as s_trigger
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

class ViewApi(s_cell.CellApi):

    async def __anit__(self, core, link, user, view):

        await s_cell.CellApi.__anit__(self, core, link, user)
        self.view = view
        self.allowedits = user.allowed(('node',), gateiden=view.wlyr.iden)

    async def storNodeEdits(self, edits, meta):

        if not self.allowedits:
            mesg = 'storNodeEdits() not allowed without node permission on layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        if meta is None:
            meta = {}

        meta['time'] = s_common.now()
        meta['user'] = self.user.iden

        return await self.view.storNodeEdits(edits, meta)

    async def syncNodeEdits2(self, offs, wait=True, compat=False):
        await self._reqUserAllowed(('view', 'read'))
        # present a layer compatible API to remote callers
        async for item in self.view.wlyr.syncNodeEdits2(offs, wait=wait, compat=compat):
            yield item
            await asyncio.sleep(0)

    @s_cell.adminapi()
    async def saveNodeEdits(self, edits, meta):
        await self.view.reqValid()
        meta['link:user'] = self.user.iden
        return await self.view.saveNodeEdits(edits, meta)

    async def getEditSize(self):
        await self._reqUserAllowed(('view', 'read'))
        return await self.view.wlyr.getEditSize()

    async def getCellIden(self):
        return self.view.iden

class View(s_nexus.Pusher):  # type: ignore
    '''
    A view represents a cortex as seen from a specific set of layers.

    The view class is used to implement Copy-On-Write layers as well as
    interact with a subset of the layers configured in a Cortex.
    '''
    tagcachesize = 1000
    nodecachesize = 10000

    async def __anit__(self, core, node):
        '''
        Async init the view.

        Args:
            core (Cortex):  The cortex that owns the view.
            node (HiveNode): The hive node containing the view info.
        '''
        self.node = node
        self.iden = node.name()
        self.bidn = s_common.uhex(self.iden)
        self.info = await node.dict()

        self.core = core
        self.dirn = s_common.gendir(core.dirn, 'views', self.iden)

        slabpath = s_common.genpath(self.dirn, 'viewstate.lmdb')
        self.viewslab = await s_lmdbslab.Slab.anit(slabpath)
        self.viewslab.addResizeCallback(core.checkFreeSpace)

        self.trigqueue = self.viewslab.getSeqn('trigqueue')

        trignode = await node.open(('triggers',))
        self.trigdict = await trignode.dict()

        self.triggers = s_trigger.Triggers(self)
        for _, tdef in self.trigdict.items():
            try:
                await self.triggers.load(tdef)

            except Exception: # pragma: no cover
                logger.exception(f'Failed to load trigger {tdef!r}')

        await s_nexus.Pusher.__anit__(self, iden=self.iden, nexsroot=core.nexsroot)

        self.onfini(self.viewslab.fini)

        self.layers = []
        self.invalid = None
        self.parent = None  # The view this view was forked from

        # This will be True for a view which has a merge in progress
        self.merging = self.info.get('merging', False)

        # isolate some initialization to easily override.
        await self._initViewLayers()

        self.readonly = self.wlyr.readonly

        self.trigtask = None
        await self.initTrigTask()

        self.mergetask = None

        self.tagcache = s_cache.FixedCache(self._getTagNode, size=self.tagcachesize)

        self.nodecache = collections.deque(maxlen=self.nodecachesize)
        self.livenodes = weakref.WeakValueDictionary()

    def clearCache(self):
        self.tagcache.clear()
        self.nodecache.clear()
        self.livenodes.clear()

    def clearCachedNode(self, nid):
        self.livenodes.pop(nid, None)

    async def saveNodeEdits(self, edits, meta, bus=None):
        '''
        Save node edits and run triggers/callbacks.
        '''

        if self.readonly:
            mesg = 'The view is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        callbacks = []

        wlyr = self.layers[0]

        # hold a reference to  all the nodes about to be edited...
        nodes = {e[0]: await self.getNodeByNid(e[0]) for e in edits if e[0] is not None}

        saveoff, nodeedits = await wlyr.saveNodeEdits(edits, meta)

        fireedit = (bus is not None and bus.view.iden == self.iden)

        # make a pass through the returned edits, apply the changes to our Nodes()
        # and collect up all the callbacks to fire at once at the end.  It is
        # critical to fire all callbacks after applying all Node() changes.

        for nid, form, edits in nodeedits:

            node = nodes.get(nid)
            if node is None:
                node = await self.getNodeByNid(nid)

                if node is None:  # pragma: no cover
                    continue

            for edit in edits:

                etyp, parms = edit

                if etyp == s_layer.EDIT_NODE_ADD:
                    callbacks.append((node.form.wasAdded, (node,), {}))
                    callbacks.append((self.runNodeAdd, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_NODE_DEL or etyp == s_layer.EDIT_NODE_TOMB:
                    callbacks.append((node.form.wasDeleted, (node,), {}))
                    callbacks.append((self.runNodeDel, (node,), {}))
                    self.clearCachedNode(nid)
                    continue

                if etyp == s_layer.EDIT_NODE_TOMB_DEL:
                    if not node.istomb():
                        callbacks.append((node.form.wasAdded, (node,), {}))
                        callbacks.append((self.runNodeAdd, (node,), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_SET:

                    (name, valu, oldv, stype, _) = parms

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'saveNodeEdits got EDIT_PROP_SET for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasSet, (node, oldv), {}))
                    callbacks.append((self.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_TOMB_DEL:

                    (name,) = parms

                    if (oldv := node.get(name)) is not None:
                        prop = node.form.props.get(name)
                        if prop is None:  # pragma: no cover
                            logger.warning(f'saveNodeEdits got EDIT_PROP_TOMB_DEL for bad prop {name} on form {node.form.full}')
                            continue

                        callbacks.append((prop.wasSet, (node, oldv), {}))
                        callbacks.append((self.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_DEL:

                    (name, oldv, stype) = parms

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'saveNodeEdits got EDIT_PROP_DEL for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_PROP_TOMB:

                    (name,) = parms

                    oldv = node.getFromLayers(name, strt=1, defv=s_common.novalu)
                    if oldv is s_common.novalu:  # pragma: no cover
                        continue

                    prop = node.form.props.get(name)
                    if prop is None:  # pragma: no cover
                        logger.warning(f'saveNodeEdits got EDIT_PROP_TOMB for bad prop {name} on form {node.form.full}')
                        continue

                    callbacks.append((prop.wasDel, (node, oldv), {}))
                    callbacks.append((self.runPropSet, (node, prop, oldv), {}))
                    continue

                if etyp == s_layer.EDIT_TAG_SET:

                    (tag, valu, oldv) = parms

                    callbacks.append((self.runTagAdd, (node, tag, valu), {}))
                    callbacks.append((wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_TOMB_DEL:
                    (tag,) = parms

                    if (oldv := node.getTag(tag)) is not None:
                        callbacks.append((self.runTagAdd, (node, tag, oldv), {}))
                        callbacks.append((wlyr.fire, ('tag:add', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_DEL:

                    (tag, oldv) = parms

                    callbacks.append((self.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_TAG_TOMB:

                    (tag,) = parms

                    oldv = node.getTagFromLayers(tag, strt=1, defval=s_common.novalu)
                    if oldv is s_common.novalu:  # pragma: no cover
                        continue

                    callbacks.append((self.runTagDel, (node, tag, oldv), {}))
                    callbacks.append((wlyr.fire, ('tag:del', ), {'tag': tag, 'node': node.iden()}))
                    continue

                if etyp == s_layer.EDIT_EDGE_ADD or etyp == s_layer.EDIT_EDGE_TOMB_DEL:
                    verb, n2nid = parms
                    callbacks.append((self.runEdgeAdd, (node, verb, n2nid), {}))

                if etyp == s_layer.EDIT_EDGE_DEL or etyp == s_layer.EDIT_EDGE_TOMB:
                    verb, n2nid = parms
                    callbacks.append((self.runEdgeDel, (node, verb, n2nid), {}))

        [await func(*args, **kwargs) for (func, args, kwargs) in callbacks]

        if nodeedits and fireedit:
            await bus.fire('node:edits', edits=nodeedits)

        return saveoff, nodeedits

    @contextlib.asynccontextmanager
    async def getNodeEditor(self, node, runt=None, transaction=False, user=None):

        if node.form.isrunt:
            mesg = f'Cannot edit runt nodes: {node.form.name}.'
            raise s_exc.IsRuntForm(mesg=mesg)

        if runt is None:
            runt = s_scope.get('runt')

        if user is None and runt is not None:
            user = runt.user

        if user is None:
            user = self.core.auth.rootuser

        errs = False
        editor = s_editor.NodeEditor(self, user)
        protonode = editor.loadNode(node)

        try:
            yield protonode
        except Exception:
            errs = True
            raise
        finally:
            if not (errs and transaction):
                nodeedits = editor.getNodeEdits()
                if nodeedits:
                    meta = editor.getEditorMeta()

                    if runt is not None:
                        bus = runt.bus
                    else:
                        bus = None

                    await self.saveNodeEdits(nodeedits, meta, bus=bus)

    @contextlib.asynccontextmanager
    async def getEditor(self, runt=None, transaction=False, user=None):

        if runt is None:
            runt = s_scope.get('runt')

        if user is None and runt is not None:
            user = runt.user

        if user is None:
            user = self.core.auth.rootuser

        errs = False
        editor = s_editor.NodeEditor(self, user)

        try:
            yield editor
        except Exception:
            errs = True
            raise
        finally:
            if not (errs and transaction):
                nodeedits = editor.getNodeEdits()
                if nodeedits:
                    meta = editor.getEditorMeta()

                    if runt is not None:
                        bus = runt.bus
                    else:
                        bus = None

                    await self.saveNodeEdits(nodeedits, meta, bus=bus)

    def reqParentQuorum(self):

        if self.parent is None:
            mesg = f'View ({self.iden}) has no parent.'
            raise s_exc.BadState(mesg=mesg)

        quorum = self.parent.info.get('quorum')
        if quorum is None:
            mesg = f'Parent view of ({self.iden}) does not require quorum voting.'
            raise s_exc.BadState(mesg=mesg)

        if self.parent.wlyr.readonly:
            mesg = f'Parent view of ({self.iden}) has a read-only top layer.'
            raise s_exc.BadState(mesg=mesg)

        return quorum

    def reqNoParentQuorum(self):

        if self.parent is None:
            return

        quorum = self.parent.info.get('quorum')
        if quorum is not None:
            mesg = f'Parent view of ({self.iden}) requires quorum voting.'
            raise s_exc.SynErr(mesg=mesg)

    async def _wipeViewMeta(self):
        for lkey in self.core.slab.scanKeysByPref(self.bidn, db='view:meta'):
            self.core.slab.delete(lkey, db='view:meta')
            await asyncio.sleep(0)

    def getMergeRequest(self):
        byts = self.core.slab.get(self.bidn + b'merge:req', db='view:meta')
        if byts is not None:
            return s_msgpack.un(byts)

    async def getMergingViews(self):
        if self.info.get('quorum') is None:
            mesg = f'View ({self.iden}) does not require quorum voting.'
            raise s_exc.BadState(mesg=mesg)

        idens = []
        for view in list(self.core.views.values()):
            await asyncio.sleep(0)
            if view.parent == self and view.getMergeRequest() is not None:
                idens.append(view.iden)
        return idens

    async def setMergeRequest(self, mergeinfo):
        self.reqParentQuorum()
        mergeinfo['iden'] = s_common.guid()
        mergeinfo['created'] = s_common.now()
        return await self._push('merge:set', mergeinfo)

    def hasKids(self):
        for view in self.core.views.values():
            if view.parent == self:
                return True
        return False

    @s_nexus.Pusher.onPush('merge:set')
    async def _setMergeRequest(self, mergeinfo):
        self.reqParentQuorum()

        s_schemas.reqValidMerge(mergeinfo)
        lkey = self.bidn + b'merge:req'
        self.core.slab.put(lkey, s_msgpack.en(mergeinfo), db='view:meta')
        await self.core.feedBeholder('view:merge:request:set', {'view': self.iden, 'merge': mergeinfo})
        return mergeinfo

    async def setMergeComment(self, comment):
        return await self._push('merge:set:comment', s_common.now(), comment)

    @s_nexus.Pusher.onPush('merge:set:comment')
    async def _setMergeRequestComment(self, updated, comment):
        self.reqParentQuorum()
        merge = self.getMergeRequest()
        if merge is None:
            mesg = 'Cannot set the comment of a merge request that does not exist.'
            raise s_exc.BadState(mesg=mesg)

        merge['updated'] = updated
        merge['comment'] = comment
        s_schemas.reqValidMerge(merge)
        lkey = self.bidn + b'merge:req'
        self.core.slab.put(lkey, s_msgpack.en(merge), db='view:meta')

        await self.core.feedBeholder('view:merge:set', {'view': self.iden, 'merge': merge})

        return merge

    async def delMergeRequest(self):
        return await self._push('merge:del')

    @s_nexus.Pusher.onPush('merge:del')
    async def _delMergeRequest(self):
        self.reqParentQuorum()
        byts = self.core.slab.pop(self.bidn + b'merge:req', db='view:meta')

        await self._delMergeMeta()

        if byts is not None:
            merge = s_msgpack.un(byts)
            await self.core.feedBeholder('view:merge:request:del', {'view': self.iden, 'merge': merge})
            return merge

    async def _delMergeMeta(self):
        for lkey in self.core.slab.scanKeysByPref(self.bidn + b'merge:', db='view:meta'):
            await asyncio.sleep(0)
            self.core.slab.delete(lkey, db='view:meta')

    async def getMergeVotes(self):
        for lkey, byts in self.core.slab.scanByPref(self.bidn + b'merge:vote', db='view:meta'):
            await asyncio.sleep(0)
            yield s_msgpack.un(byts)

    async def getMerges(self):
        '''
        Yield the historical merges into this view.
        '''
        for lkey, bidn in self.core.slab.scanByPrefBack(self.bidn + b'hist:merge:time', db='view:meta'):
            byts = self.core.slab.get(self.bidn + b'hist:merge:iden' + bidn, db='view:meta')
            if byts is not None:
                yield s_msgpack.un(byts)
            await asyncio.sleep(0)

    async def tryToMerge(self, tick):
        # NOTE: must be called from within a nexus handler!

        if self.merging: # pragma: no cover
            return

        if not await self.isMergeReady():
            return

        self.merging = True
        await self.info.set('merging', True)

        self.wlyr.readonly = True
        await self.wlyr.layrinfo.set('readonly', True)

        merge = self.getMergeRequest()
        votes = [vote async for vote in self.getMergeVotes()]

        merge['votes'] = votes
        merge['merged'] = tick

        tick = s_common.int64en(tick)
        bidn = s_common.uhex(merge.get('iden'))

        lkey = self.parent.bidn + b'hist:merge:iden' + bidn
        self.core.slab.put(lkey, s_msgpack.en(merge), db='view:meta')

        lkey = self.parent.bidn + b'hist:merge:time' + tick + bidn
        self.core.slab.put(lkey, bidn, db='view:meta')

        await self.core.feedBeholder('view:merge:init', {'view': self.iden, 'merge': merge, 'votes': votes})

        await self.initMergeTask()

    async def setMergeVote(self, vote):
        self.reqParentQuorum()
        vote['created'] = s_common.now()
        vote['offset'] = await self.wlyr.getEditIndx()
        return await self._push('merge:vote:set', vote)

    def reqValidVoter(self, useriden):

        merge = self.getMergeRequest()
        if merge is None:
            raise s_exc.BadState(mesg=f'View ({self.iden}) does not have a merge request.')

        if merge.get('creator') == useriden:
            raise s_exc.AuthDeny(mesg='A user may not vote for their own merge request.')

    @s_nexus.Pusher.onPush('merge:vote:set')
    async def _setMergeVote(self, vote):

        self.reqParentQuorum()
        s_schemas.reqValidVote(vote)

        useriden = vote.get('user')

        self.reqValidVoter(useriden)

        bidn = s_common.uhex(useriden)

        self.core.slab.put(self.bidn + b'merge:vote' + bidn, s_msgpack.en(vote), db='view:meta')

        await self.core.feedBeholder('view:merge:vote:set', {'view': self.iden, 'vote': vote})

        tick = vote.get('created')
        await self.tryToMerge(tick)

        return vote

    async def setMergeVoteComment(self, useriden, comment):
        return await self._push('merge:vote:set:comment', s_common.now(), useriden, comment)

    @s_nexus.Pusher.onPush('merge:vote:set:comment')
    async def _setMergeVoteComment(self, tick, useriden, comment):
        self.reqParentQuorum()

        uidn = s_common.uhex(useriden)

        lkey = self.bidn + b'merge:vote' + uidn
        byts = self.core.slab.pop(lkey, db='view:meta')

        if byts is None:
            mesg = 'Cannot set the comment for a vote that does not exist.'
            raise s_exc.BadState(mesg=mesg)

        vote = s_msgpack.un(byts)
        vote['updated'] = tick
        vote['comment'] = comment
        self.core.slab.put(lkey, s_msgpack.en(vote), db='view:meta')
        await self.core.feedBeholder('view:merge:vote:set', {'view': self.iden, 'vote': vote})

        return vote

    async def delMergeVote(self, useriden):
        return await self._push('merge:vote:del', useriden, s_common.now())

    @s_nexus.Pusher.onPush('merge:vote:del')
    async def _delMergeVote(self, useriden, tick):

        self.reqParentQuorum()
        uidn = s_common.uhex(useriden)

        vote = None
        byts = self.core.slab.pop(self.bidn + b'merge:vote' + uidn, db='view:meta')

        if byts is not None:
            vote = s_msgpack.un(byts)
            await self.core.feedBeholder('view:merge:vote:del', {'view': self.iden, 'vote': vote})

        await self.tryToMerge(tick)

        return vote

    async def initMergeTask(self):

        if not self.merging:
            return

        if not await self.core.isCellActive():
            return

        self.mergetask = self.core.schedCoro(self.runViewMerge())

    async def finiMergeTask(self):
        if self.mergetask is not None:
            self.mergetask.cancel()
            self.mergetask = None

    async def runViewMerge(self):
        # run a view merge which eventually results in removing the view and top layer
        # this routine must be able to be resumed and may assume that the top layer is
        # not receiving any edits.
        try:

            # ensure there are none marked dirty
            await self.wlyr._saveDirtySodes()

            merge = self.getMergeRequest()
            votes = [vote async for vote in self.getMergeVotes()]

            # merge edits as the merge request user
            meta = {
                'user': merge.get('creator'),
                'merge': merge.get('iden'),
            }

            async def chunked():
                nodeedits = []
                editor = s_editor.NodeEditor(self.parent, merge.get('creator'))

                async for (nid, form, edits) in self.wlyr.iterLayerNodeEdits():

                    if len(edits) == 1 and edits[0][0] == s_layer.EDIT_NODE_TOMB:
                        protonode = await editor.getNodeByNid(nid)
                        if protonode is None:
                            continue

                        await protonode.delEdgesN2(meta=meta)
                        await protonode.delete()

                        nodeedits.extend(editor.getNodeEdits())
                        editor.protonodes.clear()
                    else:
                        realedits = []

                        protonode = None
                        for edit in edits:
                            etyp, parms = edit

                            if etyp == s_layer.EDIT_PROP_TOMB:
                                if protonode is None:
                                    if (protonode := await editor.getNodeByNid(nid)) is None:
                                        continue

                                await protonode.pop(parms[0])
                                continue

                            if etyp == s_layer.EDIT_TAG_TOMB:
                                if protonode is None:
                                    if (protonode := await editor.getNodeByNid(nid)) is None:
                                        continue

                                await protonode.delTag(parms[0])
                                continue

                            if etyp == s_layer.EDIT_TAGPROP_TOMB:
                                if protonode is None:
                                    if (protonode := await editor.getNodeByNid(nid)) is None:
                                        continue

                                (tag, prop) = parms

                                await protonode.delTagProp(tag, prop)
                                continue

                            if etyp == s_layer.EDIT_NODEDATA_TOMB:
                                if protonode is None:
                                    if (protonode := await editor.getNodeByNid(nid)) is None:
                                        continue

                                await protonode.popData(parms[0])
                                continue

                            if etyp == s_layer.EDIT_EDGE_TOMB:
                                if protonode is None:
                                    if (protonode := await editor.getNodeByNid(nid)) is None:
                                        continue

                                (verb, n2nid) = parms

                                await protonode.delEdge(verb, n2nid)
                                continue

                            realedits.append(edit)

                        if protonode is None:
                            nodeedits.append((nid, form, realedits))
                        else:
                            deledits = editor.getNodeEdits()
                            editor.protonodes.clear()
                            if deledits:
                                deledits[0][2].extend(realedits)
                                nodeedits.extend(deledits)
                            else:
                                nodeedits.append((nid, form, realedits))

                    if len(nodeedits) >= 10:
                        yield nodeedits
                        nodeedits.clear()

                if nodeedits:
                    yield nodeedits

            total = self.wlyr.getStorNodeCount()

            count = 0
            nextprog = 1000

            await self.core.feedBeholder('view:merge:prog', {'view': self.iden, 'count': count, 'total': total, 'merge': merge, 'votes': votes})

            async for edits in chunked():

                meta['time'] = s_common.now()

                await self.parent.saveNodeEdits(edits, meta)
                await asyncio.sleep(0)

                count += len(edits)

                if count >= nextprog:
                    await self.core.feedBeholder('view:merge:prog', {'view': self.iden, 'count': count, 'total': total, 'merge': merge, 'votes': votes})
                    nextprog += 1000

            await self.core.feedBeholder('view:merge:fini', {'view': self.iden, 'merge': merge, 'merge': merge, 'votes': votes})

            # remove the view and top layer
            await self.core.delViewWithLayer(self.iden)

        except Exception as e: # pragma: no cover
            logger.exception(f'Error while merging view: {self.iden}')

    async def isMergeReady(self):
        # count the current votes and potentially trigger a merge

        offset = await self.wlyr.getEditIndx()

        quorum = self.reqParentQuorum()

        approvals = 0
        async for vote in self.getMergeVotes():

            if vote.get('offset') != offset:
                continue

            # any disapprovals will hold merging
            if not vote.get('approved'):
                return False

            approvals += 1

        return approvals >= quorum.get('count')

    async def detach(self):
        '''
        Detach the view from its parent but do not change the layers.
        ( this is not reversible! )
        '''
        if not self.parent:
            mesg = 'A view with no parent is already detached.'
            raise s_exc.BadArg(mesg=mesg)

        return await self._push('view:detach')

    @s_nexus.Pusher.onPush('view:detach')
    async def _detach(self):

        # remove any pending merge requests or votes
        await self._delMergeMeta()

        self.parent = None
        await self.info.pop('parent')

        await self.core.feedBeholder('view:set', {'iden': self.iden, 'name': 'parent', 'valu': None},
                                     gates=[self.iden, self.wlyr.iden])

    async def mergeStormIface(self, name, todo):
        '''
        Allow an interface which specifies a generator use case to yield
        (priority, value) tuples and merge results from multiple generators
        yielded in ascending priority order.
        '''
        await self.reqValid()

        root = self.core.auth.rootuser
        funcname, funcargs, funckwargs = todo

        runts = []
        genrs = []

        try:
            for moddef in await self.core.getStormIfaces(name):
                try:
                    query = await self.core.getStormQuery(moddef.get('storm'))
                    modconf = moddef.get('modconf', {})
                    runt = await s_storm.Runtime.anit(query, self, opts={'vars': {'modconf': modconf}}, user=root)
                    runts.append(runt)

                    # let it initialize the function
                    async for item in runt.execute():
                        await asyncio.sleep(0)

                    func = runt.vars.get(funcname)
                    if func is None:
                        continue

                    genrs.append(await func(*funcargs, **funckwargs))

                except Exception as e:  # pragma: no cover
                    logger.exception('mergeStormIface()')

            if genrs:
                async for item in s_common.merggenr2(genrs):
                    yield item

        finally:
            for runt in runts:
                await runt.fini()

    async def callStormIface(self, name, todo):

        await self.reqValid()

        root = self.core.auth.rootuser
        funcname, funcargs, funckwargs = todo

        for moddef in await self.core.getStormIfaces(name):
            try:
                query = await self.core.getStormQuery(moddef.get('storm'))

                modconf = moddef.get('modconf', {})

                # TODO look at caching the function returned as presume a persistant runtime?
                opts = {'vars': {'modconf': modconf}}
                async with await s_storm.Runtime.anit(query, self, opts=opts, user=root) as runt:

                    # let it initialize the function
                    async for item in runt.execute():
                        await asyncio.sleep(0)

                    func = runt.vars.get(funcname)
                    if func is None:
                        continue

                    valu = await func(*funcargs, **funckwargs)
                    yield await s_stormtypes.toprim(valu)

            except Exception as e:
                modname = moddef.get('name')
                logger.exception(f'callStormIface {name} mod: {modname}')

    async def initTrigTask(self):

        if self.trigtask is not None:
            return

        if not await self.core.isCellActive():
            return

        self.trigtask = self.schedCoro(self._trigQueueLoop())

    async def finiTrigTask(self):

        if self.trigtask is not None:
            self.trigtask.cancel()
            self.trigtask = None

    async def _trigQueueLoop(self):

        while not self.isfini:

            async for offs, triginfo in self.trigqueue.gets(0):

                nid = triginfo.get('nid')
                varz = triginfo.get('vars')
                trigiden = triginfo.get('trig')

                try:
                    trig = self.triggers.get(trigiden)
                    if trig is None:
                        continue

                    node = await self.getNodeByNid(nid)
                    if node is None:
                        continue

                    await trig._execute(node, vars=varz)

                except asyncio.CancelledError:  # pragma: no cover
                    raise

                except Exception as e:  # pragma: no cover
                    logger.exception(f'trigQueueLoop() on trigger: {trigiden} view: {self.iden}')

                finally:
                    await self.delTrigQueue(offs)

    async def getStorNodes(self, nid):
        '''
        Return a list of storage nodes for the given nid in layer order.
        NOTE: This returns a COPY of the storage node and will not receive updates!
        '''
        return [layr.getStorNode(nid) for layr in self.layers]

    def init2(self):
        '''
        We have a second round of initialization so the views can get a handle to their parents which might not
        be initialized yet
        '''
        parent = self.info.get('parent')
        if parent is not None:
            self.parent = self.core.getView(parent)

    def isafork(self):
        return self.parent is not None

    def isForkOf(self, viewiden):
        view = self.parent
        while view is not None:
            if view.iden == viewiden:
                return True
            view = view.parent
        return False

    async def _calcForkLayers(self):
        # recompute the proper set of layers for a forked view
        # (this may only be called from within a nexus handler)

        '''
        We spent a lot of time thinking/talking about this so some hefty
        comments are in order:

        For a given stack of views (example below), only the bottom view of
        the stack may have more than one original layer. When adding a new view to the
        top of the stack (via `<viewE>.setViewInfo('parent', <viewD>)`), we
        grab the top layer of each of the views from View D to View B and then
        all of the layers from View A. We know this is the right behavior
        because all views above the bottom view only have one original layer
        (but will include all of the layers of it's parents) which is enforced
        by `setViewInfo()`.

        View D
        - Layer 6 (original to View D)
        - Layer 5 (copied from View C)
        - Layer 4 (copied from View B)
        - Layer 3 (copied from View A)
        - Layer 2 (copied from View A)
        - Layer 1 (copied from View A)

        View C (parent of D)
        - Layer 5 (original to View C)
        - Layer 4 (copied from View B)
        - Layer 3 (copied from View A)
        - Layer 2 (copied from View A)
        - Layer 1 (copied from View A)

        View B (parent of C)
        - Layer 4 (original to View B)
        - Layer 3 (copied from View A)
        - Layer 2 (copied from View A)
        - Layer 1 (copied from View A)

        View A (parent of B)
        - Layer 3
        - Layer 2
        - Layer 1

        Continuing the exercise: when adding View E, it has it's own layer
        (Layer 7). We then copy Layer 6 from View D, Layer 5 from View C, Layer
        4 from View B, and Layers 3-1 from View A (the bottom view). This gives
        us the new view which looks like this:

        View E:
        - Layer 7 (original to View E)
        - Layer 6 (copied from View D)
        - Layer 5 (copied from View C)
        - Layer 4 (copied from View B)
        - Layer 3 (copied from View A)
        - Layer 2 (copied from View A)
        - Layer 1 (copied from View A)

        View D (now parent of View E)
        ... (everything from View D and below is the same as above)
        '''

        layers = []

        # Add the top layer from each of the views that aren't the bottom view.
        # This is the view's original layer.
        view = self
        while view.parent is not None:
            layers.append(view.wlyr)
            view = view.parent

        # Add all of the bottom view's layers.
        layers.extend(view.layers)

        self.layers = layers
        self.wlyr = layers[0]
        self.clearCache()
        await self.info.set('layers', [layr.iden for layr in layers])

    async def pack(self):
        d = {'iden': self.iden}
        d.update(self.info.pack())

        layrinfo = [await lyr.pack() for lyr in self.layers]
        d['layers'] = layrinfo

        triginfo = [t.pack() for _, t in self.triggers.list()]
        d['triggers'] = triginfo

        return d

    async def getFormCounts(self):
        counts = collections.defaultdict(int)
        for layr in self.layers:
            for name, valu in (await layr.getFormCounts()).items():
                counts[name] += valu
        return counts

    async def getPropCount(self, propname, valu=s_common.novalu):
        prop = self.core.model.prop(propname)
        if prop is None:
            mesg = f'No property named {propname}'
            raise s_exc.NoSuchProp(mesg=mesg)

        count = 0
        formname = None
        propname = None

        if prop.isform:
            formname = prop.name
        else:
            propname = prop.name
            if not prop.isuniv:
                formname = prop.form.name

        if valu is s_common.novalu:
            for layr in self.layers:
                await asyncio.sleep(0)
                count += await layr.getPropCount(formname, propname)
            return count

        norm, info = prop.type.norm(valu)

        for layr in self.layers:
            await asyncio.sleep(0)
            count += layr.getPropValuCount(formname, propname, prop.type.stortype, norm)

        return count

    async def getTagPropCount(self, form, tag, propname, valu=s_common.novalu):
        prop = self.core.model.getTagProp(propname)
        if prop is None:
            mesg = f'No tag property named {propname}'
            raise s_exc.NoSuchTagProp(name=propname, mesg=mesg)

        count = 0

        if valu is s_common.novalu:
            for layr in self.layers:
                await asyncio.sleep(0)
                count += await layr.getTagPropCount(form, tag, prop.name)
            return count

        norm, info = prop.type.norm(valu)

        for layr in self.layers:
            await asyncio.sleep(0)
            count += layr.getTagPropValuCount(form, tag, prop.name, prop.type.stortype, norm)

        return count

    async def getPropArrayCount(self, propname, valu=s_common.novalu):
        prop = self.core.model.prop(propname)
        if prop is None:
            mesg = f'No property named {propname}'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not prop.type.isarray:
            mesg = f'Property is not an array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        count = 0
        formname = None
        propname = None

        if prop.isform:
            formname = prop.name
        else:
            propname = prop.name
            if not prop.isuniv:
                formname = prop.form.name

        if valu is s_common.novalu:
            for layr in self.layers:
                await asyncio.sleep(0)
                count += await layr.getPropArrayCount(formname, propname)
            return count

        atyp = prop.type.arraytype
        norm, info = atyp.norm(valu)

        for layr in self.layers:
            await asyncio.sleep(0)
            count += layr.getPropArrayValuCount(formname, propname, atyp.stortype, norm)

        return count

    async def iterEdgeVerbs(self, n1nid, n2nid, strt=0, stop=None):

        last = None
        gens = [layr.iterEdgeVerbs(n1nid, n2nid) for layr in self.layers[strt:stop]]

        async for abrv, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvIndx(abrv)[0]

    def getEdgeCount(self, nid, verb=None, n2=False):

        if n2:
            key = 'n2verbs'
        else:
            key = 'n1verbs'

        ecnt = 0

        for layr in self.layers:
            if (sode := layr._getStorNode(nid)) is None:
                continue

            if sode.get('antivalu') is not None:
                return ecnt

            if (verbs := sode.get(key)) is None:
                continue

            if verb is not None:
                ecnt += verbs.get(verb, 0)
            else:
                ecnt += sum(verbs.values())

        return ecnt

    async def getEdgeVerbs(self):

        for byts, abrv in self.core.indxabrv.iterByPref(s_layer.INDX_EDGE_VERB):
            for layr in self.layers:
                if layr.indxcounts.get(abrv) > 0:
                    yield s_msgpack.un(byts[2:])[0]
                    break

    async def hasNodeEdge(self, n1nid, verb, n2nid, strt=0, stop=None):
        for layr in self.layers[strt:stop]:
            if (retn := await layr.hasNodeEdge(n1nid, verb, n2nid)) is not None:
                return retn

    async def getEdges(self, verb=None):

        last = None
        genrs = [layr.getEdges(verb=verb) for layr in self.layers]

        async for item in s_common.merggenr2(genrs, cmprkey=lambda x: x[:3]):
            edge = item[:3]
            if edge == last:
                continue

            await asyncio.sleep(0)
            last = edge

            if item[-1]:
                continue

            yield edge

    async def iterNodeEdgesN1(self, nid, verb=None, strt=0, stop=None):

        last = None
        gens = [layr.iterNodeEdgesN1(nid, verb=verb) for layr in self.layers[strt:stop]]

        async for item in s_common.merggenr2(gens, cmprkey=lambda x: x[:2]):
            edge = item[:2]
            if edge == last:
                continue

            await asyncio.sleep(0)
            last = edge

            if item[-1]:
                continue

            if verb is None:
                yield self.core.getAbrvIndx(edge[0])[0], edge[1]
            else:
                yield verb, edge[1]

    async def iterNodeEdgesN2(self, nid, verb=None):

        last = None

        async def wrap_liftgenr(lidn, genr):
            async for abrv, n1nid, tomb in genr:
                yield abrv, n1nid, lidn, tomb

        gens = []
        for indx, layr in enumerate(self.layers):
            gens.append(wrap_liftgenr(indx, layr.iterNodeEdgesN2(nid, verb=verb)))

        async for (abrv, n1nid, indx, tomb) in s_common.merggenr2(gens, cmprkey=lambda x: x[:3]):
            if (abrv, n1nid) == last:
                continue

            await asyncio.sleep(0)
            last = (abrv, n1nid)

            if tomb:
                continue

            if indx > 0:
                for layr in self.layers[0:indx]:
                    sode = layr._getStorNode(n1nid)
                    if sode is not None and sode.get('antivalu') is not None:
                        break
                else:
                    if verb is None:
                        yield self.core.getAbrvIndx(abrv)[0], n1nid
                    else:
                        yield verb, n1nid

            else:
                if verb is None:
                    yield self.core.getAbrvIndx(abrv)[0], n1nid
                else:
                    yield verb, n1nid

    async def getNdefRefs(self, buid):
        last = None
        gens = [layr.getNdefRefs(buid) for layr in self.layers]

        async for refsnid, _ in s_common.merggenr2(gens):
            if refsnid == last:
                continue

            await asyncio.sleep(0)
            last = refsnid

            yield refsnid

    async def hasNodeData(self, nid, name, strt=0, stop=None):
        '''
        Return True if the nid has nodedata set on it under the given name,
        False otherwise.
        '''
        for layr in self.layers[strt:stop]:
            if (retn := await layr.hasNodeData(nid, name)) is not None:
                return retn
        return False

    async def getNodeData(self, nid, name, defv=None, strt=0, stop=None):
        '''
        Get nodedata from closest to write layer, no merging involved.
        '''
        for layr in self.layers[strt:stop]:
            ok, valu, tomb = await layr.getNodeData(nid, name)
            if ok:
                if tomb:
                    return defv
                return valu
        return defv

    async def getNodeDataFromLayers(self, nid, name, strt=0, stop=None, defv=None):
        '''
        Get nodedata from closest to write layer, within a specific set of layers.
        '''
        for layr in self.layers[strt:stop]:
            ok, valu, tomb = await layr.getNodeData(nid, name)
            if ok:
                if tomb:
                    return defv
                return valu
        return defv

    async def iterNodeData(self, nid):
        '''
        Returns:  Iterable[Tuple[str, Any]]
        '''
        last = None
        gens = [layr.iterNodeData(nid) for layr in self.layers]

        async for abrv, valu, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvIndx(abrv)[0], valu

    async def iterNodeDataKeys(self, nid):
        '''
        Yield each data key from the given node by nid.
        '''
        last = None
        gens = [layr.iterNodeDataKeys(nid) for layr in self.layers]

        async for abrv, tomb in s_common.merggenr2(gens, cmprkey=lambda x: x[0]):
            if abrv == last:
                continue

            await asyncio.sleep(0)
            last = abrv

            if tomb:
                continue

            yield self.core.getAbrvIndx(abrv)[0]

    async def _initViewLayers(self):

        for iden in self.info.get('layers'):

            layr = self.core.layers.get(iden)

            if layr is None:
                self.invalid = iden
                logger.warning('view %r has missing layer %r' % (self.iden, iden))
                continue

            self.layers.append(layr)

        self.wlyr = self.layers[0]

    async def reqValid(self):
        if self.invalid is not None:
            raise s_exc.NoSuchLayer(mesg=f'No such layer {self.invalid}', iden=self.invalid)

    async def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        await self.reqValid()

        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        info = opts.get('_loginfo', {})
        info.update({'mode': opts.get('mode', 'storm'), 'view': self.iden})
        self.core._logStormQuery(text, user, info=info)

        taskiden = opts.get('task')
        taskinfo = {'query': text, 'view': self.iden}

        with s_scope.enter({'user': user}):

            await self.core.boss.promote('storm', user=user, info=taskinfo, taskiden=taskiden)

            mode = opts.get('mode', 'storm')

            query = await self.core.getStormQuery(text, mode=mode)
            async with await s_storm.Runtime.anit(query, self, opts=opts, user=user) as runt:
                async for node, path in runt.execute():
                    yield node

    async def callStorm(self, text, opts=None):
        user = self.core._userFromOpts(opts)
        try:

            async for item in self.eval(text, opts=opts):
                await asyncio.sleep(0)  # pragma: no cover

        except s_stormctrl.StormReturn as e:
            # Catch return( ... ) values and return the
            # primitive version of that item.
            return await s_stormtypes.toprim(e.item)

        except asyncio.CancelledError:
            logger.warning(f'callStorm cancelled',
                           extra={'synapse': {'text': text, 'username': user.name, 'user': user.iden}})
            raise

        except Exception:
            logger.exception(f'Error during callStorm execution for {{ {text} }}',
                             extra={'synapse': {'text': text, 'username': user.name, 'user': user.iden}})
            raise

        # Any other exceptions will be raised to
        # callers as expected.

    async def nodes(self, text, opts=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        return [n async for n in self.eval(text, opts=opts)]

    async def stormlist(self, text, opts=None):
        # an ease-of-use API for testing
        return [m async for m in self.storm(text, opts=opts)]

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            ((str,dict)): Storm messages.
        '''
        await self.reqValid()

        if not isinstance(text, str):
            mesg = 'Storm query text must be a string'
            raise s_exc.BadArg(mesg=mesg)

        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE)

        taskinfo = {'query': text, 'view': self.iden}
        taskiden = opts.get('task')
        keepalive = opts.get('keepalive')
        if keepalive is not None and keepalive <= 0:
            raise s_exc.BadArg(mesg=f'keepalive must be > 0; got {keepalive}')
        synt = await self.core.boss.promote('storm', user=user, info=taskinfo, taskiden=taskiden)

        show = opts.get('show', set())

        mode = opts.get('mode', 'storm')
        editformat = opts.get('editformat', 'nodeedits')
        if editformat not in ('nodeedits', 'count', 'none'):
            raise s_exc.BadConfValu(mesg=f'invalid edit format, got {editformat}', name='editformat', valu=editformat)

        texthash = hashlib.md5(text.encode(errors='surrogatepass'), usedforsecurity=False).hexdigest()

        async def runStorm():
            cancelled = False
            tick = s_common.now()
            abstick = s_common.mononow()
            count = 0
            try:

                # Always start with an init message.
                await chan.put(('init', {'tick': tick, 'text': text, 'abstick': abstick,
                                         'hash': texthash, 'task': synt.iden}))

                # Try text parsing. If this fails, we won't be able to get a storm
                # runtime, so catch and pass the `err` message
                query = await self.core.getStormQuery(text, mode=mode)

                shownode = (not show or 'node' in show)

                with s_scope.enter({'user': user}):

                    async with await s_storm.Runtime.anit(query, self, opts=opts, user=user) as runt:

                        if keepalive:
                            runt.schedCoro(runt.keepalive(keepalive))

                        if not show:
                            runt.bus.link(chan.put)

                        else:
                            [runt.bus.on(n, chan.put) for n in show]

                        if shownode:
                            async for pode in runt.iterStormPodes():
                                await chan.put(('node', pode))
                                count += 1

                        else:
                            info = opts.get('_loginfo', {})
                            info.update({'mode': opts.get('mode', 'storm'), 'view': self.iden})
                            self.core._logStormQuery(text, user, info=info)
                            async for item in runt.execute():
                                count += 1

            except s_stormctrl.StormExit:
                pass

            except asyncio.CancelledError:
                logger.warning('Storm runtime cancelled.',
                               extra={'synapse': {'text': text, 'username': user.name, 'user': user.iden}})
                cancelled = True
                raise

            except Exception as e:
                logger.exception(f'Error during storm execution for {{ {text} }}',
                                 extra={'synapse': {'text': text, 'username': user.name, 'user': user.iden}})
                enfo = s_common.err(e)
                enfo[1].pop('esrc', None)
                enfo[1].pop('ename', None)
                await chan.put(('err', enfo))

            finally:
                if not cancelled:
                    abstock = s_common.mononow()
                    abstook = abstock - abstick
                    tock = tick + abstook
                    await chan.put(('fini', {'tock': tock, 'abstock': abstock, 'took': abstook, 'count': count, }))

        await synt.worker(runStorm(), name='runstorm')

        editformat = opts.get('editformat', 'nodeedits')

        while True:

            mesg = await chan.get()
            kind = mesg[0]

            if kind == 'node':
                yield mesg
                continue

            if kind == 'node:edits':

                if editformat == 'nodeedits':

                    nodeedits = s_common.jsonsafe_nodeedits(mesg[1]['edits'])
                    mesg[1]['edits'] = nodeedits
                    yield mesg

                    continue

                if editformat == 'none':
                    continue

                assert editformat == 'count'

                count = sum(len(edit[2]) for edit in mesg[1].get('edits', ()))
                mesg = ('node:edits:count', {'count': count})
                yield mesg
                continue

            if kind == 'fini':
                yield mesg
                break

            yield mesg

    async def iterStormPodes(self, text, opts=None):

        await self.reqValid()

        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        taskinfo = {'query': text, 'view': self.iden}
        taskiden = opts.get('task')
        await self.core.boss.promote('storm', user=user, info=taskinfo, taskiden=taskiden)

        mode = opts.get('mode', 'storm')
        query = await self.core.getStormQuery(text, mode=mode)

        with s_scope.enter({'user': user}):
            async with await s_storm.Runtime.anit(query, self, opts=opts, user=user) as runt:
                async for pode in runt.iterStormPodes():
                    yield pode

    @s_nexus.Pusher.onPushAuto('trig:q:add', passitem=True)
    async def addTrigQueue(self, triginfo, nexsitem):
        nexsoff, nexsmesg = nexsitem
        self.trigqueue.add(triginfo, indx=nexsoff)

    @s_nexus.Pusher.onPushAuto('trig:q:del')
    async def delTrigQueue(self, offs):
        self.trigqueue.pop(offs)

    @s_nexus.Pusher.onPushAuto('view:set')
    async def setViewInfo(self, name, valu):
        '''
        Set a mutable view property.
        '''
        if name not in ('name', 'desc', 'parent', 'nomerge', 'protected', 'quorum'):
            # TODO: Remove nomerge after Synapse 3.x.x
            mesg = f'{name} is not a valid view info key'
            raise s_exc.BadOptValu(mesg=mesg)

        if name == 'parent':

            parent = self.core.reqView(valu, mesg='The parent view must already exist.')
            if parent.iden == self.iden:
                mesg = 'A view may not have parent set to itself.'
                raise s_exc.BadArg(mesg=mesg)

            if parent.isForkOf(self.iden):
                mesg = 'Circular dependency of view parents is not supported.'
                raise s_exc.BadArg(mesg=mesg)

            if self.parent is not None:
                if self.parent.iden == parent.iden:
                    return valu
                mesg = 'You may not set parent on a view which already has one.'
                raise s_exc.BadArg(mesg=mesg)

            if len(self.layers) != 1:
                mesg = 'You may not set parent on a view which has more than one layer.'
                raise s_exc.BadArg(mesg=mesg)

            self.parent = parent
            await self.info.set(name, valu)

            await self._calcForkLayers()

            for view in self.core.views.values():
                if view.isForkOf(self.iden):
                    await view._calcForkLayers()

            self.core._calcViewsByLayer()

        else:
            if name == 'quorum':
                # TODO hack a schema test until the setViewInfo API is updated to
                # enforce ( which will need to be done very carefully to prevent
                # existing non-compliant values from causing issues with existing views )
                if valu is not None:
                    vdef = self.info.pack()
                    vdef['quorum'] = s_msgpack.deepcopy(valu)
                    s_schemas.reqValidView(vdef)
                else:
                    for view in self.core.views.values():
                        if view.parent != self:
                            continue
                        if view.getMergeRequest() is not None:
                            await view._delMergeRequest()

            if valu is None:
                await self.info.pop(name)
            else:
                await self.info.set(name, valu)

        await self.core.feedBeholder('view:set', {'iden': self.iden, 'name': name, 'valu': valu},
                                     gates=[self.iden, self.layers[0].iden])
        return valu

    async def addLayer(self, layriden, indx=None):
        if any(layriden == layr.iden for layr in self.layers):
            raise s_exc.DupIden(mesg='May not have the same layer in a view twice')

        return await self._push('view:addlayer', layriden, indx)

    @s_nexus.Pusher.onPush('view:addlayer')
    async def _addLayer(self, layriden, indx=None):

        for view in self.core.views.values():
            if view.parent is self:
                raise s_exc.ReadOnlyLayer(mesg='May not change layers that have been forked from')

        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of forked view')

        layr = self.core.layers.get(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

        if layr in self.layers:
            return

        if indx is None:
            self.layers.append(layr)
        else:
            self.layers.insert(indx, layr)

        self.wlyr = self.layers[0]

        await self.info.set('layers', [lyr.iden for lyr in self.layers])
        await self.core.feedBeholder('view:addlayer', {'iden': self.iden, 'layer': layriden, 'indx': indx}, gates=[self.iden, layriden])
        self.core._calcViewsByLayer()

    @s_nexus.Pusher.onPushAuto('view:setlayers')
    async def setLayers(self, layers):
        '''
        Set the view layers from a list of idens.
        NOTE: view layers are stored "top down" (the write layer is self.layers[0])
        '''
        layrs = []

        if self.parent is not None:
            mesg = 'You cannot set the layers of a forked view.'
            raise s_exc.BadArg(mesg=mesg)

        for iden in layers:
            layr = self.core.layers.get(iden)
            if layr is None:
                raise s_exc.NoSuchLayer(mesg=f'No such layer {iden}', iden=iden)
            if not layrs and layr.readonly:
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {layr.iden} must not be read-only')

            layrs.append(layr)

        self.invalid = None
        self.layers = layrs
        self.wlyr = layrs[0]
        self.clearCache()

        await self.info.set('layers', layers)
        await self.core.feedBeholder('view:setlayers', {'iden': self.iden, 'layers': layers}, gates=[self.iden, layers[0]])

        await self._calcChildViews()
        self.core._calcViewsByLayer()

    async def _calcChildViews(self):

        todo = collections.deque([self])

        byparent = collections.defaultdict(list)
        for view in self.core.views.values():
            if view.parent is None:
                continue

            byparent[view.parent].append(view)

        while todo:

            view = todo.pop()

            for child in byparent.get(view, ()):

                layers = [child.layers[0]]
                layers.extend(view.layers)

                child.layers = layers
                child.wlyr = layers[0]
                self.clearCache()

                # convert layers to a list of idens...
                lids = [layr.iden for layr in layers]
                await child.info.set('layers', lids)

                await self.core.feedBeholder('view:setlayers', {'iden': child.iden, 'layers': lids}, gates=[child.iden, lids[0]])

                todo.append(child)

    async def insertParentFork(self, useriden, name=None):
        '''
        Insert a new View between a forked View and its parent.

        Returns:
            New view definition with the same perms as the current fork.
        '''
        if not self.isafork():
            mesg = f'View ({self.iden}) is not a fork, cannot insert a new fork between it and parent.'
            raise s_exc.BadState(mesg=mesg)

        ctime = s_common.now()
        layriden = s_common.guid()

        ldef = {
            'iden': layriden,
            'created': ctime,
            'creator': useriden,
            'lockmemory': self.core.conf.get('layers:lockmemory'),
            'logedits': self.core.conf.get('layers:logedits'),
            'readonly': False
        }

        vdef = {
            'iden': s_common.guid(),
            'created': ctime,
            'creator': useriden,
            'parent': self.parent.iden,
            'layers': [layriden] + [lyr.iden for lyr in self.parent.layers]
        }

        if name is not None:
            vdef['name'] = name

        s_layer.reqValidLdef(ldef)
        s_schemas.reqValidView(vdef)

        return await self._push('view:forkparent', ldef, vdef)

    @s_nexus.Pusher.onPush('view:forkparent', passitem=True)
    async def _insertParentFork(self, ldef, vdef, nexsitem):

        s_layer.reqValidLdef(ldef)
        s_schemas.reqValidView(vdef)

        if self.getMergeRequest() is not None:
            await self._delMergeRequest()

        await self.core._addLayer(ldef, nexsitem)
        await self.core._addView(vdef)

        forkiden = vdef.get('iden')
        self.parent = self.core.reqView(forkiden)
        await self.info.set('parent', forkiden)

        await self._calcForkLayers()

        for view in self.core.views.values():
            if view.isForkOf(self.iden):
                await view._calcForkLayers()

        self.core._calcViewsByLayer()

        authgate = await self.core.getAuthGate(self.iden)
        if authgate is None:  # pragma: no cover
            return await self.parent.pack()

        for userinfo in authgate.get('users'):
            useriden = userinfo.get('iden')
            if (user := self.core.auth.user(useriden)) is None:  # pragma: no cover
                logger.warning(f'View {self.iden} AuthGate refers to unknown user {useriden}')
                continue

            await user.setRules(userinfo.get('rules'), gateiden=forkiden, nexs=False)
            await user.setAdmin(userinfo.get('admin'), gateiden=forkiden, logged=False)

        for roleinfo in authgate.get('roles'):
            roleiden = roleinfo.get('iden')
            if (role := self.core.auth.role(roleiden)) is None:  # pragma: no cover
                logger.warning(f'View {self.iden} AuthGate refers to unknown role {roleiden}')
                continue

            await role.setRules(roleinfo.get('rules'), gateiden=forkiden, nexs=False)

        return await self.parent.pack()

    async def fork(self, ldef=None, vdef=None):
        '''
        Make a new view inheriting from this view with the same layers and a new write layer on top

        Args:
            ldef:  layer parameter dict
            vdef:  view parameter dict
            Passed through to cortex.addLayer

        Returns:
            new view object, with an iden the same as the new write layer iden
        '''
        if ldef is None:
            ldef = {}

        if vdef is None:
            vdef = {}

        ldef = await self.core.addLayer(ldef)
        layriden = ldef.get('iden')

        vdef['parent'] = self.iden
        vdef['layers'] = [layriden] + [lyr.iden for lyr in self.layers]

        return await self.core.addView(vdef)

    async def merge(self, useriden=None, force=False):
        '''
        Merge this view into its parent.  All changes made to this view will be applied to the parent.  Parent's
        triggers will be run.
        '''
        if useriden is None:
            user = await self.core.auth.getUserByName('root')
        else:
            user = await self.core.auth.reqUser(useriden)

        await self.mergeAllowed(user, force=force)

        taskinfo = {'merging': self.iden, 'view': self.iden}
        await self.core.boss.promote('storm', user=user, info=taskinfo)

        meta = {
            'time': s_common.now(),
            'user': user.iden
        }

        editor = s_editor.NodeEditor(self.parent, user)

        async for (nid, form, edits) in self.wlyr.iterLayerNodeEdits():

            if len(edits) == 1 and edits[0][0] == s_layer.EDIT_NODE_TOMB:
                protonode = await editor.getNodeByNid(nid)
                if protonode is None:
                    continue

                await protonode.delEdgesN2(meta=meta)
                await protonode.delete()

                deledits = editor.getNodeEdits()
                await self.parent.saveNodeEdits(deledits, meta)

                editor.protonodes.clear()
                continue

            realedits = []

            protonode = None
            for edit in edits:
                etyp, parms = edit

                if etyp == s_layer.EDIT_PROP_TOMB:
                    if protonode is None:
                        if (protonode := await editor.getNodeByNid(nid)) is None:
                            continue

                    await protonode.pop(parms[0])
                    continue

                if etyp == s_layer.EDIT_TAG_TOMB:
                    if protonode is None:
                        if (protonode := await editor.getNodeByNid(nid)) is None:
                            continue

                    await protonode.delTag(parms[0])
                    continue

                if etyp == s_layer.EDIT_TAGPROP_TOMB:
                    if protonode is None:
                        if (protonode := await editor.getNodeByNid(nid)) is None:
                            continue

                    (tag, prop) = parms

                    await protonode.delTagProp(tag, prop)
                    continue

                if etyp == s_layer.EDIT_NODEDATA_TOMB:
                    if protonode is None:
                        if (protonode := await editor.getNodeByNid(nid)) is None:
                            continue

                    await protonode.popData(parms[0])
                    continue

                if etyp == s_layer.EDIT_EDGE_TOMB:
                    if protonode is None:
                        if (protonode := await editor.getNodeByNid(nid)) is None:
                            continue

                    (verb, n2nid) = parms

                    await protonode.delEdge(verb, n2nid)
                    continue

                realedits.append(edit)

            if protonode is None:
                await self.parent.storNodeEdits([(nid, form, realedits)], meta)
                continue

            deledits = editor.getNodeEdits()
            editor.protonodes.clear()

            if deledits:
                deledits[0][2].extend(realedits)
                await self.parent.storNodeEdits(deledits, meta)
            else:
                await self.parent.storNodeEdits([(nid, form, realedits)], meta)

    async def wipeLayer(self, useriden=None):
        '''
        Delete the data in the write layer by generating del nodeedits.
        Triggers will be run.
        '''

        if useriden is None:
            user = await self.core.auth.getUserByName('root')
        else:
            user = await self.core.auth.reqUser(useriden)

        await self.wipeAllowed(user)

        meta = {
            'time': s_common.now(),
            'user': user.iden
        }

        async for nodeedit in self.layers[0].iterWipeNodeEdits():
            await self.saveNodeEdits([nodeedit], meta)

    def _confirm(self, user, perms):
        layriden = self.layers[0].iden
        if user.allowed(perms, gateiden=layriden):
            return

        perm = '.'.join(perms)
        mesg = f'User ({user.name}) must have permission {perm} on write layer {layriden} of view {self.iden}'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=user.iden, username=user.name)

    async def mergeAllowed(self, user=None, force=False):
        '''
        Check whether a user can merge a view into its parent.

        NOTE: This API may not be used to check for merges based on quorum votes.
        '''
        if self.parent is None:
            raise s_exc.CantMergeView(mesg=f'Cannot merge view ({self.iden}) that has not been forked.')

        if self.info.get('protected'):
            raise s_exc.CantMergeView(mesg=f'Cannot merge view ({self.iden}) that has protected set.')

        if self.parent.info.get('quorum') is not None:
            raise s_exc.CantMergeView(mesg=f'Cannot merge view({self.iden}). Parent view requires quorum voting.')

        if self.trigqueue.size and not force:
            raise s_exc.CantMergeView(mesg=f'There are still {self.trigqueue.size} triggers waiting to complete.', canforce=True)

        parentlayr = self.parent.layers[0]
        if parentlayr.readonly:
            raise s_exc.ReadOnlyLayer(mesg="May not merge if the parent's write layer is read-only")

        for view in self.core.views.values():
            if view.parent == self:
                raise s_exc.CantMergeView(mesg='Cannot merge a view that has children itself')

        if user is None or user.isAdmin() or user.isAdmin(gateiden=parentlayr.iden):
            return

        async for nodeedit in self.wlyr.iterLayerNodeEdits():
            for offs, perm in s_layer.getNodeEditPerms([nodeedit]):
                self.parent._confirm(user, perm)
                await asyncio.sleep(0)

    async def wipeAllowed(self, user=None):
        '''
        Check whether a user can wipe the write layer in the current view.
        '''
        if user is None or user.isAdmin():
            return

        async for nodeedit in self.wlyr.iterWipeNodeEdits():
            for offs, perm in s_layer.getNodeEditPerms([nodeedit]):
                self._confirm(user, perm)
                await asyncio.sleep(0)

    async def runTagAdd(self, node, tag, valu):

        if self.core.migration:
            return

        # Run any trigger handlers
        await self.triggers.runTagAdd(node, tag)

    async def runTagDel(self, node, tag, valu):

        if self.core.migration:
            return

        await self.triggers.runTagDel(node, tag)

    async def runNodeAdd(self, node):

        if self.core.migration:
            return

        await self.triggers.runNodeAdd(node)

    async def runNodeDel(self, node):

        if self.core.migration:
            return

        await self.triggers.runNodeDel(node)

    async def runPropSet(self, node, prop, oldv):
        '''
        Handle when a prop set trigger event fired
        '''
        if self.core.migration:
            return

        await self.triggers.runPropSet(node, prop, oldv)

    async def runEdgeAdd(self, n1, edge, n2):

        if self.core.migration:
            return

        await self.triggers.runEdgeAdd(n1, edge, n2)

    async def runEdgeDel(self, n1, edge, n2):

        if self.core.migration:
            return

        await self.triggers.runEdgeDel(n1, edge, n2)

    async def addTrigger(self, tdef):
        '''
        Adds a trigger to the view.
        '''
        iden = tdef.get('iden')
        if iden is None:
            tdef['iden'] = s_common.guid()
        elif self.triggers.get(iden) is not None:
            raise s_exc.DupIden(mesg='A trigger with this iden already exists')

        root = await self.core.auth.getUserByName('root')

        tdef.setdefault('created', s_common.now())
        tdef.setdefault('user', root.iden)
        tdef.setdefault('async', False)
        tdef.setdefault('enabled', True)

        s_trigger.reqValidTdef(tdef)

        return await self._push('trigger:add', tdef)

    @s_nexus.Pusher.onPush('trigger:add')
    async def _onPushAddTrigger(self, tdef):

        s_trigger.reqValidTdef(tdef)

        trig = self.trigdict.get(tdef['iden'])
        if trig is not None:
            return self.triggers.get(tdef['iden']).pack()

        gate = self.core.auth.getAuthGate(tdef['iden'])
        if gate is not None:
            raise s_exc.DupIden(mesg='An AuthGate with this iden already exists')

        user = self.core.auth.user(tdef['user'])
        await self.core.getStormQuery(tdef['storm'])

        trig = await self.triggers.load(tdef)

        await self.trigdict.set(trig.iden, tdef)
        await self.core.auth.addAuthGate(trig.iden, 'trigger')
        await user.setAdmin(True, gateiden=tdef.get('iden'), logged=False)

        await self.core.feedBeholder('trigger:add', trig.pack(), gates=[trig.iden])

        return trig.pack()

    async def getTrigger(self, iden):
        trig = self.triggers.get(iden)
        if trig is None:
            raise s_exc.NoSuchIden("Trigger not found")

        return trig

    async def delTrigger(self, iden):
        trig = self.triggers.get(iden)
        if trig is None:
            raise s_exc.NoSuchIden("Trigger not found")

        return await self._push('trigger:del', iden)

    @s_nexus.Pusher.onPush('trigger:del')
    async def _delTrigger(self, iden):
        '''
        Delete a trigger from the view.
        '''
        trig = self.triggers.pop(iden)
        if trig is None:
            return

        await self.core.feedBeholder('trigger:del', {'iden': trig.iden, 'view': trig.view.iden}, gates=[trig.iden])
        await self.trigdict.pop(trig.iden)
        await self.core.auth.delAuthGate(trig.iden)

    @s_nexus.Pusher.onPushAuto('trigger:set')
    async def setTriggerInfo(self, iden, name, valu):
        trig = self.triggers.get(iden)
        if trig is None:
            raise s_exc.NoSuchIden("Trigger not found")
        await trig.set(name, valu)

        await self.core.feedBeholder('trigger:set', {'iden': trig.iden, 'view': trig.view.iden, 'name': name, 'valu': valu}, gates=[trig.iden])

    async def listTriggers(self):
        '''
        List all the triggers in the view.
        '''
        trigs = self.triggers.list()
        return trigs

    async def delete(self):
        '''
        Delete the metadata for this view.

        Note: this does not delete any layer storage.
        '''
        await self.fini()
        await self.node.pop()
        await self._wipeViewMeta()
        shutil.rmtree(self.dirn, ignore_errors=True)

    async def addNode(self, form, valu, props=None, user=None, norminfo=None):

        await self.reqValid()

        if user is None:
            if (runt := s_scope.get('runt')) is not None:
                user = runt.user
            else:
                user = self.core.auth.rootuser

        async with self.getEditor(user=user, transaction=True) as editor:
            node = await editor.addNode(form, valu, props=props, norminfo=norminfo)

        return await self.getNodeByBuid(node.buid)

    async def addNodes(self, nodedefs, user=None):
        '''
        Add/merge nodes in bulk.

        The addNodes API is designed for bulk adds which will
        also set properties, add tags, add edges, and set nodedata to existing nodes.
        Nodes are specified as a list of the following tuples:

            ( (form, valu), {'props':{}, 'tags':{}})

        Args:
            nodedefs (list): A list of nodedef tuples.

        Returns:
            (list): A list of xact messages.
        '''
        await self.reqValid()

        runt = s_scope.get('runt')

        if user is None:
            if runt is not None:
                user = runt.user
            else:
                user = self.core.auth.rootuser

        if self.readonly:
            mesg = 'The view is in read-only mode.'
            raise s_exc.IsReadOnly(mesg=mesg)

        for nodedefn in nodedefs:
            node = await self._addNodeDef(nodedefn, user=user, runt=runt)
            if node is not None:
                yield node

            await asyncio.sleep(0)

    async def _addNodeDef(self, nodedefn, user, runt=None):

        n2buids = set()

        (formname, formvalu), forminfo = nodedefn

        props = forminfo.get('props')

        # remove any universal created props...
        if props is not None:
            props.pop('.created', None)

        async with self.getEditor(user=user) as editor:

            try:
                protonode = await editor.addNode(formname, formvalu)
            except Exception as e:
                if runt is not None:
                    await runt.warn(str(e))

                logger.exception(f'Error adding node {formname}={formvalu}')
                return

            if props is not None:
                for propname, propvalu in props.items():
                    try:
                        await protonode.set(propname, propvalu)
                    except Exception as e:
                        if runt is not None:
                            await runt.warn(str(e))

                        mesg = f'Error adding prop {propname}={propvalu} to node {formname}={formvalu}'
                        logger.exception(mesg)

            tags = forminfo.get('tags')
            if tags is not None:
                for tagname, tagvalu in tags.items():
                    try:
                        await protonode.addTag(tagname, tagvalu)
                    except Exception as e:
                        if runt is not None:
                            await runt.warn(str(e))

                        mesg = f'Error adding tag {tagname}'
                        if tagvalu is not None:
                            mesg += f'={tagvalu}'
                        mesg += f' to node {formname}={formvalu}'
                        logger.exception(mesg)

            nodedata = forminfo.get('nodedata')
            if isinstance(nodedata, dict):
                for dataname, datavalu in nodedata.items():
                    if not isinstance(dataname, str):
                        continue

                    try:
                        await protonode.setData(dataname, datavalu)
                    except Exception as e:
                        if runt is not None:
                            await runt.warn(str(e))

                        logger.exception(f'Error adding nodedata {dataname} to node {formname}={formvalu}')

            tagprops = forminfo.get('tagprops')
            if tagprops is not None:
                for tag, props in tagprops.items():
                    for name, valu in props.items():
                        try:
                            await protonode.setTagProp(tag, name, valu)
                        except Exception as e:
                            if runt is not None:
                                await runt.warn(str(e))

                            mesg = f'Error adding tagprop {tag}:{name}={valu} to node {formname}={formvalu}'
                            logger.exception(mesg)

            if (edges := forminfo.get('edges')) is not None:
                n2adds = []
                for verb, n2iden in edges:
                    if isinstance(n2iden, (tuple, list)):
                        (n2formname, n2valu) = n2iden
                        n2form = self.core.model.form(n2formname)
                        if n2form is None:
                            continue

                        try:
                            n2valu, _ = n2form.type.norm(n2valu)
                        except s_exc.BadTypeValu as e:
                            continue

                        n2buid = s_common.buid((n2formname, n2valu))
                        n2nid = self.core.getNidByBuid(n2buid)
                        if n2nid is None:
                            n2adds.append((n2iden, verb, n2buid))
                            continue

                    elif isinstance(n2iden, str) and s_common.isbuidhex(n2iden):
                        n2nid = self.core.getNidByBuid(s_common.uhex(n2iden))
                        if n2nid is None:
                            continue
                    else:
                        continue

                    try:
                        await protonode.addEdge(verb, n2nid)
                    except Exception as e:
                        if runt is not None:
                            await runt.warn(str(e))

                        logger.exception(f'Error adding edge -(verb)> {n2iden} to node {formname}={formvalu}')

                if n2adds:
                    async with self.getEditor() as n2editor:
                        for (n2ndef, verb, n2buid) in n2adds:
                            try:
                                await n2editor.addNode(*n2ndef)
                            except Exception as e:
                                if runt is not None:
                                    await runt.warn(str(e))

                                n2form, n2valu = n2ndef
                                logger.exception(f'Error adding node {n2form}={n2valu}')

                    for (n2ndef, verb, n2buid) in n2adds:
                        if (nid := self.core.getNidByBuid(n2buid)) is not None:
                            try:
                                await protonode.addEdge(verb, nid)
                            except Exception as e:
                                if runt is not None:
                                    await runt.warn(str(e))

                                logger.exception(f'Error adding edge -(verb)> {n2iden} to node {formname}={formvalu}')

        return await self.getNodeByBuid(protonode.buid)

    async def getTagNode(self, name):
        '''
        Retrieve a cached tag node. Requires name is normed. Does not add.
        '''
        return await self.tagcache.aget(name)

    async def _getTagNode(self, tagnorm):

        tagnode = await self.getNodeByBuid(s_common.buid(('syn:tag', tagnorm)))
        if tagnode is not None:
            isnow = tagnode.get('isnow')
            while isnow is not None:
                tagnode = await self.getNodeByBuid(s_common.buid(('syn:tag', isnow)))
                isnow = tagnode.get('isnow')

        if tagnode is None:
            return s_common.novalu

        return tagnode

    async def getNodeByBuid(self, buid, tombs=False):
        '''
        Retrieve a node tuple by binary id.

        Args:
            buid (bytes): The binary ID for the node.

        Returns:
            Optional[s_node.Node]: The node object or None.

        '''
        nid = self.core.getNidByBuid(buid)
        if nid is None:
            return None

        return await self._joinStorNode(nid, tombs=tombs)

    async def getNodeByNid(self, nid, tombs=False):
        return await self._joinStorNode(nid, tombs=tombs)

    async def getNodeByNdef(self, ndef):
        '''
        Return a single Node by (form,valu) tuple.

        Args:
            ndef ((str,obj)): A (form,valu) ndef tuple.  valu must be
            normalized.

        Returns:
            (synapse.lib.node.Node): The Node or None.
        '''
        buid = s_common.buid(ndef)
        return await self.getNodeByBuid(buid)

    async def _joinStorNode(self, nid, tombs=False):

        node = self.livenodes.get(nid)
        if node is not None:
            await asyncio.sleep(0)

            if not tombs and not node.hasvalu():
                return None
            return node

        soderefs = []
        for layr in self.layers:
            sref = layr.genStorNodeRef(nid)
            if tombs is False:
                if sref.sode.get('antivalu') is not None:
                    return None
                elif sref.sode.get('valu') is not None:
                    tombs = True

            soderefs.append(sref)

        return await self._joinSodes(nid, soderefs)

    async def _joinSodes(self, nid, soderefs):

        node = self.livenodes.get(nid)
        if node is not None:
            await asyncio.sleep(0)
            return node

        ndef = None
        # make sure at least one layer has the primary property
        for envl in soderefs:
            valt = envl.sode.get('valu')
            if valt is not None:
                ndef = (envl.sode.get('form'), valt[0])
                break

        if ndef is None:
            await asyncio.sleep(0)
            return None

        node = s_node.Node(self, nid, ndef, soderefs)

        self.livenodes[nid] = node
        self.nodecache.append(node)

        await asyncio.sleep(0)
        return node

    async def addNodeEdits(self, edits, meta):
        '''
        A telepath compatible way to apply node edits to a view.

        NOTE: This does cause trigger execution.
        '''
        await self.reqValid()

        user = await self.core.auth.reqUser(meta.get('user'))

        # go with the anti-pattern for now...
        await self.saveNodeEdits(edits, meta=meta)

    async def storNodeEdits(self, edits, meta):
        await self.saveNodeEdits(edits, meta=meta)

    async def delTombstone(self, nid, tombtype, tombinfo, runt=None):

        if (ndef := self.core.getNidNdef(nid)) is None:
            raise s_exc.BadArg(f'delTombstone() got an invalid nid: {nid}')

        edit = None

        if tombtype == s_layer.INDX_PROP:
            (form, prop) = tombinfo
            if prop is None:
                edit = [((s_layer.EDIT_NODE_TOMB_DEL), ())]
            else:
                edit = [((s_layer.EDIT_PROP_TOMB_DEL), (prop,))]

        elif tombtype == s_layer.INDX_TAG:
            (form, tag) = tombinfo
            edit = [((s_layer.EDIT_TAG_TOMB_DEL), (tag,))]

        elif tombtype == s_layer.INDX_TAGPROP:
            (form, tag, prop) = tombinfo
            edit = [((s_layer.EDIT_TAGPROP_TOMB_DEL), (tag, prop))]

        elif tombtype == s_layer.INDX_NODEDATA:
            (name,) = tombinfo
            edit = [((s_layer.EDIT_NODEDATA_TOMB_DEL), (name,))]

        elif tombtype == s_layer.INDX_EDGE_VERB:
            (verb, n2nid) = tombinfo
            edit = [((s_layer.EDIT_EDGE_TOMB_DEL), (verb, n2nid))]

        if edit is not None:

            if runt is not None:
                meta = {
                    'user': runt.user.iden,
                    'time': s_common.now()
                }
                await self.saveNodeEdits([(nid, ndef[0], edit)], meta, bus=runt.bus)
                return

            meta = {
                'user': self.core.auth.rootuser,
                'time': s_common.now()
            }
            await self.saveNodeEdits([(nid, ndef[0], edit)], meta)

    async def scrapeIface(self, text, unique=False, refang=True):
        async with await s_spooled.Set.anit(dirn=self.core.dirn, cell=self.core) as matches:  # type: s_spooled.Set
            # The synapse.lib.scrape APIs handle form arguments for us.
            async for item in s_scrape.contextScrapeAsync(text, refang=refang, first=False):
                form = item.pop('form')
                valu = item.pop('valu')
                if unique:
                    key = (form, valu)
                    if key in matches:
                        await asyncio.sleep(0)
                        continue
                    await matches.add(key)

                try:
                    tobj = self.core.model.type(form)
                    valu, _ = tobj.norm(valu)
                except s_exc.BadTypeValu:
                    await asyncio.sleep(0)
                    continue

                # Yield a tuple of <form, normed valu, info>
                yield form, valu, item

            # Return early if the scrape interface is disabled
            if not self.core.stormiface_scrape:
                return

            # Scrape interface:
            #
            # The expected scrape interface takes a text and optional form
            # argument.
            #
            # The expected interface implementation returns a list/tuple of
            # (form, valu, info) results. Info is expected to contain the
            # match offset and raw valu.
            #
            # Scrape implementers are responsible for ensuring that their
            # resulting match and offsets are found in the text we sent
            # to them.
            todo = s_common.todo('scrape', text)
            async for results in self.callStormIface('scrape', todo):
                for (form, valu, info) in results:

                    if unique:
                        key = (form, valu)
                        if key in matches:
                            await asyncio.sleep(0)
                            continue
                        await matches.add(key)

                    try:
                        tobj = self.core.model.type(form)
                        valu, _ = tobj.norm(valu)
                    except AttributeError:  # pragma: no cover
                        logger.exception(f'Scrape interface yielded unknown form {form}')
                        await asyncio.sleep(0)
                        continue
                    except (s_exc.BadTypeValu):  # pragma: no cover
                        await asyncio.sleep(0)
                        continue

                    # Yield a tuple of <form, normed valu, info>
                    yield form, valu, info
                    await asyncio.sleep(0)

    async def getRuntPodes(self, prop, cmprvalu=None):
        liftfunc = self.core.getRuntLift(prop.form.name)
        if liftfunc is not None:
            async for pode in liftfunc(self, prop, cmprvalu=cmprvalu):
                yield pode

    async def _genSrefList(self, nid, smap, filtercmpr=None):
        srefs = []
        filt = True
        hasvalu = False

        for layr in self.layers:
            if (sref := smap.get(layr.iden)) is None:
                sref = layr.genStorNodeRef(nid)
                if filt:
                    if filtercmpr is not None and filtercmpr(sref.sode):
                        return
                    if sref.sode.get('antivalu') is not None:
                        return
            else:
                filt = False

            if not hasvalu:
                if sref.sode.get('valu') is not None:
                    hasvalu = True
                elif sref.sode.get('antivalu') is not None:
                    return

            srefs.append(sref)

        if hasvalu:
            return srefs

    async def _mergeLiftRows(self, genrs, filtercmpr=None, reverse=False):
        lastnid = None
        smap = {}
        async for indx, nid, sref in s_common.merggenr2(genrs, reverse=reverse):
            if not nid == lastnid or sref.layriden in smap:
                if lastnid is not None:
                    srefs = await self._genSrefList(lastnid, smap, filtercmpr)
                    if srefs is not None:
                        yield lastnid, srefs

                    smap.clear()

                lastnid = nid

            smap[sref.layriden] = sref

        if lastnid is not None:
            srefs = await self._genSrefList(lastnid, smap, filtercmpr)
            if srefs is not None:
                yield lastnid, srefs

    # view "lift by" functions yield (nid, srefs) tuples for results.
    async def liftByProp(self, form, prop, reverse=False, indx=None):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByProp(form, prop, reverse=reverse, indx=indx):
                yield nid, [sref]
            return

        def filt(sode):
            if (antiprops := sode.get('antiprops')) is not None and antiprops.get(prop):
                return True

            if (props := sode.get('props')) is None:
                return False

            return props.get(prop) is not None

        genrs = [layr.liftByProp(form, prop, reverse=reverse, indx=indx) for layr in self.layers]
        async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
            yield item

    async def liftByFormValu(self, form, cmprvals, reverse=False, virts=None):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByFormValu(form, cmprvals, reverse=reverse, virts=virts):
                yield nid, [sref]
            return

        for cval in cmprvals:
            genrs = [layr.liftByFormValu(form, (cval,), reverse=reverse, virts=virts) for layr in self.layers]
            async for item in self._mergeLiftRows(genrs, reverse=reverse):
                yield item

    async def liftByPropValu(self, form, prop, cmprvals, reverse=False, virts=None):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByPropValu(form, prop, cmprvals, reverse=reverse, virts=virts):
                yield nid, [sref]
            return

        def filt(sode):
            if (antiprops := sode.get('antiprops')) is not None and antiprops.get(prop):
                return True

            if (props := sode.get('props')) is None:
                return False

            return props.get(prop) is not None

        for cval in cmprvals:
            genrs = [layr.liftByPropValu(form, prop, (cval,), reverse=reverse, virts=virts) for layr in self.layers]
            async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
                yield item

    async def liftByTag(self, tag, form=None, reverse=False, indx=None):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByTag(tag, form=form, reverse=reverse, indx=indx):
                yield nid, [sref]
            return

        def filt(sode):
            if (antitags := sode.get('antitags')) is not None and antitags.get(tag):
                return True

            if (tags := sode.get('tags')) is None:
                return False

            return tags.get(tag) is not None

        genrs = [layr.liftByTag(tag, form=form, reverse=reverse, indx=indx) for layr in self.layers]
        async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
            yield item

    async def liftByTagValu(self, tag, cmprvals, form=None, reverse=False):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByTagValu(tag, cmprvals, form=form, reverse=reverse):
                yield nid, [sref]
            return

        def filt(sode):
            if (antitags := sode.get('antitags')) is not None and antitags.get(tag):
                return True

            if (tags := sode.get('tags')) is None:
                return False

            return tags.get(tag) is not None

        for cval in cmprvals:
            genrs = [layr.liftByTagValu(tag, (cval,), form=form, reverse=reverse) for layr in self.layers]
            async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
                yield item

    async def liftByTagProp(self, form, tag, prop, reverse=False, indx=None):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByTagProp(form, tag, prop, reverse=reverse, indx=indx):
                yield nid, [sref]
            return

        def filt(sode):
            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and antiprops.get(prop):
                    return True

            if (tagprops := sode.get('tagprops')) is None:
                return False

            if (props := tagprops.get(tag)) is None:
                return False

            return props.get(prop) is not None

        genrs = [layr.liftByTagProp(form, tag, prop, reverse=reverse, indx=indx) for layr in self.layers]
        async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
            yield item

    async def liftByTagPropValu(self, form, tag, prop, cmprvals, reverse=False):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByTagPropValu(form, tag, prop, cmprvals, reverse=reverse):
                yield nid, [sref]
            return

        def filt(sode):
            if (antitags := sode.get('antitagprops')) is not None:
                if (antiprops := antitags.get(tag)) is not None and antiprops[prop]:
                    return True

            if (tagprops := sode.get('tagprops')) is None:
                return False

            if (props := tagprops.get(tag)) is None:
                return False

            return props.get(prop) is not None

        for cval in cmprvals:
            genrs = [layr.liftByTagPropValu(form, tag, prop, (cval,), reverse=reverse) for layr in self.layers]
            async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
                yield item

    async def liftByPropArray(self, form, prop, cmprvals, reverse=False):

        if len(self.layers) == 1:
            async for _, nid, sref in self.wlyr.liftByPropArray(form, prop, cmprvals, reverse=reverse):
                yield nid, [sref]
            return

        if prop is None:
            filt = None
        else:
            def filt(sode):
                if (antiprops := sode.get('antiprops')) is not None and antiprops.get(prop):
                    return True

                if (props := sode.get('props')) is None:
                    return False

                return props.get(prop) is not None

        for cval in cmprvals:
            genrs = [layr.liftByPropArray(form, prop, (cval,), reverse=reverse) for layr in self.layers]
            async for item in self._mergeLiftRows(genrs, filtercmpr=filt, reverse=reverse):
                yield item

    async def liftByDataName(self, name):

        if len(self.layers) == 1:
            async for nid, sref, tomb in self.wlyr.liftByDataName(name):
                if not tomb:
                    yield nid, [sref]
            return

        genrs = [layr.liftByDataName(name) for layr in self.layers]

        lastnid = None
        smap = {}

        async for nid, sref, tomb in s_common.merggenr2(genrs, cmprkey=lambda x: x[0]):
            if not nid == lastnid or sref.layriden in smap:
                if lastnid is not None and not istomb:
                    srefs = await self._genSrefList(lastnid, smap)
                    if srefs is not None:
                        yield lastnid, srefs

                lastnid = nid
                istomb = tomb

            smap[sref.layriden] = sref

        if lastnid is not None and not istomb:
            srefs = await self._genSrefList(lastnid, smap)
            if srefs is not None:
                yield lastnid, srefs

    async def nodesByDataName(self, name):
        async for nid, srefs in self.liftByDataName(name):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByProp(self, full, reverse=False, subtype=None):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isrunt:
            async for node in self.getRuntNodes(prop):
                yield node
            return

        indx = None
        if subtype is not None:
            indx = prop.type.getSubIndx(subtype)

        if prop.isform:
            genr = self.liftByProp(prop.name, None, reverse=reverse, indx=indx)

        elif prop.isuniv:
            genr = self.liftByProp(None, prop.name, reverse=reverse, indx=indx)

        else:
            genr = self.liftByProp(prop.form.name, prop.name, reverse=reverse, indx=indx)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByPropValu(self, full, cmpr, valu, reverse=False, virts=None):

        if cmpr == 'type=':
            if reverse:
                async for node in self.nodesByPropTypeValu(full, valu, reverse=reverse):
                    yield node

                async for node in self.nodesByPropValu(full, '=', valu, reverse=reverse, virts=virts):
                    yield node
            else:
                async for node in self.nodesByPropValu(full, '=', valu, reverse=reverse, virts=virts):
                    yield node

                async for node in self.nodesByPropTypeValu(full, valu, reverse=reverse):
                    yield node
            return

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu, virts=virts)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        if prop.isrunt:
            for storcmpr, storvalu, _ in cmprvals:
                async for node in self.getRuntNodes(prop, cmprvalu=(storcmpr, storvalu)):
                    yield node
            return

        if prop.isform:
            genr = self.liftByFormValu(prop.name, cmprvals, reverse=reverse, virts=virts)

        elif prop.isuniv:
            genr = self.liftByPropValu(None, prop.name, cmprvals, reverse=reverse, virts=virts)

        else:
            genr = self.liftByPropValu(prop.form.name, prop.name, cmprvals, reverse=reverse, virts=virts)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTag(self, tag, form=None, reverse=False, subtype=None):

        indx = None
        if subtype is not None:
            indx = self.core.model.type('ival').getTagSubIndx(subtype)

        async for nid, srefs in self.liftByTag(tag, form=form, reverse=reverse, indx=indx):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagValu(self, tag, cmpr, valu, form=None, reverse=False):

        cmprvals = self.core.model.type('ival').getStorCmprs(cmpr, valu)
        async for nid, srefs in self.liftByTagValu(tag, cmprvals, form, reverse=reverse):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByPropTypeValu(self, name, valu, reverse=False):

        _type = self.core.model.types.get(name)
        if _type is None:
            raise s_exc.NoSuchType(name=name)

        for prop in self.core.model.getPropsByType(name):
            async for node in self.nodesByPropValu(prop.full, '=', valu, reverse=reverse):
                yield node

        for prop in self.core.model.getArrayPropsByType(name):
            async for node in self.nodesByPropArray(prop.full, '=', valu, reverse=reverse):
                yield node

    async def nodesByPropArray(self, full, cmpr, valu, reverse=False):

        prop = self.core.model.prop(full)
        if prop is None:
            mesg = f'No property named "{full}".'
            raise s_exc.NoSuchProp(mesg=mesg)

        if not isinstance(prop.type, s_types.Array):
            mesg = f'Array syntax is invalid on non array type: {prop.type.name}.'
            raise s_exc.BadTypeValu(mesg=mesg)

        cmprvals = prop.type.arraytype.getStorCmprs(cmpr, valu)

        if prop.isform:
            genr = self.liftByPropArray(prop.name, None, cmprvals, reverse=reverse)

        else:
            formname = None
            if prop.form is not None:
                formname = prop.form.name

            genr = self.liftByPropArray(formname, prop.name, cmprvals, reverse=reverse)

        async for nid, srefs in genr:
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagProp(self, form, tag, name, reverse=False, subtype=None):
        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        indx = None
        if subtype is not None:
            indx = prop.type.getSubIndx(subtype)

        async for nid, srefs in self.liftByTagProp(form, tag, name, reverse=reverse, indx=indx):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def nodesByTagPropValu(self, form, tag, name, cmpr, valu, reverse=False):

        prop = self.core.model.getTagProp(name)
        if prop is None:
            mesg = f'No tag property named {name}'
            raise s_exc.NoSuchTagProp(name=name, mesg=mesg)

        cmprvals = prop.type.getStorCmprs(cmpr, valu)
        # an empty return probably means ?= with invalid value
        if not cmprvals:
            return

        async for nid, srefs in self.liftByTagPropValu(form, tag, name, cmprvals, reverse=reverse):
            node = await self._joinSodes(nid, srefs)
            if node is not None:
                yield node

    async def getRuntNodes(self, prop, cmprvalu=None):

        now = s_common.now()

        filt = None
        if cmprvalu is not None:

            cmpr, valu = cmprvalu

            ctor = prop.type.getCmprCtor(cmpr)
            if ctor is None:
                mesg = f'Bad comparison ({cmpr}) for type {prop.type.name}.'
                raise s_exc.BadCmprType(mesg=mesg, cmpr=cmpr)

            filt = ctor(valu)
            if filt is None:
                mesg = f'Bad value ({valu}) for comparison {cmpr} {prop.type.name}.'
                raise s_exc.BadCmprValu(mesg=mesg, cmpr=cmpr)

        async for pode in self.getRuntPodes(prop, cmprvalu=cmprvalu):

            # for runt nodes without a .created time
            pode[1]['props'].setdefault('.created', now)

            # filter based on any specified prop / cmpr / valu
            if filt is None:
                if not prop.isform:
                    pval = pode[1]['props'].get(prop.name, s_common.novalu)
                    if pval == s_common.novalu:
                        await asyncio.sleep(0)
                        continue
            else:

                if prop.isform:
                    nval = pode[0][1]
                else:
                    nval = pode[1]['props'].get(prop.name, s_common.novalu)

                if nval is s_common.novalu or not filt(nval):
                    await asyncio.sleep(0)
                    continue

            yield s_node.RuntNode(self, pode)
