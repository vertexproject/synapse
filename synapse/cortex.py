import os
import copy
import regex
import asyncio
import logging
import textwrap
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
import synapse.lib.view as s_view
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.oauth as s_oauth
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.storm as s_storm
import synapse.lib.agenda as s_agenda
import synapse.lib.config as s_config
import synapse.lib.parser as s_parser
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.modules as s_modules
import synapse.lib.schemas as s_schemas
import synapse.lib.spooled as s_spooled
import synapse.lib.version as s_version
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.hashitem as s_hashitem
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.modelrev as s_modelrev
import synapse.lib.stormsvc as s_stormsvc
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.lib.crypto.rsa as s_rsa

# Importing these registers their commands
import synapse.lib.stormhttp as s_stormhttp  # NOQA
import synapse.lib.stormwhois as s_stormwhois  # NOQA

import synapse.lib.stormtypes as s_stormtypes

import synapse.lib.stormlib.aha as s_stormlib_aha  # NOQA
import synapse.lib.stormlib.env as s_stormlib_env  # NOQA
import synapse.lib.stormlib.gen as s_stormlib_gen  # NOQA
import synapse.lib.stormlib.gis as s_stormlib_gis  # NOQA
import synapse.lib.stormlib.hex as s_stormlib_hex  # NOQA
import synapse.lib.stormlib.log as s_stormlib_log  # NOQA
import synapse.lib.stormlib.xml as s_stormlib_xml  # NOQA
import synapse.lib.stormlib.auth as s_stormlib_auth  # NOQA
import synapse.lib.stormlib.cell as s_stormlib_cell  # NOQA
import synapse.lib.stormlib.imap as s_stormlib_imap  # NOQA
import synapse.lib.stormlib.ipv6 as s_stormlib_ipv6  # NOQA
import synapse.lib.stormlib.json as s_stormlib_json  # NOQA
import synapse.lib.stormlib.math as s_stormlib_math  # NOQA
import synapse.lib.stormlib.mime as s_stormlib_mime  # NOQA
import synapse.lib.stormlib.pack as s_stormlib_pack  # NOQA
import synapse.lib.stormlib.smtp as s_stormlib_smtp  # NOQA
import synapse.lib.stormlib.stix as s_stormlib_stix  # NOQA
import synapse.lib.stormlib.yaml as s_stormlib_yaml  # NOQA
import synapse.lib.stormlib.basex as s_stormlib_basex  # NOQA
import synapse.lib.stormlib.cache as s_stormlib_cache  # NOQA
import synapse.lib.stormlib.graph as s_stormlib_graph  # NOQA
import synapse.lib.stormlib.index as s_stormlib_index  # NOQA
import synapse.lib.stormlib.iters as s_stormlib_iters  # NOQA
import synapse.lib.stormlib.macro as s_stormlib_macro
import synapse.lib.stormlib.model as s_stormlib_model
import synapse.lib.stormlib.oauth as s_stormlib_oauth  # NOQA
import synapse.lib.stormlib.stats as s_stormlib_stats  # NOQA
import synapse.lib.stormlib.storm as s_stormlib_storm  # NOQA
import synapse.lib.stormlib.utils as s_stormlib_utils  # NOQA
import synapse.lib.stormlib.vault as s_stormlib_vault  # NOQA
import synapse.lib.stormlib.backup as s_stormlib_backup  # NOQA
import synapse.lib.stormlib.cortex as s_stormlib_cortex  # NOQA
import synapse.lib.stormlib.hashes as s_stormlib_hashes  # NOQA
import synapse.lib.stormlib.random as s_stormlib_random  # NOQA
import synapse.lib.stormlib.scrape as s_stormlib_scrape   # NOQA
import synapse.lib.stormlib.infosec as s_stormlib_infosec  # NOQA
import synapse.lib.stormlib.project as s_stormlib_project  # NOQA
import synapse.lib.stormlib.spooled as s_stormlib_spooled  # NOQA
import synapse.lib.stormlib.tabular as s_stormlib_tabular  # NOQA
import synapse.lib.stormlib.version as s_stormlib_version  # NOQA
import synapse.lib.stormlib.easyperm as s_stormlib_easyperm  # NOQA
import synapse.lib.stormlib.ethereum as s_stormlib_ethereum  # NOQA
import synapse.lib.stormlib.modelext as s_stormlib_modelext  # NOQA
import synapse.lib.stormlib.compression as s_stormlib_compression  # NOQA
import synapse.lib.stormlib.notifications as s_stormlib_notifications  # NOQA

logger = logging.getLogger(__name__)
stormlogger = logging.getLogger('synapse.storm')

'''
A Cortex implements the synapse hypergraph object.
'''

reqver = '>=0.2.0,<3.0.0'

# Constants returned in results from syncLayersEvents and syncIndexEvents
SYNC_NODEEDITS = 0  # A nodeedits: (<offs>, 0, <etyp>, (<etype args>), {<meta>})
SYNC_NODEEDIT = 1   # A nodeedit:  (<offs>, 0, <etyp>, (<etype args>))
SYNC_LAYR_ADD = 3   # A layer was added
SYNC_LAYR_DEL = 4   # A layer was deleted

MAX_NEXUS_DELTA = 3_600

reqValidTagModel = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'prune': {'type': 'number', 'minimum': 1},
        'regex': {'type': 'array', 'items': {'type': ['string', 'null']}},
    },
    'additionalProperties': False,
    'required': [],
})

reqValidStormMacro = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'pattern': '^.{1,491}$'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        # user kept for backward compat. remove eventually...
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'desc': {'type': 'string', 'default': ''},
        'storm': {'type': 'string'},
        'created': {'type': 'number'},
        'updated': {'type': 'number'},
        'permissions': s_msgpack.deepcopy(s_schemas.easyPermSchema),
    },
    'required': [
        'name',
        'iden',
        'user',
        'storm',
        'creator',
        'created',
        'updated',
        'permissions',
    ],
})

def cmprkey_indx(x):
    return x[1]

def cmprkey_buid(x):
    return x[1][1]

async def wrap_liftgenr(iden, genr):
    async for indx, buid, sode in genr:
        yield iden, (indx, buid), sode

class CortexAxonMixin:

    async def prepare(self):
        await self.cell.axready.wait()
        await s_coro.ornot(super().prepare)

    def getAxon(self):
        return self.cell.axon

    async def getAxonInfo(self):
        return self.cell.axoninfo

class CortexAxonHttpHasV1(CortexAxonMixin, s_axon.AxonHttpHasV1):
    pass

class CortexAxonHttpDelV1(CortexAxonMixin, s_axon.AxonHttpDelV1):
    pass

class CortexAxonHttpUploadV1(CortexAxonMixin, s_axon.AxonHttpUploadV1):
    pass

class CortexAxonHttpBySha256V1(CortexAxonMixin, s_axon.AxonHttpBySha256V1):
    pass

class CortexAxonHttpBySha256InvalidV1(CortexAxonMixin, s_axon.AxonHttpBySha256InvalidV1):
    pass

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

    @s_cell.adminapi()
    async def saveLayerNodeEdits(self, layriden, edits, meta):
        return await self.cell.saveLayerNodeEdits(layriden, edits, meta)

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

    async def _reqDefLayerAllowed(self, perms):
        view = self.cell.getView()
        wlyr = view.layers[0]
        self.user.confirm(perms, gateiden=wlyr.iden)

    async def addNode(self, form, valu, props=None):
        '''
        Deprecated in 2.0.0.
        '''
        s_common.deprecated('CoreApi.addNode')
        async with await self.cell.snap(user=self.user) as snap:
            self.user.confirm(('node', 'add', form), gateiden=snap.wlyr.iden)
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
        s_common.deprecated('CoreApi.addNodes')

        # First check that that user may add each form
        done = {}
        for node in nodes:

            formname = node[0][0]
            if done.get(formname):
                continue

            await self._reqDefLayerAllowed(('node', 'add', formname))
            done[formname] = True

        async with await self.cell.snap(user=self.user) as snap:

            snap.strict = False
            async for node in snap.addNodes(nodes):

                if node is not None:
                    node = node.pack()

                yield node

    async def getFeedFuncs(self):
        '''
        Get a list of Cortex feed functions.

        Notes:
            Each feed dictionary has the name of the feed function, the
            full docstring for the feed function, and the first line of
            the docstring broken out in their own keys for easy use.

        Returns:
            tuple: A tuple of dictionaries.
        '''
        return await self.cell.getFeedFuncs()

    async def addFeedData(self, name, items, *, viewiden=None):

        view = self.cell.getView(viewiden, user=self.user)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view iden={viewiden}', iden=viewiden)

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

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.

        Yields:
            ((str,dict)): Storm messages.
        '''
        opts = self._reqValidStormOpts(opts)

        async for mesg in self.cell.storm(text, opts=opts):
            yield mesg

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

    async def syncLayerNodeEdits(self, offs, layriden=None, wait=True):
        '''
        Yield (indx, mesg) nodeedit sets for the given layer beginning at offset.

        Once caught up, this API will begin yielding nodeedits in real-time.
        The generator will only terminate on network disconnect or if the
        consumer falls behind the max window size of 10,000 nodeedit messages.
        '''
        layr = self.cell.getLayer(layriden)
        if layr is None:
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

        self.user.confirm(('sync',), gateiden=layr.iden)

        async for item in self.cell.syncLayerNodeEdits(layr.iden, offs, wait=wait):
            yield item

    async def getPropNorm(self, prop, valu, typeopts=None):
        '''
        Get the normalized property value based on the Cortex data model.

        Args:
            prop (str): The property to normalize.
            valu: The value to normalize.
            typeopts: A Synapse type opts dictionary used to further normalize the value.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchProp: If the prop does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        return await self.cell.getPropNorm(prop, valu, typeopts=typeopts)

    async def getTypeNorm(self, name, valu, typeopts=None):
        '''
        Get the normalized type value based on the Cortex data model.

        Args:
            name (str): The type to normalize.
            valu: The value to normalize.
            typeopts: A Synapse type opts dictionary used to further normalize the value.

        Returns:
            (tuple): A two item tuple, containing the normed value and the info dictionary.

        Raises:
            s_exc.NoSuchType: If the type does not exist.
            s_exc.BadTypeValu: If the value fails to normalize.
        '''
        return await self.cell.getTypeNorm(name, valu, typeopts=typeopts)

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
        if not s_grammar.isBasePropNoPivprop(prop):
            mesg = f'Invalid prop name {prop}'
            raise s_exc.BadPropDef(prop=prop, mesg=mesg)
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
        if not s_grammar.isBasePropNoPivprop(name):
            mesg = f'Invalid prop name {name}'
            raise s_exc.BadPropDef(name=name, mesg=mesg)
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
        if not s_grammar.isBasePropNoPivprop(name):
            mesg = f'Invalid prop name {name}'
            raise s_exc.BadPropDef(name=name, mesg=mesg)
        return await self.cell.addTagProp(name, tdef, info)

    async def delTagProp(self, name):
        '''
        Remove a previously added tag property.
        '''
        self.user.confirm(('model', 'tagprop', 'del'))
        return await self.cell.delTagProp(name)

    async def addStormPkg(self, pkgdef, verify=False):
        self.user.confirm(('pkg', 'add'))
        return await self.cell.addStormPkg(pkgdef, verify=verify)

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

    async def getAxonUpload(self):
        self.user.confirm(('axon', 'upload'))
        await self.cell.axready.wait()
        upload = await self.cell.axon.upload()
        return await s_axon.UpLoadProxy.anit(self.link, upload)

    async def getAxonBytes(self, sha256):
        self.user.confirm(('axon', 'get'))
        await self.cell.axready.wait()
        async for byts in self.cell.axon.get(s_common.uhex(sha256)):
            yield byts

    @s_cell.adminapi()
    async def getUserNotif(self, indx):
        return await self.cell.getUserNotif(indx)

    @s_cell.adminapi()
    async def delUserNotif(self, indx):
        return await self.cell.delUserNotif(indx)

    @s_cell.adminapi()
    async def addUserNotif(self, useriden, mesgtype, mesgdata=None):
        return await self.cell.addUserNotif(useriden, mesgtype, mesgdata=mesgdata)

    @s_cell.adminapi()
    async def iterUserNotifs(self, useriden, size=None):
        async for item in self.cell.iterUserNotifs(useriden, size=size):
            yield item

    @s_cell.adminapi()
    async def watchAllUserNotifs(self, offs=None):
        async for item in self.cell.watchAllUserNotifs(offs=offs):
            yield item

    @s_cell.adminapi()
    async def getHttpExtApiByPath(self, path):
        return await self.cell.getHttpExtApiByPath(path)

