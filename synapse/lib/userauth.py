import hashlib
import fnmatch
import contextlib

import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope

from synapse.common import *
from synapse.eventbus import EventBus

class Rules:
    '''
    Glob based rules evaluator class (with caching).

    The Rules cache will use the UserAuth event bus to sync.
    '''
    def __init__(self, auth, user):

        self.user = user
        self.auth = auth

        self.auth.on('syn:auth:bump:%s' % user, self._onBumpUser )

        # only triggered if auth is a proxy and reconnects
        self.auth.on('tele:sock:init', self._onTeleSock )

        self.cache = {}
        self.rules = auth.getUserRules(user)

    def _onTeleSock(self, mesg):
        self.rules = self.auth.getUserRules(user)
        self.cache.clear()

    def _onBumpUser(self, mesg):
        self.rules = mesg[1].get('rules')
        self.cache.clear()

    def allow(self, perm):
        '''
        Check if the current rules allow the given perm.

        Example:

            if rules.allow('foo.bar'):
                dostuff()

        '''
        ret = self.cache.get(perm)

        if ret == None:
            ret = False
            for rule in self.rules:
                if fnmatch.fnmatch(perm,rule):
                    ret = True
                    break

            self.cache[perm] = ret

        return ret

class UserAuth(EventBus):
    '''
    Store users, roles, and rules for AAA in a cortex.
    '''
    def __init__(self, core):
        EventBus.__init__(self)

        self.core = core

        self.core.addTufoForm('syn:auth:user')
        self.core.addTufoProp('syn:auth:user','apikey', defval='')
        self.core.addTufoProp('syn:auth:user','shadow:sha256', defval='')

        self.core.addTufoForm('syn:auth:role')

        self.core.addTufoForm('syn:auth:userrole')
        self.core.addTufoProp('syn:auth:userrole','user')
        self.core.addTufoProp('syn:auth:userrole','role')

        self.users = s_cache.TufoPropCache(core,'syn:auth:user')
        self.roles = s_cache.TufoPropCache(core,'syn:auth:role')

        self.rules = s_cache.KeyCache(self._getUserRulesCache)

    def addUser(self, user, **props):
        '''
        Add a user to the UserAuth cortex.
        '''
        if self.users.get(user) != None:
            raise DupUser(user)

        usfo = self.core.formTufoByProp('syn:auth:user', user, **props)
        self.users.put(user,usfo)

        return usfo

    def getUser(self, user):
        '''
        Return a user tufo or None by name.

        Example:

            user = auth.getUser('visi')
            if role != None:
                dostuff(role)
        '''
        return self.users.get(user)

    def getRole(self, role):
        '''
        Return a role tufo or None by name.

        Example:

            role = auth.getRole('admin')
            if role != None:
                dostuff(role)

        '''

    def addUserRule(self, user, rule):
        '''
        Add a rule glob for a user.
        '''
        usfo = self._reqUserTufo(user)
        self.core.addTufoList(usfo, 'auth:rules', rule)
        self._bumpUserRules(user)

    def getUserRoles(self, user):
        '''
        Return a list of the roles for the given user.
        '''
        usfo = self._reqUserTufo(user)
        userroles = self.core.getTufosByProp('syn:auth:userrole:user',user)
        return [ u[1].get('syn:auth:userrole:role') for u in userroles ]

    def addUserRole(self, user, role):
        '''
        Grant a role to a user.
        '''
        usfo = self._reqUserTufo(user)
        rofo = self._reqRoleTufo(role)

        props = {'user':user,'role':role}
        self.core.formTufoByProp('syn:auth:userrole', '%s:%s' % (user,role), **props)

        self._bumpUserRules(user)

    def _bumpUserRules(self, user):
        rules = self.getUserRules(user)
        self.fire('syn:auth:bump:%s' % user, rules=rules)

    def delUserRole(self, user, role):
        '''
        Revoke a role from a user.
        '''
        usfo = self._reqUserTufo(user)
        rofo = self._reqRoleTufo(role)

        self.core.delTufoByProp('syn:auth:userrole', '%s:%s' % (user,role))

        self._bumpUserRules(user)

    def addRoleRule(self, role, rule):
        '''
        Add a rule glob for the given role.
        '''
        rofo = self._reqRoleTufo(role)
        self.core.addTufoList(rofo,'auth:rules',rule)

        for userrole in self.core.getTufosByProp('syn:auth:userrole:role',role):
            user = userrole[1].get('syn:auth:userrole:user')
            self._bumpUserRules(user)

    def delRoleRule(self, role, rule):
        '''
        Delete a rule for the given role.
        '''
        rofo = self._reqRoleTufo(role)
        self.core.delTufoListValu(rofo,'auth:rules',rule)

        for userrole in self.core.getTufosByProp('syn:auth:userrole:role',role):
            user = userrole[1].get('syn:auth:userrole:user')
            self._bumpUserRules(user)

    def delUserRule(self, user, rule):
        '''
        Delete a rule for the given user.
        '''
        usfo = self._reqUserTufo(user)
        self.core.delTufoListValu(usfo,'auth:rules',rule)
        self._bumpUserRules(user)

    def addRole(self, role, **props):
        '''
        Add a new role to the UserAuth cortex.
        '''
        if self.roles.get(role) != None:
            raise DupRole(role)

        rofo = self.core.formTufoByProp('syn:auth:role', role, **props)
        self.roles.put(role,rofo)
        return rofo

    def delUser(self, user):
        '''
        Delete a user ( and associated userroles ) by name.

        Example:

            auth.delUser('visi')

        '''
        usfo = self._reqUserTufo(user)
        self.core.delTufoByProp('syn:auth:user', user)
        self.core.delTufosByProp('syn:auth:userrole:user',user)

        self.users.pop(user)
        self.rules.pop(user)

    def delRole(self, role):
        '''
        Delete a role ( and associated userroles ) by name.

        Example:

            auth.delRole('root')

        '''
        rofo = self._reqRoleTufo(role)
        userroles = self.core.getTufosByProp('syn:auth:userrole:role', role)

        users = [ u[1].get('syn:auth:userrole:user') for u in userroles ]

        self.core.delTufosByProp('syn:auth:role', role)
        self.core.delTufosByProp('syn:auth:userrole:role', role)

        self.roles.pop(role)
        [ self._bumpUserRules(user) for user in users ]

    def getUserRules(self, user):
        usfo = self._reqUserTufo(user)
        rules = self.core.getTufoList(usfo,'auth:rules')

        for userrole in self.core.getTufosByProp('syn:auth:userrole:user', user):
            rofo = self.roles.get( userrole[1].get('syn:auth:userrole:role') )
            rules.extend( self.core.getTufoList(rofo,'auth:rules') )

        return rules

    def _getUserRulesCache(self, user):
        return Rules(self, user)

    def isUserAllowed(self, user, perm):
        '''
        Returns True if a users rules ( or their roles rules ) allow a perm.
        '''
        rules = self.rules.get(user)
        return rules.allow(perm)

    def setUserProp(self, user, prop, valu):
        usfo = self._reqUserTufo(user)
        self.core.setTufoProp(usfo, prop, valu)

    def setRoleProp(self, role, prop, valu):
        rofo = self._reqRoleTufo(role)
        self.core.setTufoProp(rofo, prop, valu)

    def _reqUserTufo(self, user):
        usfo = self.users.get(user)
        if usfo == None:
            raise NoSuchUser(user)
        return usfo

    def _reqRoleTufo(self, role):
        rofo = self.roles.get(role)
        if rofo == None:
            raise NoSuchRole(role)
        return rofo

