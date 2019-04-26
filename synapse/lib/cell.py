import os
import ssl
import socket
import asyncio
import logging
import functools
import contextlib

import tornado.web as t_web

import synapse.exc as s_exc

import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive
import synapse.lib.compat as s_compat
import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

SLAB_MAP_SIZE = 128 * s_const.mebibyte

'''
Base classes for the synapse "cell" microservice architecture.
'''
def adminapi(f):

    @functools.wraps(f)
    def func(*args, **kwargs):

        if args[0].user is not None and not args[0].user.admin:
            raise s_exc.AuthDeny(mesg='User is not an admin.',
                                 user=args[0].user.name)

        logger.info('Executing [%s] as [%s] with args [%s][%s]',
                    f.__qualname__, args[0].user.name, args[1:], kwargs)

        return f(*args, **kwargs)

    func.__syn_wrapped__ = 'adminapi'

    return func

class CellApi(s_base.Base):

    async def __anit__(self, cell, link, user):
        await s_base.Base.__anit__(self)
        self.cell = cell
        self.link = link
        assert user
        self.user = user

    def getCellType(self):
        return self.cell.getCellType()

    def getCellIden(self):
        return self.cell.getCellIden()

    def getCellUser(self):
        return self.user.pack()

    def setCellUser(self, iden):
        '''
        Switch to another user (admin only).

        This API allows remote admin/service accounts
        to impersonate a user.  Used mostly by services
        that manage their own authentication/sessions.
        '''
        if not self.user.admin:
            mesg = 'setCellUser() caller must be admin.'
            raise s_exc.AuthDeny(mesg=mesg)

        user = self.cell.auth.user(iden)
        if user is None:
            raise s_exc.NoSuchUser(iden=iden)

        self.user = user
        return True

    async def ps(self):

        retn = []

        admin = self.user.admin

        for synt in self.cell.boss.ps():
            if admin or synt.user == self.user:
                retn.append(synt.pack())

        return retn

    async def kill(self, iden):

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

    async def listHiveKey(self, path=None):
        if path is None:
            path = ()
        perm = ('hive:get',) + path
        self.user.allowed(perm)
        items = self.cell.hive.dir(path)
        if items is None:
            return None
        return [item[0] for item in items]

    async def getHiveKey(self, path):
        ''' Get the value of a key in the cell default hive '''
        perm = ('hive:get',) + path
        self.user.allowed(perm)
        return await self.cell.hive.get(path)

    async def setHiveKey(self, path, value):
        ''' Set or change the value of a key in the cell default hive '''
        perm = ('hive:set',) + path
        self.user.allowed(perm)
        return await self.cell.hive.set(path, value)

    async def popHiveKey(self, path):
        ''' Remove and return the value of a key in the cell default hive '''
        perm = ('hive:pop',) + path
        self.user.allowed(perm)
        return await self.cell.hive.pop(path)

    @adminapi
    async def addAuthUser(self, name):
        user = await self.cell.auth.addUser(name)
        return user.pack()

    @adminapi
    async def delAuthUser(self, name):
        user = await self.cell.auth.delUser(name)
        return user.pack()

    @adminapi
    async def addAuthRole(self, name):
        role = await self.cell.auth.addRole(name)
        return role.pack()

    @adminapi
    async def delAuthRole(self, name):
        role = await self.cell.auth.delRole(name)
        return role.pack()

    @adminapi
    async def getAuthUsers(self, archived=False):
        if archived:
            return [u.name for u in self.cell.auth.users()]
        return [u.name for u in self.cell.auth.users() if not u.info.get('archived')]

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
        return await item.delRule(indx)

    @adminapi
    async def setAuthAdmin(self, name, admin):
        '''
        Set the admin status of the given user/role.
        '''
        item = self._getAuthItem(name)
        await item.setAdmin(admin)

    @adminapi
    async def setUserPasswd(self, name, passwd):
        user = self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setPasswd(passwd)

    @adminapi
    async def setUserLocked(self, name, locked):
        user = self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setLocked(locked)

    @adminapi
    async def setUserArchived(self, name, archived):
        user = self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setArchived(archived)

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
        pack = item.pack()

        # translate role guids to names for back compat
        if pack.get('type') == 'user':
            pack['roles'] = [self.cell.auth.role(r).name for r in pack['roles']]

        return (name, pack)

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

    async def __anit__(self, cell, link, user):
        await CellApi.__anit__(self, cell, link, user)

        for f in self.allowed_methods:
            # N.B. this curious double nesting is due to Python's closure mechanism (f is essentially captured by name)
            def funcapply(f):
                def func(*args, **kwargs):
                    return getattr(cell, f)(*args, **kwargs)
                return func
            setattr(self, f, funcapply(f))

