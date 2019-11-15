import asyncio
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
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

    async def dict(self):
        '''
        Get a HiveDict for this Node.

        Returns:
            HiveDict: A HiveDict for this Node.
        '''
        return await HiveDict.anit(self.hive, self)

    def __iter__(self):
        for name, node in self.kids.items():
            yield name, node

class Hive(s_base.Base, s_telepath.Aware):
    '''
    An optionally persistent atomically accessed tree which implements
    primitives for use in making distributed/clustered services.
    '''
    async def __anit__(self, conf=None):

        await s_base.Base.__anit__(self)
        s_telepath.Aware.__init__(self)

        if conf is None:
            conf = {}

        self.conf = conf
        self.nodes = {} # full=Node()

        self.conf.setdefault('auth:en', False)
        self.conf.setdefault('auth:path', 'hive/auth')

        # event dist by path
        self.editsbypath = collections.defaultdict(set)

        self.root = await Node.anit(self, (), None)
        self.nodes[()] = self.root

        self.root.link(self._onNodeEdit)

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
        if self.auth is None:

            path = tuple(self.conf.get('auth:path').split('/'))

            node = await self.open(path)
            self.auth = await HiveAuth.anit(node)
            self.onfini(self.auth.fini)

        return self.auth

    async def _onNodeEdit(self, mesg):

        path = mesg[1].get('path')
        for meth in self.editsbypath.get(path, ()):

            try:
                await s_coro.ornot(meth, mesg)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception('hive edit error with mesg %s', mesg)

    async def _onHiveFini(self):
        await self.root.fini()

    def onedit(self, path, func, base=None):

        if base is not None:
            async def fini():
                self.editsbypath[path].discard(func)
            base.onfini(fini)

        self.editsbypath[path].add(func)

    async def get(self, full):
        '''
        Get the value of a node at a given path.

        Args:
            full (tuple): A full path tuple.

        Returns:
            Arbitrary node value.
        '''

        node = self.nodes.get(full)
        if node is None:
            return None

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

    async def dict(self, full):
        '''
        Open a HiveDict at the given full path.

        Args:
            full (tuple): A full path tuple.

        Returns:
            HiveDict: A HiveDict for the full path.
        '''
        node = await self.open(full)
        return await HiveDict.anit(self, node)

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

    async def set(self, full, valu):
        '''
        A set operation at the hive level (full path).
        '''
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

    async def pop(self, full):
        '''
        Remove and return the value for the given node.
        '''
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
            user = auth.getUserByName('root')
            return await HiveApi.anit(self, user)

        name, info = mesg[1].get('auth')

        user = auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name)

        # passwd None always fails...
        passwd = info.get('passwd')
        if not user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return await HiveApi.anit(self, user)

    async def _storLoadHive(self):
        pass

    async def storNodeValu(self, full, valu):
        return valu

    async def storNodeDele(self, path):
        pass

class SlabHive(Hive):

    async def __anit__(self, slab, db=None, conf=None):
        self.db = db
        self.slab = slab
        await Hive.__anit__(self, conf=conf)
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

    async def setAndSync(self, path, valu, iden):
        valu = await self.hive.set(path, valu)
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return valu

    async def addAndSync(self, path, valu, iden):
        valu = await self.hive.add(path, valu)
        await self.msgq.put(('hive:sync', {'iden': iden}))
        return valu

    async def popAndSync(self, path, iden):
        valu = await self.hive.pop(path)
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

    async def set(self, path, valu):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.setAndSync(path, valu, iden)
        await evnt.wait()
        return valu

    async def add(self, path, valu):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.addAndSync(path, valu, iden)
        await evnt.wait()
        return valu

    async def pop(self, path):
        iden, evnt = self._getSyncIden()
        valu = await self.proxy.popAndSync(path, iden)
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

    # TODO: async def append(self, path, valu):