def opencore(url,**opts):
    '''
    Construct a UserAuth object around the given cortex URL.
    '''
    import synapse.cortex as s_cortex
    core = s_cortex.openurl(url,**opts)
    return UserAuth(core)

def getSynUser():
    '''
    Return the name of the current synapse user for this thread.

    Example:

        name = s_userauth.getSynUser()

    '''
    return s_scope.get('syn:user')

def getSynAuth():
    '''
    Return the current UserAuth object for the current thread.

    Example:

        auth = s_userauth.getSynAuth()

    '''
    return s_scope.get('syn:auth')

def amIAllowed(rule, onnone=False):
    '''
    Retuns True if the current synapse user and UserAuth allow the
    user access via the given rule.  If there is not currently a
    UserAuth for the calling thread, the onnone value is returned,
    allowing a "default allow" or "default deny" stance.

    Example:

        if s_userauth.amIAllowed('foo:bar:baz'):
            doFooBarBaz()

    '''
    auth = getSynAuth()
    if auth == None:
        return onnone

    # if we have an auth and user is None, deny.
    # ( it's probably a code / scope error )
    user = getSynUser()
    if user == None:
        return False

    return auth.isUserAllowed(user,rule)

@contextlib.contextmanager
def asSynUser(user, auth=None, **locs):
    '''
    Construct and return a with-block object which runs as the given
    synapse user name. Locs may be optionally populated with additional
    items to be added to the LocalScope instance.

    Example:

        import synapse.lib.userauth as s_userauth

        s_userauth.asSynUser('visi@localhost'):
            # calls from here down may use check user/perms
            dostuff()

    '''
    with s_scope.enter({'syn:user':user,'syn:auth':auth}):
        yield
