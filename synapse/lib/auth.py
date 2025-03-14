import string
import logging
import dataclasses

from typing import Optional, Union

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas

import synapse.lib.crypto.passwd as s_passwd

logger = logging.getLogger(__name__)

def getShadow(passwd):  # pragma: no cover
    '''This API is deprecated.'''
    s_common.deprecated('hiveauth.getShadow()', curv='2.110.0')
    salt = s_common.guid()
    hashed = s_common.guid((salt, passwd))
    return (salt, hashed)

def textFromRule(rule):
    text = '.'.join(rule[1])
    if not rule[0]:
        text = '!' + text
    return text

@dataclasses.dataclass(slots=True)
class _allowedReason:
    value: Union[bool | None]
    default: bool = False
    isadmin: bool = False
    islocked: bool = False
    gateiden: Union[str | None] = None
    roleiden: Union[str | None] = None
    rolename: Union[str | None] = None
    rule: tuple = ()

    @property
    def mesg(self):
        if self.islocked:
            return 'The user is locked.'
        if self.default:
            return 'No matching rule found.'

        if self.isadmin:
            if self.gateiden:
                return f'The user is an admin of auth gate {self.gateiden}.'
            return 'The user is a global admin.'

        if self.rule:
            rt = textFromRule((self.value, self.rule))
            if self.gateiden:
                if self.roleiden:
                    m = f'Matched role rule ({rt}) for role {self.rolename} on gate {self.gateiden}.'
                else:
                    m = f'Matched user rule ({rt}) on gate {self.gateiden}.'
            else:
                if self.roleiden:
                    m = f'Matched role rule ({rt}) for role {self.rolename}.'
                else:
                    m = f'Matched user rule ({rt}).'
            return m

        return 'No matching rule found.'

