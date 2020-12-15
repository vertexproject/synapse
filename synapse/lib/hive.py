import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack

import synapse.lib.lmdbslab as s_slab

logger = logging.getLogger(__name__)

class Node(s_base.Base):
    '''
    A single node within the Hive tree.
    '''
    async def __anit__(self, hive, full, valu):

        await s_base.Base.__anit__(self)

        self.kids = {}
        self.valu = valu
        self.hive = hive
        self.full = full

        self.onfini(self._onNodeFini)

    async def _onNodeFini(self):
        for node in list(self.kids.values()):
            await node.fini()

    def name(self):
        return self.full[-1]

    def parent(self):
        return self.hive.nodes.get(self.full[:-1])

    def get(self, name):
        return self.kids.get(name)

    def dir(self):
        retn = []
        for name, node in self.kids.items():
            retn.append((name, node.valu, len(node.kids)))
        return retn

    async def set(self, valu):
        return await self.hive.set(self.full, valu)

    async def add(self, valu):
        ''' Increments existing node valu '''
        return await self.hive.add(self.full, valu)

    async def open(self, path):
        '''
        Open a child Node of the this Node.

        Args:
            path (tuple): A child path of the current node.

        Returns:
            Node: A Node at the child path.
        '''
        full = self.full + path
        return await self.hive.open(full)

    async def pop(self, path=()):
        full = self.full + path
        return await self.hive.pop(full)

    async def dict(self, nexs=False):
        '''
        Get a HiveDict for this Node.

        Returns:
            HiveDict: A HiveDict for this Node.
        '''
        return await HiveDict.anit(self.hive, self, nexs=nexs)

    def __iter__(self):
        for name, node in self.kids.items():
            yield name, node

