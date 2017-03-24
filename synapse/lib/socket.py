from __future__ import absolute_import,unicode_literals

import os
import ssl
import zlib
import errno
import atexit
import select
import socket
import logging
import msgpack
import collections

logger = logging.getLogger(__name__)

import synapse.common as s_common
import synapse.lib.scope as s_scope
import synapse.lib.threads as s_threads
import synapse.lib.thisplat as s_thisplat

from synapse.eventbus import EventBus

from synapse.common import *

def sockgzip(byts):
    blen = len(byts)
    byts = zlib.compress(byts)
    #print('GZIP DELTA: %d -> %d' % (blen,len(byts)))
    return msgenpack(('sock:gzip',{'data':byts}))

class SockXform:
    '''
    Base class for a socket bytes transform class.

    Notes:

        * for obj tx/rx, these are called once per.
    '''
    def init(self, sock):
        pass

    def txform(self, byts):
        return byts

    def rxform(self, byts):
        return byts

class Socket(EventBus):

    def __init__(self, sock, **info):
        EventBus.__init__(self)

        self.sock = sock
        self.plex = None
        self.unpk = msgpack.Unpacker(use_list=0,encoding='utf8')
        self.iden = s_common.guid()
        self.xforms = []        # list of SockXform instances
        self.info = info

        # used by Plex() tx
        self.txbuf = None
        self.txsize = 0

        if self.info.get('nodelay',True):
            self._tryTcpNoDelay()

        self.txque = collections.deque()
        self.rxque = collections.deque()

        self.onfini(self._finiSocket)

    def addSockXform(self, xform):
        '''
        Add a data transformation filter to the socket.

        Example:

            sock.addSockXform(xform)

        '''
        xform.init(self)
        self.xforms.append(xform)

    def get(self, prop):
        '''
        Retrieve a property from the socket's info dict.

        Example:

            if sock.get('listen'):
                dostuff()

        '''
        return self.info.get(prop)

    def set(self, prop, valu):
        '''
        Set a property on the Socket by name.

        Example:

            sock.set('woot', 30)

        '''
        self.info[prop] = valu

    def recvall(self, size):
        '''
        Recieve the exact number of bytes requested.
        Returns None on if socket closes early.

        Example:

            byts = sock.recvall(300)
            if byts == None:
                return

            dostuff(byts)

        Notes:
            * this API will trigger fini() on close

        '''
        byts = b''
        remain = size

        try:
            while remain:
                x = self.sock.recv(remain)
                if not x:
                    return None
                byts += x
                remain -= len(x)

        except socket.error as e:
            # fini triggered above.
            return None

        for xform in self.xforms:
            byts = xform.rxform(byts)

        return byts


    def _tx_xform(self, byts):
        '''
        '''
        for xform in self.xforms:
            byts = xform.txform(byts)

        return byts

    def _rx_xform(self, byts):
        for xform in self.xforms:
            byts = xform.rxform(byts)
        return byts

    def sendall(self, byts):
        byts = self._tx_xform(byts)
        return self.sock.sendall(byts)

    def _raw_send(self, byts):
        return self.sock.send(byts)

    def _raw_sendall(self, byts):
        return self.sock.sendall(byts)

    def _raw_recvall(self, size):
        byts = b''
        remain = size

        try:

            while remain:
                x = self.sock.recv(remain)
                if not x:
                    return None
                byts += x
                remain -= len(x)

        except socket.error as e:
            # fini triggered above.
            return None

        return byts

    def recvobj(self):
        for mesg in self:
            return mesg

    def fireobj(self, msg, **msginfo):
        return self.tx( (msg,msginfo) )

    def tx(self, mesg):
        '''
        Transmit a mesg tufo ( type, info ) via the socket using msgpack.
        If present this API is safe for use with a socket in a Plex().
        '''
        if self.plex != None:
            return self.plex._txSockMesg(self,mesg)

        try:
            byts = msgenpack(mesg)

            if len(byts) > 50000 and self.get('sock:can:gzip'):
                byts = sockgzip(byts)

            self.sendall( byts )
            return True

        except socket.error as e:
            self.fini()
            return False

    def rx(self):
        '''
        Yield any completed mesg tufos (type,info) in the recv buffer.

        Example:

            for mesg in sock.rx():
                dostuff(mesg)

        '''

        # the "preread" state for a socket means it has IO todo
        # which is part of it's initial negotiation ( not mesg )
        if self.get('preread'):
            self.fire('link:sock:preread', sock=self)
            return

        byts = self.recv(102400)
        # special case for non-blocking recv with no data ready
        if byts == None:
            return

        try:

            self.unpk.feed(byts)
            for mesg in self.unpk:
                self.rxque.append(mesg)

            while self.rxque:
                yield self.rxque.popleft()

        except Exception as e:
            logger.exception(e)
            self.fini()
            return

    def __iter__(self):
        '''
        Receive loop which yields messages until socket close.
        '''
        while not self.isfini:
            for mesg in self.rx():
                yield mesg

    def _tryTcpNoDelay(self):

        if self.sock.family not in (socket.AF_INET, socket.AF_INET6):
            return False

        if self.sock.type != socket.SOCK_STREAM:
            return False

        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return True

    def accept(self):

        try:

            sock,addr = self.sock.accept()

        except Exception as e:
            return None,None

        sock = Socket(sock, accept=True)

        relay = self.get('relay')
        if relay != None:
            relay._prepLinkSock(sock)

        self.fire('link:sock:accept', sock=sock)

        # check if the link:sock:accept callback fini()d the sock.
        if sock.isfini:
            return None,None

        return sock,addr

    def close(self):
        '''
        Hook the socket close() function to trigger fini()
        '''
        self.fini()

    def recv(self, size):
        '''
        Slighly modified recv function which masks socket errors.
        ( makes them look like a simple close )

        Additionally, any non-blocking recv's with no available data
        will return None!
        '''
        try:

            byts = self.sock.recv(size)
            if not byts:
                self.fini()
                return byts

            return self._rx_xform(byts)

        except ssl.SSLError as e:

            # handle "did not complete" error where we didn't
            # get all the bytes necessary to decrypt the data.
            if e.errno == 2:
                return None

            self.fini()
            return b''

        except socket.error as e:

            if e.errno == errno.EAGAIN:
                return None

            self.fini()
            return b''

    def __getattr__(self, name):
        # allows us to be a thin wrapper
        return getattr(self.sock, name)

    def _finiSocket(self):
        try:
            self.sock.close()
        except OSError as e:
            pass

