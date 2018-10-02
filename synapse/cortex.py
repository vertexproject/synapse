import json
import asyncio
import logging
import pathlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.lmdb as s_lmdb
import synapse.lib.snap as s_snap
import synapse.lib.cache as s_cache
import synapse.lib.storm as s_storm
import synapse.lib.layer as s_layer
import synapse.lib.syntax as s_syntax
import synapse.lib.modules as s_modules

logger = logging.getLogger(__name__)

DEFAULT_LAYER_NAME = '000-default'

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

    async def snap(self):
        return await s_snap.Snap.anit(self.core, self.layers)

class CoreApi(s_cell.CellApi):
    '''
    The CoreApi is exposed over telepath.
    '''
    @s_cell.adminapi
    def getCoreMods(self):
        return self.cell.getCoreMods()

    @s_cell.adminapi
    def stat(self):
        return self.cell.stat()

    async def getNodesBy(self, full, valu, cmpr='='):
        '''
        Yield Node.pack() tuples which match the query.
        '''
        async for node in self.cell.getNodesBy(full, valu, cmpr=cmpr):
            yield node.pack()

    def allowed(self, *path):
        if self.user is None:
            return True

        return self.user.allowed(path)

    def _reqUserAllowed(self, *path):
        if not self.allowed(*path):
            perm = '.'.join(path)
            raise s_exc.AuthDeny(perm=perm, user=self.user.name)

    def getModelDict(self):
        '''
        Return a dictionary which describes the data model.

        Returns:
            (dict): A model description dictionary.
        '''
        return self.cell.model.getModelDict()

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

            node = await snap.getNodeByBuid(buid)
            if node is None:
                raise s_exc.NoSuchIden(iden=iden)

            await node.delTag(tag)
            return node.pack()

    async def setNodeProp(self, iden, name, valu):

        buid = s_common.uhex(iden)

        async with await self.cell.snap(user=self.user) as snap:

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

            snap.strict = False

            async for node in snap.addNodes(nodes):

                if node is not None:
                    node = node.pack()

                yield node

    async def addFeedData(self, name, items, seqn=None):

        self._reqUserAllowed('feed:data', *name.split('.'))

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
        async with await self.cell.snap(user=self.user) as snap:
            async for _ in snap.eval(text, opts=opts, user=self.user):
                i += 1
        return i

    async def eval(self, text, opts=None):
        '''
        Evalute a storm query and yield packed nodes.
        '''
        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE, loop=self.loop)

        async def runEval(chan):
            try:
                async with await self.cell.snap(user=self.user) as snap:
                    async for item in snap.iterStormPodes(text, opts=opts, user=self.user):
                        await chan.put(item)
            except Exception as e:
                await chan.put(e)

            finally:
                await chan.put(None)  # sentinel to indicate end of stream

        self.schedCoro(runEval(chan))

        while True:
            item = await chan.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    async def storm(self, text, opts=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            ((str,dict)): Storm messages.
        '''
        MSG_QUEUE_SIZE = 1000
        chan = asyncio.Queue(MSG_QUEUE_SIZE, loop=self.loop)

        async def runStorm(chan):
            tick = s_common.now()
            count = 0
            try:
                async with await self.cell.snap(user=self.user) as snap:
                    await chan.put(('init', {'tick': tick, 'text': text}))
                    snap.link(chan.put)
                    async for pode in snap.iterStormPodes(text, opts=opts, user=self.user):
                        await chan.put(('node', pode))
                        count += 1
            except Exception as e:
                if count:
                    logger.exception('Error during storm execution')
                    await chan.put(('err', s_common.err(e)))
                else:
                    await chan.put(e)
            finally:
                tock = s_common.now()
                took = tock - tick
                await chan.put(('fini', {'tock': tock, 'took': took, 'count': count}))

        self.schedCoro(runStorm(chan))

        while True:
            msg = await chan.get()
            if isinstance(msg, Exception):
                raise msg
            yield msg
            if msg[0] == 'fini':
                break

    @s_cell.adminapi
    async def splices(self, offs, size):
        '''
        Return the list of splices at the given offset.
        '''
        async for mesg in self.cell.layer.splices(offs, size):
            yield mesg

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

    async def __anit__(self, dirn):

        await s_cell.Cell.__anit__(self, dirn)

        self.layers = []
        self.modules = {}
        self.feedfuncs = {}

        self.stormcmds = {}
        self.stormrunts = {}

        self.addStormCmd(s_storm.HelpCmd)
        self.addStormCmd(s_storm.IdenCmd)
        self.addStormCmd(s_storm.SpinCmd)
        self.addStormCmd(s_storm.SudoCmd)
        self.addStormCmd(s_storm.UniqCmd)
        self.addStormCmd(s_storm.CountCmd)
        self.addStormCmd(s_storm.LimitCmd)
        self.addStormCmd(s_storm.DelNodeCmd)
        self.addStormCmd(s_storm.MoveTagCmd)
        self.addStormCmd(s_storm.ReIndexCmd)
        self.addStormCmd(s_storm.NoderefsCmd)

        self.splicers = {
            'node:add': self._onFeedNodeAdd,
            'node:del': self._onFeedNodeDel,
            'prop:set': self._onFeedPropSet,
            'prop:del': self._onFeedPropDel,
            'tag:add': self._onFeedTagAdd,
            'tag:del': self._onFeedTagDel,
        }

        self.newp = False
        self.setFeedFunc('syn.nodes', self._addSynNodes)
        self.setFeedFunc('syn.splice', self._addSynSplice)
        self.setFeedFunc('syn.ingest', self._addSynIngest)
        self.newp = True

        await self._initCoreLayers()

        async def fini():
            await asyncio.gather(*[layr.fini() for layr in self.layers], loop=self.loop)
        self.onfini(fini)

        # these may be used directly
        self.model = s_datamodel.Model()
        self.view = View(self, self.layers)

        self.ontagadds = collections.defaultdict(list)
        self.ontagdels = collections.defaultdict(list)

        await self.addCoreMods(s_modules.coremods)

        mods = self.conf.get('modules')

        await self.addCoreMods(mods)

        self._initCryoLoop()
        self._initPushLoop()
        self._initFeedLoops()

    def onTagAdd(self, name, func):
        '''
        Register a callback for tag addition.
        Args:
            name (str): The name of the tag.
            func (function): The callback func(node, tagname, tagval).

        '''
        #TODO allow name wild cards
        self.ontagadds[name].append(func)

    def onTagDel(self, name, func):
        '''
        Register a callback for tag deletion.
        Args:
            name (str): The name of the tag.
            func (function): The callback func(node, tagname, tagval).

        '''
        #TODO allow name wild cards
        self.ontagdels[name].append(func)

    async def runTagAdd(self, node, tag, valu):
        for func in self.ontagadds.get(tag, ()):
            try:
                await s_coro.ornot(func, node, tag, valu)
            except Exception as e:
                logger.exception('onTagAdd Error')

    async def runTagDel(self, node, tag, valu):
        for func in self.ontagdels.get(tag, ()):
            try:
                await s_coro.ornot(func, node, tag, valu)
            except Exception as e:
                logger.exception('onTagDel Error')

    async def _initCoreLayers(self):

        import synapse.cells as s_cells  # avoid import cycle

        layersdir = pathlib.Path(self.dirn, 'layers')
        layersdir.mkdir(exist_ok=True)

        if pathlib.Path(layersdir, 'default').is_dir():
            self._migrateOldDefaultLayer()

        # Layers are imported in reverse lexicographic order, where the earliest in the alphabet is the 'topmost'
        # write layer.
        for layerdir in sorted((d for d in layersdir.iterdir() if d.is_dir()), reverse=True):

            logger.info('loading external layer from %s', layerdir)

            if not pathlib.Path(layerdir, 'boot.yaml').exists():  # pragma: no cover
                logger.warning('Skipping layer directory %s due to missing boot.yaml', layerdir)
                continue

            layer = await s_cells.initFromDirn(layerdir)
            if not isinstance(layer, s_layer.Layer):
                raise s_exc.BadConfValu('layer dir %s must contain Layer cell', layerdir)

            self.layers.append(layer)

        if not self.layers:
            # Setup the fallback/default single LMDB layer
            self.layers.append(await self._makeDefaultLayer())

        self.layer = self.layers[-1]
        logger.debug('Cortex using the following layers: %s\n', (''.join(f'\n   {l.dirn}' for l in self.layers)))

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

        self.schedCoro(self._runPushLoop())

    async def _runPushLoop(self):

        url = self.conf.get('splice:sync')

        iden = self.getCellIden()

        logger.info('sync loop init: %s', url)

        while not self.isfini:

            try:

                url = self.conf.get('splice:sync')

                async with await s_telepath.openurl(url) as core:

                    # use our iden as the feed iden
                    offs = await core.getFeedOffs(iden)

                    while not self.isfini:

                        items = [x async for x in self.layer.splices(offs, 10000)]

                        if not items:
                            await self.waitfini(timeout=1)
                            continue

                        size = len(items)
                        indx = self.layer.splicelog.indx
                        perc = float(offs) / float(indx) * 100.0

                        logger.info('splice push: %d %d/%d (%.2f%%)', size, offs, indx, perc)

                        offs = await core.addFeedData('syn.splice', items, seqn=(iden, offs))
                        await self.fire('core:splice:sync:sent')

            except asyncio.CancelledError:
                break

            except Exception as e:  # pragma: no cover
                logger.exception('sync error')
                await self.waitfini(timeout=1)

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

            try:

                url = feed.get('cryotank')

                async with await s_telepath.openurl(url) as tank:

                    iden = await tank.getCellIden()

                    offs = await self.layer.getOffset(iden)

                    while not self.isfini:

                        items = [item async for item in await tank.slice(offs, fsize)]
                        if not items:
                            await self.waitfini(timeout=2)
                            continue

                        datas = [i[1] for i in items]

                        offs = await self.addFeedData(typename, datas, seqn=(iden, offs))
                        await self.fire('core:feed:loop')

            except asyncio.CancelledError:
                break

            except Exception as e:  # pragma: no cover
                logger.exception('feed error')
                await self.waitfini(timeout=1)

    async def _runCryoLoop(self):

        online = False
        tankurl = self.conf.get('splice:cryotank')

        layr = self.layers[-1]

        while not self.isfini:

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

            except Exception as e:  # pragma: no cover

                online = False
                logger.exception('splice cryotank offline')

                await self.waitfini(timeout=2)

    def setFeedFunc(self, name, func):
        '''
        Set a data ingest function.

        def func(snap, items):
            loaditems...
        '''
        if self.newp and name == 'syn.splice':
            raise Exception('omg')
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

    # def _addSynUndo(self, snap, items):
        # TODO apply splices in reverse

    async def _addSynIngest(self, snap, items):

        for item in items:
            try:
                pnodes = self._getSynIngestNodes(item)
                logger.info('Made [%s] nodes.', len(pnodes))
                async for n in snap.addNodes(pnodes):
                    yield n
            except Exception as e:
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
                    obj[1]['props'] = {'.seen': (seen, seen)}
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
                pnode[1]['props'].setdefault('.seen', (seen, seen))
            pnodes.append(pnode)

        # Make edges
        for srcdef, etyp, destndefs in item.get('edges', ()):
            for destndef in destndefs:
                ndef = [etyp, [srcdef, destndef]]
                ndefs.append(ndef)
                obj = [ndef, {}]
                if seen:
                    obj[1]['props'] = {'.seen': (seen, seen)}
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
                    obj[1]['props'] = {'.seen': (seen, seen)}
                if tags:
                    obj[1]['tags'] = tags.copy()
                pnodes.append(obj)

        # Make the source node and links
        source = item.get('source')
        if source:
            # Base object
            obj = [['source', source], {}]
            pnodes.append(obj)

            # Subsequent links
            for ndef in ndefs:
                obj = [['seen', (source, ndef)],
                       {'props': {'.seen': (seen, seen)}}]
                pnodes.append(obj)
        return pnodes

    # FIXME can remove this before 010 release, since 'old' is prelease 010.
    def _migrateOldDefaultLayer(self):  # pragma: no cover
        '''
        Migrate from 'old' 010 layers configuration structure
        '''
        layersdir = pathlib.Path(self.dirn, 'layers')
        new_path = pathlib.Path(layersdir, DEFAULT_LAYER_NAME)
        logger.info('Migrating old default layer to new location at %s', new_path)
        pathlib.Path(layersdir, 'default').rename(new_path)
        boot_yaml = pathlib.Path(new_path, 'boot.yaml')
        if not boot_yaml.exists():
            conf = {'cell:name': 'default', 'type': 'layer-lmdb'}
            s_common.yamlsave(conf, boot_yaml)

    async def _makeDefaultLayer(self):
        '''
        Since a user hasn't specified any layers, make one
        '''
        import synapse.cells as s_cells
        layerdir = s_common.gendir(self.dirn, 'layers', DEFAULT_LAYER_NAME)
        s_cells.deploy('layer-lmdb', layerdir)
        mapsize = self.conf.get('layer:lmdb:mapsize')
        if mapsize is not None:
            cell_yaml = pathlib.Path(layerdir, 'cell.yaml')
            conf = s_common.yamlload(cell_yaml) or {}
            conf['lmdb:mapsize'] = mapsize
            s_common.yamlsave(conf, cell_yaml)

        logger.info('Creating a new default storage layer at %s', layerdir)
        return await s_cells.initFromDirn(layerdir)

    def getCoreMod(self, name):
        return self.modules.get(name)

    def getCoreMods(self):
        ret = []
        for modname, mod in self.modules.items():
            ret.append((modname, mod.conf))
        return ret

    async def eval(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield Nodes only.
        '''
        async with await self.snap(user=user) as snap:
            async for node in snap.eval(text, opts=opts):
                yield node

    async def storm(self, text, opts=None, user=None):
        '''
        Evaluate a storm query and yield result messages.
        Yields:
            (Node, Path) tuples
        '''
        async with await self.snap(user=user) as snap:
            async for mesg in snap.storm(text, opts=opts):
                yield mesg

    @s_cache.memoize(size=10000)
    def getStormQuery(self, text):
        '''
        Parse storm query text and return a Query object.
        '''
        return s_syntax.Parser(self, text).query()

    def _logStormQuery(self, text, user):
        '''
        Log a storm query.
        '''
        if self.conf.get('storm:log'):
            lvl = self.conf.get('storm:log:level')
            logger.log(lvl, 'Executing storm query [%s] as [%s]', text, user)

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
        return await self.layer.getOffset(iden)

    async def setFeedOffs(self, iden, offs):
        if offs < 0:
            raise s_exc.BadConfValu(mesg='Offset must be greater than or equal to zero.', offs=offs,
                                    iden=iden)
        oldoffs = await self.getFeedOffs(iden)
        logger.info('Setting Feed offset for [%s] from [%s] to [%s]',
                    iden, oldoffs, offs)
        return await self.layer.setOffset(iden, offs)

    async def snap(self, user=None):
        '''
        Return a transaction object for the default view.

        Args:
            write (bool): Set to True for a write transaction.

        Returns:
            (synapse.lib.snap.Snap)

        NOTE: This must be used in a with block.
        '''
        snap = await self.view.snap()
        if user is not None:
            snap.setUser(user)
        return snap

    async def addCoreMods(self, mods):
        '''
        Add a list of (name,conf) module tuples to the cortex.
        '''
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
        for modu in added:
            await modu.initCoreModule()

    async def loadCoreModule(self, ctor, conf=None):
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

        await modu.initCoreModule()

    def _loadCoreModule(self, ctor):

        try:

            # print('LOAD: %r' % (ctor,))
            modu = s_dyndeps.tryDynFunc(ctor, self)

            self.modules[ctor] = modu

            # print('WOOT: %r' % (ctor,))
            return modu

        except Exception as e:
            logger.exception('mod load fail: %s' % (ctor,))
            return None

    async def stat(self):
        stats = {
            'iden': self.iden,
            'layer': await self.layer.stat()
        }
        return stats