class Hive(s_nexus.Pusher, s_telepath.Aware):
    '''
    An optionally persistent atomically accessed tree which implements
    primitives for use in making distributed/clustered services.
    '''
    async def __anit__(self, conf=None, nexsroot=None):

        await s_nexus.Pusher.__anit__(self, 'hive', nexsroot=nexsroot)

        s_telepath.Aware.__init__(self)

        if conf is None:
            conf = {}

        self.conf = conf
        self.nodes = {} # full=Node()

        self.conf.setdefault('auth:en', False)
        self.conf.setdefault('auth:path', 'hive/auth')

        self.root = await Node.anit(self, (), None)
        self.nodes[()] = self.root

        await self._storLoadHive()

        self.onfini(self._onHiveFini)

        self.auth = None

    async def saveHiveTree(self, path=()):
        tree = {}
        root = await self.open(path)
        self._saveHiveNode(root, tree)
        return tree

    def _saveHiveNode(self, node, tree):

        tree['value'] = node.valu

        kids = list(node.kids.items())
        if not kids:
            return

        kidtrees = {}
        for kidname, kidnode in kids:
            kidtree = kidtrees[kidname] = {}
            self._saveHiveNode(kidnode, kidtree)

        tree['kids'] = kidtrees

    async def loadHiveTree(self, tree, path=(), trim=False):
        root = await self.open(path)
        await self._loadHiveNode(root, tree, trim=trim)

    async def _loadHiveNode(self, node, tree, trim=False):

        valu = tree.get('value', s_common.novalu)
        if node is not self.root and valu is not s_common.novalu:
            await node.set(valu)

        kidnames = set()

        kids = tree.get('kids')
        if kids is not None:
            for kidname, kidtree in kids.items():
                kidnames.add(kidname)
                kidnode = await node.open((kidname,))
                await self._loadHiveNode(kidnode, kidtree, trim=trim)

        if trim:
            culls = [n for n in node.kids.keys() if n not in kidnames]
            for cullname in culls:
                await node.pop((cullname,))

    async def getHiveAuth(self):
        '''
        Retrieve a HiveAuth for hive standalone or non-cell uses.

        Note:
            This is for the hive's own auth, or for non-cell auth.  It isn't the same auth as for a cell
        '''
        import synapse.lib.hiveauth as s_hiveauth
        if self.auth is None:

            path = tuple(self.conf.get('auth:path').split('/'))

            node = await self.open(path)
            self.auth = await s_hiveauth.Auth.anit(node, nexsroot=self.nexsroot)
            self.onfini(self.auth.fini)

        return self.auth

    async def _onHiveFini(self):
        await self.root.fini()

    async def get(self, full, defv=None):
        '''
        Get the value of a node at a given path.

        Args:
            full (tuple): A full path tuple.

        Returns:
            Arbitrary node value.
        '''

        node = self.nodes.get(full)
        if node is None:
            return defv

        return node.valu

    async def exists(self, full):
        '''
        Returns whether the Hive path has already been created.
        '''

        return full in self.nodes

    def dir(self, full):
        '''
        List subnodes of the given Hive path.

        Args:
            full (tuple): A full path tuple.

        Notes:
            This returns None if there is not a node at the path.

        Returns:
            list: A list of tuples. Each tuple contains the name, node value, and the number of children nodes.
        '''
        node = self.nodes.get(full)
        if node is None:
            return None

        return node.dir()

    async def rename(self, oldpath, newpath):
        '''
        Moves a node at oldpath and all its descendant nodes to newpath.  newpath must not exist
        '''
        if await self.exists(newpath):
            raise s_exc.BadHivePath(mesg='path already exists')

        if len(newpath) >= len(oldpath) and newpath[:len(oldpath)] == oldpath:
            raise s_exc.BadHivePath(mesg='cannot move path into itself')

        if not await self.exists(oldpath):
            raise s_exc.BadHivePath(mesg=f'path {"/".join(oldpath)} does not exist')

        await self._rename(oldpath, newpath)

    async def _rename(self, oldpath, newpath):
        '''
        Same as rename, but no argument checking
        '''
        root = await self.open(oldpath)

        for kidname in list(root.kids):
            await self._rename(oldpath + (kidname,), newpath + (kidname,))

        await self.set(newpath, root.valu)

        await root.pop(())

    async def dict(self, full, nexs=False):
        '''
        Open a HiveDict at the given full path.

        Args:
            full (tuple): A full path tuple.

        Returns:
            HiveDict: A HiveDict for the full path.
        '''
        node = await self.open(full)
        return await HiveDict.anit(self, node, nexs=nexs)

    async def _initNodePath(self, base, path, valu):

        node = await Node.anit(self, path, valu)

        # all node events dist up the tree
        node.link(base.dist)

        self.nodes[path] = node
        base.kids[path[-1]] = node

        return node

    async def _loadNodeValu(self, full, valu):
        '''
        Load a node from storage into the tree.
        ( used by initialization routines to build the tree)
        '''
        node = self.root
        for path in iterpath(full):

            name = path[-1]

            step = node.kids.get(name)
            if step is None:
                step = await self._initNodePath(node, path, None)

            node = step

        node.valu = valu
        return node

    async def open(self, full):
        '''
        Open and return a hive Node().

        Args:
            full (tuple): A full path tuple.

        Returns:
            Node: A Hive node.
        '''
        return await self._getHiveNode(full)

    async def _getHiveNode(self, full):

        node = self.nodes.get(full)
        if node is not None:
            return node

        node = self.root

        for path in iterpath(full):

            name = path[-1]

            step = node.kids.get(name)
            if step is None:
                step = await self._initNodePath(node, path, None)

            node = step

        return node

    async def set(self, full, valu, nexs=False):
        '''
        A set operation at the hive level (full path).
        '''
        valu = s_common.tuplify(valu)
        if nexs:
            return await self._push('hive:set', full, valu)

        return await self._set(full, valu)

    @s_nexus.Pusher.onPush('hive:set')
    async def _set(self, full, valu):
        node = await self._getHiveNode(full)

        oldv = node.valu

        node.valu = await self.storNodeValu(full, valu)

        await node.fire('hive:set', path=full, valu=valu, oldv=oldv)

        return oldv

    async def add(self, full, valu):
        '''
        Atomically increments a node's value.
        '''
        node = await self.open(full)

        oldv = node.valu
        newv = oldv + valu

        node.valu = await self.storNodeValu(full, node.valu + valu)

        await node.fire('hive:set', path=full, valu=valu, oldv=oldv)

        return newv

    async def pop(self, full, nexs=False):
        '''
        Remove and return the value for the given node.
        '''
        if nexs:
            return await self._push('hive:pop', full)

        return await self._pop(full)

    @s_nexus.Pusher.onPush('hive:pop')
    async def _pop(self, full):

        node = self.nodes.get(full)
        if node is None:
            return

        valu = await self._popHiveNode(node)

        return valu

    async def _popHiveNode(self, node):
        for kidn in list(node.kids.values()):
            await self._popHiveNode(kidn)

        name = node.name()

        self.nodes.pop(node.full)
        node.parent().kids.pop(name, None)

        await self.storNodeDele(node.full)

        await node.fire('hive:pop', path=node.full, valu=node.valu)

        await node.fini()

        return node.valu

    async def getTeleApi(self, link, mesg, path):

        auth = await self.getHiveAuth()

        if not self.conf.get('auth:en'):
            user = await auth.getUserByName('root')
            return await HiveApi.anit(self, user)

        name, info = mesg[1].get('auth')

        user = await auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name)

        # passwd None always fails...
        passwd = info.get('passwd')
        if not await user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return await HiveApi.anit(self, user)

    async def _storLoadHive(self):
        pass

    async def storNodeValu(self, full, valu):
        return valu

    async def storNodeDele(self, path):
        pass

