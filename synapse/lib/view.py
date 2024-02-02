import shutil
import asyncio
import hashlib
import logging
import itertools
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.snap as s_snap
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
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
        layriden = view.layers[0].iden
        self.allowedits = user.allowed(('node',), gateiden=layriden)

    async def storNodeEdits(self, edits, meta):

        if not self.allowedits:
            mesg = 'storNodeEdits() not allowed without node permission on layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        if meta is None:
            meta = {}

        meta['time'] = s_common.now()
        meta['user'] = self.user.iden

        return await self.view.storNodeEdits(edits, meta)

    async def syncNodeEdits2(self, offs, wait=True):
        await self._reqUserAllowed(('view', 'read'))
        # present a layer compatible API to remote callers
        layr = self.view.layers[0]
        async for item in layr.syncNodeEdits2(offs, wait=wait):
            yield item

    @s_cell.adminapi()
    async def saveNodeEdits(self, edits, meta):
        meta['link:user'] = self.user.iden
        async with await self.view.snap(user=self.user) as snap:
            return await snap.saveNodeEdits(edits, meta)

    async def getEditSize(self):
        await self._reqUserAllowed(('view', 'read'))
        return await self.view.layers[0].getEditSize()

    async def getCellIden(self):
        return self.view.iden

class View(s_nexus.Pusher):  # type: ignore
    '''
    A view represents a cortex as seen from a specific set of layers.

    The view class is used to implement Copy-On-Write layers as well as
    interact with a subset of the layers configured in a Cortex.
    '''
    snapctor = s_snap.Snap.anit

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

        self.trigtask = None
        await self.initTrigTask()

        self.mergetask = None

    def reqParentQuorum(self):

        if self.parent is None:
            mesg = f'View ({self.iden}) has no parent.'
            raise s_exc.BadState(mesg=mesg)

        quorum = self.parent.info.get('quorum')
        if quorum is None:
            mesg = f'Parent view of ({self.iden}) does not require quorum voting.'
            raise s_exc.BadState(mesg=mesg)

        if self.parent.layers[0].readonly:
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

        if self.hasKids():
            mesg = 'Cannot add a merge request to a view with children.'
            raise s_exc.BadState(mesg=mesg)

        s_schemas.reqValidMerge(mergeinfo)
        lkey = self.bidn + b'merge:req'
        self.core.slab.put(lkey, s_msgpack.en(mergeinfo), db='view:meta')
        await self.core.feedBeholder('view:merge:request:set', {'view': self.iden, 'merge': mergeinfo})
        return mergeinfo

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

        layr = self.layers[0]

        layr.readonly = True
        await layr.layrinfo.set('readonly', True)

        merge = self.getMergeRequest()
        merge['votes'] = [vote async for vote in self.getMergeVotes()]
        merge['merged'] = tick

        tick = s_common.int64en(tick)
        bidn = s_common.uhex(merge.get('iden'))

        lkey = self.parent.bidn + b'hist:merge:iden' + bidn
        self.core.slab.put(lkey, s_msgpack.en(merge), db='view:meta')

        lkey = self.parent.bidn + b'hist:merge:time' + tick + bidn
        self.core.slab.put(lkey, bidn, db='view:meta')

        await self.core.feedBeholder('view:merge:init', {'view': self.iden})

        await self.initMergeTask()

    async def setMergeVote(self, vote):
        self.reqParentQuorum()
        vote['created'] = s_common.now()
        vote['offset'] = await self.layers[0].getEditIndx()
        return await self._push('merge:vote:set', vote)

    @s_nexus.Pusher.onPush('merge:vote:set')
    async def _setMergeVote(self, vote):

        self.reqParentQuorum()
        s_schemas.reqValidVote(vote)

        uidn = s_common.uhex(vote.get('user'))

        self.core.slab.put(self.bidn + b'merge:vote' + uidn, s_msgpack.en(vote), db='view:meta')

        await self.core.feedBeholder('view:merge:vote:set', {'view': self.iden, 'vote': vote})

        tick = vote.get('created')
        await self.tryToMerge(tick)

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
            await self.layers[0]._saveDirtySodes()

            merge = self.getMergeRequest()

            # merge edits as the merge request user
            meta = {
                'user': merge.get('creator'),
                'merge': merge.get('iden'),
            }

            async def chunked():
                nodeedits = []

                async for nodeedit in self.layers[0].iterLayerNodeEdits():

                    nodeedits.append(nodeedit)

                    if len(nodeedits) == 10:
                        yield nodeedits
                        nodeedits.clear()

                if nodeedits:
                    yield nodeedits

            total = self.layers[0].getStorNodeCount()

            count = 0
            nextprog = 1000

            await self.core.feedBeholder('view:merge:prog', {'view': self.iden, 'count': count, 'total': total})

            async with await self.parent.snap(user=self.core.auth.rootuser) as snap:

                async for edits in chunked():

                    meta['time'] = s_common.now()

                    await snap.saveNodeEdits(edits, meta)
                    await asyncio.sleep(0)

                    count += len(edits)

                    if count >= nextprog:
                        await self.core.feedBeholder('view:merge:prog', {'view': self.iden, 'count': count, 'total': total})
                        nextprog += 1000

            await self.core.feedBeholder('view:merge:fini', {'view': self.iden})

            # remove the view and top layer
            await self.core.delView(self.iden)
            await self.core.delLayer(self.layers[0].iden)

        except Exception as e: # pragma: no cover
            logger.exception(f'Error while merging view: {self.iden}')

    async def isMergeReady(self):
        # count the current votes and potentially trigger a merge

        offset = await self.layers[0].getEditIndx()

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
                                     gates=[self.iden, self.layers[0].iden])

    async def mergeStormIface(self, name, todo):
        '''
        Allow an interface which specifies a generator use case to yield
        (priority, value) tuples and merge results from multiple generators
        yielded in ascending priority order.
        '''
        root = self.core.auth.rootuser
        funcname, funcargs, funckwargs = todo

        genrs = []
        async with await self.snap(user=root) as snap:

            for moddef in await self.core.getStormIfaces(name):
                try:
                    query = await self.core.getStormQuery(moddef.get('storm'))
                    modconf = moddef.get('modconf', {})
                    runt = await snap.addStormRuntime(query, opts={'vars': {'modconf': modconf}}, user=root)

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

    async def callStormIface(self, name, todo):

        root = self.core.auth.rootuser
        funcname, funcargs, funckwargs = todo

        async with await self.snap(user=root) as snap:

            for moddef in await self.core.getStormIfaces(name):
                try:
                    query = await self.core.getStormQuery(moddef.get('storm'))

                    modconf = moddef.get('modconf', {})

                    # TODO look at caching the function returned as presume a persistant runtime?
                    async with snap.getStormRuntime(query, opts={'vars': {'modconf': modconf}}, user=root) as runt:

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

                buid = triginfo.get('buid')
                varz = triginfo.get('vars')
                trigiden = triginfo.get('trig')

                try:
                    trig = self.triggers.get(trigiden)
                    if trig is None:
                        continue

                    async with await self.snap(trig.user) as snap:
                        node = await snap.getNodeByBuid(buid)
                        if node is None:
                            continue

                        await trig._execute(node, vars=varz)

                except asyncio.CancelledError:  # pragma: no cover
                    raise

                except Exception as e:  # pragma: no cover
                    logger.exception(f'trigQueueLoop() on trigger: {trigiden} view: {self.iden}')

                finally:
                    await self.delTrigQueue(offs)

    async def getStorNodes(self, buid):
        '''
        Return a list of storage nodes for the given buid in layer order.
        '''
        return await self.core._getStorNodes(buid, self.layers)

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
            layers.append(view.layers[0])
            view = view.parent

        # Add all of the bottom view's layers.
        layers.extend(view.layers)

        self.layers = layers
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

    async def getEdgeVerbs(self):

        async with await s_spooled.Set.anit(dirn=self.core.dirn, cell=self.core) as vset:

            for layr in self.layers:

                async for verb in layr.getEdgeVerbs():

                    await asyncio.sleep(0)

                    if verb in vset:
                        continue

                    await vset.add(verb)
                    yield verb

    async def getEdges(self, verb=None):

        async with await s_spooled.Set.anit(dirn=self.core.dirn, cell=self.core) as eset:

            for layr in self.layers:

                async for edge in layr.getEdges(verb=verb):

                    await asyncio.sleep(0)

                    if edge in eset:
                        continue

                    await eset.add(edge)
                    yield edge

    async def _initViewLayers(self):

        for iden in self.info.get('layers'):

            layr = self.core.layers.get(iden)

            if layr is None:
                self.invalid = iden
                logger.warning('view %r has missing layer %r' % (self.iden, iden))
                continue

            self.layers.append(layr)

    async def eval(self, text, opts=None, log_info=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        if log_info is None:
            log_info = {}

        log_info['mode'] = opts.get('mode', 'storm')
        log_info['view'] = self.iden

        self.core._logStormQuery(text, user, info=log_info)

        taskiden = opts.get('task')
        taskinfo = {'query': text, 'view': self.iden}

        with s_scope.enter({'user': user}):

            await self.core.boss.promote('storm', user=user, info=taskinfo, taskiden=taskiden)

            async with await self.snap(user=user) as snap:
                async for node in snap.eval(text, opts=opts, user=user):
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
                # runtime in the snap, so catch and pass the `err` message
                await self.core.getStormQuery(text, mode=mode)

                shownode = (not show or 'node' in show)

                with s_scope.enter({'user': user}):

                    async with await self.snap(user=user) as snap:

                        if keepalive:
                            snap.schedCoro(snap.keepalive(keepalive))

                        if not show:
                            snap.link(chan.put)

                        else:
                            [snap.on(n, chan.put) for n in show]

                        if shownode:
                            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                                await chan.put(('node', pode))
                                count += 1

                        else:
                            self.core._logStormQuery(text, user,
                                                     info={'mode': opts.get('mode', 'storm'), 'view': self.iden})
                            async for item in snap.storm(text, opts=opts, user=user):
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

        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        taskinfo = {'query': text, 'view': self.iden}
        taskiden = opts.get('task')
        await self.core.boss.promote('storm', user=user, info=taskinfo, taskiden=taskiden)

        with s_scope.enter({'user': user}):
            async with await self.snap(user=user) as snap:
                async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                    yield pode

    async def snap(self, user):

        if self.invalid is not None:
            raise s_exc.NoSuchLayer(mesg=f'No such layer {self.invalid}', iden=self.invalid)

        return await self.snapctor(self, user)

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
        if name not in ('name', 'desc', 'parent', 'nomerge', 'quorum'):
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

            if parent.getMergeRequest() is not None:
                mesg = 'You may not set the parent to a view with a pending merge request.'
                raise s_exc.BadState(mesg=mesg)

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

                # convert layers to a list of idens...
                lids = [layr.iden for layr in layers]
                await child.info.set('layers', lids)

                await self.core.feedBeholder('view:setlayers', {'iden': child.iden, 'layers': lids}, gates=[child.iden, lids[0]])

                todo.append(child)

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

        if self.getMergeRequest() is not None:
            mesg = 'Cannot fork a view which has a merge request.'
            raise s_exc.BadState(mesg=mesg)

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
        fromlayr = self.layers[0]

        if useriden is None:
            user = await self.core.auth.getUserByName('root')
        else:
            user = await self.core.auth.reqUser(useriden)

        await self.mergeAllowed(user, force=force)

        taskinfo = {'merging': self.iden, 'view': self.iden}
        await self.core.boss.promote('storm', user=user, info=taskinfo)

        async with await self.parent.snap(user=user) as snap:

            meta = await snap.getSnapMeta()
            async for nodeedits in fromlayr.iterLayerNodeEdits():
                await self.parent.storNodeEdits([nodeedits], meta)

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

        async with await self.snap(user=user) as snap:
            meta = await snap.getSnapMeta()
            async for nodeedit in self.layers[0].iterWipeNodeEdits():
                await snap.getNodeByBuid(nodeedit[0])  # to load into livenodes for callbacks
                await snap.saveNodeEdits([nodeedit], meta)

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
        fromlayr = self.layers[0]
        if self.parent is None:
            raise s_exc.CantMergeView(mesg=f'Cannot merge view ({self.iden}) that has not been forked.')

        if self.info.get('nomerge'):
            raise s_exc.CantMergeView(mesg=f'Cannot merge view ({self.iden}) that has nomerge set.')

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

        async with await self.parent.snap(user=user) as snap:
            async for nodeedit in fromlayr.iterLayerNodeEdits():
                for offs, perm in s_layer.getNodeEditPerms([nodeedit]):
                    self.parent._confirm(user, perm)
                    await asyncio.sleep(0)

    async def wipeAllowed(self, user=None):
        '''
        Check whether a user can wipe the write layer in the current view.
        '''
        if user is None or user.isAdmin():
            return

        async for nodeedit in self.layers[0].iterWipeNodeEdits():
            for offs, perm in s_layer.getNodeEditPerms([nodeedit]):
                self._confirm(user, perm)
                await asyncio.sleep(0)

    async def runTagAdd(self, node, tag, valu, view=None):

        # Run the non-glob callbacks, then the glob callbacks
        funcs = itertools.chain(self.core.ontagadds.get(tag, ()), (x[1] for x in self.core.ontagaddglobs.get(tag)))
        for func in funcs:
            try:
                await s_coro.ornot(func, node, tag, valu)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception:
                logger.exception('onTagAdd Error')

        if view is None:
            view = self.iden

        # Run any trigger handlers
        await self.triggers.runTagAdd(node, tag, view=view)

    async def runTagDel(self, node, tag, valu, view=None):

        funcs = itertools.chain(self.core.ontagdels.get(tag, ()), (x[1] for x in self.core.ontagdelglobs.get(tag)))
        for func in funcs:
            try:
                await s_coro.ornot(func, node, tag, valu)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception:
                logger.exception('onTagDel Error')

        if view is None:
            view = self.iden

        await self.triggers.runTagDel(node, tag, view=view)

    async def runNodeAdd(self, node, view=None):
        if not node.snap.trigson:
            return

        if view is None:
            view = self.iden

        await self.triggers.runNodeAdd(node, view=view)

    async def runNodeDel(self, node, view=None):
        if not node.snap.trigson:
            return

        if view is None:
            view = self.iden

        await self.triggers.runNodeDel(node, view=view)

    async def runPropSet(self, node, prop, oldv, view=None):
        '''
        Handle when a prop set trigger event fired
        '''
        if not node.snap.trigson:
            return

        if view is None:
            view = self.iden

        await self.triggers.runPropSet(node, prop, oldv, view=view)

    async def runEdgeAdd(self, n1, edge, n2, view=None):
        if not n1.snap.trigson:
            return

        if view is None:
            view = self.iden

        await self.triggers.runEdgeAdd(n1, edge, n2, view=view)

    async def runEdgeDel(self, n1, edge, n2, view=None):
        if not n1.snap.trigson:
            return

        if view is None:
            view = self.iden

        await self.triggers.runEdgeDel(n1, edge, n2, view=view)

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

    async def addNode(self, form, valu, props=None, user=None):
        async with await self.snap(user=user) as snap:
            return await snap.addNode(form, valu, props=props)

    async def addNodeEdits(self, edits, meta):
        '''
        A telepath compatible way to apply node edits to a view.

        NOTE: This does cause trigger execution.
        '''
        user = await self.core.auth.reqUser(meta.get('user'))
        async with await self.snap(user=user) as snap:
            # go with the anti-pattern for now...
            await snap.saveNodeEdits(edits, None)

    async def storNodeEdits(self, edits, meta):
        return await self.addNodeEdits(edits, meta)
        # TODO remove addNodeEdits?

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
