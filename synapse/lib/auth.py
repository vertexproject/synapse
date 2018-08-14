import os
import logging
import functools
import contextlib

import lmdb

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.scope as s_scope
import synapse.lib.trees as s_trees
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

authver = (0, 0, 1)

def whoami():
    '''
    Return the name of the current synapse user for this thread.

    Example:

        name = s_auth.whoami()

    '''
    return s_scope.get('syn:user', 'root@localhost')

@contextlib.contextmanager
def runas(user):
    '''
    Construct and return a with-block object which runs as the given
    synapse user name.

    Example:

        import synapse.lib.auth as s_auth

        s_auth.runas('visi@localhost'):
            # calls from here down may use check user/perms
            dostuff()

    '''
    with s_scope.enter({'syn:user': user}):
        yield

def reqAdmin(f, attr='auth'):
    '''
    A Decorator to wrap a function to require it to be executed in a admin user context.

    Args:
        f: Function being wrapped.
        attr (str): Name of Auth local.

    Notes:
        This decorator should only be placed on methods on a class since it relies
        on having access to a local instance of a Auth object.

    Returns:
        Function results.

    Raises:
        s_exc.ReqConfOpt: If the auth local is not found on the object.
        s_exc.NoSuchUser: If the Auth local does not have a instance of the current user.
        s_exc.AuthDeny: If the user in scope is not a admin user.
    '''
    @functools.wraps(f)
    def _f(*args, **kwargs):
        auth = getattr(args[0], attr, None)  # type: s_auth.Auth
        if not auth:
            raise s_exc.ReqConfOpt(mesg='requires attr on local object',
                                   attr=attr)
        uname = whoami()
        uobj = auth.reqUser(uname)
        if not uobj.admin:
            raise s_exc.AuthDeny(mesg='Operation requires admin',
                                 name=f.__qualname__, user=uname)
        logger.info('Executing [%s][%s][%s] as [%s]',
                    f.__qualname__, args, kwargs, uname)
        return f(*args, **kwargs)

    return _f

class AuthApi(s_cell.CellApi):

    def tryTeleAuth(self, auth):
        '''
        Return a (name, info, roles) tuple for a User or None.
        '''
        name, info = auth
        user = self.cell.users.get(user)
        if user is None:
            return None

        roles = []

        for rolename, role in user.roles.items():
            roles.append((rolename, role.info))

        return (name, user.info, roles)