class Plex(EventBus):
    '''
    Manage multiple Sockets using a multi-plexor IO thread.
    '''
    def __init__(self):
        EventBus.__init__(self)

        #self._plex_sel = selectors.DefaultSelector()

        self._plex_lock = threading.Lock()
        self._plex_socks = {} # set()

        # used for select()
        self._plex_rxsocks = []
        self._plex_txsocks = []
        self._plex_xxsocks = []

        self._plex_wake, self._plex_s2 = socketpair()

        self._plex_s2.set('wake',True)
        self.addPlexSock( self._plex_s2 )

        self._plex_thr = self._plexMainLoop()

        self.onfini( self._onPlexFini )

    def __len__(self):
        return len(self._plex_socks)

    def _popPlexSock(self, iden):
        sock = self._plex_socks.pop(iden,None)
        if sock == None:
            return

        # try/wrap these because list has no discard()
        try:
            self._plex_rxsocks.remove(sock)
        except ValueError as e:
            pass

        try:
            self._plex_txsocks.remove(sock)
        except ValueError as e:
            pass

        try:
            self._plex_xxsocks.remove(sock)
        except ValueError as e:
            pass

        self._plexWake()

    def addPlexSock(self, sock):
        '''
        Add a Socket to the Plex()

        Example:

            plex.addPlexSock(sock)

        '''
        sock.plex = self
        sock.setblocking(0)

        iden = sock.iden

        sock.plex = self

        self._plex_socks[ sock.iden ] = sock

        # we monitor all socks for rx and xx
        self._plex_rxsocks.append(sock)
        self._plex_xxsocks.append(sock)

        def finisock():
            self.fire('link:sock:fini', sock=sock)
            self._popPlexSock(iden)

        sock.onfini( finisock )
        self._plexWake()

    def _txSockMesg(self, sock, mesg):
        # handle the need to send on a socket in the plex
        byts = msgenpack(mesg)
        if len(byts) > 50000 and sock.get('sock:can:gzip'):
            byts = sockgzip(byts)

        with self._plex_lock:

            # we have no backlog!
            if sock.txbuf == None:

                byts = sock._tx_xform( byts )

                try:

                    sent = sock.send(byts)

                except ssl.SSLError as e:
                    # FIXME isolate this filth within link modules.
                    sent = 0
                    if e.errno != 3:
                        #logger.exception(e)
                        sock.fini()
                        return

                except Exception as e:
                    #logger.exception(e)
                    sock.fini()
                    return

                blen = len(byts)
                if sent == blen:
                    return

                # our send was a bit short...
                sock.txbuf = byts[sent:]
                sock.txsize += (blen-sent)
                sock.fire('sock:tx:size', size=sock.txsize)

                self._plex_txsocks.append(sock)
                self._plexWake()
                return

            # so... we have a backlog...
            sock.txque.append(byts)

            sock.txsize += len(byts)
            sock.fire('sock:tx:size', size=sock.txsize)

    def _runSockTx(self, sock):
        # handle socket select() for tx
        # ( this is *always* run by plexMainLoop() )
        with self._plex_lock:

            sent = sock.send( sock.txbuf )

            sock.txsize -= sent
            sock.fire('sock:tx:size', size=sock.txsize)

            # did we not even manage the whole txbuf?
            if sent < len(sock.txbuf):
                sock.txbuf = sock.txbuf[sent:]
                return

            # we managed it! any more msgs?
            if not sock.txque:
                sock.txbuf = None

                # SPEED HACK: faster than if sock in txsocks:
                try:
                    self._plex_txsocks.remove(sock)
                except ValueError as e:
                    pass

                return

            # more msgs! lets serialize the next!
            byts = sock.txque.popleft()
            sock.txbuf = sock._tx_xform( byts )

    def _plexWake(self):
        try:
            self._plex_wake.sendall(b'\x00')
        except socket.error as e:
            return

    @s_threads.firethread
    def _plexMainLoop(self):

        s_threads.iCantWait(name='SynPlexMain')

        while not self.isfini:

            try:
                rxlist,txlist,xxlist = select.select(self._plex_rxsocks,self._plex_txsocks,self._plex_xxsocks,0.2)
            # mask "bad file descriptor" race and go around again...
            except Exception as e:
                continue

            try:

                for rxsock in rxlist:

                    if rxsock.get('wake'):
                        rxsock.recv(10240)
                        continue

                    # if he's a listen sock... accept()
                    if rxsock.get('listen'):
                        connsock,connaddr = rxsock.accept()
                        if connsock != None:
                            rxsock.fire('link:sock:init', sock=connsock)

                        continue

                    # yield any completed mesgs
                    for mesg in rxsock.rx():
                        rxsock.fire('link:sock:mesg', sock=rxsock, mesg=mesg)

                for txsock in txlist:
                    self._runSockTx(txsock)

                [ sock.fini() for sock in xxlist ]

            except Exception as e:
                logger.warning('plexMainLoop: %s', e)

    def _onPlexFini(self):

        socks = list(self._plex_socks.values())
        [ s.fini() for s in socks ]

        self._plex_wake.fini()

        self._plex_thr.join()

