import weakref

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack

import synapse.lib.crypto.passwd as s_passwd

rulestype = {
    'type': 'array',
    'items': {
        'type': 'array',
        'items': (
            {'type': 'boolean'},
            {'type': 'array', 'items': {'type': 'string'}},
        ),
        'minItems': 2,
        'maxItems': 2,
    }
}

reqValidRules = s_config.getJsValidator(s_msgpack.deepcopy(rulestype))

reqValidRole = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        # 'rules': s_msgpack.deepcopy(rulestype),
        'authgates': {'type': 'array', 'items': {'type': 'string', 'pattern': s_config.re_iden}},
    },
    'required': ['iden', 'name', 'rules'],
}, use_default=True)

reqValidUser = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'email': {'type': 'string'},
        'passwd': {},
        'admin': {'type': 'boolean', 'default': False},
        'locked': {'type': 'boolean', 'default': False},
        'archived': {'type': 'boolean', 'default': False},
        'created': {'type': 'number'},
        'roles': {'type': 'array', 'maxItems': 200, 'items': {'type': 'string', 'pattern': s_config.re_iden}},
        # 'rules': rulestype,
        'authgates': {'type': 'array', 'items': {'type': 'string', 'pattern': s_config.re_iden}},
    },
    'required': ['iden', 'name', 'admin', 'locked', 'rules'],
}, use_default=True)

reqValidGateUserInfo = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'admin': {'type': 'boolean', 'default': False},
        # 'rules': s_msgpack.deepcopy(rulestype),
    },
    'required': ['admin', 'rules'],
})

reqValidGateRoleInfo = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        # 'rules': s_msgpack.deepcopy(rulestype),
    },
    'required': ['iden', 'rules'],
})

