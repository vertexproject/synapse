import os
import ssl
import socket
import asyncio
import logging
import argparse
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
import synapse.lib.output as s_output
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

def adminapi(log=False):
    '''
    Decorator for CellApi (and subclasses) for requiring a method to be called only by an admin user.

    Args:
        log (bool): If set to True, log the user, function and arguments.
    '''

    def decrfunc(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            if args[0].user is not None and not args[0].user.isAdmin():
                raise s_exc.AuthDeny(mesg='User is not an admin.',
                                     user=args[0].user.name)
            if log:
                logger.info('Executing [%s] as [%s] with args [%s][%s]',
                            func.__qualname__, args[0].user.name, args[1:], kwargs)

            return func(*args, **kwargs)

        wrapped.__syn_wrapped__ = 'adminapi'

        return wrapped

    return decrfunc


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

    @adminapi(log=True)
    async def addUser(self, name, passwd=None, email=None):
        return await self.cell.addUser(name, passwd=passwd, email=email)

    @adminapi(log=True)
    async def delUser(self, iden):
        return await self.cell.delUser(iden)

    @adminapi(log=True)
    async def addRole(self, name):
        return await self.cell.addRole(name)

    @adminapi(log=True)
    async def delRole(self, iden):
        return await self.cell.delRole(iden)

    @adminapi()
    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.cell.dyncall(iden, todo, gatekeys=gatekeys)

    @adminapi()
    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.cell.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    @adminapi()
    async def issue(self, nexsiden: str, event: str, args, kwargs, meta=None):
        '''
        Note:  this swallows exceptions and return values.  It is expected that the nexus _followerLoop would be the
        return path
        '''
        try:
            await self.cell.nexsroot.issue(nexsiden, event, args, kwargs, meta)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    @adminapi(log=True)
    async def delAuthUser(self, name):
        await self.cell.auth.delUser(name)
        await self.cell.fire('user:mod', act='deluser', name=name)

    @adminapi(log=True)
    async def addAuthRole(self, name):
        role = await self.cell.auth.addRole(name)
        await self.cell.fire('user:mod', act='addrole', name=name)
        return role.pack()

    @adminapi(log=True)
    async def delAuthRole(self, name):
        await self.cell.auth.delRole(name)
        await self.cell.fire('user:mod', act='delrole', name=name)

    @adminapi()
    async def getAuthUsers(self, archived=False):
        '''
        Args:
            archived (bool):  If true, list all users, else list non-archived users
        '''
        return await self.cell.getAuthUsers(archived=archived)

    @adminapi()
    async def getAuthRoles(self):
        return await self.cell.getAuthRoles()

    @adminapi(log=True)
    async def addUserRule(self, iden, rule, indx=None, gateiden=None):
        return await self.cell.addUserRule(iden, rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def setUserRules(self, iden, rules, gateiden=None):
        return await self.cell.setUserRules(iden, rules, gateiden=gateiden)

    @adminapi(log=True)
    async def setRoleRules(self, iden, rules, gateiden=None):
        return await self.cell.setRoleRules(iden, rules, gateiden=gateiden)

    @adminapi(log=True)
    async def addRoleRule(self, iden, rule, indx=None, gateiden=None):
        return await self.cell.addRoleRule(iden, rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def delUserRule(self, iden, rule, gateiden=None):
        return await self.cell.delUserRule(iden, rule, gateiden=gateiden)

    @adminapi(log=True)
    async def delRoleRule(self, iden, rule, gateiden=None):
        return await self.cell.delRoleRule(iden, rule, gateiden=gateiden)

    @adminapi(log=True)
    async def setUserAdmin(self, iden, admin, gateiden=None):
        return await self.cell.setUserAdmin(iden, admin, gateiden=gateiden)

    @adminapi()
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

    @adminapi(log=True)
    async def addAuthRule(self, name, rule, indx=None, gateiden=None):
        s_common.deprecated('addAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.addRule(rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def delAuthRule(self, name, rule, gateiden=None):
        s_common.deprecated('delAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.delRule(rule, gateiden=gateiden)

    @adminapi(log=True)
    async def setAuthAdmin(self, name, isadmin):
        s_common.deprecated('setAuthAdmin')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.setAdmin(isadmin)

    async def setUserPasswd(self, iden, passwd):

        await self.cell.auth.reqUser(iden)

        if self.user.iden == iden:
            return await self.cell.setUserPasswd(iden, passwd)

        self.user.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.cell.setUserPasswd(iden, passwd)

    @adminapi(log=True)
    async def setUserLocked(self, useriden, locked):
        return await self.cell.setUserLocked(useriden, locked)

    @adminapi(log=True)
    async def setUserArchived(self, useriden, archived):
        return await self.cell.setUserArchived(useriden, archived)

    @adminapi(log=True)
    async def setUserEmail(self, useriden, email):
        return await self.cell.setUserEmail(useriden, email)

    @adminapi(log=True)
    async def addUserRole(self, useriden, roleiden):
        return await self.cell.addUserRole(useriden, roleiden)

    @adminapi(log=True)
    async def delUserRole(self, useriden, roleiden):
        return await self.cell.delUserRole(useriden, roleiden)

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

    @adminapi()
    async def getUserDef(self, iden):
        return await self.cell.getUserDef(iden)

    @adminapi()
    async def getAuthGate(self, iden):
        return await self.cell.getAuthGate(iden)

    @adminapi()
    async def getAuthGates(self):
        return await self.cell.getAuthGates()

    @adminapi()
    async def getRoleDef(self, iden):
        return await self.cell.getRoleDef(iden)

    @adminapi()
    async def getUserDefByName(self, name):
        return await self.cell.getUserDefByName(name)

    @adminapi()
    async def getRoleDefByName(self, name):
        return await self.cell.getRoleDefByName(name)

    @adminapi()
    async def getUserDefs(self):
        return await self.cell.getUserDefs()

    @adminapi()
    async def getRoleDefs(self):
        return await self.cell.getRoleDefs()

    @adminapi()
    async def isUserAllowed(self, iden, perm, gateiden=None):
        return await self.cell.isUserAllowed(iden, perm, gateiden=gateiden)

    @adminapi()
    async def tryUserPasswd(self, name, passwd):
        return await self.cell.tryUserPasswd(name, passwd)

    @adminapi()
    async def getUserProfile(self, iden):
        return await self.cell.getUserProfile(iden)

    @adminapi()
    async def getUserProfInfo(self, iden, name):
        return await self.cell.getUserProfInfo(iden, name)

    @adminapi()
    async def setUserProfInfo(self, iden, name, valu):
        return await self.cell.setUserProfInfo(iden, name, valu)

    async def getHealthCheck(self):
        await self._reqUserAllowed(('health',))
        return await self.cell.getHealthCheck()

    @adminapi()
    async def getDmonSessions(self):
        return await self.cell.getDmonSessions()

    @adminapi()
    async def listHiveKey(self, path=None):
        return await self.cell.listHiveKey(path=path)

    @adminapi()
    async def getHiveKey(self, path):
        return await self.cell.getHiveKey(path)

    @adminapi(log=True)
    async def setHiveKey(self, path, valu):
        return await self.cell.setHiveKey(path, valu)

    @adminapi(log=True)
    async def popHiveKey(self, path):
        return await self.cell.popHiveKey(path)

    @adminapi(log=True)
    async def saveHiveTree(self, path=()):
        return await self.cell.saveHiveTree(path=path)

    @adminapi()
    async def getNexusChanges(self, offs):
        async for item in self.cell.getNexusChanges(offs):
            yield item

    @adminapi()
    async def getDiagInfo(self):
        return {
            'slabs': await s_lmdbslab.Slab.getSlabStats(),
        }

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
        'nexslog:en': {
            'default': False,
            'description': 'Record all changes to the cell.  Required for mirroring (on both sides).',
            'type': 'boolean'
        },
    }

    async def __anit__(self, dirn, conf=None, readonly=False, *args, **kwargs):

        s_telepath.Aware.__init__(self)

        self.dirn = s_common.gendir(dirn)

        self.auth = None
        self.sessions = {}
        self.inaugural = False

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

        self.donexslog = self.conf.get('nexslog:en')

        await s_nexus.Pusher.__anit__(self, self.iden)

        await self._initCellSlab(readonly=readonly)

        self.setNexsRoot(await self._initNexsRoot())
        self.nexsroot.onStateChange(self.onLeaderChange)

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

        auth_passwd = self.conf.get('auth:passwd')
        if auth_passwd is not None:
            user = await self.auth.getUserByName('root')
            await user.setPasswd(auth_passwd)

        await self._initCellDmon()

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

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

    async def postNexsAnit(self):
        '''
        This must be called near the end of subclass initialization, after all the subsystems that allow nexus log
        entries to be executed, but before any new changes can be initiated.
        '''
        await self.nexsroot.recover()

    async def _initNexsRoot(self):
        nexsroot = await s_nexus.NexsRoot.anit(self.dirn, donexslog=self.donexslog)
        self.onfini(nexsroot.fini)
        nexsroot.onfini(self)
        return nexsroot

    async def onLeaderChange(self, leader):
        '''
        Cell implementers may override this method to be notified when
        nexusroot leadership changes. The leader arg will be a bool provided
        if the Cell is a leader or not.
        '''
        pass

    async def getNexusChanges(self, offs):
        async for item in self.nexsroot.iter(offs):
            yield item

    async def isUserAllowed(self, iden, perm, gateiden=None):
        user = self.auth.user(iden)
        if user is None:
            return False

        return user.allowed(perm, gateiden=gateiden)

    async def tryUserPasswd(self, name, passwd):
        user = await self.auth.getUserByName(name)
        if user is None:
            return None

        if not user.tryPasswd(passwd):
            return None

        return user.pack()

    async def getUserProfile(self, iden):
        user = await self.auth.reqUser(iden)
        return user.profile.pack()

    async def getUserProfInfo(self, iden, name):
        user = await self.auth.reqUser(iden)
        return user.profile.get(name)

    async def setUserProfInfo(self, iden, name, valu):
        user = await self.auth.reqUser(iden)
        return await user.profile.set(name, valu)

    async def addUserRule(self, iden, rule, indx=None, gateiden=None):
        user = await self.auth.reqUser(iden)
        retn = await user.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    async def addRoleRule(self, iden, rule, indx=None, gateiden=None):
        role = await self.auth.reqRole(iden)
        retn = await role.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    async def delUserRule(self, iden, rule, gateiden=None):
        user = await self.auth.reqUser(iden)
        return await user.delRule(rule, gateiden=gateiden)

    async def delRoleRule(self, iden, rule, gateiden=None):
        role = await self.auth.reqRole(iden)
        return await role.delRule(rule, gateiden=gateiden)

    async def setUserRules(self, iden, rules, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setRules(rules, gateiden=gateiden)

    async def setRoleRules(self, iden, rules, gateiden=None):
        role = await self.auth.reqRole(iden)
        await role.setRules(rules, gateiden=gateiden)

    async def setUserAdmin(self, iden, admin, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setAdmin(admin, gateiden=gateiden)

    async def addUserRole(self, useriden, roleiden):
        user = await self.auth.reqUser(useriden)
        await user.grant(roleiden)
        await self.fire('user:mod', act='grant', user=useriden, role=roleiden)

    async def delUserRole(self, useriden, roleiden):
        user = await self.auth.reqUser(useriden)
        await user.revoke(roleiden)

        await self.fire('user:mod', act='revoke', user=useriden, role=roleiden)

    async def addUser(self, name, passwd=None, email=None):
        user = await self.auth.addUser(name, passwd=passwd, email=email)
        await self.fire('user:mod', act='adduser', name=name)
        return user.pack(packroles=True)

    async def delUser(self, iden):
        await self.auth.delUser(iden)
        await self.fire('user:mod', act='deluser', user=iden)

    async def addRole(self, name):
        role = await self.auth.addRole(name)
        return role.pack()

    async def delRole(self, iden):
        await self.auth.delRole(iden)

    async def setUserEmail(self, useriden, email):
        await self.auth.setUserInfo(useriden, 'email', email)

    async def setUserPasswd(self, iden, passwd):
        user = await self.auth.reqUser(iden)
        await user.setPasswd(passwd)
        await self.fire('user:mod', act='setpasswd', user=iden)

    async def setUserLocked(self, iden, locked):
        user = await self.auth.reqUser(iden)
        await user.setLocked(locked)
        await self.fire('user:mod', act='locked', user=iden, locked=locked)

    async def setUserArchived(self, iden, archived):
        user = await self.auth.reqUser(iden)
        await user.setArchived(archived)
        await self.fire('user:mod', act='archived', user=iden, archived=archived)

    async def getUserDef(self, iden):
        user = self.auth.user(iden)
        if user is not None:
            return user.pack(packroles=True)

    async def getAuthGate(self, iden):
        gate = self.auth.getAuthGate(iden)
        if gate is None:
            return None
        return gate.pack()

    async def getAuthGates(self):
        return [g.pack() for g in self.auth.getAuthGates()]

    async def getRoleDef(self, iden):
        role = self.auth.role(iden)
        if role is not None:
            return role.pack()

    async def getUserDefByName(self, name):
        user = await self.auth.getUserByName(name)
        if user is not None:
            return user.pack(packroles=True)

    async def getRoleDefByName(self, name):
        role = await self.auth.getRoleByName(name)
        if role is not None:
            return role.pack()

    async def getUserDefs(self):
        return [u.pack(packroles=True) for u in self.auth.users()]

    async def getRoleDefs(self):
        return [r.pack() for r in self.auth.roles()]

    async def getAuthUsers(self, archived=False):
        return [u.pack() for u in self.auth.users() if archived or not u.info.get('archived')]

    async def getAuthRoles(self):
        return [r.pack() for r in self.auth.roles()]

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
                    pkey, cert = cdir.genHostCert(self.getCellType())
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
        isnew = not self.slab.dbexists('hive')

        db = self.slab.initdb('hive')
        hive = await s_hive.SlabHive.anit(self.slab, db=db, nexsroot=self.nexsroot)
        self.onfini(hive)

        if isnew:
            path = os.path.join(self.dirn, 'hiveboot.yaml')
            if os.path.isfile(path):
                logger.debug(f'Loading cell hive from {path}')
                tree = s_common.yamlload(path)
                if tree is not None:
                    # Pack and unpack the tree to avoid tuple/list issues
                    # for in-memory structures.
                    tree = s_common.tuplify(tree)
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
        auth = await s_hiveauth.Auth.anit(node, nexsroot=self.nexsroot)

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

    @classmethod
    def getEnvPrefix(cls):
        return f'SYN_{cls.__name__.upper()}'

    def getCellIden(self):
        return self.iden

    @classmethod
    def initCellConf(cls):
        '''
        Create a Config object for the Cell.

        Notes:
            The Config object has a ``envar_prefix`` set according to the results of ``cls.getEnvPrefix()``.

        Returns:
            s_config.Config: A Config helper object.
        '''
        prefix = cls.getEnvPrefix()
        schema = s_config.getJsSchema(cls.confbase, cls.confdefs)
        return s_config.Config(schema, envar_prefix=prefix)

    @classmethod
    def getArgParser(cls, conf=None):
        '''
        Get an ``argparse.ArgumentParser`` for the Cell.

        Args:
            conf (s_config.Config): Optional, a Config object which

        Notes:
            Boot time configuration data is placed in the argument group called ``config``.
            This adds default ``dirn``, ``--telepath``, ``--https`` and ``--name`` arguements to the argparser instance.
            Configuration values which have the ``hideconf`` value set to True are not added to the argparser instance.

        Returns:
            argparse.ArgumentParser: A ArgumentParser for the Cell.
        '''

        name = cls.getCellType()
        prefix = cls.getEnvPrefix()

        pars = argparse.ArgumentParser(prog=name)
        pars.add_argument('dirn', help=f'The storage directory for the {name} service.')

        pars.add_argument('--log-level', default='INFO', choices=s_const.LOG_LEVEL_CHOICES,
                          help='Specify the Python logging log level.', type=str.upper)

        telendef = None
        telepdef = 'tcp://0.0.0.0:27492'
        httpsdef = 4443
        telenvar = '_'.join((prefix, 'NAME'))
        telepvar = '_'.join((prefix, 'TELEPATH'))
        httpsvar = '_'.join((prefix, 'HTTPS'))
        telen = os.getenv(telenvar, telendef)
        telep = os.getenv(telepvar, telepdef)
        https = os.getenv(httpsvar, httpsdef)

        pars.add_argument('--telepath', default=telep, type=str,
                          help=f'The telepath URL to listen on. This defaults to {telepdef}, and may be '
                               f'also be overridden by the {telepvar} environment variable.')
        pars.add_argument('--https', default=https, type=int,
                          help=f'The port to bind for the HTTPS/REST API. This defaults to {httpsdef}, '
                               f'and may be also be overridden by the {httpsvar} environment variable.')
        pars.add_argument('--name', type=str, default=telen,
                          help=f'The (optional) additional name to share the {name} as. This defaults to '
                               f'{telendef}, and may be also be overridden by the {telenvar} environment'
                               f' variable.')

        if conf is not None:
            args = conf.getArgParseArgs()
            if args:
                pgrp = pars.add_argument_group('config', 'Configuration arguments.')
                for (argname, arginfo) in args:
                    pgrp.add_argument(argname, **arginfo)

        return pars

    @classmethod
    async def initFromArgv(cls, argv, outp=None):
        '''
        Cell launcher which does automatic argument parsing, environment variable resolution and Cell creation.

        Args:
            argv (list): A list of command line arguments to launch the Cell with.
            outp (s_ouput.OutPut): Optional, an output object.

        Notes:
            This does the following items:
                - Create a Config object from the Cell class.
                - Creates an Argument Parser from the Cell class and Config object.
                - Parses the provided arguments.
                - Loads configuration data from the parsed options and environment variables.
                - Sets logging for the process.
                - Creates the Cell from the Cell Ctor.
                - Adds a Telepath listener, HTTPs port listeners and Telepath share names.
                - Returns the Cell.

        Returns:
            Cell: This returns an instance of the Cell.
        '''

        conf = cls.initCellConf()
        pars = cls.getArgParser(conf=conf)

        opts = pars.parse_args(argv)

        conf.setConfFromOpts(opts)
        conf.setConfFromEnvs()

        s_common.setlogging(logger, defval=opts.log_level)

        cell = await cls.anit(opts.dirn, conf=conf)

        try:

            await cell.addHttpsPort(opts.https)
            await cell.dmon.listen(opts.telepath)

            if opts.name is not None:
                cell.dmon.share(opts.name, cell)

            if outp is not None:
                outp.printf(f'...{cell.getCellType()} API (telepath): %s' % (opts.telepath,))
                outp.printf(f'...{cell.getCellType()} API (https): %s' % (opts.https,))
                if opts.name is not None:
                    outp.printf(f'...{cell.getCellType()} API (telepath name): %s' % (opts.name,))

        except Exception:
            await cell.fini()
            raise

        return cell

    @classmethod
    async def execmain(cls, argv, outp=None):
        '''
        The main entry point for running the Cell as an application.

        Args:
            argv (list): A list of command line arguments to launch the Cell with.
            outp (s_ouput.OutPut): Optional, an output object.

        Notes:
            This coroutine waits until the Cell is fini'd or a SIGINT/SIGTERM signal is sent to the process.

        Returns:
            None.
        '''

        if outp is None:
            outp = s_output.stdout

        cell = await cls.initFromArgv(argv, outp=outp)

        await cell.main()

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

    @s_nexus.Pusher.onPushAuto('sync')
    async def sync(self):
        '''
        no-op mutable for testing purposes.  If I am follower, when this returns, I have received and applied all
        the writes that occurred on the leader before this call.
        '''
        return
