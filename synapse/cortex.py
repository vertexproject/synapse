import os
import copy
import regex
import asyncio
import logging
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
import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.view as s_view
import synapse.lib.cache as s_cache
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.storm as s_storm
import synapse.lib.agenda as s_agenda
import synapse.lib.config as s_config
import synapse.lib.parser as s_parser
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.httpapi as s_httpapi
import synapse.lib.modules as s_modules
import synapse.lib.spooled as s_spooled
import synapse.lib.version as s_version
import synapse.lib.modelrev as s_modelrev
import synapse.lib.stormsvc as s_stormsvc
import synapse.lib.lmdbslab as s_lmdbslab

# Importing these registers their commands
import synapse.lib.stormhttp as s_stormhttp  # NOQA
import synapse.lib.stormwhois as s_stormwhois  # NOQA

import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

import synapse.lib.stormlib.json as s_stormlib_json  # NOQA
import synapse.lib.stormlib.macro as s_stormlib_macro
import synapse.lib.stormlib.model as s_stormlib_model
import synapse.lib.stormlib.backup as s_stormlib_backup  # NOQA
import synapse.lib.stormlib.version as s_stormlib_version  # NOQA
import synapse.lib.stormlib.modelext as s_stormlib_modelext  # NOQA

logger = logging.getLogger(__name__)

'''
A Cortex implements the synapse hypergraph object.
'''

reqver = '>=0.2.0,<3.0.0'

# Constants returned in results from syncLayersEvents and syncIndexEvents
SYNC_NODEEDITS = 0  # A nodeedits: (<offs>, 0, <etyp>, (<etype args>), {<meta>})
SYNC_NODEEDIT = 1   # A nodeedit:  (<offs>, 0, <etyp>, (<etype args>))
SYNC_LAYR_ADD = 3   # A layer was added
SYNC_LAYR_DEL = 4   # A layer was deleted

# push/pull def
reqValidPush = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'time': {'type': 'number'},
        'offs': {'type': 'number'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
    },
    'additionalProperties': True,
    'required': ['iden', 'url', 'user', 'time'],
})
reqValidPull = reqValidPush