def listen(sockaddr,**sockinfo):
    '''
    Simplified listening socket contructor.
    '''
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(sockaddr)
        sock.listen(120)
        return Socket(sock,listen=True,**sockinfo)

    except socket.error as e:
        sock.close()
        raise

def connect(sockaddr,**sockinfo):
    '''
    Simplified connected TCP socket constructor.
    '''
    sock = socket.socket()

    try:
        sock.connect(sockaddr)
        return Socket(sock,**sockinfo)

    except Exception as e:
        sock.close()
        raise

def _sockpair():
    s = socket.socket()
    s.bind(('127.0.0.1',0))
    s.listen(1)

    s1 = socket.socket()
    s1.connect( s.getsockname() )

    s2 = s.accept()[0]

    s.close()
    return Socket(s1),Socket(s2)

def socketpair():
    '''
    Standard sockepair() on posix systems, and pure shinanegans on windows.
    '''
    try:
        s1,s2 = socket.socketpair()
        return Socket(s1),Socket(s2)
    except AttributeError as e:
        return _sockpair()

def inet_pton(afam,text):
    '''
    Implements classic socket.inet_pton regardless of platform. (aka windows)
    '''
    return s_thisplat.inet_pton(afam,text)

def inet_ntop(afam,byts):
    '''
    Implements classic socket.inet_ntop regardless of platform. (aka windows)
    '''
    return s_thisplat.inet_ntop(afam,byts)

def hostaddr(dest='8.8.8.8'):
    '''
    Retrieve the ipv4 address for this host ( optionally as seen from dest ).

    Example:

        addr = s_socket.hostaddr()

    '''
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    # doesn't actually send any packets!
    sock.connect( (dest,80) )
    addr,port = sock.getsockname()

    sock.close()

    return addr

# make a plex and register an atexit handler.
def _plex_ctor():
    plex = Plex()
    atexit.register( plex.fini )
    return plex

# add a Plex constructor to the global scope
s_scope.ctor('plex',_plex_ctor)
