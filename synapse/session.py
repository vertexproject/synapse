import fnmatch
import threading

import synapse.cache as s_cache

from synapse.eventbus import EventBus
from synapse.common import *

sesslocal = threading.local()

def current():
    '''
    Return the current Sess() or None.
    '''
    try:
        return sesslocal.sess
    except AttributeError as e:
        return None

class Sess(EventBus):

    def __init__(self, boss, sess):
        EventBus.__init__(self)
        self.sid = sess[0]
        self.boss = boss
        self.sess = sess
        self.local = {}      # runtime only props

    def getUserPerm(self, user, perm):
        if self.get('user') == None:
            return (None,None,False)

        return self.boss.getUserPerm(user,perm)

    def get(self, prop):
        prop = 'sess:%s' % prop
        return self.sess[1].get(prop)

    def set(self, prop, valu):
        prop = 'sess:%s' % prop
        self.boss.core.setTufoProp(self.sess,prop,valu)

    def __enter__(self):
        sesslocal.sess = self
        return self

    def __exit__(self, exc, cls, tb):
        sesslocal.sess = None

onehour = 60 * 60
class Curator(EventBus):

    def __init__(self, core=None, maxtime=onehour):
        EventBus.__init__(self)

        if core == None:
            # FIXME avoid dep loop.  reorg.
            import synapse.cortex as s_cortex
            core = s_cortex.openurl('ram:///')

        self.core = core

        self.sessions = s_cache.Cache(maxtime=maxtime)
        self.sessions.setOnMiss( self._getSessBySid )
        self.sessions.on('cache:pop', self._onSessCachePop )
        self.onfini( self.sessions.fini )

        self.users = s_cache.TufoPropCache(core,'auth:user',maxtime=onehour)
        self.onfini( self.users.fini )

        self.roles = s_cache.TufoPropCache(core,'auth:role',maxtime=onehour)
        self.onfini( self.roles.fini )

        self.rules = s_cache.Cache(maxtime=onehour)
        self.rules.setOnMiss( self._getRulesByName )
        self.onfini( self.rules.fini )

        self.perms = s_cache.Cache()
        self.perms.setOnMiss( self._getUserPerm )
        self.onfini( self.perms.fini )

    def _onSessCachePop(self, event):
        sess = event[1].get('val')
        sess.fini()

    def __iter__(self):
        return self.sessions.values()

    def getSessBySid(self, sid):
        '''
        Return a session tufo by id.

        Example:

            sess = boss.getSessBySid(sid)

        '''
        return self.sessions.get(sid)

    def _getSessBySid(self, sid):
        # look up the tufo and construct a Sess()
        sess = self.core.getTufoByProp('sess',sid)
        if sess == None:
            return None

        return Sess(self,sess)

    def getNewSess(self):
        '''
        Create a new session and return the tufo.

        Example:

            sess = boss.getNewSess()

        '''
        sid = guidstr()
        now = int(time.time())

        props = {
            'sess:root': 0,
            'sess:init': now,
        }

        sess = (sid,props)
        self.fire('sess:form',sess=sess)

        rows = [ (sid,p,v,now) for (p,v) in props.items() ]

        self.core.addRows(rows)

        self.fire('sess:init', sess=sess)

        ret = Sess(self,sess)
        self.sessions.put(sid,ret)

        return ret

    def getUserPerm(self, user, perm):
        '''
        Return a (role,rule,allow) tuple for the given perm.

        Example:

            perm = 'foo.bar'
            as,rule,allow = auth.getUserPerm('visi',perm)
            if allow:
                print('as: %s you may %s (because: %s)' % (as,perm,rule))

        '''
        return self.perms.get( (user,perm) )

    def getUserRoles(self, user):
        print('FIXME: getUserRoles')
        return []

    def _getUserPerm(self, userperm):

        user,perm = userperm

        denies,allows = self.getRulesByName(user)

        for rule in denies:
            if fnmatch.fnmatch(perm,rule):
                return (user,rule,False)

        for rule in allows:
            if fnmatch.fnmatch(perm,rule):
                return (user,rule,True)

        for role in self.getUserRoles(user):

            denies,allows = self.getRulesByName(role)
            for rule in denies:
                if fnmatch.fnmatch(perm,rule):
                    return (role,rule,False)

            for rule in allows:
                if fnmatch.fnmatch(perm,rule):
                    return (role,rule,True)

        return (user,None,False)

    def addDenyRule(self, name, rule):
        '''
        Add a user/role deny rule.

        Example:

            auth.addDenyRule('visi','foo.*')

        '''
        prop = 'rule:%s:deny' % name
        self.core.addListRows(prop,rule)
        self._bumpRuleCache(name)

    def addAllowRule(self, name, rule):
        '''
        Add a user/role allow rule.

        Example:

            auth.addAllowRule('visi','*')

        '''
        prop = 'rule:%s:allow' % name
        self.core.addListRows(prop,rule)
        self._bumpRuleCache(name)

    def getRulesByName(self, name):
        '''
        Return the (denies,allows) rules for a user/role.
        '''
        return self.rules.get(name)

    def _getRulesByName(self, name):
        drows = self.core.getRowsByProp('rule:%s:deny' % name)
        arows = self.core.getRowsByProp('rule:%s:allow' % name)

        denies = [ v for (i,p,v,t) in drows ]
        allows = [ v for (i,p,v,t) in arows ]
        return denies,allows

    def _bumpRuleCache(self, name):
        # bump rules cache
        self.rules.pop(name)

        # bump perms cache
        keys = self.perms.keys()
        keys = [ k for k in keys if k[0] == name ]
        [ self.perms.pop(k) for k in keys ]
        # FIXME unit test deny then allow

    def getUserByName(self, name):
        '''
        Return a user tufo by user:name.

        Example:

            user = auth.getUserByName('invisigoth')

        '''
        return self.users.get(name)

    def setUserProp(self, name, prop, valu):
        '''
        Set a property in the named user tufo.
        '''
        user = self.users.get(name)
        if user == None:
            raise NoSuchUser(name)

        self.core.setTufoProp(user,prop,valu)

    def setRoleProp(self, name, prop, valu):
        '''
        set a property in the named role tufo.

        Example:

            auth.setRoleProp('role:haha','hehe')

        '''
        role = self.roles.get(name)
        if role == None:
            raise NoSuchRole(name)

        self.core.setTufoProp(role,prop,valu)

    def getRoleByName(self, name):
        '''
        Return a role tufo by name.

        Example:

            role = auth.getRoleByName('kenshoto')

        '''
        return self.roles.get(name)

    def addUserName(self, name, **props):
        '''
        Add a user to the SessAuth cortex.
        '''
        if self.users.get(name) != None:
            raise DupUser(name)

        user = self.core.formTufoByProp('auth:user',name,**props)

        self.users.pop(name) # pop possible None from cache

        self.fire('auth:user:add', user=user)
        return user

    def addRoleName(self, name, **props):
        '''
        '''
        if self.roles.get(name) != None:
            raise DupRole(name)

        role = self.core.formTufoByProp('auth:role',name,**props)

        self.roles.pop(name) # pop possible None from cache

        self.fire('auth:role:add', role=role)
        return role

    def delUserByName(self, name):
        '''
        '''
        user = self.getUserByName(name)
        if user == None:
            raise NoSuchUser(name)

        self.fire('auth:user:del', user=user)

        self.core.delRowsById(user[0])
        self.core.delRowsByProp('rule:%s:deny' % name)
        self.core.delRowsByProp('rule:%s:allow' % name)

        self.users.pop(name)
        self._bumpRuleCache(name)

        return user

    def delRoleByName(self, name):
        role = self.getRoleByName(name)
        if role == None:
            raise NoSuchRole(name)

        self.fire('auth:role:del', role=role)

        self.core.delRowsById(role[0])
        self.core.delRowsByProp('rule:%s:deny' % name)
        self.core.delRowsByProp('rule:%s:allow' % name)

        self.roles.pop(name)
        self._bumpRuleCache(name)

        return role