class SlabHive(Hive):

    async def __anit__(self, slab, db=None, conf=None, nexsroot=None):
        self.db = db
        self.slab = slab
        await Hive.__anit__(self, conf=conf, nexsroot=nexsroot)
        self.slab.onfini(self.fini)

    async def _storLoadHive(self):

        for lkey, lval in self.slab.scanByFull(db=self.db):

            path = tuple(lkey.decode('utf8').split('\x00'))
            valu = s_msgpack.un(lval)

            await self._loadNodeValu(path, valu)

    async def storNodeValu(self, full, valu):
        lval = s_msgpack.en(valu)
        lkey = '\x00'.join(full).encode('utf8')
        self.slab.put(lkey, lval, db=self.db)
        return valu

    async def storNodeDele(self, full):
        lkey = '\x00'.join(full).encode('utf8')
        self.slab.pop(lkey, db=self.db)

class HiveApi(s_base.Base):

    async def __anit__(self, hive, user):

        await s_base.Base.__anit__(self)

        self.hive = hive
        self.user = user

        self.msgq = asyncio.Queue(maxsize=10000)

        self.onfini(self._onHapiFini)

    async def loadHiveTree(self, tree, path=(), trim=False):
        return await self.hive.loadHiveTree(tree, path=path, trim=trim)

    async def saveHiveTree(self, path=()):
        return await self.hive.saveHiveTree(path=path)

    async def treeAndSync(self, path, iden):

        node = await self.hive.open(path)

        # register handlers...
        node.on('hive:add', self._onHiveEdit, base=self)
        node.on('hive:set', self._onHiveEdit, base=self)
        node.on('hive:pop', self._onHiveEdit, base=self)

        # serialize the subtree into a message and return
        # via the mesg queue so there is no get/update race
        root = (node.valu, {})

        todo = collections.deque([(node, root)])

        # breadth first generator
        while todo:

            node, pode = todo.popleft()

            for name, kidn in node.kids.items():

                kidp = (kidn.valu, {})
                pode[1][name] = kidp

                todo.append((kidn, kidp))

        await self.msgq.put(('hive:tree', {'path': path, 'tree': root}))
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return

    async def setAndSync(self, path, valu, iden, nexs=False):
        valu = await self.hive.set(path, valu, nexs=nexs)
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return valu

    async def addAndSync(self, path, valu, iden):
        valu = await self.hive.add(path, valu)
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return valu

    async def popAndSync(self, path, iden, nexs=False):
        valu = await self.hive.pop(path, nexs=nexs)
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return valu

    async def _onHapiFini(self):
        await self.msgq.put(None)

    async def _onHiveEdit(self, mesg):
        self.msgq.put_nowait(mesg)

    async def get(self, full):
        return await self.hive.get(full)

    async def edits(self):

        while not self.isfini:

            item = await self.msgq.get()
            if item is None:
                return

            yield item