reqValidTagModel = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        # 'prune': {'type': 'boolean'},
        'regex': {'type': 'array', 'items': {'type': ['string', 'null']}},
    },
    'additionalProperties': False,
    'required': [],
})

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
    @s_cell.adminapi()
    def getCoreMods(self):
        return self.cell.getCoreMods()

    def stat(self):
        self.user.confirm(('status',))
        s_common.deprecated('stat')
        return self.cell.stat()

    async def getModelDict(self):
        '''
        Return a dictionary which describes the data model.

        Returns:
            (dict): A model description dictionary.
        '''
        return await self.cell.getModelDict()

    async def getModelDefs(self):
        return await self.cell.getModelDefs()

    def getCoreInfo(self):
        '''
        Return static generic information about the cortex including model definition
        '''
        return self.cell.getCoreInfo()

    async def getCoreInfoV2(self):
        '''
        Return static generic information about the cortex including model definition
        '''
        return await self.cell.getCoreInfoV2()

    def _reqValidStormOpts(self, opts):

        if opts is None:
            opts = {}

        opts.setdefault('user', self.user.iden)
        if opts.get('user') != self.user.iden:
            self.user.confirm(('impersonate',))

        return opts

    async def callStorm(self, text, opts=None):
        '''
        Return the value expressed in a return() statement within storm.
        '''
        opts = self._reqValidStormOpts(opts)
        return await self.cell.callStorm(text, opts=opts)

    async def exportStorm(self, text, opts=None):
        '''
        Execute a storm query and package nodes for export/import.

        NOTE: This API yields nodes after an initial complete lift
              in order to limit exported edges.
        '''
        opts = self._reqValidStormOpts(opts)
        async for pode in self.cell.exportStorm(text, opts=opts):
            yield pode

    async def feedFromAxon(self, sha256, opts=None):
        '''
        Import a msgpack .nodes file from the axon.
        '''
        opts = self._reqValidStormOpts(opts)
        return await self.cell.feedFromAxon(sha256, opts=opts)

    async def addCronJob(self, cdef):
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
            incvals (Union[int, List[int]):
                A integer or a list of integers of the number of units

        Returns (bytes):
            An iden that can be used to later modify, query, and delete the job.

        Notes:
            reqs must have fields present or incunit must not be None (or both)
            The incunit if not None it must be larger in unit size than all the keys in all reqs elements.
        '''
        cdef['creator'] = self.user.iden

        s_common.deprecated('addCronJob')
        self.user.confirm(('cron', 'add'), gateiden='cortex')
        return await self.cell.addCronJob(cdef)

    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        s_common.deprecated('delCronJob')
        self.user.confirm(('cron', 'del'), gateiden=iden)
        await self.cell.delCronJob(iden)

    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        s_common.deprecated('updateCronJob')
        self.user.confirm(('cron', 'set'), gateiden=iden)
        await self.cell.updateCronJob(iden, query)

    async def enableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        s_common.deprecated('enableCronJob')
        self.user.confirm(('cron', 'set'), gateiden=iden)
        await self.cell.enableCronJob(iden)

    async def disableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        s_common.deprecated('disableCronJob')
        self.user.confirm(('cron', 'set'), gateiden=iden)
        await self.cell.disableCronJob(iden)

    async def listCronJobs(self):
        '''
        Get information about all the cron jobs accessible to the current user
        '''
        s_common.deprecated('listCronJobs')

        crons = []
        for cron in await self.cell.listCronJobs():

            if not self.user.allowed(('cron', 'get'), gateiden=cron.get('iden')):
                continue

            crons.append(cron)

        return crons

    async def editCronJob(self, iden, name, valu):
        '''
        Update a value in a cron definition.
        '''
        iden = str(iden)
        name = str(name)
        self.user.confirm(('cron', 'set', name), gateiden=iden)
        return await self.cell.editCronJob(iden, name, valu)

    async def setStormCmd(self, cdef):
        '''
        Set the definition of a pure storm command in the cortex.
        '''
        self.user.confirm(('admin', 'cmds'))
        return await self.cell.setStormCmd(cdef)

    async def delStormCmd(self, name):
        '''
        Remove a pure storm command from the cortex.
        '''
        self.user.confirm(('admin', 'cmds'))
        return await self.cell.delStormCmd(name)

    async def _reqDefLayerAllowed(self, perms):
        view = self.cell.getView()
        wlyr = view.layers[0]
        self.user.confirm(perms, gateiden=wlyr.iden)

    async def addNodeTag(self, iden, tag, valu=(None, None)):
        '''
        Add a tag to a node specified by iden.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
            valu (tuple):  A time interval tuple or (None, None).
        '''
        s_common.deprecated('addNodeTag')
        await self._reqDefLayerAllowed(('node', 'tag', 'add', *tag.split('.')))
        return await self.cell.addNodeTag(self.user, iden, tag, valu)

    async def delNodeTag(self, iden, tag):
        '''
        Delete a tag from the node specified by iden. Deprecated in 2.0.0.

        Args:
            iden (str): A hex encoded node BUID.
            tag (str):  A tag string.
        '''
        s_common.deprecated('delNodeTag')
        await self._reqDefLayerAllowed(('node', 'tag', 'del', *tag.split('.')))
        return await self.cell.delNodeTag(self.user, iden, tag)

    async def setNodeProp(self, iden, name, valu):
        '''
        Set a property on a single node. Deprecated in 2.0.0.
        '''
        s_common.deprecated('setNodeProp')
        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:

            with s_provenance.claim('coreapi', meth='prop:set', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                prop = node.form.props.get(name)
                self.user.confirm(('node', 'prop', 'set', prop.full), gateiden=snap.wlyr.iden)

                await node.set(name, valu)
                return node.pack()

    async def delNodeProp(self, iden, name):
        '''
        Delete a property from a single node. Deprecated in 2.0.0.
        '''
        s_common.deprecated('delNodeProp')
        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:

            with s_provenance.claim('coreapi', meth='prop:del', user=snap.user.iden):

                node = await snap.getNodeByBuid(buid)
                if node is None:
                    raise s_exc.NoSuchIden(iden=iden)

                prop = node.form.props.get(name)

                self.user.confirm(('node', 'prop', 'del', prop.full), gateiden=snap.wlyr.iden)

                await node.pop(name)
                return node.pack()

    async def addNode(self, form, valu, props=None):
        '''
        Deprecated in 2.0.0.
        '''
        s_common.deprecated('addNode')
        async with await self.cell.snap(user=self.user) as snap:
            self.user.confirm(('node', 'add', form), gateiden=snap.wlyr.iden)
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

        Deprecated in 2.0.0
        '''
        s_common.deprecated('addNodes')

        # First check that that user may add each form
        done = {}
        for node in nodes:

            formname = node[0][0]
            if done.get(formname):
                continue

            await self._reqDefLayerAllowed(('node', 'add', formname))
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

    async def addFeedData(self, name, items, *, viewiden=None):

        view = self.cell.getView(viewiden, user=self.user)
        if view is None:
            raise s_exc.NoSuchView(iden=viewiden)

        wlyr = view.layers[0]
        parts = name.split('.')

        self.user.confirm(('feed:data', *parts), gateiden=wlyr.iden)

        await self.cell.boss.promote('feeddata',
                                     user=self.user,
                                     info={'name': name,
                                           'view': view.iden,
                                           'nitems': len(items),
                                           })

        async with await self.cell.snap(user=self.user, view=view) as snap:
            with s_provenance.claim('feed:data', name=name, user=snap.user.iden):
                snap.strict = False
                await snap.addFeedData(name, items)

    async def count(self, text, opts=None):
        '''
        Count the number of nodes which result from a storm query.

        Args:
            text (str): Storm query text.
            opts (dict): Storm query options.

        Returns:
            (int): The number of nodes resulting from the query.
        '''
        opts = self._reqValidStormOpts(opts)
        return await self.cell.count(text, opts=opts)

    async def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield packed nodes.

        NOTE: This API is deprecated as of 2.0.0 and will be removed in 3.0.0
        '''
        s_common.deprecated('eval')
        opts = self._reqValidStormOpts(opts)
        view = self.cell._viewFromOpts(opts)
        async for pode in view.iterStormPodes(text, opts=opts):
            yield pode

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.

        Yields:
            ((str,dict)): Storm messages.
        '''
        opts = self._reqValidStormOpts(opts)

        if opts.get('spawn'):
            await self._execSpawnStorm(text, opts)
            return

        async for mesg in self.cell.storm(text, opts=opts):
            yield mesg

    async def _execSpawnStorm(self, text, opts):

        view = self.cell._viewFromOpts(opts)

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

        await self.cell.boss.promote('storm:spawn', user=self.user, info={'query': text})
        proc = None
        mesg = 'Spawn complete'

        try:

            async with self.cell.spawnpool.get() as proc:
                if await proc.xact(info):
                    await link.fini()

        except (asyncio.CancelledError, Exception) as e:

            if not isinstance(e, asyncio.CancelledError):
                logger.exception('Error during spawned Storm execution.')

            if not self.cell.isfini:
                if proc:
                    await proc.fini()

            mesg = repr(e)
            raise

        finally:
            raise s_exc.DmonSpawn(mesg=mesg)

    async def reqValidStorm(self, text, opts=None):
        '''
        Parse a Storm query to validate it.

        Args:
            text (str): The text of the Storm query to parse.
            opts (dict): A Storm options dictionary.

        Returns:
            True: If the query is valid.

        Raises:
            BadSyntaxError: If the query is invalid.
        '''
        return await self.cell.reqValidStorm(text, opts)

    async def watch(self, wdef):
        '''
        Hook cortex/view/layer watch points based on a specified watch definition.

        Example:

            wdef = { 'tags': [ 'foo.bar', 'baz.*' ] }

            async for mesg in core.watch(wdef):
                dostuff(mesg)
        '''
        s_common.deprecated('watch')
        iden = wdef.get('view', self.cell.view.iden)
        self.user.confirm(('watch',), gateiden=iden)

        async for mesg in self.cell.watch(wdef):
            yield mesg

    async def syncLayerNodeEdits(self, offs, layriden=None, wait=True):
        '''
        Yield (indx, mesg) nodeedit sets for the given layer beginning at offset.

        Once caught up, this API will begin yielding nodeedits in real-time.
        The generator will only terminate on network disconnect or if the
        consumer falls behind the max window size of 10,000 nodeedit messages.
        '''
        layr = self.cell.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        self.user.confirm(('sync',), gateiden=layr.iden)

        async for item in self.cell.syncLayerNodeEdits(layr.iden, offs, wait=wait):
            yield item

    @s_cell.adminapi()
    async def splices(self, offs=None, size=None, layriden=None):
        '''
        Return the list of splices at the given offset.
        '''
        s_common.deprecated('splices')
        layr = self.cell.getLayer(layriden)
        count = 0
        async for mesg in layr.splices(offs=offs, size=size):
            count += 1
            if not count % 1000:
                await asyncio.sleep(0)
            yield mesg

    @s_cell.adminapi()
    async def splicesBack(self, offs=None, size=None):
        '''
        Return the list of splices backwards from the given offset.
        '''
        s_common.deprecated('splicesBack')
        count = 0
        async for mesg in self.cell.view.layers[0].splicesBack(offs=offs, size=size):
            count += 1
            if not count % 1000: # pragma: no cover
                await asyncio.sleep(0)
            yield mesg

    async def spliceHistory(self):
        '''
        Yield splices backwards from the end of the splice log.

        Will only return the user's own splices unless they are an admin.
        '''
        s_common.deprecated('spliceHistory')
        async for splice in self.cell.spliceHistory(self.user):
            yield splice

    @s_cell.adminapi()
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

    @s_cell.adminapi()
    async def getProvStack(self, iden: str):
        '''
        Return the provenance stack associated with the given iden.

        Args:
            iden (str):  the iden of the provenance stack

        Note: the iden appears on each splice entry as the 'prov' property
        '''
        if iden is None:
            return None

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

    async def addForm(self, formname, basetype, typeopts, typeinfo):
        '''
        Add an extended form to the data model.

        Extended forms *must* begin with _
        '''
        self.user.confirm(('model', 'form', 'add', formname))
        return await self.cell.addForm(formname, basetype, typeopts, typeinfo)

    async def delForm(self, formname):
        '''
        Remove an extended form from the data model.
        '''
        self.user.confirm(('model', 'form', 'del', formname))
        return await self.cell.delForm(formname)

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
        self.user.confirm(('pkg', 'add'))
        return await self.cell.addStormPkg(pkgdef)

    async def delStormPkg(self, iden):
        self.user.confirm(('pkg', 'del'))
        return await self.cell.delStormPkg(iden)

    @s_cell.adminapi()
    async def getStormPkgs(self):
        return await self.cell.getStormPkgs()

    @s_cell.adminapi()
    async def getStormPkg(self, name):
        return await self.cell.getStormPkg(name)

    @s_cell.adminapi()
    async def addStormDmon(self, ddef):
        return await self.cell.addStormDmon(ddef)

    @s_cell.adminapi()
    async def getStormDmons(self):
        return await self.cell.getStormDmons()

    @s_cell.adminapi()
    async def getStormDmonLog(self, iden):
        return await self.cell.getStormDmonLog(iden)

    @s_cell.adminapi()
    async def getStormDmon(self, iden):
        return await self.cell.getStormDmon(iden)

    @s_cell.adminapi()
    async def bumpStormDmon(self, iden):
        return await self.cell.bumpStormDmon(iden)

    @s_cell.adminapi()
    async def disableStormDmon(self, iden):
        return await self.cell.disableStormDmon(iden)

    @s_cell.adminapi()
    async def enableStormDmon(self, iden):
        return await self.cell.enableStormDmon(iden)

    @s_cell.adminapi()
    async def delStormDmon(self, iden):
        return await self.cell.delStormDmon(iden)

    @s_cell.adminapi(log=True)
    async def enableMigrationMode(self):
        await self.cell._enableMigrationMode()

    @s_cell.adminapi(log=True)
    async def disableMigrationMode(self):
        await self.cell._disableMigrationMode()

    @s_cell.adminapi()
    async def cloneLayer(self, iden, ldef=None):

        ldef = ldef or {}
        ldef['creator'] = self.user.iden

        return await self.cell.cloneLayer(iden, ldef)

    async def getStormVar(self, name, default=None):
        self.user.confirm(('globals', 'get', name))
        return await self.cell.getStormVar(name, default=default)

    async def popStormVar(self, name, default=None):
        self.user.confirm(('globals', 'pop', name))
        return await self.cell.popStormVar(name, default=default)

    async def setStormVar(self, name, valu):
        self.user.confirm(('globals', 'set', name))
        return await self.cell.setStormVar(name, valu)

    async def syncLayersEvents(self, offsdict=None, wait=True):
        self.user.confirm(('sync',))
        async for item in self.cell.syncLayersEvents(offsdict=offsdict, wait=wait):
            yield item

    async def syncIndexEvents(self, matchdef, offsdict=None, wait=True):
        self.user.confirm(('sync',))
        async for item in self.cell.syncIndexEvents(matchdef, offsdict=offsdict, wait=wait):
            yield item

    async def iterFormRows(self, layriden, form, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes of a single form, optionally (re)starting at startvalue

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            form(str):  A form name
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        self.user.confirm(('layer', 'lift', layriden))
        async for item in self.cell.iterFormRows(layriden, form, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterPropRows(self, layriden, form, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular secondary property, optionally (re)starting at startvalue

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            form(str):  A form name.
            prop (str):  A secondary property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        self.user.confirm(('layer', 'lift', layriden))
        async for item in self.cell.iterPropRows(layriden, form, prop, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterUnivRows(self, layriden, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular universal property, optionally (re)starting at startvalue

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        self.user.confirm(('layer', 'lift', layriden))
        async for item in self.cell.iterUnivRows(layriden, prop, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterTagRows(self, layriden, tag, form=None, starttupl=None):
        '''
        Yields (buid, (valu, form)) values that match a tag and optional form, optionally (re)starting at starttupl.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            tag (str): the tag to match
            form (Optional[str]):  if present, only yields buids of nodes that match the form.
            starttupl (Optional[Tuple[buid, form]]):  if present, (re)starts the stream of values there.

        Returns:
            AsyncIterator[Tuple(buid, (valu, form))]

        Note:
            This yields (buid, (tagvalu, form)) instead of just buid, valu in order to allow resuming an interrupted
            call by feeding the last value retrieved into starttupl
        '''
        self.user.confirm(('layer', 'lift', layriden))
        async for item in self.cell.iterTagRows(layriden, tag, form=form, starttupl=starttupl):
            yield item

    async def iterTagPropRows(self, layriden, tag, prop, form=None, stortype=None, startvalu=None):
        '''
        Yields (buid, valu) that match a tag:prop, optionally (re)starting at startvalu.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            tag (str):  tag name
            prop (str):  prop name
            form (Optional[str]):  optional form name
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        self.user.confirm(('layer', 'lift', layriden))
        async for item in self.cell.iterTagPropRows(layriden, tag, prop, form=form, stortype=stortype,
                                                    startvalu=startvalu):
            yield item

class Cortex(s_cell.Cell):  # type: ignore
    '''
    A Cortex implements the synapse hypergraph.

    The bulk of the Cortex API lives on the Snap() object which can
    be obtained by calling Cortex.snap() in a with block.  This allows
    callers to manage transaction boundaries explicitly and dramatically
    increases performance.
    '''

    # For the cortex, nexslog:en defaults to True
    confbase = copy.deepcopy(s_cell.Cell.confbase)
    confbase['nexslog:en']['default'] = True  # type: ignore

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
        'trigger:enable': {
            'default': True,
            'description': 'Enable triggers running.',
            'type': 'boolean'
        },
        'layer:lmdb:map_async': {
            'default': True,
            'description': 'Set the default lmdb:map_async value in LMDB layers.',
            'type': 'boolean'
        },
        'layers:lockmemory': {
            'default': False,
            'description': 'Should new layers lock memory for performance by default.',
            'type': 'boolean'
        },
        'layers:logedits': {
            'default': True,
            'description': 'Whether nodeedits are logged in each layer.',
            'type': 'boolean'
        },
        'provenance:en': {
            'default': False,
            'description': 'Enable provenance tracking for all writes.',
            'type': 'boolean'
        },
        'max:nodes': {
            'description': 'Maximum number of nodes which are allowed to be stored in a Cortex.',
            'type': 'integer',
            'minimum': 1,
            'hidecmdl': True,
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
        'storm:log': {
            'default': False,
            'description': 'Log storm queries via system logger.',
            'type': 'boolean'
        },
        'storm:log:level': {
            'default': 30,
            'description': 'Logging log level to emit storm logs at.',
            'type': 'integer'
        },
        'http:proxy': {
            'description': 'An aiohttp-socks compatible proxy URL to use storm HTTP API.',
            'type': 'string',
        },
    }

    cellapi = CoreApi
    viewapi = s_view.ViewApi
    layerapi = s_layer.LayerApi
    hiveapi = s_hive.HiveApi

    viewctor = s_view.View.anit
    layrctor = s_layer.Layer.anit
    spawncorector = 'synapse.lib.spawn.SpawnCore'

    # phase 2 - service storage
    async def initServiceStorage(self):

        # NOTE: we may not make *any* nexus actions in this method

        if self.inaugural:
            await self.cellinfo.set('cortex:version', s_version.version)

        corevers = self.cellinfo.get('cortex:version')
        s_version.reqVersion(corevers, reqver, exc=s_exc.BadStorageVersion,
                             mesg='cortex version in storage is incompatible with running software')

        self.views = {}
        self.layers = {}
        self.modules = {}
        self.splicers = {}
        self.feedfuncs = {}
        self.stormcmds = {}

        self.spawnpool = None

        self.maxnodes = self.conf.get('max:nodes')
        self.nodecount = 0

        self.storm_cmd_ctors = {}
        self.storm_cmd_cdefs = {}

        self.stormmods = {}     # name: mdef
        self.stormpkgs = {}     # name: pkgdef
        self.stormvars = None   # type: s_hive.HiveDict

        self.svcsbyiden = {}
        self.svcsbyname = {}
        self.svcsbysvcname = {}  # remote name, not local name

        self._runtLiftFuncs = {}
        self._runtPropSetFuncs = {}
        self._runtPropDelFuncs = {}

        self.ontagadds = collections.defaultdict(list)
        self.ontagdels = collections.defaultdict(list)
        self.ontagaddglobs = s_cache.TagGlobs()
        self.ontagdelglobs = s_cache.TagGlobs()

        self.tagvalid = s_cache.FixedCache(self._isTagValid, size=1000)

        self.libroot = (None, {}, {})
        self.bldgbuids = {} # buid -> (Node, Event)  Nodes under construction

        self.axon = None  # type: s_axon.AxonApi
        self.axready = asyncio.Event()

        self.view = None  # The default/main view

        proven = self.conf.get('provenance:en')

        self.provstor = await s_provenance.ProvStor.anit(self.dirn, proven=proven)
        self.onfini(self.provstor.fini)

        # generic fini handler for the Cortex
        self.onfini(self._onCoreFini)

        await self._initCoreHive()
        self._initSplicers()
        self._initStormLibs()
        self._initFeedFuncs()

        self._initCortexHttpApi()

        self.model = s_datamodel.Model()

        # Perform module loading
        await self._loadCoreMods()
        await self._loadExtModel()
        await self._initStormCmds()

        # Initialize our storage and views
        await self._initCoreAxon()

        await self._initCoreLayers()
        await self._initCoreViews()
        self.onfini(self._finiStor)
        await self._initCoreQueues()

        self.addHealthFunc(self._cortexHealth)

        self.stormdmons = await s_storm.DmonManager.anit(self)
        self.onfini(self.stormdmons)
        self.agenda = await s_agenda.Agenda.anit(self)
        self.onfini(self.agenda)
        await self._initStormDmons()

        self.trigson = self.conf.get('trigger:enable')

        await self._initRuntFuncs()

        taghive = await self.hive.open(('cortex', 'tagmeta'))
        cmdhive = await self.hive.open(('cortex', 'storm', 'cmds'))
        pkghive = await self.hive.open(('cortex', 'storm', 'packages'))
        svchive = await self.hive.open(('cortex', 'storm', 'services'))

        self.taghive = await taghive.dict()
        self.cmdhive = await cmdhive.dict()
        self.pkghive = await pkghive.dict()
        self.svchive = await svchive.dict()

        self.deprlocks = await self.hive.get(('cortex', 'model', 'deprlocks'), {})
        # TODO: 3.0.0 conversion will truncate this hive key
        for name, locked in self.deprlocks.items():

            form = self.model.form(name)
            if form is not None:
                form.locked = locked

            prop = self.model.prop(name)
            if prop is not None:
                prop.locked = locked

            _type = self.model.type(name)
            if _type is not None:
                _type.locked = locked

        # Finalize coremodule loading & give svchive a shot to load
        await self._initPureStormCmds()

        import synapse.lib.spawn as s_spawn  # get around circular dependency
        self.spawnpool = await s_spawn.SpawnPool.anit(self)
        self.onfini(self.spawnpool)
        self.on('user:mod', self._onEvtBumpSpawnPool)

        self.dynitems.update({
            'cron': self.agenda,
            'cortex': self,
            'multiqueue': self.multiqueue,
        })

        await self.auth.addAuthGate('cortex', 'cortex')

    async def _execCellUpdates(self):

        await self._bumpCellVers('cortex:defaults', (
            (1, self._addAllLayrRead),
        ))

    async def _addAllLayrRead(self):
        layriden = self.getView().layers[0].iden
        role = await self.auth.getRoleByName('all')
        await role.addRule((True, ('layer', 'read')), gateiden=layriden)

    async def initServiceRuntime(self):

        # do any post-nexus initialization here...
        if self.isactive:
            await self._checkNexsIndx()
            await self._checkLayerModels()
        await self._initCoreMods()
        await self._initStormSvcs()

        # share ourself via the cell dmon as "cortex"
        # for potential default remote use
        self.dmon.share('cortex', self)

    async def initServiceActive(self):
        if self.conf.get('cron:enable'):
            await self.agenda.start()
        await self.stormdmons.start()

    async def initServicePassive(self):
        await self.agenda.stop()
        await self.stormdmons.stop()

    async def _onEvtBumpSpawnPool(self, evnt):
        await self.bumpSpawnPool()

    async def bumpSpawnPool(self):
        if self.spawnpool is not None:
            await self.spawnpool.bump()

    @s_nexus.Pusher.onPushAuto('model:depr:lock')
    async def setDeprLock(self, name, locked):

        todo = []
        prop = self.model.prop(name)
        if prop is not None and prop.deprecated:
            todo.append(prop)

        _type = self.model.type(name)
        if _type is not None and _type.deprecated:
            todo.append(_type)

        if not todo:
            mesg = 'setDeprLock() called on non-existant or non-deprecated form, property, or type.'
            raise s_exc.NoSuchProp(name=name, mesg=mesg)

        self.deprlocks[name] = locked
        await self.hive.set(('cortex', 'model', 'deprlocks'), self.deprlocks)

        for elem in todo:
            elem.locked = locked

    async def getDeprLocks(self):
        '''
        Return a dictionary of deprecated properties and their lock status.
        '''
        retn = {}

        for prop in self.model.props.values():
            if not prop.deprecated:
                continue

            retn[prop.full] = prop.locked

        return retn

    async def addCoreQueue(self, name, info):

        if self.multiqueue.exists(name):
            mesg = f'Queue named {name} already exists!'
            raise s_exc.DupName(mesg=mesg)

        await self._push('queue:add', name, info)

    @s_nexus.Pusher.onPush('queue:add')
    async def _addCoreQueue(self, name, info):
        if self.multiqueue.exists(name):
            return

        await self.auth.addAuthGate(f'queue:{name}', 'queue')

        creator = info.get('creator')
        if creator is not None:
            user = await self.auth.reqUser(creator)
            await user.setAdmin(True, gateiden=f'queue:{name}', logged=False)

        await self.multiqueue.add(name, info)

    async def listCoreQueues(self):
        return self.multiqueue.list()

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
        if not self.multiqueue.exists(name):
            return

        await self.multiqueue.rem(name)

    async def coreQueueGet(self, name, offs=0, cull=True, wait=False):
        if offs and cull:
            await self.coreQueueCull(name, offs - 1)

        async for item in self.multiqueue.gets(name, offs, cull=False, wait=wait):
            return item

    async def coreQueueGets(self, name, offs=0, cull=True, wait=False, size=None):
        if offs and cull:
            await self.coreQueueCull(name, offs - 1)

        count = 0
        async for item in self.multiqueue.gets(name, offs, cull=False, wait=wait):

            yield item

            count += 1
            if size is not None and count >= size:
                return

    async def coreQueuePuts(self, name, items):
        await self._push('queue:puts', name, items)

    @s_nexus.Pusher.onPush('queue:puts', passitem=True)
    async def _coreQueuePuts(self, name, items, nexsitem):
        nexsoff, nexsmesg = nexsitem
        await self.multiqueue.puts(name, items, reqid=nexsoff)

    @s_nexus.Pusher.onPushAuto('queue:cull')
    async def coreQueueCull(self, name, offs):
        await self.multiqueue.cull(name, offs)

    @s_nexus.Pusher.onPushAuto('queue:pop')
    async def coreQueuePop(self, name, offs):
        return await self.multiqueue.pop(name, offs)

    async def coreQueueSize(self, name):
        return self.multiqueue.size(name)

    @s_nexus.Pusher.onPushAuto('tag:model:set')
    async def setTagModel(self, tagname, name, valu):
        '''
        Set a model specification property for a tag.

        Arguments:
            tagname (str): The name of the tag.
            name (str): The name of the property.
            valu (object): The value of the property.

        Tag Model Properties:
            regex - A list of None or regular expression strings to match each tag level.

        Examples:
            await core.setTagModel("cno.cve", "regex", (None, None, "[0-9]{4}", "[0-9]{5}"))

        '''
        meta = self.taghive.get(tagname)
        if meta is None:
            meta = {}

        meta[name] = valu
        reqValidTagModel(meta)

        await self.taghive.set(tagname, meta)

        # clear cached entries
        if name == 'regex':
            self.tagvalid.clear()

    @s_nexus.Pusher.onPushAuto('tag:model:del')
    async def delTagModel(self, tagname):
        '''
        Delete all the model specification properties for a tag.

        Arguments:
            tagname (str): The name of the tag.
        '''
        await self.taghive.pop(tagname)
        self.tagvalid.clear()

    @s_nexus.Pusher.onPushAuto('tag:model:pop')
    async def popTagModel(self, tagname, name):
        '''
        Pop a property from the model specification of a tag.

        Arguments:
            tagname (str): The name of the tag.
            name (str): The name of the specification property.

        Returns:
            (object): The current value of the property.
        '''

        meta = self.taghive.get(tagname)
        if meta is None:
            return None

        retn = meta.pop(name, None)
        await self.taghive.set(name, meta)

        if name == 'regex':
            self.tagvalid.clear()

        return retn

    async def isTagValid(self, tagname):
        '''
        Check if a tag name is valid according to tag model regular expressions.

        Returns:
            (bool): True if the tag is valid.
        '''
        return await self.tagvalid.aget(tagname)

    async def _isTagValid(self, tagname):

        parts = s_chop.tagpath(tagname)
        for tag in s_chop.tags(tagname):

            meta = self.taghive.get(tag)
            if meta is None:
                continue

            regx = meta.get('regex')
            if regx is None:
                continue

            for i in range(min(len(regx), len(parts))):

                if regx[i] is None:
                    continue

                if not regex.fullmatch(regx[i], parts[i]):
                    return False

        return True

    async def getTagModel(self, tagname):
        '''
        Retrieve the tag model specification for a tag.

        Returns:
            (dict): The tag model specification or None.
        '''
        retn = self.taghive.get(tagname)
        if retn is not None:
            return dict(retn)

    async def listTagModel(self):
        '''
        Retrieve a list of the tag model specifications.

        Returns:
            ([(str, dict), ...]): A list of tag model specification tuples.
        '''
        return list(self.taghive.items())

    async def getSpawnInfo(self):

        if self.spawncorector is None:
            mesg = 'spawn storm option not supported on this cortex'
            raise s_exc.FeatureNotSupported(mesg=mesg)

        ret = {
            'iden': self.iden,
            'dirn': self.dirn,
            'conf': {
                'storm:log': self.conf.get('storm:log', False),
                'storm:log:level': self.conf.get('storm:log:level', logging.INFO),
                'trigger:enable': self.conf.get('trigger:enable', True),
            },
            'loglevel': logger.getEffectiveLevel(),
            'views': [v.getSpawnInfo() for v in self.views.values()],
            'layers': [await lyr.getSpawnInfo() for lyr in self.layers.values()],
            'storm': {
                'cmds': {
                    'cdefs': list(self.storm_cmd_cdefs.items()),
                    'ctors': list(self.storm_cmd_ctors.items()),
                },
                'libs': tuple(self.libroot),
                'mods': await self.getStormMods(),
                'pkgs': await self.getStormPkgs(),
                'svcs': [svc.sdef for svc in self.getStormSvcs()],
            },
            'model': await self.getModelDefs(),
            'spawncorector': self.spawncorector,
        }
        return ret

    async def _finiStor(self):
        await asyncio.gather(*[view.fini() for view in self.views.values()])
        await asyncio.gather(*[layr.fini() for layr in self.layers.values()])

    async def _initRuntFuncs(self):

        async def onSetTrigDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            trig = node.snap.view.triggers.get(iden)
            node.snap.user.confirm(('trigger', 'set', 'doc'), gateiden=iden)
            await trig.set('doc', valu)
            node.props[prop.name] = valu

        async def onSetTrigName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            trig = node.snap.view.triggers.get(iden)
            node.snap.user.confirm(('trigger', 'set', 'name'), gateiden=iden)
            await trig.set('name', valu)
            node.props[prop.name] = valu

        async def onSetCronDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            appt = await self.agenda.get(iden)
            node.snap.user.confirm(('cron', 'set', 'doc'), gateiden=iden)
            await appt.setDoc(valu)
            node.props[prop.name] = valu

        async def onSetCronName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            appt = await self.agenda.get(iden)
            node.snap.user.confirm(('cron', 'set', 'name'), gateiden=iden)
            await appt.setName(valu)
            node.props[prop.name] = valu

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

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception as e:
                logger.warning(f'initStormDmon ({iden}) failed: {e}')

    async def _initStormSvcs(self):

        for iden, sdef in self.svchive.items():

            try:
                await self._setStormSvc(sdef)

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception as e:
                logger.warning(f'initStormService ({iden}) failed: {e}')

    async def _initCoreQueues(self):
        path = os.path.join(self.dirn, 'slabs', 'queues.lmdb')

        slab = await s_lmdbslab.Slab.anit(path)
        self.onfini(slab.fini)

        self.multiqueue = await slab.getMultiQueue('cortex:queue', nexsroot=self.nexsroot)

    @s_nexus.Pusher.onPushAuto('cmd:set')
    async def setStormCmd(self, cdef):
        '''
        Set pure storm command definition.

        Args:
            cdef (dict): A Pure Stormcmd definition dictionary.

        Notes:

            The definition dictionary is formatted like the following::

                {

                    'name': <name>,

                    'cmdargs': [
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

    async def _getStorNodes(self, buid, layers):
        # NOTE: This API lives here to make it easy to optimize
        #       the cluster case to minimize round trips
        return [await layr.getStorNode(buid) for layr in layers]

    async def _setStormCmd(self, cdef):
        '''
        Note:
            No change control or persistence
        '''

        await self._reqStormCmd(cdef)

        def ctor(runt, runtsafe):
            return s_storm.PureCmd(cdef, runt, runtsafe)

        # TODO unify class ctors and func ctors vs briefs...
        def getCmdBrief():
            return cdef.get('descr', 'No description').strip().split('\n')[0]

        ctor.getCmdBrief = getCmdBrief
        ctor.pkgname = cdef.get('pkgname')
        ctor.svciden = cdef.get('cmdconf', {}).get('svciden', '')
        ctor.forms = cdef.get('forms', {})

        def getStorNode(form):
            ndef = (form.name, form.type.norm(cdef.get('name'))[0])
            buid = s_common.buid(ndef)

            props = {
                'doc': ctor.getCmdBrief()
            }

            inpt = ctor.forms.get('input')
            outp = ctor.forms.get('output')
            nodedata = ctor.forms.get('nodedata')

            if inpt:
                props['input'] = tuple(inpt)

            if outp:
                props['output'] = tuple(outp)

            if nodedata:
                props['nodedata'] = tuple(nodedata)

            if ctor.svciden:
                props['svciden'] = ctor.svciden

            if ctor.pkgname:
                props['package'] = ctor.pkgname

            pnorms = {}
            for prop, valu in props.items():
                formprop = form.props.get(prop)
                if formprop is not None and valu is not None:
                    pnorms[prop] = formprop.type.norm(valu)[0]

            return (buid, {
                'ndef': ndef,
                'props': pnorms,
            })

        ctor.getStorNode = getStorNode

        name = cdef.get('name')
        self.stormcmds[name] = ctor
        self.storm_cmd_cdefs[name] = cdef

        await self.bumpSpawnPool()

        await self.fire('core:cmd:change', cmd=name, act='add')

    async def _popStormCmd(self, name):
        self.stormcmds.pop(name, None)
        await self.bumpSpawnPool()

        await self.fire('core:cmd:change', cmd=name, act='del')

    async def delStormCmd(self, name):
        '''
        Remove a previously set pure storm command.
        '''
        ctor = self.stormcmds.get(name)
        if ctor is None:
            mesg = f'No storm command named {name}.'
            raise s_exc.NoSuchCmd(name=name, mesg=mesg)

        return await self._push('cmd:del', name)

    @s_nexus.Pusher.onPush('cmd:del')
    async def _delStormCmd(self, name):
        ctor = self.stormcmds.get(name)
        if ctor is None:
            return

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

    async def delStormPkg(self, name):
        pkgdef = self.pkghive.get(name, None)
        if pkgdef is None:
            mesg = f'No storm package: {name}.'
            raise s_exc.NoSuchPkg(mesg=mesg)

        return await self._push('pkg:del', name)

    @s_nexus.Pusher.onPush('pkg:del')
    async def _delStormPkg(self, name):
        '''
        Delete a storm package by name.
        '''
        pkgdef = await self.pkghive.pop(name, None)
        if pkgdef is None:
            return

        await self._dropStormPkg(pkgdef)

    async def getStormPkg(self, name):
        return self.stormpkgs.get(name)

    async def getStormPkgs(self):
        return list(self.pkghive.values())

    async def getStormMods(self):
        return self.stormmods

    async def getStormMod(self, name):
        return self.stormmods.get(name)

    def getDataModel(self):
        return self.model

    async def _tryLoadStormPkg(self, pkgdef):
        try:
            await self.loadStormPkg(pkgdef)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception as e:
            name = pkgdef.get('name', '')
            logger.exception(f'Error loading pkg: {name}, {str(e)}')

    async def _confirmStormPkg(self, pkgdef):
        '''
        Validate a storm package for loading.  Raises if invalid.
        '''
        # Validate package def
        s_storm.reqValidPkgdef(pkgdef)

        pkgname = pkgdef.get('name')

        # Check minimum synapse version
        minversion = pkgdef.get('synapse_minversion')
        if minversion is not None and minversion > s_version.version:
            mesg = f'Storm package {pkgname} requires Synapse {minversion} but ' \
                   f'Cortex is running {s_version.version}'
            raise s_exc.BadVersion(mesg=mesg)

        # Validate storm contents from modules and commands
        mods = pkgdef.get('modules', ())
        cmds = pkgdef.get('commands', ())
        onload = pkgdef.get('onload')
        svciden = pkgdef.get('svciden')

        if onload is not None:
            self.getStormQuery(onload)

        for mdef in mods:
            modtext = mdef.get('storm')
            self.getStormQuery(modtext)
            mdef.setdefault('modconf', {})
            if svciden:
                mdef['modconf']['svciden'] = svciden

        for cdef in cmds:
            cdef['pkgname'] = pkgname
            cdef.setdefault('cmdconf', {})
            if svciden:
                cdef['cmdconf']['svciden'] = svciden

            cmdtext = cdef.get('storm')
            self.getStormQuery(cmdtext)

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

        onload = pkgdef.get('onload')
        if onload is not None and self.isactive:
            async def _onload():
                try:
                    async for mesg in self.storm(onload):
                        if mesg[0] in ('print', 'warn'):
                            logger.warning(f'onload output: {mesg}')
                            await asyncio.sleep(0)
                except asyncio.CancelledError: # pragma: no cover
                    raise
                except Exception: # pragma: no cover
                    logger.warning(f'onload failed for package: {name}')
            self.schedCoro(_onload())

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

        ssvc = self.svcsbysvcname.get(name)
        if name is not None:
            return ssvc

    async def waitStormSvc(self, name, timeout=None):
        ssvc = self.getStormSvc(name)
        return await s_coro.event_wait(ssvc.ready, timeout=timeout)

    async def addStormSvc(self, sdef):
        '''
        Add a registered storm service to the cortex.
        '''
        iden = sdef.get('iden')
        if iden is None:
            iden = sdef['iden'] = s_common.guid()

        if self.svcsbyiden.get(iden) is not None:
            mesg = f'Storm service already exists: {iden}'
            raise s_exc.DupStormSvc(mesg=mesg)

        return await self._push('svc:add', sdef)

    @s_nexus.Pusher.onPush('svc:add')
    async def _addStormSvc(self, sdef):

        iden = sdef.get('iden')
        ssvc = self.svcsbyiden.get(iden)
        if ssvc is not None:
            return ssvc.sdef

        ssvc = await self._setStormSvc(sdef)
        await self.svchive.set(iden, sdef)
        await self.bumpSpawnPool()

        return ssvc.sdef

    async def delStormSvc(self, iden):
        sdef = self.svchive.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg, iden=iden)

        return await self._push('svc:del', iden)

    @s_nexus.Pusher.onPush('svc:del')
    async def _delStormSvc(self, iden):
        '''
        Delete a registered storm service from the cortex.
        '''
        sdef = self.svchive.get(iden)
        if sdef is None: # pragma: no cover
            return

        try:
            if self.isactive:
                await self.runStormSvcEvent(iden, 'del')
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once py 3.8 only
            raise
        except Exception as e:
            logger.exception(f'service.del hook for service {iden} failed with error: {e}')

        sdef = await self.svchive.pop(iden)

        await self._delStormSvcPkgs(iden)

        name = sdef.get('name')
        if name is not None:
            self.svcsbyname.pop(name, None)

        ssvc = self.svcsbyiden.pop(iden, None)
        if ssvc is not None:
            self.svcsbysvcname.pop(ssvc.svcname, None)
            await ssvc.fini()

        await self.bumpSpawnPool()

    async def _delStormSvcPkgs(self, iden):
        '''
        Delete storm packages associated with a service.
        '''
        oldpkgs = []
        for _, pdef in self.pkghive.items():
            pkgiden = pdef.get('svciden')
            if pkgiden and pkgiden == iden:
                oldpkgs.append(pdef)

        for pkg in oldpkgs:
            name = pkg.get('name')
            if name:
                await self._delStormPkg(name)

    async def setStormSvcEvents(self, iden, edef):
        '''
        Set the event callbacks for a storm service. Extends the sdef dict.

        Args:
            iden (str): The service iden.
            edef (dict): The events definition.

        Notes:

            The edef is formatted like the following::

                {
                    <name> : {
                        'storm': <storm>
                    }
                }

            where ``name`` is one of the following items:

            add

                Run the given storm '*before* the service is first added (a la service.add), but not on a reconnect.

            del

                Run the given storm *after* the service is removed (a la service.del), but not on a disconnect.

        Returns:
            dict: An updated storm service definition dictionary.
        '''
        sdef = self.svchive.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        sdef['evts'] = edef
        await self.svchive.set(iden, sdef)
        return sdef

    async def _runStormSvcAdd(self, iden):
        sdef = self.svchive.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        if sdef.get('added', False):
            return

        try:
            await self.runStormSvcEvent(iden, 'add')
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once py 3.8 only
            raise
        except Exception as e:
            logger.exception(f'runStormSvcEvent service.add failed with error {e}')
            return

        sdef['added'] = True
        await self.svchive.set(iden, sdef)

    async def runStormSvcEvent(self, iden, name):
        assert name in ('add', 'del')

        sdef = self.svchive.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        evnt = sdef.get('evts', {}).get(name, {}).get('storm')
        if evnt is None:
            return

        opts = {'vars': {'cmdconf': {'svciden': iden}}}
        coro = s_common.aspin(self.storm(evnt, opts=opts))
        if name == 'add':
            await coro
        else:
            self.schedCoro(coro)

    async def _setStormSvc(self, sdef):

        ssvc = await s_stormsvc.StormSvcClient.anit(self, sdef)

        self.onfini(ssvc)

        self.svcsbyiden[ssvc.iden] = ssvc
        self.svcsbyname[ssvc.name] = ssvc

        return ssvc

    def getStormSvcs(self):
        return list(self.svcsbyiden.values())

    # Global stormvars APIs

    async def getStormVar(self, name, default=None):
        return self.stormvars.get(name, default=default)

    @s_nexus.Pusher.onPushAuto('stormvar:pop')
    async def popStormVar(self, name, default=None):
        return await self.stormvars.pop(name, default=default)

    @s_nexus.Pusher.onPushAuto('stormvar:set')
    async def setStormVar(self, name, valu):
        return await self.stormvars.set(name, valu)

    async def itemsStormVar(self):
        for item in self.stormvars.items():
            yield item

    async def _cortexHealth(self, health):
        health.update('cortex', 'nominal')

    async def _loadExtModel(self):

        self.extforms = await (await self.hive.open(('cortex', 'model', 'forms'))).dict()
        self.extprops = await (await self.hive.open(('cortex', 'model', 'props'))).dict()
        self.extunivs = await (await self.hive.open(('cortex', 'model', 'univs'))).dict()
        self.exttagprops = await (await self.hive.open(('cortex', 'model', 'tagprops'))).dict()

        for formname, basetype, typeopts, typeinfo in self.extforms.values():
            try:
                self.model.addType(formname, basetype, typeopts, typeinfo)
                form = self.model.addForm(formname, {}, ())
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception as e:
                logger.warning(f'Extended form ({formname}) error: {e}')
            else:
                if form.type.deprecated:
                    mesg = f'The extended property {formname} is using a deprecated type {form.type.name} which will' \
                           f' be removed in 3.0.0'
                    logger.warning(mesg)

        for form, prop, tdef, info in self.extprops.values():
            try:
                prop = self.model.addFormProp(form, prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception as e:
                logger.warning(f'ext prop ({form}:{prop}) error: {e}')
            else:
                if prop.type.deprecated:
                    mesg = f'The extended property {prop.full} is using a deprecated type {prop.type.name} which will' \
                           f' be removed in 3.0.0'
                    logger.warning(mesg)

        for prop, tdef, info in self.extunivs.values():
            try:
                self.model.addUnivProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception as e:
                logger.warning(f'ext univ ({prop}) error: {e}')

        for prop, tdef, info in self.exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
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

        self.model.addUnivProp(name, tdef, info)

        await self.extunivs.set(name, (name, tdef, info))
        await self.fire('core:extmodel:change', prop=name, act='add', type='univ')

    async def addForm(self, formname, basetype, typeopts, typeinfo):
        if not formname.startswith('_'):
            mesg = 'Extended form must begin with "_"'
            raise s_exc.BadFormDef(form=formname, mesg=mesg)
        if self.model.form(formname) is not None:
            mesg = f'Form name already exists: {formname}'
            raise s_exc.DupFormName(mesg=mesg)
        return await self._push('model:form:add', formname, basetype, typeopts, typeinfo)

    @s_nexus.Pusher.onPush('model:form:add')
    async def _addForm(self, formname, basetype, typeopts, typeinfo):
        self.model.addType(formname, basetype, typeopts, typeinfo)
        self.model.addForm(formname, {}, ())

        await self.extforms.set(formname, (formname, basetype, typeopts, typeinfo))
        await self.fire('core:extmodel:change', form=formname, act='add', type='form')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:form:del')
    async def delForm(self, formname):

        if not formname.startswith('_'):
            mesg = 'Extended form must begin with "_"'
            raise s_exc.BadFormDef(form=formname, mesg=mesg)

        for layr in self.layers.values():
            async for item in layr.iterFormRows(formname):
                mesg = f'Nodes still exist with form: {formname}'
                raise s_exc.CantDelForm(mesg=mesg)

        self.model.delForm(formname)
        self.model.delType(formname)

        await self.extforms.pop(formname, None)
        await self.fire('core:extmodel:change', form=formname, act='del', type='form')
        await self.bumpSpawnPool()

    @s_nexus.Pusher.onPushAuto('model:prop:add')
    async def addFormProp(self, form, prop, tdef, info):
        if not prop.startswith('_') and not form.startswith('_'):
            mesg = 'Extended prop must begin with "_" or be added to an extended form.'
            raise s_exc.BadPropDef(prop=prop, mesg=mesg)

        _prop = self.model.addFormProp(form, prop, tdef, info)
        if _prop.type.deprecated:
            mesg = f'The extended property {_prop.full} is using a deprecated type {_prop.type.name} which will' \
                   f' be removed in 3.0.0'
            logger.warning(mesg)

        await self.extprops.set(f'{form}:{prop}', (form, prop, tdef, info))
        await self.fire('core:extmodel:change', form=form, prop=prop, act='add', type='formprop')
        await self.bumpSpawnPool()

    async def delFormProp(self, form, prop):
        full = f'{form}:{prop}'
        pdef = self.extprops.get(full)

        if pdef is None:
            mesg = f'No ext prop named {full}'
            raise s_exc.NoSuchProp(form=form, prop=prop, mesg=mesg)

        return await self._push('model:prop:del', form, prop)

    @s_nexus.Pusher.onPush('model:prop:del')
    async def _delFormProp(self, form, prop):
        '''
        Remove an extended property from the cortex.
        '''
        full = f'{form}:{prop}'

        pdef = self.extprops.get(full)
        if pdef is None:
            return

        for layr in self.layers.values():
            async for item in layr.iterPropRows(form, prop):
                mesg = f'Nodes still exist with prop: {form}:{prop}'
                raise s_exc.CantDelProp(mesg=mesg)

        self.model.delFormProp(form, prop)
        await self.extprops.pop(full, None)
        await self.fire('core:extmodel:change',
                        form=form, prop=prop, act='del', type='formprop')
        await self.bumpSpawnPool()

    async def delUnivProp(self, prop):
        udef = self.extunivs.get(prop)
        if udef is None:
            mesg = f'No ext univ named {prop}'
            raise s_exc.NoSuchUniv(name=prop, mesg=mesg)

        return await self._push('model:univ:del', prop)

    @s_nexus.Pusher.onPush('model:univ:del')
    async def _delUnivProp(self, prop):
        '''
        Remove an extended universal property from the cortex.
        '''
        udef = self.extunivs.get(prop)
        if udef is None:
            return

        univname = '.' + prop
        for layr in self.layers.values():
            async for item in layr.iterUnivRows(univname):
                mesg = f'Nodes still exist with universal prop: {prop}'
                raise s_exc.CantDelUniv(mesg=mesg)

        self.model.delUnivProp(prop)
        await self.extunivs.pop(prop, None)
        await self.fire('core:extmodel:change', name=prop, act='del', type='univ')
        await self.bumpSpawnPool()

    async def addTagProp(self, name, tdef, info):
        if self.exttagprops.get(name) is not None:
            raise s_exc.DupPropName(name=name)

        return await self._push('model:tagprop:add', name, tdef, info)

    @s_nexus.Pusher.onPush('model:tagprop:add')
    async def _addTagProp(self, name, tdef, info):
        if self.exttagprops.get(name) is not None:
            return

        self.model.addTagProp(name, tdef, info)

        await self.exttagprops.set(name, (name, tdef, info))
        await self.fire('core:tagprop:change', name=name, act='add')
        await self.bumpSpawnPool()

    async def delTagProp(self, name):
        pdef = self.exttagprops.get(name)
        if pdef is None:
            mesg = f'No tag prop named {name}'
            raise s_exc.NoSuchProp(mesg=mesg, name=name)

        return await self._push('model:tagprop:del', name)

    @s_nexus.Pusher.onPush('model:tagprop:del')
    async def _delTagProp(self, name):
        pdef = self.exttagprops.get(name)
        if pdef is None:
            return

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

    async def syncLayerNodeEdits(self, iden, offs, wait=True):
        '''
        Yield (offs, mesg) tuples for nodeedits in a layer.
        '''
        layr = self.getLayer(iden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        async for item in layr.syncNodeEdits(offs, wait=wait):
            yield item

    async def syncLayersEvents(self, offsdict=None, wait=True):
        '''
        Yield (offs, layriden, STYP, item, meta) tuples for nodeedits for *all* layers, interspersed with add/del
        layer messages.

        STYP is one of the following constants:
            SYNC_NODEEDITS:  item is a nodeedits (buid, form, edits)
            SYNC_LAYR_ADD:   A layer was added (item and meta are empty)
            SYNC_LAYR_DEL:   A layer was deleted (item and meta are empty)

        Args:
            offsdict(Optional(Dict[str,int])): starting nexus/editlog offset by layer iden.  Defaults to 0 for
                unspecified layers or if offsdict is None.
            wait(bool):  whether to pend and stream value until this layer is fini'd
        '''
        async def layrgenr(layr, startoff, endoff=None, newlayer=False):
            if newlayer:
                yield layr.addoffs, layr.iden, SYNC_LAYR_ADD, (), {}

            wait = endoff is None

            if not layr.isfini:

                async for ioff, item, meta in layr.syncNodeEdits2(startoff, wait=wait):
                    if endoff is not None and ioff >= endoff:  # pragma: no cover
                        break

                    yield ioff, layr.iden, SYNC_NODEEDITS, item, meta

            if layr.isdeleted:
                yield layr.deloffs, layr.iden, SYNC_LAYR_DEL, (), {}

        # End of layrgenr

        async for item in self._syncNodeEdits(offsdict, layrgenr, wait=wait):
            yield item

    async def syncIndexEvents(self, matchdef, offsdict=None, wait=True):
        '''
        Yield (offs, layriden, <STYPE>, <item>) tuples from the nodeedit logs of all layers starting
        from the given nexus/layer offset (they are synchronized).  Only edits that match the filter in matchdef will
        be yielded, plus EDIT_PROGRESS (see layer.syncIndexEvents) messages.

        The format of the 4th element of the tuple depends on STYPE.  STYPE is one of the following constants:

          SYNC_LAYR_ADD:  item is an empty tuple ()
          SYNC_LAYR_DEL:  item is an empty tuple ()
          SYNC_NODEEDIT:  item is (buid, form, ETYPE, VALS, META)) or (None, None, s_layer.EDIT_PROGRESS, (), ())

        For edits in the past, events are yielded in offset order across all layers.  For current data (wait=True),
        events across different layers may be emitted slightly out of offset order.

        Note:
            Will not yield any values from layers created with logedits disabled

        Args:
            matchdef(Dict[str, Sequence[str]]):  a dict describing which events are yielded.  See
                layer.syncIndexEvents for matchdef specification.
            offsdict(Optional(Dict[str,int])): starting nexus/editlog offset by layer iden.  Defaults to 0 for
                unspecified layers or if offsdict is None.
            wait(bool):  whether to pend and stream value until this layer is fini'd
        '''
        async def layrgenr(layr, startoff, endoff=None, newlayer=False):
            ''' Yields matching results from a single layer '''

            if newlayer:
                yield layr.addoffs, layr.iden, SYNC_LAYR_ADD, ()

            wait = endoff is None
            ioff = startoff

            if not layr.isfini:

                async for ioff, item in layr.syncIndexEvents(startoff, matchdef, wait=wait):
                    if endoff is not None and ioff >= endoff:  # pragma: no cover
                        break

                    yield ioff, layr.iden, SYNC_NODEEDIT, item

            if layr.isdeleted:
                yield layr.deloffs, layr.iden, SYNC_LAYR_DEL, ()

        # End of layrgenr

        async for item in self._syncNodeEdits(offsdict, layrgenr, wait=wait):
            yield item

    async def _syncNodeEdits(self, offsdict, genrfunc, wait=True):
        '''
        Common guts between syncIndexEvents and syncLayersEvents

        First, it streams from the layers up to the current offset, sorted by offset.
        Then it streams from all the layers simultaneously.

        Args:
            offsdict(Dict[str, int]): starting nexus/editlog offset per layer.  Defaults to 0 if layer not present
            genrfunc(Callable): an async generator function that yields tuples that start with an offset.  The input
               parameters are:
                layr(Layer): a Layer object
                startoff(int);  the starting offset
                endoff(Optional[int]):  the ending offset
                newlayer(bool):  whether to emit a new layer item first
            wait(bool): when the end of the log is hit, whether to continue to wait for new entries and yield them
        '''
        topoffs = await self.getNexsIndx()  # The latest offset when this function started
        catchingup = True                   # whether we've caught up to topoffs
        layrsadded = {}                     # layriden -> True.  Captures all the layers added while catching up
        todo = set()                        # outstanding futures of active live streaming from layers
        layrgenrs = {}                      # layriden -> genr.  maps active layers to that layer's async generator

        if offsdict is None:
            offsdict = {}

        newtodoevent = asyncio.Event()

        async with await s_base.Base.anit() as base:

            def addlayr(layr, newlayer=False):
                '''
                A new layer joins the live stream
                '''
                genr = genrfunc(layr, topoffs, newlayer=newlayer)
                layrgenrs[layr.iden] = genr
                task = base.schedCoro(genr.__anext__())
                task.iden = layr.iden
                todo.add(task)
                newtodoevent.set()

            def onaddlayr(mesg):
                etyp, event = mesg
                layriden = event['iden']
                layr = self.getLayer(layriden)
                if catchingup:
                    layrsadded[layr] = True
                    return

                addlayr(layr, newlayer=True)

            self.on('core:layr:add', onaddlayr, base=base)

            # First, catch up to what was the current offset when we started, guaranteeing order

            genrs = [genrfunc(layr, offsdict.get(layr.iden, 0), endoff=topoffs) for layr in self.layers.values()]
            async for item in s_common.merggenr(genrs, lambda x, y: x[0] < y[0]):
                yield item

            catchingup = False

            if not wait:
                return

            # After we've caught up, read on genrs from all the layers simultaneously

            todo.clear()

            for layr in self.layers.values():
                if layr not in layrsadded:
                    addlayr(layr)

            for layr in layrsadded:
                addlayr(layr, newlayer=True)

            # Also, wake up if we get fini'd
            finitask = base.schedCoro(self.waitfini())
            todo.add(finitask)

            newtodotask = base.schedCoro(newtodoevent.wait())
            todo.add(newtodotask)

            while not self.isfini:
                newtodoevent.clear()
                done, _ = await asyncio.wait(todo, return_when=asyncio.FIRST_COMPLETED)

                for donetask in done:
                    try:
                        todo.remove(donetask)

                        if donetask is finitask:  # pragma: no cover  # We were fini'd
                            return

                        if donetask is newtodotask:
                            newtodotask = base.schedCoro(newtodoevent.wait())
                            todo.add(newtodotask)
                            continue

                        layriden = donetask.iden

                        result = donetask.result()

                        yield result

                        # Re-add a task to wait on the next iteration of the generator
                        genr = layrgenrs[layriden]
                        task = base.schedCoro(genr.__anext__())
                        task.iden = layriden
                        todo.add(task)

                    except StopAsyncIteration:
                        # Help out the garbage collector
                        del layrgenrs[layriden]

    async def spliceHistory(self, user):
        '''
        Yield splices backwards from the end of the nodeedit log.

        Will only return user's own splices unless they are an admin.
        '''
        layr = self.view.layers[0]

        count = 0
        async for _, mesg in layr.splicesBack():
            count += 1
            if not count % 1000:  # pragma: no cover
                await asyncio.sleep(0)

            if user.iden == mesg[1]['user'] or user.isAdmin():
                yield mesg

    async def _initCoreHive(self):
        stormvarsnode = await self.hive.open(('cortex', 'storm', 'vars'))
        self.stormvars = await stormvarsnode.dict()
        self.onfini(self.stormvars)

    async def _initCoreAxon(self):
        turl = self.conf.get('axon')
        if turl is None:
            path = os.path.join(self.dirn, 'axon')
            conf = {}

            proxyurl = self.conf.get('http:proxy')
            if proxyurl is not None:
                conf['http:proxy'] = proxyurl

            self.axon = await s_axon.Axon.anit(path, conf=conf)
            self.axon.onfini(self.axready.clear)
            self.dynitems['axon'] = self.axon
            self.axready.set()
            return

        async def teleloop():
            self.axready.clear()
            while not self.isfini:
                try:
                    self.axon = await s_telepath.openurl(turl)
                    self.axon.onfini(teleloop)
                    self.dynitems['axon'] = self.axon
                    self.axready.set()
                    return
                except asyncio.CancelledError:  # TODO:  remove once >= py 3.8 only
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
        self.addStormCmd(s_storm.TreeCmd)
        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.IdenCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.SudoCmd)
        self.addStormCmd(s_storm.UniqCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.GraphCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.MergeCmd)
        self.addStormCmd(s_storm.SleepCmd)
        self.addStormCmd(s_storm.ScrapeCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.LiftByVerb)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)
        self.addStormCmd(s_storm.EdgesDelCmd)
        self.addStormCmd(s_storm.ParallelCmd)
        self.addStormCmd(s_storm.TagPruneCmd)
        self.addStormCmd(s_storm.ViewExecCmd)
        self.addStormCmd(s_storm.BackgroundCmd)
        self.addStormCmd(s_storm.SpliceListCmd)
        self.addStormCmd(s_storm.SpliceUndoCmd)
        self.addStormCmd(s_stormlib_macro.MacroExecCmd)

        for cdef in s_stormsvc.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_storm.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_macro.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_model.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

    async def _initPureStormCmds(self):
        oldcmds = []
        for name, cdef in self.cmdhive.items():
            cmdiden = cdef.get('cmdconf', {}).get('svciden')
            if cmdiden and self.svchive.get(cmdiden) is None:
                oldcmds.append(name)
            else:
                await self._trySetStormCmd(name, cdef)

        for name in oldcmds:
            logger.warning(f'Removing old command: [{name}]')
            await self.cmdhive.pop(name)

        for pkgdef in self.pkghive.values():
            await self._tryLoadStormPkg(pkgdef)

    async def _trySetStormCmd(self, name, cdef):
        try:
            await self._setStormCmd(cdef)
        except (asyncio.CancelledError, Exception):
            logger.exception(f'Storm command load failed: {name}')

    def _initStormLibs(self):
        '''
        Registration for built-in Storm Libraries
        '''

        for path, ctor in s_stormtypes.registry.iterLibs():
            # Skip libbase which is registered as a default ctor in the storm Runtime
            if path:
                self.addStormLib(path, ctor)

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

    def _initFeedFuncs(self):
        '''
        Registration for built-in Cortex feed functions.
        '''
        self.setFeedFunc('syn.nodes', self._addSynNodes)
        self.setFeedFunc('syn.splice', self._addSynSplice)
        self.setFeedFunc('syn.nodeedits', self._addSynNodeEdits)

    def _initCortexHttpApi(self):
        '''
        Registration for built-in Cortex httpapi endpoints
        '''
        self.addHttpApi('/api/v1/storm', s_httpapi.StormV1, {'cell': self})
        self.addHttpApi('/api/v1/watch', s_httpapi.WatchSockV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/call', s_httpapi.StormCallV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/nodes', s_httpapi.StormNodesV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/export', s_httpapi.StormExportV1, {'cell': self})
        self.addHttpApi('/api/v1/reqvalidstorm', s_httpapi.ReqValidStormV1, {'cell': self})

        self.addHttpApi('/api/v1/storm/vars/set', s_httpapi.StormVarsSetV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/vars/get', s_httpapi.StormVarsGetV1, {'cell': self})
        self.addHttpApi('/api/v1/storm/vars/pop', s_httpapi.StormVarsPopV1, {'cell': self})

        self.addHttpApi('/api/v1/model', s_httpapi.ModelV1, {'cell': self})
        self.addHttpApi('/api/v1/model/norm', s_httpapi.ModelNormV1, {'cell': self})

        self.addHttpApi('/api/v1/core/info', s_httpapi.CoreInfoV1, {'cell': self})

    async def getCellApi(self, link, user, path):

        if not path:
            return await self.cellapi.anit(self, link, user)

        # allow an admin to directly open the cortex hive
        # (perhaps this should be a Cell() level pattern)
        if path[0] == 'hive' and user.isAdmin():
            return await self.hiveapi.anit(self.hive, user)

        if path[0] == 'layer':

            if len(path) == 1:
                # get the top layer for the default view
                layr = self.getLayer()
                return await self.layerapi.anit(self, link, user, layr)

            if len(path) == 2:
                layr = self.getLayer(path[1])
                if layr is None:
                    raise s_exc.NoSuchLayer(iden=path[1])

                return await self.layerapi.anit(self, link, user, layr)

        if path[0] == 'view':

            view = None
            if len(path) == 1:
                view = self.getView(user=user)

            elif len(path) == 2:
                view = self.getView(path[1], user=user)

            if view is not None:
                return await self.viewapi.anit(self, link, user, view)

        raise s_exc.NoSuchPath(path=path)

    async def getModelDict(self):
        return self.model.getModelDict()

    async def getModelDefs(self):
        return self.model.getModelDefs()

    async def getFormCounts(self):
        '''
        Return total form counts for all existing layers
        '''
        counts = collections.defaultdict(int)
        for layr in self.layers.values():
            layrcounts = await layr.getFormCounts()
            for name, valu in layrcounts.items():
                counts[name] += valu
        return dict(counts)

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

    async def _loadView(self, node):

        view = await self.viewctor(self, node)

        self.views[view.iden] = view
        self.dynitems[view.iden] = view

        async def fini():
            self.views.pop(view.iden, None)
            self.dynitems.pop(view.iden, None)

        view.onfini(fini)

        return view

    async def _initCoreViews(self):

        defiden = self.cellinfo.get('defaultview')

        for iden, node in await self.hive.open(('cortex', 'views')):
            view = await self._loadView(node)
            if iden == defiden:
                self.view = view

        for view in self.views.values():
            view.init2()

        # if we have no views, we are initializing.  Add a default main view and layer.
        if not self.views:
            assert self.inaugural, 'Cortex initialization failed: there are no views.'
            ldef = {'name': 'default'}
            ldef = await self.addLayer(ldef=ldef, nexs=False)
            layriden = ldef.get('iden')

            role = await self.auth.getRoleByName('all')
            await role.addRule((True, ('layer', 'read')), gateiden=layriden, nexs=False)

            vdef = {
                'name': 'default',
                'layers': (layriden,),
                'worldreadable': True,
            }
            vdef = await self.addView(vdef, nexs=False)
            iden = vdef.get('iden')
            await self.cellinfo.set('defaultview', iden)
            self.view = self.getView(iden)

    async def addView(self, vdef, nexs=True):

        vdef['iden'] = s_common.guid()
        vdef.setdefault('parent', None)
        vdef.setdefault('worldreadable', False)
        vdef.setdefault('creator', self.auth.rootuser.iden)

        s_view.reqValidVdef(vdef)

        if nexs:
            return await self._push('view:add', vdef)
        else:
            return await self._addView(vdef)

    @s_nexus.Pusher.onPush('view:add')
    async def _addView(self, vdef):

        s_view.reqValidVdef(vdef)

        iden = vdef['iden']
        if iden in self.views:
            return

        for lyriden in vdef['layers']:
            if lyriden not in self.layers:
                raise s_exc.NoSuchLayer(iden=lyriden)

        creator = vdef.get('creator', self.auth.rootuser.iden)
        user = await self.auth.reqUser(creator)

        await self.auth.addAuthGate(iden, 'view')
        await user.setAdmin(True, gateiden=iden, logged=False)

        # worldreadable is not get persisted with the view; the state ends up in perms
        worldread = vdef.pop('worldreadable', False)

        if worldread:
            role = await self.auth.getRoleByName('all')
            await role.addRule((True, ('view', 'read')), gateiden=iden, nexs=False)

        node = await self.hive.open(('cortex', 'views', iden))

        info = await node.dict()
        for name, valu in vdef.items():
            await info.set(name, valu)

        view = await self._loadView(node)
        view.init2()

        await self.bumpSpawnPool()

        return await view.pack()

    async def delView(self, iden):
        view = self.views.get(iden)
        if view is None:
            raise s_exc.NoSuchView(iden=iden)

        return await self._push('view:del', iden)

    @s_nexus.Pusher.onPush('view:del')
    async def _delView(self, iden):
        '''
        Delete a cortex view by iden.

        Note:
            This does not delete any of the view's layers
        '''
        view = self.views.get(iden, None)
        if view is None:
            return

        if iden == self.view.iden:
            raise s_exc.SynErr(mesg='Cannot delete the main view')

        for cview in self.views.values():
            if cview.parent is not None and cview.parent.iden == iden:
                raise s_exc.SynErr(mesg='Cannot delete a view that has children')

        await self.hive.pop(('cortex', 'views', iden))
        await view.delete()

        await self.auth.delAuthGate(iden)

        await self.bumpSpawnPool()

    async def delLayer(self, iden):
        layr = self.layers.get(iden, None)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        return await self._push('layer:del', iden)

    @s_nexus.Pusher.onPush('layer:del', passitem=True)
    async def _delLayer(self, iden, nexsitem):
        layr = self.layers.get(iden, None)
        if layr is None:
            return

        for view in self.views.values():
            if layr in view.layers:
                raise s_exc.LayerInUse(iden=iden)

        del self.layers[iden]

        for pdef in layr.layrinfo.get('pushs', {}).values():
            await self.delActiveCoro(pdef.get('iden'))

        for pdef in layr.layrinfo.get('pulls', {}).values():
            await self.delActiveCoro(pdef.get('iden'))

        await self.auth.delAuthGate(iden)
        self.dynitems.pop(iden)

        await self.hive.pop(('cortex', 'layers', iden))

        await layr.delete()

        layr.deloffs = nexsitem[0]

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
        # TODO:  due to our migration policy, remove in 3.0.0
        if iden == self.iden:
            return self.view.layers[0]

        return self.layers.get(iden)

    def listLayers(self):
        return self.layers.values()

    async def getLayerDef(self, iden=None):
        layr = self.getLayer(iden)
        if layr is not None:
            return await layr.pack()

    async def getLayerDefs(self):
        return [await lyr.pack() for lyr in self.layers.values()]

    def getView(self, iden=None, user=None):
        '''
        Get a View object.

        Args:
            iden (str): The View iden to retrieve.

        Returns:
            View: A View object.
        '''
        if iden is None:
            if user is not None:
                iden = user.profile.get('cortex:view')

            if iden is None:
                iden = self.view.iden

        # For backwards compatibility, resolve references to old view iden == cortex.iden to the main view
        # TODO:  due to our migration policy, remove in 3.0.0
        if iden == self.iden:
            iden = self.view.iden

        view = self.views.get(iden)
        if view is None:
            return None

        if user is not None:
            user.confirm(('view', 'read'), gateiden=iden)

        return view

    def listViews(self):
        return list(self.views.values())

    async def getViewDef(self, iden):
        view = self.getView(iden=iden)
        if view is not None:
            return await view.pack()

    async def getViewDefs(self):
        return [await v.pack() for v in self.views.values()]

    async def addLayer(self, ldef=None, nexs=True):
        '''
        Add a Layer to the cortex.

        Args:
            ldef (Optional[Dict]):  layer configuration
            nexs (bool):            whether to record a nexus transaction (internal use only)
        '''
        ldef = ldef or {}

        ldef['iden'] = s_common.guid()
        ldef.setdefault('creator', self.auth.rootuser.iden)
        ldef.setdefault('lockmemory', self.conf.get('layers:lockmemory'))
        ldef.setdefault('logedits', self.conf.get('layers:logedits'))
        ldef.setdefault('readonly', False)

        s_layer.reqValidLdef(ldef)

        if nexs:
            return await self._push('layer:add', ldef)
        else:
            return await self._addLayer(ldef, (None, None))

    @s_nexus.Pusher.onPush('layer:add', passitem=True)
    async def _addLayer(self, ldef, nexsitem):

        s_layer.reqValidLdef(ldef)

        iden = ldef.get('iden')
        if iden in self.layers:
            return

        layr = self.layers.get(iden)
        if layr is not None:
            return await layr.pack()
        creator = ldef.get('creator')

        user = await self.auth.reqUser(creator)

        node = await self.hive.open(('cortex', 'layers', iden))

        layrinfo = await node.dict()
        for name, valu in ldef.items():
            await layrinfo.set(name, valu)

        layr = await self._initLayr(layrinfo, nexsoffs=nexsitem[0])
        await user.setAdmin(True, gateiden=iden, logged=False)

        # forward wind the new layer to the current model version
        await layr.setModelVers(s_modelrev.maxvers)

        return await layr.pack()

    async def _initLayr(self, layrinfo, nexsoffs=None):
        '''
        Instantiate a Layer() instance via the provided layer info HiveDict.
        '''
        layr = await self._ctorLayr(layrinfo)
        layr.addoffs = nexsoffs

        self.layers[layr.iden] = layr
        self.dynitems[layr.iden] = layr

        if self.maxnodes:
            counts = await layr.getFormCounts()
            self.nodecount += sum(counts.values())

            def onadd():
                self.nodecount += 1

            def ondel():
                self.nodecount -= 1
            layr.nodeAddHook = onadd
            layr.nodeDelHook = ondel

        await self.auth.addAuthGate(layr.iden, 'layer')

        for pdef in layrinfo.get('pushs', {}).values():
            await self.runLayrPush(layr, pdef)

        for pdef in layrinfo.get('pulls', {}).values():
            await self.runLayrPull(layr, pdef)

        await self.bumpSpawnPool()

        await self.fire('core:layr:add', iden=layr.iden)

        return layr

    async def _ctorLayr(self, layrinfo):
        '''
        Actually construct the Layer instance for the given HiveDict.
        '''
        iden = layrinfo.get('iden')
        path = s_common.gendir(self.dirn, 'layers', iden)

        # In case that we're a mirror follower and we have a downstream layer, disable upstream sync
        # TODO allow_upstream needs to be separated out
        mirror = self.conf.get('mirror')
        return await s_layer.Layer.anit(layrinfo, path, nexsroot=self.nexsroot, allow_upstream=not mirror)

    async def _initCoreLayers(self):
        node = await self.hive.open(('cortex', 'layers'))
        for _, node in node:
            layrinfo = await node.dict()
            await self._initLayr(layrinfo)

    @s_nexus.Pusher.onPushAuto('layer:push:add')
    async def addLayrPush(self, layriden, pdef):

        reqValidPush(pdef)

        iden = pdef.get('iden')

        layr = self.layers.get(layriden)
        if layr is None:
            return

        pushs = layr.layrinfo.get('pushs')
        if pushs is None:
            pushs = {}

        # handle last-message replay
        if pushs.get(iden) is not None:
            return

        pushs[iden] = pdef

        await layr.layrinfo.set('pushs', pushs)
        await self.runLayrPush(layr, pdef)

    @s_nexus.Pusher.onPushAuto('layer:push:del')
    async def delLayrPush(self, layriden, pushiden):

        layr = self.layers.get(layriden)
        if layr is None:
            return

        pushs = layr.layrinfo.get('pushs')
        if pushs is None:
            return

        pdef = pushs.pop(pushiden, None)
        if pdef is None:
            return

        await layr.layrinfo.set('pushs', pushs)
        await self.delActiveCoro(pushiden)

    @s_nexus.Pusher.onPushAuto('layer:pull:add')
    async def addLayrPull(self, layriden, pdef):

        reqValidPull(pdef)

        # TODO: schema validation
        iden = pdef.get('iden')

        layr = self.layers.get(layriden)
        if layr is None:
            return

        pulls = layr.layrinfo.get('pulls')
        if pulls is None:
            pulls = {}

        # handle last-message replay
        if pulls.get(iden) is not None:
            return

        pulls[iden] = pdef
        await layr.layrinfo.set('pulls', pulls)

        await self.runLayrPull(layr, pdef)

    @s_nexus.Pusher.onPushAuto('layer:pull:del')
    async def delLayrPull(self, layriden, pulliden):

        layr = self.layers.get(layriden)
        if layr is None:
            return

        pulls = layr.layrinfo.get('pulls')
        if pulls is None:
            return

        pdef = pulls.pop(pulliden, None)
        if pdef is None:
            return

        await layr.layrinfo.set('pulls', pulls)
        await self.delActiveCoro(pulliden)

    async def runLayrPush(self, layr, pdef):
        url = pdef.get('url')
        iden = pdef.get('iden')
        # push() will refire as needed

        async def push():
            async with await self.boss.promote(f'layer push: {layr.iden} {iden}', self.auth.rootuser):
                async with await s_telepath.openurl(url) as proxy:
                    await self._pushBulkEdits(layr, proxy, pdef)

        self.addActiveCoro(push, iden=iden)

    async def runLayrPull(self, layr, pdef):
        url = pdef.get('url')
        iden = pdef.get('iden')
        # pull() will refire as needed

        async def pull():
            async with await self.boss.promote(f'layer pull: {layr.iden} {iden}', self.auth.rootuser):
                async with await s_telepath.openurl(url) as proxy:
                    await self._pushBulkEdits(proxy, layr, pdef)

        self.addActiveCoro(pull, iden=iden)

    async def _pushBulkEdits(self, layr0, layr1, pdef):

        iden = pdef.get('iden')
        user = pdef.get('user')

        gvar = f'push:{iden}'

        async with await s_base.Base.anit() as base:

            queue = s_queue.Queue(maxsize=10000)

            async def fill():

                try:
                    filloffs = await self.getStormVar(gvar, -1)
                    async for item in layr0.syncNodeEdits(filloffs + 1, wait=True):
                        await queue.put(item)
                    await queue.close()

                except asyncio.CancelledError: # pragma: no cover
                    raise

                except Exception as e:
                    logger.exception(f'pushBulkEdits fill() error: {e}')
                    await queue.close()

            base.schedCoro(fill())

            async for chunk in queue.slices():

                meta = {'time': s_common.now(), 'user': user}

                alledits = []
                for offs, edits in chunk:
                    # prevent push->push->push nodeedits growth
                    alledits.extend(edits)
                    if len(alledits) > 1000:
                        await layr1.storNodeEdits(alledits, meta)
                        await self.setStormVar(gvar, offs)
                        alledits.clear()

                if alledits:
                    await layr1.storNodeEdits(alledits, meta)
                    await self.setStormVar(gvar, offs)

    async def _checkNexsIndx(self):
        layroffs = [await layr.getEditIndx() for layr in self.layers.values()]
        if layroffs:
            maxindx = max(layroffs)
            if maxindx > await self.getNexsIndx():
                await self.setNexsIndx(maxindx)

    async def cloneLayer(self, iden, ldef=None):
        '''
        Make a copy of a Layer in the cortex.

        Args:
            iden (str): Layer iden to clone
            ldef (Optional[Dict]): Layer configuration overrides

        Note:
            This should only be called with a reasonably static Cortex
            due to possible races.
        '''
        layr = self.layers.get(iden, None)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=iden)

        ldef = ldef or {}
        ldef['iden'] = s_common.guid()
        ldef.setdefault('creator', self.auth.rootuser.iden)

        return await self._push('layer:clone', iden, ldef)

    @s_nexus.Pusher.onPush('layer:clone', passitem=True)
    async def _cloneLayer(self, iden, ldef, nexsitem):

        layr = self.layers.get(iden)
        if layr is None:
            return

        newiden = ldef.get('iden')
        if newiden in self.layers:
            return

        newpath = s_common.gendir(self.dirn, 'layers', newiden)
        await layr.clone(newpath)

        node = await self.hive.open(('cortex', 'layers', iden))
        copynode = await self.hive.open(('cortex', 'layers', newiden))

        layrinfo = await node.dict()
        copyinfo = await copynode.dict()
        for name, valu in layrinfo.items():
            await copyinfo.set(name, valu)

        for name, valu in ldef.items():
            await copyinfo.set(name, valu)

        copylayr = await self._initLayr(copyinfo, nexsoffs=nexsitem[0])

        creator = copyinfo.get('creator')
        user = await self.auth.reqUser(creator)
        await user.setAdmin(True, gateiden=newiden, logged=False)

        return await copylayr.pack()

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

    @s_nexus.Pusher.onPushAuto('storm:dmon:bump')
    async def bumpStormDmon(self, iden):
        ddef = self.stormdmonhive.get(iden)
        if ddef is None:
            return False

        if self.isactive:
            dmon = self.stormdmons.getDmon(iden)
            if dmon is not None:
                await dmon.bump()

        return True

    @s_nexus.Pusher.onPushAuto('storm:dmon:enable')
    async def enableStormDmon(self, iden):
        ddef = self.stormdmonhive.get(iden)
        if ddef is None:
            return False

        curv = ddef.get('enabled')

        ddef['enabled'] = True
        await self.stormdmonhive.set(iden, ddef)

        if self.isactive and not curv:
            dmon = self.stormdmons.getDmon(iden)
            await dmon.run()
        return True

    @s_nexus.Pusher.onPushAuto('storm:dmon:disable')
    async def disableStormDmon(self, iden):

        ddef = self.stormdmonhive.get(iden)
        if ddef is None:
            return False

        curv = ddef.get('enabled')

        ddef['enabled'] = False
        await self.stormdmonhive.set(iden, ddef)

        if self.isactive and curv:
            dmon = self.stormdmons.getDmon(iden)
            await dmon.stop()
        return True

    @s_nexus.Pusher.onPush('storm:dmon:add')
    async def _onAddStormDmon(self, ddef):
        iden = ddef['iden']

        dmon = self.stormdmons.getDmon(iden)
        if dmon is not None:
            return dmon.pack()

        if ddef.get('user') is None:
            user = await self.auth.getUserByName('root')
            ddef['user'] = user.iden

        dmon = await self.runStormDmon(iden, ddef)

        await self.stormdmonhive.set(iden, ddef)
        return dmon.pack()

    async def delStormDmon(self, iden):
        '''
        Stop and remove a storm dmon.
        '''
        ddef = await self.stormdmonhive.pop(iden)
        if ddef is None:
            mesg = f'No storm daemon exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        return await self._push('storm:dmon:del', iden)

    @s_nexus.Pusher.onPush('storm:dmon:del')
    async def _delStormDmon(self, iden):
        await self.stormdmons.popDmon(iden)

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    async def runStormDmon(self, iden, ddef):

        # validate ddef before firing task
        s_storm.reqValidDdef(ddef)

        dmon = self.stormdmons.getDmon(iden)
        if dmon is not None:
            return dmon

        await self.auth.reqUser(ddef['user'])

        # raises if parser failure
        self.getStormQuery(ddef.get('storm'))

        dmon = await self.stormdmons.addDmon(iden, ddef)

        return dmon

    async def getStormDmon(self, iden):
        return self.stormdmons.getDmonDef(iden)

    async def getStormDmons(self):
        return self.stormdmons.getDmonDefs()

    async def getStormDmonLog(self, iden):
        return self.stormdmons.getDmonRunlog(iden)

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

    async def getAxon(self):
        await self.axready.wait()
        return self.axon.iden

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
            doc = getattr(ctor, '__doc__', None)
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
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
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

    async def _addSynNodeEdits(self, snap, items):

        for item in items:
            item = s_common.unjsonsafe_nodeedits(item)
            await snap.applyNodeEdits(item)

    def getCoreMod(self, name):
        return self.modules.get(name)

    def getCoreMods(self):
        ret = []
        for modname, mod in self.modules.items():
            ret.append((modname, mod.conf))
        return ret

    def _initStormOpts(self, opts):
        if opts is None:
            opts = {}

        opts.setdefault('user', self.auth.rootuser.iden)
        return opts

    def _viewFromOpts(self, opts):

        user = self._userFromOpts(opts)

        viewiden = opts.get('view')
        if viewiden is None:
            viewiden = user.profile.get('cortex:view')

        if viewiden is None:
            viewiden = self.view.iden

        # For backwards compatibility, resolve references to old view iden == cortex.iden to the main view
        # TODO:  due to our migration policy, remove in 3.0.0
        if viewiden == self.iden: # pragma: no cover
            viewiden = self.view.iden

        view = self.views.get(viewiden)
        if view is None:
            raise s_exc.NoSuchView(iden=viewiden)

        user.confirm(('view', 'read'), gateiden=viewiden)

        return view

    def _userFromOpts(self, opts):

        if opts is None:
            return self.auth.rootuser

        useriden = opts.get('user')
        if useriden is None:
            return self.auth.rootuser

        user = self.auth.user(useriden)
        if user is None:
            mesg = f'No user found with iden: {useriden}'
            raise s_exc.NoSuchUser(mesg, iden=useriden)

        return user

    async def count(self, text, opts=None):

        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)

        i = 0
        async for _ in view.eval(text, opts=opts):
            i += 1

        return i

    async def storm(self, text, opts=None):
        '''
        '''
        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)
        async for mesg in view.storm(text, opts=opts):
            yield mesg

    async def callStorm(self, text, opts=None):
        opts = self._initStormOpts(opts)
        view = self._viewFromOpts(opts)
        return await view.callStorm(text, opts=opts)

    async def exportStorm(self, text, opts=None):
        opts = self._initStormOpts(opts)
        user = self._userFromOpts(opts)
        view = self._viewFromOpts(opts)

        await self.boss.promote('storm:export', user=user, info={'query': text})

        spooldict = await s_spooled.Dict.anit()
        async with await self.snap(user=user, view=view) as snap:

            async for pode in snap.iterStormPodes(text, opts=opts):
                await spooldict.set(pode[1]['iden'], pode)
                await asyncio.sleep(0)

            for iden, pode in spooldict.items():
                await asyncio.sleep(0)

                edges = []
                async for verb, n2iden in snap.iterNodeEdgesN1(s_common.uhex(iden)):
                    await asyncio.sleep(0)

                    if not spooldict.has(n2iden):
                        continue

                    edges.append((verb, n2iden))

                if edges:
                    pode[1]['edges'] = edges

                yield pode

    async def feedFromAxon(self, sha256, opts=None):

        opts = self._initStormOpts(opts)
        user = self._userFromOpts(opts)
        view = self._viewFromOpts(opts)

        await self.boss.promote('feeddata', user=user, info={'name': 'syn.nodes', 'sha256': sha256})

        # ensure that the user can make all node edits in the layer
        user.confirm(('node',), gateiden=view.layers[0].iden)

        q = s_queue.Queue(maxsize=10000)
        feedexc = None

        async with await s_base.Base.anit() as base:

            async def fill():
                nonlocal feedexc
                try:

                    async for item in self.axon.iterMpkFile(sha256):
                        await q.put(item)

                except Exception as e:
                    logger.exception(f'feedFromAxon.fill(): {e}')
                    feedexc = e

                finally:
                    await q.close()

            base.schedCoro(fill())

            count = 0
            async with await self.snap(user=user, view=view) as snap:

                # feed the items directly to syn.nodes
                async for items in q.slices(size=100):
                    async for node in self._addSynNodes(snap, items):
                        count += 1

                if feedexc is not None:
                    raise feedexc

        return count

    async def nodes(self, text, opts=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        if self.isfini: # pragma: no cover
            raise s_exc.IsFini()

        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)
        return await view.nodes(text, opts=opts)

    async def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield packed nodes.

        NOTE: This API is deprecated as of 2.0.0 and will be removed in 3.0.0
        '''
        s_common.deprecated('eval')
        opts = self._initStormOpts(opts)
        view = self._viewFromOpts(opts)
        async for node in view.eval(text, opts=opts):
            yield node

    async def stormlist(self, text, opts=None):
        return [m async for m in self.storm(text, opts=opts)]

    @s_cache.memoize(size=10000)
    def getStormQuery(self, text, mode='storm'):
        '''
        Parse storm query text and return a Query object.
        '''
        query = copy.deepcopy(s_parser.parseQuery(text, mode=mode))
        query.init(self)
        return query

    @contextlib.asynccontextmanager
    async def getStormRuntime(self, query, opts=None):

        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)
        user = self._userFromOpts(opts)

        async with await self.snap(user=user, view=view) as snap:
            with snap.getStormRuntime(query, opts=opts, user=user) as runt:
                yield runt

    async def reqValidStorm(self, text, opts=None):
        '''
        Parse a storm query to validate it.

        Args:
            text (str): The text of the Storm query to parse.
            opts (dict): A Storm options dictionary.

        Returns:
            True: If the query is valid.

        Raises:
            BadSyntaxError: If the query is invalid.
        '''
        if opts is None:
            opts = {}
        mode = opts.get('mode', 'storm')
        self.getStormQuery(text, mode)
        return True

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
        s_common.deprecated('Cortex.getCoreInfo')
        return {
            'version': synapse.version,
            'modeldef': self.model.getModelDefs(),
            'stormcmds': {cmd: {} for cmd in self.stormcmds.keys()},
        }

    async def getCoreInfoV2(self):
        return {
            'version': synapse.version,
            'modeldict': await self.getModelDict(),
            'stormdocs': await self.getStormDocs(),
        }

    async def getStormDocs(self):
        '''
        Get a struct containing the Storm Types documentation.

        Returns:
            dict: A Dictionary of storm documentation information.
        '''

        ret = {
            'libraries': s_stormtypes.registry.getLibDocs(),
            'types': s_stormtypes.registry.getTypeDocs(),
            # 'cmds': ...  # TODO - support cmd docs
            # 'packages': ...  # TODO - Support inline information for packages?
        }
        return ret

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

    async def addFeedData(self, name, items, *, viewiden=None):
        '''
        Add data using a feed/parser function.

        Args:
            name (str): The name of the feed record format.
            items (list): A list of items to ingest.
            iden (str): The iden of a view to use.
                If a view is not specified, the default view is used.
        '''

        view = self.getView(viewiden)
        if view is None:
            raise s_exc.NoSuchView(iden=viewiden)

        async with await self.snap(view=view) as snap:
            snap.strict = False
            await snap.addFeedData(name, items)

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
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
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
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise
        except Exception:
            logger.exception(f'module initCoreModule failed: {ctor}')
            self.modules.pop(ctor, None)
            return

        await self.fire('core:module:load', module=ctor)

        return modu

    async def _loadCoreMods(self):

        mods = []
        cmds = []
        mdefs = []

        for ctor in list(s_modules.coremods):
            await self._preLoadCoreModule(ctor, mods, cmds, mdefs)
        for ctor in self.conf.get('modules'):
            await self._preLoadCoreModule(ctor, mods, cmds, mdefs, custom=True)

        self.model.addDataModels(mdefs)
        [self.addStormCmd(c) for c in cmds]

    async def _preLoadCoreModule(self, ctor, mods, cmds, mdefs, custom=False):
        conf = None
        # allow module entry to be (ctor, conf) tuple
        if isinstance(ctor, (list, tuple)):
            ctor, conf = ctor

        modu = self._loadCoreModule(ctor, conf=conf)
        if modu is None:
            return

        mods.append(modu)

        try:
            await s_coro.ornot(modu.preCoreModule)
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise
        except Exception:
            logger.exception(f'module preCoreModule failed: {ctor}')
            self.modules.pop(ctor, None)
            return

        cmds.extend(modu.getStormCmds())
        model_defs = modu.getModelDefs()
        if custom:
            for _mdef, mnfo in model_defs:
                mnfo['custom'] = True
        mdefs.extend(model_defs)

    async def _initCoreMods(self):

        with s_provenance.claim('init', meth='_initCoreMods'):
            for ctor, modu in list(self.modules.items()):

                try:
                    await s_coro.ornot(modu.initCoreModule)
                except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
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

    async def addCronJob(self, cdef):
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
            incvals (Union[int, List[int]):
                A integer or a list of integers of the number of units

        Returns (bytes):
            An iden that can be used to later modify, query, and delete the job.

        Notes:
            reqs must have fields present or incunit must not be None (or both)
            The incunit if not None it must be larger in unit size than all the keys in all reqs elements.
            Non-recurring jobs may also have a req of 'now' which will cause the job to also execute immediately.
        '''
        s_agenda.reqValidCdef(cdef)

        incunit = cdef.get('incunit')
        reqs = cdef.get('reqs')

        try:
            if incunit is not None:
                if isinstance(incunit, (list, tuple)):
                    incunit = [s_agenda.TimeUnit.fromString(i) for i in incunit]
                else:
                    incunit = s_agenda.TimeUnit.fromString(incunit)
                cdef['incunit'] = incunit

            if isinstance(reqs, Mapping):
                reqs = self._convert_reqdict(reqs)
            else:
                reqs = [self._convert_reqdict(req) for req in reqs]

            if incunit is not None and s_agenda.TimeUnit.NOW in reqs:
                mesg = "Recurring jobs may not be scheduled to run 'now'"
                raise s_exc.BadConfValu(mesg)

            cdef['reqs'] = reqs
        except KeyError:
            raise s_exc.BadConfValu('Unrecognized time unit')

        cdef['iden'] = s_common.guid()

        return await self._push('cron:add', cdef)

    @s_nexus.Pusher.onPush('cron:add')
    async def _onAddCronJob(self, cdef):

        iden = cdef['iden']

        appt = self.agenda.appts.get(iden)
        if appt is not None:
            return appt.pack()

        user = await self.auth.reqUser(cdef['creator'])

        cdef = await self.agenda.add(cdef)

        await self.auth.addAuthGate(iden, 'cronjob')
        await user.setAdmin(True, gateiden=iden, logged=False)

        return cdef

    @s_nexus.Pusher.onPushAuto('cron:del')
    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        try:
            await self.agenda.delete(iden)
        except s_exc.NoSuchIden:
            return

        await self.auth.delAuthGate(iden)

    @s_nexus.Pusher.onPushAuto('cron:mod')
    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.mod(iden, query)

    @s_nexus.Pusher.onPushAuto('cron:enable')
    async def enableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.enable(iden)

    @s_nexus.Pusher.onPushAuto('cron:disable')
    async def disableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.disable(iden)

    async def listCronJobs(self):
        '''
        Get information about all the cron jobs accessible to the current user
        '''
        crons = []

        for _, cron in self.agenda.list():

            info = cron.pack()

            user = self.auth.user(cron.creator)
            info['username'] = user.name

            crons.append(info)

        return crons

    @s_nexus.Pusher.onPushAuto('cron:edit')
    async def editCronJob(self, iden, name, valu):
        '''
        Modify a cron job definition.
        '''
        appt = await self.agenda.get(iden)
        # TODO make this generic and check cdef

        if name == 'name':
            await appt.setName(str(valu))
            return appt.pack()

        if name == 'doc':
            await appt.setDoc(str(valu))
            return appt.pack()

        mesg = f'editCronJob name {name} is not supported for editing.'
        raise s_exc.BadArg(mesg=mesg)

    async def _enableMigrationMode(self):
        '''
        Prevents cron jobs and triggers from running
        '''
        self.agenda.enabled = False
        self.trigson = False

    async def _disableMigrationMode(self):
        '''
        Allows cron jobs and triggers to run
        '''
        if self.conf.get('cron:enable'):
            self.agenda.enabled = True

        if self.conf.get('trigger:enable'):
            self.trigson = True

    async def iterFormRows(self, layriden, form, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes of a single form, optionally (re)starting at startvalu.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            form (str):  A form name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        layr = self.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        async for item in layr.iterFormRows(form, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterPropRows(self, layriden, form, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular secondary property, optionally (re)starting at startvalu.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            form (str):  A form name.
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        layr = self.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        async for item in layr.iterPropRows(form, prop, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterUnivRows(self, layriden, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular universal property, optionally (re)starting at startvalu.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        layr = self.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        async for item in layr.iterUnivRows(prop, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterTagRows(self, layriden, tag, form=None, starttupl=None):
        '''
        Yields (buid, (valu, form)) values that match a tag and optional form, optionally (re)starting at starttupl.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            tag (str): the tag to match
            form (Optional[str]):  if present, only yields buids of nodes that match the form.
            starttupl (Optional[Tuple[buid, form]]):  if present, (re)starts the stream of values there.

        Returns:
            AsyncIterator[Tuple(buid, (valu, form))]

        Note:
            This yields (buid, (tagvalu, form)) instead of just buid, valu in order to allow resuming an interrupted
            call by feeding the last value retrieved into starttupl
        '''
        layr = self.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        async for item in layr.iterTagRows(tag, form=form, starttupl=starttupl):
            yield item

    async def iterTagPropRows(self, layriden, tag, prop, form=None, stortype=None, startvalu=None):
        '''
        Yields (buid, valu) that match a tag:prop, optionally (re)starting at startvalu.

        Args:
            layriden (str):  Iden of the layer to retrieve the nodes
            tag (str):  tag name
            prop (str):  prop name
            form (Optional[str]):  optional form name
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        layr = self.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(iden=layriden)

        async for item in layr.iterTagPropRows(tag, prop, form=form, stortype=stortype, startvalu=startvalu):
            yield item

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