class HiveDict(s_base.Base):
    '''
    '''
    async def __anit__(self, hive, node):

        await s_base.Base.__anit__(self)

        self.defs = {}

        self.hive = hive
        self.node = node

        self.node.onfini(self)

    def get(self, name, onedit=None, default=None):

        # use hive.onedit() here to register for
        # paths which potentially dont exist yet
        if onedit is not None:
            full = self.node.full + (name,)
            self.hive.onedit(full, onedit, base=self)

        node = self.node.get(name)
        if node is None:
            return self.defs.get(name, default)

        return node.valu

    async def set(self, name, valu):
        full = self.node.full + (name,)
        return await self.hive.set(full, valu)

    def setdefault(self, name, valu):
        self.defs[name] = valu

    def items(self):
        for key, node in iter(self.node):
            yield key, node.valu

    def values(self):
        for name, node in iter(self.node):
            yield node.valu

    async def pop(self, name, default=None):
        node = self.node.get(name)
        if node is None:
            return self.defs.get(name, default)

        retn = node.valu

        await node.hive.pop(node.full)

        return retn

# class HiveLock(s_base.Base):
# class HiveSeqn(s_base.Base):

# FIXME: move to separate file
class HiveAuth(s_base.Base):
    '''
    HiveAuth is a user authentication and authorization stored in a Hive.  Users
    correspond to separate logins with different passwords and potentially
    different privileges.

    Users are assigned "rules".  These rules are evaluated in order until a rule
    matches.  Each rule is a tuple of boolean, and a rule path (a sequence of
    strings).  Rules that are prefixes of a privilege match, i.e.  a rule
    ('foo',) will match ('foo', 'bar').

    Roles are just collections of rules.  When a user is "granted" a role those
    rules are assigned to that user.  Unlike in an RBAC system, users don't
    explicitly assume a role; they are merely a convenience mechanism to easily
    assign the same rules to multiple users.

    Authgates are objects that manage their own authorization.  Each
    AuthGate has roles and users subkeys which contain rules specific to that
    user or role for that AuthGate.  The roles and users of an AuthGate,
    called GateRole and GateUser respectively, contain the iden of a role or
    user defined prior and rules specific to that role or user; they do not
    duplicate the metadata of the role or user.

    Node layout:

    Auth root (passed into constructor)
    ├ roles
    │   ├ <role iden 1>
    │   ├ ...
    │   └ last role
    ├ users
    │   ├ <user iden 1>
    │   ├ ...
    │   └ last user
    └ authgates
        ├ <iden 1>
        │   ├ roles
        │   │   ├ <role iden 1> <- gateRole
        │   │   ├ ...
        │   │   └ last role
        │   └ users
        │       ├ <user iden 1> <- gateUser
        │       ├ ...
        │       └ last user
        ├ <iden 2>
        │   ├ ...
        └ ... last authgate
    '''

    async def __anit__(self, node):
        await s_base.Base.__anit__(self)

        self.node = node

        self.usersbyiden = {}
        self.rolesbyiden = {}
        self.usersbyname = {}
        self.rolesbyname = {}
        self.authgates = {}

        # TODO: listen for changes on role, users, authgates

        roles = await self.node.open(('roles',))
        for iden, node in roles:
            await self._addRoleNode(node)

        users = await self.node.open(('users',))
        for iden, node in users:
            await self._addUserNode(node)

        authgates = await self.node.open(('authgates',))
        for iden, node in authgates:
            try:
                await self._addAuthGate(node)
            except Exception:  # pragma: no cover
                logger.exception('Failure loading AuthGate')

        # initialize an admin user named root
        root = self.getUserByName('root')
        if root is None:
            root = await self.addUser('root')

        await root.setAdmin(True)
        await root.setLocked(False)

        async def fini():
            [await u.fini() for u in self.users()]
            [await r.fini() for r in self.roles()]
            [await a.fini() for a in self.authgates.values()]

        self.onfini(fini)

    def users(self):
        return self.usersbyiden.values()

    def roles(self):
        return self.rolesbyiden.values()

    def role(self, iden):
        return self.rolesbyiden.get(iden)

    def user(self, iden):
        return self.usersbyiden.get(iden)

    def getUserByName(self, name):
        '''
        Get a user by their username.

        Args:
            name (str): Name of the user to get.

        Returns:
            HiveUser: A Hive User.  May return None if there is no user by the requested name.
        '''
        return self.usersbyname.get(name)

    def getRoleByName(self, name):
        return self.rolesbyname.get(name)

    async def _addUserNode(self, node):

        user = await HiveUser.anit(node, self)

        self.usersbyiden[user.iden] = user
        self.usersbyname[user.name] = user

        return user

    async def _addRoleNode(self, node):

        role = await HiveRole.anit(node, self)

        self.rolesbyiden[role.iden] = role
        self.rolesbyname[role.name] = role

        return role

    async def _addAuthGate(self, node):
        gate = await AuthGate.anit(node, self)
        self.authgates[gate.iden] = gate
        return gate

    async def addAuthGate(self, iden, authgatetype):
        '''
        Retrieve AuthGate by iden.  Create if not present.

        Returns:
            (HiveAuthGate)
        '''
        gate = self.getAuthGate(iden)
        if gate is not None:
            if gate.type != authgatetype:
                raise s_exc.InconsistentStorage(mesg=f'Stored AuthGate is of type {gate.type}, not {authgatetype}')
            return gate

        path = self.node.full + ('authgates', iden)
        node = await self.node.hive.open(path)
        await self.node.hive.set(path, authgatetype)
        return await self._addAuthGate(node)

    async def delAuthGate(self, iden):
        gate = self.getAuthGate(iden)
        if gate is None:
            raise s_exc.NoSuchAuthGate(iden=iden)

        await gate.fini()
        await gate.delete()
        await gate.node.pop()
        del self.authgates[iden]

    def getAuthGate(self, iden):
        return self.authgates.get(iden)

    async def addUser(self, name):

        if self.usersbyname.get(name) is not None:
            raise s_exc.DupUserName(name=name)

        iden = s_common.guid()
        path = self.node.full + ('users', iden)

        # directly set the nodes value and let events prop
        await self.node.hive.set(path, name)

        node = await self.node.hive.open(path)
        return await self._addUserNode(node)

    async def addRole(self, name):

        if self.rolesbyname.get(name) is not None:
            raise s_exc.DupRoleName(name=name)

        iden = s_common.guid()
        path = self.node.full + ('roles', iden)

        # directly set the nodes value and let events prop
        await self.node.hive.set(path, name)

        node = await self.node.hive.open(path)
        return await self._addRoleNode(node)

    async def getRulerByName(self, name, iden=None):
        '''
        Returns:
            the HiveRuler (a HiveUser, HiveRole, GateUser, or GateRole) corresponding to the given name.
            If iden is not None, it returns the HiveRole or HiveUser of the AuthGate with iden.
        '''
        if iden is not None:
            authgate = self.getAuthGate(iden)
            if authgate is None:
                raise s_exc.NoSuchAuthGate(iden=iden)

        user = self.getUserByName(name)
        if user is not None:
            if iden is not None:
                return await authgate.getGateUser(user)
            return user

        role = self.getRoleByName(name)
        if role is not None:
            if iden is not None:
                return await authgate.getGateRole(role)
            return role

        raise s_exc.NoSuchName(name=name)

    async def delUser(self, name):

        if name == 'root':
            raise s_exc.CantDelRootUser(mesg='user "root" may not be deleted')

        user = self.usersbyname.get(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name)

        self.usersbyiden.pop(user.iden)
        self.usersbyname.pop(user.name)

        for gateuser in user.gaterulr.values():
            await gateuser.delete()

        path = self.node.full + ('users', user.iden)
        await user.fini()

        await self.node.hive.pop(path)

    def _getUsersInRole(self, role):
        for user in self.users():
            if role.iden in user.roleidens:
                yield user

    async def delRole(self, name):

        role = self.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        self.rolesbyiden.pop(role.iden)
        self.rolesbyname.pop(role.name)

        for user in self._getUsersInRole(role):
            await user.revokeRole(role)

        for gaterole in role.gaterulr.values():
            await gaterole.delete()

        await role.fini()

        # directly set the node's value and let events prop
        path = self.node.full + ('roles', role.iden)
        await self.node.hive.pop(path)