class CellAuthMixin(metaclass=s_nexus.RegMethType):

    async def _initCellAuth(self):

        if self.inaugural:
            self.cellmeta.set('auth:version', 1)

        self.users = self._getSlabBidnDict('user')

        self.users.addIndex('name', 'uniq')
        self.users.addIndex('email', 'uniq')

        self.roles = self._getSlabBidnDict('role')
        self.roles.addIndex('name', 'uniq')

        self.profiles = self._getSlabBidnDict('profiles')
        self.uservars = self._getSlabBidnDict('uservars')

        self.gates = self._getSlabBidnDict('gate')
        self.gateusers = self._getSlabBidnDict('gateusers') # <gate><user><prop> = <valu>
        self.gateroles = self._getSlabBidnDict('gateroles') # <gate><role><prop> = <valu>

        self.userroles = self._getSlabBidnLink('userroles') # <user> <-> <role>
        self.usergates = self._getSlabBidnLink('usergates') # <user> <-> <gate>
        self.rolegates = self._getSlabBidnLink('rolegates') # <role> <-> <gate>

        self.usercache = weakref.WeakValueDictionary()
        self.rolecache = weakref.WeakValueDictionary()
        self.gatecache = weakref.WeakValueDictionary()

        if self.cellmeta.get('auth:version', 0) == 0:
            await self._migrCellAuthV0()

        await self._initAllRole()

        self.rootuser = self.getUserByName('root')
        if self.rootuser is None:
            iden = s_common.guid((self.iden, 'user', 'root'))
            info = {'iden': iden, 'name': 'root', 'admin': True}
            self.rootuser = await self._addUser(info)

    async def _initAllRole(self):
        self.allrole = self.getRoleByName('all')
        if self.allrole is None:
            iden = s_common.guid((self.iden, 'role', 'all'))
            info = {'iden': iden, 'name': 'all'}
            self.allrole = await self._addRole(info)

    async def _migrCellAuthV0(self):

        for iden, node in await self.hive.open(('auth', 'roles')):
            rdef = (await node.dict()).pack()
            rdef['iden'] = iden
            rdef['name'] = node.valu
            await self._addRole(rdef)

        await self._initAllRole()

        for iden, node in await self.hive.open(('auth', 'users')):

            udef = (await node.dict()).pack()
            udef['iden'] = iden
            udef['name'] = node.valu

            print(f'USER {udef}')

            await self._addUser(udef)

        for gateiden, node in await self.hive.open(('auth', 'authgates')):

            if self.getCellType() == 'cortex':

                if node.valu == 'cortex':
                    continue

                # TODO handle queue names :(

            gdef = (await node.dict()).pack()
            print(f'GDEF {node.valu} {gdef}')

            gatebidn = s_common.uhex(gateiden)

            self.gates.set(gatebidn, 'iden', gateiden)
            self.gates.set(gatebidn, 'type', node.valu)

            for useriden, usernode in await node.open(('users',)):
                gateuser = (await usernode.dict()).pack()

                userbidn = s_common.uhex(useriden)
                admin = gateuser.get('admin', s_common.novalu)
                rules = gateuser.get('rules', s_common.novalu)

                if admin is not s_common.novalu:
                    self.gateusers.set(gatebidn + userbidn, 'admin', bool(admin))

                if rules is not s_common.novalu:
                    self.gateusers.set(gatebidn + userbidn, 'rules', tuple(rules))

                print(f'GATEUSER {useriden} {usernode.valu} {gateuser}')

            for roleiden, rolenode in await node.open(('roles',)):
                gaterole = (await rolenode.dict()).pack()
                print(f'GATEROLE {roleiden} {rolenode.valu} {gaterole}')

            gdef = (await node.dict()).pack()
            print(f'GATE {iden} {node.valu} {gdef}')

        authtree = await self.hive.saveHiveTree(path=('auth',))
        self.cellmeta.set('auth:backup:0', authtree)

        await self.hive.pop(('auth',))

        self.cellmeta.set('auth:version', 1)

    async def _addUserHook(self, user):
        pass

    async def _delUserHook(self, user):
        pass

    async def _addRoleHook(self, user):
        pass

    async def _delRoleHook(self, user):
        pass

    async def addUser(self, name, passwd=None, email=None, iden=None):

        if iden is None:
            iden = s_common.guid()

        info = {'iden': iden, 'name': name, 'created': s_common.now()}

        if email is not None:
            info['email'] = email

        user = await self._push('user:add', info)

        if passwd is not None:
            await user.setPasswd(passwd)

        return user

    async def addRole(self, name, iden=None):

        if iden is None:
            iden = s_common.guid()

        info = {'iden': iden, 'name': name, 'created': s_common.now()}
        return await self._push('role:add', info)

    @s_nexus.Pusher.onPush('user:add')
    async def _addUser(self, info):

        info.setdefault('rules', ())
        info.setdefault('admin', False)
        info.setdefault('locked', False)

        # pop these to prevent multi-editor issues...
        roles = [s_common.uhex(r) for r in info.pop('roles', ())]
        gates = [s_common.uhex(r) for r in info.pop('authgates', ())]

        async for rolebidn in s_coro.safeiter(roles):
            self._reqRoleBuid(rolebidn)

        async for gatebidn in s_coro.safeiter(gates):
            self._reqGateBuid(gatebidn)

        info = reqValidUser(info)

        bidn = s_common.uhex(info.get('iden'))

        await self.users.update(bidn, info)

        async for rolebidn in s_coro.safeiter(roles):
            self.userroles.add(bidn, rolebidn)

        async for rolebidn in s_coro.safeiter(roles):
            self.usergates.add(bidn, rolebidn)

        self.userroles.add(bidn, self.allrole.bidn)

        user = self._getUser(bidn)
        await self._addUserHook(user)

        return user

    @s_nexus.Pusher.onPushAuto('user:del')
    async def delUser(self, iden):

        bidn = s_common.uhex(iden)
        user = self._getUser(bidn)
        if user is not None:
            await self._delUserHook(user)
            user.delete()

        await self.users.clear(bidn)
        await self.profiles.clear(bidn)
        await self.uservars.clear(bidn)

        async for rolebidn in self.userroles.iter(bidn):
            self.userroles.pop(bidn, rolebidn)

        async for gatebidn in self.usergates.iter(bidn):
            await self.gateusers.clear(gatebidn + bidn)
            self.usergates.pop(bidn, gatebidn)

    @s_nexus.Pusher.onPush('role:add')
    async def _addRole(self, info):

        info.setdefault('rules', ())

        info = reqValidRole(info)

        bidn = s_common.uhex(info.get('iden'))
        gates = [s_common.uhex(g) for g in info.pop('authgates', ())]

        async for gatebidn in s_coro.safeiter(gates):
            self._reqGateBuid(gatebidn)

        await self.roles.update(bidn, info)

        async for gatebidn in s_coro.safeiter(gates):
            self.rolegates.add(bidn, gatebidn)

        role = self._getRole(bidn)
        await self._addRoleHook(role)

        return role

    @s_nexus.Pusher.onPushAuto('role:del')
    async def delRole(self, iden):

        bidn = s_common.uhex(iden)
        role = self._getRole(bidn)
        if role is None:
            return

        await self._delRoleHook(role)

        async for gatebidn in self.rolegates.iter(bidn):
            await self.gateroles.clear(gatebidn + bidn)
            self.rolegates.pop(bidn, gatebidn)

        # this must be last
        await self.roles.clear(bidn)

    def _getUser(self, bidn):

        user = self.usercache.get(bidn)
        if user is not None:
            return user

        info = self.users.dict(bidn)
        if not info:
            return None

        user = CellUser(self, info)
        self.usercache[bidn] = user

        return user

    def _getRole(self, bidn):

        role = self.rolecache.get(bidn)
        if role is not None:
            return role

        info = self.roles.dict(bidn)
        if not info:
            return

        role = CellRole(self, info)
        self.rolecache[bidn] = role

        return role

    def getUser(self, iden):
        return self._getUser(s_common.uhex(iden))

    def getUserByName(self, name):
        bidn = self.users.by('name', name)
        if bidn is not None:
            return self._getUser(bidn)

    def getUserByEmail(self, email):
        bidn = self.users.by('email', email)
        if bidn is not None:
            return self._getUser(bidn)

    def getRoleByName(self, name):
        bidn = self.roles.by('name', name)
        if bidn is not None:
            return self._getRole(bidn)

    async def setUserInfo(self, iden, prop, valu, gateiden=None):
        return await self._push('user:set', iden, prop, valu, gateiden=gateiden)

    @s_nexus.Pusher.onPush('user:set')
    async def _setUserInfo(self, iden, prop, valu):

        bidn = s_common.uhex(iden)

        self._reqUserBidn(bidn)

        user = self.usercache.get(bidn)

        info = await self.users.dict(bidn)
        info[prop] = valu

        reqValidUser(info)

        valu = self.users.set(bidn, prop, valu)

        if user is not None:
            user.clearAuthCache()
            user.info[prop] = valu

    async def setGateUserProp(self, gateiden, useriden, prop, valu):
        return await self._push('gate:user:set', gateiden, useriden, prop, valu)

    async def setGateRoleProp(self, gateiden, roleiden, prop, valu):
        return await self._push('gate:role:set', gateiden, roleiden, prop, valu)

    @s_nexus.Pusher.onPush('gate:user:set')
    async def _setGateUserProp(self, gateiden, useriden, prop, valu):

        gatebidn = s_common.uhex(gateiden)
        userbidn = s_common.uhex(useriden)

        self._reqUserBidn(userbidn)
        self._reqGateBidn(gatebidn)

        bidn = gatebidn + userbidn

        info = await self.gateusers.dict(bidn)

        info[prop] = valu
        reqValidGateUser(info)

        await self.gateusers.set(bidn, prop, valu)

        user = self.usercache.get(userbidn)
        if user is not None:
            user.clearAuthCache()

    @s_nexus.Pusher.onPush('gate:role:set')
    async def _setGateRoleProp(self, gateiden, roleiden, prop, valu):

        gatebidn = s_common.uhex(gateiden)
        rolebidn = s_common.uhex(roleiden)

        self._reqUserBidn(rolebidn)
        self._reqGateBidn(gatebidn)

        bidn = gatebidn + rolebidn

        info = await self.gateroles.dict(bidn)

        info[prop] = valu
        reqValidGateUser(info)

        await self.gateroles.set(bidn, prop, valu)

        async for userbidn in self.userroles.iter(rolebidn):
            user = self.usercache.get(userbidn)
            if user is not None:
                user.clearAuthCache()

    async def setRoleInfo(self, iden, prop, valu):
        return await self._push('role:set', iden, prop, valu)

    @s_nexus.Pusher.onPush('role:set')
    async def setRoleInfo(self, iden, prop, valu):

        stor = self.roles
        bidn = s_common.uhex(iden)

        if gateiden is not None:
            stor = self.gateroles
            bidn = s_common.uhex(gateiden) + bidn

        stor.set(bidn, prop, valu)

        async for userbidn in self.userroles.iter(bidn):
            user = self.usercache.get(userbidn)
            if user is not None:
                user.clearAuthCache()

    def getAuthGate(self, iden):
        return self._getAuthGate(s_common.uhex(iden))

    def _getAuthGate(self, bidn):

        gate = self.gatecache.get(bidn)
        if gate is not None:
            return gate

        info = self.gates.dict(bidn)
        if not info:
            return None

        gate = CellGate(self, info)
        self.gatecache[bidn] = gate

        return gate

    async def addAuthGate(self, iden, authgatetype):
        '''
        Retrieve abstract AuthGate by iden.

        WARNING: not nexusified
        '''
        bidn = s_common.uhex(iden)

        self.gates.set(bidn, 'type', authgatetype)
        self.gates.set(bidn, 'iden', iden)

        gate = CellGate(self, iden)
        self.gatecache[bidn] = gate

        return gate

    async def delAuthGate(self, iden):
        '''
        Delete abstract AuthGate by iden.

        WARNING: not nexusified
        '''
        bidn = s_common.uhex(iden)

        async for userbidn in self.usergates.iter(bidn):

            await self.gateusers.clear(bidn + userbidn)
            self.usergates.pop(userbidn, bidn)

            user = self.usercache.get(userbidn)
            if user is not None:
                user.clearAuthCache()

        async for rolebidn in self.rolegates.iter(bidn):

            await self.gateusers.clear(bidn + userbidn)
            self.rolegates.pop(userbidn, bidn)

            for userbidn in self._gate_cell.userroles.iter(rolebidn):
                user = self._gate_cell.usercache.get(userbidn)
                if user is not None:
                    user.clearAuthCache()

        await self.gates.clear(bidn)

    def getAuthGates(self):
        return list(self.authgates.values())

    def reqAuthGate(self, iden):
        gate = self.getAuthGate(iden)
        if gate is None:
            mesg = f'No auth gate found with iden: ({iden}).'
            raise s_exc.NoSuchAuthGate(iden=iden, mesg=mesg)
        return gate

    def reqUser(self, iden):
        return self._reqUser(s_common.uhex(iden))

    def _reqUser(self, bidn):
        user = self._getUser(bidn)
        if user is None:
            mesg = f'No user with iden {iden}.'
            raise s_exc.NoSuchUser(mesg=mesg)
        return user

    def _reqUserBidn(self, bidn):
        tick = self.users.get(bidn, 'iden') is not None
        if tick is None:
            mesg = f'No user with iden {s_common.ehex(bidn)}.'
            raise s_exc.NoSuchUser(mesg=mesg)

    def _reqRoleBidn(self, bidn):
        tick = self.roles.get(bidn, 'iden') is not None
        if tick is None:
            mesg = f'No role with iden {s_common.ehex(bidn)}.'
            raise s_exc.NoSuchRole

    def _reqGateBidn(self, bidn):
        tick = self.gates.get(bidn, 'iden') is not None
        if tick is None:
            mesg = f'No authgate with iden {s_common.ehex(bidn)}.'
            raise s_exc.NoSuchAuthGate(mesg=mesg)

    def reqRole(self, iden):

        role = self.getRole(iden)
        if role is None:
            mesg = f'No role with iden {iden}.'
            raise s_exc.NoSuchRole(mesg=mesg)
        return role

    def reqUserByName(self, name):
        user = self.getUserByName(name)
        if user is None:
            mesg = f'No user named {name}.'
            raise s_exc.NoSuchUser(mesg=mesg)
        return user

    async def reqRoleByName(self, name):
        role = self.getRoleByName(name)
        if role is None:
            mesg = f'No role named {name}.'
            raise s_exc.NoSuchRole(mesg=mesg)
        return role