bootdefs = (

    ('insecure', {'defval': False, 'doc': 'Disable all authentication checking. (INSECURE!)'}),

    ('auth:admin', {'defval': None, 'doc': 'Set to <user>:<passwd> (local only) to bootstrap an admin.'}),

    ('hive', {'defval': None, 'doc': 'Set to a Hive telepath URL or list of URLs'}),

)

class Cell(s_base.Base, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.
    '''
    cellapi = CellApi

    # config options that are in all cells...
    confdefs = ()
    confbase = ()

    async def __anit__(self, dirn, conf=None, readonly=False):

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

        await self._initCellDmon()

        if conf is None:
            conf = {}

        [conf.setdefault(k, v) for (k, v) in self._loadCellYaml('cell.yaml').items()]

        self.conf = s_common.config(conf, self.confdefs + self.confbase)

        self.cmds = {}
        self.insecure = self.boot.get('insecure', False)

        self.sessions = {}
        self.httpsonly = self.conf.get('https:only', False)

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        await self._initCellSlab(readonly=readonly)

        self.hive = await self._initCellHive()
        self.auth = await self._initCellAuth()

        # check and migrate old cell auth
        oldauth = s_common.genpath(self.dirn, 'auth')
        if os.path.isdir(oldauth):
            await s_compat.cellAuthToHive(oldauth, self.auth)
            os.rename(oldauth, oldauth + '.old')

        admin = self.boot.get('auth:admin')
        if admin is not None:

            name, passwd = admin.split(':', 1)

            user = self.auth.getUserByName(name)
            if user is None:
                user = await self.auth.addUser(name)

            await user.setAdmin(True)
            await user.setPasswd(passwd)
            self.insecure = False

        await self._initCellHttp()

        async def fini():
            [await s.fini() for s in self.sessions.values()]

        self.onfini(fini)

    def _getSessInfo(self, iden):
        return self.sessstor.gen(iden)

    async def genHttpSess(self, iden):

        # TODO age out http sessions
        sess = self.sessions.get(iden)
        if sess is not None:
            return sess

        sess = await s_httpapi.Sess.anit(self, iden)
        self.sessions[iden] = sess

        return sess

    async def addHttpsPort(self, port, host='0.0.0.0', sslctx=None):

        addr = socket.gethostbyname(host)

        if sslctx is None:

            pkeypath = os.path.join(self.dirn, 'sslkey.pem')
            certpath = os.path.join(self.dirn, 'sslcert.pem')

            if not os.path.isfile(certpath):
                logger.warning('NO CERTIFICATE FOUND! generating self-signed certificate.')
                with s_common.getTempDir() as dirn:
                    cdir = s_certdir.CertDir(dirn)
                    pkey, cert = cdir.genHostCert('cortex')
                    cdir.savePkeyPem(pkey, pkeypath)
                    cdir.saveCertPem(cert, certpath)

            sslctx = self.initSslCtx(certpath, pkeypath)

        serv = self.wapp.listen(port, address=addr, ssl_options=sslctx)
        self.httpds.append(serv)
        return list(serv._sockets.values())[0].getsockname()

    async def addHttpPort(self, port, host='0.0.0.0'):
        addr = socket.gethostbyname(host)
        serv = self.wapp.listen(port, address=addr)
        self.httpds.append(serv)
        return list(serv._sockets.values())[0].getsockname()

    def initSslCtx(self, certpath, keypath):

        sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        if not os.path.isfile(keypath):
            raise s_exc.NoSuchFile(name=keypath)

        if not os.path.isfile(certpath):
            raise s_exc.NoSuchFile(name=certpath)

        sslctx.load_cert_chain(certpath, keypath)
        return sslctx

    async def _initCellHttp(self):

        self.httpds = []
        self.sessstor = s_lmdbslab.GuidStor(self.slab, 'http:sess')

        async def fini():
            for http in self.httpds:
                http.stop()

        self.onfini(fini)

        # Generate/Load a Cookie Secret
        secpath = os.path.join(self.dirn, 'cookie.secret')
        if not os.path.isfile(secpath):
            with s_common.genfile(secpath) as fd:
                fd.write(s_common.guid().encode('utf8'))

        with s_common.getfile(secpath) as fd:
            secret = fd.read().decode('utf8')

        opts = {
            'cookie_secret': secret,
            'websocket_ping_interval': 10
        }

        self.wapp = t_web.Application(**opts)

        self.addHttpApi('/api/v1/login', s_httpapi.LoginV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/users', s_httpapi.AuthUsersV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/roles', s_httpapi.AuthRolesV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/adduser', s_httpapi.AuthAddUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/addrole', s_httpapi.AuthAddRoleV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/delrole', s_httpapi.AuthDelRoleV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/user/(.*)', s_httpapi.AuthUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/role/(.*)', s_httpapi.AuthRoleV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/grant', s_httpapi.AuthGrantV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/revoke', s_httpapi.AuthRevokeV1, {'cell': self})

    def addHttpApi(self, path, ctor, info):
        self.wapp.add_handlers('.*', (
            (path, ctor, info),
        ))

    async def _initCellDmon(self):
        # start a unix local socket daemon listener
        sockpath = os.path.join(self.dirn, 'sock')
        sockurl = f'unix://{sockpath}'

        self.dmon = await s_daemon.Daemon.anit()
        self.dmon.share('*', self)

        try:
            await self.dmon.listen(sockurl)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except OSError as e:
            logger.error(f'Failed to listen on unix socket at: [{sockpath}][{e}]')
            logger.error('LOCAL UNIX SOCKET WILL BE UNAVAILABLE')
        except Exception as e:  # pragma: no cover
            logging.exception('Unknown dmon listen error.')
            raise

        self.onfini(self.dmon.fini)

    async def _initCellHive(self):

        hurl = self.conf.get('hive')
        if hurl is not None:
            return await s_hive.openurl(hurl)

        db = self.slab.initdb('hive')
        hive = await s_hive.SlabHive.anit(self.slab, db=db)
        self.onfini(hive)
        return hive

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
    async def getLocalProxy(self, share='*', user='root'):
        url = self.getLocalUrl(share=share, user=user)
        prox = await s_telepath.openurl(url)
        yield prox

    def getLocalUrl(self, share='*', user='root'):
        return f'cell://{user}@{self.dirn}:{share}'

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    async def getTeleApi(self, link, mesg, path):

        # if auth is disabled or it's a unix socket, they're root.
        if self.insecure or link.get('unix'):
            name = 'root'
            auth = mesg[1].get('auth')
            if auth is not None:
                name, info = auth

            user = self.auth.getUserByName(name)
            if user is None:
                raise s_exc.NoSuchUser(name=name)

        else:
            user = self._getCellUser(mesg)

        return await self.getCellApi(link, user, path)

    async def getCellApi(self, link, user, path):
        return await self.cellapi.anit(self, link, user)

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
