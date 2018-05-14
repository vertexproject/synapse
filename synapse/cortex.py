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

    def snap(self, write=False):
        return s_snap.Snap(self.core, self.layers, write=write)

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
    )

    cellapi = CoreApi

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        self.views = {}
        self.layers = []
        self.modules = {}

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
        return s_layer.Layer(dirn)

    def getLayerConf(self, name):
        return {}

    def getForkView(self, iden):
        pass

    def newForkView(self):
        pass

    def eval(self, text):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        for mesg in self.storm(text):

            if mesg[0] != 'node':
                continue

            yield mesg[1].get('node')

    def storm(self, text, vars=None, user=None, view=None):
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
        if view is None:
            view = self.view

        parser = s_syntax.Parser(view, text)

        query = parser.query()
        for mesg in query.execute(view):
            yield mesg

        #except GeneratorExit as e:
            #query

        #except Exception as e:

            #yield s_common.geterr(e)

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
            snap.addNodes(nodedefs)

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

            # vers is expected in time format
            #for vers, func in modu.getModelRevs():
                #tick = s_time.parse(vers)

            #for name, modl in modu.getBaseModels():

                ## make sure the module's modl dict is loaded
                #if not self.isDataModl(name):
                    #toadd.append((name, modl))

                ## set the model version to 0 if it's -1
                #if self.getModlVers(name) == -1:
                    #isnew.add(name)
                    #self.setModlVers(name, 0)

            # group up versions by name so we can get max
            #for name, vers, func in modu.getModlRevs():
                #maxvers[name].append(vers)

                #revs.append((vers, name, func))

        #if toadd:
            #self.addDataModels(toadd)

        # if we didn't have it at all, forward wind...
        #for name, vals in maxvers.items():
            #if name in isnew:
                #self.setModlVers(name, max(vals))

        #revs.sort()

        #for vers, name, func in revs:
            #self.revModlVers(name, vers, func)

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