class AuthGate(s_base.Base):
    '''
    The storage object for an AuthGater, owned by a HiveAuth
    '''
    async def __anit__(self, node, auth):
        await s_base.Base.__anit__(self)
        self.auth = auth

        self.iden = node.name()
        self.type = node.valu

        self.node = node

        # TODO:  monitor users and roles nodes for changes behind my back
        self.gateroles = {} # iden -> GateRoles
        self.gateusers = {} # iden -> GateUsers

        usersnode = await node.open(('users',))
        self.onfini(usersnode)

        for name, gateusernode in usersnode:

            user = self.auth.user(name)
            if user is None:  # pragma: no cover
                logger.warning(f'Hive:  path {name} refers to unknown user')
                continue

            await GateUser.anit(gateusernode, self, user)

        rolesnode = await node.open(('roles',))
        self.onfini(rolesnode)

        for name, gaterolenode in rolesnode:

            role = self.auth.role(name)
            if role is None:  # pragma: no cover
                logger.warning(f'Hive:  path {name} refers to unknown role')
                continue

            await GateRole.anit(gaterolenode, self, role)

        async def fini():
            [await gaterulr.fini() for gaterulr in self.gateroles.values()]
            [await gaterulr.fini() for gaterulr in self.gateusers.values()]

        self.onfini(fini)

    async def _addGateRole(self, hiverole):

        path = self.node.full + ('roles', hiverole.iden)
        await self.node.hive.set(path, hiverole.name)
        node = await self.node.hive.open(path)
        gaterole = await GateRole.anit(node, self, hiverole)

        return gaterole

    async def getGateRole(self, hiverole):
        '''
        Retrieve the gaterole for a particular role.  Make it if it doesn't exist
        '''
        gaterole = self.gateroles.get(hiverole.iden)
        if gaterole is not None:
            return gaterole

        return await self._addGateRole(hiverole)

    async def _addGateUser(self, hiveuser):
        path = self.node.full + ('users', hiveuser.iden)
        await self.node.hive.set(path, hiveuser.name)
        node = await self.node.hive.open(path)
        gateuser = await GateUser.anit(node, self, hiveuser)
        self.gateusers[hiveuser.iden] = gateuser
        return gateuser

    async def getGateUser(self, hiveuser):
        '''
        Retrieve the gateuser for a particular user.  Make it if it doesn't exist
        '''
        gateuser = self.gateusers.get(hiveuser.iden)
        if gateuser is not None:
            return gateuser

        return await self._addGateUser(hiveuser)

    async def delete(self):
        todelete = list(self.gateroles.values()) + list(self.gateusers.values())
        for gaterulr in todelete:
            await gaterulr.delete()