class Auth(s_nexus.Pusher):
    '''
    Auth is a user authentication and authorization stored in a Slab.  Users
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

    AuthGates are objects that manage their own authorization.  Each
    AuthGate has roles and users subkeys which contain rules specific to that
    user or role for that AuthGate.  The roles and users of an AuthGate,
    called GateRole and GateUser respectively, contain the iden of a role or
    user defined prior and rules specific to that role or user; they do not
    duplicate the metadata of the role or user.

    Layout::

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

    async def __anit__(self, slab, dbname, pref='', nexsroot=None, seed=None, maxusers=0, policy=None):
        '''
        Args:
            slab (s_lmdb.Slab): The slab to use for persistent storage for auth
            dbname (str): The name of the db to use in the slab
        '''
        if policy:
            s_schemas.reqValidPasswdPolicy(policy)
        # Derive an iden from the db name
        iden = f'auth:{dbname}'
        await s_nexus.Pusher.__anit__(self, iden, nexsroot=nexsroot)

        self.dbname = dbname

        self.slab = slab
        self.stor = self.slab.getSafeKeyVal(dbname)

        if seed is None:
            seed = s_common.guid()

        self.maxusers = maxusers
        self.policy = policy

        self.userdefs = self.stor.getSubKeyVal('user:info:')
        self.useridenbyname = self.stor.getSubKeyVal('user:name:')
        self.userbyidencache = s_cache.FixedCache(self._getUser, size=1000)
        self.useridenbynamecache = s_cache.FixedCache(self._getUserIden, size=1000)

        self.roledefs = self.stor.getSubKeyVal('role:info:')
        self.roleidenbyname = self.stor.getSubKeyVal('role:name:')
        self.rolebyidencache = s_cache.FixedCache(self._getRole, size=1000)
        self.roleidenbynamecache = s_cache.FixedCache(self._getRoleIden, size=1000)

        self.gatedefs = self.stor.getSubKeyVal('gate:info:')
        self.authgates = s_cache.FixedCache(self._getAuthGate, size=1000)

        self.allrole = await self.getRoleByName('all')
        if self.allrole is None:
            # initialize the role of which all users are a member
            guid = s_common.guid((seed, 'auth', 'role', 'all'))
            await self._addRole(guid, 'all')
            self.allrole = self.role(guid)

        # initialize an admin user named root
        self.rootuser = await self.getUserByName('root')
        if self.rootuser is None:
            guid = s_common.guid((seed, 'auth', 'user', 'root'))
            await self._addUser(guid, 'root')
            self.rootuser = self.user(guid)

        await self.rootuser.setAdmin(True, logged=False)
        await self.rootuser.setLocked(False, logged=False)

    def users(self):
        for useriden in self.useridenbyname.values():
            userinfo = self.userdefs.get(useriden)
            yield User(userinfo, self)

    def roles(self):
        for roleiden in self.roleidenbyname.values():
            roleinfo = self.roledefs.get(roleiden)
            yield Role(roleinfo, self)

    def role(self, iden):
        return self.rolebyidencache.get(iden)

    def _getRole(self, iden):
        roleinfo = self.roledefs.get(iden)
        if roleinfo is not None:
            return Role(roleinfo, self)

    def user(self, iden):
        return self.userbyidencache.get(iden)

    def _getUser(self, iden):
        userinfo = self.userdefs.get(iden)
        if userinfo is not None:
            return User(userinfo, self)

    async def reqUser(self, iden):
        user = self.user(iden)
        if user is None:
            mesg = f'No user with iden {iden}.'
            raise s_exc.NoSuchUser(mesg=mesg, user=iden)
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
            raise s_exc.NoSuchUser(mesg=mesg, username=name)
        return user

    async def reqUserByNameOrIden(self, name):
        user = await self.getUserByName(name)
        if user is not None:
            return user

        user = self.user(name)
        if user is None:
            mesg = f'No user with name or iden {name}.'
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
            User: A User.  May return None if there is no user by the requested name.
        '''
        useriden = self.useridenbynamecache.get(name)
        if useriden is not None:
            return self.user(useriden)

    async def getUserIdenByName(self, name):
        return self.useridenbynamecache.get(name)

    def _getUserIden(self, name):
        return self.useridenbyname.get(name)

    async def getRoleByName(self, name):
        roleiden = self.roleidenbynamecache.get(name)
        if roleiden is not None:
            return self.role(roleiden)

    def _getRoleIden(self, name):
        return self.roleidenbyname.get(name)

    # TODO convert getUserByName() and getRoleByName()
    # back from async? These were plumbed to avoid infecting
    # type norm/repr functions with async...
    def _getRoleByName(self, name):
        roleiden = self.roleidenbynamecache.get(name)
        if roleiden is not None:
            return self.role(roleiden)

    def _getUserByName(self, name):
        useriden = self.useridenbynamecache.get(name)
        if useriden is not None:
            return self.user(useriden)

    @s_nexus.Pusher.onPushAuto('user:profile:set')
    async def setUserProfileValu(self, iden, name, valu):
        user = await self.reqUser(iden)
        return user.profile.set(name, valu)

    @s_nexus.Pusher.onPushAuto('user:profile:pop')
    async def popUserProfileValu(self, iden, name, default=None):
        user = await self.reqUser(iden)
        return user.profile.pop(name, defv=default)

    @s_nexus.Pusher.onPushAuto('user:var:set')
    async def setUserVarValu(self, iden, name, valu):
        user = await self.reqUser(iden)
        return user.vars.set(name, valu)

    @s_nexus.Pusher.onPushAuto('user:var:pop')
    async def popUserVarValu(self, iden, name, default=None):
        user = await self.reqUser(iden)
        return user.vars.pop(name, defv=default)

    @s_nexus.Pusher.onPushAuto('user:name')
    async def setUserName(self, iden, name):
        if not isinstance(name, str):
            raise s_exc.BadArg(mesg='setUserName() name must be a string')

        user = await self.getUserByName(name)
        if user is not None:
            if user.iden == iden:
                return
            raise s_exc.DupUserName(mesg=f'Duplicate username, {name=} already exists.', name=name)

        user = await self.reqUser(iden)

        if user.iden == self.rootuser.iden:
            raise s_exc.BadArg(mesg='Cannot change the name of the root user.')

        self.useridenbyname.set(name, iden)
        self.useridenbyname.delete(user.name)
        self.useridenbynamecache.pop(name)
        self.useridenbynamecache.pop(user.name)

        user.name = name
        user.info['name'] = name
        self.userdefs.set(iden, user.info)

        beheld = {
            'iden': iden,
            'valu': name,
        }
        await self.feedBeholder('user:name', beheld)

    @s_nexus.Pusher.onPushAuto('role:name')
    async def setRoleName(self, iden, name):
        if not isinstance(name, str):
            raise s_exc.BadArg(mesg='setRoleName() name must be a string')

        role = await self.getRoleByName(name)
        if role is not None:
            if role.iden == iden:
                return
            raise s_exc.DupRoleName(mesg=f'Duplicate role name, {name=} already exists.', name=name)

        role = await self.reqRole(iden)

        if role.name == 'all':
            mesg = 'Role "all" may not be renamed.'
            raise s_exc.BadArg(mesg=mesg)

        self.roleidenbyname.set(name, iden)
        self.roleidenbyname.delete(role.name)
        self.roleidenbynamecache.pop(name)
        self.roleidenbynamecache.pop(role.name)

        role.name = name
        role.info['name'] = name
        self.roledefs.set(iden, role.info)

        beheld = {
            'iden': iden,
            'valu': name,
        }
        await self.feedBeholder('role:name', beheld)

    async def feedBeholder(self, evnt, info, gateiden=None, logged=True):
        if self.nexsroot and self.nexsroot.started and logged:
            behold = {
                'event': evnt,
                'offset': await self.nexsroot.index(),
                'info': info
            }

            if gateiden:
                gate = self.getAuthGate(gateiden)
                if gate:
                    behold['gates'] = [gate.pack()]

            await self.fire('cell:beholder', **behold)

    async def setUserInfo(self, iden, name, valu, gateiden=None, logged=True, mesg=None):

        user = await self.reqUser(iden)

        if name == 'locked' and not valu and user.isArchived():
            raise s_exc.BadArg(mesg='Cannot unlock archived user.', user=iden, username=user.name)

        if name in ('locked', 'archived') and not valu:
            self.checkUserLimit()

        await self._push('user:info', iden, name, valu, gateiden=gateiden, logged=logged, mesg=mesg)

    @s_nexus.Pusher.onPush('user:info')
    async def _setUserInfo(self, iden, name, valu, gateiden=None, logged=True, mesg=None):
        user = await self.reqUser(iden)

        if self.nexsroot and self.nexsroot.cell.nexsvers >= (2, 198):
            # If the nexus version is less than 2.197 then the leader hasn't been upgraded yet and
            # we don't want to get into a schism because we're bouncing edits and the leader is
            # applying them.
            if name == 'locked' and not valu and user.isArchived():
                return

        if name in ('locked', 'archived') and not valu:
            self.checkUserLimit()

        if gateiden is not None:
            info = user.genGateInfo(gateiden)
            info[name] = s_msgpack.deepcopy(valu)
            gate = self.reqAuthGate(gateiden)
            gate.users.set(iden, info)

            user.info['authgates'][gateiden] = info
            self.userdefs.set(iden, user.info)
        else:
            user.info[name] = s_msgpack.deepcopy(valu)
            self.userdefs.set(iden, user.info)

        if mesg is None:
            mesg = {
                'iden': iden,
                'name': name,
            }
            if name != 'passwd':
                mesg['valu'] = valu

        await self.feedBeholder('user:info', mesg, gateiden=gateiden, logged=logged)

        if name == 'locked':
            await self.fire('user:lock', user=iden, locked=valu)

        # since any user info *may* effect auth
        user.clearAuthCache()

    @s_nexus.Pusher.onPushAuto('role:info')
    async def setRoleInfo(self, iden, name, valu, gateiden=None, logged=True, mesg=None):
        role = await self.reqRole(iden)

        if gateiden is not None:
            info = role.genGateInfo(gateiden)
            info[name] = s_msgpack.deepcopy(valu)
            gate = self.reqAuthGate(gateiden)
            gate.roles.set(iden, info)

            role.info['authgates'][gateiden] = info
            self.roledefs.set(iden, role.info)
        else:
            role.info[name] = s_msgpack.deepcopy(valu)
            self.roledefs.set(iden, role.info)

        if mesg is None:
            mesg = {
                'iden': iden,
                'name': name,
                'valu': valu,
            }
        await self.feedBeholder('role:info', mesg, gateiden=gateiden, logged=logged)

        role.clearAuthCache()

    async def addAuthGate(self, iden, authgatetype):
        '''
        Retrieve AuthGate by iden.  Create if not present.

        Note:
            Not change distributed

        Returns:
            (AuthGate)
        '''
        gate = self.getAuthGate(iden)
        if gate is not None:
            if gate.type != authgatetype:
                raise s_exc.InconsistentStorage(mesg=f'Stored AuthGate is of type {gate.type}, not {authgatetype}')
            return gate

        info = {
            'iden': iden,
            'type': authgatetype
        }
        self.gatedefs.set(iden, info)

        gate = AuthGate(info, self)
        self.authgates.put(iden, gate)

        return gate

    async def delAuthGate(self, iden):
        '''
        Delete AuthGate by iden.

        Note:
            Not change distributed
        '''
        gate = self.getAuthGate(iden)
        if gate is None:
            raise s_exc.NoSuchAuthGate(iden=iden)

        await gate.delete()

    def getAuthGate(self, iden):
        return self.authgates.get(iden)

    def _getAuthGate(self, iden):
        gateinfo = self.gatedefs.get(iden)
        if gateinfo is not None:
            return AuthGate(gateinfo, self)

    def getAuthGates(self):
        for gateinfo in self.gatedefs.values():
            yield AuthGate(gateinfo, self)

    def reqAuthGate(self, iden):
        gate = self.authgates.get(iden)
        if gate is None:
            mesg = f'No auth gate found with iden: ({iden}).'
            raise s_exc.NoSuchAuthGate(iden=iden, mesg=mesg)
        return gate

    def reqNoAuthGate(self, iden):
        if self.authgates.get(iden) is not None:
            mesg = f'An auth gate already exists with iden: ({iden}).'
            raise s_exc.DupIden(iden=iden, mesg=mesg)

    def checkUserLimit(self):
        '''
        Check if we're at the specified user limit.

        This should be called right before adding/unlocking/unarchiving a user.

        Raises: s_exc.HitLimit if the number of active users is at the maximum.
        '''
        if self.maxusers == 0:
            return

        numusers = 0

        for user in self.users():
            if user.name == 'root':
                continue

            if user.isLocked() or user.isArchived():
                continue

            numusers += 1

        if numusers >= self.maxusers:
            mesg = f'Cell at maximum number of users ({self.maxusers}).'
            raise s_exc.HitLimit(mesg=mesg)

    async def addUser(self, name, passwd=None, email=None, iden=None):
        '''
        Add a User to the Auth system.

        Args:
            name (str): The name of the User.
            passwd (str): A optional password for the user.
            email (str): A optional email for the user.
            iden (str): A optional iden to use as the user iden.

        Returns:
            User: A User.
        '''

        self.checkUserLimit()

        if self.useridenbynamecache.get(name) is not None:
            raise s_exc.DupUserName(mesg=f'Duplicate username, {name=} already exists.', name=name)

        if iden is None:
            iden = s_common.guid()
        else:
            if not s_common.isguid(iden):
                raise s_exc.BadArg(name='iden', arg=iden, mesg='Argument it not a valid iden.')

            if self.userdefs.get(iden) is not None:
                raise s_exc.DupIden(name=name, iden=iden,
                                    mesg='User already exists for the iden.')

        await self._push('user:add', iden, name)

        user = self.user(iden)

        # Everyone's a member of 'all'
        await user.grant(self.allrole.iden)

        if email is not None:
            await self.setUserInfo(user.iden, 'email', email)

        if passwd is not None:
            await user.setPasswd(passwd)

        return user

    @s_nexus.Pusher.onPush('user:add')
    async def _addUser(self, iden, name):

        user = self.useridenbynamecache.get(name)
        if user is not None:
            return

        self.reqNoAuthGate(iden)

        info = {
            'iden': iden,
            'name': name,
            'admin': False,
            'roles': (),
            'rules': (),
            'passwd': None,
            'locked': False,
            'archived': False,
            'authgates': {},
        }

        self.userdefs.set(iden, info)
        self.useridenbyname.set(name, iden)

        user = User(info, self)
        self.userbyidencache.put(iden, user)
        self.useridenbynamecache.put(name, iden)

        await self.feedBeholder('user:add', user.pack())

    async def addRole(self, name, iden=None):
        '''
        Add a Role to the Auth system.

        Args:
            name (str): The name of the role.
            iden (str): A optional iden to use as the role iden.

        Returns:
            Role: A Role.
        '''
        if self.roleidenbynamecache.get(name) is not None:
            raise s_exc.DupRoleName(mesg=f'Duplicate role name, {name=} already exists.', name=name)

        if iden is None:
            iden = s_common.guid()
        else:
            if not s_common.isguid(iden):
                raise s_exc.BadArg(name='iden', arg=iden, mesg=f'Argument {iden} it not a valid iden.')

            if self.rolebyidencache.get(iden) is not None:
                raise s_exc.DupIden(name=name, iden=iden,
                                    mesg=f'Role already exists for {iden=}.')

        await self._push('role:add', iden, name)

        return self.role(iden)

    @s_nexus.Pusher.onPush('role:add')
    async def _addRole(self, iden, name):

        role = self.roleidenbynamecache.get(name)
        if role is not None:
            return

        self.reqNoAuthGate(iden)

        info = {
            'iden': iden,
            'name': name,
            'admin': False,
            'rules': (),
            'authgates': {},
        }

        self.roledefs.set(iden, info)
        self.roleidenbyname.set(name, iden)

        role = Role(info, self)
        self.rolebyidencache.put(iden, role)
        self.roleidenbynamecache.put(name, iden)

        await self.feedBeholder('role:add', role.pack())

    async def delUser(self, iden):

        await self.reqUser(iden)
        return await self._push('user:del', iden)

    @s_nexus.Pusher.onPush('user:del')
    async def _delUser(self, iden):

        if iden == self.rootuser.iden:
            mesg = 'User "root" may not be deleted.'
            raise s_exc.BadArg(mesg=mesg)

        user = self.user(iden)
        if user is None:
            return

        udef = user.pack()
        self.userbyidencache.pop(user.iden)
        self.useridenbynamecache.pop(user.name)

        for gateiden in user.authgates.keys():
            gate = self.getAuthGate(gateiden)
            if gate is not None:
                await gate._delGateUser(user.iden)

        await user.vars.truncate()
        await user.profile.truncate()
        self.userdefs.delete(iden)
        self.useridenbyname.delete(user.name)

        await self.fire('user:del', udef=udef)
        await self.feedBeholder('user:del', {'iden': iden})

    def _getUsersInRole(self, role):
        for user in self.users():
            if role.iden in user.info.get('roles', ()):
                yield user

    async def delRole(self, iden):
        await self.reqRole(iden)
        return await self._push('role:del', iden)

    @s_nexus.Pusher.onPush('role:del')
    async def _delRole(self, iden):

        if iden == self.allrole.iden:
            mesg = 'Role "all" may not be deleted.'
            raise s_exc.BadArg(mesg=mesg)

        role = self.role(iden)
        if role is None:
            return

        for user in self._getUsersInRole(role):
            await user.revoke(role.iden, nexs=False)

        for gateiden in role.authgates.keys():
            gate = self.getAuthGate(gateiden)
            if gate is not None:
                await gate._delGateRole(role.iden)

        self.rolebyidencache.pop(role.iden)
        self.roleidenbynamecache.pop(role.name)

        self.roledefs.delete(iden)
        self.roleidenbyname.delete(role.name)
        await self.feedBeholder('role:del', {'iden': iden})

    def clearAuthCache(self):
        '''
        Clear all auth caches.
        '''
        self.userbyidencache.clear()
        self.useridenbynamecache.clear()
        self.rolebyidencache.clear()
        self.roleidenbynamecache.clear()
        self.authgates.clear()

