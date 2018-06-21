import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.snap as s_snap
import synapse.lib.const as s_const
import synapse.lib.storm as s_storm
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

        "foo": <time>,
        "foo.bar": <time>,
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

        # our "top" layer is "us"
        self.layer = self.layers[-1]

    def snap(self):
        return s_snap.Snap(self.core, self.layers)

    def getStormQuery(self, text):
        parser = s_syntax.Parser(self, text)
        return parser.query()

class CoreApi(s_cell.CellApi):
    '''
    The CoreApi is exposed over telepath.
    '''
    @s_cell.adminapi
    def getCoreMods(self):
        return self.cell.getCoreMods()

    def getNodesBy(self, full, valu, cmpr='='):
        '''
        Yield Node.pack() tuples which match the query.
        '''
        for node in self.cell.getNodesBy(full, valu, cmpr=cmpr):
            yield node.pack()

    async def fini(self):
        pass

    def addNodes(self, nodes):

        with self.cell.snap() as snap:

            snap.strict = False
            snap.setUser(self.user)

            for node in snap.addNodes(nodes):

                if node is not None:
                    node = node.pack()

                yield node

    def addFeedData(self, name, items, seqn=None):

        with self.cell.snap() as snap:
            snap.strict = False
            snap.setUser(self.user)
            return snap.addFeedData(name, items, seqn=seqn)

    def getFeedOffs(self, iden):
        return self.cell.layer.getOffset(iden)

    def count(self, text, opts=None):
        '''
        Count the number of nodes which result from a storm query.

        Args:
            text (str): Storm query text.
            opts (dict): Storm query options.

        Returns:
            (int): The number of nodes resulting from the query.
        '''
        query = self._getStormQuery(text, opts=opts)
        return sum((1 for n in query.evaluate()))

    def eval(self, text, opts=None):
        '''
        Evalute a storm query and yield packed nodes.
        '''
        query = self._getStormQuery(text, opts=opts)
        dorepr = query.opts.get('repr')

        try:

            for node in query.evaluate():
                yield node.pack(dorepr=dorepr)

        except Exception as e:
            logging.exception('exception during storm eval')
            query.cancel()
            raise

    def _getStormQuery(self, text, opts=None):

        query = self.cell.view.getStormQuery(text)
        query.setUser(self.user)

        if opts is not None:
            query.opts.update(opts)

        if self.cell.conf.get('storm:log'):
            lvl = self.cell.conf.get('storm:log:level')
            logger.log(lvl, 'Executing storm query [%s] as [%s]', text, self.user)

        return query

    def storm(self, text, opts=None):
        '''
        Execute a storm query and yield messages.
        '''
        query = self._getStormQuery(text, opts=opts)

        try:

            for mesg in query.execute():
                yield mesg

        except Exception as e:
            logger.exception('exception during storm')
            query.cancel()

    @s_cell.adminapi
    def splices(self, offs, size):
        '''
        Return the list of splices at the given offset.
        '''
        yield from self.cell.layer.splices(offs, size)