class TeleHive(Hive):
    '''
    A Hive that acts as a consistent read cache for a telepath proxy Hive
    '''

    async def __anit__(self, proxy):

        self.proxy = proxy

        await Hive.__anit__(self)

        self.lock = asyncio.Lock()

        self.syncevents = {} # iden: asyncio.Event()

        # fire a task to sync the sections of the tree we open
        self.schedCoro(self._runHiveLoop())

        self.mesgbus = await s_base.Base.anit()
        self.mesgbus.on('hive:set', self._onHiveSet)
        self.mesgbus.on('hive:pop', self._onHivePop)
        self.mesgbus.on('hive:tree', self._onHiveTree)
        self.mesgbus.on('hive:sync', self._onHiveSync)

        self.onfini(self.mesgbus.fini)

        self.onfini(proxy.fini)

    async def _onHiveSync(self, mesg):

        iden = mesg[1].get('iden')
        evnt = self.syncevents.pop(iden, None)
        if evnt is None:
            return

        evnt.set()

    def _getSyncIden(self):
        iden = s_common.guid()
        evnt = asyncio.Event()
        self.syncevents[iden] = evnt
        return iden, evnt

    async def _runHiveLoop(self):
        while not self.isfini:
            async for mesg in self.proxy.edits():
                await self.mesgbus.dist(mesg)

    async def _onHiveSet(self, mesg):
        path = mesg[1].get('path')
        valu = mesg[1].get('valu')
        await Hive.set(self, path, valu)

    async def _onHivePop(self, mesg):
        path = mesg[1].get('path')
        await Hive.pop(self, path)

    async def _onHiveTree(self, mesg):

        # get an entire tree update at once
        path = mesg[1].get('path')
        tree = mesg[1].get('tree')

        node = await Hive.open(self, path)

        todo = collections.deque([(node, path, tree)])

        while todo:

            node, path, (valu, kids) = todo.popleft()

            # do *not* go through the set() API
            node.valu = valu
            for name, kidt in kids.items():

                kidp = path + (name,)
                kidn = await Hive.open(self, kidp)

                todo.append((kidn, kidp, kidt))

    async def set(self, path, valu, nexs=False):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.setAndSync(path, valu, iden, nexs=nexs)
        await evnt.wait()
        return valu

    async def add(self, path, valu):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.addAndSync(path, valu, iden)
        await evnt.wait()
        return valu

    async def pop(self, path, nexs=False):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.popAndSync(path, iden, nexs=nexs)
        await evnt.wait()
        return valu

    async def get(self, path):
        return await self.proxy.get(path)

    async def open(self, path):

        # try once pre-lock for speed
        node = self.nodes.get(path)
        if node is not None:
            return node

        async with self.lock:

            # try again with lock to avoid race
            node = self.nodes.get(path)
            if node is not None:
                return node

            iden, evnt = self._getSyncIden()

            await self.proxy.treeAndSync(path, iden)

            await evnt.wait()

            return self.nodes.get(path)

class HiveDict(s_base.Base):
    '''
    '''
    async def __anit__(self, hive, node, nexs=False):

        await s_base.Base.__anit__(self)

        self.defs = {}

        self.nexs = nexs
        self.hive = hive
        self.node = node

        self.node.onfini(self)

    def get(self, name, default=None):

        node = self.node.get(name)
        if node is None:
            return self.defs.get(name, default)

        return node.valu

    async def set(self, name, valu):
        full = self.node.full + (name,)
        return await self.hive.set(full, valu, nexs=self.nexs)

    def setdefault(self, name, valu):
        self.defs[name] = valu

    def items(self):
        for key, node in iter(self.node):
            yield key, node.valu

    def values(self):
        for _, node in iter(self.node):
            yield node.valu

    def pack(self):
        return {name: node.valu for (name, node) in iter(self.node)}

    async def pop(self, name, default=None):
        node = self.node.get(name)
        if node is None:
            return self.defs.get(name, default)

        retn = node.valu

        await node.hive.pop(node.full, nexs=self.nexs)

        return retn

def iterpath(path):
    for i in range(len(path)):
        yield path[:i + 1]

async def openurl(url, **opts):
    prox = await s_telepath.openurl(url, **opts)
    return await TeleHive.anit(prox)

async def opendir(dirn, conf=None):
    slab = await s_slab.Slab.anit(dirn, map_size=s_const.gibibyte)
    db = slab.initdb('hive')
    return await SlabHive(slab, db=db, conf=conf)
