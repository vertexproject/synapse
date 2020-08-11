import asyncio
import logging
import itertools
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.snap as s_snap
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.spooled as s_spooled
import synapse.lib.trigger as s_trigger
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

reqValidVdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'parent': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
    },
    'additionalProperties': True,
    'required': ['iden', 'parent', 'creator'],
})

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

        self.core = core

        trignode = await node.open(('triggers',))
        self.trigdict = await trignode.dict()

        self.triggers = s_trigger.Triggers(self)
        for _, tdef in self.trigdict.items():
            try:
                self.triggers.load(tdef)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(f'Failed to load trigger {tdef!r}')

        await s_nexus.Pusher.__anit__(self, iden=self.iden, nexsroot=core.nexsroot)

        self.layers = []
        self.invalid = None
        self.parent = None  # The view this view was forked from

        self.permCheck = {
            'node:add': self._nodeAddConfirm,
            'prop:set': self._propSetConfirm,
            'tag:add': self._tagAddConfirm,
            'tag:prop:set': self._tagPropSetConfirm,
        }

        # isolate some initialization to easily override for SpawnView.
        await self._initViewLayers()

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

    def pack(self):
        d = {'iden': self.iden}
        d.update(self.info.pack())

        layrinfo = [lyr.pack() for lyr in self.layers]
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

    async def getEdgeVerbs(self):

        async with await s_spooled.Set.anit(dirn=self.core.dirn) as vset:

            for layr in self.layers:

                async for verb in layr.getEdgeVerbs():

                    if verb in vset:
                        continue

                    await vset.add(verb)
                    yield verb

    async def getEdges(self, verb=None):

        async with await s_spooled.Set.anit(dirn=self.core.dirn) as eset:

            for layr in self.layers:

                async for edge in layr.getEdges(verb=verb):

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

    async def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)

        info = {'query': text, 'opts': opts}
        await self.core.boss.promote('storm', user=user, info=info)

        async with await self.snap(user=user) as snap:
            async for node in snap.eval(text, opts=opts, user=user):
                yield node

    async def callStorm(self, text, opts=None):
        try:

            async for item in self.eval(text, opts=opts):
                await asyncio.sleep(0)  # pragma: no cover

        except s_exc.StormReturn as e:

            return await s_stormtypes.toprim(e.item)

    async def nodes(self, text, opts=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        return [n async for n in self.eval(text, opts=opts)]

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            ((str,dict)): Storm messages.
        '''
        opts = self.core._initStormOpts(opts)

        user = self.core._userFromOpts(opts)

        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE, loop=self.loop)

        info = {'query': text, 'opts': opts}
        synt = await self.core.boss.promote('storm', user=user, info=info)

        show = opts.get('show', set())

        mode = opts.get('mode', 'storm')
        editformat = opts.get('editformat', 'nodeedits')
        if editformat not in ('nodeedits', 'splices', 'count', 'none'):
            raise s_exc.BadConfValu(mesg='editformat')

        async def runStorm():
            cancelled = False
            tick = s_common.now()
            count = 0
            try:

                # Always start with an init message.
                await chan.put(('init', {'tick': tick, 'text': text, 'task': synt.iden}))

                # Try text parsing. If this fails, we won't be able to get a storm
                # runtime in the snap, so catch and pass the `err` message
                self.core.getStormQuery(text, mode=mode)

                shownode = (not show or 'node' in show)

                async with await self.snap(user=user) as snap:

                    if not show:
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
                if not cancelled:
                    tock = s_common.now()
                    took = tock - tick
                    await chan.put(('fini', {'tock': tock, 'took': took, 'count': count}))

        await synt.worker(runStorm())

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

                if editformat == 'count':
                    count = sum(len(edit[2]) for edit in mesg[1].get('edits', ()))
                    mesg = ('node:edits:count', {'count': count})
                    yield mesg
                    continue

                assert editformat == 'splices'

                nodeedits = mesg[1].get('edits', [()])
                async for _, splice in self.layers[0].makeSplices(0, nodeedits, None):
                    if not show or splice[0] in show:
                        yield splice
                continue

            if kind == 'fini':
                yield mesg
                break

            yield mesg

    async def iterStormPodes(self, text, opts=None):
        opts = self.core._initStormOpts(opts)
        user = self.core._userFromOpts(opts)
        info = {'query': text, 'opts': opts}
        await self.core.boss.promote('storm', user=user, info=info)

        async with await self.snap(user=user) as snap:
            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                yield pode

    async def snap(self, user):

        if self.invalid is not None:
            raise s_exc.NoSuchLayer(iden=self.invalid)

        return await self.snapctor(self, user)

    @s_nexus.Pusher.onPushAuto('view:set')
    async def setViewInfo(self, name, valu):
        '''
        Set a mutable view property.
        '''
        if name not in ('name',):
            mesg = f'{name} is not a valid view info key'
            raise s_exc.BadOptValu(mesg=mesg)
        # TODO when we can set more props, we may need to parse values.
        await self.info.set(name, valu)
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
            raise s_exc.NoSuchLayer(iden=layriden)

        if layr in self.layers:
            return

        if indx is None:
            self.layers.append(layr)
        else:
            self.layers.insert(indx, layr)

        await self.info.set('layers', [lyr.iden for lyr in self.layers])

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

    async def merge(self, useriden=None):
        '''
        Merge this view into it's parent. All changes made to this view will be applied to the parent.
        '''
        fromlayr = self.layers[0]

        if useriden is None:
            user = await self.core.auth.getUserByName('root')
        else:
            user = await self.core.auth.reqUser(useriden)

        await self.mergeAllowed(user)

        parentlayr = self.parent.layers[0]

        await self.core.boss.promote('storm', user=user, info={'merging': self.iden})

        async with await self.parent.snap(user=user) as snap:

            with snap.getStormRuntime(user=user):
                meta = await snap.getSnapMeta()

                async for nodeedits in fromlayr.iterLayerNodeEdits():
                    await parentlayr.storNodeEditsNoLift([nodeedits], meta)

        await fromlayr.truncate()

    def _confirm(self, user, perms):
        layriden = self.layers[0].iden
        if user.allowed(perms, gateiden=layriden):
            return

        perm = '.'.join(perms)
        mesg = f'User must have permission {perm} on write layer {layriden} of view {self.iden}'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=user.name)

    async def _nodeAddConfirm(self, user, snap, splice):
        perms = ('node', 'add', splice['ndef'][0])
        self.parent._confirm(user, perms)

    async def _propSetConfirm(self, user, snap, splice):
        ndef = splice.get('ndef')
        prop = splice.get('prop')
        full = f'{ndef[0]}:{prop}'
        perms = ('node', 'prop', 'set', full)
        self.parent._confirm(user, perms)

    async def _tagAddConfirm(self, user, snap, splice):
        tag = splice.get('tag')
        perms = ('node', 'tag', 'add', *tag.split('.'))
        self.parent._confirm(user, perms)

    async def _tagPropSetConfirm(self, user, snap, splice):
        tag = splice.get('tag')
        perms = ('node', 'tag', 'add', *tag.split('.'))
        self.parent._confirm(user, perms)

    async def mergeAllowed(self, user=None):
        '''
        Check whether a user can merge a view into its parent.
        '''
        fromlayr = self.layers[0]
        if self.parent is None:
            raise s_exc.CantMergeView(mesg=f'Cannot merge a view {self.iden} than has not been forked')

        parentlayr = self.parent.layers[0]
        if parentlayr.readonly:
            raise s_exc.ReadOnlyLayer(mesg="May not merge if the parent's write layer is read-only")

        for view in self.core.views.values():
            if view.parent == self:
                raise s_exc.CantMergeView(mesg='Cannot merge a view that has children itself')

        if user is None or user.isAdmin() or user.isAdmin(gateiden=parentlayr.iden):
            return

        async with await self.parent.snap(user=user) as snap:
            splicecount = 0
            async for nodeedit in fromlayr.iterLayerNodeEdits():
                async for offs, splice in fromlayr.makeSplices(0, [nodeedit], None):
                    check = self.permCheck.get(splice[0])
                    if check is None:
                        raise s_exc.SynErr(mesg='Unknown splice type, cannot safely merge',
                                           splicetype=splice[0])

                    await check(user, snap, splice[1])

                    splicecount += 1

                    if splicecount % 1000 == 0:
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
        iden = tdef.get('iden')
        if iden is None:
            tdef['iden'] = s_common.guid()
        elif self.triggers.get(iden) is not None:
            raise s_exc.DupIden(mesg='A trigger with this iden already exists')

        root = await self.core.auth.getUserByName('root')

        tdef.setdefault('user', root.iden)
        tdef.setdefault('enabled', True)

        s_trigger.reqValidTdef(tdef)

        return await self._push('trigger:add', tdef)

    @s_nexus.Pusher.onPush('trigger:add')
    async def _onPushAddTrigger(self, tdef):

        s_trigger.reqValidTdef(tdef)

        trig = self.trigdict.get(tdef['iden'])
        if trig is not None:
            return self.triggers.get(tdef['iden']).pack()

        user = self.core.auth.user(tdef['user'])
        self.core.getStormQuery(tdef['storm'])

        trig = self.triggers.load(tdef)

        await self.trigdict.set(trig.iden, tdef)
        await self.core.auth.addAuthGate(trig.iden, 'trigger')
        await user.setAdmin(True, gateiden=tdef.get('iden'), logged=False)

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

        await self.trigdict.pop(trig.iden)
        await self.core.auth.delAuthGate(trig.iden)

    @s_nexus.Pusher.onPushAuto('trigger:set')
    async def setTriggerInfo(self, iden, name, valu):
        trig = self.triggers.get(iden)
        if trig is None:
            raise s_exc.NoSuchIden("Trigger not found")
        await trig.set(name, valu)

    async def listTriggers(self):
        '''
        List all the triggers in the view.
        '''
        trigs = self.triggers.list()
        if self.parent is not None:
            trigs.extend(await self.parent.listTriggers())
        return trigs

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