class AuthGate():
    '''
    The storage object for object specific rules for users/roles.
    '''
    def __init__(self, info, auth):

        self.auth = auth

        self.iden = info.get('iden')
        self.type = info.get('type')

        self.gateroles = {}  # iden -> role info
        self.gateusers = {}  # iden -> user info

        self.users = auth.stor.getSubKeyVal(f'gate:{self.iden}:user:')
        self.roles = auth.stor.getSubKeyVal(f'gate:{self.iden}:role:')

        for useriden, userinfo in self.users.items():
            self.gateusers[useriden] = userinfo

        for roleiden, roleinfo in self.roles.items():
            self.gateroles[roleiden] = roleinfo

    def genUserInfo(self, iden):
        userinfo = self.gateusers.get(iden)
        if userinfo is not None:  # pragma: no cover
            return userinfo

        self.gateusers[iden] = userinfo = {}
        return userinfo

    def genRoleInfo(self, iden):
        roleinfo = self.gateroles.get(iden)
        if roleinfo is not None:  # pragma: no cover
            return roleinfo

        self.gateroles[iden] = roleinfo = {}
        return roleinfo

    async def _delGateUser(self, iden):
        self.gateusers.pop(iden, None)
        self.users.delete(iden)

    async def _delGateRole(self, iden):
        self.gateroles.pop(iden, None)
        self.roles.delete(iden)

    async def delete(self):

        for useriden in self.gateusers.keys():
            user = self.auth.user(useriden)
            if user.authgates.pop(self.iden) is not None:
                self.auth.userdefs.set(useriden, user.info)
                user.clearAuthCache()

        for roleiden in self.gateroles.keys():
            role = self.auth.role(roleiden)
            if role.authgates.pop(self.iden) is not None:
                self.auth.roledefs.set(roleiden, role.info)
                role.clearAuthCache()

        self.auth.gatedefs.delete(self.iden)
        self.auth.authgates.pop(self.iden)
        await self.auth.stor.truncate(f'gate:{self.iden}:')

    def pack(self):
        users = []
        for useriden, userinfo in self.gateusers.items():
            users.append({
                'iden': useriden,
                'rules': userinfo.get('rules', ()),
                'admin': userinfo.get('admin', False),
            })

        roles = []
        for roleiden, roleinfo in self.gateroles.items():
            roles.append({
                'iden': roleiden,
                'rules': roleinfo.get('rules', ()),
                'admin': roleinfo.get('admin', False),
            })

        return {
            'iden': self.iden,
            'type': self.type,
            'users': users,
            'roles': roles,
        }