class AuthGater(s_base.Base):
    '''
    An object that manages its own permissions

    Note:
        This is a mixin and is intended to be subclassed by view, layers
    '''
    async def __anit__(self, auth):  # type: ignore
        '''
        Precondition:
            self.iden and self.authgatetype must be set
        '''
        await s_base.Base.__anit__(self)

        self.authgate = await auth.addAuthGate(self.iden, self.authgatetype)
        self.onfini(self.authgate)

    async def trash(self):
        '''
        Remove all rules relating to this object

        Prerequisite: Object must be fini'd first
        '''
        assert self.isfini
        await self.authgate.auth.delAuthGate(self.iden)

    async def _reqUserAllowed(self, hiveuser, perm):
        '''
        Raise AuthDeny if hiveuser does not have permissions perm

        Note:
            async for consistency with CellApi._reqUserAllowed
        '''
        if not self.allowed(hiveuser, perm):
            perm = '.'.join(perm)
            mesg = f'User must have permission {perm} for {self.iden}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=hiveuser.name)

    def allowed(self, hiveuser, perm, elev=True, default=None):
        '''
        Returns (Optional[bool]):
            True if explicitly granted, False if denied, None if neither
        '''
        if hiveuser.locked:
            return False

        if hiveuser.admin and elev:
            return True

        # 1. local user rules: check for an AuthGate-specific rule first
        gaterulr = self.authgate.gateusers.get(hiveuser.iden)
        if gaterulr:
            retn = gaterulr.allowedLocal(perm)
            if retn is not None:
                return retn

        # 2. global user rules
        retn = hiveuser.allowedLocal(perm)
        if retn is not None:
            return retn

        idenset = set(hiveuser.roleidens)

        # 3. local role rules: check for an AuthGate-specific role rule
        for iden, gaterole in self.authgate.gateroles.items():
            if iden in idenset:
                retn = gaterole.allowedLocal(perm)
            if retn is not None:
                return retn

        # 4. global role rules
        for role in hiveuser.roles:
            retn = role.allowedLocal(perm)
            if retn is not None:
                return retn

        return default if retn is None else retn