class Cortex(s_oauth.OAuthMixin, s_cell.Cell):  # type: ignore
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
    confbase['mirror']['hidedocs'] = False  # type: ignore
    confbase['mirror']['hidecmdl'] = False  # type: ignore

    confdefs = {
        'axon': {
            'description': 'A telepath URL for a remote axon.',
            'type': 'string'
        },
        'jsonstor': {
            'description': 'A telepath URL for a remote jsonstor.',
            'type': 'string'
        },
        'cron:enable': {
            'default': True,
            'description': 'Deprecated. This option no longer controls cron execution and will be removed in Synapse 3.0.',
            'type': 'boolean'
        },
        'trigger:enable': {
            'default': True,
            'description': 'Deprecated. This option no longer controls trigger execution and will be removed in Synapse 3.0.',
            'type': 'boolean'
        },
        'layer:lmdb:map_async': {
            'default': True,
            'description': 'Deprecated. This value is ignored.',
            'type': 'boolean',
            'hidecmdl': True,
            'hideconf': True,
        },
        'layer:lmdb:max_replay_log': {
            'default': 10000,
            'description': 'Deprecated. This value is ignored.',
            'type': 'integer',
            'hidecmdl': True,
            'hideconf': True,
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
        'provenance:en': {  # TODO: Remove in 3.0.0
            'default': False,
            'description': 'This no longer does anything.',
            'type': 'boolean',
            'hideconf': True,
        },
        'max:nodes': {
            'description': 'Maximum number of nodes which are allowed to be stored in a Cortex.',
            'type': 'integer',
            'minimum': 1,
            'hidecmdl': True,
        },
        'modules': {
            'default': [],
            'description': 'Deprecated. A list of module classes to load.',
            'type': 'array'
        },
        'storm:log': {
            'default': False,
            'description': 'Log storm queries via system logger.',
            'type': 'boolean'
        },
        'storm:log:level': {
            'default': 'INFO',
            'description': 'Logging log level to emit storm logs at.',
            'type': [
                'integer',
                'string',
            ],
        },
        'storm:interface:search': {
            'default': True,
            'description': 'Enable Storm search interfaces for lookup mode.',
            'type': 'boolean',
        },
        'storm:interface:scrape': {
            'default': True,
            'description': 'Enable Storm scrape interfaces when using $lib.scrape APIs.',
            'type': 'boolean',
        },
        'http:proxy': {
            'description': 'An aiohttp-socks compatible proxy URL to use storm HTTP API.',
            'type': 'string',
        },
        'tls:ca:dir': {
            'description': 'An optional directory of CAs which are added to the TLS CA chain for Storm HTTP API calls.',
            'type': 'string',
        },
    }

    cellapi = CoreApi
    viewapi = s_view.ViewApi
    layerapi = s_layer.LayerApi

    viewctor = s_view.View.anit
    layrctor = s_layer.Layer.anit

    # phase 2 - service storage
    async def initServiceStorage(self):

        # NOTE: we may not make *any* nexus actions in this method
        self.macrodb = self.slab.initdb('storm:macros')
        self.httpextapidb = self.slab.initdb('http:ext:apis')

        if self.inaugural:
            self.cellinfo.set('cortex:version', s_version.version)

        corevers = self.cellinfo.get('cortex:version')
        s_version.reqVersion(corevers, reqver, exc=s_exc.BadStorageVersion,
                             mesg='cortex version in storage is incompatible with running software')

        self.viewmeta = self.slab.initdb('view:meta')

        self.views = {}
        self.layers = {}
        self.viewsbylayer = collections.defaultdict(list)

        self.modules = {}
        self.feedfuncs = {}
        self.stormcmds = {}

        self.maxnodes = self.conf.get('max:nodes')
        self.nodecount = 0

        self.migration = False
        self._migration_lock = asyncio.Lock()

        self.stormmods = {}     # name: mdef
        self.stormpkgs = {}     # name: pkgdef
        self.stormvars = None   # type: s_lmdbslab.SafeKeyVal

        self.svcsbyiden = {}
        self.svcsbyname = {}
        self.svcsbysvcname = {}  # remote name, not local name

        self._propSetHooks = {}
        self._runtLiftFuncs = {}
        self._runtPropSetFuncs = {}
        self._runtPropDelFuncs = {}

        self.tagvalid = s_cache.FixedCache(self._isTagValid, size=1000)
        self.tagprune = s_cache.FixedCache(self._getTagPrune, size=1000)

        self.querycache = s_cache.FixedCache(self._getStormQuery, size=10000)

        self.stormpool = None
        self.stormpoolurl = None
        self.stormpoolopts = None

        self.libroot = (None, {}, {})
        self.stormlibs = []

        self.bldgbuids = {}  # buid -> (Node, Event)  Nodes under construction

        self.axon = None  # type: s_axon.AxonApi
        self.axready = asyncio.Event()
        self.axoninfo = {}

        self.view = None  # The default/main view

        self._cortex_permdefs = []
        self._initCorePerms()

        # Reset the storm:log:level from the config value to an int for internal use.
        self.conf['storm:log:level'] = s_common.normLogLevel(self.conf.get('storm:log:level'))
        self.stormlog = self.conf.get('storm:log')
        self.stormloglvl = self.conf.get('storm:log:level')

        # generic fini handler for the Cortex
        self.onfini(self._onCoreFini)

        self.cortexdata = self.slab.getSafeKeyVal('cortex')

        await self._initCoreInfo()
        self._initStormLibs()
        self._initFeedFuncs()

        self.modsbyiface = {}
        self.stormiface_search = self.conf.get('storm:interface:search')
        self.stormiface_scrape = self.conf.get('storm:interface:scrape')

        self._initCortexHttpApi()
        self._exthttpapis = {}  # iden -> adef; relies on cpython ordered dictionary behavior.
        self._exthttpapiorder = b'exthttpapiorder'
        self._exthttpapicache = s_cache.FixedCache(self._getHttpExtApiByPath, size=1000)
        self._initCortexExtHttpApi()

        self.model = s_datamodel.Model(core=self)

        await self._bumpCellVers('cortex:extmodel', (
            (1, self._migrateTaxonomyIface),
        ), nexs=False)

        await self._bumpCellVers('cortex:storage', (
            (1, self._storUpdateMacros),
            (4, self._storCortexHiveMigration),
        ), nexs=False)

        # Perform module loading
        await self._loadCoreMods()
        await self._loadExtModel()
        await self._initStormCmds()

        # Initialize our storage and views
        await self._initCoreAxon()
        await self._initJsonStor()

        await self._initCoreLayers()
        await self._initCoreViews()
        self.onfini(self._finiStor)
        await self._initCoreQueues()

        self.addHealthFunc(self._cortexHealth)

        await self._initOAuthManager()

        self.stormdmondefs = self.cortexdata.getSubKeyVal('storm:dmons:')
        self.stormdmons = await s_storm.DmonManager.anit(self)
        self.onfini(self.stormdmons)

        self.agenda = await s_agenda.Agenda.anit(self)
        self.onfini(self.agenda)

        await self._initStormGraphs()

        await self._initRuntFuncs()

        self.tagmeta = self.cortexdata.getSubKeyVal('tagmeta:')
        self.cmddefs = self.cortexdata.getSubKeyVal('storm:cmds:')
        self.pkgdefs = self.cortexdata.getSubKeyVal('storm:packages:')
        self.svcdefs = self.cortexdata.getSubKeyVal('storm:services:')

        await self._initDeprLocks()
        await self._warnDeprLocks()

        # Finalize coremodule loading & give svchive a shot to load
        await self._initPureStormCmds()

        self.dynitems.update({
            'cron': self.agenda,
            'cortex': self,
            'multiqueue': self.multiqueue,
        })

        # TODO - Remove this in 3.0.0
        ag = await self.auth.addAuthGate('cortex', 'cortex')
        for useriden in ag.gateusers.keys():
            user = self.auth.user(useriden)
            if user is None:
                continue

            mesg = f'User {useriden} ({user.name}) has a rule on the "cortex" authgate. This authgate is not used ' \
                   f'for permission checks and will be removed in Synapse v3.0.0.'
            logger.warning(mesg, extra=await self.getLogExtra(user=useriden, username=user.name))
        for roleiden in ag.gateroles.keys():
            role = self.auth.role(roleiden)
            if role is None:
                continue

            mesg = f'Role {roleiden} ({role.name}) has a rule on the "cortex" authgate. This authgate is not used ' \
                   f'for permission checks and will be removed in Synapse v3.0.0.'
            logger.warning(mesg, extra=await self.getLogExtra(role=roleiden, rolename=role.name))

        self._initVaults()

    async def _storCortexHiveMigration(self):

        logger.warning('migrating Cortex data out of hive')

        viewdefs = self.cortexdata.getSubKeyVal('view:info:')
        async with await self.hive.open(('cortex', 'views')) as viewnodes:
            for view_iden, node in viewnodes:
                viewdict = await node.dict()
                viewinfo = viewdict.pack()
                viewinfo.setdefault('iden', view_iden)
                viewdefs.set(view_iden, viewinfo)

                trigdict = self.cortexdata.getSubKeyVal(f'view:{view_iden}:trigger:')
                async with await node.open(('triggers',)) as trignodes:
                    for iden, trig in trignodes:
                        valu = trig.valu
                        if valu.get('view', s_common.novalu) != view_iden:
                            valu['view'] = view_iden
                        trigdict.set(iden, valu)

        layrdefs = self.cortexdata.getSubKeyVal('layer:info:')
        async with await self.hive.open(('cortex', 'layers')) as layrnodes:
            for iden, node in layrnodes:
                layrdict = await node.dict()
                layrinfo = layrdict.pack()
                pushs = layrinfo.get('pushs', {})
                if pushs:
                    for pdef in pushs.values():
                        pdef.setdefault('chunk:size', s_const.layer_pdef_csize)
                        pdef.setdefault('queue:size', s_const.layer_pdef_qsize)

                pulls = layrinfo.get('pulls', {})
                if pulls:
                    pulls = layrinfo.get('pulls', {})
                    for pdef in pulls.values():
                        pdef.setdefault('chunk:size', s_const.layer_pdef_csize)
                        pdef.setdefault('queue:size', s_const.layer_pdef_qsize)

                layrdefs.set(iden, layrinfo)

        migrs = (
            (('agenda', 'appts'), 'agenda:appt:'),
            (('cortex', 'tagmeta'), 'tagmeta:'),
            (('cortex', 'storm', 'cmds'), 'storm:cmds:'),
            (('cortex', 'storm', 'vars'), 'storm:vars:'),
            (('cortex', 'storm', 'dmons'), 'storm:dmons:'),
            (('cortex', 'storm', 'packages'), 'storm:packages:'),
            (('cortex', 'storm', 'services'), 'storm:services:'),
            (('cortex', 'model', 'forms'), 'model:forms:'),
            (('cortex', 'model', 'props'), 'model:props:'),
            (('cortex', 'model', 'univs'), 'model:univs:'),
            (('cortex', 'model', 'tagprops'), 'model:tagprops:'),
            (('cortex', 'model', 'deprlocks'), 'model:deprlocks:'),
        )

        for hivepath, kvpref in migrs:
            subkv = self.cortexdata.getSubKeyVal(kvpref)
            async with await self.hive.open(hivepath) as hivenode:
                for name, node in hivenode:
                    subkv.set(name, node.valu)

        logger.warning('...Cortex data migration complete!')

    async def _viewNomergeToProtected(self):
        for view in self.views.values():
            nomerge = view.info.get('nomerge', False)
            await view.setViewInfo('protected', nomerge)
            await view.setViewInfo('nomerge', None)

    async def _storUpdateMacros(self):
        for name, node in await self.hive.open(('cortex', 'storm', 'macros')):

            try:

                info = {
                    'name': name,
                    'storm': node.valu.get('storm'),
                }

                user = node.valu.get('user')
                if user is not None:
                    info['user'] = user

                created = node.valu.get('created')
                if created is not None:
                    info['created'] = created

                edited = node.valu.get('edited')
                if edited is not None:
                    info['updated'] = edited

                    if info.get('created') is None:
                        info['created'] = edited

                mdef = self._initStormMacro(info)

                await self._addStormMacro(mdef)

            except Exception as e:
                logger.exception(f'Macro migration error for macro: {name} (skipped).')

    def getStormMacro(self, name, user=None):

        if not name:
            raise s_exc.BadArg(mesg=f'Macro names must be at least 1 character long')

        if len(name) > 491:
            raise s_exc.BadArg(mesg='Macro names may only be up to 491 chars.')

        byts = self.slab.get(name.encode(), db=self.macrodb)
        if byts is None:
            return None

        mdef = s_msgpack.un(byts)

        if user is not None:
            mesg = f'User requires read permission on macro: {name}.'
            self._reqEasyPerm(mdef, user, s_cell.PERM_READ, mesg=mesg)

        return mdef

    def reqStormMacro(self, name, user=None):

        mdef = self.getStormMacro(name)
        if mdef is None:
            raise s_exc.NoSuchName(mesg=f'Macro name not found: {name}')

        if user is not None:
            mesg = f'User requires read permission on macro: {name}.'
            self._reqEasyPerm(mdef, user, s_cell.PERM_READ, mesg=mesg)

        return mdef

    def _reqStormMacroPerm(self, user, name, level):
        mdef = self.reqStormMacro(name)
        mesg = f'User requires {s_cell.permnames.get(level)} permission on macro: {name}'

        if level == s_cell.PERM_EDIT and (
            user.allowed(('storm', 'macro', 'edit')) or
            user.allowed(('storm', 'macro', 'admin'))):
            return mdef

        if level == s_cell.PERM_ADMIN and user.allowed(('storm', 'macro', 'admin')):
            return mdef

        self._reqEasyPerm(mdef, user, level, mesg=mesg)
        return mdef

    async def addStormMacro(self, mdef, user=None):

        if user is None:
            user = self.auth.rootuser

        user.confirm(('storm', 'macro', 'add'), default=True)

        mdef = self._initStormMacro(mdef, user=user)

        reqValidStormMacro(mdef)

        return await self._push('storm:macro:add', mdef)

    def _initStormMacro(self, mdef, user=None):

        if user is None:
            user = self.auth.rootuser

        mdef['iden'] = s_common.guid()

        now = s_common.now()

        mdef.setdefault('updated', now)
        mdef.setdefault('created', now)

        useriden = mdef.get('user', user.iden)

        mdef['user'] = useriden
        mdef['creator'] = useriden

        mdef.setdefault('storm', '')
        self._initEasyPerm(mdef)

        mdef['permissions']['users'][useriden] = s_cell.PERM_ADMIN

        return mdef

    @s_nexus.Pusher.onPush('storm:macro:add')
    async def _addStormMacro(self, mdef):
        name = mdef.get('name')
        reqValidStormMacro(mdef)

        # idempotency protection...
        oldv = self.getStormMacro(name)
        if oldv is not None and oldv.get('iden') != mdef.get('iden'):
            raise s_exc.BadArg(mesg=f'Duplicate macro name: {name}')

        self.slab.put(name.encode(), s_msgpack.en(mdef), db=self.macrodb)
        await self.feedBeholder('storm:macro:add', {'macro': mdef})
        return mdef

    async def delStormMacro(self, name, user=None):

        if user is not None:
            self._reqStormMacroPerm(user, name, s_cell.PERM_ADMIN)

        return await self._push('storm:macro:del', name)

    @s_nexus.Pusher.onPush('storm:macro:del')
    async def _delStormMacro(self, name):
        if not name:
            raise s_exc.BadArg(mesg=f'Macro names must be at least 1 character long')

        byts = self.slab.pop(name.encode(), db=self.macrodb)

        if byts is not None:
            macro = s_msgpack.un(byts)
            await self.feedBeholder('storm:macro:del', {'name': name, 'iden': macro.get('iden')})
            return macro

    async def modStormMacro(self, name, info, user=None):
        if user is not None:
            self._reqStormMacroPerm(user, name, s_cell.PERM_EDIT)
        return await self._push('storm:macro:mod', name, info)

    @s_nexus.Pusher.onPush('storm:macro:mod')
    async def _modStormMacro(self, name, info):

        mdef = self.getStormMacro(name)
        if mdef is None:
            return

        mdef.update(info)

        reqValidStormMacro(mdef)

        newname = info.get('name')
        if newname is not None and newname != name:

            byts = self.slab.get(newname.encode(), db=self.macrodb)
            if byts is not None:
                raise s_exc.DupName(mesg=f'A macro named {newname} already exists!', name=newname)

            self.slab.put(newname.encode(), s_msgpack.en(mdef), db=self.macrodb)
            self.slab.pop(name.encode(), db=self.macrodb)
        else:
            self.slab.put(name.encode(), s_msgpack.en(mdef), db=self.macrodb)

        await self.feedBeholder('storm:macro:mod', {'macro': mdef, 'info': info})
        return mdef

    async def setStormMacroPerm(self, name, scope, iden, level, user=None):

        if user is not None:
            self._reqStormMacroPerm(user, name, s_cell.PERM_ADMIN)

        return await self._push('storm:macro:set:perm', name, scope, iden, level)

    @s_nexus.Pusher.onPush('storm:macro:set:perm')
    async def _setStormMacroPerm(self, name, scope, iden, level):

        mdef = self.reqStormMacro(name)
        await self._setEasyPerm(mdef, scope, iden, level)

        reqValidStormMacro(mdef)

        self.slab.put(name.encode(), s_msgpack.en(mdef), db=self.macrodb)

        info = {
            'scope': scope,
            'iden': iden,
            'level': level
        }

        await self.feedBeholder('storm:macro:set:perm', {'macro': mdef, 'info': info})
        return mdef

    async def getStormMacros(self, user=None):

        retn = []

        for lkey, byts in self.slab.scanByFull(db=self.macrodb):

            await asyncio.sleep(0)

            mdef = s_msgpack.un(byts)

            if user is not None and not self._hasEasyPerm(mdef, user, s_cell.PERM_READ):
                continue

            retn.append(mdef)

        return retn

    async def getStormIfaces(self, name):

        mods = self.modsbyiface.get(name)
        if mods is not None:
            return mods

        mods = []
        for moddef in self.stormmods.values():

            ifaces = moddef.get('interfaces')
            if ifaces is None:
                continue

            if name not in ifaces:
                continue

            mods.append(moddef)

        self.modsbyiface[name] = tuple(mods)
        return mods

    def _initCorePerms(self):
        self._cortex_permdefs.extend((
            {'perm': ('model', 'form', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding extended model forms.'},
            {'perm': ('model', 'form', 'add', '<form>'), 'gate': 'cortex',
             'desc': 'Controls access to adding specific extended model forms.',
             'ex': 'model.form.add._foo:bar'},
            {'perm': ('model', 'form', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting extended model forms.'},
            {'perm': ('model', 'form', 'del', '<form>'), 'gate': 'cortex',
             'desc': 'Controls access to deleting specific extended model forms.',
             'ex': 'model.form.del._foo:bar'},

            {'perm': ('model', 'type', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding extended model types.'},
            {'perm': ('model', 'type', 'add', '<type>'), 'gate': 'cortex',
             'desc': 'Controls access to adding specific extended model types.',
             'ex': 'model.type.add._foo:bar'},
            {'perm': ('model', 'type', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting extended model types.'},
            {'perm': ('model', 'type', 'del', '<type>'), 'gate': 'cortex',
             'desc': 'Controls access to deleting specific extended model types.',
             'ex': 'model.type.del._foo:bar'},

            {'perm': ('model', 'prop', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding extended model properties.'},
            {'perm': ('model', 'prop', 'add', '<form>'), 'gate': 'cortex',
             'desc': 'Controls access to adding specific extended model properties.',
             'ex': 'model.prop.add._foo:bar'},
            {'perm': ('model', 'prop', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting extended model properties and values.'},
            {'perm': ('model', 'prop', 'del', '<form>'), 'gate': 'cortex',
             'desc': 'Controls access to deleting specific extended model properties and values.',
             'ex': 'model.prop.del._foo:bar'},

            {'perm': ('model', 'tagprop', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding extended model tag properties and values.'},
            {'perm': ('model', 'tagprop', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting extended model tag properties and values.'},

            {'perm': ('model', 'univ', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding extended model universal properties.'},
            {'perm': ('model', 'univ', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting extended model universal properties and values.'},

            {'perm': ('node',), 'gate': 'layer',
             'desc': 'Controls all node edits in a layer.'},
            {'perm': ('node', 'add'), 'gate': 'layer',
             'desc': 'Controls adding any form of node in a layer.'},
            {'perm': ('node', 'del'), 'gate': 'layer',
             'desc': 'Controls removing any form of node in a layer.'},

            {'perm': ('node', 'add', '<form>'), 'gate': 'layer',
             'ex': 'node.add.inet:ipv4',
             'desc': 'Controls adding a specific form of node in a layer.'},
            {'perm': ('node', 'del', '<form>'), 'gate': 'layer',
             'desc': 'Controls removing a specific form of node in a layer.'},

            {'perm': ('node', 'edge', 'add'), 'gate': 'layer',
             'desc': 'Controls adding light edges to a node.'},
            {'perm': ('node', 'edge', 'del'), 'gate': 'layer',
             'desc': 'Controls adding light edges to a node.'},

            {'perm': ('node', 'edge', 'add', '<verb>'), 'gate': 'layer',
             'desc': 'Controls adding a specific light edge to a node.'},
            {'perm': ('node', 'edge', 'del', '<verb>'), 'gate': 'layer',
             'desc': 'Controls adding a specific light edge to a node.'},

            {'perm': ('node', 'tag'), 'gate': 'layer',
             'desc': 'Controls editing any tag on any node in a layer.'},
            {'perm': ('node', 'tag', 'add'), 'gate': 'layer',
             'desc': 'Controls adding any tag on any node in a layer.'},
            {'perm': ('node', 'tag', 'del'), 'gate': 'layer',
             'desc': 'Controls removing any tag on any node in a layer.'},

            {'perm': ('node', 'tag', 'add', '<tag...>'), 'gate': 'layer',
             'ex': 'node.tag.add.cno.mal.redtree',
             'desc': 'Controls adding a specific tag on any node in a layer.'},
            {'perm': ('node', 'tag', 'del', '<tag...>'), 'gate': 'layer',
             'ex': 'node.tag.del.cno.mal.redtree',
             'desc': 'Controls removing a specific tag on any node in a layer.'},

            {'perm': ('node', 'prop'), 'gate': 'layer',
             'desc': 'Controls editing any prop on any node in the layer.'},

            {'perm': ('node', 'prop', 'set'), 'gate': 'layer',
             'desc': 'Controls setting any prop on any node in a layer.'},
            {'perm': ('node', 'prop', 'set', '<form>'), 'gate': 'layer',
             'ex': 'node.prop.set.inet:ipv4',
             'desc': 'Controls setting any property on a form of node in a layer.'},
            {'perm': ('node', 'prop', 'set', '<form>', '<prop>'), 'gate': 'layer',
             'ex': 'node.prop.set.inet:ipv4.asn',
             'desc': 'Controls setting a specific property on a form of node in a layer.'},

            {'perm': ('node', 'prop', 'del'), 'gate': 'layer',
             'desc': 'Controls removing any prop on any node in a layer.'},
            {'perm': ('node', 'prop', 'del', '<form>'), 'gate': 'layer',
             'ex': 'node.prop.del.inet:ipv4',
             'desc': 'Controls removing any property from a form of node in a layer.'},
            {'perm': ('node', 'prop', 'del', '<form>', '<prop>'), 'gate': 'layer',
             'ex': 'node.prop.del.inet:ipv4.asn',
             'desc': 'Controls removing a specific property from a form of node in a layer.'},

            {'perm': ('node', 'data', 'set'), 'gate': 'layer',
             'desc': 'Permits a user to set node data in a given layer.'},
            {'perm': ('node', 'data', 'set', '<key>'), 'gate': 'layer',
              'ex': 'node.data.set.hehe',
             'desc': 'Permits a user to set node data in a given layer for a specific key.'},
            {'perm': ('node', 'data', 'pop'), 'gate': 'layer',
             'desc': 'Permits a user to remove node data in a given layer.'},
            {'perm': ('node', 'data', 'pop', '<key>'), 'gate': 'layer',
             'ex': 'node.data.pop.hehe',
             'desc': 'Permits a user to remove node data in a given layer for a specific key.'},

            {'perm': ('pkg', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to adding storm packages.'},
            {'perm': ('pkg', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to deleting storm packages.'},

            {'perm': ('storm', 'asroot', 'cmd', '<cmdname>'), 'gate': 'cortex',
            'desc': 'Controls running storm commands requiring root privileges.',
             'ex': 'storm.asroot.cmd.movetag'},
            {'perm': ('storm', 'asroot', 'mod', '<modname>'), 'gate': 'cortex',
            'desc': 'Controls importing modules requiring root privileges.',
             'ex': 'storm.asroot.cmd.synapse-misp.privsep'},

            {'perm': ('storm', 'graph', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to add a storm graph.',
             'default': True},
            {'perm': ('storm', 'macro', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to add a storm macro.',
             'default': True},
            {'perm': ('storm', 'macro', 'admin'), 'gate': 'cortex',
             'desc': 'Controls access to edit/set/delete a storm macro.'},
            {'perm': ('storm', 'macro', 'edit'), 'gate': 'cortex',
             'desc': 'Controls access to edit a storm macro.'},

            {'perm': ('task', 'get'), 'gate': 'cortex',
             'desc': 'Controls access to view other users tasks.'},
            {'perm': ('task', 'del'), 'gate': 'cortex',
             'desc': 'Controls access to terminate other users tasks.'},

            {'perm': ('view',), 'gate': 'cortex',
             'desc': 'Controls all view permissions.'},
            {'perm': ('view', 'add'), 'gate': 'cortex',
             'desc': 'Controls access to add a new view including forks.'},
            {'perm': ('view', 'del'), 'gate': 'view',
             'desc': 'Controls access to delete a view.'},
            {'perm': ('view', 'fork'), 'gate': 'view', 'default': True,
             'desc': 'Controls access to fork a view.'},
            {'perm': ('view', 'read'), 'gate': 'view',
             'desc': 'Controls read access to view.'},
            {'perm': ('view', 'set', '<setting>'), 'gate': 'view',
             'desc': 'Controls access to change view settings.',
             'ex': 'view.set.name'},

            {'perm': ('axon', 'upload'), 'gate': 'cortex',
             'desc': 'Controls the ability to upload a file to the Axon.'},
            {'perm': ('axon', 'get'), 'gate': 'cortex',
             'desc': 'Controls the ability to retrieve a file from the Axon.'},
            {'perm': ('axon', 'has'), 'gate': 'cortex',
             'desc': 'Controls the ability to check if the Axon contains a file.'},
            {'perm': ('axon', 'del'), 'gate': 'cortex',
             'desc': 'Controls the ability to remove a file from the Axon.'},
        ))
        for pdef in self._cortex_permdefs:
            s_schemas.reqValidPermDef(pdef)

    def _getPermDefs(self):

        permdefs = list(s_cell.Cell._getPermDefs(self))
        permdefs.extend(self._cortex_permdefs)

        for spkg in self._getStormPkgs():
            permdefs.extend(spkg.get('perms', ()))

        for (path, ctor) in self.stormlibs:
            permdefs.extend(ctor._storm_lib_perms)

        permdefs.sort(key=lambda x: x['perm'])

        return tuple(permdefs)

    def _setPropSetHook(self, name, hook):
        self._propSetHooks[name] = hook

    async def _callPropSetHook(self, node, prop, norm):
        hook = self._propSetHooks.get(prop.full)
        if hook is None:
            return
        await hook(node, prop, norm)

    async def _execCellUpdates(self):

        await self._bumpCellVers('cortex:defaults', (
            (1, self._addAllLayrRead),
            (2, self._viewNomergeToProtected),
        ))

    async def _addAllLayrRead(self):
        layriden = self.getView().layers[0].iden
        role = await self.auth.getRoleByName('all')
        await role.addRule((True, ('layer', 'read')), gateiden=layriden)

    async def initServiceRuntime(self):

        # do any post-nexus initialization here...
        if self.isactive:
            await self._checkNexsIndx()

        await self._initCoreMods()

        if self.isactive:
            await self._checkLayerModels()

        self.addActiveCoro(self.agenda.runloop)

        await self._initStormDmons()
        await self._initStormSvcs()

        # share ourself via the cell dmon as "cortex"
        # for potential default remote use
        self.dmon.share('cortex', self)

    async def initServiceActive(self):

        await self.stormdmons.start()

        async def _runMigrations():
            # Run migrations when this cortex becomes active. This is to prevent
            # migrations getting skipped in a zero-downtime upgrade path
            # (upgrade mirror, promote mirror).
            await self._checkLayerModels()

            # Once migrations are complete, start the view and layer tasks.
            for view in self.views.values():
                await view.initTrigTask()
                await view.initMergeTask()

            for layer in self.layers.values():
                await layer.initLayerActive()

        self.runActiveTask(_runMigrations())

        await self.initStormPool()

    async def initServicePassive(self):

        await self.stormdmons.stop()

        for view in self.views.values():
            await view.finiTrigTask()
            await view.finiMergeTask()

        for layer in self.layers.values():
            await layer.initLayerPassive()

        await self.finiStormPool()

    async def initStormPool(self):

        try:

            byts = self.slab.get(b'storm:pool', db='cell:conf')
            if byts is None:
                return

            url, opts = s_msgpack.un(byts)

            self.stormpoolurl = url
            self.stormpoolopts = opts

            async def onlink(proxy, urlinfo):
                _url = s_urlhelp.sanitizeUrl(s_telepath.zipurl(urlinfo))
                logger.debug(f'Stormpool client connected to {_url}')

            self.stormpool = await s_telepath.open(url, onlink=onlink)

            # make this one a fini weakref vs the fini() handler
            self.onfini(self.stormpool)

        except Exception as e:  # pragma: no cover
            logger.exception(f'Error starting stormpool, it will not be available: {e}')

    async def finiStormPool(self):

        if self.stormpool is not None:
            await self.stormpool.fini()
            self.stormpool = None

    async def getStormPool(self):
        byts = self.slab.get(b'storm:pool', db='cell:conf')
        if byts is None:
            return None
        return s_msgpack.un(byts)

    @s_nexus.Pusher.onPushAuto('storm:pool:set')
    async def setStormPool(self, url, opts):

        s_schemas.reqValidStormPoolOpts(opts)

        info = (url, opts)
        self.slab.put(b'storm:pool', s_msgpack.en(info), db='cell:conf')

        if self.isactive:
            await self.finiStormPool()
            await self.initStormPool()

    @s_nexus.Pusher.onPushAuto('storm:pool:del')
    async def delStormPool(self):

        self.slab.pop(b'storm:pool', db='cell:conf')

        if self.isactive:
            await self.finiStormPool()

    @s_nexus.Pusher.onPushAuto('model:lock:prop')
    async def setPropLocked(self, name, locked):
        prop = self.model.reqProp(name)
        self.modellocks.set(f'prop/{name}', locked)
        prop.locked = locked

    @s_nexus.Pusher.onPushAuto('model:lock:univ')
    async def setUnivLocked(self, name, locked):
        prop = self.model.reqUniv(name)
        self.modellocks.set(f'univ/{name}', locked)
        for prop in self.model.getAllUnivs(name):
            prop.locked = locked

    @s_nexus.Pusher.onPushAuto('model:lock:tagprop')
    async def setTagPropLocked(self, name, locked):
        prop = self.model.reqTagProp(name)
        self.modellocks.set(f'tagprop/{name}', locked)
        prop.locked = locked

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

        self.deprlocks.set(name, locked)

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

            # Skip universal properties on other props
            if not prop.isform and prop.univ is not None:
                continue

            retn[prop.full] = prop.locked

        return retn

    async def _warnDeprLocks(self):
        # Check for deprecated properties which are unused and unlocked
        deprs = await self.getDeprLocks()

        count = 0

        for propname, locked in deprs.items():
            if locked:
                continue

            prop = self.model.props.get(propname)

            for layr in self.layers.values():
                if not prop.isform and prop.isuniv:
                    if await layr.getUnivPropCount(prop.name, maxsize=1):
                        break

                else:
                    if await layr.getPropCount(propname, maxsize=1):
                        break

                    if await layr.getPropCount(prop.form.name, prop.name, maxsize=1):
                        break
            else:
                count += 1

        if count:
            mesg = f'Detected {count} deprecated properties unlocked and not in use, '
            mesg += 'recommend locking (https://v.vtx.lk/deprlock).'
            logger.warning(mesg)

    async def reqValidStormGraph(self, gdef):
        for filt in gdef.get('filters', ()):
            await self.getStormQuery(filt)

        for pivo in gdef.get('pivots', ()):
            await self.getStormQuery(pivo)

        for form, rule in gdef.get('forms', {}).items():
            if form != '*' and self.model.form(form) is None:
                raise s_exc.NoSuchForm.init(form)

            for filt in rule.get('filters', ()):
                await self.getStormQuery(filt)

            for pivo in rule.get('pivots', ()):
                await self.getStormQuery(pivo)

    async def addStormGraph(self, gdef, user=None):

        if user is None:
            user = self.auth.rootuser

        user.confirm(('storm', 'graph', 'add'), default=True)

        self._initEasyPerm(gdef)

        now = s_common.now()

        gdef['iden'] = s_common.guid()
        gdef['scope'] = 'user'
        gdef['creator'] = user.iden
        gdef['created'] = now
        gdef['updated'] = now
        gdef['permissions']['users'][user.iden] = s_cell.PERM_ADMIN

        s_schemas.reqValidGdef(gdef)

        await self.reqValidStormGraph(gdef)

        return await self._push('storm:graph:add', gdef)

    @s_nexus.Pusher.onPush('storm:graph:add')
    async def _addStormGraph(self, gdef):
        s_schemas.reqValidGdef(gdef)

        await self.reqValidStormGraph(gdef)

        if gdef['scope'] == 'power-up':
            mesg = 'Power-up graph projections may only be added by power-ups.'
            raise s_exc.SynErr(mesg=mesg)

        iden = gdef['iden']
        if self.graphs.get(iden) is not None:
            return

        self.graphs.set(iden, gdef)

        await self.feedBeholder('storm:graph:add', {'gdef': gdef})
        return copy.deepcopy(gdef)

    def _reqStormGraphPerm(self, user, iden, level):
        gdef = self.graphs.get(iden)
        if gdef is None:
            gdef = self.pkggraphs.get(iden)

        if gdef is None:
            mesg = f'No graph projection with iden {iden} exists!'
            raise s_exc.NoSuchIden(mesg=mesg)

        if gdef['scope'] == 'power-up' and level > s_cell.PERM_READ:
            mesg = 'Power-up graph projections may not be modified.'
            raise s_exc.AuthDeny(mesg=mesg, user=user.iden, username=user.name)

        if user is not None:
            mesg = f'User requires {s_cell.permnames.get(level)} permission on graph: {iden}.'
            self._reqEasyPerm(gdef, user, level, mesg=mesg)

        return gdef

    async def delStormGraph(self, iden, user=None):
        self._reqStormGraphPerm(user, iden, s_cell.PERM_ADMIN)
        return await self._push('storm:graph:del', iden)

    @s_nexus.Pusher.onPush('storm:graph:del')
    async def _delStormGraph(self, iden):
        gdef = self.graphs.pop(iden, None)
        if gdef is not None:
            await self.feedBeholder('storm:graph:del', {'iden': iden})
            return gdef

    async def getStormGraph(self, iden, user=None):
        gdef = self._reqStormGraphPerm(user, iden, s_cell.PERM_READ)
        return copy.deepcopy(gdef)

    async def getStormGraphs(self, user=None):

        for _, gdef in self.graphs.items():

            await asyncio.sleep(0)

            if user is not None and self._hasEasyPerm(gdef, user, s_cell.PERM_READ):
                yield copy.deepcopy(gdef)

        for gdef in self.pkggraphs.values():

            await asyncio.sleep(0)

            if user is not None and self._hasEasyPerm(gdef, user, s_cell.PERM_READ):
                yield copy.deepcopy(gdef)

    async def modStormGraph(self, iden, info, user=None):
        self._reqStormGraphPerm(user, iden, s_cell.PERM_EDIT)
        info['updated'] = s_common.now()
        return await self._push('storm:graph:mod', iden, info)

    @s_nexus.Pusher.onPush('storm:graph:mod')
    async def _modStormGraph(self, iden, info):

        gdef = self._reqStormGraphPerm(None, iden, s_cell.PERM_EDIT)
        gdef = copy.deepcopy(gdef)
        gdef.update(info)

        s_schemas.reqValidGdef(gdef)

        await self.reqValidStormGraph(gdef)

        self.graphs.set(iden, gdef)

        await self.feedBeholder('storm:graph:mod', {'gdef': gdef})
        return copy.deepcopy(gdef)

    async def setStormGraphPerm(self, gden, scope, iden, level, user=None):
        self._reqStormGraphPerm(user, gden, s_cell.PERM_ADMIN)
        return await self._push('storm:graph:set:perm', gden, scope, iden, level, s_common.now())

    @s_nexus.Pusher.onPush('storm:graph:set:perm')
    async def _setStormGraphPerm(self, gden, scope, iden, level, utime):

        gdef = self._reqStormGraphPerm(None, gden, s_cell.PERM_ADMIN)
        gdef = copy.deepcopy(gdef)
        gdef['updated'] = utime

        await self._setEasyPerm(gdef, scope, iden, level)

        s_schemas.reqValidGdef(gdef)

        self.graphs.set(gden, gdef)

        await self.feedBeholder('storm:graph:set:perm', {'gdef': gdef})
        return copy.deepcopy(gdef)

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
        return await self._push('queue:puts', name, items)

    @s_nexus.Pusher.onPush('queue:puts', passitem=True)
    async def _coreQueuePuts(self, name, items, nexsitem):
        nexsoff, nexsmesg = nexsitem
        return await self.multiqueue.puts(name, items, reqid=nexsoff)

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
            prune - A number that determines how many levels of pruning are desired.

        Examples:
            await core.setTagModel("cno.cve", "regex", (None, None, "[0-9]{4}", "[0-9]{5}"))

        '''
        meta = self.tagmeta.get(tagname)
        if meta is None:
            meta = {}

        meta[name] = valu
        reqValidTagModel(meta)

        self.tagmeta.set(tagname, meta)

        # clear cached entries
        if name == 'regex':
            self.tagvalid.clear()
        elif name == 'prune':
            self.tagprune.clear()

    @s_nexus.Pusher.onPushAuto('tag:model:del')
    async def delTagModel(self, tagname):
        '''
        Delete all the model specification properties for a tag.

        Arguments:
            tagname (str): The name of the tag.
        '''
        self.tagmeta.pop(tagname)
        self.tagvalid.clear()
        self.tagprune.clear()

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

        meta = self.tagmeta.get(tagname)
        if meta is None:
            return None

        retn = meta.pop(name, None)
        self.tagmeta.set(tagname, meta)

        if name == 'regex':
            self.tagvalid.clear()
        elif name == 'prune':
            self.tagprune.clear()

        return retn

    def isTagValid(self, tagname):
        '''
        Check if a tag name is valid according to tag model regular expressions.

        Returns:
            (bool): True if the tag is valid.
        '''
        return self.tagvalid.get(tagname)

    def _isTagValid(self, tagname):

        parts = s_chop.tagpath(tagname)
        for tag in s_chop.tags(tagname):

            meta = self.tagmeta.get(tag)
            if meta is None:
                continue

            regx = meta.get('regex')
            if regx is None:
                continue

            for i in range(min(len(regx), len(parts))):

                if regx[i] is None:
                    continue

                if not regex.fullmatch(regx[i], parts[i]):
                    mesg = f'Tag part ({parts[i]}) of tag ({tagname}) does not match the tag model regex: [{regx[i]}]'
                    return (False, mesg)

        return (True, None)

    async def getTagPrune(self, tagname):
        return self.tagprune.get(tagname)

    def _getTagPrune(self, tagname):

        prune = []

        pruning = 0
        for tag in s_chop.tags(tagname):

            if pruning:
                pruning -= 1
                prune.append(tag)
                continue

            meta = self.tagmeta.get(tag)
            if meta is None:
                continue

            pruning = meta.get('prune', 0)
            if pruning:
                pruning -= 1
                prune.append(tag)

        # if we dont reach the final tag for pruning, skip it.
        if prune and not prune[-1] == tagname:
            return ()

        return tuple(prune)

    async def getTagModel(self, tagname):
        '''
        Retrieve the tag model specification for a tag.

        Returns:
            (dict): The tag model specification or None.
        '''
        retn = self.tagmeta.get(tagname)
        if retn is not None:
            return dict(retn)

    async def listTagModel(self):
        '''
        Retrieve a list of the tag model specifications.

        Returns:
            ([(str, dict), ...]): A list of tag model specification tuples.
        '''
        return list(self.tagmeta.items())

    async def _finiStor(self):
        await asyncio.gather(*[view.fini() for view in self.views.values()])
        await asyncio.gather(*[layr.fini() for layr in self.layers.values()])

    async def _initRuntFuncs(self):

        async def onSetTrigDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            node.snap.user.confirm(('trigger', 'set', 'doc'), gateiden=iden)
            await node.snap.view.setTriggerInfo(iden, 'doc', valu)
            node.props[prop.name] = valu

        async def onSetTrigName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            node.snap.user.confirm(('trigger', 'set', 'name'), gateiden=iden)
            await node.snap.view.setTriggerInfo(iden, 'name', valu)
            node.props[prop.name] = valu

        async def onSetCronDoc(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            node.snap.user.confirm(('cron', 'set', 'doc'), gateiden=iden)
            await self.editCronJob(iden, 'doc', valu)
            node.props[prop.name] = valu

        async def onSetCronName(node, prop, valu):
            valu = str(valu)
            iden = node.ndef[1]
            node.snap.user.confirm(('cron', 'set', 'name'), gateiden=iden)
            await self.editCronJob(iden, 'name', valu)
            node.props[prop.name] = valu

        self.addRuntPropSet('syn:cron:doc', onSetCronDoc)
        self.addRuntPropSet('syn:cron:name', onSetCronName)

        self.addRuntPropSet('syn:trigger:doc', onSetTrigDoc)
        self.addRuntPropSet('syn:trigger:name', onSetTrigName)

    async def _initStormDmons(self):

        for iden, ddef in self.stormdmondefs.items():
            try:
                await self.runStormDmon(iden, ddef)

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception as e:
                logger.warning(f'initStormDmon ({iden}) failed: {e}')

    async def _initStormSvcs(self):

        for iden, sdef in self.svcdefs.items():

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

    async def _initStormGraphs(self):
        path = os.path.join(self.dirn, 'slabs', 'graphs.lmdb')

        slab = await s_lmdbslab.Slab.anit(path)
        self.onfini(slab.fini)

        self.pkggraphs = {}
        self.graphs = s_lmdbslab.SlabDict(slab, db=slab.initdb('graphs'))

    async def setStormCmd(self, cdef):
        await self._reqStormCmd(cdef)
        return await self._push('cmd:set', cdef)

    @s_nexus.Pusher.onPush('cmd:set')
    async def _onSetStormCmd(self, cdef):
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
        self._setStormCmd(cdef)
        self.cmddefs.set(name, cdef)

    async def _reqStormCmd(self, cdef):

        name = cdef.get('name')
        if not s_grammar.isCmdName(name):
            raise s_exc.BadCmdName(name=name)

        await self.getStormQuery(cdef.get('storm'))

    async def _getStorNodes(self, buid, layers):
        # NOTE: This API lives here to make it easy to optimize
        #       the cluster case to minimize round trips
        return [await layr.getStorNode(buid) for layr in layers]

    async def _genSodeList(self, buid, sodes, layers, filtercmpr=None):
        sodelist = []

        if filtercmpr is not None:
            filt = True
            for layr in layers[-1::-1]:
                sode = sodes.get(layr.iden)
                if sode is None:
                    sode = await layr.getStorNode(buid)
                    if filt and filtercmpr(sode):
                        return
                else:
                    filt = False
                sodelist.append((layr.iden, sode))

            return (buid, sodelist[::-1])

        for layr in layers:
            sode = sodes.get(layr.iden)
            if sode is None:
                sode = await layr.getStorNode(buid)
            sodelist.append((layr.iden, sode))

        return (buid, sodelist)

    async def _mergeSodes(self, layers, genrs, cmprkey, filtercmpr=None, reverse=False):
        lastbuid = None
        sodes = {}
        async for layr, (_, buid), sode in s_common.merggenr2(genrs, cmprkey, reverse=reverse):
            if not buid == lastbuid or layr in sodes:
                if lastbuid is not None:
                    sodelist = await self._genSodeList(lastbuid, sodes, layers, filtercmpr)
                    if sodelist is not None:
                        yield sodelist
                    sodes.clear()
                lastbuid = buid
            sodes[layr] = sode

        if lastbuid is not None:
            sodelist = await self._genSodeList(lastbuid, sodes, layers, filtercmpr)
            if sodelist is not None:
                yield sodelist

    async def _liftByDataName(self, name, layers):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByDataName(name):
                yield (buid, [(layr, sode)])
            return

        genrs = []
        for layr in layers:
            genrs.append(wrap_liftgenr(layr.iden, layr.liftByDataName(name)))

        async for sodes in self._mergeSodes(layers, genrs, cmprkey_buid):
            yield sodes

    async def _liftByProp(self, form, prop, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByProp(form, prop, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        genrs = []
        for layr in layers:
            genrs.append(wrap_liftgenr(layr.iden, layr.liftByProp(form, prop, reverse=reverse)))

        def filtercmpr(sode):
            if (props := sode.get('props')) is None:
                return False

            return props.get(prop) is not None

        async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, filtercmpr, reverse=reverse):
            yield sodes

    async def _liftByPropValu(self, form, prop, cmprvals, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByPropValu(form, prop, cmprvals, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        def filtercmpr(sode):
            props = sode.get('props')
            if props is None:
                return False
            return props.get(prop) is not None

        for cval in cmprvals:
            genrs = []
            for layr in layers:
                genrs.append(wrap_liftgenr(layr.iden, layr.liftByPropValu(form, prop, (cval,), reverse=reverse)))

            async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, filtercmpr, reverse=reverse):
                yield sodes

    async def _liftByPropArray(self, form, prop, cmprvals, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByPropArray(form, prop, cmprvals, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        if prop is None:
            filtercmpr = None
        else:
            def filtercmpr(sode):
                props = sode.get('props')
                if props is None:
                    return False
                return props.get(prop) is not None

        for cval in cmprvals:
            genrs = []
            for layr in layers:
                genrs.append(wrap_liftgenr(layr.iden, layr.liftByPropArray(form, prop, (cval,), reverse=reverse)))

            async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, filtercmpr, reverse=reverse):
                yield sodes

    async def _liftByFormValu(self, form, cmprvals, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByFormValu(form, cmprvals, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        for cval in cmprvals:
            genrs = []
            for layr in layers:
                genrs.append(wrap_liftgenr(layr.iden, layr.liftByFormValu(form, (cval,), reverse=reverse)))

            async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, reverse=reverse):
                yield sodes

    async def _liftByTag(self, tag, form, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByTag(tag, form, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        if form is None:
            def filtercmpr(sode):
                tags = sode.get('tags')
                if tags is None:
                    return False
                return tags.get(tag) is not None
        else:
            filtercmpr = None

        genrs = []
        for layr in layers:
            genrs.append(wrap_liftgenr(layr.iden, layr.liftByTag(tag, form, reverse=reverse)))

        async for sodes in self._mergeSodes(layers, genrs, cmprkey_buid, filtercmpr, reverse=reverse):
            yield sodes

    async def _liftByTagValu(self, tag, cmpr, valu, form, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByTagValu(tag, cmpr, valu, form, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        def filtercmpr(sode):
            tags = sode.get('tags')
            if tags is None:
                return False
            return tags.get(tag) is not None

        genrs = []
        for layr in layers:
            genrs.append(wrap_liftgenr(layr.iden, layr.liftByTagValu(tag, cmpr, valu, form, reverse=reverse)))

        async for sodes in self._mergeSodes(layers, genrs, cmprkey_buid, filtercmpr, reverse=reverse):
            yield sodes

    async def _liftByTagProp(self, form, tag, prop, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByTagProp(form, tag, prop, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        genrs = []
        for layr in layers:
            genrs.append(wrap_liftgenr(layr.iden, layr.liftByTagProp(form, tag, prop, reverse=reverse)))

        def filtercmpr(sode):
            if (tagprops := sode.get('tagprops')) is None:
                return False

            if (props := tagprops.get(tag)) is None:
                return False

            return props.get(prop) is not None

        async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, filtercmpr, reverse=reverse):
            yield sodes

    async def _liftByTagPropValu(self, form, tag, prop, cmprvals, layers, reverse=False):
        if len(layers) == 1:
            layr = layers[0].iden
            async for _, buid, sode in layers[0].liftByTagPropValu(form, tag, prop, cmprvals, reverse=reverse):
                yield (buid, [(layr, sode)])
            return

        def filtercmpr(sode):
            tagprops = sode.get('tagprops')
            if tagprops is None:
                return False
            props = tagprops.get(tag)
            if not props:
                return False
            return props.get(prop) is not None

        for cval in cmprvals:
            genrs = []
            for layr in layers:
                genrs.append(wrap_liftgenr(layr.iden, layr.liftByTagPropValu(form, tag, prop, (cval,), reverse=reverse)))

            async for sodes in self._mergeSodes(layers, genrs, cmprkey_indx, filtercmpr, reverse=reverse):
                yield sodes

    def _setStormCmd(self, cdef):
        '''
        Note:
            No change control or persistence
        '''
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

    def _popStormCmd(self, name):
        self.stormcmds.pop(name, None)

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

        cdef = self.cmddefs.get(name)
        if cdef is None:
            mesg = f'The storm command ({name}) is not dynamic.'
            raise s_exc.CantDelCmd(mesg=mesg)

        self.cmddefs.pop(name)
        self.stormcmds.pop(name, None)

    async def addStormPkg(self, pkgdef, verify=False):
        '''
        Add the given storm package to the cortex.

        This will store the package for future use.
        '''
        # do validation before nexs...
        if verify:
            pkgcopy = s_msgpack.deepcopy(pkgdef)
            codesign = pkgcopy.pop('codesign', None)
            if codesign is None:
                mesg = 'Storm package is not signed!'
                raise s_exc.BadPkgDef(mesg=mesg)

            certbyts = codesign.get('cert')
            if certbyts is None:
                mesg = 'Storm package has no certificate!'
                raise s_exc.BadPkgDef(mesg=mesg)

            signbyts = codesign.get('sign')
            if signbyts is None:
                mesg = 'Storm package has no signature!'
                raise s_exc.BadPkgDef(mesg=mesg)

            try:
                cert = self.certdir.loadCertByts(certbyts.encode('utf-8'))
            except s_exc.BadCertBytes as e:
                raise s_exc.BadPkgDef(mesg='Storm package has malformed certificate!') from None

            try:
                self.certdir.valCodeCert(certbyts.encode())
            except s_exc.BadCertVerify as e:
                mesg = e.get('mesg')
                if mesg:
                    mesg = f'Storm package has invalid certificate: {mesg}'
                else:
                    mesg = 'Storm package has invalid certificate!'
                raise s_exc.BadPkgDef(mesg=mesg) from None

            pubk = s_rsa.PubKey(cert.public_key())
            if not pubk.verifyitem(pkgcopy, s_common.uhex(signbyts)):
                mesg = 'Storm package signature does not match!'
                raise s_exc.BadPkgDef(mesg=mesg)

        await self._normStormPkg(pkgdef)
        return await self._push('pkg:add', pkgdef)

    @s_nexus.Pusher.onPush('pkg:add')
    async def _addStormPkg(self, pkgdef):
        name = pkgdef.get('name')
        olddef = self.pkgdefs.get(name, None)
        if olddef is not None:
            if s_hashitem.hashitem(pkgdef) != s_hashitem.hashitem(olddef):
                self._dropStormPkg(olddef)
            else:
                return

        self.loadStormPkg(pkgdef)
        self.pkgdefs.set(name, pkgdef)

        self._clearPermDefs()

        gates = []
        perms = []
        pkgperms = pkgdef.get('perms')
        if pkgperms:
            gates = [p['gate'] for p in pkgperms if p.get('gate') is not None]
            perms = [p['perm'] for p in pkgperms if p.get('perm') is not None]
        await self.feedBeholder('pkg:add', pkgdef, gates=gates, perms=perms)

    async def delStormPkg(self, name):
        pkgdef = self.pkgdefs.get(name)
        if pkgdef is None:
            mesg = f'No storm package: {name}.'
            raise s_exc.NoSuchPkg(mesg=mesg)

        return await self._push('pkg:del', name)

    @s_nexus.Pusher.onPush('pkg:del')
    async def _delStormPkg(self, name):
        '''
        Delete a storm package by name.
        '''
        pkgdef = self.pkgdefs.pop(name, None)
        if pkgdef is None:
            return

        self._dropStormPkg(pkgdef)

        self._clearPermDefs()

        gates = []
        perms = []
        pkgperms = pkgdef.get('perms')
        if pkgperms:
            gates = [p['gate'] for p in pkgperms if p.get('gate') is not None]
            perms = [p['perm'] for p in pkgperms if p.get('perm') is not None]
        await self.feedBeholder('pkg:del', {'name': name}, gates=gates, perms=perms)

    async def getStormPkg(self, name):
        return copy.deepcopy(self.stormpkgs.get(name))

    async def getStormPkgs(self):
        return self._getStormPkgs()

    def _getStormPkgs(self):
        return copy.deepcopy(list(self.pkgdefs.values()))

    async def getStormMods(self):
        return copy.deepcopy(self.stormmods)

    async def getStormMod(self, name, reqvers=None):

        mdef = copy.deepcopy(self.stormmods.get(name))
        if mdef is None or reqvers is None:
            return mdef

        pkgvers = mdef.get('pkgvers')
        if pkgvers is None:
            mesg = f'getStormMod: requested storm module {name}@{reqvers}' \
                    'has no version information to check.'
            logger.warning(mesg)
            return

        if isinstance(pkgvers, tuple):
            pkgvers = '%d.%d.%d' % pkgvers

        if s_version.matches(pkgvers, reqvers):
            return mdef

    def getDataModel(self):
        return self.model

    async def _tryLoadStormPkg(self, pkgdef):
        try:
            await self._normStormPkg(pkgdef, validstorm=False)
            self.loadStormPkg(pkgdef)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception as e:
            name = pkgdef.get('name', '')
            logger.exception(f'Error loading pkg: {name}, {str(e)}')

    async def verifyStormPkgDeps(self, pkgdef):

        result = {
            'requires': [],
            'conflicts': [],
        }

        deps = pkgdef.get('depends')
        if deps is None:
            return result

        requires = deps.get('requires', ())
        for require in requires:

            pkgname = require.get('name')
            cmprvers = require.get('version')

            item = require.copy()
            item.setdefault('desc', None)

            cpkg = await self.getStormPkg(pkgname)

            if cpkg is None:
                item.update({'ok': False, 'actual': None})
            else:
                cver = cpkg.get('version')
                ok = s_version.matches(cver, cmprvers)
                item.update({'ok': ok, 'actual': cver})

            result['requires'].append(item)

        conflicts = deps.get('conflicts', ())
        for conflict in conflicts:

            pkgname = conflict.get('name')
            cmprvers = conflict.get('version')

            item = conflict.copy()
            item.setdefault('version', None)
            item.setdefault('desc', None)

            cpkg = await self.getStormPkg(pkgname)

            if cpkg is None:
                item.update({'ok': True, 'actual': None})
            else:
                cver = cpkg.get('version')
                ok = cmprvers is not None and not s_version.matches(cver, cmprvers)
                item.update({'ok': ok, 'actual': cver})

            result['conflicts'].append(item)

        return result

    async def _reqStormPkgDeps(self, pkgdef):

        name = pkgdef.get('name')

        deps = await self.verifyStormPkgDeps(pkgdef)

        for require in deps['requires']:

            if require['ok']:
                continue

            option = ' '
            if require.get('optional'):
                option = ' optional '

            mesg = f'Storm package {name}{option}requirement {require.get("name")}{require.get("version")} is currently unmet.'
            logger.debug(mesg)

        for conflict in deps['conflicts']:

            if conflict['ok']:
                continue

            mesg = f'Storm package {name} conflicts with {conflict.get("name")}{conflict.get("version") or ""}.'
            raise s_exc.StormPkgConflicts(mesg=mesg)

    def _reqStormPkgVarType(self, pkgname, vartype):
        if isinstance(vartype, (tuple, list)):
            for vtyp in vartype:
                self._reqStormPkgVarType(pkgname, vtyp)
        else:
            if vartype not in self.model.types:
                mesg = f'Storm package {pkgname} has unknown config var type {vartype}.'
                raise s_exc.NoSuchType(mesg=mesg, type=vartype)

    async def _normStormPkg(self, pkgdef, validstorm=True):
        '''
        Normalize and validate a storm package (optionally storm code).
        '''
        version = pkgdef.get('version')
        if isinstance(version, (tuple, list)):
            pkgdef['version'] = '%d.%d.%d' % tuple(version)

        await self._reqStormPkgDeps(pkgdef)

        pkgname = pkgdef.get('name')

        # Check synapse version requirement
        reqversion = pkgdef.get('synapse_version')
        if reqversion is not None:
            mesg = f'Storm package {pkgname} requires Synapse {reqversion} but ' \
                   f'Cortex is running {s_version.version}'
            s_version.reqVersion(s_version.version, reqversion, mesg=mesg)

        elif (minversion := pkgdef.get('synapse_minversion')) is not None:
            # This is for older packages that might not have the
            # `synapse_version` field.
            # TODO: Remove this whole else block after Synapse 3.0.0.
            if tuple(minversion) > s_version.version:
                mesg = f'Storm package {pkgname} requires Synapse {minversion} but ' \
                       f'Cortex is running {s_version.version}'
                raise s_exc.BadVersion(mesg=mesg)

        # Validate storm contents from modules and commands
        mods = pkgdef.get('modules', ())
        cmds = pkgdef.get('commands', ())
        onload = pkgdef.get('onload')
        svciden = pkgdef.get('svciden')

        if onload is not None and validstorm:
            await self.getStormQuery(onload)

        for mdef in mods:
            mdef.setdefault('modconf', {})
            if svciden:
                mdef['modconf']['svciden'] = svciden

            if validstorm:
                modtext = mdef.get('storm')
                await self.getStormQuery(modtext)

        for cdef in cmds:
            cdef['pkgname'] = pkgname
            cdef.setdefault('cmdconf', {})
            if svciden:
                cdef['cmdconf']['svciden'] = svciden

            if validstorm:
                cmdtext = cdef.get('storm')
                await self.getStormQuery(cmdtext)

            if cdef.get('forms') is not None:
                name = cdef.get('name')
                mesg = f"Storm command definition 'forms' key is deprecated and will be removed " \
                       f"in 3.0.0 (command {name} in package {pkgname})"
                logger.warning(mesg, extra=await self.getLogExtra(name=name, pkgname=pkgname))

        for gdef in pkgdef.get('graphs', ()):
            gdef['iden'] = s_common.guid((pkgname, gdef.get('name')))
            gdef['scope'] = 'power-up'
            gdef['power-up'] = pkgname

            if validstorm:
                await self.reqValidStormGraph(gdef)

        # Validate package def (post normalization)
        s_schemas.reqValidPkgdef(pkgdef)

        for configvar in pkgdef.get('configvars', ()):
            self._reqStormPkgVarType(pkgname, configvar.get('type'))

    # N.B. This function is intentionally not async in order to prevent possible user race conditions for code
    # executing outside of the nexus lock.
    def loadStormPkg(self, pkgdef):
        '''
        Load a storm package into the storm library for this cortex.

        NOTE: This will *not* persist the package (allowing service dynamism).
        '''
        self.modsbyiface.clear()
        name = pkgdef.get('name')

        mods = pkgdef.get('modules', ())
        cmds = pkgdef.get('commands', ())

        # now actually load...
        self.stormpkgs[name] = pkgdef

        pkgvers = pkgdef.get('version')

        # copy the mods dict and smash the ref so
        # updates are atomic and dont effect running
        # storm queries.
        stormmods = self.stormmods.copy()
        for mdef in mods:
            mdef = mdef.copy()
            modname = mdef.get('name')
            mdef['pkgvers'] = pkgvers
            stormmods[modname] = mdef

        self.stormmods = stormmods

        for cdef in cmds:
            self._setStormCmd(cdef)

        for gdef in pkgdef.get('graphs', ()):
            gdef = copy.deepcopy(gdef)
            self._initEasyPerm(gdef)
            self.pkggraphs[gdef['iden']] = gdef

        onload = pkgdef.get('onload')
        if onload is not None and self.isactive:
            async def _onload():
                try:
                    async for mesg in self.storm(onload):
                        if mesg[0] == 'print':
                            logger.info(f'{name} onload output: {mesg[1].get("mesg")}')
                        if mesg[0] == 'warn':
                            logger.warning(f'{name} onload output: {mesg[1].get("mesg")}')
                        if mesg[0] == 'err':
                            logger.error(f'{name} onload output: {mesg[1]}')
                        await asyncio.sleep(0)
                except asyncio.CancelledError:  # pragma: no cover
                    raise
                except Exception:  # pragma: no cover
                    logger.warning(f'onload failed for package: {name}')
                await self.fire('core:pkg:onload:complete', pkg=name)
            self.schedCoro(_onload())

    # N.B. This function is intentionally not async in order to prevent possible user race conditions for code
    # executing outside of the nexus lock.
    def _dropStormPkg(self, pkgdef):
        '''
        Reverse the process of loadStormPkg()
        '''
        self.modsbyiface.clear()
        for mdef in pkgdef.get('modules', ()):
            modname = mdef.get('name')
            self.stormmods.pop(modname, None)

        for cdef in pkgdef.get('commands', ()):
            name = cdef.get('name')
            self._popStormCmd(name)

        pkgname = pkgdef.get('name')

        for gdef in pkgdef.get('graphs', ()):
            self.pkggraphs.pop(gdef['iden'], None)

        self.stormpkgs.pop(pkgname, None)

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
        self.svcdefs.set(iden, sdef)

        await self.feedBeholder('svc:add', {'name': sdef.get('name'), 'iden': iden})
        return ssvc.sdef

    async def delStormSvc(self, iden):
        sdef = self.svcdefs.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg, iden=iden)

        return await self._push('svc:del', iden)

    @s_nexus.Pusher.onPush('svc:del')
    async def _delStormSvc(self, iden):
        '''
        Delete a registered storm service from the cortex.
        '''
        sdef = self.svcdefs.get(iden)
        if sdef is None:  # pragma: no cover
            return

        try:
            if self.isactive:
                await self.runStormSvcEvent(iden, 'del')
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once py 3.8 only
            raise
        except Exception as e:
            logger.exception(f'service.del hook for service {iden} failed with error: {e}')

        sdef = self.svcdefs.pop(iden)

        await self._delStormSvcPkgs(iden)

        name = sdef.get('name')
        if name is not None:
            self.svcsbyname.pop(name, None)

        ssvc = self.svcsbyiden.pop(iden, None)
        if ssvc is not None:
            self.svcsbysvcname.pop(ssvc.svcname, None)
            await ssvc.fini()

        await self.feedBeholder('svc:del', {'iden': iden, 'name': name, 'svcname': ssvc.svcname})

    async def _delStormSvcPkgs(self, iden):
        '''
        Delete storm packages associated with a service.
        '''
        for pkg in self.getStormSvcPkgs(iden):
            name = pkg.get('name')
            if name:
                await self._delStormPkg(name)

    def getStormSvcPkgs(self, iden):
        pkgs = []
        for _, pdef in self.pkgdefs.items():
            pkgiden = pdef.get('svciden')
            if pkgiden and pkgiden == iden:
                pkgs.append(pdef)
        return pkgs

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
        sdef = self.svcdefs.get(iden)
        if sdef is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        sdef['evts'] = edef
        self.svcdefs.set(iden, sdef)
        return sdef

    async def _runStormSvcAdd(self, iden):
        sdef = self.svcdefs.get(iden)
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
        self.svcdefs.set(iden, sdef)

    async def runStormSvcEvent(self, iden, name):
        assert name in ('add', 'del')

        sdef = self.svcdefs.get(iden)
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
        return self.stormvars.get(name, defv=default)

    @s_nexus.Pusher.onPushAuto('stormvar:pop')
    async def popStormVar(self, name, default=None):
        return self.stormvars.pop(name, defv=default)

    @s_nexus.Pusher.onPushAuto('stormvar:set')
    async def setStormVar(self, name, valu):
        return self.stormvars.set(name, valu)

    async def itemsStormVar(self):
        for item in self.stormvars.items():
            yield item

    async def _cortexHealth(self, health):
        health.update('cortex', 'nominal')

    async def _migrateTaxonomyIface(self):

        extforms = await (await self.hive.open(('cortex', 'model', 'forms'))).dict()

        for formname, basetype, typeopts, typeinfo in extforms.values():
            try:
                ifaces = typeinfo.get('interfaces')

                if ifaces and 'taxonomy' in ifaces:
                    logger.warning(f'Migrating taxonomy interface on form {formname} to meta:taxonomy.')

                    ifaces = set(ifaces)
                    ifaces.remove('taxonomy')
                    ifaces.add('meta:taxonomy')
                    typeinfo['interfaces'] = tuple(ifaces)

                    await extforms.set(formname, (formname, basetype, typeopts, typeinfo))

            except Exception as e:  # pragma: no cover
                logger.exception(f'Taxonomy migration error for form: {formname} (skipped).')

    async def _loadExtModel(self):

        self.exttypes = self.cortexdata.getSubKeyVal('model:types:')
        self.extforms = self.cortexdata.getSubKeyVal('model:forms:')
        self.extprops = self.cortexdata.getSubKeyVal('model:props:')
        self.extunivs = self.cortexdata.getSubKeyVal('model:univs:')
        self.extedges = self.cortexdata.getSubKeyVal('model:edges:')
        self.exttagprops = self.cortexdata.getSubKeyVal('model:tagprops:')

        for typename, basetype, typeopts, typeinfo in self.exttypes.values():
            try:
                self.model.addType(typename, basetype, typeopts, typeinfo)
            except Exception as e:
                logger.warning(f'Extended type ({typename}) error: {e}')

        for formname, basetype, typeopts, typeinfo in self.extforms.values():
            try:
                self.model.addType(formname, basetype, typeopts, typeinfo)
                form = self.model.addForm(formname, {}, ())
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
            except Exception as e:
                logger.warning(f'ext univ ({prop}) error: {e}')

        for prop, tdef, info in self.exttagprops.values():
            try:
                self.model.addTagProp(prop, tdef, info)
            except Exception as e:
                logger.warning(f'ext tag prop ({prop}) error: {e}')

        for edge, info in self.extedges.values():
            try:
                self.model.addEdge(edge, info)
            except Exception as e:
                logger.warning(f'ext edge ({edge}) error: {e}')

    async def getExtModel(self):
        '''
        Get all extended model properties in the Cortex.

        Returns:
            dict: A dictionary containing forms, form properties, universal properties and tag properties.
        '''
        ret = collections.defaultdict(list)
        for typename, basetype, typeopts, typeinfo in self.exttypes.values():
            ret['types'].append((typename, basetype, typeopts, typeinfo))

        for formname, basetype, typeopts, typeinfo in self.extforms.values():
            ret['forms'].append((formname, basetype, typeopts, typeinfo))

        for form, prop, tdef, info in self.extprops.values():
            ret['props'].append((form, prop, tdef, info))

        for prop, tdef, info in self.extunivs.values():
            ret['univs'].append((prop, tdef, info))

        for prop, tdef, info in self.exttagprops.values():
            ret['tagprops'].append((prop, tdef, info))

        for edge, info in self.extedges.values():
            ret['edges'].append((edge, info))

        ret['version'] = (1, 0)
        return copy.deepcopy(dict(ret))

    async def addExtModel(self, model):
        '''
        Add an extended model definition to a Cortex from the output of getExtModel().

        Args:
            model (dict): An extended model dictionary.

        Returns:
            Bool: True when the model was added.

        Raises:
            s_exc.BadFormDef: If a form exists with a different definition than the provided definition.
            s_exc.BadPropDef: If a property, tagprop, or universal property exists with a different definition
                              than the provided definition.
            s_exc.BadEdgeDef: If an edge exists with a different definition than the provided definition.
        '''

        # Get our current model definition
        emodl = await self.getExtModel()
        amodl = collections.defaultdict(list)

        types = {info[0]: info for info in model.get('types', ())}
        forms = {info[0]: info for info in model.get('forms', ())}
        props = {(info[0], info[1]): info for info in model.get('props', ())}
        tagprops = {info[0]: info for info in model.get('tagprops', ())}
        univs = {info[0]: info for info in model.get('univs', ())}
        edges = {info[0]: info for info in model.get('edges', ())}

        etyps = {info[0]: info for info in emodl.get('types', ())}
        efrms = {info[0]: info for info in emodl.get('forms', ())}
        eprops = {(info[0], info[1]): info for info in emodl.get('props', ())}
        etagprops = {info[0]: info for info in emodl.get('tagprops', ())}
        eunivs = {info[0]: info for info in emodl.get('univs', ())}
        eedges = {info[0]: info for info in emodl.get('edges', ())}

        for (name, info) in types.items():
            enfo = etyps.get(name)
            if enfo is None:
                amodl['types'].append(info)
                continue
            if enfo == info:
                continue
            mesg = f'Extended type definition differs from existing definition for {name}.'
            raise s_exc.BadTypeDef(mesg=mesg, name=name)

        for (name, info) in forms.items():
            enfo = efrms.get(name)
            if enfo is None:
                amodl['forms'].append(info)
                continue
            if enfo == info:
                continue
            mesg = f'Extended form definition differs from existing definition for {name}.'
            raise s_exc.BadFormDef(mesg=mesg, name=name)

        for (name, info) in props.items():
            enfo = eprops.get(name)
            if enfo is None:
                amodl['props'].append(info)
                continue
            if enfo == info:
                continue
            mesg = f'Extended prop definition differs from existing definition for {name}'
            raise s_exc.BadPropDef(mesg=mesg, name=name)

        for (name, info) in tagprops.items():
            enfo = etagprops.get(name)
            if enfo is None:
                amodl['tagprops'].append(info)
                continue
            if enfo == info:
                continue
            mesg = f'Extended tagprop definition differs from existing definition for {name}'
            raise s_exc.BadPropDef(mesg=mesg, name=name)

        for (name, info) in univs.items():
            enfo = eunivs.get(name)
            if enfo is None:
                amodl['univs'].append(info)
                continue
            if enfo == info:
                continue
            mesg = f'Extended universal property definition differs from existing definition for {name}'
            raise s_exc.BadPropDef(mesg=mesg, name=name)

        for (name, info) in edges.items():
            enfo = eedges.get(name)
            if enfo is None:
                amodl['edges'].append(info)
                continue
            if enfo == info:
                continue

            (n1form, verb, n2form) = info[0]
            mesg = f'Extended edge definition differs from existing definition for {info[0]}'
            raise s_exc.BadEdgeDef(mesg=mesg, n1form=n1form, verb=verb, n2form=n2form)

        for typename, basetype, typeopts, typeinfo in amodl['types']:
            await self.addType(typename, basetype, typeopts, typeinfo)

        for formname, basetype, typeopts, typeinfo in amodl['forms']:
            await self.addForm(formname, basetype, typeopts, typeinfo)

        for form, prop, tdef, info in amodl['props']:
            await self.addFormProp(form, prop, tdef, info)

        for prop, tdef, info in amodl['tagprops']:
            await self.addTagProp(prop, tdef, info)

        for prop, tdef, info in amodl['univs']:
            await self.addUnivProp(prop, tdef, info)

        for edge, info in amodl['edges']:
            await self.addEdge(edge, info)

        return True

    async def addUnivProp(self, name, tdef, info):
        if not isinstance(tdef, tuple):
            mesg = 'Universal property type definitions should be a tuple.'
            raise s_exc.BadArg(name=name, mesg=mesg)

        if not isinstance(info, dict):
            mesg = 'Universal property definitions should be a dict.'
            raise s_exc.BadArg(name=name, mesg=mesg)

        # the loading function does the actual validation...
        if not name.startswith('_'):
            mesg = 'ext univ name must start with "_"'
            raise s_exc.BadPropDef(name=name, mesg=mesg)

        base = '.' + name
        if base in self.model.props:
            raise s_exc.DupPropName(mesg=f'Cannot add duplicate universal property {base}',
                                    prop=name)
        await self._push('model:univ:add', name, tdef, info)

    @s_nexus.Pusher.onPush('model:univ:add')
    async def _addUnivProp(self, name, tdef, info):
        base = '.' + name
        if base in self.model.props:
            return

        self.model.addUnivProp(name, tdef, info)

        self.extunivs.set(name, (name, tdef, info))
        await self.fire('core:extmodel:change', prop=name, act='add', type='univ')
        base = '.' + name
        univ = self.model.univ(base)
        if univ:
            await self.feedBeholder('model:univ:add', univ.pack())

    async def addForm(self, formname, basetype, typeopts, typeinfo):
        if not isinstance(typeopts, dict):
            mesg = 'Form type options should be a dict.'
            raise s_exc.BadArg(form=formname, mesg=mesg)

        if not isinstance(typeinfo, dict):
            mesg = 'Form type info should be a dict.'
            raise s_exc.BadArg(form=formname, mesg=mesg)

        if not formname.startswith('_'):
            mesg = 'Extended form must begin with "_"'
            raise s_exc.BadFormDef(form=formname, mesg=mesg)

        if self.model.form(formname) is not None:
            mesg = f'Form name already exists: {formname}'
            raise s_exc.DupFormName(mesg=mesg)

        if self.model.type(formname) is not None:
            mesg = f'Type already exists: {formname}'
            raise s_exc.DupTypeName.init(formname)

        return await self._push('model:form:add', formname, basetype, typeopts, typeinfo)

    @s_nexus.Pusher.onPush('model:form:add')
    async def _addForm(self, formname, basetype, typeopts, typeinfo):
        if self.model.form(formname) is not None:
            return

        ifaces = typeinfo.get('interfaces')

        if ifaces and 'taxonomy' in ifaces:
            logger.warning(f'{formname} is using the deprecated taxonomy interface, updating to meta:taxonomy.')

            ifaces = set(ifaces)
            ifaces.remove('taxonomy')
            ifaces.add('meta:taxonomy')
            typeinfo['interfaces'] = tuple(ifaces)

        self.model.addType(formname, basetype, typeopts, typeinfo)
        self.model.addForm(formname, {}, ())

        self.extforms.set(formname, (formname, basetype, typeopts, typeinfo))
        await self.fire('core:extmodel:change', form=formname, act='add', type='form')
        form = self.model.form(formname)
        ftyp = self.model.type(formname)
        if form and ftyp:
            await self.feedBeholder('model:form:add', {'form': form.pack(), 'type': ftyp.pack()})

    async def delForm(self, formname):
        if not formname.startswith('_'):
            mesg = 'Extended form must begin with "_"'
            raise s_exc.BadFormDef(form=formname, mesg=mesg)

        if self.model.form(formname) is None:
            raise s_exc.NoSuchForm.init(formname)

        return await self._push('model:form:del', formname)

    @s_nexus.Pusher.onPush('model:form:del')
    async def _delForm(self, formname):
        if self.model.form(formname) is None:
            return

        for layr in self.layers.values():
            async for item in layr.iterFormRows(formname):
                mesg = f'Nodes still exist with form: {formname} in layer {layr.iden}'
                raise s_exc.CantDelForm(mesg=mesg)

        self.model.delForm(formname)
        self.model.delType(formname)

        self.extforms.pop(formname, None)
        await self.fire('core:extmodel:change', form=formname, act='del', type='form')
        await self.feedBeholder('model:form:del', {'form': formname})

    async def addType(self, typename, basetype, typeopts, typeinfo):
        if not isinstance(typeopts, dict):
            mesg = 'Type options should be a dict.'
            raise s_exc.BadArg(type=typename, mesg=mesg)

        if not isinstance(typeinfo, dict):
            mesg = 'Type info should be a dict.'
            raise s_exc.BadArg(type=typename, mesg=mesg)

        if not typename.startswith('_'):
            mesg = 'Extended type must begin with "_".'
            raise s_exc.BadTypeDef(type=typename, mesg=mesg)

        if self.model.type(typename) is not None:
            raise s_exc.DupTypeName.init(typename)

        if (base := self.model.type(basetype)) is None:
            mesg = f'Specified base type {basetype} does not exist.'
            raise s_exc.NoSuchType(mesg=mesg, name=basetype)

        base.clone(typeopts)

        return await self._push('model:type:add', typename, basetype, typeopts, typeinfo)

    @s_nexus.Pusher.onPush('model:type:add')
    async def _addType(self, typename, basetype, typeopts, typeinfo):
        if self.model.type(typename) is not None:
            return

        ifaces = typeinfo.get('interfaces')

        if ifaces and 'taxonomy' in ifaces:
            logger.warning(f'{typename} is using the deprecated taxonomy interface, updating to meta:taxonomy.')

            ifaces = set(ifaces)
            ifaces.remove('taxonomy')
            ifaces.add('meta:taxonomy')
            typeinfo['interfaces'] = tuple(ifaces)

        self.model.addType(typename, basetype, typeopts, typeinfo)

        self.exttypes.set(typename, (typename, basetype, typeopts, typeinfo))
        await self.fire('core:extmodel:change', name=typename, act='add', type='type')

        if (_type := self.model.type(typename)) is not None:
            await self.feedBeholder('model:type:add', {'type': _type.pack()})

    async def delType(self, typename):
        if not typename.startswith('_'):
            mesg = 'Extended type must begin with "_".'
            raise s_exc.BadTypeDef(type=typename, mesg=mesg)

        if self.model.type(typename) is None:
            raise s_exc.NoSuchType.init(typename)

        return await self._push('model:type:del', typename)

    @s_nexus.Pusher.onPush('model:type:del')
    async def _delType(self, typename):
        if self.model.type(typename) is None:
            return

        self.model.delType(typename)

        self.exttypes.pop(typename, None)
        await self.fire('core:extmodel:change', name=typename, act='del', type='type')
        await self.feedBeholder('model:type:del', {'type': typename})

    async def addFormProp(self, form, prop, tdef, info):
        if not isinstance(tdef, tuple):
            mesg = 'Form property type definitions should be a tuple.'
            raise s_exc.BadArg(form=form, mesg=mesg)

        if not isinstance(info, dict):
            mesg = 'Form property definitions should be a dict.'
            raise s_exc.BadArg(form=form, mesg=mesg)

        if not prop.startswith('_') and not form.startswith('_'):
            mesg = 'Extended prop must begin with "_" or be added to an extended form.'
            raise s_exc.BadPropDef(prop=prop, mesg=mesg)
        _form = self.model.form(form)
        if _form is None:
            raise s_exc.NoSuchForm.init(form)
        if _form.prop(prop):
            raise s_exc.DupPropName(mesg=f'Cannot add duplicate form prop {form} {prop}',
                                     form=form, prop=prop)
        await self._push('model:prop:add', form, prop, tdef, info)

    @s_nexus.Pusher.onPush('model:prop:add')
    async def _addFormProp(self, form, prop, tdef, info):
        if (_form := self.model.form(form)) is not None and _form.prop(prop) is not None:
            return

        _prop = self.model.addFormProp(form, prop, tdef, info)
        if _prop.type.deprecated:
            mesg = f'The extended property {_prop.full} is using a deprecated type {_prop.type.name} which will' \
                   f' be removed in 3.0.0'
            logger.warning(mesg)

        full = f'{form}:{prop}'
        self.extprops.set(full, (form, prop, tdef, info))
        await self.fire('core:extmodel:change', form=form, prop=prop, act='add', type='formprop')
        prop = self.model.prop(full)
        if prop:
            await self.feedBeholder('model:prop:add', {'form': form, 'prop': prop.pack()})

    async def delFormProp(self, form, prop):
        self.reqExtProp(form, prop)
        return await self._push('model:prop:del', form, prop)

    async def _delAllFormProp(self, formname, propname, meta):
        '''
        Delete all instances of a property from all layers.

        NOTE: This does not fire triggers.
        '''
        self.reqExtProp(formname, propname)

        fullname = f'{formname}:{propname}'
        prop = self.model.prop(fullname)

        await self.setPropLocked(fullname, True)

        for layr in list(self.layers.values()):

            genr = layr.iterPropRows(formname, propname)

            async for rows in s_coro.chunks(genr):
                nodeedits = []
                for buid, valu in rows:
                    nodeedits.append((buid, prop.form.name, (
                        (s_layer.EDIT_PROP_DEL, (prop.name, None, prop.type.stortype), ()),
                    )))

                await layr.saveNodeEdits(nodeedits, meta)
                await asyncio.sleep(0)

    async def _delAllUnivProp(self, propname, meta):
        '''
        Delete all instances of a universal property from all layers.

        NOTE: This does not fire triggers.
        '''
        self.reqExtUniv(propname)

        full = f'.{propname}'
        prop = self.model.univ(full)

        await self.setUnivLocked(full, True)

        for layr in list(self.layers.values()):

            genr = layr.iterUnivRows(full)

            async for rows in s_coro.chunks(genr):
                nodeedits = []
                for buid, valu in rows:
                    sode = await layr.getStorNode(buid)
                    nodeedits.append((buid, sode.get('form'), (
                        (s_layer.EDIT_PROP_DEL, (prop.name, None, prop.type.stortype), ()),
                    )))

                await layr.saveNodeEdits(nodeedits, meta)
                await asyncio.sleep(0)

    async def _delAllTagProp(self, propname, meta):
        '''
        Delete all instances of a tag property from all layers.

        NOTE: This does not fire triggers.
        '''
        self.reqExtTagProp(propname)
        prop = self.model.getTagProp(propname)

        await self.setTagPropLocked(propname, True)

        for layr in list(self.layers.values()):

            for form, tag, tagprop in layr.getTagProps():

                if tagprop != propname: # pragma: no cover
                    await asyncio.sleep(0)
                    continue

                genr = layr.iterTagPropRows(tag, tagprop, form)

                async for rows in s_coro.chunks(genr):
                    nodeedits = []
                    for buid, valu in rows:
                        nodeedits.append((buid, form, (
                            (s_layer.EDIT_TAGPROP_DEL, (tag, prop.name, None, prop.type.stortype), ()),
                        )))

                    await layr.saveNodeEdits(nodeedits, meta)
                    await asyncio.sleep(0)

    def reqExtProp(self, form, prop):
        full = f'{form}:{prop}'
        pdef = self.extprops.get(full)
        if pdef is None:
            mesg = f'No ext prop named {full}'
            raise s_exc.NoSuchProp(form=form, prop=prop, mesg=mesg)
        return pdef

    def reqExtUniv(self, prop):
        udef = self.extunivs.get(prop)
        if udef is None:
            mesg = f'No ext univ named {prop}'
            raise s_exc.NoSuchUniv(name=prop, mesg=mesg)
        return udef

    def reqExtTagProp(self, name):
        pdef = self.exttagprops.get(name)
        if pdef is None:
            mesg = f'No tag prop named {name}'
            raise s_exc.NoSuchTagProp(mesg=mesg, name=name)
        return pdef

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
                mesg = f'Nodes still exist with prop: {form}:{prop} in layer {layr.iden}'
                raise s_exc.CantDelProp(mesg=mesg)

        self.model.delFormProp(form, prop)
        self.extprops.pop(full, None)
        self.modellocks.pop(f'prop/{full}', None)
        await self.fire('core:extmodel:change',
                        form=form, prop=prop, act='del', type='formprop')

        await self.feedBeholder('model:prop:del', {'form': form, 'prop': prop})

    async def delUnivProp(self, prop):
        self.reqExtUniv(prop)
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
                mesg = f'Nodes still exist with universal prop: {prop} in layer {layr.iden}'
                raise s_exc.CantDelUniv(mesg=mesg)

        self.model.delUnivProp(prop)
        self.extunivs.pop(prop, None)
        self.modellocks.pop(f'univ/{prop}', None)
        await self.fire('core:extmodel:change', name=prop, act='del', type='univ')
        await self.feedBeholder('model:univ:del', {'prop': univname})

    async def addTagProp(self, name, tdef, info):
        if not isinstance(tdef, tuple):
            mesg = 'Tag property type definitions should be a tuple.'
            raise s_exc.BadArg(name=name, mesg=mesg)

        if not isinstance(info, dict):
            mesg = 'Tag property definitions should be a dict.'
            raise s_exc.BadArg(name=name, mesg=mesg)

        if self.exttagprops.get(name) is not None:
            raise s_exc.DupPropName(name=name)

        return await self._push('model:tagprop:add', name, tdef, info)

    @s_nexus.Pusher.onPush('model:tagprop:add')
    async def _addTagProp(self, name, tdef, info):
        if self.exttagprops.get(name) is not None:
            return

        self.model.addTagProp(name, tdef, info)

        self.exttagprops.set(name, (name, tdef, info))
        await self.fire('core:tagprop:change', name=name, act='add')
        tagp = self.model.tagprop(name)
        if tagp:
            await self.feedBeholder('model:tagprop:add', tagp.pack())

    async def delTagProp(self, name):
        self.reqExtTagProp(name)
        return await self._push('model:tagprop:del', name)

    @s_nexus.Pusher.onPush('model:tagprop:del')
    async def _delTagProp(self, name):
        pdef = self.exttagprops.get(name)
        if pdef is None:
            return

        for layr in self.layers.values():
            if await layr.hasTagProp(name):
                mesg = f'Nodes still exist with tagprop: {name} in layer {layr.iden}'
                raise s_exc.CantDelProp(mesg=mesg)

        self.model.delTagProp(name)

        self.exttagprops.pop(name, None)
        self.modellocks.pop(f'tagprop/{name}', None)
        await self.fire('core:tagprop:change', name=name, act='del')
        await self.feedBeholder('model:tagprop:del', {'tagprop': name})

    async def addEdge(self, edge, edgeinfo):
        if not isinstance(edgeinfo, dict):
            mesg = 'Edge info should be a dict.'
            raise s_exc.BadArg(mesg=mesg, edgeinfo=edgeinfo)

        (n1form, verb, n2form) = edge
        if not verb.startswith('_'):
            mesg = f'Extended edge verb must begin with "_"; got {verb}'
            raise s_exc.BadEdgeDef(mesg=mesg, n1form=n1form, verb=verb, n2form=n2form)

        if n1form is not None:
            self.model._reqFormName(n1form)

        if n2form is not None:
            self.model._reqFormName(n2form)

        if self.model.edge(edge) is not None:
            raise s_exc.DupEdgeType.init(edge)

        return await self._push('model:edge:add', edge, edgeinfo)

    @s_nexus.Pusher.onPush('model:edge:add')
    async def _addEdge(self, edge, edgeinfo):
        if self.model.edge(edge) is not None:
            return

        self.model.addEdge(edge, edgeinfo)

        self.extedges.set(s_common.guid(edge), (edge, edgeinfo))
        await self.fire('core:extmodel:change', edge=edge, act='add', type='edge')
        await self.feedBeholder('model:edge:add', {'edge': edge, 'info': edgeinfo})

    async def delEdge(self, edge):
        if self.extedges.get(s_common.guid(edge)) is None:
            raise s_exc.NoSuchEdge.init(edge)

        return await self._push('model:edge:del', edge)

    @s_nexus.Pusher.onPush('model:edge:del')
    async def _delEdge(self, edge):
        edgeguid = s_common.guid(edge)
        if self.extedges.get(edgeguid) is None:
            return

        self.model.delEdge(edge)

        self.extedges.pop(edgeguid, None)
        await self.fire('core:extmodel:change', edge=edge, act='del', type='edge')
        await self.feedBeholder('model:edge:del', {'edge': edge})

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {iden}', iden=iden)

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
                    await asyncio.sleep(0)

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
        catchingup = True                   # whether we've caught up to topoffs
        layrsadded = {}                     # layriden -> True.  Captures all the layers added while catching up
        todo = set()                        # outstanding futures of active live streaming from layers
        layrgenrs = {}                      # layriden -> genr.  maps active layers to that layer's async generator

        # The offset to start from once the catch-up phase is complete
        topoffs = max(layr.nodeeditlog.index() for layr in self.layers.values())

        if offsdict is None:
            offsdict = {}

        newtodoevent = asyncio.Event()

        async with await s_base.Base.anit() as base:

            def addlayr(layr, newlayer=False, startoffs=topoffs):
                '''
                A new layer joins the live stream
                '''
                genr = genrfunc(layr, startoffs, newlayer=newlayer)
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

            logger.debug(f'_syncNodeEdits() running catch-up sync to offs={topoffs}')

            genrs = [genrfunc(layr, offsdict.get(layr.iden, 0), endoff=topoffs) for layr in self.layers.values()]
            async for item in s_common.merggenr(genrs, lambda x, y: x[0] < y[0]):
                yield item

            catchingup = False

            if not wait:
                return

            # After we've caught up, read on genrs from all the layers simultaneously

            logger.debug('_syncNodeEdits() entering into live sync')

            lastoffs = {}

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

                        lastoffs[layriden] = result[0]

                        # Re-add a task to wait on the next iteration of the generator
                        genr = layrgenrs[layriden]
                        task = base.schedCoro(genr.__anext__())
                        task.iden = layriden
                        todo.add(task)

                    except StopAsyncIteration:

                        # Help out the garbage collector
                        del layrgenrs[layriden]

                        layr = self.getLayer(iden=layriden)
                        if layr is None or not layr.logedits:
                            logger.debug(f'_syncNodeEdits() removed {layriden=} from sync')
                            continue

                        startoffs = lastoffs[layriden] + 1 if layriden in lastoffs else topoffs
                        logger.debug(f'_syncNodeEdits() restarting {layriden=} live sync from offs={startoffs}')
                        addlayr(layr, startoffs=startoffs)

                        await self.waitfini(1)

    async def _initCoreInfo(self):
        self.stormvars = self.cortexdata.getSubKeyVal('storm:vars:')
        if self.inaugural:
            self.stormvars.set(s_stormlib_cell.runtime_fixes_key, s_stormlib_cell.getMaxHotFixes())

    async def _initDeprLocks(self):

        self.deprlocks = self.cortexdata.getSubKeyVal('model:deprlocks:')
        self.modellocks = self.cortexdata.getSubKeyVal('model:locks:')

        # TODO: 3.0.0 conversion will truncate this hive key

        if self.inaugural:
            locks = (
                # 2.87.0 - lock out incorrect crypto model
                ('crypto:currency:transaction:inputs', True),
                ('crypto:currency:transaction:outputs', True),
            )
            for k, v in locks:
                await self._hndlsetDeprLock(k, v)

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

        for name, locked in self.modellocks.items():

            prop = None
            elemtype, elemname = name.split('/', 1)

            if elemtype == 'prop':
                prop = self.model.prop(elemname)
            elif elemtype == 'univ':
                prop = self.model.univ(elemname)
                if prop is not None:
                    for univ in self.model.getAllUnivs(elemname):
                        univ.locked = locked
            elif elemtype == 'tagprop':
                prop = self.model.getTagProp(elemname)

            if prop is not None:
                prop.locked = locked

    async def _initJsonStor(self):

        self.jsonurl = self.conf.get('jsonstor')
        if self.jsonurl is not None:

            async def onlink(proxy: s_telepath.Proxy):
                logger.debug(f'Connected to remote jsonstor {s_urlhelp.sanitizeUrl(self.jsonurl)}')

            self.jsonstor = await s_telepath.Client.anit(self.jsonurl, onlink=onlink)
        else:
            path = os.path.join(self.dirn, 'jsonstor')
            jsoniden = s_common.guid((self.iden, 'jsonstor'))

            idenpath = os.path.join(path, 'cell.guid')
            # check that the jsonstor cell GUID is what it should be. If not, update it.
            # ( bugfix for first release where cell was allowed to generate it's own iden )
            if os.path.isfile(idenpath):

                with open(idenpath, 'r') as fd:
                    existiden = fd.read()

                if jsoniden != existiden:
                    with open(idenpath, 'w') as fd:
                        fd.write(jsoniden)

            # Disable sysctl checks for embedded jsonstor server
            conf = {'cell:guid': jsoniden, 'health:sysctl:checks': False}
            self.jsonstor = await s_jsonstor.JsonStorCell.anit(path, conf=conf, parent=self)

        self.onfini(self.jsonstor)

    async def getJsonObj(self, path):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.getPathObj(path)

    async def hasJsonObj(self, path):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.hasPathObj(path)

    async def getJsonObjs(self, path):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        async for item in self.jsonstor.getPathObjs(path):
            yield item

    async def getJsonObjProp(self, path, prop):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.getPathObjProp(path, prop)

    async def delJsonObj(self, path):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.delPathObj(path)

    async def delJsonObjProp(self, path, prop):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.delPathObjProp(path, prop)

    async def setJsonObj(self, path, item):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.setPathObj(path, item)

    async def setJsonObjProp(self, path, prop, item):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.setPathObjProp(path, prop, item)

    async def getUserNotif(self, indx):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.getUserNotif(indx)

    async def delUserNotif(self, indx):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.delUserNotif(indx)

    async def addUserNotif(self, useriden, mesgtype, mesgdata=None):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        return await self.jsonstor.addUserNotif(useriden, mesgtype, mesgdata=mesgdata)

    async def iterUserNotifs(self, useriden, size=None):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        async for item in self.jsonstor.iterUserNotifs(useriden, size=size):
            yield item

    async def watchAllUserNotifs(self, offs=None):
        if self.jsonurl is not None:
            await self.jsonstor.waitready()
        async for item in self.jsonstor.watchAllUserNotifs(offs=offs):
            yield item

    async def _initCoreAxon(self):
        turl = self.conf.get('axon')
        if turl is None:
            path = os.path.join(self.dirn, 'axon')
            # Disable sysctl checks for embedded axon server
            conf = {'health:sysctl:checks': False}

            proxyurl = self.conf.get('http:proxy')
            if proxyurl is not None:
                conf['http:proxy'] = proxyurl

            cadir = self.conf.get('tls:ca:dir')
            if cadir is not None:
                conf['tls:ca:dir'] = cadir

            self.axon = await s_axon.Axon.anit(path, conf=conf, parent=self)
            self.axoninfo = await self.axon.getCellInfo()
            self.axon.onfini(self.axready.clear)
            self.dynitems['axon'] = self.axon
            self.axready.set()
            return

        async def onlink(proxy: s_telepath.Proxy):
            logger.debug(f'Connected to remote axon {s_urlhelp.sanitizeUrl(turl)}')

            async def fini():
                self.axready.clear()

            self.axoninfo = await proxy.getCellInfo()

            proxy.onfini(fini)
            self.axready.set()

        self.axon = await s_telepath.Client.anit(turl, onlink=onlink)
        self.dynitems['axon'] = self.axon
        self.onfini(self.axon)

    async def _initStormCmds(self):
        '''
        Registration for built-in Storm commands.
        '''
        self.addStormCmd(s_storm.MaxCmd)
        self.addStormCmd(s_storm.MinCmd)
        self.addStormCmd(s_storm.TeeCmd)
        self.addStormCmd(s_storm.DiffCmd)
        self.addStormCmd(s_storm.OnceCmd)
        self.addStormCmd(s_storm.TreeCmd)
        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.IdenCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.UniqCmd)
        self.addStormCmd(s_storm.BatchCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.GraphCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.MergeCmd)
        self.addStormCmd(s_storm.RunAsCmd)
        self.addStormCmd(s_storm.SleepCmd)
        self.addStormCmd(s_storm.CopyToCmd)
        self.addStormCmd(s_storm.DivertCmd)
        self.addStormCmd(s_storm.ScrapeCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.LiftByVerb)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)
        self.addStormCmd(s_storm.EdgesDelCmd)
        self.addStormCmd(s_storm.ParallelCmd)
        self.addStormCmd(s_storm.TagPruneCmd)
        self.addStormCmd(s_storm.ViewExecCmd)
        self.addStormCmd(s_storm.IntersectCmd)
        self.addStormCmd(s_storm.MoveNodesCmd)
        self.addStormCmd(s_storm.BackgroundCmd)
        self.addStormCmd(s_stormlib_macro.MacroExecCmd)
        self.addStormCmd(s_stormlib_storm.StormExecCmd)
        self.addStormCmd(s_stormlib_stats.StatsCountByCmd)
        self.addStormCmd(s_stormlib_cortex.StormPoolDelCmd)
        self.addStormCmd(s_stormlib_cortex.StormPoolGetCmd)
        self.addStormCmd(s_stormlib_cortex.StormPoolSetCmd)

        for cdef in s_stormsvc.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_storm.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_aha.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_gen.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_auth.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_macro.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_model.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_cortex.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_vault.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

        for cdef in s_stormlib_index.stormcmds:
            await self._trySetStormCmd(cdef.get('name'), cdef)

    async def _initPureStormCmds(self):
        oldcmds = []
        for name, cdef in self.cmddefs.items():
            cmdiden = cdef.get('cmdconf', {}).get('svciden')
            if cmdiden and self.svcdefs.get(cmdiden) is None:
                oldcmds.append(name)
            else:
                await self._trySetStormCmd(name, cdef)

        for name in oldcmds:
            logger.warning(f'Removing old command: [{name}]')
            self.cmddefs.pop(name)

        for pkgdef in self.pkgdefs.values():
            await self._tryLoadStormPkg(pkgdef)

    async def _trySetStormCmd(self, name, cdef):
        try:
            self._setStormCmd(cdef)
        except (asyncio.CancelledError, Exception):
            logger.exception(f'Storm command load failed: {name}')

    def _initStormLibs(self):
        '''
        Registration for built-in Storm Libraries
        '''

        for path, ctor in s_stormtypes.registry.iterLibs():
            # Ensure each ctor's permdefs are valid
            for pdef in ctor._storm_lib_perms:
                s_schemas.reqValidPermDef(pdef)
            # Skip libbase which is registered as a default ctor in the storm Runtime
            if path:
                self.addStormLib(path, ctor)

    def _initFeedFuncs(self):
        '''
        Registration for built-in Cortex feed functions.
        '''
        self.setFeedFunc('syn.nodes', self._addSynNodes)

    def _initCortexHttpApi(self):
        '''
        Registration for built-in Cortex httpapi endpoints
        '''
        self.addHttpApi('/api/v1/feed', s_httpapi.FeedV1, {'cell': self})
        self.addHttpApi('/api/v1/storm', s_httpapi.StormV1, {'cell': self})
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

        self.addHttpApi('/api/v1/axon/files/del', CortexAxonHttpDelV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/put', CortexAxonHttpUploadV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/has/sha256/([0-9a-fA-F]{64}$)', CortexAxonHttpHasV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/by/sha256/([0-9a-fA-F]{64}$)', CortexAxonHttpBySha256V1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/by/sha256/(.*)', CortexAxonHttpBySha256InvalidV1, {'cell': self})

        self.addHttpApi('/api/ext/(.*)', s_httpapi.ExtApiHandler, {'cell': self})

    def _initCortexExtHttpApi(self):
        self._exthttpapis.clear()
        self._exthttpapicache.clear()

        byts = self.slab.get(self._exthttpapiorder, self.httpextapidb)
        if byts is None:
            return

        order = s_msgpack.un(byts)

        for iden in order:
            byts = self.slab.get(s_common.uhex(iden), self.httpextapidb)
            if byts is None:  # pragma: no cover
                logger.error(f'Missing HTTP API definition for iden={iden}')
                continue
            adef = s_msgpack.un(byts)
            self._exthttpapis[adef.get('iden')] = adef

    async def addHttpExtApi(self, adef):
        path = adef.get('path')
        try:
            _ = regex.compile(path)
        except Exception as e:
            mesg = f'Invalid path for Extended HTTP API - cannot compile regular expression for [{path}] : {e}'
            raise s_exc.BadArg(mesg=mesg) from None

        if adef.get('iden') is None:
            adef['iden'] = s_common.guid()

        iden = adef['iden']
        if self._exthttpapis.get(iden) is not None:
            raise s_exc.DupIden(mesg=f'Duplicate iden specified for Extended HTTP API: {iden}', iden=iden)

        adef['created'] = s_common.now()
        adef['updated'] = adef['created']
        adef = s_schemas.reqValidHttpExtAPIConf(adef)
        return await self._push('http:api:add', adef)

    @s_nexus.Pusher.onPush('http:api:add')
    async def _addHttpExtApi(self, adef):
        iden = adef.get('iden')
        self.slab.put(s_common.uhex(iden), s_msgpack.en(adef), db=self.httpextapidb)

        order = self.slab.get(self._exthttpapiorder, db=self.httpextapidb)
        if order is None:
            self.slab.put(self._exthttpapiorder, s_msgpack.en([iden]), db=self.httpextapidb)
        else:
            order = s_msgpack.un(order)  # type: tuple
            if iden not in order:
                # Replay safety
                order = order + (iden, )  # New handlers go to the end of the list of handlers
                self.slab.put(self._exthttpapiorder, s_msgpack.en(order), db=self.httpextapidb)

        # Re-initialize the HTTP API list from the index order
        self._initCortexExtHttpApi()
        return adef

    @s_nexus.Pusher.onPushAuto('http:api:del')
    async def delHttpExtApi(self, iden):
        if s_common.isguid(iden) is False:
            raise s_exc.BadArg(mesg=f'Must provide an iden. Got {iden}')

        self.slab.pop(s_common.uhex(iden), db=self.httpextapidb)

        byts = self.slab.get(self._exthttpapiorder, self.httpextapidb)
        order = list(s_msgpack.un(byts))
        if iden in order:
            order.remove(iden)
            self.slab.put(self._exthttpapiorder, s_msgpack.en(order), db=self.httpextapidb)

        self._initCortexExtHttpApi()

        return

    @s_nexus.Pusher.onPushAuto('http:api:mod')
    async def modHttpExtApi(self, iden, name, valu):
        # Created, Creator, Updated are not mutable
        if name in ('name', 'desc', 'runas', 'methods', 'authenticated', 'pool', 'perms', 'readonly', 'vars'):
            # Schema takes care of these values
            pass
        elif name == 'owner':
            _obj = await self.getUserDef(valu, packroles=False)
            if _obj is None:
                raise s_exc.NoSuchUser(mesg=f'Cannot set owner={valu} on extended httpapi, it does not exist.')
        elif name == 'view':
            _obj = self.getView(valu)
            if _obj is None:
                raise s_exc.NoSuchView(mesg=f'Cannot set view={valu} on extended httpapi, it does not exist.')
        elif name == 'path':
            try:
                _ = regex.compile(valu)
            except Exception as e:
                mesg = f'Invalid path for Extended HTTP API - cannot compile regular expression for [{valu}] : {e}'
                raise s_exc.BadArg(mesg=mesg) from None
        else:
            raise s_exc.BadArg(mesg=f'Cannot set {name=} on extended httpapi')

        byts = self.slab.get(s_common.uhex(iden), db=self.httpextapidb)
        if byts is None:
            raise s_exc.NoSuchIden(mesg=f'No http api for {iden=}', iden=iden)

        adef = s_msgpack.un(byts)
        adef[name] = valu
        adef['updated'] = s_common.now()
        adef = s_schemas.reqValidHttpExtAPIConf(adef)
        self.slab.put(s_common.uhex(iden), s_msgpack.en(adef), db=self.httpextapidb)

        self._initCortexExtHttpApi()

        return adef

    @s_nexus.Pusher.onPushAuto('http:api:indx')
    async def setHttpApiIndx(self, iden, indx):
        if indx < 0:
            raise s_exc.BadArg(mesg=f'indx must be greater than or equal to 0; got {indx}')
        byts = self.slab.get(self._exthttpapiorder, db=self.httpextapidb)
        if byts is None:
            raise s_exc.SynErr(mesg='No Extended HTTP handlers registered. Cannot set order.')

        order = list(s_msgpack.un(byts))

        if iden not in order:
            raise s_exc.NoSuchIden(mesg=f'Extended HTTP API is not set: {iden}')

        if order.index(iden) == indx:
            return indx
        order.remove(iden)
        # indx values > length of the list end up at the end of the list.
        order.insert(indx, iden)
        self.slab.put(self._exthttpapiorder, s_msgpack.en(order), db=self.httpextapidb)
        self._initCortexExtHttpApi()
        return order.index(iden)

    async def getHttpExtApis(self):
        return copy.deepcopy(list(self._exthttpapis.values()))

    async def getHttpExtApi(self, iden):
        adef = self._exthttpapis.get(iden)
        if adef is None:
            raise s_exc.NoSuchIden(mesg=f'No extended http api for {iden=}', iden=iden)
        return copy.deepcopy(adef)

    async def getHttpExtApiByPath(self, path):
        iden, args = self._exthttpapicache.get(path)
        adef = copy.deepcopy(self._exthttpapis.get(iden))
        return adef, args

    def _getHttpExtApiByPath(self, key):
        # Cache callback.
        # Returns (iden, args) or (None, ()) for caching.
        for iden, adef in self._exthttpapis.items():
            match = regex.fullmatch(adef.get('path'), key)
            if match is None:
                continue
            return iden, match.groups()
        return None, ()

    async def getCellApi(self, link, user, path):

        if not path:
            return await self.cellapi.anit(self, link, user)

        if path[0] == 'layer':

            if len(path) == 1:
                # get the top layer for the default view
                layr = self.getLayer()
                return await self.layerapi.anit(self, link, user, layr)

            if len(path) == 2:
                layr = self.getLayer(path[1])
                if layr is None:
                    raise s_exc.NoSuchLayer(mesg=f'No such layer {path[1]}', iden=path[1])

                return await self.layerapi.anit(self, link, user, layr)

        if path[0] == 'view':

            view = None
            if len(path) == 1:
                view = self.getView(user=user)

            elif len(path) == 2:
                view = self.getView(path[1], user=user)

            if view is not None:
                return await self.viewapi.anit(self, link, user, view)

        raise s_exc.NoSuchPath(mesg=f'Invalid telepath path={path}', path=path)

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

    async def runRuntLift(self, full, valu=None, cmpr=None, view=None):
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
            async for pode in func(full, valu, cmpr, view):
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
        async with self.enterMigrationMode():
            mrev = s_modelrev.ModelRev(self)
            await mrev.revCoreLayers()

    async def _loadView(self, vdef):

        view = await self.viewctor(self, vdef)

        self.views[view.iden] = view
        self.dynitems[view.iden] = view

        async def fini():
            self.views.pop(view.iden, None)
            self.dynitems.pop(view.iden, None)

        view.onfini(fini)

        return view

    def _calcViewsByLayer(self):
        # keep track of views by layer
        self.viewsbylayer.clear()
        for view in self.views.values():
            for layr in view.layers:
                self.viewsbylayer[layr.iden].append(view)

    async def _initCoreViews(self):

        defiden = self.cellinfo.get('defaultview')

        self.viewdefs = self.cortexdata.getSubKeyVal('view:info:')

        for iden, vdef in self.viewdefs.items():
            view = await self._loadView(vdef)
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
            self.cellinfo.set('defaultview', iden)
            self.view = self.getView(iden)

        self._calcViewsByLayer()

    async def addView(self, vdef, nexs=True):

        vdef['iden'] = s_common.guid()
        vdef['created'] = s_common.now()

        vdef.setdefault('parent', None)
        vdef.setdefault('worldreadable', False)
        vdef.setdefault('creator', self.auth.rootuser.iden)

        s_schemas.reqValidView(vdef)

        if nexs:
            return await self._push('view:add', vdef)
        else:
            return await self._addView(vdef)

    @s_nexus.Pusher.onPush('view:add')
    async def _addView(self, vdef):

        s_schemas.reqValidView(vdef)

        iden = vdef['iden']
        if iden in self.views:
            return

        for lyriden in vdef['layers']:
            if lyriden not in self.layers:
                raise s_exc.NoSuchLayer(mesg=f'No such layer {lyriden}', iden=lyriden)

        creator = vdef.get('creator', self.auth.rootuser.iden)
        user = await self.auth.reqUser(creator)

        await self.auth.addAuthGate(iden, 'view')
        await user.setAdmin(True, gateiden=iden, logged=False)

        # worldreadable does not get persisted with the view; the state ends up in perms
        worldread = vdef.pop('worldreadable', False)

        if worldread:
            role = await self.auth.getRoleByName('all')
            await role.addRule((True, ('view', 'read')), gateiden=iden, nexs=False)

        self.viewdefs.set(iden, vdef)

        view = await self._loadView(vdef)
        view.init2()

        self._calcViewsByLayer()
        pack = await view.pack()
        await self.feedBeholder('view:add', pack, gates=[iden])
        return pack

    async def delViewWithLayer(self, iden):
        '''
        Delete a Cortex View and its write Layer if not in use by other View stacks.

        Note:
            Any children of the View will have their parent View updated to
            the deleted View's parent (if present). The deleted View's write Layer
            will also be removed from any child Views which contain it in their
            Layer stack. If the Layer is used in Views which are not children of
            the deleted View, the Layer will be preserved, otherwise it will be
            deleted as well.
        '''
        view = self.views.get(iden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view {iden=}', iden=iden)

        if view.info.get('protected'):
            mesg = f'Cannot delete view ({iden}) that has protected set.'
            raise s_exc.CantDelView(mesg=mesg)

        layriden = view.layers[0].iden
        pareiden = None
        if view.parent is not None:
            pareiden = view.parent.iden

        return await self._push('view:delwithlayer', iden, layriden, newparent=pareiden)

    @s_nexus.Pusher.onPush('view:delwithlayer', passitem=True)
    async def _delViewWithLayer(self, viewiden, layriden, nexsitem, newparent=None):

        if viewiden == self.view.iden:
            raise s_exc.SynErr(mesg='Cannot delete the main view')

        if (view := self.views.get(viewiden)) is not None:

            self.viewdefs.pop(viewiden)
            await view.delete()

            self._calcViewsByLayer()
            await self.feedBeholder('view:del', {'iden': viewiden}, gates=[viewiden])
            await self.auth.delAuthGate(viewiden)

        if newparent is not None:
            newview = self.views.get(newparent)

        layrinuse = False
        for view in self.viewsbylayer[layriden]:
            if not view.isForkOf(viewiden):
                layrinuse = True
                continue

            view.layers = [lyr for lyr in view.layers if lyr.iden != layriden]

            layridens = [lyr.iden for lyr in view.layers]
            view.info['layers'] = layridens

            mesg = {'iden': view.iden, 'layers': layridens}
            await self.feedBeholder('view:setlayers', mesg, gates=[view.iden, layridens[0]])

            if view.parent.iden == viewiden:
                if newparent is None:
                    view.parent = None
                    view.info['parent'] = None
                else:
                    view.parent = newview
                    view.info['parent'] = newparent

                mesg = {'iden': view.iden, 'name': 'parent', 'valu': newparent}
                await self.feedBeholder('view:set', mesg, gates=[view.iden, layridens[0]])

            self.viewdefs.set(view.iden, view.info)

        if not layrinuse and (layr := self.layers.get(layriden)) is not None:
            del self.layers[layriden]

            for pdef in layr.layrinfo.get('pushs', {}).values():
                await self.delActiveCoro(pdef.get('iden'))

            for pdef in layr.layrinfo.get('pulls', {}).values():
                await self.delActiveCoro(pdef.get('iden'))

            await self.feedBeholder('layer:del', {'iden': layriden}, gates=[layriden])
            await self.auth.delAuthGate(layriden)
            self.dynitems.pop(layriden)

            self.layerdefs.pop(layriden)
            await layr.delete()

            layr.deloffs = nexsitem[0]

    async def delView(self, iden):
        view = self.views.get(iden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view {iden=}', iden=iden)

        if view.info.get('protected'):
            mesg = f'Cannot delete view ({iden}) that has protected set.'
            raise s_exc.CantDelView(mesg=mesg)

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

        self.viewdefs.pop(iden)
        await view.delete()

        self._calcViewsByLayer()
        await self.feedBeholder('view:del', {'iden': iden}, gates=[iden])
        await self.auth.delAuthGate(iden)

    async def delLayer(self, iden):
        layr = self.layers.get(iden, None)
        if layr is None:
            raise s_exc.NoSuchLayer(mesg=f'No such layer {iden}', iden=iden)

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

        await self.feedBeholder('layer:del', {'iden': iden}, gates=[iden])
        await self.auth.delAuthGate(iden)
        self.dynitems.pop(iden)

        self.layerdefs.pop(iden)

        await layr.delete()

        layr.deloffs = nexsitem[0]

    async def setViewLayers(self, layers, iden=None):
        '''
        Args:
            layers ([str]): A top-down list of of layer guids
            iden (str): The view iden (defaults to default view).
        '''
        view = self.getView(iden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view {iden=}', iden=iden)

        await view.setLayers(layers)
        self._calcViewsByLayer()

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

    def reqLayer(self, iden=None):
        layr = self.getLayer(iden=iden)
        if layr is None:
            mesg = f'No layer found with iden: {iden}'
            raise s_exc.NoSuchLayer(mesg=mesg, iden=iden)
        return layr

    def listLayers(self):
        return self.layers.values()

    async def getLayerDef(self, iden=None):
        layr = self.getLayer(iden)
        if layr is not None:
            return await layr.pack()

    async def getLayerDefs(self):
        return [await lyr.pack() for lyr in list(self.layers.values())]

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

    def reqView(self, iden, mesg=None):
        view = self.getView(iden)
        if view is None: # pragma: no cover
            if mesg is None:
                mesg = f'No view with iden: {iden}'
            raise s_exc.NoSuchView(mesg=mesg, iden=iden)
        return view

    def listViews(self):
        return list(self.views.values())

    async def getViewDef(self, iden):
        view = self.getView(iden=iden)
        if view is not None:
            return await view.pack()

    async def getViewDefs(self, deporder=False):

        views = list(self.views.values())
        if not deporder:
            return [await v.pack() for v in views]

        def depth(view):
            x = 0
            llen = len(view.layers)
            while view:
                x += 1
                view = view.parent
            return (x, llen)
        views.sort(key=lambda x: depth(x))

        return [await v.pack() for v in views]

    async def addLayer(self, ldef=None, nexs=True):
        '''
        Add a Layer to the cortex.

        Args:
            ldef (Optional[Dict]):  layer configuration
            nexs (bool):            whether to record a nexus transaction (internal use only)
        '''
        ldef = ldef or {}

        ldef['iden'] = s_common.guid()
        ldef['created'] = s_common.now()

        ldef.setdefault('creator', self.auth.rootuser.iden)
        ldef.setdefault('lockmemory', self.conf.get('layers:lockmemory'))
        ldef.setdefault('logedits', self.conf.get('layers:logedits'))
        ldef.setdefault('readonly', False)

        s_layer.reqValidLdef(ldef)

        if nexs:
            return await self._push('layer:add', ldef)
        else:
            return await self._addLayer(ldef, (None, None))

    async def _twinLayer(self, oldlayr):

        newldef = s_msgpack.deepcopy(oldlayr.layrinfo)

        newldef.pop('iden', None)

        newldef = await self.addLayer(newldef)
        newlayr = self.reqLayer(newldef.get('iden'))

        oldinfo = self.auth.reqAuthGate(oldlayr.iden).pack()

        for userinfo in oldinfo.get('users', ()):

            user = self.auth.user(userinfo.get('iden'))
            if user is None: # pragma: no cover
                continue

            if userinfo.get('admin'):
                await user.setAdmin(True, gateiden=newlayr.iden)

            for rule in userinfo.get('rules', ()):
                await user.addRule(rule, gateiden=newlayr.iden)

        for roleinfo in oldinfo.get('roles', ()):

            role = self.auth.role(roleinfo.get('iden'))
            if role is None: # pragma: no cover
                continue

            for rule in roleinfo.get('rules', ()):
                await role.addRule(rule, gateiden=newlayr.iden)

        return newlayr

    @s_nexus.Pusher.onPushAuto('layer:swap')
    async def swapLayer(self, oldiden, newiden):
        '''
        Atomically swap out a layer from all views that contain it.
        '''
        self.reqLayer(oldiden)
        self.reqLayer(newiden)

        for view in list(self.views.values()):
            await asyncio.sleep(0)

            oldlayers = view.info.get('layers')
            if oldiden not in oldlayers:
                continue

            newlayers = list(oldlayers)
            newlayers[oldlayers.index(oldiden)] = newiden

            await view._setLayerIdens(newlayers)

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

        self.layerdefs.set(iden, ldef)

        layr = await self._initLayr(ldef, nexsoffs=nexsitem[0])
        await user.setAdmin(True, gateiden=iden, logged=False)

        # forward wind the new layer to the current model version
        await layr._setModelVers(s_modelrev.maxvers)

        if self.isactive:
            await layr.initLayerActive()
        else:
            await layr.initLayerPassive()

        pack = await layr.pack()
        await self.feedBeholder('layer:add', pack, gates=[iden])
        return pack

    def _checkMaxNodes(self, delta=1):

        if self.maxnodes is None:
            return

        remain = self.maxnodes - self.nodecount
        if remain < delta:
            mesg = f'Cortex is at node:count limit: {self.maxnodes}'
            raise s_exc.HitLimit(mesg=mesg)

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

        await self.fire('core:layr:add', iden=layr.iden)

        return layr

    async def _ctorLayr(self, layrinfo):
        '''
        Actually construct the Layer instance for the given HiveDict.
        '''
        return await s_layer.Layer.anit(self, layrinfo)

    async def _initCoreLayers(self):
        self.layerdefs = self.cortexdata.getSubKeyVal('layer:info:')
        for ldef in self.layerdefs.values():
            await self._initLayr(ldef)

    @s_nexus.Pusher.onPushAuto('layer:push:add')
    async def addLayrPush(self, layriden, pdef):

        s_schemas.reqValidPush(pdef)

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

        layr.layrinfo['pushs'] = pushs
        self.layerdefs.set(layr.iden, layr.layrinfo)

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

        layr.layrinfo['pushs'] = pushs
        self.layerdefs.set(layr.iden, layr.layrinfo)

        await self.delActiveCoro(pushiden)

    @s_nexus.Pusher.onPushAuto('layer:pull:add')
    async def addLayrPull(self, layriden, pdef):

        s_schemas.reqValidPull(pdef)

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

        layr.layrinfo['pulls'] = pulls
        self.layerdefs.set(layr.iden, layr.layrinfo)

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

        layr.layrinfo['pulls'] = pulls
        self.layerdefs.set(layr.iden, layr.layrinfo)

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
        # TODO Remove the defaults in 3.0.0
        csize = pdef.get('chunk:size', s_const.layer_pdef_csize)
        qsize = pdef.get('queue:size', s_const.layer_pdef_qsize)

        async with await s_base.Base.anit() as base:

            queue = s_queue.Queue(maxsize=qsize)

            async def fill():

                try:
                    filloffs = await self.getStormVar(gvar, -1)
                    async for item in layr0.syncNodeEdits(filloffs + 1, wait=True):
                        await queue.put(item)
                    await queue.close()

                except asyncio.CancelledError:  # pragma: no cover
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
                    if len(alledits) > csize:
                        await layr1.storNodeEdits(alledits, meta)
                        await self.setStormVar(gvar, offs)
                        alledits.clear()

                if alledits:
                    await layr1.storNodeEdits(alledits, meta)
                    await self.setStormVar(gvar, offs)

    async def _checkNexsIndx(self):
        layroffs = [await layr.getEditIndx() for layr in list(self.layers.values())]
        if layroffs:
            maxindx = max(layroffs)
            if maxindx > await self.getNexsIndx():
                await self.setNexsIndx(maxindx)

    async def saveLayerNodeEdits(self, layriden, edits, meta):
        layr = self.reqLayer(layriden)
        return await layr.saveNodeEdits(edits, meta)

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {iden}', iden=iden)

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

        copyinfo = self.layerdefs.get(iden)

        for name, valu in copyinfo.items():
            ldef.setdefault(name, valu)

        self.layerdefs.set(newiden, ldef)

        copylayr = await self._initLayr(ldef, nexsoffs=nexsitem[0])

        creator = copyinfo.get('creator')
        user = await self.auth.reqUser(creator)
        await user.setAdmin(True, gateiden=newiden, logged=False)

        return ldef

    def addStormCmd(self, ctor):
        '''
        Add a synapse.lib.storm.Cmd class to the cortex.
        '''
        if not s_grammar.isCmdName(ctor.name):
            raise s_exc.BadCmdName(name=ctor.name)

        self.stormcmds[ctor.name] = ctor

    async def addStormDmon(self, ddef):
        '''
        Add a storm dmon task.
        '''
        if ddef.get('iden') is None:
            ddef['iden'] = s_common.guid()

        if await self.getStormDmon(ddef['iden']) is not None:
            mesg = f'Duplicate iden specified for dmon: {ddef["iden"]}'
            raise s_exc.DupIden(mesg=mesg)

        return await self._push('storm:dmon:add', ddef)

    @s_nexus.Pusher.onPushAuto('storm:dmon:bump')
    async def bumpStormDmon(self, iden):
        ddef = self.stormdmondefs.get(iden)
        if ddef is None:
            return False

        if self.isactive:
            dmon = self.stormdmons.getDmon(iden)
            if dmon is not None:
                await dmon.bump()

        return True

    async def _bumpUserDmons(self, iden):
        '''
        Bump all the Dmons for a given user.
        Args:
            iden (str): User iden.
        '''
        for dmoniden, ddef in list(self.stormdmondefs.items()):
            if ddef.get('user') == iden:
                await self.bumpStormDmon(dmoniden)

    @s_nexus.Pusher.onPushAuto('storm:dmon:enable')
    async def enableStormDmon(self, iden):
        dmon = self.stormdmons.getDmon(iden)
        if dmon is None:
            return False

        if dmon.enabled:
            return False

        dmon.enabled = True
        dmon.ddef['enabled'] = True

        self.stormdmondefs.set(iden, dmon.ddef)

        if self.isactive:
            await dmon.run()

        return True

    @s_nexus.Pusher.onPushAuto('storm:dmon:disable')
    async def disableStormDmon(self, iden):

        dmon = self.stormdmons.getDmon(iden)
        if dmon is None:
            return False

        if not dmon.enabled:
            return False

        dmon.enabled = False
        dmon.ddef['enabled'] = False

        self.stormdmondefs.set(iden, dmon.ddef)

        if self.isactive:
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

        self.stormdmondefs.set(iden, ddef)
        return dmon.pack()

    async def delStormDmon(self, iden):
        '''
        Stop and remove a storm dmon.
        '''
        ddef = self.stormdmondefs.get(iden)
        if ddef is None:
            mesg = f'No storm daemon exists with iden {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        return await self._push('storm:dmon:del', iden)

    @s_nexus.Pusher.onPush('storm:dmon:del')
    async def _delStormDmon(self, iden):
        ddef = self.stormdmondefs.pop(iden)
        if ddef is None:  # pragma: no cover
            return
        await self.stormdmons.popDmon(iden)

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    async def runStormDmon(self, iden, ddef):

        # validate ddef before firing task
        s_schemas.reqValidDdef(ddef)

        dmon = self.stormdmons.getDmon(iden)
        if dmon is not None:
            return dmon

        await self.auth.reqUser(ddef['user'])

        # raises if parser failure
        await self.getStormQuery(ddef.get('storm'))

        dmon = await self.stormdmons.addDmon(iden, ddef)

        return dmon

    @s_cell.from_leader
    async def getStormDmon(self, iden):
        return self.stormdmons.getDmonDef(iden)

    @s_cell.from_leader
    async def getStormDmons(self):
        return self.stormdmons.getDmonDefs()

    @s_cell.from_leader
    async def getStormDmonLog(self, iden):
        return self.stormdmons.getDmonRunlog(iden)

    def addStormLib(self, path, ctor):

        self.stormlibs.append((path, ctor))

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
            pass

    async def setUserLocked(self, iden, locked):
        retn = await s_cell.Cell.setUserLocked(self, iden, locked)
        await self._bumpUserDmons(iden)
        return retn

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

    def _viewFromOpts(self, opts, user=None):

        if user is None:
            user = self._userFromOpts(opts)

        viewiden = opts.get('view')
        if viewiden is None:
            viewiden = user.profile.get('cortex:view')

        if viewiden is None:
            viewiden = self.view.iden

        # For backwards compatibility, resolve references to old view iden == cortex.iden to the main view
        # TODO:  due to our migration policy, remove in 3.0.0
        if viewiden == self.iden:  # pragma: no cover
            viewiden = self.view.iden

        view = self.views.get(viewiden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view iden={viewiden}', iden=viewiden)

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
            raise s_exc.NoSuchUser(mesg=mesg, user=useriden)

        return user

    async def count(self, text, opts=None):

        opts = self._initStormOpts(opts)

        if self.stormpool is not None and opts.get('mirror', True):
            proxy = await self._getMirrorProxy(opts)

            if proxy is not None:
                proxname = proxy._ahainfo.get('name')
                extra = await self.getLogExtra(mirror=proxname, hash=s_storm.queryhash(text))
                logger.info(f'Offloading Storm query to mirror {proxname}.', extra=extra)

                mirropts = await self._getMirrorOpts(opts)

                mirropts.setdefault('_loginfo', {})
                mirropts['_loginfo']['pool:from'] = self.ahasvcname

                try:
                    return await proxy.count(text, opts=mirropts)

                except s_exc.TimeOut:
                    mesg = 'Timeout waiting for query mirror, running locally instead.'
                    logger.warning(mesg)

        if (nexsoffs := opts.get('nexsoffs')) is not None:
            if not await self.waitNexsOffs(nexsoffs, timeout=opts.get('nexstimeout')):
                raise s_exc.TimeOut(mesg=f'Timeout waiting for nexus offset {nexsoffs} in count()')

        view = self._viewFromOpts(opts)

        i = 0
        async for _ in view.eval(text, opts=opts):
            i += 1

        return i

    async def _getMirrorOpts(self, opts):
        assert 'nexsoffs' in opts
        mirropts = s_msgpack.deepcopy(opts)
        mirropts['mirror'] = False
        mirropts['nexstimeout'] = self.stormpoolopts.get('timeout:sync')
        return mirropts

    async def _getMirrorProxy(self, opts):

        if self.stormpool is None:  # pragma: no cover
            return None

        size = self.stormpool.size()
        if size == 0:
            logger.warning('Storm query mirror pool is empty, running query locally.')
            return None

        for _ in range(size):

            try:
                timeout = self.stormpoolopts.get('timeout:connection')
                proxy = await self.stormpool.proxy(timeout=timeout)
                proxyname = proxy._ahainfo.get('name')
                if proxyname is not None and proxyname == self.ahasvcname:
                    # we are part of the pool and were selected. Convert to local use.
                    return None

            except TimeoutError:
                logger.warning('Timeout waiting for pool mirror proxy.')
                continue

            try:

                curoffs = opts.setdefault('nexsoffs', await self.getNexsIndx() - 1)
                miroffs = await s_common.wait_for(proxy.getNexsIndx(), timeout) - 1
                if (delta := curoffs - miroffs) <= MAX_NEXUS_DELTA:
                    return proxy

                mesg = f'Pool mirror [{proxyname}] is too far out of sync. Skipping.'
                logger.warning(mesg, extra=await self.getLogExtra(delta=delta, mirror=proxyname, mirror_offset=miroffs))

            except s_exc.IsFini:
                mesg = f'Proxy for pool mirror [{proxyname}] was shutdown. Skipping.'
                logger.warning(mesg, extra=await self.getLogExtra(mirror=proxyname))

            except TimeoutError:
                mesg = f'Timeout waiting for pool mirror [{proxyname}] Nexus offset.'
                logger.warning(mesg, extra=await self.getLogExtra(mirror=proxyname))

        logger.warning('Pool members exhausted. Running query locally.', extra=await self.getLogExtra())
        return None

    async def storm(self, text, opts=None):

        opts = self._initStormOpts(opts)

        if self.stormpool is not None and opts.get('mirror', True):
            proxy = await self._getMirrorProxy(opts)

            if proxy is not None:
                proxname = proxy._ahainfo.get('name')
                extra = await self.getLogExtra(mirror=proxname, hash=s_storm.queryhash(text))
                logger.info(f'Offloading Storm query to mirror {proxname}.', extra=extra)

                mirropts = await self._getMirrorOpts(opts)

                mirropts.setdefault('_loginfo', {})
                mirropts['_loginfo']['pool:from'] = self.ahasvcname

                try:
                    async for mesg in proxy.storm(text, opts=mirropts):
                        yield mesg
                    return

                except s_exc.TimeOut:
                    mesg = 'Timeout waiting for query mirror, running locally instead.'
                    logger.warning(mesg, extra=extra)

        if (nexsoffs := opts.get('nexsoffs')) is not None:
            if not await self.waitNexsOffs(nexsoffs, timeout=opts.get('nexstimeout')):
                raise s_exc.TimeOut(mesg=f'Timeout waiting for nexus offset {nexsoffs} in storm().')

        view = self._viewFromOpts(opts)
        async for mesg in view.storm(text, opts=opts):
            yield mesg

    async def callStorm(self, text, opts=None):

        opts = self._initStormOpts(opts)

        if self.stormpool is not None and opts.get('mirror', True):
            proxy = await self._getMirrorProxy(opts)

            if proxy is not None:
                proxname = proxy._ahainfo.get('name')
                extra = await self.getLogExtra(mirror=proxname, hash=s_storm.queryhash(text))
                logger.info(f'Offloading Storm query to mirror {proxname}.', extra=extra)

                mirropts = await self._getMirrorOpts(opts)

                mirropts.setdefault('_loginfo', {})
                mirropts['_loginfo']['pool:from'] = self.ahasvcname

                try:
                    return await proxy.callStorm(text, opts=mirropts)
                except s_exc.TimeOut:
                    mesg = 'Timeout waiting for query mirror, running locally instead.'
                    logger.warning(mesg, extra=extra)

        if (nexsoffs := opts.get('nexsoffs')) is not None:
            if not await self.waitNexsOffs(nexsoffs, timeout=opts.get('nexstimeout')):
                raise s_exc.TimeOut(mesg=f'Timeout waiting for nexus offset {nexsoffs} in callStorm().')

        view = self._viewFromOpts(opts)
        return await view.callStorm(text, opts=opts)

    async def exportStorm(self, text, opts=None):
        opts = self._initStormOpts(opts)

        if self.stormpool is not None and opts.get('mirror', True):
            proxy = await self._getMirrorProxy(opts)

            if proxy is not None:
                proxname = proxy._ahainfo.get('name')
                extra = await self.getLogExtra(mirror=proxname, hash=s_storm.queryhash(text))
                logger.info(f'Offloading Storm query to mirror {proxname}.', extra=extra)

                mirropts = await self._getMirrorOpts(opts)

                mirropts.setdefault('_loginfo', {})
                mirropts['_loginfo']['pool:from'] = self.ahasvcname

                try:
                    async for mesg in proxy.exportStorm(text, opts=mirropts):
                        yield mesg
                    return

                except s_exc.TimeOut:
                    mesg = 'Timeout waiting for query mirror, running locally instead.'
                    logger.warning(mesg, extra=extra)

        if (nexsoffs := opts.get('nexsoffs')) is not None:
            if not await self.waitNexsOffs(nexsoffs, timeout=opts.get('nexstimeout')):
                raise s_exc.TimeOut(mesg=f'Timeout waiting for nexus offset {nexsoffs} in exportStorm().')

        user = self._userFromOpts(opts)
        view = self._viewFromOpts(opts)

        taskinfo = {'query': text, 'view': view.iden}
        taskiden = opts.get('task')
        await self.boss.promote('storm:export', user=user, info=taskinfo, taskiden=taskiden)

        with s_scope.enter({'user': user}):

            async with await s_spooled.Dict.anit(dirn=self.dirn, cell=self) as spooldict:
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

    async def exportStormToAxon(self, text, opts=None):
        async with await self.axon.upload() as fd:
            async for pode in self.exportStorm(text, opts=opts):
                await fd.write(s_msgpack.en(pode))
            size, sha256 = await fd.save()
            return (size, s_common.ehex(sha256))

    async def feedFromAxon(self, sha256, opts=None):

        opts = self._initStormOpts(opts)
        user = self._userFromOpts(opts)
        view = self._viewFromOpts(opts)

        taskiden = opts.get('task')
        taskinfo = {'name': 'syn.nodes', 'sha256': sha256, 'view': view.iden}

        await self.boss.promote('feeddata', user=user, info=taskinfo, taskiden=taskiden)

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
                    async for node in snap.addNodes(items):
                        count += 1

                if feedexc is not None:
                    raise feedexc

        return count

    async def nodes(self, text, opts=None):
        '''
        A simple non-streaming way to return a list of nodes.
        '''
        if self.isfini:  # pragma: no cover
            raise s_exc.IsFini()

        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)
        return await view.nodes(text, opts=opts)

    async def stormlist(self, text, opts=None):
        return [m async for m in self.storm(text, opts=opts)]

    async def _getStormEval(self, text):
        try:
            astvalu = copy.deepcopy(await s_parser.evalcache.aget(text))
        except s_exc.FatalErr:
            logger.exception(f'Fatal error while parsing [{text}]', extra={'synapse': {'text': text}})
            await self.fini()
            raise
        astvalu.init(self)
        return astvalu

    async def _getStormQuery(self, args):
        try:
            query = copy.deepcopy(await s_parser.querycache.aget(args))
        except s_exc.FatalErr:
            logger.exception(f'Fatal error while parsing [{args}]', extra={'synapse': {'text': args[0]}})
            await self.fini()
            raise
        query.init(self)
        await asyncio.sleep(0)
        return query

    async def getStormQuery(self, text, mode='storm'):
        return await self.querycache.aget((text, mode))

    @contextlib.asynccontextmanager
    async def getStormRuntime(self, query, opts=None):

        opts = self._initStormOpts(opts)

        view = self._viewFromOpts(opts)
        user = self._userFromOpts(opts)

        async with await self.snap(user=user, view=view) as snap:
            async with snap.getStormRuntime(query, opts=opts, user=user) as runt:
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
        await self.getStormQuery(text, mode=mode)
        return True

    def _logStormQuery(self, text, user, info=None):
        '''
        Log a storm query.
        '''
        if self.stormlog:
            if info is None:
                info = {}
            info['text'] = text
            info['username'] = user.name
            info['user'] = user.iden
            info['hash'] = s_storm.queryhash(text)
            stormlogger.log(self.stormloglvl, 'Executing storm query {%s} as [%s]', text, user.name,
                            extra={'synapse': info})

    async def getNodeByNdef(self, ndef, view=None):
        '''
        Return a single Node() instance by (form,valu) tuple.
        '''
        name, valu = ndef

        form = self.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm.init(name)

        norm, info = form.type.norm(valu)

        buid = s_common.buid((form.name, norm))

        async with await self.snap(view=view) as snap:
            return await snap.getNodeByBuid(buid)

    def getCoreInfo(self):
        '''This API is deprecated.'''
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

        cmds = []

        for name, cmd in self.stormcmds.items():
            entry = {
                'name': name,
                'doc': cmd.getCmdBrief(),
            }

            if cmd.pkgname:
                entry['package'] = cmd.pkgname

            if cmd.svciden:
                entry['svciden'] = cmd.svciden

            cmds.append(entry)

        ret = {
            'libraries': s_stormtypes.registry.getLibDocs(),
            'types': s_stormtypes.registry.getTypeDocs(),
            'commands': cmds,
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
            viewiden (str): The iden of a view to use.
                If a view is not specified, the default view is used.
        '''

        view = self.getView(viewiden)
        if view is None:
            raise s_exc.NoSuchView(mesg=f'No such view iden={viewiden}', iden=viewiden)

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

        if not ctor.startswith(('synapse.tests', 'synapse.models')):
            s_common.deprecated("'modules' Cortex config value", curv='2.206.0')

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

    async def getPropNorm(self, prop, valu, typeopts=None):
        '''
        Get the normalized property value based on the Cortex data model.

        Args:
            prop (str): The property to normalize.
            valu: The value to normalize.
            typeopts: A Synapse type opts dictionary used to further normalize the value.

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

        tobj = pobj.type
        if typeopts:
            tobj = tobj.clone(typeopts)

        norm, info = tobj.norm(valu)
        return norm, info

    async def getTypeNorm(self, name, valu, typeopts=None):
        '''
        Get the normalized type value based on the Cortex data model.

        Args:
            name (str): The type to normalize.
            valu: The value to normalize.
            typeopts: A Synapse type opts dictionary used to further normalize the value.

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
        if typeopts:
            tobj = tobj.clone(typeopts)

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
        s_schemas.reqValidCronDef(cdef)

        iden = cdef.get('iden')
        appt = self.agenda.appts.get(iden)
        if appt is not None:
            raise s_exc.DupIden(mesg=f'Duplicate cron iden ({iden})')

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
            raise s_exc.BadConfValu(mesg='Unrecognized time unit')

        if not cdef.get('iden'):
            cdef['iden'] = s_common.guid()

        cdef['created'] = s_common.now()

        opts = {'user': cdef['creator'], 'view': cdef.get('view')}

        view = self._viewFromOpts(opts)
        cdef['view'] = view.iden

        return await self._push('cron:add', cdef)

    @s_nexus.Pusher.onPush('cron:add')
    async def _onAddCronJob(self, cdef):

        iden = cdef['iden']

        appt = self.agenda.appts.get(iden)
        if appt is not None:
            return appt.pack()

        self.auth.reqNoAuthGate(iden)

        user = await self.auth.reqUser(cdef['creator'])

        cdef = await self.agenda.add(cdef)

        await self.auth.addAuthGate(iden, 'cronjob')
        await user.setAdmin(True, gateiden=iden, logged=False)

        await self.feedBeholder('cron:add', cdef, gates=[iden])
        return cdef

    async def moveCronJob(self, useriden, croniden, viewiden):
        view = self._viewFromOpts({'view': viewiden, 'user': useriden})

        appt = self.agenda.appts.get(croniden)
        if appt is None:
            raise s_exc.NoSuchIden(iden=croniden)

        if appt.view == view.iden:
            return croniden

        return await self._push('cron:move', croniden, viewiden)

    @s_nexus.Pusher.onPush('cron:move')
    async def _onMoveCronJob(self, croniden, viewiden):
        await self.agenda.move(croniden, viewiden)
        await self.feedBeholder('cron:move', {'iden': croniden, 'view': viewiden}, gates=[croniden])
        return croniden

    @s_nexus.Pusher.onPushAuto('cron:del')
    async def delCronJob(self, iden):
        '''
        Delete a cron job

        Args:
            iden (bytes):  The iden of the cron job to be deleted
        '''
        await self._killCronTask(iden)
        try:
            await self.agenda.delete(iden)
        except s_exc.NoSuchIden:
            return

        await self.feedBeholder('cron:del', {'iden': iden}, gates=[iden])
        await self.auth.delAuthGate(iden)

    @s_nexus.Pusher.onPushAuto('cron:mod')
    async def updateCronJob(self, iden, query):
        '''
        Change an existing cron job's query

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.mod(iden, query)
        await self.feedBeholder('cron:edit:query', {'iden': iden, 'query': query}, gates=[iden])

    @s_nexus.Pusher.onPushAuto('cron:enable')
    async def enableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.enable(iden)
        await self.feedBeholder('cron:enable', {'iden': iden}, gates=[iden])
        logger.info(f'Enabled cron job {iden}', extra=await self.getLogExtra(iden=iden, status='MODIFY'))

    @s_nexus.Pusher.onPushAuto('cron:disable')
    async def disableCronJob(self, iden):
        '''
        Enable a cron job

        Args:
            iden (bytes):  The iden of the cron job to be changed
        '''
        await self.agenda.disable(iden)
        await self._killCronTask(iden)
        await self.feedBeholder('cron:disable', {'iden': iden}, gates=[iden])
        logger.info(f'Disabled cron job {iden}', extra=await self.getLogExtra(iden=iden, status='MODIFY'))

    async def killCronTask(self, iden):
        if self.agenda.appts.get(iden) is None:
            return False
        return await self._push('cron:task:kill', iden)

    @s_nexus.Pusher.onPush('cron:task:kill')
    async def _killCronTask(self, iden):

        appt = self.agenda.appts.get(iden)
        if appt is None:
            return False

        task = appt.task
        if task is None:
            return False

        self.schedCoro(task.kill())
        return True

    async def listCronJobs(self):
        '''
        Get information about all the cron jobs accessible to the current user
        '''
        crons = []

        for _, cron in self.agenda.list():

            info = cron.pack()

            user = self.auth.user(cron.creator)
            if user is not None:
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

        if name == 'creator':
            await self.auth.reqUser(valu)
            appt.creator = valu

        elif name == 'name':
            appt.name = str(valu)

        elif name == 'doc':
            appt.doc = str(valu)

        elif name == 'pool':
            appt.pool = bool(valu)

        else:
            mesg = f'editCronJob name {name} is not supported for editing.'
            raise s_exc.BadArg(mesg=mesg)

        await appt.save()

        pckd = appt.pack()
        await self.feedBeholder(f'cron:edit:{name}', {'iden': iden, name: pckd.get(name)}, gates=[iden])
        return pckd

    @s_nexus.Pusher.onPushAuto('cron:edits')
    async def addCronEdits(self, iden, edits):
        '''
        Take a dictionary of edits and apply them to the appointment (cron job)
        '''
        appt = await self.agenda.get(iden)
        await appt.edits(edits)

    @contextlib.asynccontextmanager
    async def enterMigrationMode(self):
        async with self._migration_lock:
            self.migration = True
            yield
            self.migration = False

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

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
            raise s_exc.NoSuchLayer(mesg=f'No such layer {layriden}', iden=layriden)

        async for item in layr.iterTagPropRows(tag, prop, form=form, stortype=stortype, startvalu=startvalu):
            yield item

    def _initVaults(self):
        self.vaultsdb = self.slab.initdb('vaults')
        # { idenb: s_msgpack.en(vault), ... }

        self.vaultsbynamedb = self.slab.initdb('vaults:byname')
        # { name.encode(): idenb, ... }

        # TSI = type, scope, iden. This is used to deconflict uniqueness of
        # scoped vaults without requiring a bunch of other indexes.
        self.vaultsbyTSIdb = self.slab.initdb('vaults:byTSI')
        # { TSI.encode(): idenb, ... }

    def _getVaults(self):
        '''
        Slab helper function for getting all vaults.
        '''
        genr = self.slab.scanByFull(db=self.vaultsdb)
        for idenb, byts in genr:
            vault = s_msgpack.un(byts)
            yield vault

    def _getVaultByBidn(self, bidn):
        '''
        Slab helper function for getting a vault by iden (bytes).
        '''
        byts = self.slab.get(bidn, db=self.vaultsdb)
        if byts is None:
            return None

        vault = s_msgpack.un(byts)

        return vault

    def _getVaultByTSI(self, vtype, scope, iden):
        '''
        Slab helper function for getting a vault by type,scope,iden.
        '''
        if scope == 'global':
            tsi = f'{vtype}:global'
        elif scope in ('user', 'role'):
            tsi = f'{vtype}:{scope}:{iden}'
        else:
            raise s_exc.BadArg(mesg=f'Invalid scope: {scope}.')

        bidn = self.slab.get(tsi.encode(), db=self.vaultsbyTSIdb)
        if bidn is None:
            return None

        return self._getVaultByBidn(bidn)

    def getVault(self, iden):
        '''
        Get a vault.

        Args:
            iden (str): Iden of the vault to get.

        Returns: vault or None
        '''
        if not s_common.isguid(iden):
            return None

        bidn = s_common.uhex(iden)
        return self._getVaultByBidn(bidn)

    def getVaultByName(self, name):
        '''
        Get a vault by name.

        Args:
            name (str): Name of the vault to get.

        Returns: vault or None
        '''
        bidn = self.slab.get(name.encode(), db=self.vaultsbynamedb)
        if bidn is None:
            return None
        return self._getVaultByBidn(bidn)

    def getVaultByType(self, vtype, useriden, scope=None):
        '''
        Get a vault of type `vtype` and scope `scope` for user with `iden`.

        This function allows the caller to retrieve a vault of the specified
        `vtype` by searching for the first available vault that matches the
        `vtype` and `scope` criteria. The search order for opening vaults is as
        follows:
            - If `scope` is specified, return the vault with `vtype` and `scope`.
              Return None if such a vault doesn't exist.
            - Check 'user' scope for a vault of `vtype`. Continue if non-existent.
            - Check 'role' scope for a vault of `vtype`. Continue if non-existent.
            - Check 'global' scope for a vault of `vtype`. Continue if non-existent.
            - Return None

        Args:
            vtype (str): Type of the vault to open.
            useriden (str): Iden of user trying to open the vault.
            scope (str|None): The vault scope to open.

        Raises:
            synapse.exc.BadArg: Invalid scope specified.

        Returns: vault or None if matching vault could not be found.
        '''
        if scope not in (None, 'user', 'role', 'global'):
            raise s_exc.BadArg(mesg=f'Invalid scope: {scope}.')

        def _getVault(_scope):
            vault = None
            if _scope == 'user':
                vault = self._getVaultByTSI(vtype, _scope, useriden)

            elif _scope == 'role':
                user = self.auth.user(useriden)
                if user is None:
                    mesg = f'No user with iden {useriden}.'
                    raise s_exc.NoSuchUser(mesg=mesg, user=useriden)

                for role in user.getRoles():
                    vault = self._getVaultByTSI(vtype, _scope, role.iden)
                    if vault:
                        if not self._hasEasyPerm(vault, user, s_cell.PERM_READ):
                            vault = None
                            continue

                        break

            elif _scope == 'global':
                vault = self._getVaultByTSI(vtype, _scope, None)

            return vault

        # If caller specified a scope, return that vault if it exists
        if scope is not None:
            return _getVault(scope)

        # Finally, try the user, role, and global vaults in order
        for _scope in ('user', 'role', 'global'):
            vault = _getVault(_scope)
            if vault:
                return vault

        return None

    def reqVault(self, iden):
        '''
        Get a vault by iden.

        Args:
            iden (str): Iden of the vault to get.

        Raises:
            synapse.exc.NoSuchIden: Vault with `iden` not found.

        Returns: vault
        '''
        if not s_common.isguid(iden):
            raise s_exc.BadArg(mesg=f'Iden is not a valid iden: {iden}.')

        vault = self.getVault(iden)
        if vault is None:
            raise s_exc.NoSuchIden(mesg=f'Vault not found for iden: {iden}.', iden=iden)

        return vault

    def reqVaultByName(self, name):
        '''
        Get a vault by name.

        Args:
            name (str): Name of the vault to get.

        Raises:
            synapse.exc.NoSuchName: Vault with `name` not found.

        Returns: vault
        '''
        vault = self.getVaultByName(name)
        if vault is None:
            raise s_exc.NoSuchName(mesg=f'Vault not found for name: {name}.')

        return vault

    def reqVaultByType(self, vtype, iden, scope=None):
        '''
        Get a vault by type.

        Args:
            vtype (str): Type of the vault to get.
            iden (str): Iden of the user or role for the vault type.
            scope (str|None): Scope of the vault to get.

        Raises:
            synapse.exc.NoSuchName: Vault with `vtype`/`iden`/`scope` not found.

        Returns: vault
        '''
        vault = self.getVaultByType(vtype, iden, scope)
        if vault is None:
            raise s_exc.NoSuchName(mesg=f'Vault not found for type: {vtype}.')

        return vault

    async def addVault(self, vdef):
        '''
        Create a new vault.

        Args:
            vdef (dict): The vault to add.

        Raises:
            synapse.exc.SchemaViolation: `vdef` does not conform to the vault schema.
            synapse.exc.DupName:
                - Vault already exists for type/scope/owner.
                - Vault already exists with specified name.
            synapse.exc.BadArg:
                - Invalid vault definition provided.
                - Owner required for unscoped, user, and role vaults.
                - Vault secrets is not msgpack safe.
                - Vault configs is not msgpack safe.

        Returns: iden of new vault
        '''
        if not isinstance(vdef, dict):
            raise s_exc.BadArg(mesg='Invalid vault definition provided.')

        # Set some standard properties on the vdef before validating
        vdef['iden'] = s_common.guid()

        if 'permissions' in vdef:
            vdef.pop('permissions')

        self._initEasyPerm(vdef, default=s_cell.PERM_DENY)

        vault = s_schemas.reqValidVault(vdef)

        scope = vault.get('scope')
        vtype = vault.get('type')
        owner = vault.get('owner')
        name = vault.get('name')

        if owner is None and scope != 'global':
            raise s_exc.BadArg(mesg='Owner required for unscoped, user, and role vaults.')

        # Make sure the type/scope/owner combination is unique. Not for unscoped vaults
        if scope is not None and self._getVaultByTSI(vtype, scope, owner) is not None:
            raise s_exc.DupName(mesg=f'Vault already exists for type {vtype}, scope {scope}, owner {owner}.')

        # Make sure the requested name is unique
        if self.getVaultByName(name) is not None:
            raise s_exc.DupName(mesg=f'Vault {name} already exists.')

        secrets = vault.get('secrets')
        configs = vault.get('configs')

        try:
            s_msgpack.en(secrets)
        except s_exc.NotMsgpackSafe as exc:
            raise s_exc.BadArg(mesg=f'Vault secrets must be msgpack safe.') from None

        try:
            s_msgpack.en(configs)
        except s_exc.NotMsgpackSafe as exc:
            raise s_exc.BadArg(mesg=f'Vault configs must be msgpack safe.') from None

        if scope == 'global':
            # everyone gets read access
            await self._setEasyPerm(vault, 'roles', self.auth.allrole.iden, s_cell.PERM_READ)

        elif scope == 'user':
            user = self.auth.user(owner)
            if user is None:
                raise s_exc.NoSuchUser(mesg=f'User with iden {owner} not found.')

            # The user is the admin, everyone else no access
            await self._setEasyPerm(vault, 'users', owner, s_cell.PERM_ADMIN)

        elif scope == 'role':
            role = self.auth.role(owner)
            if role is None:
                raise s_exc.NoSuchRole(mesg=f'Role with iden {owner} not found.')

            # role members gets read access
            await self._setEasyPerm(vault, 'roles', owner, s_cell.PERM_READ)

        else:
            # Unscoped vaults

            # The creator gets admin, everyone else no access
            await self._setEasyPerm(vault, 'users', owner, s_cell.PERM_ADMIN)

        return await self._push('vault:add', vault)

    @s_nexus.Pusher.onPush('vault:add')
    async def _addVault(self, vault):
        iden = vault.get('iden')
        name = vault.get('name')
        scope = vault.get('scope')

        bidn = s_common.uhex(iden)

        if scope is not None:
            vtype = vault.get('type')
            owner = vault.get('owner')

            if scope == 'global':
                tsi = f'{vtype}:global'
            else:
                tsi = f'{vtype}:{scope}:{owner}'

            self.slab.put(tsi.encode(), bidn, db=self.vaultsbyTSIdb)

        self.slab.put(name.encode(), bidn, db=self.vaultsbynamedb)
        self.slab.put(bidn, s_msgpack.en(vault), db=self.vaultsdb)
        return iden

    async def setVaultSecrets(self, iden, key, valu):
        '''
        Set vault secret item.

        This function sets the `key`:`valu` into the vault secrets.

        Args:
            iden (str): The iden of the vault to edit.
            key (str): Vault secret key.
            valu (str): Vault secret value. s_common.novalu to delete a key.

        Raises:
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.
            synapse.exc.NotMsgpackSafe: One of `key` or `valu` is not msgpack safe.

        Returns: Updated vault.
        '''
        vault = self.reqVault(iden)

        secrets = vault.get('secrets')

        delete = False

        if valu is s_common.novalu:
            if key not in secrets:
                raise s_exc.BadArg(mesg=f'Key {key} not found in vault secrets.')

            valu = None
            delete = True

        else:
            try:
                s_msgpack.en({key: valu})
            except s_exc.NotMsgpackSafe as exc:
                raise s_exc.NotMsgpackSafe(mesg=f'Vault secrets must be msgpack safe.') from None

        return await self._push('vault:data:set', iden, 'secrets', key, valu, delete)

    async def setVaultConfigs(self, iden, key, valu):
        '''
        Set vault config item.

        This function sets the `key`:`valu` into the vault configs.

        Args:
            iden (str): The iden of the vault to edit.
            key (str): Vault secret key.
            valu (str): Vault secret value. s_common.novalu to delete a key.

        Raises:
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.
            synapse.exc.NotMsgpackSafe: One of `key` or `valu` is not msgpack safe.

        Returns: Updated vault.
        '''
        vault = self.reqVault(iden)

        configs = vault.get('configs')

        delete = False

        if valu is s_common.novalu:
            if key not in configs:
                raise s_exc.BadArg(mesg=f'Key {key} not found in vault configs.')

            valu = None
            delete = True

        else:
            try:
                s_msgpack.en({key: valu})
            except s_exc.NotMsgpackSafe as exc:
                raise s_exc.NotMsgpackSafe(mesg=f'Vault configs must be msgpack safe.') from None

        return await self._push('vault:data:set', iden, 'configs', key, valu, delete)

    @s_nexus.Pusher.onPush('vault:data:set')
    async def _setVaultData(self, iden, obj, key, valu, delete):
        vault = self.reqVault(iden)
        data = vault.get(obj)

        bidn = s_common.uhex(iden)

        if delete:
            if key in data:
                data.pop(key)
        else:
            data[key] = valu

        self.slab.put(bidn, s_msgpack.en(vault), db=self.vaultsdb)
        return data

    async def replaceVaultConfigs(self, iden, valu):
        '''
        Replace the entire vault config.

        Args:
            iden (str): The iden of the vault to edit.
            valu (str): New configs object to store on the vault.

        Raises:
            synapse.exc.BadArg: `valu` is not a dictionary.
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.
            synapse.exc.NotMsgpackSafe: `valu` is not msgpack safe.

        Returns: New configs.
        '''
        vault = self.reqVault(iden)

        if not isinstance(valu, dict):
            raise s_exc.BadArg(mesg='valu must be a dictionary.', name='valu', valu=valu)

        try:
            s_msgpack.en(valu)
        except s_exc.NotMsgpackSafe:
            short = textwrap.shorten(repr(valu), width=64)
            raise s_exc.NotMsgpackSafe(
                mesg='Vault configs must be msgpack safe.',
                name='valu',
                valu=short) from None

        return await self._push('vault:data:replace', iden, 'configs', valu)

    async def replaceVaultSecrets(self, iden, valu):
        '''
        Replace the entire vault config.

        Args:
            iden (str): The iden of the vault to edit.
            valu (str): New secrets object to store on the vault.

        Raises:
            synapse.exc.BadArg: `valu` is not a dictionary.
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.
            synapse.exc.NotMsgpackSafe: `valu` is not msgpack safe.

        Returns: New secrets.
        '''
        vault = self.reqVault(iden)

        if not isinstance(valu, dict):
            raise s_exc.BadArg(mesg='valu must be a dictionary.', name='valu', valu=valu)

        try:
            s_msgpack.en(valu)
        except s_exc.NotMsgpackSafe:
            short = textwrap.shorten(repr(valu), width=64)
            raise s_exc.NotMsgpackSafe(
                mesg='Vault secrets must be msgpack safe.',
                name='valu',
                valu=short) from None

        return await self._push('vault:data:replace', iden, 'secrets', valu)

    @s_nexus.Pusher.onPush('vault:data:replace')
    async def _replaceVaultData(self, iden, obj, valu):
        vault = self.reqVault(iden)
        bidn = s_common.uhex(iden)

        vault[obj] = valu

        self.slab.put(bidn, s_msgpack.en(vault), db=self.vaultsdb)
        return valu

    def listVaults(self):
        '''
        List all vaults.

        Args: None

        Raises: None

        Yields: tuples of vault info: (<iden>, <name>, <type>, <scope>).
        '''
        for vault in self._getVaults():
            yield vault

    async def setVaultPerm(self, viden, iden, level):
        '''
        Set vault permissions.
        Args:
            viden (str): The iden of the vault to edit.
            iden (str): Iden of the user/role to add permissions for.
            level (int): Easy perms level.

        Raises:
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.

        Returns: Updated vault.
        '''
        vault = self.reqVault(viden)

        scope = 'users'
        ident = self.auth.user(iden)
        if ident is None:
            scope = 'roles'
            ident = self.auth.role(iden)
            if ident is None:
                raise s_exc.NoSuchIden(mesg=f'Iden {iden} is not a valid user or role.', iden=iden)

        await self._setEasyPerm(vault, scope, ident.iden, level)
        permissions = vault.get('permissions')
        return await self._push(('vault:set'), viden, 'permissions', permissions)

    async def renameVault(self, iden, name):
        '''
        Rename a vault.

        Args:
            iden (str): Iden of the vault to rename.
            name (str): New vault name.

        Raises:
            synapse.exc.NoSuchIden: Vault with `iden` does not exist.
            synapse.exc.DupName: Vault with `name` already exists.

        Returns: Updated vault.
        '''
        if self.getVaultByName(name) is not None:
            raise s_exc.DupName(mesg=f'Vault with name {name} already exists.', name=name)

        return await self._push(('vault:set'), iden, 'name', name)

    @s_nexus.Pusher.onPush('vault:set')
    async def _setVault(self, iden, key, valu):
        if key not in ('name', 'permissions'):  # pragma: no cover
            raise s_exc.BadArg(mesg='Only vault names and permissions can be changed.')

        vault = self.reqVault(iden)
        oldv = vault.get(key)
        vault[key] = valu

        s_schemas.reqValidVault(vault)

        bidn = s_common.uhex(iden)

        if key == 'name':
            self.slab.delete(oldv.encode(), db=self.vaultsbynamedb)
            self.slab.put(valu.encode(), bidn, db=self.vaultsbynamedb)

        self.slab.put(bidn, s_msgpack.en(vault), db=self.vaultsdb)
        return vault

    @s_nexus.Pusher.onPushAuto('vault:del')
    async def delVault(self, iden):
        '''
        Delete a vault.

        Args:
            iden (str): Iden of the vault to delete.

        Returns: None
        '''
        vault = self.getVault(iden)
        if vault is None:
            return

        bidn = s_common.uhex(iden)

        name = vault.get('name')
        vtype = vault.get('type')
        scope = vault.get('scope')

        tsi = None
        if scope == 'global':
            tsi = f'{vtype}:global'
        elif scope in ('user', 'role'):
            owner = vault.get('owner')
            tsi = f'{vtype}:{scope}:{owner}'

        if tsi is not None:
            self.slab.delete(tsi.encode(), db=self.vaultsbyTSIdb)

        self.slab.delete(name.encode(), db=self.vaultsbynamedb)
        self.slab.delete(bidn, db=self.vaultsdb)

    def _propAllowedReason(self, user, perms, gateiden=None, default=None):
        '''
        Similar to allowed, but always prefer the default value specified by the caller.
        Default values are still pulled from permdefs if there is a match there; but still prefer caller default.
        This results in a ternary response that can be used to know if a rule had a positive/negative or no match.
        The matching reason metadata is also returned.
        '''
        if default is None:
            permdef = self.getPermDef(perms)
            if permdef:
                default = permdef.get('default', default)

        return user.getAllowedReason(perms, gateiden=gateiden, default=default)

    def confirmPropSet(self, user, prop, layriden):
        meta0 = self._propAllowedReason(user, prop.setperms[0], gateiden=layriden)

        if meta0.isadmin:
            return

        allowed0 = meta0.value

        meta1 = self._propAllowedReason(user, prop.setperms[1], gateiden=layriden)
        allowed1 = meta1.value

        if allowed0:
            if allowed1:
                return
            elif allowed1 is False:
                # This is a allow-with-precedence case.
                # Inspect meta to determine if the rule a0 is more specific than rule a1
                if len(meta0.rule) >= len(meta1.rule):
                    return
                user.raisePermDeny(prop.setperms[0], gateiden=layriden)
            return

        if allowed1:
            if allowed0 is None:
                return
            # allowed0 here is False. This is a deny-with-precedence case.
            # Inspect meta to determine if the rule a1 is more specific than rule a0
            if len(meta1.rule) > len(meta0.rule):
                return

        user.raisePermDeny(prop.setperms[0], gateiden=layriden)

    def confirmPropDel(self, user, prop, layriden):
        meta0 = self._propAllowedReason(user, prop.delperms[0], gateiden=layriden)

        if meta0.isadmin:
            return

        allowed0 = meta0.value
        meta1 = self._propAllowedReason(user, prop.delperms[1], gateiden=layriden)
        allowed1 = meta1.value

        if allowed0:
            if allowed1:
                return
            elif allowed1 is False:
                # This is a allow-with-precedence case.
                # Inspect meta to determine if the rule a0 is more specific than rule a1
                if len(meta0.rule) >= len(meta1.rule):
                    return
                user.raisePermDeny(prop.delperms[0], gateiden=layriden)
            return

        if allowed1:
            if allowed0 is None:
                return
            # allowed0 here is False. This is a deny-with-precedence case.
            # Inspect meta to determine if the rule a1 is more specific than rule a0
            if len(meta1.rule) > len(meta0.rule):
                return

        user.raisePermDeny(prop.delperms[0], gateiden=layriden)

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
        logger.debug(f'Creating temporary cortex as {dirn}')
        conf = {
            'health:sysctl:checks': False,
        }
        async with await Cortex.anit(dirn, conf=conf) as core:
            if mods:
                for mod in mods:
                    await core.loadCoreModule(mod)
            async with core.getLocalProxy() as prox:
                yield prox