class Ruler():
    '''
    An object that holds a list of rules.  This includes Users, Roles, and the AuthGate variants of those
    '''

    def __init__(self, info, auth):

        self.auth = auth
        self.info = info
        self.name = info.get('name')
        self.iden = info.get('iden')

        self.authgates = info.get('authgates')

    async def _setRulrInfo(self, name, valu, gateiden=None, nexs=True, mesg=None):  # pragma: no cover
        raise s_exc.NoSuchImpl(mesg='Subclass must implement _setRulrInfo')

    def getRules(self, gateiden=None):

        if gateiden is None:
            return list(self.info.get('rules', ()))

        gateinfo = self.authgates.get(gateiden)
        if gateinfo is None:
            return []

        return list(gateinfo.get('rules', ()))

    async def setRules(self, rules, gateiden=None, nexs=True, mesg=None):
        s_schemas.reqValidRules(rules)
        return await self._setRulrInfo('rules', rules, gateiden=gateiden, nexs=nexs, mesg=mesg)

    async def addRule(self, rule, indx=None, gateiden=None, nexs=True):
        s_schemas.reqValidRules((rule,))
        rules = self.getRules(gateiden=gateiden)

        mesg = {
            'name': 'rule:add',
            'iden': self.iden,
            'valu': rule,
        }
        if indx is None:
            rules.append(rule)
        else:
            rules.insert(indx, rule)
            mesg['indx'] = indx

        await self.setRules(rules, gateiden=gateiden, nexs=nexs, mesg=mesg)

    async def delRule(self, rule, gateiden=None):
        s_schemas.reqValidRules((rule,))
        rules = self.getRules(gateiden=gateiden)
        if rule not in rules:
            return False

        mesg = {
            'name': 'rule:del',
            'iden': self.iden,
            'valu': rule,
        }
        rules.remove(rule)
        await self.setRules(rules, gateiden=gateiden, mesg=mesg)
        return True

