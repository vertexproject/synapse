import time
import threading
import importlib

import synapse.common as s_common
import synapse.crypto as s_crypto
import synapse.threads as s_threads

from synapse.dispatch import Dispatcher
from synapse.statemach import StateMachine, keepstate

linktypes = {
    'tcp':'synapse.links.tcp',
    'local':'synapse.links.local',
}

class DupLink(Exception):pass
class NoSuchLink(Exception):pass
class NoSuchLinkType(Exception):pass

class BadLinkInfo(Exception):pass
class NoLinkProp(BadLinkInfo):pass
class BadLinkProp(BadLinkInfo):pass

class Linker(Dispatcher,StateMachine):
    '''
    A Linker is a mixin object for managing both persistant
    and non-persistant link configuration states.

    A "link" is a tuple of (linktype,linkinfo).

    '''
    def __init__(self, statefd=None):
        Dispatcher.__init__(self)
        self.synOn('fini',self._finiLinker)

        self.links = {}
        self.linkmods = {}
        self.linksocks = {}
        self.linkrun = False

        StateMachine.__init__(self, statefd=statefd)

    def runLinkMain(self):
        '''
        Fire off the link managers to run and maintain links.

        Example:

            linker.runLinkMain()

        Notes:

            * One *must* call this API to begin link management

        '''
        self.linkrun = True
        for link in self.links.values():
            self.runLink(link)

        self.synFire('linkrun')

    def getLinkModule(self, linktype):
        '''
        Retrieve the link module to handle a given link type.

        Example:

            mod = linker.getLinkModule('tcp')
            if mod != None:
                print('the linker knows how to speak tcp!')

        '''
        mod = self.linkmods.get(linktype)
        if mod != None:
            return mod

        name = linktypes.get(linktype)
        if name == None:
            return None

        mod = importlib.import_module(name)
        self.linkmods[linktype] = mod
        return mod

    def setLinkModule(self, linktype, mod):
        '''
        Override or add a link module type.

        Example:

            class MyLinkMod:

                def reqValidLink(self, link):
                    # do validation or raise

                def initLinkSock(self, link):
                    #return Socket() or None

                def initLinkServSock(self, link):
                    #return Socket( listen=True)

            mod = MyLinkMod()
            linker.setLinkModule('woot',mod)

        '''
        self.linkmods[linktype] = mod

    def getLinkInfo(self, name, prop):
        '''
        Retrieve a property about a link by name.

        Example:

            port = linker.getLinkInfo('woot1','port')

        '''
        link = self.links.get(name)
        if link == None:
            raise NoSuchLink(name)

        return link[1].get(prop)

    @keepstate
    def setLinkInfo(self, name, prop, valu):
        '''
        Set a property about a link by name.

        Example:

            linker.setLinkInfo('woot1','foo',30)

        Notes:

            * This info *will* persist via StateMachine.

        '''
        link = self.links.get(name)
        if link == None:
            raise NoSuchLink(name)

        link[1][prop] = valu
        return link

    @keepstate
    def addLink(self, name, link):
        '''
        Add a link descriptor to be managed by this linker.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            linker.addLink('wootwoot',link)

        Notes:

            * If a StateMachine statefd is in use, this change will
              persist across restarts.  Use firePoolLink() for
              non-persistent link addition.

        '''
        if self.links.get(name) != None:
            DupLink(name)

        # a touch of magic to avoid these checks during load
        if self.statefd != None:
            self.checkLinkInfo(link)

        self.links[name] = link

        # If we're already running, run this one right away...
        if self.linkrun:
            self.runLink(link)

    def initLinkSock(self, link):
        '''
        Construct a client Socket for the given link.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            sock = linker.initLinkSock(link)

        '''
        mod = self._reqLinkModule(link[0])

        sock = mod.initLinkSock(link)
        if sock != None:
            sock.setSockInfo('link',link)
        return sock

    def initLinkServSock(self, link):
        '''
        Construct a server Socket for the given link.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            sock = linker.initLinkServSock(link)

        '''
        mod = self._reqLinkModule(link[0])

        sock = mod.initLinkServSock(link)
        if sock != None:
            sock.setSockInfo('link',link)

        return sock

    def initLinkFromUri(self, uri):
        '''
        Create a link tuple from a uri.

        Example:

            link = linker.initLinkFromUri('tcp://1.2.3.4:99/')

        '''
        proto = uri.split(':',1)[0]
        mod = self._reqLinkModule(proto)
        return mod.initLinkFromUri(uri)

    def _reqLinkModule(self, name):
        mod = self.getLinkModule(name)
        if mod == None:
            raise NoSuchLinkType(name)
        return mod

    def checkLinkInfo(self, link):
        '''
        Validate the link configuration or raise.

        Example:

            linker.checkLinkInfo(link)

        '''
        mod = self._reqLinkModule(link[0])
        mod.reqValidLink(link)

    def runLink(self, link):
        '''
        Run and manage a new link.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            linker.runLink(link)

        Notes:

            * This method does *not* update StateMachine.

        '''
        self.checkLinkInfo(link)
        self._runLinkThread(link)

    @s_threads.firethread
    def _runLinkThread(self, link):
        '''
        A thread routine to attempt to establish a link sock.
        Once established, the sock is dispatched with

        synFire('sockinit',sock)

        and configured to fire runLink again on close unless
        the Linker is being shut down...
        '''
        mod = self.getLinkModule(link[0])

        delay = 0
        while not self.isfini:
            sock = mod.initLinkSock(link)
            if sock != None:
                sid = sock.getSockId()
                sock.setSockInfo('link',link)
                self.linksocks[sid] = sock
                def runagain():
                    self.linksocks.pop(sid,None)
                    if not self.isfini:
                        self.runLink(link)

                sock.synOn('fini',runagain)
                self.synFire('sockinit',sock)
                return

            time.sleep(delay)

            delayinc = link[1].get('delayinc',0.1)
            delaymax = link[1].get('delaymax',1)
            delay = min( delay + delayinc, delaymax )

    def _finiLinker(self):
        for sock in list(self.linksocks.values()):
            sock.close()

