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
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.const as s_const
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.health as s_health
import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi
import synapse.lib.version as s_version
import synapse.lib.hiveauth as s_hiveauth

import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

SLAB_MAP_SIZE = 128 * s_const.mebibyte

'''
Base classes for the synapse "cell" microservice architecture.
'''
def adminapi(f):

    @functools.wraps(f)
    def func(*args, **kwargs):

        if args[0].user is not None and not args[0].user.isAdmin():
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
        sess = self.link.get('sess')  # type: s_daemon.Sess
        sess.user = user

    async def allowed(self, perm, default=None):
        '''
        Check if the user has the requested permission.

        Args:
            perm: permission path components to check
            default: Value returned if no value stored

        Examples:

            Form a path and check the permission from a remote proxy::

                perm = ('node:add', 'inet:ipv4')
                allowed = await prox.allowed(perm)
                if allowed:
                    dostuff()

        Returns:
            Optional[bool]: True if the user has permission, False if explicitly denied, None if no entry
        '''
        return self.user.allowed(perm, default=default)

    async def _reqUserAllowed(self, perm):
        '''
        Helper method that subclasses can use for user permission checking.

        Args:
            perm: permission path components to check

        Notes:
            This can be used to require a permission; and will throw an exception if the permission is not allowed.

        Examples:

            Implement an API that requires a user to have a specific permission in order to execute it::

                async def makeWidget(self, wvalu, wtype):
                    # This will throw if the user doesn't have the appropriate widget permission
                    await self._reqUserAllowed(('widget', wtype))
                    return await self.cell.makeWidget((wvalu, wtype))

        Returns:
            None: This API does not return anything. It only throws an exception on failure.

        Raises:
            s_exc.AuthDeny: If the permission is not allowed.

        '''
        if not await self.allowed(perm):
            perm = '.'.join(perm)
            mesg = f'User must have permission {perm}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.user.name)

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
        if not self.user.isAdmin():
            mesg = 'setCellUser() caller must be admin.'
            raise s_exc.AuthDeny(mesg=mesg)

        user = self.cell.auth.user(iden)
        if user is None:
            raise s_exc.NoSuchUser(iden=iden)

        self.user = user
        self.link.get('sess').user = user
        return True

    async def ps(self):

        retn = []

        isallowed = await self.allowed(('task', 'get'))

        for task in self.cell.boss.ps():
            if (task.user == self.user) or isallowed:
                retn.append(task.pack())

        return retn

    async def kill(self, iden):
        perm = ('task', 'del')
        isallowed = await self.allowed(perm)

        logger.info(f'User [{self.user.name}] Requesting task kill: {iden}')
        task = self.cell.boss.get(iden)
        if task is None:
            logger.info(f'Task does not exist: {iden}')
            return False

        if (task.user == self.user) or isallowed:
            logger.info(f'Killing task: {iden}')
            await task.kill()
            logger.info(f'Task killed: {iden}')
            return True

        perm = '.'.join(perm)
        raise s_exc.AuthDeny(mesg=f'User must have permission {perm} or own the task',
                             task=iden, user=str(self.user), perm=perm)

    @adminapi
    async def addAuthUser(self, name):

        # Note:  change handling is implemented inside auth
        user = await self.cell.auth.addUser(name)
        await self.cell.fire('user:mod', act='adduser', name=name)
        return user.pack()

    @adminapi
    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.cell.dyncall(iden, todo, gatekeys=gatekeys)

    @adminapi
    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.cell.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    @adminapi
    async def delAuthUser(self, name):
        await self.cell.auth.delUser(name)
        await self.cell.fire('user:mod', act='deluser', name=name)

    @adminapi
    async def addAuthRole(self, name):
        role = await self.cell.auth.addRole(name)
        await self.cell.fire('user:mod', act='addrole', name=name)
        return role.pack()

    @adminapi
    async def delAuthRole(self, name):
        await self.cell.auth.delRole(name)
        await self.cell.fire('user:mod', act='delrole', name=name)

    @adminapi
    async def getAuthUsers(self, archived=False):
        '''
        Args:
            archived (bool):  If true, list all users, else list non-archived users
        '''
        return [u.name for u in self.cell.auth.users() if archived or not u.info.get('archived')]

    @adminapi
    async def getAuthRoles(self):
        return [r.name for r in self.cell.auth.roles()]

    @adminapi
    async def addUserRule(self, name, rule, indx=None, gateiden=None):
        user = await self.cell.auth.reqUserByName(name)
        retn = await user.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    @adminapi
    async def addRoleRule(self, name, rule, indx=None, gateiden=None):
        role = await self.cell.auth.reqRoleByName(name)
        retn = await role.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    @adminapi
    async def delUserRule(self, name, rule, gateiden=None):
        user = await self.cell.auth.reqUserByName(name)
        return await user.delRule(rule, gateiden=gateiden)

    @adminapi
    async def delRoleRule(self, name, rule, gateiden=None):
        role = await self.cell.auth.reqRoleByName(name)
        return await role.delRule(rule, gateiden=gateiden)

    @adminapi
    async def setUserAdmin(self, name, admin, gateiden=None):
        user = await self.cell.auth.reqUserByName(name)
        await user.setAdmin(admin, gateiden=gateiden)

    @adminapi
    async def setRoleAdmin(self, name, admin, gateiden=None):
        role = await self.cell.auth.reqRoleByName(name)
        await role.setAdmin(admin, gateiden=gateiden)

    @adminapi
    async def getAuthInfo(self, name):
        s_common.deprecated('getAuthInfo')
        user = await self.cell.auth.getUserByName(name)
        if user is not None:
            info = user.pack()
            info['roles'] = [self.cell.auth.role(r).name for r in info['roles']]
            return info

        role = await self.cell.auth.getRoleByName(name)
        if role is not None:
            return role.pack()

        raise s_exc.NoSuchName(name=name)

    @adminapi
    async def addAuthRule(self, name, rule, indx=None, gateiden=None):
        s_common.deprecated('addAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.addRule(rule, indx=indx, gateiden=gateiden)

    @adminapi
    async def delAuthRule(self, name, rule, gateiden=None):
        s_common.deprecated('delAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.delRule(rule, gateiden=gateiden)

    @adminapi
    async def setAuthAdmin(self, name, isadmin):
        s_common.deprecated('setAuthAdmin')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.setAdmin(isadmin)

    async def setUserPasswd(self, name, passwd):
        user = await self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)
        if not (self.user.isAdmin() or self.user.iden == user.iden):
            raise s_exc.AuthDeny(mesg='Cannot change user password.', user=user.name)

        await user.setPasswd(passwd)
        await self.cell.fire('user:mod', act='setpasswd', name=name)

    @adminapi
    async def setUserLocked(self, name, locked):
        user = await self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setLocked(locked)
        await self.cell.fire('user:mod', act='locked', name=name, locked=locked)

    @adminapi
    async def setUserArchived(self, name, archived):
        user = await self.cell.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(user=name)

        await user.setArchived(archived)
        await self.cell.fire('user:mod', act='archived', name=name, archived=archived)

    @adminapi
    async def addUserRole(self, username, rolename):
        user = await self.cell.auth.getUserByName(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        await user.grant(rolename)
        await self.cell.fire('user:mod', act='grant', name=username, role=rolename)

    @adminapi
    async def delUserRole(self, username, rolename):

        user = await self.cell.auth.getUserByName(username)
        if user is None:
            raise s_exc.NoSuchUser(user=username)

        await user.revoke(rolename)
        await self.cell.fire('user:mod', act='revoke', name=username, role=rolename)

    async def getUserInfo(self, name):
        user = await self.cell.auth.reqUserByName(name)
        if self.user.isAdmin() or self.user.iden == user.iden:
            info = user.pack()
            info['roles'] = [self.cell.auth.role(r).name for r in info['roles']]
            return info

        mesg = 'getUserInfo denied for non-admin and non-self'
        raise s_exc.AuthDeny(mesg=mesg)

    async def getRoleInfo(self, name):
        role = await self.cell.auth.reqRoleByName(name)
        if self.user.isAdmin() or role.iden in self.user.info.get('roles', ()):
            return role.pack()

        mesg = 'getRoleInfo denied for non-admin and non-member'
        raise s_exc.AuthDeny(mesg=mesg)

    async def getHealthCheck(self):
        await self._reqUserAllowed(('health',))
        return await self.cell.getHealthCheck()

    @adminapi
    async def getDmonSessions(self):
        return await self.cell.getDmonSessions()

    @adminapi
    async def listHiveKey(self, path=None):
        return await self.cell.listHiveKey(path=path)

    @adminapi
    async def getHiveKey(self, path):
        return await self.cell.getHiveKey(path)

    @adminapi
    async def setHiveKey(self, path, valu):
        return await self.cell.setHiveKey(path, valu)

    @adminapi
    async def popHiveKey(self, path):
        return await self.cell.popHiveKey(path)

    @adminapi
    async def saveHiveTree(self, path=()):
        return await self.cell.saveHiveTree(path=path)

class Cell(s_nexus.Pusher, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.
    '''
    cellapi = CellApi

    confdefs = {}  # type: ignore  # This should be a JSONSchema properties list for an object.
    confbase = {
        'auth:passwd': {
            'description': 'Set to <passwd> (local only) to bootstrap the root user password.',
            'type': 'string'
        },
        'hive': {
            'description': 'Set to a Hive telepath URL.',
            'type': 'string'
        },
        'logchanges': {
            'default': False,
            'description': 'Record all changes to the cell.  Required for mirroring.',
            'type': 'boolean'
        },
    }

    async def __anit__(self, dirn, conf=None, readonly=False, *args, **kwargs):

        s_telepath.Aware.__init__(self)

        self.dirn = s_common.gendir(dirn)

        self.auth = None
        self.inaugural = False
        self.remote_hive = False

        # each cell has a guid
        path = s_common.genpath(dirn, 'cell.guid')

        # generate a guid file if needed
        if not os.path.isfile(path):
            self.inaugural = True
            with open(path, 'w') as fd:
                fd.write(s_common.guid())

        # read our guid file
        with open(path, 'r') as fd:
            self.iden = fd.read().strip()

        if conf is None:
            conf = {}

        self.conf = self._initCellConf(conf)
        self.dologging = self.conf.get('layers:logedits')

        await s_nexus.Pusher.__anit__(self, self.iden)

        await self._initCellDmon()

        self.cmds = {}
        self.sessions = {}

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        await self._initCellSlab(readonly=readonly)

        self.setNexsRoot(await self._initNexsRoot())

        self.hive = await self._initCellHive()

        # self.cellinfo, a HiveDict for general purpose persistent storage
        node = await self.hive.open(('cellinfo',))
        self.cellinfo = await node.dict()
        self.onfini(node)

        if self.inaugural:
            await self.cellinfo.set('synapse:version', s_version.version)

        synvers = self.cellinfo.get('synapse:version')
        if synvers is None or synvers < s_version.version:
            await self.cellinfo.set('synapse:version', s_version.version)

        self.auth = await self._initCellAuth()

        # self.cellinfo, a HiveDict for general purpose persistent storage
        node = await self.hive.open(('cellinfo',))
        self.cellinfo = await node.dict()
        self.onfini(node)

        if self.inaugural:
            await self.cellinfo.set('synapse:version', s_version.version)

        synvers = self.cellinfo.get('synapse:version')
        if synvers is None or synvers < s_version.version:
            await self.cellinfo.set('synapse:version', s_version.version)

        self.auth = await self._initCellAuth()

        auth_passwd = self.conf.get('auth:passwd')
        if auth_passwd is not None:
            if self.remote_hive:
                # This is a invalid configuration - bail
                raise s_exc.BadConfValu(mesg='Cannot set root password on a cell configured to use a remote hive.',
                                        name='auth:passwd')
            user = await self.auth.getUserByName('root')
            await user.setPasswd(auth_passwd)

        await self._initCellHttp()

        self._health_funcs = []
        self.addHealthFunc(self._cellHealth)

        async def fini():
            [await s.fini() for s in self.sessions.values()]

        self.onfini(fini)

        self.dynitems = {
            'auth': self.auth,
            'cell': self
        }

    async def _initNexsRoot(self):
        nexsroot = await s_nexus.NexsRoot.anit(self.dirn, dologging=self.dologging)
        self.onfini(nexsroot.fini)
        return nexsroot

    async def dyniter(self, iden, todo, gatekeys=()):

        for useriden, perm, gateiden in gatekeys:
            (await self.auth.reqUser(useriden)).confirm(perm, gateiden=gateiden)

        item = self.dynitems.get(iden)
        name, args, kwargs = todo

        meth = getattr(item, name)
        async for item in meth(*args, **kwargs):
            yield item

    async def dyncall(self, iden, todo, gatekeys=()):

        for useriden, perm, gateiden in gatekeys:
            (await self.auth.reqUser(useriden)).confirm(perm, gateiden=gateiden)

        item = self.dynitems.get(iden)
        if item is None:
            raise s_exc.NoSuchIden(mesg=iden)

        name, args, kwargs = todo
        meth = getattr(item, name)

        return await s_coro.ornot(meth, *args, **kwargs)

    async def getConfOpt(self, name):
        return self.conf.get(name)

    def _getSessInfo(self, iden):
        return self.sessstor.gen(iden)

    def getUserName(self, iden, defv='<unknown>'):
        '''
        Translate the user iden to a user name.
        '''
        # since this pattern is so common, utilitizing...
        user = self.auth.user(iden)
        if user is None:
            return defv
        return user.name

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
        self._initCellHttpApis()

    def _initCellHttpApis(self):

        self.addHttpApi('/api/v1/login', s_httpapi.LoginV1, {'cell': self})
        self.addHttpApi('/api/v1/healthcheck', s_httpapi.HealthCheckV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/users', s_httpapi.AuthUsersV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/roles', s_httpapi.AuthRolesV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/adduser', s_httpapi.AuthAddUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/addrole', s_httpapi.AuthAddRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/delrole', s_httpapi.AuthDelRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/user/(.*)', s_httpapi.AuthUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/role/(.*)', s_httpapi.AuthRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/password/(.*)', s_httpapi.AuthUserPasswdV1, {'cell': self})
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
        except Exception:  # pragma: no cover
            logging.exception(f'Unknown dmon listen error.')
            raise

        self.onfini(self.dmon.fini)

    async def _initCellHive(self):

        hurl = self.conf.get('hive')
        if hurl is not None:
            self.remote_hive = True
            return await s_hive.openurl(hurl)

        isnew = not self.slab.dbexists('hive')

        db = self.slab.initdb('hive')
        hive = await s_hive.SlabHive.anit(self.slab, db=db, nexsroot=self.nexsroot)
        self.onfini(hive)

        if isnew:
            path = os.path.join(self.dirn, 'hiveboot.yaml')
            if os.path.isfile(path):
                tree = s_common.yamlload(path)
                if tree is not None:
                    await hive.loadHiveTree(tree)

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
        auth = await s_hiveauth.Auth.anit(node)

        self.onfini(auth.fini)
        return auth

    @contextlib.asynccontextmanager
    async def getLocalProxy(self, share='*', user='root'):
        url = self.getLocalUrl(share=share, user=user)
        prox = await s_telepath.openurl(url)
        yield prox

    def getLocalUrl(self, share='*', user='root'):
        return f'cell://{user}@{self.dirn}:{share}'

    def _initCellConf(self, conf):
        if isinstance(conf, dict):
            conf = s_config.Config.getConfFromCell(self, conf=conf)
        for k, v in self._loadCellYaml('cell.yaml').items():
            conf.setdefault(k, v)
        conf.reqConfValid()
        return conf

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    async def getTeleApi(self, link, mesg, path):

        # if auth is disabled or it's a unix socket, they're root.
        if link.get('unix'):
            name = 'root'
            auth = mesg[1].get('auth')
            if auth is not None:
                name, info = auth

            user = await self.auth.getUserByName(name)
            if user is None:
                raise s_exc.NoSuchUser(name=name)

        else:
            user = await self._getCellUser(mesg)

        return await self.getCellApi(link, user, path)

    async def getCellApi(self, link, user, path):
        return await self.cellapi.anit(self, link, user)

    @classmethod
    def getCellType(cls):
        return cls.__name__.lower()

    def getCellIden(self):
        return self.iden

    async def _getCellUser(self, mesg):

        auth = mesg[1].get('auth')
        if auth is None:
            raise s_exc.AuthDeny(mesg='Unable to find cell user')

        name, info = auth

        user = await self.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name, mesg=f'No such user: {name}.')

        # passwd None always fails...
        passwd = info.get('passwd')
        if not user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return user

    async def getHealthCheck(self):
        health = s_health.HealthCheck(self.getCellIden())
        for func in self._health_funcs:
            await func(health)
        return health.pack()

    def addHealthFunc(self, func):
        '''Register a callback function to get a HealthCheck object.'''
        self._health_funcs.append(func)

    async def _cellHealth(self, health):
        pass

    async def getDmonSessions(self):
        return await self.dmon.getSessInfo()

    # ----- Change distributed Auth methods ----

    async def listHiveKey(self, path=None):
        if path is None:
            path = ()
        items = self.hive.dir(path)
        if items is None:
            return None
        return [item[0] for item in items]

    async def getHiveKey(self, path):
        '''
        Get the value of a key in the cell default hive
        '''
        return await self.hive.get(path)

    async def setHiveKey(self, path, valu):
        '''
        Set or change the value of a key in the cell default hive
        '''
        return await self.hive.set(path, valu, nexs=True)

    async def popHiveKey(self, path):
        '''
        Remove and return the value of a key in the cell default hive.

        Note:  this is for expert emergency use only.
        '''
        return await self.hive.pop(path, nexs=True)

    async def saveHiveTree(self, path=()):
        return await self.hive.saveHiveTree(path=path)

    async def loadHiveTree(self, tree, path=(), trim=False):
        '''
        Note:  this is for expert emergency use only.
        '''
        return await self._push('hive:loadtree', tree, path, trim)

    @s_nexus.Pusher.onPush('hive:loadtree')
    async def _onLoadHiveTree(self, tree, path, trim):
        return await self.hive.loadHiveTree(tree, path=path, trim=trim)