class Role(Ruler):
    '''
    A role within the authorization subsystem.

    A role in Auth exists to bundle rules together so that the same
    set of rules can be applied to multiple users.
    '''
    def pack(self):
        ret = {
            'type': 'role',
            'iden': self.iden,
            'name': self.name,
            'rules': self.info.get('rules'),
            'authgates': self.authgates,
        }
        return s_msgpack.deepcopy(ret)

    async def _setRulrInfo(self, name, valu, gateiden=None, nexs=True, mesg=None):
        if nexs:
            return await self.auth.setRoleInfo(self.iden, name, valu, gateiden=gateiden, mesg=mesg)
        else:
            return await self.auth._hndlsetRoleInfo(self.iden, name, valu, gateiden=gateiden, logged=nexs, mesg=mesg)

    async def setName(self, name):
        return await self.auth.setRoleName(self.iden, name)

    def clearAuthCache(self):
        for user in self.auth.userbyidencache.cache.values():
            if user is not None and user.hasRole(self.iden):
                user.clearAuthCache()

    def genGateInfo(self, gateiden):
        info = self.authgates.get(gateiden)
        if info is None:
            gate = self.auth.reqAuthGate(gateiden)
            info = self.authgates[gateiden] = gate.genRoleInfo(self.iden)
        return info

    def allowed(self, perm, default=None, gateiden=None):

        perm = tuple(perm)
        if gateiden is not None:
            info = self.authgates.get(gateiden)
            if info is not None:
                for allow, path in info.get('rules', ()):
                    if perm[:len(path)] == path:
                        return allow
            return default

        # 2. check role rules
        for allow, path in self.info.get('rules', ()):
            if perm[:len(path)] == path:
                return allow

        return default

