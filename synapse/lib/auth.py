import os
import lmdb
import logging
import functools
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.reactor as s_react

import synapse.lib.tufo as s_tufo
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class Rules:
    '''
    Rules provides an abstraction for metadata
    based filtration of events and tufos.

    Each "rule" is a tuple of:
        (allow, perm): (bool, (str, dict))
    '''

    def __init__(self, rules):
        self._r_rules = rules
        self._r_match = s_cache.MatchCache()
        self._r_rules_by_perm = s_cache.Cache(onmiss=self._onRulesPermMiss)

    def _onRulesPermMiss(self, name):
        retn = []
        for rule in self._r_rules:
            if self._r_match.match(name, rule[1][0]):
                retn.append(rule)
        return retn

    def _cmprule(self, rule, perm):

        for prop, must in rule[1][1].items():

            valu = perm[1].get(prop)
            if valu is None:
                return False

            if not self._r_match.match(valu, must):
                return False

        return True

    def allow(self, perm):
        '''
        Returns True if the given perm/info is allowed by the rules.

        Args:
            perm ((str,dict)): The requested permission tuple

        Returns:
            (bool):  True if the rules allow the perm/info
        '''
        for rule in self._r_rules_by_perm.get(perm[0]):
            if self._cmprule(rule, perm):
                return rule[0]

        return False

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

def reqAdmin(f):
    @functools.wraps(f)
    def _f(*args, **kwargs):
        auth = getattr(args[0], '_mxauth', None)  # type: s_auth.Auth
        if not auth:
            raise s_exc.ReqConfOpt(mesg='requires _mxauth on local object')
        uname = whoami()
        uobj = auth.reqUser(uname)
        if not uobj.admin:
            raise s_exc.AuthDeny(mesg='Operation requires admin',
                                 name=f.__qualname__)
        logger.info('Executing [%s][%s][%s] as [%s]',
                    f.__qualname__, args, kwargs, uname)
        return f(*args, **kwargs)

    return _f