class HiveRuler(s_base.Base):
    '''
    A HiveNode that holds a list of rules.  This includes HiveUsers, HiveRoles, and the AuthGate variants of those
    '''

    async def __anit__(self, node, auth):

        await s_base.Base.__anit__(self)

        self.auth = auth
        self.node = node

        # Stores the AuthGate-specific instances of this ruler, by authgate tuple
        self.gaterulr = {}  # gate iden -> GateRuler

        self.name = node.valu
        self.iden = node.name()
        self.info = await node.dict()
        self.onfini(self.info)
        self.info.setdefault('rules', ())
        self.rules = self.info.get('rules', onedit=self._onRulesEdit)
        self.permcache = s_cache.FixedCache(self._calcPermAllow)

    async def _onRulesEdit(self, mesg):
        self.rules = self.info.get('rules')
        self.permcache.clear()

    async def setName(self, name):
        self.name = name
        await self.node.set(name)

    async def setRules(self, rules):
        self.rules = list(rules)
        await self.info.set('rules', rules)

    async def addRule(self, rule, indx=None):

        rules = list(self.rules)

        if indx is None:
            rules.append(rule)
        else:
            rules.insert(indx, rule)

        await self.info.set('rules', rules)

    async def delRule(self, rule):

        if rule not in self.rules:
            return False

        rules = list(self.rules)
        rules.remove(rule)

        await self.info.set('rules', rules)
        return True

    async def delRuleIndx(self, indx):
        if indx < 0:
            raise s_exc.BadArg(mesg='Rule index must be greater than or equal to 0',
                               valu=indx)
        rules = list(self.rules)
        try:
            rules.pop(indx)
        except IndexError:
            raise s_exc.BadArg(mesg='Rule does not exist at specified index.',
                               valu=indx) from None

        await self.info.set('rules', rules)

    def _calcPermAllow(self, perm):

        for rule in self.rules:
            allow, path = rule
            if perm[:len(path)] == path:
                return allow

    def allowedLocal(self, perm):
        '''
        Returns cached evaluation of my own rules only
        '''
        return self.permcache.get(perm)

