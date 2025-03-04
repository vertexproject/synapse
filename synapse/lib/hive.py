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

class Hive(s_nexus.Pusher):
    '''
    An optionally persistent atomically accessed tree which implements
    primitives for use in making distributed/clustered services.
    '''
    async def __anit__(self, conf=None, nexsroot=None, cell=None):

        await s_nexus.Pusher.__anit__(self, 'hive', nexsroot=nexsroot)

        if conf is None:
            conf = {}

        self.cell = cell
        self.conf = conf
        self.nodes = {}  # full=Node()

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
        if self.cell is not None:
            if full[0] == 'auth':
                if len(full) == 5:
                    _, _, iden, dtyp, name = full
                    if dtyp == 'vars':
                        await self.cell.auth._hndlsetUserVarValu(iden, name, valu)
                    elif dtyp == 'profile':
                        await self.cell.auth._hndlsetUserProfileValu(iden, name, valu)

            elif full[0] == 'cellvers':
                await self.cell.setCellVers(full[-1], valu, nexs=False)

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

        if self.cell is not None and full[0] == 'auth':
            if len(full) == 5:
                _, _, iden, dtyp, name = full
                if dtyp == 'vars':
                    await self.cell.auth._hndlpopUserVarValu(iden, name)
                elif dtyp == 'profile':
                    await self.cell.auth._hndlpopUserProfileValu(iden, name)

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

    async def _storLoadHive(self):
        pass

    async def storNodeValu(self, full, valu):
        return valu

    async def storNodeDele(self, path):
        pass

class SlabHive(Hive):

    async def __anit__(self, slab, db=None, conf=None, nexsroot=None, cell=None):
        self.db = db
        self.slab = slab
        await Hive.__anit__(self, conf=conf, nexsroot=nexsroot, cell=cell)
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

    async def set(self, name, valu, nexs=None):

        if nexs is None:
            nexs = self.nexs

        full = self.node.full + (name,)
        return await self.hive.set(full, valu, nexs=nexs)

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

async def opendir(dirn, conf=None):
    slab = await s_slab.Slab.anit(dirn, map_size=s_const.gibibyte)
    db = slab.initdb('hive')
    return await SlabHive(slab, db=db, conf=conf)