class AuthMixin:
    def __init__(self, auth):
        '''
        A mixin that can be used to provide helpers around Auth objects.
        All calls to the helper APIs require the current user in scope to be a
        admin user.

        Args:
            auth (Auth):
        '''
        self._mxauth = auth
        self._mxrtor = s_react.Reactor()
        self._mxrtor.act('auth:get:users', self.__authGetUsers)
        self._mxrtor.act('auth:get:roles', self.__authGetRoles)
        # User actions
        self._mxrtor.act('auth:add:user', self.__authAddUser)
        self._mxrtor.act('auth:del:user', self.__authDelUser)
        self._mxrtor.act('auth:req:user', self.__authReqUser)
        self._mxrtor.act('auth:add:urole', self.__authAddUserRole)
        self._mxrtor.act('auth:add:urule', self.__authAddUserRule)
        self._mxrtor.act('auth:del:urole', self.__authDelUserRole)
        self._mxrtor.act('auth:del:urule', self.__authDelUserRule)
        # User admin actions
        self._mxrtor.act('auth:add:admin', self.__authAddAdmin)
        self._mxrtor.act('auth:del:admin', self.__authDelAdmin)
        # Role actions
        self._mxrtor.act('auth:req:role', self.__authReqRole)
        self._mxrtor.act('auth:add:role', self.__authAddRole)
        self._mxrtor.act('auth:del:role', self.__authDelRole)
        self._mxrtor.act('auth:add:rrule', self.__authAddRoleRule)
        self._mxrtor.act('auth:del:rrule', self.__authDelRoleRule)

    def authReact(self, mesg):
        '''
        General interface for interfacing with auth.

        Args:
            mesg:

        Returns:
            (bool, ((str, dict))): isok, retn tufo
        '''
        try:
            isok, retn = self._mxrtor.react(mesg)
        except Exception as e:
            logger.exception('Failed to process mesg [%s]', mesg)
            retn = s_common.getexcfo(e)
            isok = False
        finally:
            return isok, retn

    @reqAdmin
    def __authGetUsers(self, mesg):
        mname, mdict = mesg
        users = self._mxauth.getUsers()
        ret = (mname, {'users': users})
        return True, ret

    @reqAdmin
    def __authGetRoles(self, mesg):
        mname, mdict = mesg
        roles = self._mxauth.getRoles()
        ret = (mname, {'roles': roles})
        return True, ret

    @reqAdmin
    def __authReqUser(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        uobj = self._mxauth.reqUser(name)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authReqRole(self, mesg):
        mname, mdict = mesg
        name = mdict.get('role')
        robj = self._mxauth.reqRole(name)
        ret = s_tufo.tufo(mname, role=(name, robj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authAddUser(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        uobj = self._mxauth.addUser(name)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authDelUser(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        _ret = self._mxauth.delUser(name)
        ret = s_tufo.tufo(mname, user=name, deleted=_ret)
        return True, ret

    @reqAdmin
    def __authDelRole(self, mesg):
        mname, mdict = mesg
        name = mdict.get('role')
        _ret = self._mxauth.delRole(name)
        ret = s_tufo.tufo(mname, role=name, deleted=_ret)
        return True, ret

    @reqAdmin
    def __authAddRole(self, mesg):
        mname, mdict = mesg
        name = mdict.get('role')
        robj = self._mxauth.addRole(name)
        ret = s_tufo.tufo(mname, role=(name, robj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authAddUserRule(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        rule = mdict.get('rule')
        uobj = self._mxauth.reqUser(name)
        uobj.addRule(rule)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authDelUserRule(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        rule = mdict.get('rule')
        uobj = self._mxauth.reqUser(name)
        uobj.delRule(rule)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authAddRoleRule(self, mesg):
        mname, mdict = mesg
        name = mdict.get('role')
        rule = mdict.get('rule')
        robj = self._mxauth.reqRole(name)
        robj.addRule(rule)
        ret = s_tufo.tufo(mname, role=(name, robj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authDelRoleRule(self, mesg):
        mname, mdict = mesg
        name = mdict.get('role')
        rule = mdict.get('rule')
        robj = self._mxauth.reqRole(name)
        robj.delRule(rule)
        ret = s_tufo.tufo(mname, role=(name, robj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authAddAdmin(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        uobj = self._mxauth.reqUser(name)
        uobj.setAdmin(True)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authDelAdmin(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        uobj = self._mxauth.reqUser(name)
        uobj.setAdmin(False)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authAddUserRole(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        role = mdict.get('role')
        uobj = self._mxauth.reqUser(name)
        robj = self._mxauth.reqRole(role)
        uobj.addRole(role)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

    @reqAdmin
    def __authDelUserRole(self, mesg):
        mname, mdict = mesg
        name = mdict.get('user')
        role = mdict.get('role')
        uobj = self._mxauth.reqUser(name)
        robj = self._mxauth.reqRole(role)
        uobj.delRole(role)
        ret = s_tufo.tufo(mname, user=(name, uobj._getAuthData()))
        return True, ret

class Auth(s_config.Config):
    '''
    An authorization object which can help enforce cortex rules.
    '''

    def __init__(self, dirn, conf=None):

        s_config.Config.__init__(self, opts=conf)

        path = os.path.join(dirn, 'auth.lmdb')

        mapsize = self.getConfOpt('lmdb:mapsize')

        self.lenv = lmdb.open(path, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.onfini(self.lenv.close)

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

    def initConfDefs(self):
        self.addConfDefs((
            ('lmdb:mapsize', {'type': 'int', 'defval': s_const.gigabyte,
                'doc': 'Memory map size for the auth LMDB.'}),
        ))

    def addUser(self, name):
        '''
        Add a new user to the auth system.

        Args:
            name (str): The user name.

        Returns:
            (synapse.lib.auth.User): The newly created user.
        '''

        with self.lenv.begin(write=True) as xact:

            if self.users.get(name) is not None:
                raise s_exc.DupUserName(name=name)

            user = User(self, name)
            self.users[name] = user

            uenc = name.encode('utf8')
            byts = s_msgpack.en(user._getAuthData())

            xact.put(uenc, byts, db=self._db_users)
            return user

    def delUser(self, name):
        '''
        Delete a user from the auth system.

        Args:
            name (str): The user name to delete.
        '''
        with self.lenv.begin(write=True) as xact:

            user = self.users.pop(name, None)
            if user is None:
                raise s_exc.NoSuchUser(name=name)

            uenc = name.encode('utf8')
            xact.delete(uenc, db=self._db_users)
        return True

    def addRole(self, name):
        '''
        Add a new role to the auth system.

        Args:
            name (str): The role name.

        Returns:
            (synapse.lib.auth.Role): The newly created role.
        '''
        with self.lenv.begin(write=True) as xact:

            if self.roles.get(name) is not None:
                raise s_exc.DupRoleName(name=name)

            # Role() does rdef validation
            role = Role(self, name)
            self.roles[name] = role

            renc = name.encode('utf8')
            byts = s_msgpack.en(role._getAuthData())

            xact.put(renc, byts, db=self._db_roles)
            return role

    def delRole(self, name):
        '''
        Delete a role from the auth system.

        Args:
            name (str): The user name to delete.
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
                    byts = s_msgpack.en(user._getAuthData())

                    xact.put(nenc, byts, db=self._db_users)
        return True

    def _iterAuthDefs(self, xact, db):

        with xact.cursor(db=db) as curs:

            for nenc, byts in curs.iternext():
                name = nenc.decode('utf8')
                info = s_msgpack.un(byts)

                yield name, info

    def _saveAuthData(self, name, info, db):

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

        Returns:
            list:
        '''
        return list(self.users.keys())

    def getRoles(self):
        '''

        Returns:
            list:
        '''
        return list(self.roles.keys())

    def reqUser(self, user):
        '''

        Args:
            user (str):

        Returns:
            User:
        '''
        user = self.users.get(user)
        if not user:
            raise s_exc.NoSuchUser(user=user)
        return user

    def reqRole(self, role):
        '''

        Args:
            role (str):

        Returns:
            Role:
        '''
        role = self.roles.get(role)
        if not role:
            raise s_exc.NoSuchRole(role=role)
        return role


class TagTree:
    '''
    A tag-oriented hierarchical permissions tree.
    '''
    def __init__(self):
        self.root = (False, {})
        self.cache = {}

    def clear(self):
        '''
        Clear the tag tree and cache.
        '''
        self.cache.clear()
        self.root = (False, {})

    def add(self, tag):
        '''
        Add a tag to the tree.

        Args:
            tag (str): The tag (with no #)
        '''
        node = self.root
        for name in tag.split('.'):

            step = node[1].get(name)
            if step is None:
                step = node[1][name] = [False, {}]

            node = step

        node[0] = True
        self.cache.clear()

    def get(self, tag):
        '''
        Get a tag status from the tree.
        ( hierarchical permissions )
        '''
        retn = self.cache.get(tag)
        if retn is not None:
            return retn

        node = self.root
        for name in tag.split('.'):

            step = node[1].get(name)
            if step is None:
                self.cache[tag] = False
                return False

            if step[0]:
                self.cache[tag] = True
                return True

            node = step

        return False

class AuthBase:
    '''
    ('node:add', {'form': <form>}),
    ('node:del', {'form': <form>}),

    ('node:prop:set', {'form': <form>, 'prop': <prop>})

    ('node:tag:add', {'tag': <tag>}),
    ('node:tag:del', {'tag': <tag>}),

    # * may be used to mean "any" for form/prop values.
    # ( since tags are implemented as a perm tree, they do not need wild cards yet )
    '''
    def __init__(self, auth, name, info=None):

        if info is None:
            info = {}

        self.auth = auth
        self.info = info

        # it is ok for callers to access these...
        self.name = name

        self.admin = info.get('admin', False)
        self.rules = list(info.get('rules', ()))

        self._add_funcs = {
            'node:add': self._addNodeAdd,
            'node:del': self._addNodeDel,

            'node:prop:set': self._addNodeSet,

            'node:tag:add': self._addTagAdd,
            'node:tag:del': self._addTagDel,
        }

        self._may_funcs = {
            'node:add': self._mayNodeAdd,
            'node:del': self._mayNodeDel,

            'node:prop:set': self._mayNodeSet,

            'node:tag:add': self._mayTagAdd,
            'node:tag:del': self._mayTagDel,
        }

        #self.permcache = s_cache.KeyCache(self._allowed)

        # tags are a tree.  so are the perms.
        self._tag_add = TagTree()
        self._tag_del = TagTree()

        self._node_add = {} # <form>: True
        self._node_del = {} # <form>: True
        self._node_set = {} # (<form>,<prop>): True

        self._initAuthData()

    def setAdmin(self, admin):

        admin = bool(admin)
        if admin == self.admin:
            return admin

        self.admin = admin
        self._syncAuthData()
        return admin

    def addRule(self, rule):
        '''
        Add an allow rule.

        Args:
            rule ((str,dict)): A rule tufo.
        '''
        ret = self._addRuleTufo(rule)
        if not ret:
            return ret
        self.rules.append(rule)
        self._syncAuthData()
        return ret

    def delRule(self, rule):
        '''
        Remove an allow rule.

        Args:
            rule ((str,dict)): A rule tufo.
        '''
        try:
            self.rules.remove(rule)
        except ValueError:
            raise s_exc.NoSuchRule(rule=rule, name=self.name,
                                   mesg='Rule does not exist')
        self._syncAuthData()
        self._initAuthData()
        return True

    def _getAuthData(self):
        return {
            'admin': self.admin,
            'rules': self.rules,
        }

    def allowed(self, perm, elev=True):
        '''
        Check if the user/role is allowed the given permission.

        Args:
            perm ((str,dict)): A permission tuple.
            elev (bool): If true, allow admin status.
        '''
        if self.admin and elev:
            return True

        func = self._may_funcs.get(perm[0])
        if func is None:
            logger.warning('unknown perm: %r' % (perm,))
            return False

        try:
            return func(perm)

        except Exception as e:
            logger.warning('AuthBase "may" func error: %r' % (perm,))
            return False

    def _syncAuthData(self):
        self.info = self._getAuthData()
        self._saveAuthData()

    def _saveAuthData(self):  # pragma: no cover
        raise s_exc.NoSuchImpl(name='_saveAuthData',
                               mesg='_saveAuthData not implemented by AuthBase')

    def _initAuthData(self):

        self._node_add.clear()
        self._node_del.clear()
        self._node_set.clear()

        self._tag_add.clear()
        self._tag_del.clear()

        [self._addRuleTufo(rule) for rule in self.rules]

    def _addRuleTufo(self, rule):

        func = self._add_funcs.get(rule[0])
        if func is None:
            logger.warning('no such rule func: %r' % (rule,))
            return False

        try:
            func(rule)
        except Exception as e:
            logger.exception('rule function error: %r' % (rule,))
            return False

        return True
    #####################################################

    def _addNodeAdd(self, rule):
        form = rule[1].get('form')
        if not form:
            raise s_exc.BadRuleValu(key='form', valu=form,
                                    mesg='node:add requires "form"')
        self._node_add[form] = True

    def _addNodeDel(self, rule):
        form = rule[1].get('form')
        if not form:
            raise s_exc.BadRuleValu(key='form', valu=form,
                                    mesg='node:del requires "form"')
        self._node_del[form] = True

    def _addNodeSet(self, rule):
        form = rule[1].get('form')
        prop = rule[1].get('prop')
        if not form:
            raise s_exc.BadRuleValu(key='form', valu=form,
                                    mesg='node:set:prop requires "form"')
        if not prop:
            raise s_exc.BadRuleValu(key='valu', valu=prop,
                                    mesg='node:set:prop requires "prop"')
        self._node_set[(form, prop)] = True

    def _addTagAdd(self, rule):
        tag = rule[1].get('tag')
        if not tag:
            raise s_exc.BadRuleValu(key='tag', valu=tag,
                                    mesg='node:tag:add requires "tag"')
        self._tag_add.add(tag)

    def _addTagDel(self, rule):
        tag = rule[1].get('tag')
        if not tag:
            raise s_exc.BadRuleValu(key='tag', valu=tag,
                                    mesg='node:tag:del requires "tag"')
        self._tag_del.add(tag)

    #####################################################

    def _mayNodeAdd(self, perm):

        form = perm[1].get('form')

        if self._node_add.get(form):
            return True

        if self._node_add.get('*'):
            return True

        return False

    def _mayNodeDel(self, perm):

        form = perm[1].get('form')

        if self._node_del.get(form):
            return True

        if self._node_del.get('*'):
            return True

        return False

    def _mayNodeSet(self, perm):

        form = perm[1].get('form')
        prop = perm[1].get('prop')

        if self._node_set.get((form, prop)):
            return True

        if self._node_set.get((form, '*')):
            return True

        return False

    def _mayTagAdd(self, perm):
        tag = perm[1].get('tag')
        return self._tag_add.get(tag)

    def _mayTagDel(self, perm):
        tag = perm[1].get('tag')
        return self._tag_del.get(tag)

    #####################################################

class Role(AuthBase):

    def _saveAuthData(self):
        info = {
            'admin': self.admin,
            'rules': self.rules
        }
        self.auth._saveRoleInfo(self.name, info)

class User(AuthBase):

    def _getAuthData(self):
        info = AuthBase._getAuthData(self)
        info['roles'] = list(self.roles.keys())
        return info

    def _saveAuthData(self):
        info = self._getAuthData()
        self.auth._saveUserInfo(self.name, info)

    def _initAuthData(self):

        AuthBase._initAuthData(self)

        self.roles = {}

        for name in self.info.get('roles', ()):

            role = self.auth.roles.get(name)

            if role is None:  # pragma: no cover
                logger.warning('user has non-existant role: %r' % (name,))
                continue

            self.roles[name] = role

    def allowed(self, perm, elev=True):
        '''
        Check if a user is allowed the given permission.

        Args:
            perm ((str,dict)): A permission tuple.
            elev (bool): If true, allow admin status.
        '''

        if AuthBase.allowed(self, perm, elev=elev):
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
        '''
        role = self.auth.roles.get(name)
        if role is None:
            raise s_exc.NoSuchRole(name=name)

        self.roles[name] = role
        self._saveAuthData()
        return True

    def delRole(self, name):
        '''
        Revoke a role from a user.

        Args:
            name (str): The name of the role to revoke.
        '''
        role = self.roles.pop(name, None)
        if role is None:
            return False

        self._saveAuthData()
        return True
