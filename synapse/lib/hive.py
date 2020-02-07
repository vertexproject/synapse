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

        # FIXME:  reconsider this whole use case given new change dist scheme

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
            user = await auth.getUserByName('root')
            return await HiveApi.anit(self, user)

        name, info = mesg[1].get('auth')

        user = await auth.getUserByName(name)
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

    def get(self, name, default=None):

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

    def pack(self):
        return {name: node.valu for (name, node) in iter(self.node)}

    async def pop(self, name, default=None):
        node = self.node.get(name)
        if node is None:
            return self.defs.get(name, default)

        retn = node.valu

        await node.hive.pop(node.full)

        return retn

# FIXME: move to separate file
class HiveAuth(s_nexus.Pusher):
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
        │   │   ├ <role iden 1>
        │   │   ├ ...
        │   │   └ last role
        │   └ users
        │       ├ <user iden 1>
        │       ├ ...
        │       └ last user
        ├ <iden 2>
        │   ├ ...
        └ ... last authgate
    '''

    async def __anit__(self, node, nexsroot=None):
        '''
        Args:
            node (HiveNode): The root of the persistent storage for auth
        '''
        # Derive an iden from the parent
        iden = 'auth:' + ':'.join(node.full)
        await s_nexus.Pusher.__anit__(self, iden, nexsroot=nexsroot)

        self.node = node

        self.usersbyiden = {}
        self.rolesbyiden = {}
        self.usersbyname = {}
        self.rolesbyname = {}
        self.authgates = {}

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

        self.allrole = await self.getRoleByName('all')
        if self.allrole is None:
            # initialize the role of which all users are a member
            self.allrole = await self.addRole('all')

        # initialize an admin user named root
        self.rootuser = await self.getUserByName('root')
        if self.rootuser is None:
            self.rootuser = await self.addUser('root')

        await self.rootuser.setAdmin(True)
        await self.rootuser.setLocked(False)

        async def fini():
            await self.allrole.fini()
            await self.rootuser.fini()
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

    async def reqUser(self, iden):

        user = self.user(iden)
        if user is None:
            mesg = f'No user with iden {iden}.'
            raise s_exc.NoSuchUser(mesg=mesg)
        return user

    async def reqRole(self, iden):

        role = self.role(iden)
        if role is None:
            mesg = f'No role with iden {iden}.'
            raise s_exc.NoSuchRole(mesg=mesg)
        return role

    async def reqUserByName(self, name):
        user = await self.getUserByName(name)
        if user is None:
            mesg = f'No user named {name}.'
            raise s_exc.NoSuchUser(mesg=mesg)
        return user

    async def reqRoleByName(self, name):
        role = await self.getRoleByName(name)
        if role is None:
            mesg = f'No role named {name}.'
            raise s_exc.NoSuchRole(mesg=mesg)
        return role

    async def getUserByName(self, name):
        '''
        Get a user by their username.

        Args:
            name (str): Name of the user to get.

        Returns:
            HiveUser: A Hive User.  May return None if there is no user by the requested name.
        '''
        return self.usersbyname.get(name)

    async def getUserIdenByName(self, name):
        user = await self.getUserByName(name)
        return None if user is None else user.iden

    async def getRoleByName(self, name):
        return self.rolesbyname.get(name)

    async def _addUserNode(self, node):

        user = await HiveUser.anit(node, self)

        self.usersbyiden[user.iden] = user
        self.usersbyname[user.name] = user

        return user

    @s_nexus.Pusher.onPushAuto('user:name')
    async def setUserName(self, iden, name):

        if self.usersbyname.get(name) is not None:
            raise s_exc.DupUserName(name=name)

        user = await self.reqUser(iden)
        user.name = name
        await user.node.set(name)

    @s_nexus.Pusher.onPushAuto('role:name')
    async def setRoleName(self, iden, name):

        if self.rolesbyname.get(name) is not None:
            raise s_exc.DupRoleName(name=name)

        role = await self.reqRole(iden)
        role.name = name
        await role.node.set(name)

    @s_nexus.Pusher.onPushAuto('user:info')
    async def setUserInfo(self, iden, name, valu, gateiden=None):

        user = await self.reqUser(iden)

        info = user.info
        if gateiden is not None:
            info = await user.genGateInfo(gateiden)

        await info.set(name, valu)

        # since any user info *may* effect auth
        user.clearAuthCache()

    async def getUserVar(self, iden, name, default=None):
        user = await self.reqUser(iden)
        return user.vars.get(name, default=default)

    @s_nexus.Pusher.onPushAuto('user:var:set')
    async def setUserVar(self, iden, name, valu):
        user = await self.reqUser(iden)
        await user.vars.set(name, valu)

    @s_nexus.Pusher.onPushAuto('user:var:pop')
    async def popUserVar(self, iden, name, default=None):
        user = await self.reqUser(iden)
        return await user.vars.pop(name, default=default)

    async def itemsUserVar(self, iden):
        user = await self.reqUser(iden)
        for item in user.vars.items():
            yield item

    @s_nexus.Pusher.onPushAuto('user:profile')
    async def setUserProfile(self, iden, name, valu):
        user = await self.reqUser(iden)
        await user.profile.set(name, valu)

    @s_nexus.Pusher.onPushAuto('role:info')
    async def setRoleInfo(self, iden, name, valu, gateiden=None):
        role = await self.reqRole(iden)

        info = role.info
        if gateiden is not None:
            info = await role.genGateInfo(gateiden)

        await info.set(name, valu)
        role.clearAuthCache()

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

        Note:
            Not change distributed

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
        '''
        Delete AuthGate by iden.

        Note:
            Not change distributed
        '''
        gate = self.getAuthGate(iden)
        if gate is None:
            raise s_exc.NoSuchAuthGate(iden=iden)

        await gate.fini()
        await gate.delete()
        await gate.node.pop()

        del self.authgates[iden]

    def getAuthGate(self, iden):
        return self.authgates.get(iden)

    def reqAuthGate(self, iden):
        gate = self.authgates.get(iden)
        if gate is None:
            mesg = f'No auth gate found with iden: ({iden}).'
            raise s_exc.NoSuchAuthGate(iden=iden, mesg=mesg)
        return gate

    async def addUser(self, name):

        iden = s_common.guid()
        user = await self._push('user:add', iden, name)

        # Everyone's a member of 'all'
        await user.grant('all')

        return user

    @s_nexus.Pusher.onPush('user:add')
    async def _addUser(self, iden, name):

        if self.usersbyname.get(name) is not None:
            raise s_exc.DupUserName(name=name)

        node = await self.node.open(('users', iden))
        await node.set(name)

        return await self._addUserNode(node)

    async def addRole(self, name):
        iden = s_common.guid()
        return await self._push('role:add', iden, name)

    @s_nexus.Pusher.onPush('role:add')
    async def _addRole(self, iden, name):

        if self.rolesbyname.get(name) is not None:
            raise s_exc.DupRoleName(name=name)

        node = await self.node.open(('roles', iden))
        await node.set(name)

        return await self._addRoleNode(node)

    @s_nexus.Pusher.onPushAuto('user:del')
    async def delUser(self, name):

        if name == 'root':
            raise s_exc.CantDelRootUser(mesg='user "root" may not be deleted')

        user = await self.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name)

        self.usersbyiden.pop(user.iden)
        self.usersbyname.pop(user.name)

        path = self.node.full + ('users', user.iden)

        await user.fini()
        await self.node.hive.pop(path)

    def _getUsersInRole(self, role):
        for user in self.users():
            if role.iden in user.info.get('roles', ()):
                yield user

    @s_nexus.Pusher.onPushAuto('role:del')
    async def delRole(self, name):

        if name == 'all':
            raise s_exc.CantDelAllRole(mesg='role "all" may not be deleted')

        role = self.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        for user in self._getUsersInRole(role):
            await user.revoke(role.name)

        self.rolesbyiden.pop(role.iden)
        self.rolesbyname.pop(role.name)

        await role.fini()

        # directly set the node's value and let events prop
        path = self.node.full + ('roles', role.iden)
        await self.node.hive.pop(path)

class AuthGate(s_base.Base):
    '''
    The storage object for object specific rules for users/roles.
    '''
    async def __anit__(self, node, auth):
        await s_base.Base.__anit__(self)
        self.auth = auth

        self.iden = node.name()
        self.type = node.valu

        self.node = node

        self.gateroles = {} # iden -> HiveRole
        self.gateusers = {} # iden -> HiveUser

        for useriden, usernode in await node.open(('users',)):

            user = self.auth.user(useriden)
            if user is None:  # pragma: no cover
                logger.warning(f'Hive: path {useriden} refers to unknown user')
                continue

            userinfo = await usernode.dict()
            self.gateusers[user.iden] = user
            user.authgates[self.iden] = userinfo
            user.clearAuthCache()

        for roleiden, rolenode in await node.open(('roles',)):

            role = self.auth.role(roleiden)
            if role is None:  # pragma: no cover
                logger.warning(f'Hive: path {roleiden} refers to unknown role')
                continue

            roleinfo = await rolenode.dict()
            self.gateroles[role.iden] = role
            role.authgates[self.iden] = roleinfo

    async def genUserInfo(self, iden):
        node = await self.node.open(('users', iden))
        userinfo = await node.dict()

        user = self.auth.user(iden)
        self.gateusers[iden] = user
        user.authgates[self.iden] = userinfo

        return userinfo

    async def genRoleInfo(self, iden):
        node = await self.node.open(('roles', iden))
        roleinfo = await node.dict()

        role = self.auth.role(iden)
        self.gateroles[iden] = role
        role.authgates[self.iden] = roleinfo

        return roleinfo

    async def _delGateUser(self, iden):
        self.gateusers.pop(iden, None)
        await self.node.pop(('users', iden))

    async def _delGateRole(self, iden):
        self.gateroles.pop(iden, None)
        await self.node.pop(('roles', iden))

    async def delete(self):

        await self.fini()

        for iden, user in list(self.gateusers.items()):
            user.authgates.pop(self.iden, None)
            user.clearAuthCache()

        for iden, role in list(self.gateroles.items()):
            role.authgates.pop(self.iden, None)
            role.clearAuthCache()

        await self.node.pop()

class HiveRuler(s_base.Base):
    '''
    A HiveNode that holds a list of rules.  This includes HiveUsers, HiveRoles, and the AuthGate variants of those
    '''

    async def __anit__(self, node, auth):
        await s_base.Base.__anit__(self)

        self.iden = node.name()

        self.auth = auth
        self.node = node
        self.name = node.valu
        self.info = await node.dict()

        self.info.setdefault('admin', False)
        self.info.setdefault('rules', ())

        self.authgates = {}

    async def _setRulrInfo(self, name, valu, gateiden=None): # pragma: no cover
        raise s_exc.NoSuchImpl(mesg='Subclass must implement _setRulrInfo')

    def getRules(self, gateiden=None):

        if gateiden is None:
            return list(self.info.get('rules', ()))

        gateinfo = self.authgates.get(gateiden)
        if gateinfo is None:
            return []

        return list(gateinfo.get('rules', ()))

    async def setRules(self, rules, gateiden=None):
        return await self._setRulrInfo('rules', rules, gateiden=gateiden)

    async def addRule(self, rule, indx=None, gateiden=None):

        rules = self.getRules(gateiden=gateiden)
        assert len(rule) == 2

        if indx is None:
            rules.append(rule)
        else:
            rules.insert(indx, rule)

        await self.setRules(rules, gateiden=gateiden)

    async def delRule(self, rule, gateiden=None):

        rules = self.getRules(gateiden=gateiden)
        if rule not in rules:
            return False

        rules.remove(rule)
        await self.setRules(rules, gateiden=gateiden)
        return True

#    async def delRuleIndx(self, indx, gateiden=None):
#
#        rules = self.getRules(gateiden=gateiden)
#
#        try:
#            rules.pop(indx)
#        except IndexError:
#            raise s_exc.BadArg(mesg='Rule does not exist at specified index.',
#                               valu=indx) from None
#
#        await self.setRules(rules, gateiden=gateiden)

class HiveRole(HiveRuler):
    '''
    A role within the Hive authorization subsystem.

    A role in HiveAuth exists to bundle rules together so that the same
    set of rules can be applied to multiple users.
    '''
    def pack(self):
        return {
            'type': 'role',
            'iden': self.iden,
            'name': self.name,
            'rules': self.info.get('rules'),
            'authgates': {name: info.pack() for (name, info) in self.authgates.items()},
        }

    async def _setRulrInfo(self, name, valu, gateiden=None):
        return await self.auth.setRoleInfo(self.iden, name, valu, gateiden=gateiden)

    async def setName(self, name):
        return await self.auth.setRoleName(self.iden, name)

    def clearAuthCache(self):
        for user in self.auth.users():
            if user.hasRole(self.iden):
                user.clearAuthCache()

    async def genGateInfo(self, gateiden):
        info = self.authgates.get(gateiden)
        if info is None:
            gate = self.auth.reqAuthGate(gateiden)
            info = self.authgates[gateiden] = await gate.genRoleInfo(self.iden)
        return info

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

        # arbitrary profile data for application layer use
        prof = await self.node.open(('profile',))
        self.profile = await prof.dict()

        # vars cache for persistent user level data storage
        # TODO: max size check / max count check?
        _vars = await self.node.open(('vars',))
        self.vars = await _vars.dict()

        self.permcache = s_cache.FixedCache(self._allowed)

    def pack(self):
        return {
            'type': 'user',
            'iden': self.iden,
            'name': self.name,
            'rules': self.info.get('rules', ()),
            'roles': self.info.get('roles', ()),
            'admin': self.info.get('admin', ()),
            'email': self.info.get('email'),
            'locked': self.info.get('locked'),
            'archived': self.info.get('archived'),
            'authgates': {name: info.pack() for (name, info) in self.authgates.items()},
        }

    async def _setRulrInfo(self, name, valu, gateiden=None):
        return await self.auth.setUserInfo(self.iden, name, valu, gateiden=gateiden)

    async def setName(self, name):
        return await self.auth.setUserName(self.iden, name)

    def allowed(self, perm, default=None, gateiden=None):
        return self.permcache.get((perm, default, gateiden))

    def _allowed(self, pkey):

        perm, default, gateiden = pkey

        if self.info.get('locked'):
            return False

        if self.info.get('admin'):
            return True

        # 1. check authgate user rules
        if gateiden is not None:

            info = self.authgates.get(gateiden)
            if info is not None:

                if info.get('admin'):
                    return True

                for allow, path in info.get('rules', ()):
                    if perm[:len(path)] == path:
                        return allow

        # 2. check user rules
        for allow, path in self.info.get('rules', ()):
            if perm[:len(path)] == path:
                return allow

        # 3. check authgate role rules
        if gateiden is not None:

            for role in self.getRoles():

                info = role.authgates.get(gateiden)
                if info is None:
                    continue

                for allow, path in info.get('rules', ()):
                    if perm[:len(path)] == path:
                        return allow

        # 4. check role rules
        for role in self.getRoles():
            for allow, path in role.info.get('rules', ()):
                if perm[:len(path)] == path:
                    return allow

        return default

    def clearAuthCache(self):
        self.permcache.clear()

    async def genGateInfo(self, gateiden):
        info = self.authgates.get(gateiden)
        if info is None:
            gate = self.auth.reqAuthGate(gateiden)
            info = await gate.genUserInfo(self.iden)
        return info

    def confirm(self, perm, default=None, gateiden=None):
        if not self.allowed(perm, default=default, gateiden=gateiden):
            self.raisePermDeny(perm, gateiden=gateiden)

    def raisePermDeny(self, perm, gateiden=None):

        perm = '.'.join(perm)
        if gateiden is None:
            mesg = f'User {self.name!r} ({self.iden}) must have permission {perm}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.name)

        gate = self.auth.reqAuthGate(gateiden)
        mesg = f'User {self.name!r} ({self.iden}) must have permission {perm} on object {gate.iden} ({gate.type}).'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.name)

    def getRoles(self):
        for iden in self.info.get('roles', ()):
            role = self.auth.role(iden)
            if role is None:
                logger.warn('user {self.iden} has non-existent role: {iden}')
                continue
            yield role

    def hasRole(self, iden):
        return iden in self.info.get('roles', ())

    async def grant(self, name, indx=None):

        role = self.auth.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        roles = list(self.info.get('roles'))
        if role.iden in roles:
            return

        if indx is None:
            roles.append(role.iden)
        else:
            roles.insert(indx, role.iden)

        await self.auth.setUserInfo(self.iden, 'roles', roles)

    async def revoke(self, name):

        role = self.auth.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        if role.name == 'all':
            raise s_exc.CantRevokeAllRole(mesg='role "all" may not be revoked')

        roles = list(self.info.get('roles'))
        if role.iden not in roles:
            return

        roles.remove(role.iden)
        await self.auth.setUserInfo(self.iden, 'roles', roles)

    def isLocked(self):
        return self.info.get('locked')

    def isAdmin(self, gateiden=None):

        if gateiden is None:
            return self.info.get('admin', False)

        gateinfo = self.authgates.get(gateiden)
        if gateinfo is None:
            return False

        return gateinfo.get('admin', False)

    async def setAdmin(self, admin, gateiden=None):
        await self.auth.setUserInfo(self.iden, 'admin', admin, gateiden=gateiden)

    async def setLocked(self, locked):
        await self.auth.setUserInfo(self.iden, 'locked', locked)

    async def setArchived(self, archived):
        await self.auth.setUserInfo(self.iden, 'archived', archived)
        if archived:
            await self.setLocked(True)

    def tryPasswd(self, passwd):

        if self.info.get('locked', False):
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
