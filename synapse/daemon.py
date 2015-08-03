import traceback
import collections

import synapse.link as s_link
import synapse.threads as s_threads

import synapse.telepath as s_telepath

from synapse.eventbus import EventBus
from synapse.statemach import StateMachine, keepstate

class DupLink(Exception):pass
class ImplementMe(Exception):pass

class Daemon(
        EventBus,
        StateMachine,
        s_telepath.TeleMixin
    ):
    '''
    Base class for the various synapse daemons.
    '''
    def __init__(self, statefd=None):
        EventBus.__init__(self)

        self.authmod = None
        self.links = {}
        self.mesgmeths = {}

        self.boss = s_threads.ThreadBoss()
        self.onfini( self.boss.fini )

        s_telepath.TeleMixin.__init__(self)

        StateMachine.__init__(self,statefd=statefd)
        self.on('link:sock:mesg',self._onLinkSockMesg)

    def setAuthModule(self, authmod):
        '''
        Enable auth/perm enforcement on the daemon using the given module.

        Example:

            class MyAuthModule(AuthModule):
                ...

            daemon = Daemon()
            authmod = MyAuthModule()

            daemon.setAuthModule(authmod)

        Notes:

            * Daemon will fini the auth module on daemon fini

        '''
        self.authmod = authmod
        self.onfini( authmod.fini )

    def getAuthAllow(self, ident, rule):
        '''
        If an auth module is present, check the given allow rule.

        Example:

            if not daemon.getAuthAllow( ident, rule ):
                return sock.senderr('noperm','permission denied')

        Notes:

            * If no AuthModule is set, default is to allow

        '''
        if self.authmod == None:
            return True

        return self.authmod.getAuthAllow(ident,rule)

    def getAuthIdent(self, authinfo):
        '''
        Translate arbitrary "authinfo" dictionary to a unique id.

        Example:

            ident = daemon.getAuthIdent( authinfo )

        Notes:

            * The ident can be used in calls to getAuthAllow()

        '''
        if self.authmod == None:
            return None

        return self.authmod.getAuthIdent(authinfo)

    def setMesgMethod(self, name, meth):
        '''
        Add a message method to the Daemon.

            def wootmeth(sock,mesg):
                stuff()

            daemon.setMesgMethod('woot',wootmeth)

        '''
        self.mesgmeths[name] = meth

    def addLinkServer(self, name, link):
        '''
        Add a link tuple to the Daemon.

        Example:

            from synapse.common import tufo

            link = tufo('tcp',host='1.2.3.4',port=80)
            daemon.addLinkServer('wootwoot',link)

        Notes:

            * If a StateMachine statefd is in use, this change will
              persist across restarts.

        '''
        if self.links.get(name) != None:
            raise DupLink()

        self.links[name] = link
        self.runLinkServer(link)

    def getLink(self, name):
        '''
        Retrieve a link tuple by name.

        Example:

            link = daemon.getLink('woot')

        Notes:

            * Do not make changes directly to the link info

        '''
        return self.links.get(name)

    def getLinks(self):
        '''
        Return a list of (name,link) tuples.

        Example:

            for name,link in daemon.getLinks():
                stuff()

        '''
        return list(self.links.items())

    def runLinkServer(self, link):
        '''
        Run and manage a new LinkServer.

        Example:

            link = tufo('tcp',host='0.0.0.0',port=80)
            daemon.runLinkServer(link)
        '''
        relay = s_link.initLinkRelay( link )
        server = relay.initLinkServer()

        server.on('link:sock:mesg',self.dist)
        server.on('link:sock:init',self.dist)
        server.on('link:sock:fini',self.dist)

        self.onfini(server.fini)
        return server.runLinkServer()

    def runLinkPeer(self, link):
        '''
        Run and manage a new LinkPeer.
        '''
        relay = s_link.initLinkRelay(link)
        peer = relay.initLinkPeer()

        peer.on('link:sock:mesg',self.dist)
        peer.on('link:sock:init',self.dist)
        peer.on('link:sock:fini',self.dist)

        self.onfini(peer.fini)
        return peer.runLinkPeer()

    def _onLinkSockMesg(self, event):
        sock = event[1].get('sock')
        mesg = event[1].get('mesg')

        meth = self.mesgmeths.get(mesg[0])
        # ignore messages we dont understand
        if meth == None:
            return

        try:

            repl = meth(sock,mesg)
            if repl != None:
                repl[1]['reply'] = mesg[1].get('ident')
                sock.sendobj(repl)
            
        except Exception as e:
            traceback.print_exc()