class Auth(s_cell.Cell):
    '''
    An authentication / authorization management helper.
    '''
    cellapi = AuthApi

    confdefs = (
        ('lmdb:mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_SMALL_MAP_SIZE,
            'doc': 'Memory map size for the auth LMDB.'}),
    )

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        path = os.path.join(dirn, 'auth.lmdb')

        mapsize = self.conf.get('lmdb:mapsize')

        self.lenv = lmdb.open(path, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        def authFini():
            self.lenv.sync()
            self.lenv.close()

        self.onfini(authFini)

        self._db_users = self.lenv.open_db(b'users')
        self._db_roles = self.lenv.open_db(b'roles')

        # these may be used by Auth() callers
        self.users = {}
        self.roles = {}

        with self.lenv.begin() as xact:

            for name, info in self._iterAuthDefs(xact, self._db_roles):
                self.roles[name] = Role(self, name, info)

            for name, info in self._iterAuthDefs(xact, self._db_users):
                self.users[name] = User(self, name, info)

    def initCellAuth(self):
        # we *are* the auth...
        self.auth = self

    def initConfDefs(self):
        self.addConfDefs((
            ('lmdb:mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_SMALL_MAP_SIZE,
                'doc': 'Memory map size for the auth LMDB.'}),
        ))

    def addUser(self, name, passwd=None):
        '''
        Add a new user to the auth system.

        Args:
            name (str): The user name.

        Returns:
            User: The newly created user.

        Raises:
            s_exc.DupUserName: If the user already exists.
        '''
        with self.lenv.begin(write=True) as xact:

            if self.users.get(name) is not None:
                raise s_exc.DupUserName(name=name)

            if self.roles.get(name) is not None:
                raise s_exc.DupUserName(name=name)

            user = User(self, name, {})
            self.users[name] = user

            uenc = name.encode('utf8')

            user.info['vers'] = authver
            byts = s_msgpack.en(user.info)

            xact.put(uenc, byts, db=self._db_users)
            return user

    def delUser(self, name):
        '''
        Delete a user from the auth system.

        Args:
            name (str): The user name to delete.

        Returns:
            True: True if the operation succeeded.

        Raises:
            s_exc.NoSuchUser: If the user did not exist.
        '''
        with self.lenv.begin(write=True) as xact:

            user = self.users.pop(name, None)
            if user is None:
                raise s_exc.NoSuchUser(user=name)

            uenc = name.encode('utf8')
            xact.delete(uenc, db=self._db_users)
        return True

    def addRole(self, name):
        '''
        Add a new role to the auth system.

        Args:
            name (str): The role name.

        Returns:
            Role: The newly created role.

        Raises:
            s_exc.DupRoleName: If the role already exists.
        '''
        with self.lenv.begin(write=True) as xact:

            if self.roles.get(name) is not None:
                raise s_exc.DupRoleName(name=name)

            if self.users.get(name) is not None:
                raise s_exc.DupRoleName(name=name)

            # Role() does rdef validation
            role = Role(self, name, {})
            self.roles[name] = role

            renc = name.encode('utf8')
            role.info['vers'] = authver

            byts = s_msgpack.en(role.info)

            xact.put(renc, byts, db=self._db_roles)
            return role

    def delRole(self, name):
        '''
        Delete a role from the auth system.

        Args:
            name (str): The user name to delete.

        Returns:
            True: True if the operation succeeded.

        Raises:
            s_exc.NoSuchRole: If the role does not exist.
        '''
        with self.lenv.begin(write=True) as xact:

            role = self.roles.pop(name, None)
            if role is None:
                raise s_exc.NoSuchRole(name=name)

            nenc = name.encode('utf8')
            xact.delete(nenc, db=self._db_roles)

            for user in self.users.values():

                role = user.roles.pop(name, None)
                if role is not None:
                    nenc = user.name.encode('utf8')
                    data = user._getAuthData()
                    data['vers'] = authver
                    byts = s_msgpack.en(data)

                    xact.put(nenc, byts, db=self._db_users)
        return True

    def _iterAuthDefs(self, xact, db):

        with xact.cursor(db=db) as curs:

            for nenc, byts in curs.iternext():
                name = nenc.decode('utf8')
                info = s_msgpack.un(byts)

                yield name, info

    def _saveAuthData(self, name, info, db):
        info['vers'] = authver
        with self.lenv.begin(write=True) as xact:
            lkey = name.encode('utf8')
            lval = s_msgpack.en(info)
            xact.put(lkey, lval, db=db)

    def _saveUserInfo(self, user, info):
        self._saveAuthData(user, info, self._db_users)

    def _saveRoleInfo(self, role, info):
        self._saveAuthData(role, info, self._db_roles)

    def getUsers(self):
        '''
        Get a list of user names.

        Returns:
            list: List of user names.
        '''
        return list(self.users.keys())

    def getRoles(self):
        '''
        Get a list of roles.

        Returns:
            list: List of role names.
        '''
        return list(self.roles.keys())

    def reqUser(self, user):
        '''
        Get a user object.

        Args:
            user (str): Username to request.

        Returns:
            User: User object.

        Raises:
            s_exc.NoSuchUser: If the user does not exist.
        '''
        user = self.users.get(user)
        if not user:
            raise s_exc.NoSuchUser(user=user)
        return user

    def reqRole(self, role):
        '''
        Get a role object.

        Args:
            role (str): Name of the role object to get.

        Returns:
            Role: Role object.

        Raises:
            s_exc.NoSuchRole: If the role does not exist.
        '''
        role = self.roles.get(role)
        if not role:
            raise s_exc.NoSuchRole(role=role)
        return role