class LinkClient(Dispatcher):
    '''
    A synapse link client.

    Dispatcher Hooks:

        synFire('sockinit',sock)    # on client reconnect

        # with runClientThread() active...
        synFire('sockmesg',sock,mesg)

    '''
    def __init__(self, link, linker=None):
        Dispatcher.__init__(self)
        self.lock = threading.Lock()

        # if they didn't specify, use the default linker.
        if linker == None:
            linker = Linker()

        self.thr = None
        self.sock = None

        self.link = link
        self.linker = linker

        self.synOn('fini', self._finiClient )
        self.synOn('sockinit', self._onSockInit )

    def runClientThread(self):
        '''
        Fire a thread to consume messages and fire dispatches.

        Example:

            client.runClientThread()

        Notes:

            * The thread will reconnect the socket on close.

        '''
        if self.thr == None:
            self.thr = self._runClientThread()

    def sendLinkMesg(self, mesg):
        '''
        Send a message on the link.

        Example:

            client.sendLinkMesg( ('woot',{}) )

        Notes:

            * This API will reconnect as needed

        '''
        with self.lock:
            self._sendLinkMesg(mesg)

    def txrxLinkMesg(self, mesg):
        '''
        Send a message and receive a message transactionally.

        Example:

            resp = client.txrxLinkMesg( ('woot',{}) )

        Notes:

            * This API will reconnect as needed

        '''
        with self.lock:
            while True:
                self._sendLinkMesg(mesg)
                ret = self.sock.recvSockMesg()
                if ret != None:
                    return ret

    def recvLinkMessage(self):
        with self.lock:
            mesg = self.sock.recvSockMesg()
            while mesg == None:
                self._runReConnect()
                mesg = self.sock.recvSockMesg()
        return mesg

    @s_threads.firethread
    def _runClientThread(self):
        self._runReConnect()
        self.sock.synOn('fini', self._runReConnect)
        while not self.isfini:
            for mesg in self.sock:
                self.synFire('sockmesg',self.sock,mesg)

    def _finiClient(self):
        self.sock.close()
        if self.thr != None:
            self.thr.join()

    def __enter__(self):
        self._runReConnect()
        return self

    def __exit__(self, t, v, tb):
        self.sock.close()

    def _sendLinkMesg(self, mesg):

        if self.sock == None:
            self._runReConnect()

        sent = self.sock.sendSockMesg(mesg)
        while not sent and not self.isfini:
            self._runReConnect()
            sent = self.sock.sendSockMesg(mesg)

    def _initClientSock(self):
        return self.linker.initLinkSock( self.link )

    def _onSockInit(self, sock):
        rc4key = self.link[1].get('rc4key')
        if rc4key != None:
            prov = s_crypto.RC4Crypto(self.link)
            sock._setCryptoProv( prov )

    def _runReConnect(self):
        delay = 0
        if self.sock != None:
            self.sock.close()

        self.sock = self._initClientSock()

        while self.sock == None and not self.isfini:
            time.sleep(delay)

            delay = min( delay + 0.2, 2 )

            self.sock = self._initClientSock()

        self.synFire('sockinit',self.sock)

class LinkServer(Dispatcher):
    '''
    A threaded (thread per) link server.

    ( for async/pool services use SocketPool )

    Dispatcher Hooks:

        synFire('sockinit',sock)        # on each new connection
        synFire('sockmesg',sock,mesg)   # on each socket message

    '''
    def __init__(self, link, linker=None):
        Dispatcher.__init__(self)

        if linker == None:
            linker = Linker()

        self.lisn = None
        self.sockets = {}

        self.link = link
        self.linker = linker

        self.boss = s_threads.ThreadBoss()

        self.synOn('fini', self._finiLinkServer )
        self.synOn('sockinit', self._onSockInit )

    def runLinkServer(self):
        '''
        Actually bind the port and begin serving clients.
        '''
        self.lisn = self.linker.initLinkServSock( self.link )
        self.boss.worker( self._runLisnThread )
        addr = self.lisn.getsockname()
        return addr

    def _runLisnThread(self):
        while not self.isfini:
            sock,addr = self.lisn.accept()
            self.synOn('fini',sock.close,weak=True)
            self.boss.worker( self._runSockThread, sock )

    def _runSockThread(self, sock):
        sid = sock.getSockId()

        timeout = self.link[1].get('timeout')
        if timeout != None:
            sock.settimeout(timeout)

        self.synFire('sockinit',sock)
        for mesg in sock:
            self.synFire('sockmesg',sock,mesg)

    def _onSockInit(self, sock):
        '''
        Handle a few "server wide" link options.
        '''
        # handle our "cheap" rc4 static keying
        rc4key = self.link[1].get('rc4key')
        if rc4key != None:
            prov = s_crypto.RC4Crypto(self.link)
            sock._setCryptoProv( prov )

    def _finiLinkServer(self):

        # wake the sleeping listener
        sock = self.linker.initLinkSock( self.link )
        if sock != None:
            sock.close()

        self.lisn.close()

        #for sock in list(self.sockets.values()):
            #sock.close()

        self.boss.synFireFini()

