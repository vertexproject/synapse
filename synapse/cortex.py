import os
import asyncio
import logging
import itertools
import contextlib
import collections

from collections.abc import Mapping

import synapse
import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.snap as s_snap
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.storm as s_storm
import synapse.lib.agenda as s_agenda
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.httpapi as s_httpapi
import synapse.lib.modules as s_modules
import synapse.lib.trigger as s_trigger
import synapse.lib.modelrev as s_modelrev
import synapse.lib.lmdblayer as s_lmdblayer
import synapse.lib.stormhttp as s_stormhttp
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.remotelayer as s_remotelayer

logger = logging.getLogger(__name__)

'''
A Cortex implements the synapse hypergraph object.
'''

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

        self.borked = None

        self.info = await node.dict()
        self.info.setdefault('owner', 'root')
        self.info.setdefault('layers', ())

        self.layers = []

        for iden in self.info.get('layers'):

            layr = core.layers.get(iden)

            if layr is None:
                self.borked = iden
                logger.warning('view %r has missing layer %r' % (self.iden, iden))
                continue

            if not self.layers and layr.readonly:
                self.borked = iden
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {iden} must not be read-only')

            self.layers.append(layr)

    async def snap(self, user):

        if self.borked is not None:
            raise s_exc.NoSuchLayer(iden=self.borked)

        return await s_snap.Snap.anit(self.core, self.layers, user)

    def pack(self):
        return {
            'iden': self.iden,
            'owner': self.info.get('owner'),
            'layers': self.info.get('layers'),
        }

    async def addLayer(self, layr, indx=None):
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
        layrs = []

        for iden in layers:
            layr = self.core.layers.get(iden)
            if layr is None:
                raise s_exc.NoSuchLayer(iden=iden)
            if not layrs and layr.readonly:
                raise s_exc.ReadOnlyLayer(mesg=f'First layer {layr.iden} must not be read-only')

            layrs.append(layr)

        self.borked = None
        self.layers = layrs

        await self.info.set('layers', layers)

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

    async def getNodesBy(self, full, valu, cmpr='='):
        '''
        Yield Node.pack() tuples which match the query.
        '''
        async for node in self.cell.getNodesBy(full, valu, cmpr=cmpr):
            yield node.pack()

    def allowed(self, *path):
        return self.user.allowed(path)

    def _reqUserAllowed(self, *path):
        if not self.allowed(*path):
            perm = '.'.join(path)
            raise s_exc.AuthDeny(perm=perm, user=self.user.name)

    async def getModelDict(self):
        '''
        Return a dictionary which describes the data model.

        Returns:
            (dict): A model description dictionary.
        '''
        return await self.cell.getModelDict()

    def axon(self):
        '''
        '''
        return s_axon.AxonApi.anit(self.cell.axon, self.link, self.user)

    def getCoreInfo(self):
        '''
        Return static generic information about the cortex including model definition
        '''
        return self.cell.getCoreInfo()

    async def addTrigger(self, condition, query, info):
        '''
        Adds a trigger to the cortex
        '''
        iden = self.cell.triggers.add(self.user.iden, condition, query, info=info)
        return iden

    def _trig_auth_check(self, useriden):
        ''' Check that, as a non-admin, may only manipulate resources created by you. '''
        if not self.user.admin and useriden != self.user.iden:
            raise s_exc.AuthDeny(user=self.user.name, mesg='As non-admin, may only manipulate triggers created by you')

    async def delTrigger(self, iden):
        '''
        Deletes a trigger from the cortex
        '''
        trig = self.cell.triggers.get(iden)
        self._trig_auth_check(trig.get('useriden'))
        self.cell.triggers.delete(iden)

    async def updateTrigger(self, iden, query):
        '''
        Change an existing trigger's query
        '''
        trig = self.cell.triggers.get(iden)
        self._trig_auth_check(trig.get('useriden'))
        self.cell.triggers.mod(iden, query)

    async def listTriggers(self):
        '''
        Lists all the triggers that the current user is authorized to access
        '''
        trigs = []
        for (iden, trig) in self.cell.triggers.list():
            useriden = trig['useriden']
            if not (self.user.admin or useriden == self.user.iden):
                continue
            user = self.cell.auth.user(useriden)
            trig['username'] = '<unknown>' if user is None else user.name
            trigs.append((iden, trig))

        return trigs

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

        def _convert_reqdict(reqdict):
            return {s_agenda.TimeUnit.fromString(k): v for (k, v) in reqdict.items()}

        try:
            if incunit is not None:
                if isinstance(incunit, (list, tuple)):
                    incunit = [s_agenda.TimeUnit.fromString(i) for i in incunit]
                else:
                    incunit = s_agenda.TimeUnit.fromString(incunit)
            if isinstance(reqs, Mapping):
                newreqs = _convert_reqdict(reqs)
            else:
                newreqs = [_convert_reqdict(req) for req in reqs]

        except KeyError:
            raise s_exc.BadConfValu('Unrecognized time unit')

        return await self.cell.agenda.add(self.user.iden, query, newreqs, incunit, incval)

    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        cron = self.cell.agenda.appts.get(iden)
        if cron is None:
            raise s_exc.NoSuchIden()
        self._trig_auth_check(cron.useriden)
        await self.cell.agenda.delete(iden)

    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        cron = self.cell.agenda.appts.get(iden)
        if cron is None:
            raise s_exc.NoSuchIden()
        self._trig_auth_check(cron.useriden)
        await self.cell.agenda.mod(iden, query)

    async def listCronJobs(self):
        '''
        Get information about all the cron jobs accessible to the current user
        '''
        crons = []
        for iden, cron in self.cell.agenda.list():
            useriden = cron['useriden']
            if not (self.user.admin or useriden == self.user.iden):
                continue
            user = self.cell.auth.user(useriden)
            cron['username'] = '<unknown>' if user is None else user.name
            crons.append((iden, cron))

        return crons

    async def addNodeTag(self, iden, tag, valu=(None, None)):
        '''
        Add a tag to a node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
            valu (tuple):  A time interval tuple or (None, None).
        '''
        buid = s_common.uhex(iden)

        parts = tag.split('.')
        self._reqUserAllowed('tag:add', *parts)

        async with await self.cell.snap(user=self.user) as snap:
            with s_provenance.claim('coreapi', meth='tag:add', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                await node.addTag(tag, valu=valu)
                return node.pack()

    async def delNodeTag(self, iden, tag):
        '''
        Delete a tag from the node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
        '''
        buid = s_common.uhex(iden)

        parts = tag.split('.')
        self._reqUserAllowed('tag:del', *parts)

        async with await self.cell.snap(user=self.user) as snap:
            with s_provenance.claim('coreapi', meth='tag:del', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                await node.delTag(tag)
                return node.pack()

    async def setNodeProp(self, iden, name, valu):

        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:
            with s_provenance.claim('coreapi', meth='prop:set', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                prop = node.form.props.get(name)
                self._reqUserAllowed('prop:set', prop.full)

                await node.set(name, valu)
                return node.pack()

    async def addNode(self, form, valu, props=None):

        self._reqUserAllowed('node:add', form)

        async with await self.cell.snap(user=self.user) as snap:
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

        '''

        # First check that that user may add each form

        done = {}
        for node in nodes:

            formname = node[0][0]
            if done.get(formname):
                continue

            self._reqUserAllowed('node:add', formname)
            done[formname] = True

        async with await self.cell.snap(user=self.user) as snap:
            with s_provenance.claim('coreapi', meth='node:add', user=snap.user.iden):

                snap.strict = False

                async for node in snap.addNodes(nodes):

                    if node is not None:
                        node = node.pack()

                    yield node

    async def addFeedData(self, name, items, seqn=None):

        self._reqUserAllowed('feed:data', *name.split('.'))

        with s_provenance.claim('feed:data', name=name):

            async with await self.cell.snap(user=self.user) as snap:
                snap.strict = False
                return await snap.addFeedData(name, items, seqn=seqn)

    def getFeedOffs(self, iden):
        return self.cell.getFeedOffs(iden)

    @s_cell.adminapi
    def setFeedOffs(self, iden, offs):
        return self.cell.setFeedOffs(iden, offs)

    async def count(self, text, opts=None):
        '''
        Count the number of nodes which result from a storm query.

        Args:
            text (str): Storm query text.
            opts (dict): Storm query options.

        Returns:
            (int): The number of nodes resulting from the query.
        '''
        i = 0
        async for _ in self.cell.eval(text, opts=opts, user=self.user):
            i += 1
        return i

    async def eval(self, text, opts=None):
        '''
        Evalute a storm query and yield packed nodes.
        '''
        async for pode in self.cell.iterStormPodes(text, opts=opts, user=self.user):
            yield pode

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            ((str,dict)): Storm messages.
        '''
        async for mesg in self.cell.streamstorm(text, opts, user=self.user):
            yield mesg

    async def syncLayerSplices(self, iden, offs):
        '''
        Yield (indx, mesg) splices for the given layer beginning at offset.

        Once caught up, this API will begin yielding splices in real-time.
        The generator will only terminate on network disconnect or if the
        consumer falls behind the max window size of 10,000 splice messages.
        '''
        if not self.allowed('layer:sync', iden):
            mesg = f'User must have permission layer:sync.{iden}.'
            raise s_exc.AuthDeny(mesg=mesg, perm=('layer:sync', iden))

        async for item in self.cell.syncLayerSplices(iden, offs):
            yield item

    @s_cell.adminapi
    async def splices(self, offs, size):
        '''
        Return the list of splices at the given offset.
        '''
        count = 0
        async for mesg in self.cell.view.layers[0].splices(offs, size):
            count += 1
            if not count % 1000:
                await asyncio.sleep(0)
            yield mesg

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

class Cortex(s_cell.Cell):
    '''
    A Cortex implements the synapse hypergraph.

    The bulk of the Cortex API lives on the Snap() object which can
    be obtained by calling Cortex.snap() in a with block.  This allows
    callers to manage transaction boundaries explicitly and dramatically
    increases performance.
    '''
    confdefs = (  # type: ignore

        ('modules', {
            'type': 'list', 'defval': (),
            'doc': 'A list of module classes to load.'
        }),

        ('storm:log', {
            'type': 'bool', 'defval': False,
            'doc': 'Log storm queries via system logger.'
        }),

        ('storm:log:level', {
            'type': 'int',
            'defval': logging.WARNING,
            'doc': 'Logging log level to emit storm logs at.'
        }),

        ('splice:sync', {
            'type': 'str', 'defval': None,
            'doc': 'A telepath URL for an upstream cortex.'
        }),

        ('splice:cryotank', {
            'type': 'str', 'defval': None,
            'doc': 'A telepath URL for a cryotank used to archive splices.'
        }),

        ('feeds', {
            'type': 'list', 'defval': (),
            'doc': 'A list of feed dictionaries.'
        }),

        ('cron:enable', {
            'type': 'bool', 'defval': True,
            'doc': 'Enable cron jobs running.'
        }),
    )

    cellapi = CoreApi

    async def __anit__(self, dirn, conf=None):

        await s_cell.Cell.__anit__(self, dirn, conf=conf)

        # share ourself via the cell dmon as "cortex"
        # for potential default remote use
        self.dmon.share('cortex', self)

        self.views = {}
        self.layers = {}
        self.counts = {}
        self.modules = {}
        self.splicers = {}
        self.layrctors = {}
        self.feedfuncs = {}
        self.stormcmds = {}
        self.stormrunts = {}

        self._runtLiftFuncs = {}
        self._runtPropSetFuncs = {}
        self._runtPropDelFuncs = {}

        self.ontagadds = collections.defaultdict(list)
        self.ontagdels = collections.defaultdict(list)
        self.ontagaddglobs = s_cache.TagGlobs()
        self.ontagdelglobs = s_cache.TagGlobs()

        self.libroot = (None, {}, {})
        self.bldgbuids = {} # buid -> (Node, Event)  Nodes under construction

        self._initSplicers()
        self._initStormCmds()
        self._initStormLibs()
        self._initFeedFuncs()
        self._initFormCounts()
        self._initLayerCtors()
        self._initCortexHttpApi()

        self.model = s_datamodel.Model()

        # Perform module loading
        mods = list(s_modules.coremods)
        mods.extend(self.conf.get('modules'))
        await self._loadCoreMods(mods)

        # Initialize our storage and views
        await self._initCoreLayers()
        await self._checkLayerModels()
        await self._initCoreViews()
        # our "main" view has the same iden as we do
        self.view = self.views.get(self.iden)

        self.provstor = await s_provenance.ProvStor.anit(self.dirn)
        self.onfini(self.provstor.fini)
        self.provstor.migratePre010(self.view.layers[0])

        async def fini():
            await asyncio.gather(*[view.fini() for view in self.views.values()])
            await asyncio.gather(*[layr.fini() for layr in self.layers.values()])

        self.onfini(fini)

        self.triggers = s_trigger.Triggers(self)
        self.agenda = await s_agenda.Agenda.anit(self)
        self.onfini(self.agenda)

        if self.conf.get('cron:enable'):
            await self.agenda.enable()

        await self._initCoreMods()

        # Initialize free-running tasks.
        self._initCryoLoop()
        self._initPushLoop()
        self._initFeedLoops()

    async def syncLayerSplices(self, iden, offs):
        '''
        Yield (offs, mesg) tuples for splices in a layer.
        '''
        layr = self.getLayer(iden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        async for item in layr.syncSplices(offs):
            yield item

    async def initCoreMirror(self, url):
        '''
        Initialize this cortex as a down-stream mirror from a telepath url.

        NOTE: This cortex *must* be initialized from a backup of the target
              cortex!
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

                    logger.warning(f'mirror loop connected ({url}')

                    # assume only the main layer for now...
                    layr = self.getLayer()

                    offs = await layr.getOffset(layr.iden)

                    if offs == 0:
                        stat = await layr.stat()
                        offs = stat.get('splicelog_indx', 0)
                        await layr.setOffset(layr.iden, offs)

                    while not proxy.isfini:

                        # gotta do this in the loop as welll...
                        offs = await layr.getOffset(layr.iden)

                        # pump them into a queue so we can consume them in chunks
                        q = asyncio.Queue(maxsize=1000)

                        async def consume(x):
                            try:
                                async for item in proxy.syncLayerSplices(layr.iden, x):
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

                            splices = [i[1] for i in items]
                            await self.addFeedData('syn.splice', splices)
                            await layr.setOffset(layr.iden, items[-1][0])

            except asyncio.CancelledError: # pragma: no cover
                raise

            except Exception as e:
                logger.exception('error in initCoreMirror loop')
                await asyncio.sleep(1)

    async def _getWaitFor(self, name, valu):
        form = self.model.form(name)
        return form.getWaitFor(valu)

    def _initStormCmds(self):
        '''
        Registration for built-in Storm commands.
        '''
        self.addStormCmd(s_storm.MaxCmd)
        self.addStormCmd(s_storm.MinCmd)
        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.IdenCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.SudoCmd)
        self.addStormCmd(s_storm.UniqCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.GraphCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.SleepCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)

    def _initStormLibs(self):
        '''
        Registration for built-in Storm Libraries
        '''
        self.addStormLib(('str',), s_stormtypes.LibStr)
        self.addStormLib(('time',), s_stormtypes.LibTime)
        self.addStormLib(('inet', 'http'), s_stormhttp.LibHttp)

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
        }
        self.splicers.update(**splicers)

    def _initLayerCtors(self):
        '''
        Registration for built-in Layer ctors
        '''
        ctors = {
            'lmdb': s_lmdblayer.LmdbLayer,
            'remote': s_remotelayer.RemoteLayer,
        }
        self.layrctors.update(**ctors)

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
                # get the main layer...
                layr = self.layers.get(self.iden)
                return await s_layer.LayerApi.anit(self, link, user, layr)

            if len(path) == 2:
                layr = self.layers.get(path[1])
                if layr is None:
                    raise s_exc.NoSuchLayer(iden=path[1])

                return await s_layer.LayerApi.anit(self, link, user, layr)

        raise s_exc.NoSuchPath(path=path)

    async def getModelDict(self):
        return self.model.getModelDict()

    def _initFormCounts(self):

        self.formcountdb = self.slab.initdb('form:counts')

        for lkey, lval in self.slab.scanByFull(db=self.formcountdb):
            form = lkey.decode('utf8')
            valu = s_common.int64un(lval)
            self.counts[form] = valu

    def pokeFormCount(self, form, valu):

        curv = self.counts.get(form, 0)
        newv = curv + valu

        self.counts[form] = newv

        byts = s_common.int64en(newv)
        self.slab.put(form.encode('utf8'), byts, db=self.formcountdb)

    async def _calcFormCounts(self):
        '''
        Recalculate form counts from scratch.
        '''
        logger.info('Calculating form counts from scratch.')
        self.counts.clear()

        nameforms = list(self.model.forms.items())
        fairiter = 5
        tcount = 0
        for i, (name, form) in enumerate(nameforms, 1):
            logger.info('Calculating form counts for [%s] [%s/%s]',
                        name, i, len(nameforms))
            count = 0

            async for buid, valu in self.view.layers[0].iterFormRows(name):

                count += 1
                tcount += 1

                if count % fairiter == 0:
                    await asyncio.sleep(0)
                    # identity check for small integer
                    if fairiter == 5 and tcount > 100000:
                        fairiter = 1000

            self.counts[name] = count

        for name, valu in self.counts.items():
            byts = s_common.int64en(valu)
            self.slab.put(name.encode('utf8'), byts, db=self.formcountdb)
        logger.info('Done calculating form counts.')

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
        if func is None:
            raise s_exc.NoSuchLift(mesg='No runt lift implemented for requested property.',
                                   full=full, valu=valu, cmpr=cmpr)

        async for buid, rows in func(full, valu, cmpr):
            yield buid, rows

    def addRuntPropSet(self, prop, func):
        '''
        Register a prop set helper for a runt form
        '''
        self._runtPropSetFuncs[prop.full] = func

    async def runRuntPropSet(self, node, prop, valu):
        func = self._runtPropSetFuncs.get(prop.full)
        if func is None:
            raise s_exc.IsRuntForm(mesg='No prop:set func set for runt property.',
                                   prop=prop.full, valu=valu, ndef=node.ndef)
        ret = await s_coro.ornot(func, node, prop, valu)
        return ret

    def addRuntPropDel(self, prop, func):
        '''
        Register a prop set helper for a runt form
        '''
        self._runtPropDelFuncs[prop.full] = func

    async def runRuntPropDel(self, node, prop):
        func = self._runtPropDelFuncs.get(prop.full)
        if func is None:
            raise s_exc.IsRuntForm(mesg='No prop:del func set for runt property.',
                                   prop=prop.full, ndef=node.ndef)
        ret = await s_coro.ornot(func, node, prop)
        return ret

    async def runTagAdd(self, node, tag, valu):

        # Run the non-glob callbacks, then the glob callbacks
        funcs = itertools.chain(self.ontagadds.get(tag, ()), (x[1] for x in self.ontagaddglobs.get(tag)))
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

        funcs = itertools.chain(self.ontagdels.get(tag, ()), (x[1] for x in self.ontagdelglobs.get(tag)))
        for func in funcs:
            try:
                await s_coro.ornot(func, node, tag, valu)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('onTagDel Error')

        await self.triggers.runTagDel(node, tag)

    async def _checkLayerModels(self):
        mrev = s_modelrev.ModelRev(self)
        await mrev.revCoreLayers()

    def addLayerCtor(self, name, ctor):
        '''
        Modules may use this to register additional layer constructors.
        '''
        self.layrctors[name] = ctor

    async def _initCoreViews(self):

        for iden, node in await self.hive.open(('cortex', 'views')):
            view = await View.anit(self, node)
            self.views[iden] = view

        # if we have no views, we are initializing.  add the main view.
        if self.views.get(self.iden) is None:
            await self.addView(self.iden, 'root', (self.iden,))

    async def addView(self, iden, owner, layers):

        node = await self.hive.open(('cortex', 'views', iden))
        info = await node.dict()

        await info.set('owner', owner)
        await info.set('layers', layers)

        view = await View.anit(self, node)
        self.views[iden] = view

        return view

    async def delView(self, iden):
        '''
        Delete a cortex view by iden.
        '''
        if iden == self.iden:
            raise s_exc.SynErr(mesg='cannot delete the main view')

        view = self.views.pop(iden, None)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        await self.hive.pop(('cortex', 'views', iden))
        await view.fini()

    async def setViewLayers(self, layers, iden=None):
        '''
        Args:
            layers ([str]): A top-down list of of layer guids
            iden (str): The view iden ( defaults to default view ).
        '''
        if iden is None:
            iden = self.iden

        view = self.views.get(iden)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        await view.setLayers(layers)

    def getLayer(self, iden=None):
        if iden is None:
            iden = self.iden
        return self.layers.get(iden)

    def getView(self, iden=None):
        if iden is None:
            iden = self.iden
        return self.views.get(iden)

    async def addLayer(self, **info):
        '''
        Add a Layer to the cortex.

        Notes:

            The addLayer ``**info`` arg is expected to be shaped like the following::

                info = {
                    'iden': <str>, ( optional iden. default guid() )
                    'type': <str>, ( optional type. default lmdb )
                    'owner': <str>, ( optional owner. default root )
                    'config': {}, # type specific config options.
                }

        '''
        iden = info.pop('iden', None)
        if iden is None:
            iden = s_common.guid()

        node = await self.hive.open(('cortex', 'layers', iden))

        layrinfo = await node.dict()
        layrconf = await (await node.open(('config',))).dict()

        await layrinfo.set('type', info.get('type', 'lmdb'))
        await layrinfo.set('owner', info.get('owner', 'root'))
        await layrinfo.set('name', info.get('name', '??'))

        for name, valu in info.get('config', {}).items():
            await layrconf.set(name, valu)

        return await self._layrFromNode(node)

    async def joinTeleLayer(self, url, indx=None):
        '''
        Convenience function to join a remote telepath layer
        into this cortex and default view.
        '''
        info = {
            'type': 'remote',
            'owner': 'root',
            'config': {
                'url': url
            }
        }

        layr = await self.addLayer(**info)
        await self.view.addLayer(layr, indx=indx)
        return layr.iden

    async def _layrFromNode(self, node):

        info = await node.dict()

        ctor = self.layrctors.get(info.get('type'))
        if ctor is None:
            logger.warning('layer has invalid type: %r %r' % (node.name(), info.get('type')))
            return None

        layr = await ctor.anit(self, node)
        self.layers[layr.iden] = layr

        return layr

    async def _initCoreLayers(self):

        node = await self.hive.open(('cortex', 'layers'))

        # TODO eventually hold this and watch for changes
        for iden, node in node:
            await self._layrFromNode(node)

        self._migrOrigLayer()

        if self.layers.get(self.iden) is None:
            # we have no layers.  initialize the default layer.
            await self.addLayer(iden=self.iden)

    def _migrOrigLayer(self):

        oldpath = os.path.join(self.dirn, 'layers', '000-default')
        if not os.path.exists(oldpath):
            return

        newpath = os.path.join(self.dirn, 'layers', self.iden)
        os.rename(oldpath, newpath)

    def addStormCmd(self, ctor):
        '''
        Add a synapse.lib.storm.Cmd class to the cortex.
        '''
        if not s_grammar.isCmdName(ctor.name):
            raise s_exc.BadCmdName(name=ctor.name)

        self.stormcmds[ctor.name] = ctor

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

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

    def _initPushLoop(self):

        if self.conf.get('splice:sync') is None:
            return

        self.schedCoro(self._runPushLoop())

    async def _runPushLoop(self):

        url = self.conf.get('splice:sync')

        iden = self.getCellIden()

        logger.info('sync loop init: %s', url)

        while not self.isfini:
            timeout = 1
            try:

                url = self.conf.get('splice:sync')

                async with await s_telepath.openurl(url) as core:

                    # use our iden as the feed iden
                    offs = await core.getFeedOffs(iden)

                    while not self.isfini:
                        layer = self.view.layers[0]

                        items = [x async for x in layer.splices(offs, 10000)]

                        if not items:
                            await self.waitfini(timeout=1)
                            continue

                        size = len(items)
                        indx = (await layer.stat())['splicelog_indx']

                        perc = float(offs) / float(indx) * 100.0

                        logger.info('splice push: %d %d/%d (%.4f%%)', size, offs, indx, perc)

                        offs = await core.addFeedData('syn.splice', items, seqn=(iden, offs))
                        await self.fire('core:splice:sync:sent')

            except asyncio.CancelledError:
                break

            except Exception as e:  # pragma: no cover
                if isinstance(e, OSError):
                    timeout = 60

                logger.exception('sync error')
                await self.waitfini(timeout)

    def _initCryoLoop(self):

        tankurl = self.conf.get('splice:cryotank')
        if tankurl is None:
            return

        self.schedCoro(self._runCryoLoop())

    def _initFeedLoops(self):
        '''
        feeds:
            - cryotank: tcp://cryo.vertex.link/cryo00/tank01
              type: syn.splice
        '''
        feeds = self.conf.get('feeds', ())
        if not feeds:
            return

        for feed in feeds:

            # do some validation before we fire tasks...
            typename = feed.get('type')
            if self.getFeedFunc(typename) is None:
                raise s_exc.NoSuchType(name=typename)

            self.schedCoro(self._runFeedLoop(feed))

    async def _runFeedLoop(self, feed):

        url = feed.get('cryotank')
        typename = feed.get('type')
        fsize = feed.get('size', 1000)

        logger.info('feed loop init: %s @ %s', typename, url)

        while not self.isfini:
            timeout = 1
            try:

                url = feed.get('cryotank')

                async with await s_telepath.openurl(url) as tank:

                    layer = self.view.layers[0]

                    iden = await tank.iden()

                    offs = await layer.getOffset(iden)

                    while not self.isfini:

                        items = [item async for item in tank.slice(offs, fsize)]
                        if not items:
                            await self.waitfini(timeout=2)
                            continue

                        datas = [i[1] for i in items]

                        offs = await self.addFeedData(typename, datas, seqn=(iden, offs))
                        await self.fire('core:feed:loop')
                        logger.debug('Processed [%s] records with [%s]',
                                     len(datas), typename)

            except asyncio.CancelledError:
                break

            except Exception as e:  # pragma: no cover
                if isinstance(e, OSError):
                    timeout = 60
                logger.exception('feed error')
                await self.waitfini(timeout)

    async def _runCryoLoop(self):

        online = False
        tankurl = self.conf.get('splice:cryotank')

        # TODO:  what to do when write layer changes?

        # push splices for our main layer
        layr = self.view.layers[0]

        while not self.isfini:
            timeout = 2
            try:

                async with await s_telepath.openurl(tankurl) as tank:

                    if not online:
                        online = True
                        logger.info('splice cryotank: online')

                    offs = await tank.offset(self.iden)

                    while not self.isfini:

                        items = [item async for item in layr.splices(offs, 10000)]

                        if not len(items):
                            layr.spliced.clear()
                            await s_coro.event_wait(layr.spliced, timeout=1)
                            continue

                        logger.info('tanking splices: %d', len(items))

                        offs = await tank.puts(items, seqn=(self.iden, offs))
                        await self.fire('core:splice:cryotank:sent')

            except asyncio.CancelledError:  # pragma: no cover
                break

            except Exception as e:  # pragma: no cover
                if isinstance(e, OSError):
                    timeout = 60
                online = False
                logger.exception('splice cryotank offline')

                await self.waitfini(timeout)

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

    async def _addSynNodes(self, snap, items):
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

    @s_coro.genrhelp
    async def eval(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        if user is None:
            user = self.auth.getUserByName('root')

        await self.boss.promote('storm', user=user, info={'query': text})
        async with await self.snap(user=user) as snap:
            async for node in snap.eval(text, opts=opts, user=user):
                yield node

    @s_coro.genrhelp
    async def storm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield (node, path) tuples.
        Yields:
            (Node, Path) tuples
        '''
        if user is None:
            user = self.auth.getUserByName('root')

        await self.boss.promote('storm', user=user, info={'query': text})
        async with await self.snap(user=user) as snap:
            async for mesg in snap.storm(text, opts=opts, user=user):
                yield mesg

    async def nodes(self, text, opts=None, user=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        return [n async for n in self.eval(text, opts=opts, user=user)]

    @s_coro.genrhelp
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
            user = self.auth.getUserByName('root')

        # promote ourself to a synapse task
        synt = await self.boss.promote('storm', user=user, info={'query': text})

        show = opts.get('show')

        async def runStorm():
            cancelled = False
            tick = s_common.now()
            count = 0
            try:
                # First, try text parsing. If this fails, we won't be able to get
                # a storm runtime in the snap, so catch and pass the `err` message
                # before handing a `fini` message along.
                self.getStormQuery(text)

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
                logger.exception('Error during storm execution')
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

    @s_coro.genrhelp
    async def iterStormPodes(self, text, opts=None, user=None):
        if user is None:
            user = self.auth.getUserByName('root')

        await self.boss.promote('storm', user=user, info={'query': text})
        async with await self.snap(user=user) as snap:
            async for pode in snap.iterStormPodes(text, opts=opts, user=user):
                yield pode

    @s_cache.memoize(size=10000)
    def getStormQuery(self, text):
        '''
        Parse storm query text and return a Query object.
        '''
        query = s_grammar.Parser(text).query()
        query.init(self)
        return query

    def _logStormQuery(self, text, user):
        '''
        Log a storm query.
        '''
        if self.conf.get('storm:log'):
            lvl = self.conf.get('storm:log:level')
            logger.log(lvl, 'Executing storm query {%s} as [%s]', text, user.name)

    async def getNodeByNdef(self, ndef):
        '''
        Return a single Node() instance by (form,valu) tuple.
        '''
        name, valu = ndef

        form = self.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        norm, info = form.type.norm(valu)

        buid = s_common.buid((form.name, norm))

        async with await self.snap() as snap:
            return await snap.getNodeByBuid(buid)

    async def getNodesBy(self, full, valu, cmpr='='):
        '''
        Get nodes by a property value or lift syntax.

        Args:
            full (str): The full name of a property <form>:<prop>.
            valu (obj): A value that the type knows how to lift by.
            cmpr (str): The comparison operator you are lifting by.

        Some node property types allow special syntax here.

        Examples:

            # simple lift by property equality
            core.getNodesBy('file:bytes:size', 20)

            # The inet:ipv4 type knows about cidr syntax
            core.getNodesBy('inet:ipv4', '1.2.3.0/24')
        '''
        async with await self.snap() as snap:
            async for node in snap.getNodesBy(full, valu, cmpr=cmpr):
                yield node

    def getCoreInfo(self):
        return {
            'version': synapse.version,
            'modeldef': self.model.getModelDef(),
            'stormcmds': {cmd: {} for cmd in self.stormcmds.keys()},
        }

    async def addNodes(self, nodedefs):
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
        async with await self.snap() as snap:
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

    async def getFeedOffs(self, iden):
        return await self.view.layers[0].getOffset(iden)

    async def setFeedOffs(self, iden, offs):

        if offs < 0:
            mesg = 'Offset must be >= 0.'
            raise s_exc.BadConfValu(mesg=mesg, offs=offs, iden=iden)

        return await self.view.layers[0].setOffset(iden, offs)

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
            user = self.auth.getUserByName('root')

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
            'layer': await self.view.layers[0].stat(),
            'formcounts': self.counts,
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
