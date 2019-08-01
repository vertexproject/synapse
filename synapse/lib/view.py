import asyncio
import logging
import itertools

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.snap as s_snap
import synapse.lib.trigger as s_trigger

logger = logging.getLogger(__name__)

class View(s_base.Base):
    '''
    A view represents a cortex as seen from a specific set of layers.

    The view class is used to implement Copy-On-Write layers as well as
    interact with a subset of the layers configured in a Cortex.
    '''

    async def __anit__(self, core, node):
        '''
        Async init the view.

        Args:
            core (Cortex):  The cortex that owns the view.
            node (HiveNode): The hive node containing the view info.
        '''
        await s_base.Base.__anit__(self)

        self.core = core

        self.node = node
        self.iden = node.name()

        self.invalid = None
        self.parent = None

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
        # FIXME: check for no children?
        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of inherited view')

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
        NOTE: view layers are stored "top down" ( write is layers[0] )
        '''
        # FIXME: check for no children?
        if self.parent is not None:
            raise s_exc.ReadOnlyLayer(mesg='May not change layers of inherited view')

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

    async def makeChild(self):
        '''
        Makes a new view inheriting from this view with the same layers and a new write layer on top
        '''
        # FIXME
        pass

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

    async def addTrigger(self, condition, query, info, disabled=False, user=None):
        '''
        Adds a trigger to the cortex
        '''
        if user is None:
            user = self.core.auth.getUserByName('root')

        iden = self.triggers.add(user.iden, condition, query, info=info)
        if disabled:
            self.triggers.disable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='add')
        return iden

    def getTrigger(self, iden):
        return self.triggers.get(iden)

    async def delTrigger(self, iden):
        '''
        Deletes a trigger from the cortex
        '''
        self.triggers.delete(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='delete')

    async def updateTrigger(self, iden, query):
        '''
        Change an existing trigger's query
        '''
        self.triggers.mod(iden, query)
        await self.core.fire('core:trigger:action', iden=iden, action='mod')

    async def enableTrigger(self, iden):
        '''
        Change an existing trigger's query
        '''
        self.triggers.enable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='enable')

    async def disableTrigger(self, iden):
        '''
        Change an existing trigger's query
        '''
        self.triggers.disable(iden)
        await self.core.fire('core:trigger:action', iden=iden, action='disable')

    def listTriggers(self):
        '''
        Lists all the triggers in the View.
        '''
        trigs = []
        for (iden, trig) in self.triggers.list():
            useriden = trig['useriden']
            user = self.core.auth.user(useriden)
            trig['username'] = '<unknown>' if user is None else user.name
            trig['inherited'] = False
            trigs.append((iden, trig))

        if self.parent is not None:
            inheritd = self.parent.listTriggers()
            for trig in inheritd:
                trig['inherited'] = True
            trigs.extend(inheritd)

        return trigs
