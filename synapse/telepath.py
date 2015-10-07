'''
An RMI framework for synapse.
'''
import copy
import threading
import traceback

import synapse.link as s_link

from synapse.common import *
from synapse.eventbus import EventBus

class TeleMixin:
    '''
    Telepath RMI Daemon Mixin

    Example:

        import synapse.link as s_link
        import synapse.daemon as s_daemon

        daemon = s_daemon.Daemon()

        class Foo:
            def bar(self, x, y):
                return x + y

        link = s_link.chopLinkUrl('tcp://0.0.0.0:9999')

        daemon.runLinkServer(link)
        daemon.addSharedObject('foo',Foo())

    '''
    def __init__(self): #, statefd=None):

        self.shared = {}

        self.setMesgMeth('tele:syn', self._onMesgTeleSyn )
        self.setMesgMeth('tele:call', self._onMesgTeleCall )

    def addSharedObject(self, name, obj):
        '''
        Share an object via the telepath Server.

        Example:

            foo = Foo()

            serv.addSharedObject('foo',foo)

        '''
        self.shared[name] = obj

    def delSharedObject(self, name):
        '''
        Remove a shared object from the telepath Server.

        Example:

            serv.delSharedObject('foo')

        '''
        return self.shared.pop(name,None)

    def getSharedObject(self, name):
        '''
        Return a reference to a shared object by name.

        Example:

            foo = serv.getSharedObject('foo')

        '''
        return self.shared.get(name)

    def _onMesgTeleSyn(self, sock, mesg):
        '''
        Handle an initial "syn" message from a newly connected client.

        cli: ('syn',{'name':'objname'})
        srv: ('syn',{'meths':[name1, name2, ...],})

        '''
        sock.setSockInfo('tele:syn',True)
        authinfo = mesg[1].get('authinfo')
        ident = self.getAuthIdent(authinfo)
        sock.setSockInfo('tele:ident',ident)
        sock.fireobj('tele:syn')

    def _onMesgTeleCall(self, sock, mesg):

        if not sock.getSockInfo('tele:syn'):
            sock.fireobj('tele:err', code='nosyn')
            return

        _,msginfo = mesg

        oname,mname,args,kwargs = mesg[1].get('teletask')

        if self.authmod != None:
            rule = 'tele.call.%s.%s' % (oname,mname)
            ident = sock.getSockInfo('tele:ident')
            if not self.getAuthAllow(ident,rule):
                sock.fireobj('tele:err', code='noperm')
                return

        obj = self.shared.get(oname)
        if obj == None:
            sock.fireobj('tele:err',code='noobj')
            return

        meth = getattr(obj,mname,None)
        if meth == None:
            sock.fireobj('tele:err',code='nometh',name=mname)
            return

        try:
            sock.fireobj('tele:call', ret=meth(*args,**kwargs) )

        except Exception as e:
            trace = traceback.format_exc()
            sock.fireobj('tele:call',exc=str(e),trace=trace)

class TeleErr(Exception):pass

# raised on invalid protocol response
class ProtoErr(TeleErr):
    def __init__(self, event):
        mesg = '%s: %r' % event
        TeleErr.__init__(self, mesg)

class NoSuchObj(TeleErr):pass
class NoSuchMeth(TeleErr):pass
class PermDenied(TeleErr):pass

class RemoteException(Exception):pass

class ProxyMeth:

    def __init__(self, proxy, name):
        self.name = name
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        task = (self.proxy.objname, self.name, args, kwargs)

        client = self.proxy._getLinkClient()
        reply = client.sendAndRecv('tele:call',teletask=task)

        if reply[0] == 'tele:call':
            exc = reply[1].get('exc')
            if exc != None:
                raise RemoteException(exc)

            return reply[1].get('ret')

        if reply[0] == 'tele:err':

            code = reply[1].get('code')
            if code == 'noperm':
                raise PermDenied()

            if code == 'nometh':
                name = reply[1].get('name')
                raise NoSuchMeth(name)

            if code == 'noobj':
                raise NoSuchObj(self.proxy.objname)

        raise ProtoErr(reply)
            
class Proxy:

    def __init__(self, link):
        self.bus = EventBus()

        self.link = link
        self.relay = s_link.initLinkRelay(link)
        self.client = self._initLinkClient()

        self._tele_with = {}    # tid:client for with blocks

        # objname is path minus leading "/"
        self.objname = link[1].get('path')[1:]

    def fini(self):
        self.bus.fini()

    def _initLinkClient(self):
        client = self.relay.initLinkClient()
        authinfo = self.link[1].get('authinfo')
        client.sendAndRecv('tele:syn', authinfo=authinfo)
        self.bus.onfini( client.fini, weak=True )
        return client

    def __enter__(self):
        # FIXME PerThread
        thrid = threading.currentThread().ident
        client = self._initLinkClient()
        self._tele_with[thrid] = client
        return self

    def __exit__(self, exc, cls, tb):
        thrid = threading.currentThread().ident
        client = self._tele_with.pop(thrid,None)
        if client != None:
            client.fini()

    def _getLinkClient(self):
        # If the thread is managing a with block, give him his client
        thrid = threading.currentThread().ident
        client = self._tele_with.get(thrid)
        if client != None:
            return client

        return self.client

    def __getattr__(self, name):
        meth = ProxyMeth(self, name)
        setattr(self,name,meth)
        return meth

    def __getitem__(self, path):
        # allows bar = foo['bar'] object switching
        link = copy.deepcopy(self.link)
        link[1]['path'] = '/%s' % path
        return Proxy(link)

    # some methods to avoid round trips...
    def __nonzero__(self):
        return True

    def __eq__(self, obj):
        return id(self) == id(obj)

    def __ne__(self, obj):
        return not self.__eq__(obj)


def getProxy(url):
    '''
    Construct a telepath proxy from a url.

    Example:

        foo = getProxy('tcp://1.2.3.4:90/foo')

        foo.dostuff(30) # call remote method

    '''
    link = s_link.chopLinkUrl(url)
    return Proxy(link)
