import time
import threading

import synapse.crypto as s_crypto
import synapse.threads as s_threads

from synapse.eventbus import EventBus

class BadLinkInfo(Exception):pass
class NoLinkProp(BadLinkInfo):pass
class BadLinkProp(BadLinkInfo):pass
class NoSuchLinkProto(Exception):pass

class LinkFailure(Exception):pass
class RetryExceeded(LinkFailure):pass

class ImplementMe(Exception):pass

class LinkRelay:

    proto = None

    def __init__(self, link):
        self.link = link
        self._reqValidLink(link)

    def initLinkServer(self):
        '''
        Construct and return a new LinkServer for the link.
        '''
        return self._initLinkServer()

    def initLinkClient(self):
        '''
        Construct and return a new LinkClient for the link.

        Example:

            cli = relay.initLinkClient(link)

        '''
        return self._initLinkClient()

    def initLinkPeer(self):
        '''
        Construct and return a new LinkPeer for the link.

        Example:

            def sockmesg(event):
                stuff()

            peer = relay.initLinkPeer()
            peer.on('link:sock:mesg',sockmesg)
            peer.runLinkPeer()

        '''
        return self._initLinkPeer()

    def initServerSock(self):
        return self._initServerSock()

    def initClientSock(self):
        sock = self._initClientSock()
        if sock == None:
            return None
        return _prepLinkSock(sock,self.link)

    def _initClientSock(self):
        raise ImplementMe()

    def _initServerSock(self):
        raise ImplementMe()

    def _initLinkServer(self):
        raise ImplementMe()

    def _initLinkClient(self):
        raise ImplementMe()

    def _initLinkPeer(self):
        raise ImplementMe()

    def _reqValidLink(self, link):
        raise ImplementMe()

def _prepLinkSock(sock,link):
    '''
    Used by LinkClient and LinkServer to handle universal link options.
    '''
    sock.setSockInfo('trans',link[1].get('trans'))

    # must remain first!
    zerosig = link[1].get('zerosig')
    if zerosig != None:
        xform = s_crypto.Rc4Xform(b'')
        sock.addSockXform(xform)

    rc4key = link[1].get('rc4key')
    if rc4key != None:
        xform = s_crypto.Rc4Xform(rc4key)
        sock.addSockXform(xform)

    timeout = link[1].get('timeout')
    if timeout != None:
        sock.settimeout(timeout)

    #FIXME support DH KEX
    return sock

class LinkServer(EventBus):
    '''
    A synapse LinkServer.

    Each synapse LinkServer is capable of producing newly
    connected Socket() objects:

    Example:

        def linksock(sock):
            stuff()

        def linkmesg(sock,mesg):
            stuff()

        link = ('tcp',{'host':'0.0.0.0','port':'0.0.0.0'})

        relay = initLinkRelay(link)

        server = relay.initLinkServer()
        server.on('link:sock:init',linksock)
        server.on('link:sock:mesg',linkmesg)
        server.runLinkServer()

    EventBus Events:

        ('link:sock:init',{'sock':sock})
        ('link:sock:fini',{'sock':sock})
        ('link:sock:mesg',{'sock':sock, 'mesg':mesg})

    '''
    def __init__(self, relay):
        EventBus.__init__(self)
        self.relay = relay

        self.boss = s_threads.ThreadBoss()
        self.onfini(self.boss.fini)
        self.socks = {}

        # we get the sock first to fill in info
        self.on('link:sock:init', self._onLinkSockInit)
        self.on('link:sock:fini', self._onLinkSockFini)

        self.onfini( self._finiAllSocks )

    def _prepLinkSock(self, sock):
        '''
        Used by LinkServer implementors to handle universal link options.
        '''
        return _prepLinkSock(sock,self.relay.link)

    def _onLinkSockInit(self, event):
        sock = event[1].get('sock')
        if self.isfini:
            sock.fini()
            return

        sock.setSockInfo('server',self)
        self.socks[sock.ident] = sock

    def _onLinkSockFini(self, event):
        sock = event[1].get('sock')
        self.socks.pop(sock.ident,None)

    def _finiAllSocks(self):
        socks = list( self.socks.values() )
        [ sock.fini() for sock in socks ]

    def runLinkServer(self):
        '''
        Run a thread to handle this LinkServer.
        '''
        self._initLinkServer()
        self.boss.worker( self._runLinkServer )

    def _runLinkServer(self):
        raise ImplementMe()

    def _initLinkServer(self):
        raise ImplementMe()

    def _runSockLoop(self, sock):

        # apply universal link properties
        sock = self._prepLinkSock(sock)

        self.onfini(sock.close,weak=True)
        self.fire('link:sock:init',sock=sock)

        for mesg in sock:
            self.fire('link:sock:mesg',sock=sock,mesg=mesg)
            if sock.getSockInfo('plex'):
                return

        self.fire('link:sock:fini',sock=sock)

class LinkPeer(EventBus):
    '''
    A LinkPeer is a persistent peer-to-peer client-like
    object for long running "client" connections with
    multiplexing.
    '''
    def __init__(self, relay):
        EventBus.__init__(self)
        self.relay = relay

        self.boss = s_threads.ThreadBoss()
        self.onfini(self.boss.fini)

    def runLinkPeer(self):
        self.boss.worker(self._runLinkPeer)

    def _runLinkPeer(self):

        while not self.isfini:

            sock = self.relay.initClientSock()
            if sock == None:
                time.sleep(1)
                continue

            sock.setSockInfo('peer',True)
            self.fire('link:sock:init',sock=sock)

            for mesg in sock:
                self.fire('link:sock:mesg',sock=sock,mesg=mesg)

            self.fire('link:sock:fini',sock=sock)

            sock.fini()

class LinkClient(EventBus):
    '''
    A synapse link client.
    '''
    def __init__(self, relay):
        EventBus.__init__(self)

        self.lock = threading.Lock()

        self.relay = relay
        self.trans = relay.link[1].get('trans')

        self.onfini(self._finiLinkClient)

        self.sock = relay.initClientSock()

        if self.sock == None:
            raise Exception('Initial Link Failed: %r' % (self.link,))

        if self.trans:
            self.sock.fini()

    def sendAndRecv(self, name, **info):
        '''
        Send a message and receive a message transactionally.

        Example:

            resp = client.sendAndRecv( ('woot',{}) )

        Notes:

            * This API will reconnect as needed

        '''
        mesg = (name, info)

        # no need to lock or anything...
        if self.trans:
            sock = self.initSockLoop()
            try:
                sock.sendobj( mesg )
                return sock.recvobj()
            finally:
                sock.fini()

        with self.lock:
            while True:
                while not self.sock.sendobj( mesg ):
                    self.sock.fini()
                    self.sock = self.initSockLoop()

                resp = self.sock.recvobj()
                if resp != None:
                    return resp

                self.sock.fini()
                self.sock = self.initSockLoop()

    def _finiLinkClient(self):
        self.sock.fini()

    def initSockLoop(self):
        sock = self.relay.initClientSock()
        if sock != None:
            return sock

        tries = 1
        retry = self.relay.link[1].get('retry')
        delay = self.relay.link[1].get('delay',0)

        while sock == None and not self.isfini:

            if retry != None and tries > retry:
                raise RetryExceeded()

            time.sleep(delay)

            delaymax = self.relay.link[1].get('delaymax',2)
            delayinc = self.relay.link[1].get('delayinc',0.2)
            delay = min( delay + delayinc, delaymax )

            sock = self.relay.initClientSock()

            tries += 1

        return sock

