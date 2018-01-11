import ssl
import zlib
import errno
import atexit
import select
import socket
import logging
import msgpack
import threading
import collections

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads
import synapse.lib.thisplat as s_thisplat

from synapse.eventbus import EventBus

def sockgzip(byts):
    blen = len(byts)
    byts = zlib.compress(byts)
    #print('GZIP DELTA: %d -> %d' % (blen,len(byts)))
    return s_msgpack.en(('sock:gzip', {'data': byts}))

class Socket(EventBus):
    '''
    Wrapper for the builtin socket.Socket class.

    Args:
        sock socket.socket: socket to wrap
        **info:
    '''

    def __init__(self, sock, **info):
        EventBus.__init__(self)

        self.sock = sock  # type: socket.socket
        self.unpk = msgpack.Unpacker(use_list=False, encoding='utf8',
                                     unicode_errors='surrogatepass')
        self.iden = s_common.guid()

        self.info = info
        self.blocking = True    # sockets are blocking by default

        if self.info.get('nodelay', True):
            self._tryTcpNoDelay()

        self.txbuf = None   # the remainder of a partially sent byts
        self.txque = collections.deque()
        self.rxque = collections.deque()

        self.onfini(self._finiSocket)

    def _addTxByts(self, byts):
        self.txque.append(byts)
        self.fire('sock:tx:add')

    def send(self, byts):
        '''
        Send bytes on the socket.

        Args:
            byts (bytes): The bytes to send

        Returns:
            int: The sent byte count (or None) on fini()
        '''
        try:
            return self.sock.send(byts)
        except (OSError, ConnectionError) as e:
            logger.exception('Error during socket.send() - shutting down socket [%s]', self)
            self.fini()
            return None

    def runTxLoop(self):
        '''
        Run a pass through the non-blocking tx loop.

        Returns:
            (bool): True if there is still more work to do
        '''
        while True:

            if not self.txbuf:

                if not self.txque:
                    break

                self.txbuf = self.txque.popleft()
                self.fire('sock:tx:pop')

            sent = self.send(self.txbuf)
            self.txbuf = self.txbuf[sent:]

            # if we still have a txbuf after sending
            # we could only send part of the buffer
            if self.txbuf:
                break

        if not self.txbuf and not self.txque:
            return False

        return True

    def get(self, prop, defval=None):
        '''
        Retrieve a property from the socket's info dict.

        Example:

            if sock.get('listen'):
                dostuff()

        '''
        return self.info.get(prop, defval)

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

        return byts

    def recvobj(self):
        for mesg in self:
            return mesg

    def setblocking(self, valu):
        '''
        Set the socket's blocking mode to True/False.

        Args:
            valu (bool): False to set socket non-blocking
        '''
        valu = bool(valu)
        self.blocking = valu
        self.sock.setblocking(valu)

    def tx(self, mesg):
        '''
        Transmit a mesg tufo ( type, info ) via the socket using msgpack.
        If present this API is safe for use with a socket in a Plex().
        '''

        byts = s_msgpack.en(mesg)
        return self.txbytes(byts)

    def txbytes(self, byts):

        # we may support gzip on the socket message
        if len(byts) > 50000 and self.get('sock:can:gzip'):
            byts = sockgzip(byts)

        # if the socket is non-blocking assume someone is managing
        # the socket via sock:tx:add events
        if not self.blocking:
            self._addTxByts(byts)
            return True

        try:
            self.sendall(byts)
            return True
        except (OSError, ConnectionError) as e:
            logger.exception('Error during socket.txbytes() - shutting down socket [%s]', self)
            self.fini()
            return False

    def rx(self):
        '''
        Yield any completed mesg tufos (type,info) in the recv buffer.

        Example:

            for mesg in sock.rx():
                dostuff(mesg)

        '''
        # Yield any objects we have already queued up first.
        while self.rxque:
            yield self.rxque.popleft()

        # the "preread" state for a socket means it has IO todo
        # which is part of it's initial negotiation ( not mesg )
        if self.get('preread'):
            self.fire('link:sock:preread', sock=self)
            return

        byts = self.recv(1024000)

        # special case for non-blocking recv with no data ready
        if byts is None:
            return

        try:
            self.unpk.feed(byts)
            for mesg in self.unpk:
                self.rxque.append(mesg)

            while self.rxque:
                yield self.rxque.popleft()

        except Exception as e:
            logger.exception('Error during unpacking / yielding message - shutting down socket [%s]', self)
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

            sock, addr = self.sock.accept()

        except Exception as e:
            return None, None

        logger.debug('Accepting connection from %r', addr)
        sock = self.__class__(sock, accept=True)

        relay = self.get('relay')
        if relay is not None:
            relay._prepLinkSock(sock)

        self.fire('link:sock:accept', sock=sock)

        # check if the link:sock:accept callback fini()d the sock.
        if sock.isfini:
            return None, None

        return sock, addr

    def close(self):
        '''
        Hook the socket close() function to trigger fini()
        '''
        self.fini()

    def recv(self, size):
        '''
        Slightly modified recv function which masks socket errors.
        ( makes them look like a simple close )

        Additionally, any non-blocking recv's with no available data
        will return None!
        '''
        try:

            byts = self.sock.recv(size)
            if not byts:
                self.fini()
                return byts

            return byts

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

        self._plex_thr = None
        self._plex_lock = threading.Lock()
        self._plex_socks = {}

        # used for select()
        self._plex_rxsocks = []
        self._plex_txsocks = []
        self._plex_xxsocks = []

        self._plex_wake, self._plex_s2 = socketpair()

        self._plex_s2.set('wake', True)
        self.addPlexSock(self._plex_s2)

        self.onfini(self._onPlexFini)

        self._plex_thr = self._plexMainLoop()

    def __len__(self):
        return len(self._plex_socks)

    def getPlexSocks(self):
        '''
        Return a list of the Socket()s managed by the Plex().

        Returns:
            ([Socket(),...]):   The list of Socket() instances.
        '''
        return self._plex_socks.values()

    def _finiPlexSock(self, sock):

        self._plex_socks.pop(sock.iden, None)

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

        self.wake()

        # call sock fini from a pool thread
        if not sock.isfini:
            s_glob.pool.call(sock.fini)

    def wake(self):
        '''
        '''
        if s_threads.current() is self._plex_thr:
            return

        self._plexWake()

    def addPlexSock(self, sock):
        '''
        Add a Socket to the Plex()

        Args:
            sock (Socket): Socket to add.

        Example:

            plex.addPlexSock(sock)

        '''
        sock.setblocking(0)

        def txadd(mesg):

            with self._plex_lock:
                istx = sock.get('plex:istx')

                if not istx:
                    # since it's not in the tx list yet lets fire the
                    # tx loop and see if we need to be added...
                    if sock.runTxLoop():
                        sock.set('plex:istx', True)
                        self._plex_txsocks.append(sock)
                        self.wake()

        sock.on('sock:tx:add', txadd)

        self._plex_socks[sock.iden] = sock

        # we monitor all socks for rx and xx
        self._plex_rxsocks.append(sock)
        self._plex_xxsocks.append(sock)

        def fini():
            self._finiPlexSock(sock)

        sock.onfini(fini)
        self.wake()

    def _plexWake(self):
        try:
            self._plex_wake.sendall(b'\x00')
        except socket.error as e:
            return

    @s_common.firethread
    def _plexMainLoop(self):

        s_threads.iCantWait(name='SynPlexMain')

        while not self.isfini:

            try:
                rxlist, txlist, xxlist = select.select(self._plex_rxsocks, self._plex_txsocks, self._plex_xxsocks, 0.2)
            except Exception as e:
                # go through ALL of our sockets, and call _finiPlexSock on that socket if it has been fini'd or
                # if those sockets fileno() call is -1
                # The .copy() method is used since it is faster for small lists.
                # The identity check of -1 is reliant on a CPython optimization which keeps a single
                # addressed copy of integers between -5 and 256 in. memory
                logger.exception('Error during socket select. Culling fini or fileno==-1 sockets.')
                [self._finiPlexSock(sck) for sck in self._plex_rxsocks.copy() if sck.isfini or sck.fileno() is -1]
                [self._finiPlexSock(sck) for sck in self._plex_txsocks.copy() if sck.isfini or sck.fileno() is -1]
                [self._finiPlexSock(sck) for sck in self._plex_xxsocks.copy() if sck.isfini or sck.fileno() is -1]
                continue

            try:

                for rxsock in rxlist:

                    if rxsock.get('wake'):
                        rxsock.recv(10240)
                        continue

                    # if he's a listen sock... accept()
                    if rxsock.get('listen'):
                        connsock, connaddr = rxsock.accept()
                        if connsock is not None:
                            self.addPlexSock(connsock)
                            self.fire('link:sock:init', sock=connsock)

                        continue

                    # yield any completed mesgs
                    for mesg in rxsock.rx():
                        self.fire('link:sock:mesg', sock=rxsock, mesg=mesg)

                for txsock in txlist:
                    if not txsock.runTxLoop():
                        txsock.set('plex:istx', False)
                        try:
                            self._plex_txsocks.remove(txsock)
                        except ValueError as e:
                            pass

                [self._finiPlexSock(sock) for sock in xxlist]

            except Exception as e:
                logger.warning('plexMainLoop: %s', e)

    def _onPlexFini(self):

        socks = list(self._plex_socks.values())
        [s.fini() for s in socks]

        self._plex_wake.fini()

        self._plex_thr.join()