class AuthModule(StateMachine,EventBus):

    '''
    Modular authentication/authorization for daemon services.

    An AuthModule implementation is primarily responsible for two
    things:

    1. Translate link specified authinfo into a unique identity
    2. Store and evaluate a set of allow rules for the unique identity

    '''
    def __init__(self, statefd=None):
        self.authinfo = {}
        self.authrules = collections.defaultdict(dict)

        EventBus.__init__(self)
        StateMachine.__init__(self, statefd=statefd)

        if self.getAuthInfo('defauth') == None:
            self.setAuthInfo('defauth', False)

        self._loadAuthRules()

    def getAuthInfo(self, prop):
        '''
        Retrieve a persistent property from the AuthModule.

        Example:

            auth.getAuthInfo('foo')

        '''
        return self.authinfo.get(prop)

    @keepstate
    def setAuthInfo(self, prop, valu):
        '''
        Set a persistent property in the AuthModule.

        Example:

            auth.setAuthInfo('foo','bar')

        Notes:

            * This API generates EventBus events:
                ('auth:info',{'prop':<prop>,'valu':<valu>})
                ('auth:info:<prop>',{'valu':<valu>})

        '''
        self.authinfo[prop] = valu
        self.fire('auth:info', prop=prop, valu=valu)
        self.fire('auth:info:%s' % prop, valu=valu)

    def getAuthIdent(self, authdata):
        '''
        Return an ident (used in subsequent getAuthAllow calls) from
        the authdata dict provided by a connecting client.
        '''
        if authdata == None:
            return None

        return self._getAuthIdent(authdata)

    def getAuthAllow(self, ident, rule):
        '''
        Returns True if the given rule is allowed for the ident.

        Example:

            if not auth.getAuthAllow(ident,rule):
                return

        '''
        return self._getAuthAllow(ident,rule)

    @keepstate
    def addAuthRule(self, ident, rule, allow=True):
        '''
        Add an allow/deny rule to the AuthModule.

        Example:

            auth.addAuthRule('visi','do.thing', True)

        '''
        return self._addAuthRule(ident, rule, allow)

    def delAuthRule(self, ident, rule):
        '''
        Remove an allow/deny rule from the AuthModule.

        Example:

            auth.delAuthRule('visi','do.thing')

        '''
        return self._delAuthRule(ident,rule)

    def _getAuthIdent(self, authinfo):
        raise ImplementMe()

    def _getAuthAllow(self, ident, rule):
        rules = self.authrules.get(ident)
        if rules == None:
            return self.getAuthInfo('defauth')

        allow = rules.get(rule)
        if allow == None:
            return self.getAuthInfo('defauth')

        return allow

    def _addAuthRule(self, ident, rule, allow):
        self.authrules[ident][rule] = allow

    def _delAuthRule(self, ident, rule):
        rules = self.authrules.get(ident)
        if rules == None:
            return

        return rules.pop(rule,None)

    def _loadAuthRules(self):
        '''
        A API for subclasses to load auth rules from outside.
        '''
        pass

class ApiKeyAuth(AuthModule):
    '''
    A simple "apikey" based AuthModele which stores data in the daemon.
    '''
    def _getAuthIdent(self, authinfo):
        return authinfo.get('apikey')