class Cortex(s_cell.Cell):
    '''
    A Cortex implements the synapse hypergraph.

    The bulk of the Cortex API lives on the Snap() object which can
    be obtained by calling Cortex.snap() in a with block.  This allows
    callers to manage transaction boundaries explicitly and dramatically
    increases performance.
    '''
    confdefs = (

        ('layer:lmdb:mapsize', {
            'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE,
            'doc': 'The default size for a new LMDB layer map.'
        }),

        ('modules', {
            'type': 'list', 'defval': (),
            'doc': 'A list of module classes to load.'
        }),

        ('layers', {
            'type': 'list', 'defval': (),
            'doc': 'A list of layer paths to load.'
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

        # ('storm:save', {
        #     'type': 'bool', 'defval': False,
        #     'doc': 'Archive storm queries for audit trail.'
        # }),

    )

    cellapi = CoreApi

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        self.views = {}
        self.layers = []
        self.modules = {}
        self.feedfuncs = {}

        self.stormcmds = {}

        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.SudoCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)

        self.splicers = {
            'node:add': self._onFeedNodeAdd,
            'node:del': self._onFeedNodeDel,
            'prop:set': self._onFeedPropSet,
            'prop:del': self._onFeedPropDel,
            'tag:add': self._onFeedTagAdd,
            'tag:del': self._onFeedTagDel,
        }

        self.setFeedFunc('syn.splice', self._addSynSplice)

        # load any configured external layers
        for path in self.conf.get('layers'):
            logger.info('loading external layer: %r', path)
            self.layers.append(s_layer.opendir(path))

        # initialize any cortex directory structures
        self._initCoreDir()

        # these may be used directly
        self.model = s_datamodel.Model()
        self.view = View(self, self.layers)

        self.addCoreMods(s_modules.coremods)

        mods = self.conf.get('modules')
        self.addCoreMods(mods)

        self._initCryoLoop()
        self._initPushLoop()
        self._initFeedLoops()

    def addStormCmd(self, ctor):
        '''
        Add a synapse.lib.storm.Cmd class to the cortex.
        '''
        self.stormcmds[ctor.name] = ctor

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    def getStormCmds(self):
        return list(self.stormcmds.items())

    def _initPushLoop(self):

        if self.conf.get('splice:sync') is None:
            return

        thrd = self._runPushLoop()
        def fini():
            return thrd.join(timeout=8)

        self.onfini(fini)

    @s_common.firethread
    def _runPushLoop(self):

        url = self.conf.get('splice:sync')

        iden = self.getCellIden()

        logger.info('sync loop init: %s', url)

        while not self.isfini:

            try:

                url = self.conf.get('splice:sync')

                with s_telepath.openurl(url) as core:

                    # use our iden as the feed iden
                    offs = core.getFeedOffs(iden)

                    while not self.isfini:

                        items = list(self.layer.splices(offs, 10000))

                        if not items:
                            self.cellfini.wait(timeout=1)
                            continue

                        size = len(items)
                        indx = self.layer.splicelog.indx
                        perc = float(offs) / float(indx) * 100.0

                        logger.info('splice push: %d %d/%d (%.2f%%)', size, offs, indx, perc)

                        offs = core.addFeedData('syn.splice', items, seqn=(iden, offs))
                        self.fire('core:splice:sync:sent')

            except Exception as e:  # pragma: no cover
                logger.exception('sync error')
                self.cellfini.wait(timeout=1)

    def _initCryoLoop(self):

        tankurl = self.conf.get('splice:cryotank')
        if tankurl is None:
            return

        self.cryothread = self._runCryoLoop()

        def fini():
            self.cryothread.join(timeout=8)

        self.onfini(fini)

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

            # do some validation before we fire threads...
            typename = feed.get('type')
            if self.getFeedFunc(typename) is None:
                raise s_exc.NoSuchType(name=typename)

            thrd = self._runFeedLoop(feed)

            def fini():
                thrd.join(timeout=2)

            self.onfini(fini)

    @s_common.firethread
    def _runFeedLoop(self, feed):

        url = feed.get('cryotank')
        typename = feed.get('type')
        fsize = feed.get('size', 1000)

        logger.info('feed loop init: %s @ %s', typename, url)

        while not self.isfini:

            try:

                url = feed.get('cryotank')

                with s_telepath.openurl(url) as tank:

                    iden = tank.getCellIden()

                    offs = self.layer.getOffset(iden)

                    while not self.isfini:

                        items = list(tank.slice(offs, fsize))
                        if not items:
                            self.cellfini.wait(timeout=2)
                            continue

                        datas = [i[1] for i in items]

                        offs = self.addFeedData(typename, datas, seqn=(iden, offs))
                        self.fire('core:feed:loop')

            except Exception as e:  # pragma: no cover
                logger.exception('feed error')
                self.cellfini.wait(timeout=1)

    @s_common.firethread
    def _runCryoLoop(self):

        online = False
        tankurl = self.conf.get('splice:cryotank')

        layr = self.layers[-1]

        while not self.isfini:

            try:

                with s_telepath.openurl(tankurl) as tank:

                    if not online:
                        online = True
                        logger.info('splice cryotank: online')

                    offs = tank.offset(self.iden)

                    while not self.isfini:

                        items = list(layr.splices(offs, 10000))

                        if not len(items):
                            layr.spliced.clear()
                            layr.spliced.wait(timeout=1)
                            continue

                        logger.info('tanking splices: {:,}'.format(len(items)))

                        offs = tank.puts(items, seqn=(self.iden, offs))
                        self.fire('core:splice:cryotank:sent')

            except Exception as e:  # pragma: no cover

                online = False
                logger.exception('splice cryotank offline')

                self.cellfini.wait(timeout=2)

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

    def _addSynSplice(self, snap, items):

        for item in items:

            func = self.splicers.get(item[0])

            if func is None:
                snap.warn(f'no such splice: {item!r}')
                continue

            try:
                func(snap, item)
            except Exception as e:
                logger.exception('splice error')
                snap.warn(f'splice error: {e}')

    def _onFeedNodeAdd(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        if ndef is None:
            snap.warn(f'Invalid Splice: {mesg!r}')
            return

        snap.addNode(*ndef)

    def _onFeedNodeDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        node = snap.getNodeByNdef(ndef)
        if node is None:
            return

        node.delete()

    def _onFeedPropSet(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        name = mesg[1].get('prop')
        valu = mesg[1].get('valu')

        node = snap.getNodeByNdef(ndef)
        if node is None:
            return

        node.set(name, valu)

    def _onFeedPropDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        name = mesg[1].get('prop')

        node = snap.getNodeByNdef(ndef)
        if node is None:
            return

        node.pop(name)

    def _onFeedTagAdd(self, snap, mesg):

        ndef = mesg[1].get('ndef')

        tag = mesg[1].get('tag')
        valu = mesg[1].get('valu')

        node = snap.getNodeByNdef(ndef)
        if node is None:
            return

        node.addTag(tag, valu=valu)

    def _onFeedTagDel(self, snap, mesg):

        ndef = mesg[1].get('ndef')
        tag = mesg[1].get('tag')

        node = snap.getNodeByNdef(ndef)
        if node is None:
            return

        node.delTag(tag)

    #def _addSynUndo(self, snap, items):
        # TODO apply splices in reverse

    def _initCoreDir(self):

        # each cortex has a default write layer...
        path = s_common.gendir(self.dirn, 'layers', 'default')

        self.layer = self.openLayerName('default')
        self.layers.append(self.layer)

    def openLayerName(self, name):
        dirn = s_common.gendir(self.dirn, 'layers', name)
        return s_layer.opendir(dirn)

    def getCoreMod(self, name):
        return self.modules.get(name)

    def getCoreMods(self):
        ret = []
        for modname, mod in self.modules.items():
            ret.append((modname, mod.conf))
        return ret

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

        if opts is not None:
            query.opts.update(opts)

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

        if opts is not None:
            query.opts.update(opts)

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
            for node in snap.getNodesBy(full, valu, cmpr=cmpr):
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
        with self.snap() as snap:
            snap.strict = False
            yield from snap.addNodes(nodedefs)

    def addFeedData(self, name, items, seqn=None):
        '''
        Add data using a feed/parser function.

        Args:
            name (str): The name of the feed record format.
            items (list): A list of items to ingest.
            seqn ((str,int)): An (iden, offs) tuple for this feed chunk.

        Returns:
            (int): The next expected offset (or None) if seqn is None.
        '''
        with self.snap() as snap:
            snap.strict = False
            return snap.addFeedData(name, items, seqn=seqn)

    def getFeedOffs(self, iden):
        return self.layer.getOffset(iden)

    def snap(self):
        '''
        Return a transaction object for the default view.

        Args:
            write (bool): Set to True for a write transaction.

        Returns:
            (synapse.lib.snap.Snap)

        NOTE: This must be used in a with block.
        '''
        return self.view.snap()

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
