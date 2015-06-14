'''
An RMI framework for synapse.
'''
import traceback

import synapse.link as s_link
import synapse.common as s_common

class Server(s_link.LinkServer):
    '''
    Telepath RMI Server

    Example:

        import synapse.telepath as s_telepath

        class Foo:
            def bar(self, x, y):
                return x + y

        link = ('tcp',{'host':'127.0.0.1','port':5656})
        serv = s_telepath.Server(link)

        foo = Foo()
        serv.addSharedObject('foo',foo)
        serv.runLinkServer()

    Dispatcher Hooks:

        synFire('sockinit',sock)    # on new sock connection

            Called for each newly connected socket.

        synFire('tele:call:auth',sock,mesg) # 

            Called for every client request to call an API.
            May be used to enforce perms etc.  Any hook in the chain
            returning False will cause the call request to be denied.

    '''

    def __init__(self, link, linker=None, **info):
        s_link.LinkServer.__init__(self, link, linker=linker)
        self.synOn('sockmesg', self._onSockMesg )

        self.shared = {}        # shared objects by name
        self.methods = {}       # objname:[meth,...]
        #self.teleinfo = info

        self.handlers = {
            'tele:syn':self._onMesgSyn,
            'tele:call':self._onMesgCall,
            #'open':self._onMesgOpen,
        }


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

    #@keepstate
    #def setTeleInfo(self, prop, valu):
        #self.synFire('tele:info',prop,valu)
        #self.synFire('tele:info:%s' % prop, valu)
        #self.teleinfo[prop] = valu

    def _onSockMesg(self, sock, mesg):
        meth = self.handlers.get(mesg[0])
        if meth == None:
            return

        try:
            meth(sock,mesg)
        except Exception as e:
            self.synFire('err',exc)

    def _onMesgSyn(self, sock, mesg):
        '''
        Handle an initial "syn" message from a newly connected client.

        cli: ('syn',{'name':'objname'})
        srv: ('syn',{'meths':[name1, name2, ...],})

        '''
        #name = mesg[1].get('obj')
        sock.setSockInfo('tele:syn',True)
        sock.sendSockMesg( ('tele:syn',{}) )

    def _onMesgCall(self, sock, mesg):
        '''
        cli: ('tele:call',{'obj':<name>,'meth':<name>,'args':<args>,'kwargs':<kwargs>})
        srv: ('tele:call',{'ret':<ret>})  or  ('tele:call',{'exc':<str>})
        '''

        if not sock.getSockInfo('tele:syn'):
            sock.sendSockErr('nosyn','no syn mesg received')
            return

        _,msginfo = mesg

        # see if all 'tele:call:auth' listeners approve...
        authres = self.synFire('tele:call:auth',sock,mesg)
        if not all(authres):
            sock.sendSockErr('noperm','permission denied')
            return

        oname = msginfo.get('obj')
        obj = self.shared.get(oname)
        if obj == None:
            sock.sendSockErr('noobj','no such object: %s' % (oname,))
            return

        mname = msginfo.get('meth')
        meth = getattr(obj,mname,None)
        if meth == None:
            sock.sendSockErr('nometh','no such method: %s' % (mname,))
            return

        args = msginfo.get('args')
        kwargs = msginfo.get('kwargs')

        try:
            ret = meth(*args,**kwargs)
            sock.sendSockMesg( ('tele:call',{'ret':ret}) )
        except Exception as e:
            trace = traceback.format_exc()
            sock.sendSockMesg( ('tele:call',{'exc':str(e),'trace':trace}) )

class TeleProtoError(Exception):pass
class RemoteException(Exception):pass

class ProxyMeth:

    def __init__(self, proxy, name):
        self.name = name
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        mesg = ('tele:call',{
                    'obj':self.proxy.objname,
                    'meth':self.name,
                    'args':args,
                    'kwargs':kwargs})

        reply = self.proxy.txrxLinkMesg( mesg )
        if reply[0] == 'tele:call':
            exc = reply[1].get('exc')
            if exc != None:
                raise RemoteException(exc)

            return reply[1].get('ret')

        raise TeleProtoError( reply[1].get('msg') )
            

class Proxy(s_link.LinkClient):

    # FIXME make these use links!
    def __init__(self, objname, link, linker=None):
        self.objname = objname
        s_link.LinkClient.__init__(self, link, linker=linker)

        self.txrxLinkMesg( ('tele:syn',{}) )

    def __getattr__(self, name):
        meth = ProxyMeth(self, name)
        setattr(self,name,meth)
        return meth

