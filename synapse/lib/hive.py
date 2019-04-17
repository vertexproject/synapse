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
        full = self.full + path
        return await self.hive.open(full)

    async def pop(self, path):
        full = self.full + path
        return await self.hive.pop(full)

    async def dict(self):
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

    async def getHiveAuth(self):

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

        node = self.nodes.get(full)
        if node is None:
            return None

        return node.valu

    def dir(self, full):
        node = self.nodes.get(full)
        if node is None:
            return None

        return node.dir()

    async def dict(self, full):
        '''
        Open a HiveDict at the given full path.
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
                #print('STEP: %r %r' % (path, step))
                # hive add events alert the *parent* path of edits
                #await node.fire('hive:add', path=path[:-1], name=name, valu=None)

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

    def get(self, name, onedit=None):

        # use hive.onedit() here to register for
        # paths which potentially dont exist yet
        if onedit is not None:
            full = self.node.full + (name,)
            self.hive.onedit(full, onedit, base=self)

        node = self.node.get(name)
        if node is None:
            return self.defs.get(name)

        return node.valu

    async def set(self, name, valu):
        full = self.node.full + (name,)
        return await self.hive.set(full, valu)

    def setdefault(self, name, valu):
        self.defs[name] = valu

    def items(self):
        for key, node in iter(self.node):
            yield key, node.valu

    async def pop(self, name):
        node = self.node.get(name)
        if node is None:
            return self.defs.get(name)

        retn = node.valu

        await node.hive.pop(node.full)

        return retn

#TODO
#class HiveLock(s_base.Base):
#class HiveSeqn(s_base.Base):
#class HiveRules(s_base.Base): allow separate rules for different objects

class HiveAuth(s_base.Base):

    async def __anit__(self, node):

        await s_base.Base.__anit__(self)

        self.node = node

        self.usersbyiden = {}
        self.rolesbyiden = {}
        self.usersbyname = {}
        self.rolesbyname = {}

        roles = await self.node.open(('roles',))
        for iden, node in roles:
            await self._addRoleNode(node)

        users = await self.node.open(('users',))
        for iden, node in users:
            await self._addUserNode(node)

        # initialize an admin user named root
        root = self.getUserByName('root')
        if root is None:
            root = await self.addUser('root')

        await root.setAdmin(True)
        await root.setLocked(False)

        async def fini():
            [await u.fini() for u in self.users()]
            [await r.fini() for r in self.roles()]

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
        return self.usersbyname.get(name)

    def getRoleByName(self, name):
        return self.rolesbyname.get(name)

    async def _addUserNode(self, node):

        user = await HiveUser.anit(self, node)

        self.onfini(user)
        self.usersbyiden[user.iden] = user
        self.usersbyname[user.name] = user

        return user

    async def _addRoleNode(self, node):

        role = await HiveRole.anit(self, node)

        self.onfini(role)

        self.rolesbyiden[role.iden] = role
        self.rolesbyname[role.name] = role

        return role

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

    async def delUser(self, name):

        if name == 'root':
            raise s_exc.CantDelRootUser(mesg='user "root" may not be deleted')

        user = self.usersbyname.get(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name)

        self.usersbyiden.pop(user.iden)
        self.usersbyname.pop(user.name)

        path = self.node.full + ('users', user.iden)

        await self.node.hive.pop(path)

    def _getUsersInRole(self, role):
        for user in self.users():
            if role.iden in user.roles:
                yield user

    async def delRole(self, name):

        role = self.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        self.rolesbyiden.pop(role.iden)
        self.rolesbyname.pop(role.name)

        path = self.node.full + ('roles', role.iden)

        for user in self._getUsersInRole(role):
            await user.revokeRole(role)

        # directly set the nodes value and let events prop
        await self.node.hive.pop(path)

class HiveIden(s_base.Base):

    async def __anit__(self, auth, node):

        await s_base.Base.__anit__(self)

        self.auth = auth
        self.node = node
        self.iden = node.name()
        self.name = node.valu

        self.info = await node.dict()
        self.onfini(self.info)

        self.info.setdefault('rules', ())
        self.rules = self.info.get('rules', onedit=self._onRulesEdit)

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

class HiveRole(HiveIden):
    '''
    A role within the Hive authorization subsystem.
    The HiveRole mainly exists to contain rules.
    '''
    async def _onRulesEdit(self, mesg):

        self.rules = self.info.get('rules')

        for user in self.auth.usersbyiden.values():

            if self.iden in user.roles:
                user._initFullRules()

    def pack(self):
        return {
            'type': 'role',
            'iden': self.iden,
            'name': self.name,
            'rules': self.rules,
        }

class HiveUser(HiveIden):

    async def __anit__(self, auth, node):

        await HiveIden.__anit__(self, auth, node)

        self.info.setdefault('roles', ())

        self.info.setdefault('admin', False)
        self.info.setdefault('passwd', None)
        self.info.setdefault('locked', False)
        self.info.setdefault('archived', False)

        self.roles = self.info.get('roles', onedit=self._onRolesEdit)
        self.admin = self.info.get('admin', onedit=self._onAdminEdit)
        self.locked = self.info.get('locked', onedit=self._onLockedEdit)

        # arbitrary profile data for application layer use
        prof = await self.node.open(('profile',))
        self.profile = await prof.dict()

        self.fullrules = []
        self.permcache = s_cache.FixedCache(self._calcPermAllow)

        self._initFullRules()

    def pack(self):
        return {
            'type': 'user',
            'name': self.name,
            'iden': self.node.name(),
            'rules': self.rules,
            'roles': [r.iden for r in self.getRoles()],
            'admin': self.admin,
            'email': self.info.get('email'),
            'locked': self.locked,
            'archived': self.info.get('archived'),
        }

    def _calcPermAllow(self, perm):
        for retn, path in self.fullrules:
            if perm[:len(path)] == path:
                return retn

        return False

    def getRoles(self):
        for iden in self.roles:
            role = self.auth.role(iden)
            if role is not None:
                yield role

    def _initFullRules(self):

        self.fullrules.clear()
        self.permcache.clear()

        for rule in self.rules:
            self.fullrules.append(rule)

        for iden in self.roles:

            role = self.auth.role(iden)

            for rule in role.rules:
                self.fullrules.append(rule)

    async def _onRolesEdit(self, mesg):
        self.roles = self.info.get('roles')
        self._initFullRules()

    async def _onRulesEdit(self, mesg):
        self.rules = self.info.get('rules')
        self._initFullRules()

    async def _onAdminEdit(self, mesg):
        self.admin = self.info.get('admin')
        # no need to bump the cache/rules

    async def _onLockedEdit(self, mesg):
        self.locked = self.info.get('locked')

    def allowed(self, perm, elev=True):

        if self.locked:
            return False

        if self.admin and elev:
            return True

        return self.permcache.get(perm)

    async def grant(self, name, indx=None):

        role = self.auth.rolesbyname.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        return await self.grantRole(role)

    async def grantRole(self, role, indx=None):

        roles = list(self.roles)
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

        roles = list(self.roles)
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
