#import os
#import json

import logging

import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.datamodel as s_datamodel

import synapse.lib.cell as s_cell
import synapse.lib.snap as s_snap
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.syntax as s_syntax
import synapse.lib.modules as s_modules

logger = logging.getLogger(__name__)

'''
A Cortex implements the synapse hypergraph object.

Many Cortex APIs operate on nodes which consist of primitive data structures
which can be serialized with msgpack/json

Example Node

( (<form>, <valu>), {

    "props": {
        <name>: <valu>,
        ...
    },
    "tags": {

        "#foo": <time>,
        "#foo.bar": <time>,
    },
})
'''

class View:
    '''
    A view represents a cortex as seen from a specific set of layers.

    The view class is used to implement Copy-On-Write layers as well as
    interact with a subset of the layers configured in a Cortex.
    '''
    def __init__(self, core, layers):
        self.core = core
        self.layers = layers
        self.model = core.model

    def snap(self, write=False):
        return s_snap.Snap(self.core, self.layers, write=write)

    def getStormQuery(self, text):
        parser = s_syntax.Parser(self, text)
        return parser.query()

class CoreApi(s_cell.CellApi):
    '''
    The CoreApi is exposed over telepath.
    '''
    def getNodesBy(self, full, valu, cmpr='='):
        '''
        Yield Node.pack() tuples which match the query.
        '''
        for node in self.cell.getNodesBy(full, valu, cmpr=cmpr):
            yield node.pack()

    def addNodes(self, nodes):
        with self.cell.snap(write=True) as snap:
            snap.setUser(self.user)
            for node in snap.addNodes(nodes):
                yield node.pack()

    def eval(self, text, opts=None):

        query = self.cell.view.getStormQuery(text)
        query.setUser(self.user)

        for node in query.evaluate():
            yield node

    def storm(self, text, opts=None):

        query = self.cell.view.getStormQuery(text)
        query.setUser(self.user)

        for mesg in query.execute():
            yield mesg

class Cortex(s_cell.Cell):
    '''
    A Cortex implements the synapse hypergraph.

    The bulk of the Cortex API lives on the Xact() object which can
    be obtained by calling Cortex.snap() in a with block.  This allows
    callers to manage transaction boundaries explicitly and dramatically
    increases performance.
    '''
    confdefs = (

        ('auth:en', {'type': 'bool', 'defval': False,
            'doc': 'Set to True to enable cortex permissions enforcement.'}),

        ('layer:lmdb:mapsize', {'type': 'int', 'defval': s_const.tebibyte,
            'doc': 'The default size for a new LMDB layer map.'}),

        ('modules', {'type': 'list', 'defval': (),
            'doc': 'A list of (ctor, conf) modules to load.'}),

        ('layers', {'type': 'list', 'defval': (),
            'doc': 'A list of layer paths to load.'}),
    )

    cellapi = CoreApi

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        self.views = {}
        self.layers = []
        self.modules = {}

        # load any configured external layers
        for path in self.conf.get('layers'):
            logger.warning('loading external layer: %r' % (path,))
            self.layers.append(s_layer.opendir(path))

        # initialize any cortex directory structures
        self._initCoreDir()

        # these may be used directly
        self.model = s_datamodel.Model()
        self.view = View(self, self.layers)

        self.addCoreMods(s_modules.coremods)

        mods = self.conf.get('modules')
        self.addCoreMods(mods)

    def _initCoreDir(self):

        # each cortex has a default write layer...
        path = s_common.gendir(self.dirn, 'layers', 'default')

        layr = self.openLayerName('default')
        self.layers.append(layr)

    def splices(self, msgs):
        with self.view.snap(write=True) as snap:
            for deltas in snap.splices(msgs):
                yield deltas

    def openLayerName(self, name):
        dirn = s_common.gendir(self.dirn, 'layers', name)
        return s_layer.opendir(dirn)

    def getLayerConf(self, name):
        return {}

    def getForkView(self, iden):
        pass

    def newForkView(self):
        pass

    def eval(self, text, opts=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        query = self.view.getStormQuery(text)
        for node in query.evaluate():
            yield node

    def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.

        Args:
            text (str): A storm query.
            vars (dict): A set of input variables.
            user (str): The user to run as (or s_auth.whoami())
            view (str): An optional view guid.

        Yields:
            ((str,dict)): Storm messages.
        '''
        query = self.view.getStormQuery(text)
        for mesg in query.execute():
            yield mesg

    def getNodeByNdef(self, ndef):
        '''
        Return a single Node() instance by (form,valu) tuple.
        '''
        name, valu = ndef

        form = self.model.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm(name=name)

        norm, info = form.type.norm(valu)

        buid = s_common.buid((form.name, norm))

        with self.snap() as snap:
            return snap.getNodeByBuid(buid)

    def getNodesBy(self, full, valu, cmpr='='):
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
        with self.snap() as snap:
            for node in  snap.getNodesBy(full, valu, cmpr=cmpr):
                yield node

    def addNodes(self, nodedefs):
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
        with self.snap(write=True) as snap:
            yield from snap.addNodes(nodedefs)

    def snap(self, write=False):
        '''
        Return a transaction object for the default view.

        Args:
            write (bool): Set to True for a write transaction.

        Returns:
            (synapse.lib.snap.Snap)

        NOTE: This must be used in a with block.
        '''
        return self.view.snap(write=write)

    def addCoreMods(self, mods):
        '''
        Add a list of (name,conf) module tuples to the cortex.
        '''
        revs = []

        mdefs = []
        added = []

        for ctor in mods:

            modu = self._loadCoreModule(ctor)
            if modu is None:
                continue

            added.append(modu)

            # does the module carry have a data model?
            mdef = modu.getModelDefs()
            if mdef is not None:
                mdefs.extend(mdef)

        # add all data models at once.
        self.model.addDataModels(mdefs)

        # now that we've loaded all their models
        # we can call their init functions
        for  modu in added:
            modu.initCoreModule()

    def loadCoreModule(self, ctor, conf=None):
        '''
        Load a cortex module with the given ctor and conf.

        Args:
            ctor (str): The python module class path
            conf (dict):Config dictionary for the module
        '''
        if conf is None:
            conf = {}

        modu = self._loadCoreModule(ctor)

        mdefs = modu.getModelDefs()
        self.model.addDataModels(mdefs)

        modu.initCoreModule()

    def _loadCoreModule(self, ctor):

        try:

            modu = s_dyndeps.tryDynFunc(ctor, self)

            self.modules[ctor] = modu

            return modu

        except Exception as e:
            logger.exception('mod load fail: %s' % (ctor,))
            return None
