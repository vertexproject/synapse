'''
An RMI framework for synapse.
'''
import traceback

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *

class Daemon(s_daemon.Daemon):
    '''
    Telepath RMI Daemon

    Example:

        import synapse.telepath as s_telepath
        from synapse.common import *

        class Foo:
            def bar(self, x, y):
                return x + y


        link = tufo('tcp',listen=('0.0.0.0',9999))

        daemon = s_telepath.Daemon()

        daemon.runLink(link)
        daemon.addSharedObject('foo',Foo())

    '''
    def __init__(self, statefd=None):

        self.shared = {}
        self.methods = {}

        s_daemon.Daemon.__init__(self, statefd=statefd)

        self.setMesgMethod('tele:syn', self._onMesgTeleSyn )
        self.setMesgMethod('tele:call', self._onMesgTeleCall )

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

        return tufo('tele:syn')

    def _onMesgTeleCall(self, sock, mesg):

        if not sock.getSockInfo('tele:syn'):
            sock.senderr('nosyn','no syn mesg received')
            return

        _,msginfo = mesg

        oname,mname,args,kwargs = mesg[1].get('teletask')

        rule = 'tele.call.%s.%s' % (oname,mname)

        ident = sock.getSockInfo('tele:ident')
        if not self.getAuthAllow(ident,rule):
            sock.senderr('noperm','permission denied')
            return

        obj = self.shared.get(oname)
        if obj == None:
            return tufo('err',code='noobj')

        meth = getattr(obj,mname,None)
        if meth == None:
            return tufo('err',code='nometh')

        try:
            return tufo('tele:call', ret=meth(*args,**kwargs) )

        except Exception as e:
            trace = traceback.format_exc()
            return tufo('tele:call',exc=str(e),trace=trace)

class TeleProtoError(Exception):pass
class TelePermDenied(Exception):pass
class RemoteException(Exception):pass

class ProxyMeth:

    def __init__(self, proxy, name):
        self.name = name
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        task = (self.proxy.objname, self.name, args, kwargs)
        reply = self.proxy.sendAndRecv('tele:call',teletask=task)

        if reply[0] == 'tele:call':
            exc = reply[1].get('exc')
            if exc != None:
                raise RemoteException(exc)

            return reply[1].get('ret')

        if reply[1].get('code') == 'noperm':
            raise TelePermDenied()

        raise TeleProtoError( reply[1].get('msg') )
            
class Proxy(s_link.LinkClient):

    # FIXME make these use links!
    def __init__(self, link):
        self.objname = link[1].get('telepath')
        s_link.LinkClient.__init__(self, link)

        authinfo = link[1].get('authinfo')
        self.sendAndRecv('tele:syn',authinfo=authinfo)

    def __getattr__(self, name):
        meth = ProxyMeth(self, name)
        setattr(self,name,meth)
        return meth