class CellUser:

    def __init__(self, cell, info):
        self.cell = cell
        self.info = info
        self.deleted = False
        # it is safe to set this because it is immutable
        self.iden = info.get('iden')
        self.permcache = s_cache.FixedCache(self._allowed)

        self.bidn = s_common.uhex(self.iden)

        self.vars = self.cell.uservars.look(self.bidn)
        self.profile = self.cell.profiles.look(self.bidn)

    async def set(self, name, valu):
        return await self.cell.setUserInfo(self.iden, name, valu)

    def get(self, name, defv=None, gateiden=None):

        if gateiden is None:
            return self.info.get(name, defv)

        gatebidn = s_common.uhex(gateiden)
        return self.cell.gateusers.get(gatebidn + self.bidn, name, defv=defv)

    def updated(self):
        self.permcache.clear()
        # we keep the base user info cached
        self.info = self.cell.users.dict(self.bidn)

    def isAdmin(self, gateiden=None):
        return bool(self.get('admin', gateiden=gateiden))

    async def setAdmin(self, admin, gateiden=None):
        return await self.set('admin', bool(admin), gateiden=None)

    def isLocked(self):
        return self.info.get('locked')

    async def setLocked(self, locked):
        return await self.set('locked', bool(locked))

    def getRules(self, gateiden=None):

        if gateiden is None:
            return list(self.info.get('rules', ()))

        gatebidn = s_common.uhex(gateiden)
        return list(self.cell.gateusers.get(gatebidn + self.bidn, 'rules', ()))

    async def addRule(self, rule, indx=None, gateiden=None):

        if gateiden is not None:
            self.cell.reqAuthGate(gateiden)
            rules = list(self.cell.getGateUserProp(self.iden, 'rules', ()))

        gate = self.cell.reqAuthGate(gateiden)

        rules = self.getRules(gateiden=gateiden)

        if indx is None:
            rules.append(rule)
        else:
            rules.insert(indx, rule)

        await self.cell.setUserInfo(self.iden, 'rules', rules)

    async def setPasswd(self, passwd, nexs=True):

        if passwd is None:
            shadow = None

        elif passwd and isinstance(passwd, str):
            shadow = await s_passwd.getShadowV2(passwd=passwd)

        else:
            raise s_exc.BadArg(mesg='Password must be a string')

        await self.cell.setUserInfo(self.iden, 'passwd', shadow)

    async def tryPasswd(self, passwd):

        if self.info.get('locked', False):
            return False

        if passwd is None:
            return False

        onepass = self.info.get('onepass')
        if onepass is not None:
            if isinstance(onepass, dict):
                shadow = onepass.get('shadow')
                expires = onepass.get('expires')
                if expires >= s_common.now():
                    if await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow):
                        await self.cell.setUserInfo(self.iden, 'onepass', None)
                        logger.debug(f'Used one time password for {self.name}',
                                     extra={'synapse': {'user': self.iden, 'username': self.name}})
                        return True
            else:
                # Backwards compatible password handling
                expires, params, hashed = onepass
                if expires >= s_common.now():
                    if s_common.guid((params, passwd)) == hashed:
                        await self.cell.setUserInfo(self.iden, 'onepass', None)
                        logger.debug(f'Used one time password for {self.name}',
                                     extra={'synapse': {'user': self.iden, 'username': self.name}})
                        return True

        shadow = self.info.get('passwd')
        if shadow is None:
            return False

        if isinstance(shadow, dict):
            return await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow)

        # Backwards compatible password handling
        salt, hashed = shadow
        if s_common.guid((salt, passwd)) == hashed:
            logger.debug(f'Migrating password to shadowv2 format for user {self.name}',
                         extra={'synapse': {'user': self.iden, 'username': self.name}})
            # Update user to new password hashing scheme.
            await self.setPasswd(passwd=passwd)

            return True

        return False

    async def allow(self, perm):
        if not await self.allowed(perm):
            await self.addRule((True, perm), indx=0)

    async def allowed(self, perm, default=None, gateiden=None):
        perm = tuple(perm)
        return await self.permcache.aget((perm, default, gateiden))

    async def confirm(self, perm, default=None, gateiden=None):
        if not await self.allowed(perm, default=default, gateiden=gateiden):
            self.raisePermDeny(perm, gateiden=gateiden)

    def raisePermDeny(self, perm, gateiden=None):

        perm = '.'.join(perm)
        if gateiden is None:
            mesg = f'User {self.name!r} ({self.iden}) must have permission {perm}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.name)

        gatebidn = s_common.uhex(gateiden)

        self.cell._reqGateBidn(gatebidn)
        gatetype = self.cell.gates.get(gatebidn, 'type')

        mesg = f'User {self.name!r} ({self.iden}) must have permission {perm} on object {gateiden} ({gatetype}).'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.name)

    async def _allowed(self, pkey):

        perm, default, gateiden = pkey

        if self.deleted:
            return False

        if self.info.get('locked'):
            return False

        if self.info.get('admin'):
            return True

        # 1. check authgate user rules
        if gateiden is not None:

            gatebidn = s_common.uhex(gateiden)

            gateuser = gatebidn + self.bidn
            if self.cell.gateusers.get(gateuser, 'admin'):
                return True

            for allow, path in self.cell.gateusers.get(gateuser, 'rules', ()):
                if perm[:len(path)] == path:
                    return allow

        # 2. check user rules
        for allow, path in self.info.get('rules', ()):
            if perm[:len(path)] == path:
                return allow

        # 3. check authgate role rules

        if gateiden is not None:

            async for rolebidn in self.cell.userroles.iter(self.bidn):
                for allow, path in self.cell.gateroles.get(gatebidn + rolebidn, 'rules', defv=()):
                    if perm[:len(path)] == path:
                        return allow

        # 4. check role rules
        async for rolebidn in self.cell.userroles.iter(self.bidn):
            for allow, path in self.cell.roles.get(rolebidn, 'rules', defv=()):
                if perm[:len(path)] == path:
                    return allow

        return default

    def clearAuthCache(self):
        self.permcache.clear()

    def delete(self):
        self.deleted = True
        self.permcache.clear()

    async def pack(self, packroles=False):

        roles = []
        gates = []

        retn = {
            'type': 'user',
            'iden': self.iden,
            'name': self.name,
            'rules': self.rules,
            'roles': roles,
            'authgates': gates,
        }

        async for gatebidn in self.cell.usergates.iter(self.bidn):
            gates.append(await self.cell.gateusers.pack(gatebidn + self.bidn))
            if len(gates) >= 1000:
                break

        async for rolebidn in self.cell.userroles.iter(self.bidn):

            if packroles:
                roles.append(await self.cell.roles.pack(rolebidn))
            else:
                roles.append(s_common.ehex(rolebidn))

            if len(gates) >= 1000:
                break

        return retn

    # for backward compatibility...
    def __getattr__(self, name):
        valu = self.info.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        raise AttributeError(f'CellUser has no attribute named: {name}')

