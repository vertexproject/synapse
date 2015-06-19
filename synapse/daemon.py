import traceback

import synapse.link as s_link
import synapse.pathtree as s_pathtree

import synapse.neuron as s_neuron
#import synapse.impulse as s_impulse
import synapse.telepath as s_telepath

from synapse.eventbus import EventBus

class DupLink(Exception):pass
class DupSense(Exception):pass
class DupSenseMeth(Exception):pass

class NoSuchLink(Exception):pass
class NoSuchService(Exception):pass

class ImplementMe(Exception):pass

synsvcs = {
    'neuron':s_neuron.Neuron,
    #'impulse':s_impulse.Service,
    'telepath':s_telepath.Telepath,
}

def initTcpServer(host, port, **linkopts):
    '''
    Convenience function for making a TCP server Daemon.

    Example:

        daemon = initTcpServer('0.0.0.0',9999,timeout=5)

    Notes:

        * All standard link options may be specified

    '''
    daemon = Daemon()
    linkopts['host'] = host
    linkopts['port'] = port
    daemon.addLink( ('tcpd',linkopts) )
    return daemon

class Daemon(EventBus):
    '''
    A Daemon provides synapse Services to LinkRelay sockets.
    '''
    def __init__(self, statefd=None):
        EventBus.__init__(self)

        self.authmod = None
        self.services = {}    # name:Service()
        self.mesgmeths = {}

        self.pathtree = s_pathtree.PathTree(statefd=statefd)

        # setup a couple sense methods for the daemon itself
        self.setMesgMethod('dae:syn', self._onMesgDaeSyn)

    def setAuthModule(self, authmod):
        '''
        Enable auth/perm enforcement on the daemon using the given module.

        Example:

            class MyAuthModule(AuthModule):
                ...

            daemon = Daemon()
            authmod = MyAuthModule()

            daemon.setAuthModule(authmod)

        '''
        self.authmod = authmod

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
        if authinfo == None:
            return None

        if self.authmod == None:
            return None

        return self.authmod.getAuthIdent(authinfo)

    def getPathTreeNode(self, path):
        return self.pathtree.node(path)

    def getSubPathTree(self, path):
        '''
        Retrieve an object from the PathTree for this Daemon.
        '''
        return self.pathtree.subtree(path)

    def loadSynService(self, name):
        '''
        Load a pre-defined synapse service by name.

        Example:

            tele = daemon.loadSynService('telepath')

        '''
        svc = self.services.get(name)
        if svc == None:
            cls = synsvcs.get(name)
            if cls == None:
                raise NoSuchService(name)

            svc = cls(self)
            self.services[name] = svc

            for name,meth in svc.getMesgMethods():
                self.setMesgMethod(name,meth)

        return svc

    def addSynService(self, name, svcobj):
        self.services[name] = svcobj

        for name,meth in svcobj.getMesgMethods():
            self.setMesgMethod(name,meth)

    def _onMesgDaeSyn(self, sock, mesg):
        '''
        ( 'dae:syn', {} )
        '''
        services = list(self.services.keys())
        # FIXME do we need this anymore?
        sock.sendobj( ('dae:syn:ret',{'services':services}) )

    def setMesgMethod(self, name, meth):
        '''
        Add a message method to the Daemon.

            def wootmeth(sock,mesg):
                stuff()

            daemon.setMesgMethod('woot',wootmeth)

        '''
        self.mesgmeths[name] = meth

    def addLink(self, name, link):
        '''
        Add a link tuple to the Daemon.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            daemon.addLink('wootwoot',link)

        Notes:

            * If a StateMachine statefd is in use, this change will
              persist across restarts.

        '''
        path = ('daemon','links',name)

        if self.pathtree.get(path) != None:
            DupLink(name)

        self.pathtree.set(path, link)

        self.runLink(link)

    def getLink(self, name):
        '''
        Retrieve a link tuple by name.

        Example:

            link = daemon.getLink('woot')

        Notes:

            * Do not make changes to the link info
              ( you must delLink / addLink )

        '''
        path = ('daemon','links',name)
        return self.pathtree.get(path)

    def getLinks(self):
        '''
        Return a list of (name,link) tuples.

        Example:

            for name,link in daemon.getLinks():
                stuff()

        '''
        path = ('daemon','links')
        return self.pathtree.items(path)

    def addLinkUri(self, name, uri):
        '''
        A convenience function to add a link by uri.

        Example:

            daemon.addLinkUri('tcpd://0.0.0.0:9999')

        '''
        link = s_link.initLinkFromUri(uri)
        return self.addLink(name,link)

    def runLink(self, link):
        '''
        Run and manage a new link.

        Example:

            link = ('tcpd',{'host':'0.0.0.0','port':80})
            daemon.runLink(link)

        Notes:

            * This method does *not* update StateMachine.

        '''
        relay = s_link.initLinkRelay( link )
        relay.synOn('link:sock:mesg',self._onSockMesg)
        relay.synOn('link:sock:init',self._fireSockInit)
        relay.synOn('link:sock:fini',self._fireSockFini)

        self.synOnFini(relay.synFini)

        relay.runLinkRelay()

    def runLinkUri(self, uri):
        '''
        A convenience function to run a link by uri.

        Example:

            daemon.runLinkUri('tcpd://0.0.0.0:9999')

        '''
        link = s_link.initLinkFromUri(uri)
        return self.runLink(link)

    # FIXME merge these out ( use only one sockinit event type )
    def _fireSockInit(self, event):
        sock = event[1].get('sock')
        sock.setSockInfo('daemon',self)
        self.synFire('sockinit',sock=sock)

    def _fireSockFini(self, event):
        sock = event[1].get('sock')
        self.synFire('sockfini',sock=sock)

    def _onSockMesg(self, event):
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

class AuthModule:

    '''
    Modular authentication/authorization for daemon services.

    An AuthModule implementation is primarily responsible for two
    things:

    1. Translate link specified authinfo into a unique identity
    2. Store and evaluate a set of allow rules for the unique identity

    '''

    def __init__(self):
        pass

    def getAuthIdent(self, authdata):
        raise ImplementMe()

    def getAuthAllow(self, ident, rule):
        '''
        Returns True if the given rule is allowed for the ident.
        '''
        raise ImplementMe()

    def addAuthAllow(self, ident, rule):
        raise ImplementMe()

    def delAuthAllow(self, ident, rule):
        raise ImplementMe()

class ApiKeyAuth:
    '''
    A simple "apikey" based AuthModele which stores data in the daemon.
    '''

    def __init__(self, daemon):
        self.daemon = daemon
        #self.apikeys = daemon.getPathTreeNode( ('daemon','apikeys') )
        self.apirules = daemon.getPathTreeNode( ('daemon','apirules') )

    def getAuthIdent(self, authinfo):
        return authinfo.get('apikey')

    def addAuthAllow(self, apikey, rule):
        self.apirules[apikey].set( rule, True )

    def getAuthAllow(self, apikey, rule):
        rules = self.apirules.get(apikey)
        if rules == None:
            return False

        return rules.get(rule)

    def delAuthAllow(self, apikey, rule):
        rules = self.apirules.get(apikey)
        if rules == None:
            return False

        return rules.pop(rule)

