import os
import logging
import pathlib
import tempfile
import contextlib

import synapse.exc as s_exc

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

SLAB_MAP_SIZE = 128 * s_const.mebibyte

'''
Base classes for the synapse "cell" microservice architecture.
'''
def adminapi(f):

    def func(*args, **kwargs):

        if args[0].user is None:
            raise s_exc.AuthDeny(mesg='Auth not enabled.')

        if not args[0].user.admin:
            raise s_exc.AuthDeny(mesg='User is not an admin.',
                                 user=args[0].user.name)

        logger.info('Executing [%s] as [%s] with args [%s][%s]',
                    f.__qualname__, args[0].user, args[1:], kwargs)

        return f(*args, **kwargs)

    return func

class CellApi(s_base.Base):

    async def __anit__(self, cell, link):
        await s_base.Base.__anit__(self)
        self.cell = cell
        self.link = link
        self.user = link.get('cell:user')

    def getCellType(self):
        return self.cell.getCellType()

    def getCellIden(self):
        return self.cell.getCellIden()

    async def ps(self):

        retn = []

        admin = False
        if self.user is not None:
            admin = self.user.admin

        for synt in self.cell.boss.ps():
            if admin or synt.user == self.user:
                retn.append(synt.pack())

        return retn

    async def kill(self, iden):

        admin = False
        if self.user is not None:
            admin = self.user.admin

        logger.info(f'User [{str(self.user)}] Requesting task kill: {iden}')
        task = self.cell.boss.get(iden)
        if task is None:
            logger.info(f'Task does not exist: {iden}')
            return False

        if admin or task.user == self.user:
            logger.info(f'Killing task: {iden}')
            await task.kill()
            logger.info(f'Task killed: {iden}')
            return True

        raise s_exc.AuthDeny(mesg='Caller must own task or be admin.', task=iden, user=str(self.user))

    @adminapi
    def addAuthUser(self, name):
        self.cell.auth.addUser(name)

    @adminapi
    def addAuthRole(self, name):
        self.cell.auth.addRole(name)

    @adminapi
    def getAuthUsers(self):
        return self.cell.auth.getUsers()

    @adminapi
    def getAuthRoles(self):
        return self.cell.auth.getRoles()

    @adminapi
    def addAuthRule(self, name, rule, indx=None):
        item = self._getAuthItem(name)
        return item.addRule(rule, indx=indx)

    @adminapi
    def delAuthRule(self, name, indx):
        item = self._getAuthItem(name)
        return item.delRule(indx)

    @adminapi
    def setAuthAdmin(self, name, admin):
        '''
        Set the admin status of the given user/role.
        '''
        item = self._getAuthItem(name)
        item.setAdmin(admin)

    @adminapi
    def setUserPasswd(self, name, passwd):
        user = self.cell.auth.users.get(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        user.setPasswd(passwd)

    @adminapi
    def setUserLocked(self, name, locked):
        user = self.cell.auth.users.get(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        user.setLocked(locked)

    @adminapi
    def addUserRole(self, username, rolename):
        user = self.cell.auth.users.get(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        role = self.cell.auth.roles.get(rolename)
        if role is None:
            raise s_exc.NoSuchRole(role=rolename)

        user.addRole(rolename)

    @adminapi
    def delUserRole(self, username, rolename):

        user = self.cell.auth.users.get(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        role = self.cell.auth.roles.get(rolename)
        if role is None:
            raise s_exc.NoSuchRole(role=rolename)

        user.delRole(rolename)

    @adminapi
    def getAuthInfo(self, name):
        '''
        An admin only API endpoint for getting user info.
        '''
        item = self._getAuthItem(name)
        if item is None:
            return None

        return self._getAuthInfo(item)

    def _getAuthItem(self, name):
        # return user or role by name.
        user = self.cell.auth.users.get(name)
        if user is not None:
            return user

        role = self.cell.auth.roles.get(name)
        if role is not None:
            return role

        raise s_exc.NoSuchName(name=name)

    def _getAuthInfo(self, role):

        authtype = role.info.get('type')
        info = {
            'type': authtype,
            'admin': role.admin,
            'rules': role.info.get('rules', ()),
        }

        if authtype == 'user':
            info['locked'] = role.locked

            roles = []
            info['roles'] = roles

            for userrole in role.roles.values():
                roles.append(self._getAuthInfo(userrole))

        return (role.name, info)

class PassThroughApi(CellApi):
    '''
    Class that passes through methods made on it to its cell.
    '''
    allowed_methods = []  # type: ignore

    async def __anit__(self, cell, link):
        await CellApi.__anit__(self, cell, link)

        for f in self.allowed_methods:
            # N.B. this curious double nesting is due to Python's closure mechanism (f is essentially captured by name)
            def funcapply(f):
                def func(*args, **kwargs):
                    return getattr(cell, f)(*args, **kwargs)
                return func
            setattr(self, f, funcapply(f))

bootdefs = (

    ('auth:en', {'defval': False, 'doc': 'Set to True to enable auth for this cortex.'}),

    ('auth:admin', {'defval': None, 'doc': 'Set to <user>:<passwd> (local only) to bootstrap an admin.'}),

    ('hive', {'defval': None, 'doc': 'Set to a Hive telepath URL or list of URLs'}),

)

class Cell(s_base.Base, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.
    '''
    cellapi = CellApi

    # config options that are in all cells...
    confbase = ()
    confdefs = ()

    async def __anit__(self, dirn, readonly=False):

        await s_base.Base.__anit__(self)

        s_telepath.Aware.__init__(self)

        self.dirn = s_common.gendir(dirn)

        self.auth = None

        # each cell has a guid
        path = s_common.genpath(dirn, 'cell.guid')

        # generate a guid file if needed
        if not os.path.isfile(path):
            with open(path, 'w') as fd:
                fd.write(s_common.guid())

        # read our guid file
        with open(path, 'r') as fd:
            self.iden = fd.read().strip()

        boot = self._loadCellYaml('boot.yaml')
        self.boot = s_common.config(boot, bootdefs)

        conf = self._loadCellYaml('cell.yaml')
        self.conf = s_common.config(conf, self.confdefs + self.confbase)

        self.cmds = {}

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        self.cellname = self.boot.get('cell:name')
        if self.cellname is None:
            self.cellname = self.__class__.__name__

        await self._initCellAuth()
        await self._initCellSlab(readonly=readonly)
        await self._initCellHive()

    async def _initCellHive(self):

        hurl = self.conf.get('hive')

        if hurl is not None:
            self.hive = await s_hive.openurl(hurl)

        else:

            db = self.slab.initdb('hive')
            self.hive = await s_hive.SlabHive.anit(self.slab, db=db)
            self.onfini(self.hive.fini)

    #async def onTeleOpen(self, link, path):
        # TODO make a path resolver for layers/etc
        #if path == 'hive/auth'

    async def _initCellSlab(self, readonly=False):

        s_common.gendir(self.dirn, 'slabs')

        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        if not os.path.exists(path) and readonly:
            logger.warning('Creating a slab for a readonly cell.')
            _slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE)
            _slab.initdb('hive')
            await _slab.fini()

        self.slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE, readonly=readonly)
        self.onfini(self.slab.fini)

    async def _initCellAuth(self):

        if not self.boot.get('auth:en'):
            return

        # runtime import.  dep loop.
        import synapse.cells as s_cells

        authdir = s_common.gendir(self.dirn, 'auth')
        self.auth = await s_cells.init('auth', authdir)

        admin = self.boot.get('auth:admin')
        if admin is not None:

            name, passwd = admin.split(':')

            user = self.auth.users.get(name)
            if user is None:
                user = self.auth.addUser(name)
                logger.warning(f'adding admin user: {name} to {self.cellname}')

            user.setAdmin(True)
            user.setPasswd(passwd)

        self.onfini(self.auth.fini)

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    @classmethod
    def deploy(cls, dirn):
        # sub-classes may over-ride to do deploy initialization
        pass

    async def getTeleApi(self, link, mesg):

        if self.auth is None:
            return await self.cellapi.anit(self, link)

        user = self._getCellUser(link, mesg)

        link.set('cell:user', user)
        return await self.cellapi.anit(self, link)

    def getCellType(self):
        return self.__class__.__name__.lower()

    def getCellIden(self):
        return self.iden

    def _getCellUser(self, link, mesg):

        auth = mesg[1].get('auth')
        if auth is None:
            raise s_exc.AuthDeny(mesg='Unable to find cell user')

        name, info = auth

        user = self.auth.users.get(name)
        if user is None:
            raise s_exc.AuthDeny(mesg='User not present in link', user=name)

        # passwd None always fails...
        passwd = info.get('passwd')
        if not user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return user

    def initCellAuth(self):

        # To avoid import cycle
        import synapse.lib.auth as s_auth

        valu = self.boot.get('auth:en')
        if not valu:
            return

        url = self.boot.get('auth:url')
        if url is not None:
            self.auth = s_telepath.openurl(url)
            return

        # setup local auth

        dirn = s_common.gendir(self.dirn, 'auth')

        self.auth = s_auth.Auth(dirn)  # FIXME this is not imported, but would cause circular import

        # let them hard code an initial admin user:passwd
        admin = self.boot.get('auth:admin')
        if admin is not None:
            name, passwd = admin.split(':', 1)

            user = self.auth.getUser(name)
            if user is None:
                user = self.auth.addUser(name)

            user.setAdmin(True)
            user.setPasswd(passwd)

    def addCellCmd(self, name, func):
        '''
        Add a Cmdr() command to the cell.
        '''
        self.cmds[name] = func

    @contextlib.asynccontextmanager
    async def getLocalProxy(self):
        '''
        Creates a local telepath daemon, shares this object, and returns the telepath proxy of this object

        TODO:  currently, this will fini self if the created dmon is fini'd
        '''
        import synapse.daemon as s_daemon  # avoid import cycle
        with tempfile.TemporaryDirectory() as dirn:
            coredir = pathlib.Path(dirn, 'cells', 'core')
            if coredir.is_dir():
                ldir = s_common.gendir(coredir, 'layers')
                if self.alt_write_layer:
                    os.symlink(self.alt_write_layer, pathlib.Path(ldir, '000-default'))

            async with await s_daemon.Daemon.anit(dirn, conf={'listen': None}) as dmon:
                dmon.share('core', self)
                listenaddr = 'tcp://127.0.0.1:0'
                print(f'listing on local loopback: {listenaddr}')
                addr = await dmon.listen(listenaddr)
                prox = await s_telepath.openurl('tcp://127.0.0.1/core', port=addr[1])
                yield prox