class CellRole:

    def __init__(self, cell, info):
        self.cell = cell
        self.info = info
        self.iden = info.get('iden')
        self.bidn = s_common.uhex(self.iden)

    def get(self, name, defv=None):
        return self.info.get(name, defv)

    async def set(self, name, valu, gateiden=None):
        return await self.cell.setRoleInfo(self.iden, name, valu, gateiden=gateiden)

    def getRules(self, gateiden=None):

        if gateiden is None:
            return list(self.info.get('rules', ()))

        gaterole = s_common.uhex(gateiden) + self.bidn
        return list(self.cell.gateroles.get(gaterole, 'rules', defv=()))

    async def addRule(self, rule, indx=None, gateiden=None):

        rules = self.getRules(gateiden=gateiden)

        if indx is None:
            rules.append(rule)
        else:
            rules.insert(indx, rule)

        await self.cell.setRoleInfo(self.iden, 'rules', rules, gateiden=gateiden)

    # for backward compatibility...
    def __getattr__(self, name):
        valu = self.info.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        raise AttributeError(f'CellRole has no attribute named: {name}')

class CellGate:
    '''

    The CellGate class is designed for use as a mixin *or* ephemeral class to edit confiurations.

    NOTE: CellGate edit APIs are *not* nexusified and should be manipulated within other nexus handlers.
    '''

    def __init__(self, cell, iden):
        self._gate_cell = cell
        self._gate_iden = iden
        self._gate_bidn = s_common.uhex(iden)

    def setUserAdmin(self, useriden, admin):
        '''
        WARNING: not nexusified
        '''
        return self._gate_cell._setGateUserProp(self._gate_iden, useriden, 'admin', bool(admin))

    def getUserRules(self, useriden):
        userbidn = s_common.uhex(useriden)
        return list(self._gate_cell.gateusers.get(self._gate_bidn + userbidn, 'rules', ()))

    def getRoleRules(self, roleiden):
        rolebidn = s_common.uhex(roleiden)
        return list(self._gate_cell.gateroles.get(self._gate_bidn + rolebidn, 'rules', ()))

    async def setUserRules(self, useriden, rules):
        '''
        WARNING: not nexusified
        '''
        return self._gate_cell._setGateUserProp(self._gate_iden, useriden, 'rules', tuple(rules))

    async def setRoleRules(self, roleiden, rules):
        '''
        WARNING: not nexusified
        '''
        return self._gate_cell._setGateRoleProp(self._gate_iden, useriden, 'rules', tuple(rules))

    async def addRoleRule(self, roleiden, rule):

        reqValidRules((rule,))

        rules = self.getRoleRules(roleiden)
        rules.insert(0, rule)

        await self.setRoleRules(roleiden, rules)

    async def addUserRule(self, useriden, rule):

        reqValidRules((rule,))

        rules = self.getUserRules(useriden)
        rules.insert(0, rule)

        await self.setUserRules(useriden, rules)

    async def delete(self):

        async for userbidn in self._gate_cell.usergates.iter(self._gate_bidn):

            await self._gate_cell.gateusers.clear(self._gate_bidn + userbidn)
            self._gate_cell.usergates.pop(userbidn, self._gate_bidn)

            user = self._gate_cell.usercache.get(userbidn)
            if user is not None:
                user.clearAuthCache()

        async for rolebidn in self._gate_cell.rolegates.iter(self._gate_bidn):

            await self._gate_cell.gateusers.clear(self._gate_bidn + userbidn)
            self._gate_cell.rolegates.pop(rolebidn, self._gate_bidn)

            async for userbidn in self._gate_cell.userroles.iter(rolebidn):
                user = self.cell._gate_cell.usercache.get(userbidn)
                if user is not None:
                    user.clearAuthCache()

class HiveAuthNexs():
    '''
    Consume old HiveAuth nexus events and make modern API calls.
    '''
    pass