class GateRuler(HiveRuler):
    '''
    Store AuthGate-specific rules for a role or user
    '''
    async def __anit__(self, node, authgate, hiverulr):  # type: ignore
        '''
        Args:
            node (Node): HiveNode where this object persists
            authgate (AuthGate): business logic object these rules apply to
            hiverulr (HiveRulr): a reference to a HiveRole or HiveUser that has the rest of the metadata
        '''
        await HiveRuler.__anit__(self, node, authgate.auth)
        self.gate = authgate
        self.hiverulr = hiverulr

        gateiden = authgate.iden

        assert gateiden not in hiverulr.gaterulr
        # Give the subject a reference to me for easy status querying
        hiverulr.gaterulr[gateiden] = self
        self.onfini(node)

    async def delete(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(mesg='GateRuler subclasses must implement delete')

class GateRole(GateRuler):
    '''
    A bundle of rules specific to a particular AuthGate for a role
    '''
    async def __anit__(self, node, authgate, hiverulr):  # type: ignore
        authgate.gateroles[hiverulr.iden] = self
        await GateRuler.__anit__(self, node, authgate, hiverulr)

    async def delete(self):
        del self.gate.gateroles[self.iden]
        await self.node.pop(())
        await self.fini()

class GateUser(GateRuler):
    '''
    A bundle of rules specific to a particular AuthGate for a particular user
    '''
    async def __anit__(self, node, authgate, hiverulr):  # type: ignore
        await GateRuler.__anit__(self, node, authgate, hiverulr)
        authgate.gateusers[hiverulr.iden] = self

    async def delete(self):
        del self.gate.gateusers[self.iden]
        await self.node.pop(())
        await self.fini()

class HiveRole(HiveRuler):
    '''
    A role within the Hive authorization subsystem.

    A role in HiveAuth exists to bundle rules together so that the same
    set of rules can be applied to multiple users.
    '''
    def pack(self):
        # Filter out the boring empty nodes with no rules
        gaterules = {key: e.rules for key, e in self.gaterulr.items() if e.rules}
        return {
            'type': 'role',
            'iden': self.iden,
            'name': self.name,
            'rules': self.rules,
            'gaterules': gaterules
        }

class HiveUser(HiveRuler):
    '''
    A user (could be human or computer) of the system within HiveAuth.

    Cortex-wide rules are stored here.  AuthGate-specific rules for this user are stored in an GateUser.
    '''
    async def __anit__(self, node, auth):
        await HiveRuler.__anit__(self, node, auth)

        self.info.setdefault('roles', ())

        self.info.setdefault('admin', False)
        self.info.setdefault('passwd', None)
        self.info.setdefault('locked', False)
        self.info.setdefault('archived', False)

        self.roleidens = self.info.get('roles', onedit=self._onRolesEdit)
        self.roles = []
        self.admin = self.info.get('admin', onedit=self._onAdminEdit)
        self.locked = self.info.get('locked', onedit=self._onLockedEdit)

        # arbitrary profile data for application layer use
        prof = await self.node.open(('profile',))
        self.profile = await prof.dict()

        # vars cache for persistent user level data storage
        # TODO: max size check / max count check?
        pvars = await self.node.open(('vars',))
        self.pvars = await pvars.dict()

        self.fullrules = []
        self._onRolesEdit(None)

    def pack(self):
        return {
            'type': 'user',
            'name': self.name,
            'iden': self.node.name(),
            'rules': self.rules,
            'roles': self.roleidens,
            'admin': self.admin,
            'email': self.info.get('email'),
            'locked': self.locked,
            'archived': self.info.get('archived'),
            'gaterules': {key: e.rules for key, e in self.gaterulr.items()}
        }

    def allowed(self, perm, elev=True, default=None):
        if self.locked:
            return False

        if self.admin and elev:
            return True

        retn = self.allowedLocal(perm)
        if retn is not None:
            return retn

        for role in self.roles:
            retn = role.allowedLocal(perm)
            if retn is not None:
                return retn

        return retn if retn else default

    def getRoles(self):
        return self.roles

    def _onRolesEdit(self, mesg):
        '''
        Update my roles
        '''
        self.roleidens = self.info.get('roles')
        self.roles = [self.auth.role(iden) for iden in self.roleidens]
        self.permcache.clear()

    async def _onAdminEdit(self, mesg):
        self.admin = self.info.get('admin')
        # no need to bump the cache, as admin check is not cached

    async def _onLockedEdit(self, mesg):
        self.locked = self.info.get('locked')

    async def grant(self, name, indx=None):

        role = self.auth.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        return await self.grantRole(role)

    async def grantRole(self, role, indx=None):

        roles = list(self.roleidens)
        if role.iden in roles:
            return

        if indx is None:
            roles.append(role.iden)
        else:
            roles.insert(indx, role.iden)

        await self.info.set('roles', roles)

    async def revoke(self, name):

        role = self.auth.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        return await self.revokeRole(role)

    async def revokeRole(self, role):

        roles = list(self.roleidens)
        if role.iden not in roles:
            return

        roles.remove(role.iden)
        await self.info.set('roles', roles)

    async def setAdmin(self, admin):
        await self.info.set('admin', admin)

    async def setLocked(self, locked):
        await self.info.set('locked', locked)

    async def setArchived(self, archived):
        await self.info.set('archived', archived)
        if archived:
            await self.setLocked(True)

    def tryPasswd(self, passwd):

        if self.locked:
            return False

        if passwd is None:
            return False

        shadow = self.info.get('passwd')
        if shadow is None:
            return False

        salt, hashed = shadow

        if s_common.guid((salt, passwd)) == hashed:
            return True

        return False

    async def setPasswd(self, passwd):
        # Prevent empty string or non-string values
        if not passwd or not isinstance(passwd, str):
            raise s_exc.BadArg(mesg='Password must be a string')
        salt = s_common.guid()
        hashed = s_common.guid((salt, passwd))
        await self.info.set('passwd', (salt, hashed))

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