class Role:
    '''
    A Role within the auth system.
    '''
    def __init__(self, auth, name, info):

        # it is ok for callers to access these...
        self.name = name
        self.info = info
        self.auth = auth

        info.setdefault('type', self.__class__.__name__.lower())
        info.setdefault('rules', ())
        info.setdefault('admin', False)

        self.admin = info.get('admin')
        self.rules = list(info.get('rules'))

        self.initRuleTree()

    def __str__(self):
        return self.name

    def setAdmin(self, admin):
        '''
        Set the admin value to True/False.

        Args:
            admin (bool): Value to set the admin value too.

        Returns:
            bool: The current AuthBase admin value.
        '''
        admin = bool(admin)
        if admin == self.admin:
            return admin

        self.admin = admin
        self.info['admin'] = admin

        self.save()

        return admin

    def addRule(self, rule, indx=None):
        '''
        Add an allow rule.

        Args:
            rule (bool, tuple): Add an allow/deny and path tuple.
            indx (int): The index for where to insert the rule.

        Returns:
            bool: True if the rule was added. False otherwise.
        '''
        if indx:
            self.rules.insert(indx, rule)
        else:
            self.rules.append(rule)

        self.info['rules'] = tuple(self.rules)

        self.initRuleTree()

        self.save()
        return True

    def initRuleTree(self):
        self.ruletree = s_trees.Tree()
        for allowed, path in self.rules:
            self.ruletree.put(path, allowed)

    def delRule(self, indx):
        '''
        Remove an allow rule.

        Args:
            indx (int): The rule number to remove.

        Returns:
            True:

        Raises:
            s_exc.NoSuchRule: If the rule did not exist.
        '''
        try:
            self.rules.pop(indx)
        except IndexError:
            mesg = 'Rule index invalid'
            raise s_exc.NoSuchRule(mesg=mesg)

        self.info['rules'] = tuple(self.rules)
        self.initRuleTree()

        self.save()
        return True

    def allowed(self, perm, elev=True):
        '''
        Check if the user/role is allowed the given permission.

        Args:
            perm ((str,)): A permission path tuple.
            elev (bool): If true, allow admin status.

        Returns:
            bool: True if the permission is allowed. False otherwise.
        '''
        if self.admin and elev:
            return True

        return self.ruletree.last(perm)

    def save(self):
        self.auth._saveRoleInfo(self.name, self.info)

class User(Role):

    def __init__(self, auth, name, info):

        Role.__init__(self, auth, name, info)
        self.info.setdefault('roles', ())

        self.roles = {}
        self.locked = self.info.get('locked', False)

        for name in self.info.get('roles'):
            self.roles[name] = self.auth.roles.get(name)

        self.shadow = info.get('shadow')

    def save(self):
        self.auth._saveUserInfo(self.name, self.info)

    def tryPasswd(self, passwd):

        if self.locked:
            return False

        if passwd is None:
            return False

        if self.shadow is None:
            return False

        salt, hashed = self.shadow
        if s_common.guid((salt, passwd)) == hashed:
            return True

        return False

    def setPasswd(self, passwd):

        salt = s_common.guid()
        hashed = s_common.guid((salt, passwd))

        self.shadow = (salt, hashed)
        self.info['shadow'] = self.shadow

        self.save()

    def setLocked(self, locked):
        self.locked = locked
        self.info['locked'] = locked
        self.save()

    def allowed(self, perm, elev=True):
        '''
        Check if a user is allowed the given permission.

        Args:
            perm (tuple): A permission path tuple.
            elev (bool): If true, allow admin status.

        Returns:
            bool: True if the permission is allowed. False otherwise.
        '''
        if self.locked:
            return False

        if Role.allowed(self, perm, elev=elev):
            return True

        for name, role in self.roles.items():
            if role.allowed(perm, elev=elev):
                return True

        return False

    def addRole(self, name):
        '''
        Grant a role to a user.

        Args:
            name (str): The name of the role to grant.

        Returns:
            True:

        Raises:
            s_exc.NoSuchRole: If the role does not exist.
        '''
        role = self.auth.roles.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        self.roles[name] = role
        self.info['roles'] = tuple(self.roles.keys())

        self.save()
        return True

    def delRole(self, name):
        '''
        Revoke a role from a user.

        Args:
            name (str): The name of the role to revoke.

        Returns:
            bool: True if the role was removed; False if the role was not on the user.
        '''
        role = self.roles.pop(name, None)
        if role is None:
            return False

        self.info['roles'] = tuple(self.roles.keys())

        self.save()
        return True
