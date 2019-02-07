import os
import logging
import pathlib
import tempfile
import contextlib

import synapse.exc as s_exc

import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive
import synapse.lib.compat as s_compat

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

SLAB_MAP_SIZE = 128 * s_const.mebibyte

'''
Base classes for the synapse "cell" microservice architecture.
'''
def adminapi(f):

    def func(*args, **kwargs):

        if args[0].user is not None and not args[0].user.admin:
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

    def getCellUser(self):
        return self.user.pack()

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
    async def listHiveKey(self, path=None):
        if path is None:
            path = ()
        items = self.cell.hive.dir(path)
        if items is None:
            return None
        return [item[0] for item in items]

    @adminapi
    async def getHiveKey(self, path):
        ''' Get the value of a key in the cell default hive '''
        return await self.cell.hive.get(path)

    @adminapi
    async def setHiveKey(self, path, value):
        ''' Set or change the value of a key in the cell default hive '''
        return await self.cell.hive.set(path, value)

    @adminapi
    async def popHiveKey(self, path):
        ''' Remove and return the value of a key in the cell default hive '''
        return await self.cell.hive.pop(path)

    @adminapi
    async def addAuthUser(self, name):
        await self.cell.auth.addUser(name)

    @adminapi
    async def addAuthRole(self, name):
        await self.cell.auth.addRole(name)

    @adminapi
    async def getAuthUsers(self):
        return [u.name for u in self.cell.auth.users()]

    @adminapi
    async def getAuthRoles(self):
        return [r.name for r in self.cell.auth.roles()]

    @adminapi
    async def addAuthRule(self, name, rule, indx=None):
        item = self._getAuthItem(name)
        return await item.addRule(rule, indx=indx)

    @adminapi
    async def delAuthRule(self, name, indx):
        item = self._getAuthItem(name)
        return item.delRule(indx)

    @adminapi
    async def setAuthAdmin(self, name, admin):
        '''
        Set the admin status of the given user/role.
        '''
        item = self._getAuthItem(name)
        item.setAdmin(admin)

    @adminapi
    async def setUserPasswd(self, name, passwd):
        user = self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        user.setPasswd(passwd)

    @adminapi
    async def setUserLocked(self, name, locked):
        user = self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setLocked(locked)

    @adminapi
    async def addUserRole(self, username, rolename):
        user = self.cell.auth.getUserByName(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        await user.grant(rolename)

    @adminapi
    async def delUserRole(self, username, rolename):

        user = self.cell.auth.getUserByName(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        await user.revoke(rolename)

    @adminapi
    async def getAuthInfo(self, name):
        '''
        An admin only API endpoint for getting user info.
        '''
        item = self._getAuthItem(name)
        return (name, item.pack())

    def _getAuthItem(self, name):
        user = self.cell.auth.getUserByName(name)
        if user is not None:
            return user

        role = self.cell.auth.getRoleByName(name)
        if role is not None:
            return role

        raise s_exc.NoSuchName(name=name)

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

        # start a unix local socket daemon listener
        sockpath = os.path.join(self.dirn, 'sock')

        dmonconf = {'listen': f'unix://{sockpath}'}
        self.dmon = await s_daemon.Daemon.anit(conf=dmonconf)
        self.dmon.share('*', self)

        self.onfini(self.dmon.fini)

        conf = self._loadCellYaml('cell.yaml')
        self.conf = s_common.config(conf, self.confdefs + self.confbase)

        self.cmds = {}
        self.insecure = False

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        await self._initCellSlab(readonly=readonly)

        self.hive = await self._initCellHive()

        self.insecure = not self.boot.get('auth:en')

        self.auth = await self._initCellAuth()

        # check and migrate old cell auth
        oldauth = s_common.genpath(self.dirn, 'auth')
        if os.path.isdir(oldauth):
            await s_compat.cellAuthToHive(oldauth, self.auth)
            os.path.rename(oldauth, oldauth + '.old')

        admin = self.boot.get('auth:admin')
        if admin is not None:

            name, passwd = admin.split(':', 1)

            user = self.auth.getUserByName(name)
            if user is None:
                user = await auth.addUser(name)

            await user.setAdmin(True)
            await user.setPasswd(passwd)

    async def _initCellHive(self):

        hurl = self.conf.get('hive')
        if hurl is not None:
            return await s_hive.openurl(hurl)

        db = self.slab.initdb('hive')
        return await s_hive.SlabHive.anit(self.slab, db=db)

    # async def onTeleOpen(self, link, path):
        # TODO make a path resolver for layers/etc
        # if path == 'hive/auth'

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
        node = await self.hive.open(('auth',))
        auth = await s_hive.HiveAuth.anit(node)

        self.onfini(auth.fini)
        return auth

    @contextlib.asynccontextmanager
    async def getCellProxy(self):
        prox = await s_telepath.openurl('cell://', path=self.dirn)
        yield prox

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

        # if auth is disabled or it's a unix socket, they're root.
        if self.insecure or link.get('unix'):
            user = self.auth.getUserByName('root')

        else:
            user = self._getCellUser(mesg)

        link.set('cell:user', user)
        return await self.cellapi.anit(self, link)

    def getCellType(self):
        return self.__class__.__name__.lower()

    def getCellIden(self):
        return self.iden

    def _getCellUser(self, mesg):

        auth = mesg[1].get('auth')
        if auth is None:
            raise s_exc.AuthDeny(mesg='Unable to find cell user')

        name, info = auth

        user = self.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name, mesg=f'No such user: {name}.')

        # passwd None always fails...
        passwd = info.get('passwd')
        if not user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return user

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
                addr = await dmon.listen('tcp://127.0.0.1:0')
                prox = await s_telepath.openurl('tcp://127.0.0.1/core', port=addr[1])
                yield prox