def listen(sockaddr, **sockinfo):
    '''
    Simplified listening socket contructor.
    '''
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(sockaddr)
        sock.listen(120)
        return Socket(sock, listen=True, **sockinfo)

    except socket.error as e:
        sock.close()
        raise

def connect(sockaddr, **sockinfo):
    '''
    Simplified connected TCP socket constructor.
    '''
    sock = socket.socket()

    try:
        sock.connect(sockaddr)
        return Socket(sock, **sockinfo)

    except Exception as e:
        sock.close()
        raise

def _sockpair():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    s.listen(1)

    s1 = socket.socket()
    s1.connect(s.getsockname())

    s2 = s.accept()[0]

    s.close()
    return Socket(s1), Socket(s2)

def socketpair():
    '''
    Standard sockepair() on posix systems, and pure shinanegans on windows.
    '''
    try:
        s1, s2 = socket.socketpair()
        return Socket(s1), Socket(s2)
    except AttributeError as e:
        return _sockpair()

def inet_pton(afam, text):
    '''
    Implements classic socket.inet_pton regardless of platform. (aka windows)
    '''
    return s_thisplat.inet_pton(afam, text)

def inet_ntop(afam, byts):
    '''
    Implements classic socket.inet_ntop regardless of platform. (aka windows)
    '''
    return s_thisplat.inet_ntop(afam, byts)

def hostaddr(dest='8.8.8.8'):
    '''
    Retrieve the ipv4 address for this host ( optionally as seen from dest ).

    Example:

        addr = s_socket.hostaddr()

    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # doesn't actually send any packets!
    sock.connect((dest, 80))
    addr, port = sock.getsockname()

    sock.close()

    return addr

# make a plex and register an atexit handler.
def _plex_ctor():
    plex = Plex()
    atexit.register(plex.fini)
    return plex

# add a Plex constructor to the global scope
s_scope.ctor('plex', _plex_ctor)