class User(Ruler):
    '''
    A user (could be human or computer) of the system within Auth.

    Cortex-wide rules are stored here.  AuthGate-specific rules for this user are stored in an GateUser.
    '''
    def __init__(self, info, auth):
        Ruler.__init__(self, info, auth)

        self.vars = auth.stor.getSubKeyVal(f'user:{self.iden}:vars:')
        self.profile = auth.stor.getSubKeyVal(f'user:{self.iden}:profile:')

        self.permcache = s_cache.FixedCache(self._allowed)
        self.allowedcache = s_cache.FixedCache(self._getAllowedReason)

    def pack(self, packroles=False):

        roles = self.info.get('roles', ())
        if packroles:
            _roles = []
            for r in roles:
                role = self.auth.role(r)
                if role is None:
                    logger.error(f'User {self.iden} ({self.name}) contains a missing role: {r}')
                    continue
                _roles.append(role.pack())
            roles = _roles

        ret = {
            'type': 'user',
            'iden': self.iden,
            'name': self.name,
            'rules': self.info.get('rules'),
            'roles': roles,
            'admin': self.info.get('admin'),
            'email': self.info.get('email'),
            'locked': self.info.get('locked'),
            'archived': self.info.get('archived'),
            'authgates': self.authgates,
        }
        return s_msgpack.deepcopy(ret)

    async def _setRulrInfo(self, name, valu, gateiden=None, nexs=True, mesg=None):
        if nexs:
            return await self.auth.setUserInfo(self.iden, name, valu, gateiden=gateiden, mesg=mesg)
        else:
            return await self.auth._setUserInfo(self.iden, name, valu, gateiden=gateiden, logged=nexs, mesg=mesg)

    async def setName(self, name):
        return await self.auth.setUserName(self.iden, name)

    async def setProfileValu(self, name, valu):
        return await self.auth.setUserProfileValu(self.iden, name, valu)

    async def popProfileValu(self, name, default=None):
        return await self.auth.popUserProfileValu(self.iden, name, default=default)

    async def setVarValu(self, name, valu):
        return await self.auth.setUserVarValu(self.iden, name, valu)

    async def popVarValu(self, name, default=None):
        return await self.auth.popUserVarValu(self.iden, name, default=default)

    async def allow(self, perm):
        if not self.allowed(perm):
            await self.addRule((True, perm), indx=0)

    def allowed(self,
                perm: tuple[str, ...],
                default: Optional[str] = None,
                gateiden: Optional[str] = None,
                deepdeny: bool = False) -> Union[bool, None]:
        '''
        Check if a user is allowed a given permission.

        Args:
            perm: The permission tuple to check.
            default: The default rule value if there is no match.
            gateiden: The gate iden to check against.
            deepdeny: If True, give precedence for checking deny rules which are more specific than the requested
                      permission.

        Notes:
            The use of the deepdeny argument is intended for checking a less-specific part of a permissions tree, in
            order to know about possible short circuit options. Using it to check a more specific part may have
            unintended results.

        Returns:
            The allowed value of the permission.
        '''
        perm = tuple(perm)
        return self.permcache.get((perm, default, gateiden, deepdeny))

    def _allowed(self, pkey):
        '''
        NOTE: This must remain in sync with any changes to _getAllowedReason()!
        '''
        perm, default, gateiden, deepdeny = pkey

        if self.info.get('locked'):
            return False

        if self.info.get('admin'):
            return True

        if deepdeny and self._hasDeepDeny(perm, gateiden):
            return False

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

    def getAllowedReason(self, perm, default=None, gateiden=None):
        '''
        A routine which will return a tuple of (allowed, info).
        '''
        perm = tuple(perm)
        return self.allowedcache.get((perm, default, gateiden))

    def _getAllowedReason(self, pkey):
        '''
        NOTE: This must remain in sync with any changes to _allowed()!
        '''
        perm, default, gateiden = pkey
        if self.info.get('locked'):
            return _allowedReason(False, islocked=True)

        if self.info.get('admin'):
            return _allowedReason(True, isadmin=True)

        # 1. check authgate user rules
        if gateiden is not None:

            info = self.authgates.get(gateiden)
            if info is not None:

                if info.get('admin'):
                    return _allowedReason(True, isadmin=True, gateiden=gateiden)

                for allow, path in info.get('rules', ()):
                    if perm[:len(path)] == path:
                        return _allowedReason(allow, gateiden=gateiden, rule=path)

        # 2. check user rules
        for allow, path in self.info.get('rules', ()):
            if perm[:len(path)] == path:
                return _allowedReason(allow, rule=path)

        # 3. check authgate role rules
        if gateiden is not None:

            for role in self.getRoles():

                info = role.authgates.get(gateiden)
                if info is None:
                    continue

                for allow, path in info.get('rules', ()):
                    if perm[:len(path)] == path:
                        return _allowedReason(allow, gateiden=gateiden, roleiden=role.iden, rolename=role.name,
                                              rule=path)

        # 4. check role rules
        for role in self.getRoles():
            for allow, path in role.info.get('rules', ()):
                if perm[:len(path)] == path:
                    return _allowedReason(allow, roleiden=role.iden, rolename=role.name, rule=path)

        return _allowedReason(default, default=True)

    def _hasDeepDeny(self, perm, gateiden):

        permlen = len(perm)

        # 1. check authgate user rules
        if gateiden is not None:

            info = self.authgates.get(gateiden)
            if info is not None:

                if info.get('admin'):
                    return False

                for allow, path in info.get('rules', ()):
                    if allow:
                        continue
                    if path[:permlen] == perm and len(path) > permlen:
                        return True

        # 2. check user rules
        for allow, path in self.info.get('rules', ()):
            if allow:
                continue

            if path[:permlen] == perm and len(path) > permlen:
                return True

        # 3. check authgate role rules
        if gateiden is not None:

            for role in self.getRoles():

                info = role.authgates.get(gateiden)
                if info is None:
                    continue

                for allow, path in info.get('rules', ()):
                    if allow:
                        continue
                    if path[:permlen] == perm and len(path) > permlen:
                        return True

        # 4. check role rules
        for role in self.getRoles():
            for allow, path in role.info.get('rules', ()):
                if allow:
                    continue
                if path[:permlen] == perm and len(path) > permlen:
                    return True

        return False

    def clearAuthCache(self):
        self.permcache.clear()
        self.allowedcache.clear()

    def genGateInfo(self, gateiden):
        info = self.authgates.get(gateiden)
        if info is None:
            gate = self.auth.reqAuthGate(gateiden)
            info = gate.genUserInfo(self.iden)
        return info

    def confirm(self, perm, default=None, gateiden=None):
        if not self.allowed(perm, default=default, gateiden=gateiden):
            self.raisePermDeny(perm, gateiden=gateiden)

    def raisePermDeny(self, perm, gateiden=None):

        perm = '.'.join(perm)
        if gateiden is None:
            mesg = f'User {self.name!r} ({self.iden}) must have permission {perm}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.iden, username=self.name)

        gate = self.auth.reqAuthGate(gateiden)
        mesg = f'User {self.name!r} ({self.iden}) must have permission {perm} on object {gate.iden} ({gate.type}).'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.iden, username=self.name)

    def getRoles(self):
        for iden in self.info.get('roles', ()):
            role = self.auth.role(iden)
            if role is None:
                logger.warning(f'user {self.iden} has non-existent role: {iden}')
                continue
            yield role

    def hasRole(self, iden):
        return iden in self.info.get('roles', ())

    async def grant(self, roleiden, indx=None):

        role = await self.auth.reqRole(roleiden)

        roles = list(self.info.get('roles'))
        if role.iden in roles:
            return

        if indx is None:
            roles.append(role.iden)
        else:
            roles.insert(indx, role.iden)

        mesg = {'name': 'role:grant', 'iden': self.iden, 'role': role.pack()}
        await self.auth.setUserInfo(self.iden, 'roles', roles, mesg=mesg)

    async def setRoles(self, roleidens):
        '''
        Replace all the roles for a given user with a new list of roles.

        Args:
            roleidens (list): A list of roleidens.

        Notes:
            The roleiden for the "all" role must be present in the new list of roles. This replaces all existing roles
            that the user has with the new roles.

        Returns:
            None
        '''
        current_roles = list(self.info.get('roles'))

        roleidens = list(roleidens)

        if current_roles == roleidens:
            return

        if self.auth.allrole.iden not in roleidens:
            mesg = 'Role "all" must be in the list of roles set.'
            raise s_exc.BadArg(mesg=mesg)

        roles = []
        for iden in roleidens:
            r = await self.auth.reqRole(iden)
            roles.append(r.pack())

        mesg = {'name': 'role:set', 'iden': self.iden, 'roles': roles}
        await self.auth.setUserInfo(self.iden, 'roles', roleidens, mesg=mesg)

    async def revoke(self, iden, nexs=True):

        role = await self.auth.reqRole(iden)

        if role.name == 'all':
            mesg = 'Role "all" may not be revoked.'
            raise s_exc.BadArg(mesg=mesg)

        roles = list(self.info.get('roles'))
        if role.iden not in roles:
            return

        roles.remove(role.iden)
        mesg = {'name': 'role:revoke', 'iden': self.iden, 'role': role.pack()}
        if nexs:
            await self.auth.setUserInfo(self.iden, 'roles', roles, mesg=mesg)
        else:
            await self.auth._setUserInfo(self.iden, 'roles', roles, logged=nexs, mesg=mesg)

    def isLocked(self):
        return self.info.get('locked')

    def isAdmin(self, gateiden=None):

        # being a global admin always wins
        admin = self.info.get('admin', False)
        if admin or gateiden is None:
            return admin

        gateinfo = self.authgates.get(gateiden)
        if gateinfo is None:
            return False

        return gateinfo.get('admin', False)

    def reqAdmin(self, gateiden=None, mesg=None):

        if self.isAdmin(gateiden=gateiden):
            return

        if mesg is None:
            mesg = 'This action requires global admin permissions.'
            if gateiden is not None:
                mesg = f'This action requires admin permissions on gate: {gateiden}'

        raise s_exc.AuthDeny(mesg=mesg, user=self.iden, username=self.name)

    def isArchived(self):
        return self.info.get('archived')

    async def setAdmin(self, admin, gateiden=None, logged=True):
        if not isinstance(admin, bool):
            raise s_exc.BadArg(mesg='setAdmin requires a boolean')

        if self.iden == self.auth.rootuser.iden and not admin:
            raise s_exc.BadArg(mesg='Cannot remove admin from root user.')

        if logged:
            await self.auth.setUserInfo(self.iden, 'admin', admin, gateiden=gateiden)
        else:
            await self.auth._setUserInfo(self.iden, 'admin', admin, gateiden=gateiden, logged=logged)

    async def setLocked(self, locked, logged=True):
        if not isinstance(locked, bool):
            raise s_exc.BadArg(mesg='setLocked requires a boolean')

        if self.iden == self.auth.rootuser.iden and locked:
            raise s_exc.BadArg(mesg='Cannot lock admin root user.')

        resetAttempts = (
            not locked and
            self.info.get('policy:attempts', 0) > 0
        )

        if logged:
            await self.auth.setUserInfo(self.iden, 'locked', locked)
            if resetAttempts:
                await self.auth.setUserInfo(self.iden, 'policy:attempts', 0)

        else:
            await self.auth._setUserInfo(self.iden, 'locked', locked, logged=logged)
            if resetAttempts:
                await self.auth._setUserInfo(self.iden, 'policy:attempts', 0)

    async def setArchived(self, archived):
        if not isinstance(archived, bool):
            raise s_exc.BadArg(mesg='setArchived requires a boolean')

        if self.iden == self.auth.rootuser.iden and archived:
            raise s_exc.BadArg(mesg='Cannot archive root user.')

        await self.auth.setUserInfo(self.iden, 'archived', archived)
        if archived:
            await self.setLocked(True)

    async def tryPasswd(self, passwd, nexs=True, enforce_policy=True):

        if self.isLocked():
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
                        await self.auth.setUserInfo(self.iden, 'onepass', None)
                        logger.debug(f'Used one time password for {self.name}',
                                     extra={'synapse': {'user': self.iden, 'username': self.name}})
                        return True
            else:
                # Backwards compatible password handling
                expires, params, hashed = onepass
                if expires >= s_common.now():
                    if s_common.guid((params, passwd)) == hashed:
                        await self.auth.setUserInfo(self.iden, 'onepass', None)
                        logger.debug(f'Used one time password for {self.name}',
                                     extra={'synapse': {'user': self.iden, 'username': self.name}})
                        return True

        shadow = self.info.get('passwd')
        if shadow is None:
            return False

        if isinstance(shadow, dict):
            result = await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow)
            if self.auth.policy and (attempts := self.auth.policy.get('attempts')) is not None:
                valu = self.info.get('policy:attempts', 0)
                if result:
                    if valu > 0:
                        await self.auth.setUserInfo(self.iden, 'policy:attempts', 0)
                    return True

                if enforce_policy:

                    valu += 1
                    await self.auth.setUserInfo(self.iden, 'policy:attempts', valu)

                    if valu >= attempts:

                        if self.iden == self.auth.rootuser.iden:
                            mesg = f'User {self.name} has exceeded the number of allowed password attempts ({valu + 1}),. Cannot lock {self.name} user.'
                            extra = {'synapse': {'target_user': self.iden, 'target_username': self.name, }}
                            logger.error(mesg, extra=extra)
                            return False

                        await self.auth.nexsroot.cell.setUserLocked(self.iden, True)

                        mesg = f'User {self.name} has exceeded the number of allowed password attempts ({valu + 1}), locking their account.'
                        extra = {'synapse': {'target_user': self.iden, 'target_username': self.name, 'status': 'MODIFY'}}
                        logger.warning(mesg, extra=extra)

                    return False

            return result

        # Backwards compatible password handling
        salt, hashed = shadow
        if s_common.guid((salt, passwd)) == hashed:
            logger.debug(f'Migrating password to shadowv2 format for user {self.name}',
                         extra={'synapse': {'user': self.iden, 'username': self.name}})
            # Update user to new password hashing scheme. We cannot enforce policy
            # when migrating an existing password.
            await self.setPasswd(passwd=passwd, nexs=nexs, enforce_policy=False)

            return True

        return False

    async def _checkPasswdPolicy(self, passwd, shadow, nexs=True):
        if not self.auth.policy:
            return

        failures = []

        # Check complexity of password
        complexity = self.auth.policy.get('complexity')
        if complexity is not None:

            # Check password length
            minlen = complexity.get('length')
            if minlen is not None and (passwd is None or len(passwd) < minlen):
                failures.append(f'Password must be at least {minlen} characters.')

            if minlen is not None and passwd is None:
                # Set password to empty string so we get the rest of the failure info
                passwd = ''

            if passwd is None:
                return

            allvalid = []

            # Check uppercase
            count = complexity.get('upper:count', 0)
            if (valid := complexity.get('upper:valid', string.ascii_uppercase)):
                allvalid.append(valid)
                if count is not None and (found := len([k for k in passwd if k in valid])) < count:
                    failures.append(f'Password must contain at least {count} uppercase characters, {found} found.')

            # Check lowercase
            count = complexity.get('lower:count', 0)
            if (valid := complexity.get('lower:valid', string.ascii_lowercase)):
                allvalid.append(valid)

                if count is not None and (found := len([k for k in passwd if k in valid])) < count:
                    failures.append(f'Password must contain at least {count} lowercase characters, {found} found.')

            # Check special
            count = complexity.get('special:count', 0)
            if (valid := complexity.get('special:valid', string.punctuation)):
                allvalid.append(valid)

                if count is not None and (found := len([k for k in passwd if k in valid])) < count:
                    failures.append(f'Password must contain at least {count} special characters, {found} found.')

            # Check numbers
            count = complexity.get('number:count', 0)
            if (valid := complexity.get('number:valid', string.digits)):
                allvalid.append(valid)
                if count is not None and (found := len([k for k in passwd if k in valid])) < count:
                    failures.append(f'Password must contain at least {count} digit characters, {found} found.')

            if allvalid:
                allvalid = ''.join(allvalid)
                if (invalid := set(passwd) - set(allvalid)):
                    failures.append(f'Password contains invalid characters: {sorted(list(invalid))}')

            # Check sequences
            seqlen = complexity.get('sequences')
            if seqlen is not None:
                # Convert each character to it's ordinal value so we can look for
                # forward and reverse sequences in windows of seqlen. Doing it this
                # way allows us to easily check unicode sequences too.
                passb = [ord(k) for k in passwd]
                for offs in range(len(passwd) - (seqlen - 1)):
                    curv = passb[offs]
                    fseq = list(range(curv, curv + seqlen))
                    rseq = list(range(curv, curv - seqlen, -1))
                    window = passb[offs:offs + seqlen]
                    if window == fseq or window == rseq:
                        failures.append(f'Password must not contain forward/reverse sequences longer than {seqlen} characters.')
                        break

        # Check for previous password reuse
        prevvalu = self.auth.policy.get('previous')
        if prevvalu is not None:
            previous = self.info.get('policy:previous', ())
            for prevshad in previous:
                if await s_passwd.checkShadowV2(passwd, prevshad):
                    failures.append(f'Password cannot be the same as previous {prevvalu} password(s).')
                    break

        if failures:
            mesg = ['Cannot change password due to the following policy violations:']
            mesg.extend(f'  - {msg}' for msg in failures)
            raise s_exc.BadArg(mesg='\n'.join(mesg), failures=failures)

        if prevvalu is not None:
            # Looks like this password is good, add it to the list of previous passwords
            previous = self.info.get('policy:previous', ())
            previous = (shadow,) + previous
            if nexs:
                await self.auth.setUserInfo(self.iden, 'policy:previous', previous[:prevvalu])
            else:
                await self.auth._setUserInfo(self.iden, 'policy:previous', previous[:prevvalu], logged=nexs)

    async def setPasswd(self, passwd, nexs=True, enforce_policy=True):
        # Prevent empty string or non-string values
        if passwd is None:
            shadow = None
            enforce_policy = False
        elif passwd and isinstance(passwd, str):
            shadow = await s_passwd.getShadowV2(passwd=passwd)
        else:
            raise s_exc.BadArg(mesg='Password must be a string')

        if enforce_policy:
            await self._checkPasswdPolicy(passwd, shadow, nexs=nexs)

        if nexs:
            await self.auth.setUserInfo(self.iden, 'passwd', shadow)
        else:
            await self.auth._setUserInfo(self.iden, 'passwd', shadow, logged=nexs)
