import os
import asyncio
import logging
import copy
import contextlib
import collections

from collections.abc import Mapping

import synapse
import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.view as s_view
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.spawn as s_spawn
import synapse.lib.storm as s_storm
import synapse.lib.agenda as s_agenda
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.httpapi as s_httpapi
import synapse.lib.modules as s_modules
import synapse.lib.trigger as s_trigger
import synapse.lib.modelrev as s_modelrev
import synapse.lib.stormsvc as s_stormsvc
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slaboffs as s_slaboffs
import synapse.lib.stormhttp as s_stormhttp
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

'''
A Cortex implements the synapse hypergraph object.
'''

class CoreApi(s_cell.CellApi):
    '''
    The CoreApi is exposed when connecting to a Cortex over Telepath.

    Many CoreApi methods operate on packed nodes consisting of primitive data structures
    which can be serialized with msgpack/json.

    An example of a packaged Node::

        ( (<form>, <valu>), {

            "props": {
                <name>: <valu>,
                ...
            },
            "tags": {
                "foo": <time>,
                "foo.bar": <time>,
            },
        })

    '''
    @s_cell.adminapi
    def getCoreMods(self):
        return self.cell.getCoreMods()

    @s_cell.adminapi
    def stat(self):
        return self.cell.stat()

    @s_cell.adminapi
    async def joinTeleLayer(self, url, indx=None):
        ret = await self.cell.joinTeleLayer(url, indx=indx)
        return ret

    # FIXME:  ModelDict/Def/Defs is a mess
    async def getModelDict(self):
        '''
        Return a dictionary which describes the data model.

        Returns:
            (dict): A model description dictionary.
        '''
        return await self.cell.getModelDict()

    async def getModelDef(self):
        return await self.cell.getModelDef()

    async def getModelDefs(self):
        return await self.cell.getModelDefs()

    def getCoreInfo(self):
        '''
        Return static generic information about the cortex including model definition
        '''
        return self.cell.getCoreInfo()

    async def _getViewFromOpts(self, opts):
        '''

        Args:
            opts(Optional[Dict]): opts dicts that may contain a view field

        Returns:
            view object

        Raises:
            s_exc.NoSuchView: If the view iden doesn't exist
            s_exc.AuthDeny: If the current user doesn't have read access to the view

        '''
        iden = (opts or {}).get('view')
        return await self._getView(iden)

    async def _getView(self, iden):

        view = self.cell.getView(iden)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        self.user.confirm(('view', 'read'), gateiden=view.iden)

        return view

    async def addTrigger(self, condition, query, info, disabled=False, view=None):
        '''
        Adds a trigger to the cortex

        '''
        wlyr = self.cell.view.layers[0]
        await wlyr._reqUserAllowed(self.user, ('trigger', 'add'))

        view = self._getView(view)

        iden = await view.addTrigger(condition, query, info, disabled, user=self.user)
        return iden

    async def delTrigger(self, iden, view=None):
        '''
        Deletes a trigger from the cortex
        '''
        trig = await self.cell.getTrigger(iden)
        trig.confirm(self.user, ('trigger', 'del'))
        await self.cell.delTrigger(iden)

        await view.delTrigger(iden)

    async def updateTrigger(self, iden, query, view=None):
        '''
        Change an existing trigger's query
        '''
        trig = await self.cell.getTrigger(iden)
        trig.confirm(self.user, ('trigger', 'set'))
        await self.cell.updateTrigger(iden, query)

        await view.updateTrigger(iden, query)

    async def enableTrigger(self, iden, view=None):
        '''
        Enable an existing trigger
        '''
        trig = await self.cell.getTrigger(iden)
        trig.confirm(self.user, ('trigger', 'set'))
        await self.cell.enableTrigger(iden)

        await view.enableTrigger(iden)

    async def disableTrigger(self, iden, view=None):
        '''
        Disable an existing trigger
        '''
        trig = await self.cell.getTrigger(iden)
        trig.confirm(self.user, ('trigger', 'set'))
        await self.cell.disableTrigger(iden)

        await view.disableTrigger(iden)

    async def listTriggers(self, view=None):
        '''
        Lists all the triggers that the current user is authorized to access
        '''
        trigs = []
        view = self._getView(view)
        rawtrigs = await view.listTriggers()

        for (iden, trig) in rawtrigs:
            if await trig.allowed(self.user, ('trigger', 'get')):
                info = trig.pack()
                # pack the username into the return as a convenience
                info['username'] = self.cell.getUserName(trig.useriden)
                trigs.append((iden, info))

        return trigs

    # FIXME:  add view parm here (it wouldn't be stored on the view though)
    async def addCronJob(self, query, reqs, incunit=None, incval=1):
        '''
        Add a cron job to the cortex

        A cron job is a persistently-stored item that causes storm queries to be run in the future.  The specification
        for the times that the queries run can be one-shot or recurring.

        Args:
            query (str):  The storm query to execute in the future
            reqs (Union[Dict[str, Union[int, List[int]]], List[Dict[...]]]):
                Either a dict of the fixed time fields or a list of such dicts.  The keys are in the set ('year',
                'month', 'dayofmonth', 'dayofweek', 'hour', 'minute'.  The values must be positive integers, except for
                the key of 'dayofmonth' in which it may also be a negative integer which represents the number of days
                from the end of the month with -1 representing the last day of the month.  All values may also be lists
                of valid values.
            incunit (Optional[str]):
                A member of the same set as above, with an additional member 'day'.  If is None (default), then the
                appointment is one-shot and will not recur.
            incval (Union[int, List[int]):
                A integer or a list of integers of the number of units

        Returns (bytes):
            An iden that can be used to later modify, query, and delete the job.

        Notes:
            reqs must have fields present or incunit must not be None (or both)
            The incunit if not None it must be larger in unit size than all the keys in all reqs elements.
        '''
        self.user.confirm(('cron', 'add'))

        return await self.cell.addCronJob(self.user, query, reqs, incunit, incval)

    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        gate = self.cell.auth.reqAuthGate(iden)
        gate.confirm(self.user, ('cron', 'del'))

        await self.cell.delCronJob.delete(iden)

    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        # FIXME: discuss this model
        # await cron.reqAllowed(self.user, ('cron', 'set'))
        gate = self.cell.auth.reqAuthGate(iden)
        gate.confirm(self.user, ('cron', 'set'))
        await self.cell.updateCronJob(iden, query)

    async def enableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        gate = self.cell.auth.reqAuthGate(iden)
        gate.confirm(self.user, ('cron', 'set'))
        await self.cell.enableCronJob(iden)

    async def disableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        gate = self.cell.auth.reqAuthGate(iden)
        gate.confirm(self.user, ('cron', 'set'))
        await self.cell.disableCronJob(iden)

    async def listCronJobs(self):
        '''
        Get information about all the cron jobs accessible to the current user
        '''
        crons = []

        for iden, cron in self.cell.agenda.list():
            if not cron.allowed(self.user, ('cron', 'get')):
                continue

            info = cron.pack()
            info['username'] = self.cell.getUserName(cron.useriden)
            crons.append((iden, info))

        return crons

    async def setStormCmd(self, cdef):
        '''
        Set the definition of a pure storm command in the cortex.
        '''
        self.user.confirm(('storm', 'admin', 'cmds'))
        return await self.cell.setStormCmd(cdef)

    async def delStormCmd(self, name):
        '''
        Remove a pure storm command from the cortex.
        '''
        self.user.confirm(('storm', 'admin', 'cmds'))
        return await self.cell.delStormCmd(name)

    async def _reqDefLayerAllowed(self, perms):
        view = self.cell.getView()
        wlyr = view.layers[0]
        self.user.confirm(perms, gateiden=wlyr.iden)

    async def addNodeTag(self, iden, tag, valu=(None, None)):
        '''
        Deprecated in 0.2.0.

        FIXME:  add view parm?
        Add a tag to a node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
            valu (tuple):  A time interval tuple or (None, None).
        '''
        await self._reqDefLayerAllowed(('tag:add', *tag.split('.')))
        return await self.cell.addNodeTag(self.user, iden, tag, valu)

    async def delNodeTag(self, iden, tag):
        '''
        Deprecated in 0.2.0.
        Delete a tag from the node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
        '''
        await self._reqDefLayerAllowed(('tag:del', *tag.split('.')))
        return await self.cell.delNodeTag(self.user, iden, tag)

    async def setNodeProp(self, iden, name, valu):
        '''
        Deprecated in 0.2.0.

        Set a property on a single node.
        FIXME:  how to move to cortex and still have enforcement?
        '''
        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:

            with s_provenance.claim('coreapi', meth='prop:set', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                prop = node.form.props.get(name)
                self.user.confirm(('prop:set', prop.full), gateiden=snap.wlyr.iden)

                await node.set(name, valu)
                return node.pack()

    async def delNodeProp(self, iden, name):
        '''
        Deprecated in 0.2.0.

        Delete a property from a single node.
        '''

        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:

            with s_provenance.claim('coreapi', meth='prop:del', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                prop = node.form.props.get(name)

                self.user.confirm(('prop:del', prop.full), gateiden=snap.wlyr.iden)

                await node.pop(name)
                return node.pack()

    async def addNode(self, form, valu, props=None):
        '''
        Deprecated in 0.2.0.
        '''
        async with await self.cell.snap(user=self.user) as snap:
            self.user.confirm(('node:add', form), gateiden=snap.wlyr.iden)
            with s_provenance.claim('coreapi', meth='node:add', user=snap.user.iden):

                node = await snap.addNode(form, valu, props=props)
                return node.pack()

    async def addNodes(self, nodes):
        '''
        Add a list of packed nodes to the cortex.

        Args:
            nodes (list): [ ( (form, valu), {'props':{}, 'tags':{}}), ... ]

        Yields:
            (tuple): Packed node tuples ((form,valu), {'props': {}, 'tags':{}})

        Deprecated in 0.2.0
        '''

        # First check that that user may add each form
        done = {}
        for node in nodes:

            formname = node[0][0]
            if done.get(formname):
                continue

            await self._reqDefLayerAllowed(('node:add', formname))
            done[formname] = True

        async with await self.cell.snap(user=self.user) as snap:
            with s_provenance.claim('coreapi', meth='node:add', user=snap.user.iden):

                snap.strict = False

                async for node in snap.addNodes(nodes):

                    if node is not None:
                        node = node.pack()

                    yield node

    async def getFeedFuncs(self):
        '''
        Get a list of Cortex feed functions.

        Notes:
            Each feed dictinonary has the name of the feed function, the
            full docstring for the feed function, and the first line of
            the docstring broken out in their own keys for easy use.

        Returns:
            tuple: A tuple of dictionaries.
        '''
        return await self.cell.getFeedFuncs()

    async def addFeedData(self, name, items, seqn=None):

        wlyr = self.cell.view.layers[0]

        parts = name.split('.')

        self.user.confirm(('feed:data', *parts), gateiden=wlyr.iden)

        with s_provenance.claim('feed:data', name=name):

            async with await self.cell.snap(user=self.user) as snap:
                snap.strict = False
                # FIXME:  is this enough to make snap a nexus?  Alternative is to add a cortex pass-through
                return await snap.addFeedData(name, items, seqn=seqn)

    async def count(self, text, opts=None):
        '''
        Count the number of nodes which result from a storm query.

        Args:
            text (str): Storm query text.
            opts (dict): Storm query options.

        Returns:
            (int): The number of nodes resulting from the query.
        '''
        view = await self._getViewFromOpts(opts)

        i = 0
        # FIXME:  make a count method on view
        async for _ in view.eval(text, opts=opts, user=self.user):
            i += 1
        return i

    async def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield packed nodes.
        '''

        view = await self._getViewFromOpts(opts)

        async for pode in view.iterStormPodes(text, opts=opts, user=self.user):
            yield pode

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.

        Yields:
            ((str,dict)): Storm messages.
        '''
        view = await self._getViewFromOpts(opts)

        if opts is not None and opts.get('spawn'):

            link = s_scope.get('link')

            opts.pop('spawn', None)
            info = {
                'link': link.getSpawnInfo(),
                'view': view.iden,
                'user': self.user.iden,
                'storm': {
                    'opts': opts,
                    'query': text,
                }
            }

            tnfo = {'query': text}
            if opts:
                tnfo['opts'] = opts
            await self.cell.boss.promote('storm:spawn',
                                         user=self.user,
                                         info=tnfo)
            proc = None
            mesg = 'Spawn complete'
            try:
                async with self.cell.spawnpool.get() as proc:
                    if await proc.xact(info):
                        await link.fini()
            except Exception as e:
                if not isinstance(e, asyncio.CancelledError):
                    logger.exception('Error during spawned Storm execution.')
                if not self.cell.isfini:
                    if proc:
                        await proc.fini()
                mesg = repr(e)
                raise
            finally:
                raise s_exc.DmonSpawn(mesg=mesg)

        async for mesg in view.streamstorm(text, opts, user=self.user):
            yield mesg

    async def watch(self, wdef):
        '''
        Hook cortex/view/layer watch points based on a specified watch definition.

        Example:

            wdef = { 'tags': [ 'foo.bar', 'baz.*' ] }

            async for mesg in core.watch(wdef):
                dostuff(mesg)
        '''
        iden = wdef.get('view', self.cell.view.iden)
        self.user.confirm(('watch',), gateiden=iden)

        async for mesg in self.cell.watch(wdef):
            yield mesg

    async def getNexusChanges(self, offs):
        async for item in self.cell.getNexusChanges(offs):
            yield item

    async def syncLayerSplices(self, iden, offs, layriden=None):
        '''
        Yield (indx, mesg) splices for the given layer beginning at offset.

        Once caught up, this API will begin yielding splices in real-time.
        The generator will only terminate on network disconnect or if the
        consumer falls behind the max window size of 10,000 splice messages.
        '''
        self.user.confirm(('sync',), gateiden=iden)
        async for item in self.cell.syncLayerSplices(iden, offs):
            yield item

    @s_cell.adminapi
    async def splices(self, offs, size, layriden=None):
        '''
        Return the list of splices at the given offset.
        '''
        layr = self.cell.getLayer(layriden)
        self.user.confirm(('read',), gateiden=layr.iden)
        count = 0
        async for mesg in layr.splices(offs, size):
            count += 1
            if not count % 1000:
                await asyncio.sleep(0)
            yield mesg

    @s_cell.adminapi
    async def splicesBack(self, offs, size):
        '''
        Return the list of splices backwards from the given offset.
        '''
        # FIXME:  perm check
        count = 0
        async for mesg in self.cell.view.layers[0].splicesBack(offs, size):
            count += 1
            if not count % 1000: # pragma: no cover
                await asyncio.sleep(0)
            yield mesg

    async def spliceHistory(self):
        '''
        Yield splices backwards from the end of the splice log.

        Will only return the user's own splices unless they are an admin.
        '''
        async for splice in self.cell.spliceHistory(self.user):
            yield splice

    @s_cell.adminapi
    async def provStacks(self, offs, size):
        '''
        Return stream of (iden, provenance stack) tuples at the given offset.
        '''
        count = 0
        for iden, stack in self.cell.provstor.provStacks(offs, size):
            count += 1
            if not count % 1000:
                await asyncio.sleep(0)
            yield s_common.ehex(iden), stack

    @s_cell.adminapi
    async def getProvStack(self, iden: str):
        '''
        Return the providence stack associated with the given iden.

        Args:
            iden (str):  the iden from splice

        Note: the iden appears on each splice entry as the 'prov' property
        '''
        return self.cell.provstor.getProvStack(s_common.uhex(iden))

    async def getPropNorm(self, prop, valu):
        '''
        Get the normalized property value based on the Cortex data model.

        Args:
            prop (str): The property to normalize.
            valu: The value to normalize.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchProp: If the prop does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        return await self.cell.getPropNorm(prop, valu)

    async def getTypeNorm(self, name, valu):
        '''
        Get the normalized type value based on the Cortex data model.

        Args:
            name (str): The type to normalize.
            valu: The value to normalize.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchType: If the type does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        return await self.cell.getTypeNorm(name, valu)

    async def addFormProp(self, form, prop, tdef, info):
        '''
        Add an extended property to the given form.

        Extended properties *must* begin with _
        '''
        self.user.confirm(('model', 'prop', 'add', form))
        return await self.cell.addFormProp(form, prop, tdef, info)

    async def delFormProp(self, form, name):
        '''
        Remove an extended property from the given form.
        '''
        self.user.confirm(('model', 'prop', 'del', form))
        return await self.cell.delFormProp(form, name)

    async def addUnivProp(self, name, tdef, info):
        '''
        Add an extended universal property.

        Extended properties *must* begin with _
        '''
        self.user.confirm(('model', 'univ', 'add'))
        return await self.cell.addUnivProp(name, tdef, info)

    async def delUnivProp(self, name):
        '''
        Remove an extended universal property.
        '''
        self.user.confirm(('model', 'univ', 'del'))
        return await self.cell.delUnivProp(name)

    async def addTagProp(self, name, tdef, info):
        '''
        Add a tag property to record data about tags on nodes.
        '''
        self.user.confirm(('model', 'tagprop', 'add'))
        return await self.cell.addTagProp(name, tdef, info)

    async def delTagProp(self, name):
        '''
        Remove a previously added tag property.
        '''
        self.user.confirm(('model', 'tagprop', 'del'))
        return await self.cell.delTagProp(name)

    async def addStormPkg(self, pkgdef):
        self.user.confirm(('storm', 'pkg', 'add'))
        return await self.cell.addStormPkg(pkgdef)

    async def delStormPkg(self, iden):
        self.user.confirm(('storm', 'pkg', 'del'))
        return await self.cell.delStormPkg(iden)

    async def getStormPkgs(self):
        return await self.cell.getStormPkgs()

    async def getStormPkg(self, name):
        return await self.cell.getStormPkg(name)

    # APIs to support spawned cortexes
    @s_cell.adminapi
    async def runRuntLift(self, *args, **kwargs):
        async for item in self.cell.runRuntLift(*args, **kwargs):
            yield item

    #@s_cell.adminapi
    #async def addCoreQueue(self, name, info):
        #return await self.cell.addCoreQueue(name, info)

    #@s_cell.adminapi
    #async def delCoreQueue(self, name):
        #return await self.cell.delCoreQueue(name)

    #@s_cell.adminapi
    #async def coreQueueGets(self, name):
        #return await self.cell.delCoreQueue(name)

    #@s_cell.adminapi
    #async def hasCoreQueue(self, name):
        #return await self.cell.hasCoreQueue(name)

    #@s_cell.adminapi
    #async def delCoreQueue(self, name):
        #return await self.cell.delCoreQueue(name)

    #@s_cell.adminapi
    #async def getCoreQueue(self, name):
        #return await self.cell.getCoreQueue(name)

    #@s_cell.adminapi
    #async def getCoreQueues(self):
        #return await self.cell.getCoreQueues()

    #@s_cell.adminapi
    #async def getsCoreQueue(self, name, offs=0, wait=True, cull=True, size=None):
        #async for item in self.cell.getsCoreQueue(name, offs=offs, wait=wait, cull=cull, size=size):
            #yield item

    #@s_cell.adminapi
    #async def putCoreQueue(self, name, item):
        #return await self.cell.putCoreQueue(name, item)

    #@s_cell.adminapi
    #async def putsCoreQueue(self, name, items):
        #return await self.cell.putsCoreQueue(name, items)

    #@s_cell.adminapi
    #async def cullCoreQueue(self, name, offs):
        #return await self.cell.cullCoreQueue(name, offs)

class Cortex(s_cell.Cell):  # type: ignore
    '''
    A Cortex implements the synapse hypergraph.

    The bulk of the Cortex API lives on the Snap() object which can
    be obtained by calling Cortex.snap() in a with block.  This allows
    callers to manage transaction boundaries explicitly and dramatically
    increases performance.
    '''
    confdefs = {
        'axon': {
            'description': 'A telepath URL for a remote axon.',
            'type': 'string'
        },
        'cron:enable': {
            'default': True,
            'description': 'Enable cron jobs running.',
            'type': 'boolean'
        },
        'dedicated': {
            'default': False,
            'description': 'The cortex is free to use most of the resources of the system.',
            'type': 'boolean'
        },
        'feeds': {
            'default': [],
            'description': 'A list of feed dictionaries.',
            'type': 'array'
        },
        'layer:lmdb:map_async': {
            'default': False,
            'description': 'Set the default lmdb:map_async value in LMDB layers.',
            'type': 'boolean'
        },
        'layers:lockmemory': {
            'default': True,
            'description': 'Should new layers lock memory for performance by default.',
            'type': 'boolean'
        },
        'modules': {
            'default': [],
            'description': 'A list of module classes to load.',
            'type': 'array'
        },
        'spawn:poolsize': {
            'default': 8,
            'description': 'The max number of spare processes to keep around in the storm spawn pool.',
            'type': 'integer'
        },
        'splice:cryotank': {
            'description': 'A telepath URL for a cryotank used to archive splices.',
            'type': 'string'
        },
        'splice:en': {
            'default': True,
            'description': 'Enable storing splices for layer changes.',
            'type': 'boolean'
        },
        'splice:sync': {
            'description': 'A telepath URL for an upstream cortex.',
            'type': 'string'
        },
        'storm:log': {
            'default': False,
            'description': 'Log storm queries via system logger.',
            'type': 'boolean'
        },
        'storm:log:level': {
            'default': 30,
            'description': 'Logging log level to emit storm logs at.',
            'type': 'integer'
        }
    }

    cellapi = CoreApi

    async def __anit__(self, dirn, conf=None):

        await s_cell.Cell.__anit__(self, dirn, conf=conf)

        offsdb = self.slab.initdb('offsets')
        self.offs = s_slaboffs.SlabOffs(self.slab, offsdb)

        # share ourself via the cell dmon as "cortex"
        # for potential default remote use
        self.dmon.share('cortex', self)

        self.views = {}
        self.layers = {}
        # self.counts = {}
        self.modules = {}
        self.storage = {}
        self.storctors = {}
        self.splicers = {}
        self.feedfuncs = {}
        self.stormcmds = {}
        self.spawnpool = None

        # differentiate these for spawning
        self.storm_cmd_ctors = {}
        self.storm_cmd_cdefs = {}

        self.stormmods = {}     # name: mdef
        self.stormpkgs = {}     # name: pkgdef
        self.stormvars = None   # type: s_hive.HiveDict

        self.stormdmons = {}

        self.svcsbyiden = {}
        self.svcsbyname = {}

        self._runtLiftFuncs = {}
        self._runtPropSetFuncs = {}
        self._runtPropDelFuncs = {}

        self.ontagadds = collections.defaultdict(list)
        self.ontagdels = collections.defaultdict(list)
        self.ontagaddglobs = s_cache.TagGlobs()
        self.ontagdelglobs = s_cache.TagGlobs()

        self.libroot = (None, {}, {})
        self.bldgbuids = {} # buid -> (Node, Event)  Nodes under construction

        self.axon = None  # type: s_axon.AxonApi
        self.axready = asyncio.Event()

        self.view = None  # The default/main view

        # Change distribution
        self.nexsroot = await s_nexus.NexsRoot.anit(dirn)
        self.onfini(self.nexsroot.fini)
        self.nexswaits = collections.defaultdict(list)

        # generic fini handler for the Cortex
        self.onfini(self._onCoreFini)

        await self._initCoreHive()
        self._initSplicers()
        self._initStormLibs()
        self._initFeedFuncs()

        await self._initStorCtors()

        if self.inaugural:
            await self._initDefLayrStor()

        await self._loadLayrStors()

        self._initCortexHttpApi()

        self.model = s_datamodel.Model()

        # Perform module loading
        mods = list(s_modules.coremods)
        mods.extend(self.conf.get('modules'))
        await self._loadCoreMods(mods)
        await self._loadExtModel()
        await self._initStormCmds()

        # Initialize our storage and views
        await self._initCoreAxon()

        await self._migrateViewsLayers()
        await self._initCoreLayers()
        await self._initCoreViews()
        self.onfini(self._finiStor)
        await self._checkLayerModels()
        await self._initCoreQueues()

        self.provstor = await s_provenance.ProvStor.anit(self.dirn)
        self.onfini(self.provstor.fini)

        self.addHealthFunc(self._cortexHealth)

        async def finidmon():
            await asyncio.gather(*[dmon.fini() for dmon in self.stormdmons.values()])

        self.onfini(finidmon)

        self.trigstor = s_trigger.TriggerStorage(self)
        self.agenda = await s_agenda.Agenda.anit(self)
        self.onfini(self.agenda)

        await self._initRuntFuncs()

        cmdhive = await self.hive.open(('cortex', 'storm', 'cmds'))
        pkghive = await self.hive.open(('cortex', 'storm', 'packages'))
        self.cmdhive = await cmdhive.dict()
        self.pkghive = await pkghive.dict()

        # Finalize coremodule loading & give stormservices a shot to load
        await self._initCoreMods()
        await self._initStormSvcs()
        await self._initPureStormCmds()

        # Now start agenda and dmons after all coremodules have finished
        # loading and services have gotten a shot to be registerd.
        if self.conf.get('cron:enable'):
            await self.agenda.start()
        await self._initStormDmons()

        # Initialize free-running tasks.
        # self._initCryoLoop()
        # self._initPushLoop()
        # self._initFeedLoops()

        self.spawnpool = await s_spawn.SpawnPool.anit(self)
        self.onfini(self.spawnpool)
        self.on('user:mod', self._onEvtBumpSpawnPool)

        self.dynitems.update({
            'cron': self.agenda,
            'cortex': self,
            'triggers': self.trigstor,
            'multiqueue': self.multiqueue,
        })

        await self.auth.addAuthGate('cortex', 'cortex')

    async def _onEvtBumpSpawnPool(self, evnt):
        await self.bumpSpawnPool()

    async def bumpSpawnPool(self):
        if self.spawnpool is not None:
            await self.spawnpool.bump()

    async def addCoreQueue(self, name, info):

        if self.multiqueue.exists(name):
            mesg = f'Queue named {name} already exists!'
            raise s_exc.DupName(mesg=mesg)

        await self._push('queue:add', name, info)

        await self.auth.addAuthGate(f'queue:{name}', 'queue')

        creator = info.get('creator')
        if creator is not None:
            user = await self.auth.reqUser(creator)
            await user.setAdmin(True, gateiden=f'queue:{name}')

        return info

    @s_nexus.Pusher.onPush('queue:add')
    async def _addCoreQueue(self, name, info):
        return await self.multiqueue.add(name, info)

    async def getCoreQueue(self, name):
        return self.multiqueue.status(name)

    async def delCoreQueue(self, name):

        if not self.multiqueue.exists(name):
            mesg = f'No queue named {name} exists!'
            raise s_exc.NoSuchName(mesg=mesg)

        await self._push('queue:del', name)
        await self.auth.delAuthGate(f'queue:{name}')

    @s_nexus.Pusher.onPush('queue:del')
    async def _delCoreQueue(self, name):
        await self.multiqueue.rem(name)

    async def coreQueueGet(self, name, offs=0, wait=None):
        async for item in self.multiqueue.gets(name, offs, wait=wait):
            return item

    async def coreQueueGets(self, name, offs=0, wait=None, size=None):
        count = 0
        async for item in self.multiqueue.gets(name, offs, wait=wait):

            yield item

            count += 1
            if size is not None and count >= size:
                return

    async def coreQueuePuts(self, name, items):
        return await self._push('queue:puts', name, items)

    @s_nexus.Pusher.onPush('queue:puts')
    async def _coreQueuePuts(self, name, items):
        await self.multiqueue.puts(name, items)

    async def coreQueueCull(self, name, offs):
        await self._push('queue:cull', name, offs)

    @s_nexus.Pusher.onPush('queue:cull')
    async def _coreQueueCull(self, name, offs):
        await self.multiqueue.cull(name, offs)

    async def getSpawnInfo(self):
        return {
            'iden': self.iden,
            'dirn': self.dirn,
            'conf': {
                'storm:log': self.conf.get('storm:log', False),
                'storm:log:level': self.conf.get('storm:log:level', logging.INFO),
            },
            'loglevel': logger.getEffectiveLevel(),
            # TODO make getModelDefs include extended model
            'views': [v.getSpawnInfo() for v in self.views.values()],
            'layers': [l.getSpawnInfo() for l in self.layers.values()],
            'storm': {
                'cmds': {
                    'cdefs': list(self.storm_cmd_cdefs.items()),
                    'ctors': list(self.storm_cmd_ctors.items()),
                },
                'libs': tuple(self.libroot),
                'mods': await self.getStormMods()
            },
            'model': await self.getModelDefs(),
        }

    async def _finiStor(self):
        await asyncio.gather(*[view.fini() for view in self.views.values()])
        await asyncio.gather(*[layr.fini() for layr in self.layers.values()])

    async def _initRuntFuncs(self):

        async def onSetTrigDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            trig = await node.snap.view.triggers.get(iden)
            trig.confirm(node.snap.user, ('trigger', 'set', 'doc'))
            await trig.setDoc(valu)
            node.props[prop.name] = valu
            await self.fire('core:trigger:action', iden=iden, action='mod')

        async def onSetTrigName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            trig = await node.snap.view.triggers.get(iden)
            trig.confirm(node.snap.user, ('trigger', 'set', 'name'))
            await trig.setName(valu)
            node.props[prop.name] = valu
            await self.fire('core:trigger:action', iden=iden, action='mod')

        async def onSetCronDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            appt = await self.agenda.get(iden)
            appt.confirm(node.snap.user, ('cron', 'set', 'doc'))
            await appt.setDoc(valu)
            node.props[prop.name] = valu

        async def onSetCronName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            appt = await self.agenda.get(iden)
            appt.confirm(node.snap.user, ('cron', 'set', 'name'))
            await appt.setName(valu)
            node.props[prop.name] = valu

        # TODO runt node lifting needs to become per view
        self.addRuntLift('syn:cron', self.agenda.onLiftRunts)

        self.addRuntPropSet('syn:cron:doc', onSetCronDoc)
        self.addRuntPropSet('syn:cron:name', onSetCronName)

        self.addRuntPropSet('syn:trigger:doc', onSetTrigDoc)
        self.addRuntPropSet('syn:trigger:name', onSetTrigName)

    async def _initStormDmons(self):

        node = await self.hive.open(('cortex', 'storm', 'dmons'))

        self.stormdmonhive = await node.dict()

        for iden, ddef in self.stormdmonhive.items():
            try:
                await self.runStormDmon(iden, ddef)

            except asyncio.CancelledError:  # pragma: no cover
                raise

            except Exception as e:
                logger.warning(f'initStormDmon ({iden}) failed: {e}')

    async def _initStormSvcs(self):

        node = await self.hive.open(('cortex', 'storm', 'services'))

        self.stormservices = await node.dict()

        for iden, sdef in self.stormservices.items():

            try:
                await self._setStormSvc(sdef)

            except asyncio.CancelledError:  # pragma: no cover
                raise

            except Exception as e:
                logger.warning(f'initStormService ({iden}) failed: {e}')

    async def _initCoreQueues(self):
        path = os.path.join(self.dirn, 'slabs', 'queues.lmdb')

        slab = await s_lmdbslab.Slab.anit(path, map_async=True)
        self.onfini(slab.fini)

        self.multiqueue = await slab.getMultiQueue('cortex:queue', nexsroot=self.nexsroot)

    @s_nexus.Pusher.onPushAuto('cmd:set')
    async def setStormCmd(self, cdef):
        '''
        Set pure storm command definition.

        Args:
        cdef = {

            'name': <name>,

            'cmdopts': [
                (<name>, <opts>),
            ]

            'cmdconf': {
                <str>: <valu>
            },

            'storm': <text>,

        }
        '''
        name = cdef.get('name')
        await self._setStormCmd(cdef)
        await self.cmdhive.set(name, cdef)

    async def _reqStormCmd(self, cdef):

        name = cdef.get('name')
        if not s_grammar.isCmdName(name):
            raise s_exc.BadCmdName(name=name)

        self.getStormQuery(cdef.get('storm'))

    async def _setStormCmd(self, cdef):
        '''
        Note:
            No change control or persistence
        '''

        await self._reqStormCmd(cdef)

        def ctor(argv):
            return s_storm.PureCmd(cdef, argv)

        # TODO unify class ctors and func ctors vs briefs...
        def getCmdBrief():
            return cdef.get('descr', 'No description').strip().split('\n')[0]

        ctor.getCmdBrief = getCmdBrief
        ctor.pkgname = cdef.get('pkgname')
        ctor.svciden = cdef.get('cmdconf', {}).get('svciden', '')
        ctor.forms = cdef.get('forms', {})

        name = cdef.get('name')
        self.stormcmds[name] = ctor
        self.storm_cmd_cdefs[name] = cdef

        await self.bumpSpawnPool()

        await self.fire('core:cmd:change', cmd=name, act='add')

    async def _popStormCmd(self, name):
        self.stormcmds.pop(name, None)
        await self.bumpSpawnPool()

        await self.fire('core:cmd:change', cmd=name, act='del')

    @s_nexus.Pusher.onPushAuto('cmd:del')
    async def delStormCmd(self, name):
        '''
        Remove a previously set pure storm command.
        '''
        ctor = self.stormcmds.get(name)
        if ctor is None:
            mesg = f'No storm command named {name}.'
            raise s_exc.NoSuchCmd(name=name, mesg=mesg)

        cdef = self.cmdhive.get(name)
        if cdef is None:
            mesg = f'The storm command ({name}) is not dynamic.'
            raise s_exc.CantDelCmd(mesg=mesg)

        await self.cmdhive.pop(name)
        self.stormcmds.pop(name, None)
        await self.bumpSpawnPool()

        await self.fire('core:cmd:change', cmd=name, act='del')

    @s_nexus.Pusher.onPushAuto('pkg:add')
    async def addStormPkg(self, pkgdef):
        '''
        Add the given storm package to the cortex.

        This will store the package for future use.
        '''
        await self.loadStormPkg(pkgdef)
        name = pkgdef.get('name')
        await self.pkghive.set(name, pkgdef)

    @s_nexus.Pusher.onPushAuto('pkg:del')
    async def delStormPkg(self, name):
        '''
        Delete a storm package by name.
        '''
        pkgdef = await self.pkghive.pop(name, None)
        if pkgdef is None:
            mesg = f'No storm package: {name}.'
            raise s_exc.NoSuchPkg(mesg=mesg)

        await self._dropStormPkg(pkgdef)

    async def getStormPkg(self, name):
        return self.stormpkgs.get(name)

    async def getStormPkgs(self):
        return list(self.pkghive.values())

    async def getStormMods(self):
        return self.stormmods

    async def _tryLoadStormPkg(self, pkgdef):
        try:
            await self.loadStormPkg(pkgdef)
        except asyncio.CancelledError:
            raise  # pragma: no cover

        except Exception as e:
            name = pkgdef.get('name', '')
            logger.exception(f'Error loading pkg: {name}, {str(e)}')

    async def _confirmStormPkg(self, pkgdef):
        '''
        Validate a storm package for loading.  Raises if invalid.
        '''
        # validate things first...
        name = pkgdef.get('name')
        if name is None:
            mesg = 'Package definition has no "name" field.'
            raise s_exc.BadPkgDef(mesg=mesg)

        vers = pkgdef.get('version')
        if vers is None:
            mesg = 'Package definition has no "version" field.'
            raise s_exc.BadPkgDef(mesg=mesg)

        mods = pkgdef.get('modules', ())
        cmds = pkgdef.get('commands', ())
        svciden = pkgdef.get('svciden')

        # Validate storm contents from modules and commands
        for mdef in mods:

            modname = mdef.get('name')
            if modname is None:
                raise s_exc.BadPkgDef(mesg='Package module is missing a name.',
                                      package=name)
            modtext = mdef.get('storm')
            self.getStormQuery(modtext)

        for cdef in cmds:
            cdef.setdefault('cmdconf', {})
            if svciden:
                cdef['cmdconf']['svciden'] = svciden

            cdef['pkgname'] = name

            await self._reqStormCmd(cdef)

    async def loadStormPkg(self, pkgdef):
        '''
        Load a storm package into the storm library for this cortex.

        NOTE: This will *not* persist the package (allowing service dynamism).
        '''
        await self._confirmStormPkg(pkgdef)
        name = pkgdef.get('name')

        mods = pkgdef.get('modules', ())
        cmds = pkgdef.get('commands', ())

        # now actually load...
        self.stormpkgs[name] = pkgdef

        # copy the mods dict and smash the ref so
        # updates are atomic and dont effect running
        # storm queries.
        stormmods = self.stormmods.copy()
        for mdef in mods:
            modname = mdef.get('name')
            stormmods[modname] = mdef

        self.stormmods = stormmods

        for cdef in cmds:
            await self._setStormCmd(cdef)

        await self.bumpSpawnPool()

    async def _dropStormPkg(self, pkgdef):
        '''
        Reverse the process of loadStormPkg()
        '''
        for mdef in pkgdef.get('modules', ()):
            modname = mdef.get('name')
            self.stormmods.pop(modname, None)

        for cdef in pkgdef.get('commands', ()):
            name = cdef.get('name')
            await self._popStormCmd(name)

        await self.bumpSpawnPool()

    def getStormSvc(self, name):

        ssvc = self.svcsbyiden.get(name)
        if ssvc is not None:
            return ssvc

        ssvc = self.svcsbyname.get(name)
        if ssvc is not None:
            return ssvc

    async def addStormSvc(self, sdef):
        '''
        Add a registered storm service to the cortex.
        '''
        if sdef.get('iden') is None:
            sdef['iden'] = s_common.guid()
        return await self._push('storm:svc:add', sdef)

    @s_nexus.Pusher.onPush('svc:add')
    async def _onAddStormSvc(self, sdef):

        iden = sdef.get('iden')
        if self.svcsbyiden.get(iden) is not None:
            mesg = f'Storm service already exists: {iden}'
            raise s_exc.DupStormSvc(mesg=mesg)

        ssvc = await self._setStormSvc(sdef)
        await self.stormservices.set(iden, sdef)
        await self.bumpSpawnPool()

        return ssvc.sdef

    @s_nexus.Pusher.onPushAuto('svc:del')
    async def delStormSvc(self, iden):
        '''
        Delete a registered storm service from the cortex.
        '''
        try:
            await self.runStormSvcEvent(iden, 'del')
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            logger.exception(f'service.del hook for service {iden} failed with error: {e}')

        sdef = await self.stormservices.pop(iden, None)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        await self._delStormSvcPkgs(iden)

        name = sdef.get('name')
        if name is not None:
            self.svcsbyname.pop(name, None)

        ssvc = self.svcsbyiden.pop(iden, None)
        if ssvc is not None:
            await ssvc.fini()

        await self.bumpSpawnPool()

    async def _delStormSvcPkgs(self, iden):
        '''
        Delete storm packages associated with a service.
        '''
        oldpkgs = []
        for name, pdef in self.pkghive.items():
            pkgiden = pdef.get('svciden')
            if pkgiden and pkgiden == iden:
                oldpkgs.append(pdef)

        for pkg in oldpkgs:
            name = pkg.get('name')
            if name:
                await self.delStormPkg(name)

    async def setStormSvcEvents(self, iden, edef):
        '''
        Set the event callbacks for a storm service. Extends the sdef dict

        edef = {
            <name> : {
                'storm': <storm>
            }
        }

        where <name> can be one of [add, del], where
        add -- Run the given storm '*before* the service is first added (a la service.add), but not on a reconnect.
        del -- Run the given storm *after* the service is removed (a la service.del), but not on a disconnect.
        '''
        sdef = self.stormservices.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        sdef['evts'] = edef
        await self.stormservices.set(iden, sdef)
        return sdef

    async def _runStormSvcAdd(self, iden):
        sdef = self.stormservices.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        if sdef.get('added', False):
            return

        try:
            await self.runStormSvcEvent(iden, 'add')
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            logger.exception(f'runStormSvcEvent service.add failed with error {e}')
            return

        sdef['added'] = True
        await self.stormservices.set(iden, sdef)

    async def runStormSvcEvent(self, iden, name):
        sdef = self.stormservices.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        evnt = sdef.get('evts', {}).get(name, {}).get('storm')
        if evnt is None:
            return
        await s_common.aspin(self.storm(evnt, opts={'vars': {'cmdconf': {'svciden': iden}}}))

    async def _setStormSvc(self, sdef):

        ssvc = await s_stormsvc.StormSvcClient.anit(self, sdef)

        self.onfini(ssvc)

        self.svcsbyiden[ssvc.iden] = ssvc
        self.svcsbyname[ssvc.name] = ssvc

        return ssvc

    def getStormSvcs(self):
        return list(self.svcsbyiden.values())

    async def _cortexHealth(self, health):
        health.update('cortex', 'nominal')

    async def _loadExtModel(self):

        self.extprops = await (await self.hive.open(('cortex', 'model', 'props'))).dict()
        self.extunivs = await (await self.hive.open(('cortex', 'model', 'univs'))).dict()
        self.exttagprops = await (await self.hive.open(('cortex', 'model', 'tagprops'))).dict()

        for form, prop, tdef, info in self.extprops.values():
            try:
                self.model.addFormProp(form, prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext prop ({form}:{prop}) error: {e}')

        for prop, tdef, info in self.extunivs.values():
            try:
                self.model.addUnivProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext univ ({prop}) error: {e}')

        for prop, tdef, info in self.exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.warning(f'ext tag prop ({prop}) error: {e}')

        await self.bumpSpawnPool()

    @contextlib.asynccontextmanager
    async def watcher(self, wdef):

        iden = wdef.get('view', self.view.iden)

        view = self.views.get(iden)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        async with await s_queue.Window.anit(maxsize=10000) as wind:

            tags = wdef.get('tags')
            if tags is not None:

                tglobs = s_cache.TagGlobs()
                [tglobs.add(t, True) for t in tags]

                async def ontag(mesg):
                    name = mesg[1].get('tag')
                    if not tglobs.get(name):
                        return

                    await wind.put(mesg)

                for layr in self.view.layers:
                    layr.on('tag:add', ontag, base=wind)
                    layr.on('tag:del', ontag, base=wind)

            yield wind

    async def watch(self, wdef):
        '''
        Hook cortex/view/layer watch points based on a specified watch definition.
        ( see CoreApi.watch() docs for details )
        '''
        async with self.watcher(wdef) as wind:
            async for mesg in wind:
                yield mesg

    @s_nexus.Pusher.onPushAuto('model:univ:add')
    async def addUnivProp(self, name, tdef, info):
        # the loading function does the actual validation...
        if not name.startswith('_'):
            mesg = 'ext univ name must start with "_"'
            raise s_exc.BadPropDef(name=name, mesg=mesg)

        if info.get('defval', s_common.novalu) is not s_common.novalu:
            mesg = 'Ext univ may not (yet) have a default value.'
            raise s_exc.BadPropDef(name=name, mesg=mesg)

        self.model.addUnivProp(name, tdef, info)

        await self.extunivs.set(name, (name, tdef, info))
        await self.fire('core:extmodel:change', prop=name, act='add', type='univ')

    @s_nexus.Pusher.onPushAuto('model:prop:add')
    async def addFormProp(self, form, prop, tdef, info):
        if not prop.startswith('_'):
            mesg = 'ext prop must begin with "_"'
            raise s_exc.BadPropDef(prop=prop, mesg=mesg)

        if info.get('defval', s_common.novalu) is not s_common.novalu:
            mesg = 'Ext prop may not (yet) have a default value.'
            raise s_exc.BadPropDef(prop=prop, mesg=mesg)

        self.model.addFormProp(form, prop, tdef, info)
        await self.extprops.set(f'{form}:{prop}', (form, prop, tdef, info))
        await self.fire('core:extmodel:change',
                        form=form, prop=prop, act='add', type='formprop')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:prop:del')
    async def delFormProp(self, form, prop):
        '''
        Remove an extended property from the cortex.
        '''
        full = f'{form}:{prop}'

        pdef = self.extprops.get(full)
        if pdef is None:
            mesg = f'No ext prop named {full}'
            raise s_exc.NoSuchProp(form=form, prop=prop, mesg=mesg)

        for layr in self.layers.values():
            async for item in layr.iterPropRows(form, prop):
                mesg = f'Nodes still exist with prop: {form}:{prop}'
                raise s_exc.CantDelProp(mesg=mesg)

        self.model.delFormProp(form, prop)
        await self.extprops.pop(full, None)
        await self.fire('core:extmodel:change',
                        form=form, prop=prop, act='del', type='formprop')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:univ:del')
    async def delUnivProp(self, prop):
        '''
        Remove an extended universal property from the cortex.
        '''
        udef = self.extunivs.get(prop)
        if udef is None:
            mesg = f'No ext univ named {prop}'
            raise s_exc.NoSuchUniv(name=prop, mesg=mesg)

        univname = '.' + prop
        for layr in self.layers.values():
            async for item in layr.iterUnivRows(univname):
                mesg = f'Nodes still exist with universal prop: {prop}'
                raise s_exc.CantDelUniv(mesg=mesg)

        self.model.delUnivProp(prop)
        await self.extunivs.pop(prop, None)
        await self.fire('core:extmodel:change', name=prop, act='del', type='univ')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:tagprop:add')
    async def addTagProp(self, name, tdef, info):
        if self.exttagprops.get(name) is not None:
            raise s_exc.DupPropName(name=name)

        self.model.addTagProp(name, tdef, info)

        await self.exttagprops.set(name, (name, tdef, info))
        await self.fire('core:tagprop:change', name=name, act='add')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:tagprop:del')
    async def delTagProp(self, name):
        pdef = self.exttagprops.get(name)
        if pdef is None:
            mesg = f'No tag prop named {name}'
            raise s_exc.NoSuchProp(mesg=mesg, name=name)

        for layr in self.layers.values():
            if await layr.hasTagProp(name):
                mesg = f'Nodes still exist with tagprop: {name}'
                raise s_exc.CantDelProp(mesg=mesg)

        self.model.delTagProp(name)

        await self.exttagprops.pop(name, None)
        await self.fire('core:tagprop:change', name=name, act='del')
        await self.bumpSpawnPool()

    async def addNodeTag(self, user, iden, tag, valu=(None, None)):
        '''
        Add a tag to a node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
            valu (tuple):  A time interval tuple or (None, None).
        '''

        buid = s_common.uhex(iden)
        async with await self.snap(user=user) as snap:

            with s_provenance.claim('coreapi', meth='tag:add', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                await node.addTag(tag, valu=valu)
                return node.pack()

    async def addNode(self, user, form, valu, props=None):

        async with await self.snap(user=user) as snap:
            node = await snap.addNode(form, valu, props=props)
            return node.pack()

    async def delNodeTag(self, user, iden, tag):
        '''
        Delete a tag from the node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
        '''
        buid = s_common.uhex(iden)

        async with await self.snap(user=user) as snap:

            with s_provenance.claim('coreapi', meth='tag:del', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                await node.delTag(tag)
                return node.pack()

    async def _onCoreFini(self):
        '''
        Generic fini handler for cortex components which may change or vary at runtime.
        '''
        if self.axon:
            await self.axon.fini()

    async def getNexusChanges(self, offs):
        async for item in self.nexsroot.iter(offs):
            yield item

    async def syncLayerSplices(self, iden, offs):
        '''
        Yield (offs, mesg) tuples for splices in a layer.
        '''
        layr = self.getLayer(iden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        async for item in layr.syncSplices(offs):
            yield item

    async def spliceHistory(self, user):
        '''
        Yield splices backwards from the end of the splice log.

        Will only return user's own splices unless they are an admin.
        '''
        layr = self.view.layers[0]
        indx = (await layr.stat())['splicelog_indx']

        count = 0
        async for mesg in layr.splicesBack(indx):
            count += 1
            if not count % 1000: # pragma: no cover
                await asyncio.sleep(0)

            if user.iden == mesg[1]['user'] or user.admin:
                yield mesg

    async def initCoreMirror(self, url):
        '''
        Initialize this cortex as a down-stream mirror from a telepath url, receiving splices from another cortex.

        Note:
            This cortex *must* be initialized from a backup of the target cortex!
        '''
        self.schedCoro(self._initCoreMirror(url))

    async def _initCoreMirror(self, url):

        while not self.isfini:

            try:

                async with await s_telepath.openurl(url) as proxy:

                    # if we really are a backup mirror, we have the same iden.
                    if self.iden != await proxy.getCellIden():
                        logger.error('remote cortex has different iden! (aborting mirror, shutting down cortex.).')
                        await self.fini()
                        return

                    offs = self.nexsroot.getOffset()

                    logger.warning(f'mirror loop connected ({url} offset={offs})')

                    while not proxy.isfini:

                        # gotta do this in the loop as well...
                        offs = self.nexsroot.getOffset()

                        # pump them into a queue so we can consume them in chunks
                        q = asyncio.Queue(maxsize=1000)

                        async def consume(x):
                            try:
                                async for item in proxy.getNexusChanges(x):
                                    await q.put(item)
                            finally:
                                await q.put(None)

                        proxy.schedCoro(consume(offs))

                        done = False
                        while not done:

                            # get the next item so we maybe block...
                            item = await q.get()
                            if item is None:
                                break

                            items = [item]

                            # check if there are more we can eat
                            for i in range(q.qsize()):

                                nexi = await q.get()
                                if nexi is None:
                                    done = True
                                    break

                                items.append(nexi)

                            for nexi in items:
                                iden, evt, args, kwargs = nexi[1]
                                await self.nexsroot.eat(iden, evt, args, kwargs)

                                waits = self.nexswaits.pop(nexi[0] + 1, None)
                                if waits is not None:
                                    [e.set() for e in waits]

            except asyncio.CancelledError: # pragma: no cover
                return

            except Exception:
                logger.exception('error in initCoreMirror loop')

            await self.waitfini(1)

    async def getNexusOffs(self):
        return self.nexsroot.getOffset()

    async def waitNexusOffs(self, offs):
        evnt = asyncio.Event()

        if self.nexsroot.getOffset() >= offs:
            evnt.set()
        else:
            self.nexswaits[offs].append(evnt)

        return evnt

#    async def _getWaitFor(self, name, valu):
#        form = self.model.form(name)
#        return form.getWaitFor(valu)

    async def _initCoreHive(self):
        stormvars = await self.hive.open(('cortex', 'storm', 'vars'))
        self.stormvars = await s_hive.NexusHiveDict.anit(await stormvars.dict(), nexsroot=self.nexsroot)
        self.onfini(self.stormvars)

    async def _initCoreAxon(self):
        turl = self.conf.get('axon')
        if turl is None:
            path = os.path.join(self.dirn, 'axon')
            self.axon = await s_axon.Axon.anit(path)
            self.axon.onfini(self.axready.clear)
            self.axready.set()
            return

        async def teleloop():
            self.axready.clear()
            while not self.isfini:
                try:
                    self.axon = await s_telepath.openurl(turl)
                    self.axon.onfini(teleloop)
                    self.axready.set()
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning('remote axon error: %r' % (e,))
                await self.waitfini(1)

        self.schedCoro(teleloop())

    async def _initStormCmds(self):
        '''
        Registration for built-in Storm commands.
        '''
        self.addStormCmd(s_storm.MaxCmd)
        self.addStormCmd(s_storm.MinCmd)
        self.addStormCmd(s_storm.TeeCmd)
        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.IdenCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.UniqCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.GraphCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.SleepCmd)
        self.addStormCmd(s_storm.ScrapeCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)
        self.addStormCmd(s_storm.SpliceListCmd)
        self.addStormCmd(s_storm.SpliceUndoCmd)

        for cdef in s_stormsvc.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_storm.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

    async def _initPureStormCmds(self):
        oldcmds = []
        for name, cdef in self.cmdhive.items():
            cmdiden = cdef.get('cmdconf', {}).get('svciden')
            if cmdiden and self.stormservices.get(cmdiden) is None:
                oldcmds.append(name)
            else:
                await self._trySetStormCmd(name, cdef)

        for name in oldcmds:
            logger.warning(f'Removing old command: [{name}]')
            await self.cmdhive.pop(name)

        for name, pkgdef in self.pkghive.items():
            await self._tryLoadStormPkg(pkgdef)

    async def _trySetStormCmd(self, name, cdef):
        try:
            await self._setStormCmd(cdef)
        except Exception:
            logger.exception(f'Storm command load failed: {name}')

    def _initStormLibs(self):
        '''
        Registration for built-in Storm Libraries
        '''
        self.addStormLib(('csv',), s_stormtypes.LibCsv)
        self.addStormLib(('str',), s_stormtypes.LibStr)
        self.addStormLib(('pkg',), s_stormtypes.LibPkg)
        self.addStormLib(('dmon',), s_stormtypes.LibDmon)
        self.addStormLib(('feed',), s_stormtypes.LibFeed)
        self.addStormLib(('time',), s_stormtypes.LibTime)
        self.addStormLib(('user',), s_stormtypes.LibUser)
        self.addStormLib(('vars',), s_stormtypes.LibVars)
        self.addStormLib(('view',), s_stormtypes.LibView)
        self.addStormLib(('queue',), s_stormtypes.LibQueue)
        self.addStormLib(('stats',), s_stormtypes.LibStats)
        self.addStormLib(('service',), s_stormtypes.LibService)
        self.addStormLib(('bytes',), s_stormtypes.LibBytes)
        self.addStormLib(('globals',), s_stormtypes.LibGlobals)
        self.addStormLib(('telepath',), s_stormtypes.LibTelepath)

        self.addStormLib(('inet', 'http'), s_stormhttp.LibHttp)
        self.addStormLib(('base64',), s_stormtypes.LibBase64)

    def _initSplicers(self):
        '''
        Registration for splice handlers.
        '''
        splicers = {
            'tag:add': self._onFeedTagAdd,
            'tag:del': self._onFeedTagDel,
            'node:add': self._onFeedNodeAdd,
            'node:del': self._onFeedNodeDel,
            'prop:set': self._onFeedPropSet,
            'prop:del': self._onFeedPropDel,
            'tag:prop:set': self._onFeedTagPropSet,
            'tag:prop:del': self._onFeedTagPropDel,
        }
        self.splicers.update(**splicers)

    async def _initStorCtors(self):
        '''
        Registration for built-in Layer ctors
        '''
        self.addLayrStorClass(s_layer.LayerStorage)

    async def _loadLayrStors(self):

        for iden, node in await self.hive.open(('cortex', 'storage')):
            storinfo = await node.dict()
            try:
                await self._initLayrStor(storinfo)

            except asyncio.CancelledError: # pragma: no cover
                raise

            except Exception:
                logger.exception('error loading layer storage!')

        iden = self.cellinfo.get('layr:stor:default')
        self.defstor = self.storage.get(iden)

    async def _initDefLayrStor(self):
        layr = await self.addLayrStor('local', {})
        await self.cellinfo.set('layr:stor:default', layr.iden)

    @s_nexus.Pusher.onPushAuto('storage:add')
    async def addLayrStor(self, typename, typeconf):
        iden = s_common.guid()
        clas = self.storctors.get(typename)
        if clas is None:
            raise s_exc.NoSuchStor(name=typename)

        await clas.reqValidConf(typeconf)

        node = await self.hive.open(('cortex', 'storage', iden))

        info = await node.dict()

        await info.set('iden', iden)
        await info.set('type', typename)
        await info.set('conf', typeconf)

        return await self._initLayrStor(info)

    async def _initLayrStor(self, storinfo):

        iden = storinfo.get('iden')
        typename = storinfo.get('type')

        clas = self.storctors.get(typename)

        # We don't want to persist the path, as it makes backup more difficult
        path = s_common.gendir(self.dirn, 'layers')

        layrstor = await clas.anit(storinfo, path)

        self.storage[iden] = layrstor

        self.onfini(layrstor)

        return layrstor

    def addLayrStorClass(self, clas):
        self.storctors[clas.stortype] = clas

    def _initFeedFuncs(self):
        '''
        Registration for built-in Cortex feed functions.
        '''
        self.setFeedFunc('syn.nodes', self._addSynNodes)
        self.setFeedFunc('syn.splice', self._addSynSplice)
        self.setFeedFunc('syn.ingest', self._addSynIngest)

    def _initCortexHttpApi(self):
        '''
        Registration for built-in Cortex httpapi endpoints
        '''
        self.addHttpApi('/api/v1/storm', s_httpapi.StormV1, {'cell': self})
        self.addHttpApi('/api/v1/watch', s_httpapi.WatchSockV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/nodes', s_httpapi.StormNodesV1, {'cell': self})

        self.addHttpApi('/api/v1/model', s_httpapi.ModelV1, {'cell': self})
        self.addHttpApi('/api/v1/model/norm', s_httpapi.ModelNormV1, {'cell': self})

    async def getCellApi(self, link, user, path):

        if not path:
            return await CoreApi.anit(self, link, user)

        # allow an admin to directly open the cortex hive
        # (perhaps this should be a Cell() level pattern)
        if path[0] == 'hive' and user.admin:
            return await s_hive.HiveApi.anit(self.hive, user)

        if path[0] == 'layer':

            if len(path) == 1:
                # get the top layer for the default view
                layr = self.getLayer()
                return await s_layer.LayerApi.anit(self, link, user, layr)

            if len(path) == 2:
                layr = self.getLayer(path[1])
                if layr is None:
                    raise s_exc.NoSuchLayer(iden=path[1])

                return await s_layer.LayerApi.anit(self, link, user, layr)

        raise s_exc.NoSuchPath(path=path)

    async def getModelDict(self):
        return self.model.getModelDict()

    async def getModelDefs(self):
        defs = self.model.getModelDefs()
        # TODO add extended model defs
        return defs

    async def getFormCounts(self):
        '''
        Return total form counts for all existing layers
        '''
        counts = collections.defaultdict(int)
        for layr in self.layers.values():
            layrcounts = await layr.getFormCounts()
            for name, valu in layrcounts.items():
                counts[name] += valu
        return counts

    def onTagAdd(self, name, func):
        '''
        Register a callback for tag addition.

        Args:
            name (str): The name of the tag or tag glob.
            func (function): The callback func(node, tagname, tagval).

        '''
        # TODO allow name wild cards
        if '*' in name:
            self.ontagaddglobs.add(name, func)
        else:
            self.ontagadds[name].append(func)

    def offTagAdd(self, name, func):
        '''
        Unregister a callback for tag addition.

        Args:
            name (str): The name of the tag or tag glob.
            func (function): The callback func(node, tagname, tagval).

        '''
        if '*' in name:
            self.ontagaddglobs.rem(name, func)
            return

        cblist = self.ontagadds.get(name)
        if cblist is None:
            return
        try:
            cblist.remove(func)
        except ValueError:
            pass

    def onTagDel(self, name, func):
        '''
        Register a callback for tag deletion.

        Args:
            name (str): The name of the tag or tag glob.
            func (function): The callback func(node, tagname, tagval).

        '''
        if '*' in name:
            self.ontagdelglobs.add(name, func)
        else:
            self.ontagdels[name].append(func)

    def offTagDel(self, name, func):
        '''
        Unregister a callback for tag deletion.

        Args:
            name (str): The name of the tag or tag glob.
            func (function): The callback func(node, tagname, tagval).

        '''
        if '*' in name:
            self.ontagdelglobs.rem(name, func)
            return

        cblist = self.ontagdels.get(name)
        if cblist is None:
            return
        try:
            cblist.remove(func)
        except ValueError:
            pass

    def addRuntLift(self, prop, func):
        '''
        Register a runt lift helper for a given prop.

        Args:
            prop (str): Full property name for the prop to register the helper for.
            func:

        Returns:
            None: None.
        '''
        self._runtLiftFuncs[prop] = func

    async def runRuntLift(self, full, valu=None, cmpr=None):
        '''
        Execute a runt lift function.

        Args:
            full (str): Property to lift by.
            valu:
            cmpr:

        Returns:
            bytes, list: Yields bytes, list tuples where the list contains a series of
                key/value pairs which are used to construct a Node object.

        '''
        func = self._runtLiftFuncs.get(full)
        if func is not None:
            async for pode in func(full, valu, cmpr):
                yield pode

    def addRuntPropSet(self, full, func):
        '''
        Register a prop set helper for a runt form
        '''
        self._runtPropSetFuncs[full] = func

    async def runRuntPropSet(self, node, prop, valu):
        func = self._runtPropSetFuncs.get(prop.full)
        if func is None:
            raise s_exc.IsRuntForm(mesg='No prop:set func set for runt property.',
                                   prop=prop.full, valu=valu, ndef=node.ndef)
        ret = await s_coro.ornot(func, node, prop, valu)
        return ret

    def addRuntPropDel(self, full, func):
        '''
        Register a prop set helper for a runt form
        '''
        self._runtPropDelFuncs[full] = func

    async def runRuntPropDel(self, node, prop):
        func = self._runtPropDelFuncs.get(prop.full)
        if func is None:
            raise s_exc.IsRuntForm(mesg='No prop:del func set for runt property.',
                                   prop=prop.full, ndef=node.ndef)
        ret = await s_coro.ornot(func, node, prop)
        return ret

    async def _checkLayerModels(self):
        mrev = s_modelrev.ModelRev(self)
        await mrev.revCoreLayers()

    # FIXME: mirror split horizon problem with addLayer, addView
    async def _initCoreViews(self):

        defiden = self.cellinfo.get('defaultview')

        for iden, node in await self.hive.open(('cortex', 'views')):
            view = await s_view.View.anit(self, node)
            self.views[iden] = view
            if iden == defiden:
                self.view = view

        # if we have no views, we are initializing.  Add a default main view and layer.
        if not self.views:
            layr = await self.addLayer()
            vdef = {
                'layers': (layr.iden,),
                'worldreadable': True,
            }
            view = await self.addView(vdef)
            await self.cellinfo.set('defaultview', view.iden)
            self.view = view

    async def _migrateViewsLayers(self):
        '''
        Move directories and idens to current scheme where cortex, views, and layers all have unique idens

        Note:
            This changes directories and hive data, not existing View or Layer objects

        TODO:  due to our migration policy, remove in 0.3.0

        '''
        defiden = self.cellinfo.get('defaultview')
        if defiden is not None:
            # No need for migration; we're up-to-date
            return

        oldlayriden = self.iden
        newlayriden = s_common.guid()

        oldviewiden = self.iden
        newviewiden = s_common.guid()

        if not await self.hive.exists(('cortex', 'views', oldviewiden)):
            # No view info present; this is a fresh cortex
            return

        await self.hive.rename(('cortex', 'views', oldviewiden), ('cortex', 'views', newviewiden))
        logger.info('Migrated view from duplicate iden %s to new iden %s', oldviewiden, newviewiden)

        # Move view/layer metadata
        await self.hive.rename(('cortex', 'layers', oldlayriden), ('cortex', 'layers', newlayriden))
        logger.info('Migrated layer from duplicate iden %s to new iden %s', oldlayriden, newlayriden)

        # Move layer data
        oldpath = os.path.join(self.dirn, 'layers', oldlayriden)
        newpath = os.path.join(self.dirn, 'layers', newlayriden)
        os.rename(oldpath, newpath)

        # Replace all views' references to old layer iden with new layer iden
        node = await self.hive.open(('cortex', 'views'))
        for iden, viewnode in node:
            info = await viewnode.dict()
            layers = info.get('layers')
            newlayers = [newlayriden if layr == oldlayriden else layr for layr in layers]
            await info.set('layers', newlayers)

        await self.cellinfo.set('defaultview', newviewiden)

    async def _migrateLayerOffset(self):
        '''
        In case this is a downstream mirror, move the offsets for the old layr iden to the new layr iden

        Precondition:
            Layers and Views are initialized.  Mirror logic has not started.

        TODO:  due to our migration policy, remove in 0.3.0
        '''
        oldlayriden = self.iden
        layr = self.getLayer()
        newlayriden = layr.iden

        offs = await layr.getOffset(oldlayriden)
        if offs == 0:
            return

        await layr.setOffset(newlayriden, offs)
        await layr.delOffset(oldlayriden)

    async def getOffset(self, iden):
        '''
        '''
        return self.offs.get(iden)

    async def setOffset(self, iden, offs):
        '''
        '''
        # TODO NEXUS
        return self.offs.set(iden, offs)

    async def delOffset(self, iden):
        '''
        '''
        # TODO NEXUS
        return self.offs.delete(iden)

    async def addView(self, vdef):

        vdef.setdefault('iden', s_common.guid())
        vdef.setdefault('parent', None)
        vdef.setdefault('worldreadable', False)
        vdef.setdefault('creator', self.auth.rootuser.iden)

        creator = vdef.get('creator')
        user = await self.auth.reqUser(creator)

        # this should not get saved
        worldread = vdef.pop('worldreadable')

        view = await self._push('view:add', vdef)

        await user.setAdmin(True, gateiden=view.iden)

        if worldread:
            role = await self.auth.getRoleByName('all')
            await role.addRule((True, ('view', 'read')), gateiden=view.iden)

        return view

    @s_nexus.Pusher.onPush('view:add')
    async def _addView(self, vdef):

        iden = vdef.get('iden')
        node = await self.hive.open(('cortex', 'views', iden))

        info = await node.dict()
        for name, valu in vdef.items():
            await info.set(name, valu)

        view = await s_view.View.anit(self, node)
        self.views[iden] = view

        await self.auth.addAuthGate(iden, 'view')

        await self.bumpSpawnPool()
        return view

    @s_nexus.Pusher.onPushAuto('view:del')
    async def delView(self, iden):
        '''
        Delete a cortex view by iden.

        Note:
            This does not delete any of the view's layers
        '''
        if iden == self.view.iden:
            raise s_exc.SynErr(mesg='Cannot delete the main view')

        for view in self.views.values():
            if view.parent is not None and view.parent.iden == iden:
                raise s_exc.SynErr(mesg='Cannot delete a view that has children')

        view = self.views.pop(iden, None)
        if view is None:
            # TODO probably need a retn convention here...
            raise s_exc.NoSuchView(iden=iden)

        #if view.parent is not None:
            #await self.delLayer(view.layers[0].iden)
            #await view.layers[0].delete()

        await self.hive.pop(('cortex', 'views', iden))
        await view.delete()

        await self.auth.delAuthGate(iden)

        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('layer:del')
    async def delLayer(self, iden):
        layr = self.layers.get(iden, None)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        for view in self.views.values():
            if layr in view.layers:
                raise s_exc.LayerInUse(iden=iden)

        del self.layers[iden]

        await self.auth.delAuthGate(iden)

        await self.hive.pop(('cortex', 'layers', iden))

        await layr.delete()
        await self.bumpSpawnPool()

    async def setViewLayers(self, layers, iden=None):
        '''
        Args:
            layers ([str]): A top-down list of of layer guids
            iden (str): The view iden (defaults to default view).
        '''
        view = self.getView(iden)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        await view.setLayers(layers)
        await self.bumpSpawnPool()

    def getLayer(self, iden=None):
        '''
        Get a Layer object.

        Args:
            iden (str): The layer iden to retrieve.

        Returns:
            Layer: A Layer object.
        '''
        if iden is None:
            return self.view.layers[0]

        # For backwards compatibility, resolve references to old layer iden == cortex.iden to the main layer
        # TODO:  due to our migration policy, remove in 0.3.x
        if iden == self.iden:
            return self.view.layers[0]

        return self.layers.get(iden)

    def getView(self, iden=None):
        '''
        Get a View object.

        Args:
            iden (str): The View iden to retrieve.

        Returns:
            View: A View object.
        '''
        if iden is None:
            return self.view

        # For backwards compatibility, resolve references to old view iden == cortex.iden to the main view
        # TODO:  due to our migration policy, remove in 0.3.x
        if iden == self.iden:
            return self.view

        return self.views.get(iden)

    async def addLayer(self, ldef=None):
        '''
        Add a Layer to the cortex.
        '''
        ldef = ldef or {}

        ldef.setdefault('iden', s_common.guid())
        ldef.setdefault('conf', {})
        ldef.setdefault('stor', self.defstor.iden)
        ldef.setdefault('creator', self.auth.rootuser.iden)

        # FIXME: why do we have two levels of conf?
        conf = ldef.get('conf')
        conf.setdefault('lockmemory', self.conf.get('layers:lockmemory'))

        return await self._push('layer:add', ldef)

    @s_nexus.Pusher.onPush('layer:add')
    async def _addLayer(self, ldef):

        stor = ldef.get('stor')

        layrstor = self.storage.get(stor)
        if layrstor is None:
            raise s_exc.NoSuchIden(iden=stor)

        conf = ldef.get('conf')
        await layrstor.reqValidLayrConf(conf)

        creator = ldef.get('creator')
        await self.auth.reqUser(creator)

        iden = ldef.get('iden')

        creator = ldef.get('creator')

        user = await self.auth.reqUser(creator)

        node = await self.hive.open(('cortex', 'layers', iden))

        layrinfo = await node.dict()
        for name, valu in ldef.items():
            await layrinfo.set(name, valu)

        layr = await self._initLayr(layrinfo)
        await user.setAdmin(True, gateiden=iden)

        # forward wind the new layer to the current model version
        await layr.setModelVers(s_modelrev.maxvers)

        return layr

    async def _initLayr(self, layrinfo):
        '''
        Instantiate a Layer() instance via the provided layer info HiveDict.
        '''
        stor = layrinfo.get('stor')
        layrstor = self.storage.get(stor)

        if layrstor is None:
            raise s_exc.SynErr('missing layer storage')

        layr = await layrstor.initLayr(layrinfo, nexsroot=self.nexsroot)

        self.layers[layr.iden] = layr

        await self.auth.addAuthGate(layr.iden, 'layer')

        await self.bumpSpawnPool()

        return layr

    async def joinTeleLayer(self, url, indx=None):
        '''
        Convenience function to join a remote telepath layer
        into this cortex and default view.
        '''
        info = {
            'type': 'remote',
            'creator': 'root',
            'config': {
                'url': url
            }
        }

        layr = await self.addLayer(**info)
        await self.view.addLayer(layr, indx=indx)
        # FIXME: unchange this; change dist methods can return heavy objects
        return layr.iden

    async def _initCoreLayers(self):

        node = await self.hive.open(('cortex', 'layers'))

        # TODO eventually hold this and watch for changes
        for iden, node in node:
            layrinfo = await node.dict()
            await self._initLayr(layrinfo)

    def addStormCmd(self, ctor):
        '''
        Add a synapse.lib.storm.Cmd class to the cortex.
        '''
        if not s_grammar.isCmdName(ctor.name):
            raise s_exc.BadCmdName(name=ctor.name)

        self.stormcmds[ctor.name] = ctor
        self.storm_cmd_ctors[ctor.name] = ctor

    async def addStormDmon(self, ddef):
        '''
        Add a storm dmon task.
        '''
        iden = s_common.guid()
        ddef['iden'] = iden
        return await self._push('storm:dmon:add', ddef)

    @s_nexus.Pusher.onPush('storm:dmon:add')
    async def _onAddStormDmon(self, ddef):
        iden = ddef['iden']

        if ddef.get('user') is None:
            user = await self.auth.getUserByName('root')
            ddef['user'] = user.iden

        dmon = await self.runStormDmon(iden, ddef)
        await self.stormdmonhive.set(iden, ddef)
        return dmon

    @s_nexus.Pusher.onPushAuto('storm:dmon:del')
    async def delStormDmon(self, iden):
        '''
        Stop and remove a storm dmon.
        '''
        ddef = await self.stormdmonhive.pop(iden)
        if ddef is None:
            mesg = f'No storm daemon exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        dmon = self.stormdmons.pop(iden, None)
        if dmon is not None:
            await dmon.fini()

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    @s_nexus.Pusher.onPushAuto('storm:dmon:run')
    async def runStormDmon(self, iden, ddef):

        # validate ddef before firing task
        uidn = ddef.get('user')
        if uidn is None:
            mesg = 'Storm daemon definition requires "user".'
            raise s_exc.NeedConfValu(mesg=mesg)
        # FIXME:  no such call
        await self.auth.reqUser(uidn)

        # raises if parser failure
        self.getStormQuery(ddef.get('storm'))

        dmon = await s_storm.StormDmon.anit(self, iden, ddef)

        self.stormdmons[iden] = dmon

        def fini():
            self.stormdmons.pop(iden, None)

        dmon.onfini(fini)
        await dmon.run()

        return dmon

    async def getStormDmon(self, iden):
        return self.stormdmons.get(iden)

    async def getStormDmons(self):
        return list(self.stormdmons.values())

    def addStormLib(self, path, ctor):

        root = self.libroot
        # (name, {kids}, {funcs})

        for name in path:
            step = root[1].get(name)
            if step is None:
                step = (name, {}, {})
                root[1][name] = step
            root = step

        root[2]['ctor'] = ctor

    def getStormLib(self, path):
        root = self.libroot
        for name in path:
            step = root[1].get(name)
            if step is None:
                return None
            root = step
        return root

    def getStormCmds(self):
        return list(self.stormcmds.items())

# FIXME: change these to daemons
#    def _initPushLoop(self):
#
#        if self.conf.get('splice:sync') is None:
#            return
#
#        self.schedCoro(self._runPushLoop())
#
#    async def _runPushLoop(self):
#
#        url = self.conf.get('splice:sync')
#
#        iden = self.getCellIden()
#
#        logger.info('sync loop init: %s', url)
#
#        while not self.isfini:
#            timeout = 1
#            try:
#
#                url = self.conf.get('splice:sync')
#
#                async with await s_telepath.openurl(url) as core:
#
#                    # use our iden as the feed iden
#                    offs = await core.getFeedOffs(iden)
#
#                    while not self.isfini:
#                        layer = self.getLayer()
#
#                        items = [x async for x in layer.splices(offs, 10000)]
#
#                        if not items:
#                            await self.waitfini(timeout=1)
#                            continue
#
#                        size = len(items)
#                        indx = (await layer.stat())['splicelog_indx']
#
#                        perc = float(offs) / float(indx) * 100.0
#
#                        logger.info('splice push: %d %d/%d (%.4f%%)', size, offs, indx, perc)
#
#                        offs = await core.addFeedData('syn.splice', items, seqn=(iden, offs))
#                        await self.fire('core:splice:sync:sent')
#
#            except asyncio.CancelledError:
#                break
#
#            except Exception as e:  # pragma: no cover
#                if isinstance(e, OSError):
#                    timeout = 60
#
#                logger.exception('sync error')
#                await self.waitfini(timeout)
#
#    def _initCryoLoop(self):
#
#        tankurl = self.conf.get('splice:cryotank')
#        if tankurl is None:
#            return
#
#        self.schedCoro(self._runCryoLoop())
#
#    def _initFeedLoops(self):
#        '''
#        feeds:
#            - cryotank: tcp://cryo.vertex.link/cryo00/tank01
#              xtype: syn.splice
#        '''
#        feeds = self.conf.get('feeds', ())
#        if not feeds:
#            return
#
#        for feed in feeds:
#
#            # do some validation before we fire tasks...
#            typename = feed.get('type')
#            if self.getFeedFunc(typename) is None:
#                raise s_exc.NoSuchType(name=typename)
#
#            self.schedCoro(self._runFeedLoop(feed))
#
#    async def _runFeedLoop(self, feed):
#
#        url = feed.get('cryotank')
#        typename = feed.get('type')
#        fsize = feed.get('size', 1000)
#
#        logger.info('feed loop init: %s @ %s', typename, url)
#
#        while not self.isfini:
#            timeout = 1
#            try:
#
#                url = feed.get('cryotank')
#
#                async with await s_telepath.openurl(url) as tank:
#
#                    layer = self.getLayer()
#
#                    iden = await tank.iden()
#
#                    offs = await layer.getOffset(iden)
#
#                    while not self.isfini:
#
#                        items = [item async for item in tank.slice(offs, fsize)]
#                        if not items:
#                            await self.waitfini(timeout=2)
#                            continue
#
#                        datas = [i[1] for i in items]
#
#                        offs = await self.addFeedData(typename, datas, seqn=(iden, offs))
#                        await self.fire('core:feed:loop')
#                        logger.debug('Processed [%s] records with [%s]',
#                                     len(datas), typename)
#
#            except asyncio.CancelledError:
#                break
#
#            except Exception as e:  # pragma: no cover
#                if isinstance(e, OSError):
#                    timeout = 60
#                logger.exception('feed error')
#                await self.waitfini(timeout)
#
#    async def _runCryoLoop(self):
#
#        online = False
#        tankurl = self.conf.get('splice:cryotank')
#
#        # TODO:  what to do when write layer changes?
#
#        # push splices for our main layer
#        layr = self.getLayer()
#
#        while not self.isfini:
#            timeout = 2
#            try:
#
#                async with await s_telepath.openurl(tankurl) as tank:
#
#                    if not online:
#                        online = True
#                        logger.info('splice cryotank: online')
#
#                    offs = await tank.offset(self.iden)
#
#                    while not self.isfini:
#
#                        items = [item async for item in layr.splices(offs, 10000)]
#
#                        if not len(items):
#                            layr.spliced.clear()
#                            await s_coro.event_wait(layr.spliced, timeout=1)
#                            continue
#
#                        logger.info('tanking splices: %d', len(items))
#
#                        offs = await tank.puts(items, seqn=(self.iden, offs))
#                        await self.fire('core:splice:cryotank:sent')
#
#            except asyncio.CancelledError:  # pragma: no cover
#                break
#
#            except Exception as e:  # pragma: no cover
#                if isinstance(e, OSError):
#                    timeout = 60
#                online = False
#                logger.exception('splice cryotank offline')
#
#                await self.waitfini(timeout)

    def setFeedFunc(self, name, func):
        '''
        Set a data ingest function.

        def func(snap, items):
            loaditems...
        '''
        self.feedfuncs[name] = func

    def getFeedFunc(self, name):
        '''
        Get a data ingest function.
        '''
        return self.feedfuncs.get(name)

    async def getFeedFuncs(self):
        ret = []
        for name, ctor in self.feedfuncs.items():
            # TODO - Future support for feed functions defined via Storm.
            doc = getattr(ctor, '__doc__')
            if doc is None:
                doc = 'No feed docstring'
            doc = doc.strip()
            desc = doc.split('\n')[0]
            ret.append({'name': name,
                        'desc': desc,
                        'fulldoc': doc,
                        })
        return tuple(ret)

    async def _addSynNodes(self, snap, items):
        '''
        Add nodes to the Cortex via the packed node format.
        '''
        async for node in snap.addNodes(items):
            yield node

    async def _addSynSplice(self, snap, items):

        for item in items:
            func = self.splicers.get(item[0])

            if func is None:
                await snap.warn(f'no such splice: {item!r}')
                continue

            try:
                await func(snap, item)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception('splice error')
                await snap.warn(f'splice error: {e}')

    async def _onFeedNodeAdd(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        if ndef is None:
            await snap.warn(f'Invalid Splice: {mesg!r}')
            return

        await snap.addNode(*ndef)

    async def _onFeedNodeDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        node = await snap.getNodeByNdef(ndef)
        if node is None:
            return

        await node.delete()

    async def _onFeedPropSet(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        name = mesg[1].get('prop')
        valu = mesg[1].get('valu')

        node = await snap.getNodeByNdef(ndef)
        if node is None:
            return

        await node.set(name, valu)

    async def _onFeedPropDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        name = mesg[1].get('prop')

        node = await snap.getNodeByNdef(ndef)
        if node is None:
            return

        await node.pop(name)

    async def _onFeedTagAdd(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        tag = mesg[1].get('tag')
        valu = mesg[1].get('valu')

        node = await snap.getNodeByNdef(ndef)
        if node is None:
            return

        await node.addTag(tag, valu=valu)

    async def _onFeedTagDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        tag = mesg[1].get('tag')

        node = await snap.getNodeByNdef(ndef)
        if node is None:
            return

        await node.delTag(tag)

    async def _onFeedTagPropSet(self, snap, mesg):

        tag = mesg[1].get('tag')
        prop = mesg[1].get('prop')
        ndef = mesg[1].get('ndef')
        valu = mesg[1].get('valu')

        node = await snap.getNodeByNdef(ndef)
        if node is not None:
            await node.setTagProp(tag, prop, valu)

    async def _onFeedTagPropDel(self, snap, mesg):
        tag = mesg[1].get('tag')
        prop = mesg[1].get('prop')
        ndef = mesg[1].get('ndef')

        node = await snap.getNodeByNdef(ndef)
        if node is not None:
            await node.delTagProp(tag, prop)

    async def _addSynIngest(self, snap, items):

        for item in items:
            try:
                pnodes = self._getSynIngestNodes(item)
                logger.info('Made [%s] nodes.', len(pnodes))
                async for node in snap.addNodes(pnodes):
                    yield node
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('Failed to process ingest [%r]', item)
                continue

    def _getSynIngestNodes(self, item):
        '''
        Get a list of packed nodes from a ingest definition.
        '''
        pnodes = []
        seen = item.get('seen')
        # Track all the ndefs we make so we can make sources
        ndefs = []

        # Make the form nodes
        tags = item.get('tags', {})
        forms = item.get('forms', {})
        for form, valus in forms.items():
            for valu in valus:
                ndef = [form, valu]
                ndefs.append(ndef)
                obj = [ndef, {'tags': tags}]
                if seen:
                    obj[1]['props'] = {'.seen': seen}
                pnodes.append(obj)

        # Make the packed nodes
        nodes = item.get('nodes', ())
        for pnode in nodes:
            ndefs.append(pnode[0])
            pnode[1].setdefault('tags', {})
            for tag, valu in tags.items():
                # Tag in the packed node has a higher predecence
                # than the tag in the whole ingest set of data.
                pnode[1]['tags'].setdefault(tag, valu)
            if seen:
                pnode[1].setdefault('props', {})
                pnode[1]['props'].setdefault('.seen', seen)
            pnodes.append(pnode)

        # Make edges
        for srcdef, etyp, destndefs in item.get('edges', ()):
            for destndef in destndefs:
                ndef = [etyp, [srcdef, destndef]]
                ndefs.append(ndef)
                obj = [ndef, {}]
                if seen:
                    obj[1]['props'] = {'.seen': seen}
                if tags:
                    obj[1]['tags'] = tags.copy()
                pnodes.append(obj)

        # Make time based edges
        for srcdef, etyp, destndefs in item.get('time:edges', ()):
            for destndef, time in destndefs:
                ndef = [etyp, [srcdef, destndef, time]]
                ndefs.append(ndef)
                obj = [ndef, {}]
                if seen:
                    obj[1]['props'] = {'.seen': seen}
                if tags:
                    obj[1]['tags'] = tags.copy()
                pnodes.append(obj)

        # Make the source node and links
        source = item.get('source')
        if source:
            # Base object
            obj = [['meta:source', source], {}]
            pnodes.append(obj)

            # Subsequent links
            for ndef in ndefs:
                obj = [['meta:seen', (source, ndef)],
                       {'props': {'.seen': seen}}]
                pnodes.append(obj)
        return pnodes

    def getCoreMod(self, name):
        return self.modules.get(name)

    def getCoreMods(self):
        ret = []
        for modname, mod in self.modules.items():
            ret.append((modname, mod.conf))
        return ret

    def _viewFromOpts(self, opts):
        if opts is None:
            return self.view

        viewiden = opts.get('view')
        view = self.getView(viewiden)
        if view is None:
            raise s_exc.NoSuchView(iden=viewiden)

        return view

    @s_coro.genrhelp
    async def eval(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        view = self._viewFromOpts(opts)

        async for node in view.eval(text, opts, user):
            yield node

    @s_coro.genrhelp
    async def storm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield (node, path) tuples.
        Yields:
            (Node, Path) tuples
        '''
        view = self._viewFromOpts(opts)

        async for mesg in view.storm(text, opts, user):
            yield mesg

    async def nodes(self, text, opts=None, user=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        async def nodes():
            return [n async for n in self.eval(text, opts=opts, user=user)]
        task = self.schedCoro(nodes())
        return await task

    @s_coro.genrhelp
    async def streamstorm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield result messages.

        Yields:
            ((str,dict)): Storm messages.
        '''
        view = self._viewFromOpts(opts)

        async for mesg in view.streamstorm(text, opts, user):
            yield mesg

    @s_coro.genrhelp
    async def iterStormPodes(self, text, opts=None, user=None):
        if user is None:
            user = await self.auth.getUserByName('root')

        view = self._viewFromOpts(opts)

        info = {'query': text}
        if opts is not None:
            info['opts'] = opts

        await self.boss.promote('storm', user=user, info=info)
        async with await self.snap(user=user, view=view) as snap:
            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                yield pode

    @s_cache.memoize(size=10000)
    def getStormQuery(self, text):
        '''
        Parse storm query text and return a Query object.
        '''
        query = copy.deepcopy(s_grammar.parseQuery(text))
        query.init(self)
        return query

    def _logStormQuery(self, text, user):
        '''
        Log a storm query.
        '''
        if self.conf.get('storm:log'):
            lvl = self.conf.get('storm:log:level')
            logger.log(lvl, 'Executing storm query {%s} as [%s]', text, user.name)

    async def getNodeByNdef(self, ndef, view=None):
        '''
        Return a single Node() instance by (form,valu) tuple.
        '''
        name, valu = ndef

        form = self.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        norm, info = form.type.norm(valu)

        buid = s_common.buid((form.name, norm))

        async with await self.snap(view=view) as snap:
            return await snap.getNodeByBuid(buid)

    def getCoreInfo(self):
        return {
            'version': synapse.version,
            'modeldef': self.model.getModelDef(),
            'stormcmds': {cmd: {} for cmd in self.stormcmds.keys()},
        }

    async def addNodes(self, nodedefs, view=None):
        '''
        Quickly add/modify a list of nodes from node definition tuples.
        This API is the simplest/fastest way to add nodes, set node props,
        and add tags to nodes remotely.

        Args:

            nodedefs (list): A list of node definition tuples. See below.

        A node definition tuple is defined as:

            ( (form, valu), {'props':{}, 'tags':{})

        The "props" or "tags" keys may be omitted.

        '''
        async with await self.snap(view=view) as snap:
            snap.strict = False
            async for node in snap.addNodes(nodedefs):
                yield node

    async def addFeedData(self, name, items, seqn=None):
        '''
        Add data using a feed/parser function.

        Args:
            name (str): The name of the feed record format.
            items (list): A list of items to ingest.
            seqn ((str,int)): An (iden, offs) tuple for this feed chunk.

        Returns:
            (int): The next expected offset (or None) if seqn is None.
        '''
        async with await self.snap() as snap:
            snap.strict = False
            return await snap.addFeedData(name, items, seqn=seqn)

    # async def getFeedOffs(self, iden):
    #    return await self.getLayer().getOffset(iden)

    # async def setFeedOffs(self, iden, offs):
    #    if offs < 0:
        #    mesg = 'Offset must be >= 0.'
        #    raise s_exc.BadConfValu(mesg=mesg, offs=offs, iden=iden)

    #    return await self.getLayer().setOffset(iden, offs)

    async def snap(self, user=None, view=None):
        '''
        Return a transaction object for the default view.

        Args:
            user (str): The user to get the snap for.
            view (View): View object to use when making the snap.

        Notes:
            This must be used as an asynchronous context manager.

        Returns:
            s_snap.Snap: A Snap object for the view.
        '''

        if view is None:
            view = self.view

        if user is None:
            user = await self.auth.getUserByName('root')

        snap = await view.snap(user)

        return snap

    async def loadCoreModule(self, ctor, conf=None):
        '''
        Load a single cortex module with the given ctor and conf.

        Args:
            ctor (str): The python module class path
            conf (dict):Config dictionary for the module
        '''
        if conf is None:
            conf = {}

        modu = self._loadCoreModule(ctor, conf=conf)

        try:
            await s_coro.ornot(modu.preCoreModule)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:
            logger.exception(f'module preCoreModule failed: {ctor}')
            self.modules.pop(ctor, None)
            return

        mdefs = modu.getModelDefs()
        self.model.addDataModels(mdefs)

        cmds = modu.getStormCmds()
        [self.addStormCmd(c) for c in cmds]

        try:
            await s_coro.ornot(modu.initCoreModule)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:
            logger.exception(f'module initCoreModule failed: {ctor}')
            self.modules.pop(ctor, None)
            return

        await self.fire('core:module:load', module=ctor)

        return modu

    async def _loadCoreMods(self, ctors):

        mods = []

        cmds = []
        mdefs = []

        for ctor in ctors:

            conf = None

            # allow module entry to be (ctor, conf) tuple
            if isinstance(ctor, (list, tuple)):
                ctor, conf = ctor

            modu = self._loadCoreModule(ctor, conf=conf)
            if modu is None:
                continue

            mods.append(modu)

            try:
                await s_coro.ornot(modu.preCoreModule)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception:
                logger.exception(f'module preCoreModule failed: {ctor}')
                self.modules.pop(ctor, None)
                continue

            cmds.extend(modu.getStormCmds())
            mdefs.extend(modu.getModelDefs())

        self.model.addDataModels(mdefs)
        [self.addStormCmd(c) for c in cmds]

    async def _initCoreMods(self):

        for ctor, modu in list(self.modules.items()):

            try:
                await s_coro.ornot(modu.initCoreModule)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception:
                logger.exception(f'module initCoreModule failed: {ctor}')
                self.modules.pop(ctor, None)

    def _loadCoreModule(self, ctor, conf=None):

        if ctor in self.modules:
            raise s_exc.ModAlreadyLoaded(mesg=f'{ctor} already loaded')
        try:
            modu = s_dyndeps.tryDynFunc(ctor, self, conf=conf)
            self.modules[ctor] = modu
            return modu

        except Exception:
            logger.exception('mod load fail: %s' % (ctor,))
            return None

    async def stat(self):
        stats = {
            'iden': self.iden,
            'layer': await self.getLayer().stat(),
            'formcounts': await self.getFormCounts(),
        }
        return stats

    async def getPropNorm(self, prop, valu):
        '''
        Get the normalized property value based on the Cortex data model.

        Args:
            prop (str): The property to normalize.
            valu: The value to normalize.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchProp: If the prop does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        pobj = self.model.prop(prop)
        if pobj is None:
            raise s_exc.NoSuchProp(mesg=f'The property {prop} does not exist.',
                                   prop=prop)
        norm, info = pobj.type.norm(valu)
        return norm, info

    async def getTypeNorm(self, name, valu):
        '''
        Get the normalized type value based on the Cortex data model.

        Args:
            name (str): The type to normalize.
            valu: The value to normalize.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchType: If the type does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        tobj = self.model.type(name)
        if tobj is None:
            raise s_exc.NoSuchType(mesg=f'The type {name} does not exist.',
                                   name=name)
        norm, info = tobj.norm(valu)
        return norm, info

    @staticmethod
    def _convert_reqdict(reqdict):
        return {s_agenda.TimeUnit.fromString(k): v for (k, v) in reqdict.items()}

    async def addCronJob(self, user, query, reqs, incunit=None, incval=1):
        '''
        Add a cron job to the cortex.  Convenience wrapper around agenda.add

        A cron job is a persistently-stored item that causes storm queries to be run in the future.  The specification
        for the times that the queries run can be one-shot or recurring.

        Args:
            query (str):  The storm query to execute in the future
            reqs (Union[Dict[str, Union[int, List[int]]], List[Dict[...]]]):
                Either a dict of the fixed time fields or a list of such dicts.  The keys are in the set ('year',
                'month', 'dayofmonth', 'dayofweek', 'hour', 'minute'.  The values must be positive integers, except for
                the key of 'dayofmonth' in which it may also be a negative integer which represents the number of days
                from the end of the month with -1 representing the last day of the month.  All values may also be lists
                of valid values.
            incunit (Optional[str]):
                A member of the same set as above, with an additional member 'day'.  If is None (default), then the
                appointment is one-shot and will not recur.
            incval (Union[int, List[int]):
                A integer or a list of integers of the number of units

        Returns (bytes):
            An iden that can be used to later modify, query, and delete the job.

        Notes:
            reqs must have fields present or incunit must not be None (or both)
            The incunit if not None it must be larger in unit size than all the keys in all reqs elements.
        '''
        try:
            if incunit is not None:
                if isinstance(incunit, (list, tuple)):
                    incunit = [s_agenda.TimeUnit.fromString(i) for i in incunit]
                else:
                    incunit = s_agenda.TimeUnit.fromString(incunit)
            if isinstance(reqs, Mapping):
                newreqs = self._convert_reqdict(reqs)
            else:
                newreqs = [self._convert_reqdict(req) for req in reqs]
        except KeyError:
            raise s_exc.BadConfValu('Unrecognized time unit')

        return await self._push('cron:add', user.iden, s_common.guid(), query, newreqs, incunit, incval)

    @s_nexus.Pusher.onPush('cron:add')
    async def _onAddCronJob(self, useriden, croniden, query, newreqs, incunit=None, incval=1):

        return await self.agenda.add(useriden, croniden, query, newreqs, incunit, incval)

    @s_nexus.Pusher.onPushAuto('cron:del')
    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        await self.cell.agenda.delete(iden)

    @s_nexus.Pusher.onPushAuto('cron:mod')
    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.cell.agenda.mod(iden, query)

    @s_nexus.Pusher.onPushAuto('cron:enable')
    async def enableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.cell.agenda.enable(iden)

    @s_nexus.Pusher.onPushAuto('cron:disable')
    async def disableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.cell.agenda.disable(iden)

@contextlib.asynccontextmanager
async def getTempCortex(mods=None):
    '''
    Get a proxy to a cortex backed by a temporary directory.

    Args:
        mods (list): A list of modules which are loaded into the cortex.

    Notes:
        The cortex and temporary directory are town down on exit.
        This should only be called from synchronous code.

    Returns:
        Proxy to the cortex.
    '''
    with s_common.getTempDir() as dirn:

        async with await Cortex.anit(dirn) as core:
            if mods:
                for mod in mods:
                    await core.loadCoreModule(mod)
            async with core.getLocalProxy() as prox:
                yield prox
