import asyncio
import logging
import itertools

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.snap as s_snap
import synapse.lib.trigger as s_trigger

logger = logging.getLogger(__name__)

class View(s_hive.AuthGater):
    '''
    A view represents a cortex as seen from a specific set of layers.

    The view class is used to implement Copy-On-Write layers as well as
    interact with a subset of the layers configured in a Cortex.
    '''

    authgatetype = 'view'

    async def __anit__(self, core, node):
        '''
        Async init the view.

        Args:
            core (Cortex):  The cortex that owns the view.
            node (HiveNode): The hive node containing the view info.
        '''
        self.node = node
        self.iden = node.name()
        self.core = core

        await s_hive.AuthGater.__anit__(self, self.core.auth)

        self.invalid = None
        self.parent = None  # The view this view was forked from
        self.worldreadable = True  # Default read permissions of this view

        self.info = await node.dict()
        self.info.setdefault('owner', 'root')
        self.info.setdefault('layers', ())

        self.triggers = s_trigger.Triggers(self)

        self.layers = []

        for iden in self.info.get('layers'):

            layr = core.layers.get(iden)

            if layr is None:
                self.invalid = iden
                logger.warning('view %r has missing layer %r' % (self.iden, iden))
                continue

            if not self.layers and layr.readonly:
                self.invalid = iden
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {iden} must not be read-only')

            self.layers.append(layr)

    def allowed(self, hiveuser, perm, elev=True, default=None):
        if self.worldreadable and perm == ('view', 'read'):
            default = True

        return s_hive.AuthGater.allowed(self, hiveuser, perm, elev=elev, default=default)

    async def eval(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        if user is None:
            user = self.core.auth.getUserByName('root')

        await self.core.boss.promote('storm', user=user, info={'query': text})
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
            user = self.core.auth.getUserByName('root')

        await self.core.boss.promote('storm', user=user, info={'query': text})
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
        if opts is None:
            opts = {}

        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE, loop=self.loop)

        if user is None:
            user = self.core.auth.getUserByName('root')

        # promote ourself to a synapse task
        synt = await self.core.boss.promote('storm', user=user, info={'query': text})

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
            user = self.auth.getUserByName('root')

        await self.core.boss.promote('storm', user=user, info={'query': text})
        async with await self.snap(user=user) as snap:
            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                yield pode

    async def snap(self, user):

        if self.invalid is not None:
            raise s_exc.NoSuchLayer(iden=self.invalid)

        return await s_snap.Snap.anit(self, user)

    def pack(self):
        return {
            'iden': self.iden,
            'owner': self.info.get('owner'),
            'layers': self.info.get('layers'),
        }

    async def addLayer(self, layr, indx=None):

        for view in self.core.views.values():
            if view.parent is self:
                raise s_exc.ReadOnlyLayer(mesg='May not change layers that have been forked from')

        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of forked view')

        if indx is None:
            if not self.layers and layr.readonly:
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {layr.iden} must not be read-only')
            self.layers.append(layr)
        else:
            if indx == 0 and layr.readonly:
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {layr.iden} must not be read-only')
            self.layers.insert(indx, layr)
        await self.info.set('layers', [l.iden for l in self.layers])

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

    async def fork(self, **layrinfo):
        '''
        Makes a new view inheriting from this view with the same layers and a new write layer on top

        Args:
            Passed through to cortex.addLayer

        Returns:
            new view object, with an iden the same as the new write layer iden
        '''
        writlayr = await self.core.addLayer(**layrinfo)
        self.onfini(writlayr)

        viewiden = s_common.guid()
        owner = layrinfo.get('owner', 'root')
        layeridens = [writlayr.iden] + [l.iden for l in self.layers]

        view = await self.core.addView(viewiden, owner, layeridens)
        view.worldreadable = False
        view.parent = self

        return view

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
        await self.triggers.runNodeAdd(node)
        if self.parent is not None:
            await self.parent.runNodeAdd(node)

    async def runNodeDel(self, node):
        await self.triggers.runNodeDel(node)
        if self.parent is not None:
            await self.parent.runNodeDel(node)

    async def runPropSet(self, node, prop, oldv):
        await self.triggers.runPropSet(node, prop, oldv)

        if self.parent is not None:
            await self.parent.runPropSet(node, prop, oldv)

    async def addTrigger(self, condition, query, info, disabled=False, user=None):
        '''
        Adds a trigger to the view.
        '''
        if user is None:
            user = self.core.auth.getUserByName('root')

        iden = self.triggers.add(user.iden, condition, query, info=info)
        if disabled:
            self.triggers.disable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='add')
        return iden

    async def getTrigger(self, iden):
        return await self.triggers.get(iden)

    async def delTrigger(self, iden):
        '''
        Delete a trigger from the view.
        '''
        self.triggers.delete(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='delete')

    async def updateTrigger(self, iden, query):
        '''
        Change an existing trigger's query.
        '''
        self.triggers.mod(iden, query)
        await self.core.fire('core:trigger:action', iden=iden, action='mod')

    async def enableTrigger(self, iden):
        '''
        Enable an existing trigger.
        '''
        self.triggers.enable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='enable')

    async def disableTrigger(self, iden):
        '''
        Disable an existing trigger.
        '''
        self.triggers.disable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='disable')

    async def listTriggers(self):
        '''
        List all the triggers in the view.
        '''
        trigs = self.triggers.list()
        if self.parent is not None:
            trigs.extend(await self.parent.listTriggers())
        return trigs

    async def trash(self):
        '''
        Delete the underlying storage for the view.

        Note: this does not delete any layer storage.
        '''
        await s_hive.AuthGater.trash(self)

        for (iden, _) in self.triggers.list():
            self.triggers.delete(iden)
