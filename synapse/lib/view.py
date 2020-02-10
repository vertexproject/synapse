import asyncio
import logging
import itertools
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.snap as s_snap
import synapse.lib.nexus as s_nexus
import synapse.lib.trigger as s_trigger

logger = logging.getLogger(__name__)

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
        self.info = await node.dict()

        trignode = await node.open(('triggers',))
        self.trigdict = await trignode.dict()

        self.triggers = s_trigger.Triggers(self)
        for iden, tdef in self.trigdict.items():
            try:
                self.triggers.load(tdef)

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.exception(f'Failed to load trigger {tdef!r}')

        self.core = core

        #await self.core.auth.addAuthGate(self.iden, 'view')
        await s_nexus.Pusher.__anit__(self, iden=self.iden, nexsroot=core.nexsroot)

        self.layers = []
        self.invalid = None
        self.parent = None  # The view this view was forked from

        parent = self.info.get('parent')
        if parent is not None:
            self.parent = self.core.getView(parent)

        self.permCheck = {
            'node:add': self._nodeAddConfirm,
            'node:del': self._nodeDelConfirm,
            'prop:set': self._propSetConfirm,
            'prop:del': self._propDelConfirm,
            'tag:add': self._tagAddConfirm,
            'tag:del': self._tagDelConfirm,
            'tag:prop:set': self._tagPropSetConfirm,
            'tag:prop:del': self._tagPropDelConfirm,
        }

        # isolate some initialization to easily override for SpawnView.
        await self._initViewLayers()

    def pack(self):
        d = {'iden': self.iden}
        d.update(self.info.pack())
        return d

    async def getFormCounts(self):
        counts = collections.defaultdict(int)
        for layr in self.layers:
            for name, valu in (await layr.getFormCounts()).items():
                counts[name] += valu
        return counts

    async def _initViewLayers(self):

        for iden in self.info.get('layers'):

            layr = self.core.layers.get(iden)

            if layr is None:
                self.invalid = iden
                logger.warning('view %r has missing layer %r' % (self.iden, iden))
                continue

            self.layers.append(layr)

    async def eval(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        if user is None:
            user = await self.core.auth.getUserByName('root')

        info = {'query': text}
        if opts is not None:
            info['opts'] = opts

        await self.core.boss.promote('storm', user=user, info=info)

        async with await self.snap(user=user) as snap:
            async for node in snap.eval(text, opts=opts, user=user):
                yield node

    async def storm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield (node, path) tuples.

        Yields:
            (Node, Path) tuples
        '''
        if user is None:
            user = await self.core.auth.getUserByName('root')

        info = {'query': text}
        if opts is not None:
            info['opts'] = opts

        await self.core.boss.promote('storm', user=user, info=info)

        async with await self.snap(user=user) as snap:
            async for mesg in snap.storm(text, opts=opts, user=user):
                yield mesg

    async def nodes(self, text, opts=None, user=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        return [n async for n in self.eval(text, opts=opts, user=user)]

    async def streamstorm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            ((str,dict)): Storm messages.
        '''
        info = {'query': text}
        if opts is not None:
            info['opts'] = opts

        if opts is None:
            opts = {}

        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE, loop=self.loop)

        if user is None:
            user = await self.core.auth.getUserByName('root')

        synt = await self.core.boss.promote('storm', user=user, info=info)

        show = opts.get('show')

        async def runStorm():
            cancelled = False
            tick = s_common.now()
            count = 0
            try:
                # First, try text parsing. If this fails, we won't be able to get
                # a storm runtime in the snap, so catch and pass the `err` message
                # before handing a `fini` message along.
                self.core.getStormQuery(text)

                await chan.put(('init', {'tick': tick, 'text': text, 'task': synt.iden}))

                shownode = (show is None or 'node' in show)
                async with await self.snap(user=user) as snap:

                    if show is None:
                        snap.link(chan.put)

                    else:
                        [snap.on(n, chan.put) for n in show]

                    if shownode:
                        async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                            await chan.put(('node', pode))
                            count += 1

                    else:
                        async for item in snap.storm(text, opts=opts, user=user):
                            count += 1

            except asyncio.CancelledError:
                logger.warning('Storm runtime cancelled.')
                cancelled = True
                raise

            except Exception as e:
                logger.exception(f'Error during storm execution for {{ {text} }}')
                enfo = s_common.err(e)
                enfo[1].pop('esrc', None)
                enfo[1].pop('ename', None)
                await chan.put(('err', enfo))

            finally:
                if cancelled:
                    return
                tock = s_common.now()
                took = tock - tick
                await chan.put(('fini', {'tock': tock, 'took': took, 'count': count}))

        await synt.worker(runStorm())

        while True:

            mesg = await chan.get()

            yield mesg

            if mesg[0] == 'fini':
                break

    async def iterStormPodes(self, text, opts=None, user=None):
        if user is None:
            user = await self.core.auth.getUserByName('root')

        info = {'query': text}
        if opts is not None:
            info['opts'] = opts

        await self.core.boss.promote('storm', user=user, info=info)

        async with await self.snap(user=user) as snap:
            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                yield pode

    async def snap(self, user):

        if self.invalid is not None:
            raise s_exc.NoSuchLayer(iden=self.invalid)

        return await self.snapctor(self, user)

    def pack(self):
        return {
            'iden': self.iden,
            'owner': self.info.get('owner'),
            'layers': self.info.get('layers'),
        }

    @s_nexus.Pusher.onPushAuto('view:addlayer')
    async def addLayer(self, layriden, indx=None):

        for view in self.core.views.values():
            if view.parent is self:
                raise s_exc.ReadOnlyLayer(mesg='May not change layers that have been forked from')

        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of forked view')

        layr = self.core.layers.get(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        if indx is None:
            self.layers.append(layr)
        else:
            self.layers.insert(indx, layr)

        await self.info.set('layers', [l.iden for l in self.layers])

    @s_nexus.Pusher.onPushAuto('view:setlayers')
    async def setLayers(self, layers):
        '''
        Set the view layers from a list of idens.
        NOTE: view layers are stored "top down" (the write layer is self.layers[0])
        '''
        for view in self.core.views.values():
            if view.parent is self:
                raise s_exc.ReadOnlyLayer(mesg='May not change layers that have been forked from')

        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of forked view')

        layrs = []

        for iden in layers:
            layr = self.core.layers.get(iden)
            if layr is None:
                raise s_exc.NoSuchLayer(iden=iden)
            if not layrs and layr.readonly:
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {layr.iden} must not be read-only')

            layrs.append(layr)

        self.invalid = None
        self.layers = layrs

        await self.info.set('layers', layers)

    async def fork(self, ldef=None, vdef=None):
        '''
        Make a new view inheriting from this view with the same layers and a new write layer on top

        Args:
            Passed through to cortex.addLayer

        Returns:
            new view object, with an iden the same as the new write layer iden
        '''
        if ldef is None:
            ldef = {}

        if vdef is None:
            vdef = {}

        layr = await self.core.addLayer(ldef)

        vdef['parent'] = self.iden
        vdef['layers'] = [layr.iden] + [l.iden for l in self.layers]

        return await self.core.addView(vdef)

    async def merge(self, user=None):
        '''
        Merge this view into its parent.  All changes made to this view will be applied to the parent.

        When complete, delete this view.
        '''
        fromlayr = self.layers[0]
        if self.parent is None:
            raise s_exc.SynErr('Cannot merge a view than has not been forked')

        if self.parent.layers[0].readonly:
            raise s_exc.ReadOnlyLayer(mesg="May not merge if the parent's write layer is read-only")

        for view in self.core.views.values():
            if view.parent is not None and view.parent == self:
                raise s_exc.SynErr(mesg='Cannot merge a view that has children itself')

        CHUNKSIZE = 1000
        fromoff = 0

        if user is None:
            user = await self.core.auth.getUserByName('root')

        await self.core.boss.promote('storm', user=user, info={'merging': self.iden})
        async with await self.parent.snap(user=user) as snap:
            snap.disableTriggers()
            snap.strict = False
            with snap.getStormRuntime(user=user) as runt:
                while True:
                    splicechunk = [x async for x in fromlayr.splices(fromoff, CHUNKSIZE)]

                    await snap.addFeedData('syn.splice', splicechunk)

                    if len(splicechunk) < CHUNKSIZE:
                        break

                    fromoff += CHUNKSIZE
                    await asyncio.sleep(0)

        await self.core.delView(self.iden)

    # FIXME:  all these should be refactored and call runt.confirmLayer
    def _confirm(self, user, parentlayr, perms):
        if not parentlayr.allowed(user, perms):
            perm = '.'.join(perms)
            mesg = f'User must have permission {perm} on write layer'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=user.name)

    async def _nodeAddConfirm(self, user, snap, parentlayr, splice):
        perms = ('node:add', splice['ndef'][0])
        self._confirm(user, parentlayr, perms)

    async def _nodeDelConfirm(self, user, snap, parentlayr, splice):
        buid = s_common.buid(splice['ndef'])
        node = await snap.getNodeByBuid(buid)

        if node is not None:
            for tag in node.tags.keys():
                perms = ('tag:del', *tag.split('.'))
                self._confirm(user, parentlayr, perms)

            perms = ('node:del', splice['ndef'][0])
            self._confirm(user, parentlayr, perms)

    async def _propSetConfirm(self, user, snap, parentlayr, splice):
        ndef = splice.get('ndef')
        prop = splice.get('prop')

        perms = ('prop:set', ':'.join([ndef[0], prop]))
        self._confirm(user, parentlayr, perms)

    async def _propDelConfirm(self, user, snap, parentlayr, splice):
        ndef = splice.get('ndef')
        prop = splice.get('prop')

        perms = ('prop:del', ':'.join([ndef[0], prop]))
        self._confirm(user, parentlayr, perms)

    async def _tagAddConfirm(self, user, snap, parentlayr, splice):
        tag = splice.get('tag')
        perms = ('tag:add', *tag.split('.'))
        self._confirm(user, parentlayr, perms)

    async def _tagDelConfirm(self, user, snap, parentlayr, splice):
        tag = splice.get('tag')
        perms = ('tag:del', *tag.split('.'))
        self._confirm(user, parentlayr, perms)

    async def _tagPropSetConfirm(self, user, snap, parentlayr, splice):
        tag = splice.get('tag')
        perms = ('tag:add', *tag.split('.'))
        self._confirm(user, parentlayr, perms)

    async def _tagPropDelConfirm(self, user, snap, parentlayr, splice):
        tag = splice.get('tag')
        perms = ('tag:del', *tag.split('.'))
        self._confirm(user, parentlayr, perms)

    async def mergeAllowed(self, user=None):
        '''
        Check whether a user can merge a view into its parent.
        '''
        fromlayr = self.layers[0]
        if self.parent is None:
            raise s_exc.SynErr('Cannot merge a view than has not been forked')

        parentlayr = self.parent.layers[0]
        if parentlayr.readonly:
            raise s_exc.ReadOnlyLayer(mesg="May not merge if the parent's write layer is read-only")

        for view in self.core.views.values():
            if view.parent is not None and view.parent == self:
                raise s_exc.SynErr(mesg='Cannot merge a view that has children itself')

        if user is None or user.isAdmin():
            return True

        CHUNKSIZE = 1000
        fromoff = 0

        async with await self.parent.snap(user=user) as snap:
            while True:

                splicecount = 0
                async for splice in fromlayr.splices(fromoff, CHUNKSIZE):
                    # FIXME: this sucks; we shouldn't dupe layer perm checking here
                    check = self.permCheck.get(splice[0])
                    if check is None:
                        raise s_exc.SynErr(mesg='Unknown splice type, cannot safely merge',
                                           splicetype=splice[0])

                    await check(user, snap, parentlayr, splice[1])

                    splicecount += 1

                if splicecount < CHUNKSIZE:
                    break

                fromoff += CHUNKSIZE
                await asyncio.sleep(0)

    async def runTagAdd(self, node, tag, valu):

        # Run the non-glob callbacks, then the glob callbacks
        funcs = itertools.chain(self.core.ontagadds.get(tag, ()), (x[1] for x in self.core.ontagaddglobs.get(tag)))
        for func in funcs:
            try:
                await s_coro.ornot(func, node, tag, valu)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('onTagAdd Error')

        # Run any trigger handlers
        await self.triggers.runTagAdd(node, tag)

    async def runTagSet(self, node, tag, valu, oldv):
        await self.triggers.runTagSet(node, tag, oldv)

    async def runTagDel(self, node, tag, valu):

        funcs = itertools.chain(self.core.ontagdels.get(tag, ()), (x[1] for x in self.core.ontagdelglobs.get(tag)))
        for func in funcs:
            try:
                await s_coro.ornot(func, node, tag, valu)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('onTagDel Error')

        await self.triggers.runTagDel(node, tag)

    async def runNodeAdd(self, node):
        if not node.snap.trigson:
            return

        await self.triggers.runNodeAdd(node)

        if self.parent is not None:
            await self.parent.runNodeAdd(node)

    async def runNodeDel(self, node):
        if not node.snap.trigson:
            return

        await self.triggers.runNodeDel(node)

        if self.parent is not None:
            await self.parent.runNodeDel(node)

    async def runPropSet(self, node, prop, oldv):
        '''
        Handle when a prop set trigger event fired
        '''
        if not node.snap.trigson:
            return

        await self.triggers.runPropSet(node, prop, oldv)

        if self.parent is not None:
            await self.parent.runPropSet(node, prop, oldv)

    async def addTrigger(self, tdef):
        '''
        Adds a trigger to the view.
        '''
        tdef['iden'] = s_common.guid()

        tdef = await self._push('trigger:add', tdef)
        user = self.core.auth.user(tdef.get('user'))

        await user.setAdmin(True, gateiden=tdef.get('iden'))

        return tdef

    @s_nexus.Pusher.onPush('trigger:add')
    async def _onPushAddTrigger(self, tdef):

        root = await self.core.auth.getUserByName('root')

        tdef.setdefault('user', root.iden)
        tdef.setdefault('enabled', True)

        self.core.getStormQuery(tdef.get('storm'))

        trig = self.triggers.load(tdef)
        await self.trigdict.set(trig.iden, tdef)
        await self.core.auth.addAuthGate(trig.iden, 'trigger')

        return trig.pack()

    async def getTrigger(self, iden):
        return await self.triggers.get(iden)

    @s_nexus.Pusher.onPushAuto('trigger:del')
    async def delTrigger(self, iden):
        '''
        Delete a trigger from the view.
        '''
        trig = self.triggers.pop(iden)
        await self.trigdict.pop(trig.iden)
        await self.core.auth.delAuthGate(trig.iden)

    @s_nexus.Pusher.onPushAuto('trigger:set')
    async def setTrigInfo(self, iden, name, valu):
        trig = self.triggers.get(iden)
        await trig.set(name, valu)

    async def listTriggers(self):
        '''
        List all the triggers in the view.
        '''
        trigs = self.triggers.list()
        if self.parent is not None:
            trigs.extend(await self.parent.listTriggers())
        return trigs

    async def packTriggers(self, useriden):

        triggers = []
        auth = self.core.auth
        user = auth.user(useriden)
        for (iden, trig) in await self.listTriggers():
            if user.allowed(('trigger', 'get'), gateiden=iden):
                packed = trig.pack()

                useriden = packed['user']
                triguser = auth.user(useriden)
                packed['username'] = triguser.name

                triggers.append(packed)

        return triggers

    async def delete(self):
        '''
        Delete the metadata for this view.

        Note: this does not delete any layer storage.
        '''
        await self.fini()
        await self.node.pop()

    def getSpawnInfo(self):
        return {
            'iden': self.iden,
        }
