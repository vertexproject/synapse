import os
import queue
import socket
import msgpack
import selectors
import threading
import traceback

import synapse.link as s_link
import synapse.common as s_common
import synapse.threads as s_threads

from synapse.dispatch import Dispatcher
from synapse.statemach import keepstate

class Socket(Dispatcher):

    def __init__(self, sock, **info):
        Dispatcher.__init__(self)
        self.sock = sock
        self.unpk = msgpack.Unpacker(use_list=0,encoding='utf8')
        self.ident = s_common.guid()
        self.crypto = None
        self.sockinfo = info

        self.synOn('fini', self._finiSocket)

    def __repr__(self):
        return 'Socket: %r' % (self.sockinfo,)

    def getSockId(self):
        '''
        Get the GUID for this socket.

        Examples:

            sid = sock.getSockId()

        '''
        return self.ident

    def getSockInfo(self, prop):
        '''
        Retrieve a property from the socket's info dict.

        Example:

            if sock.getSockInfo('listen'):
                dostuff()

        '''
        return self.sockinfo.get(prop)

    def setSockInfo(self, prop, valu):
        '''
        Set a property on the Socket by name.

        Example:

            sock.setSockInfo('woot', 30)

        '''
        self.sockinfo[prop] = valu

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
            * this API will trigger synFireFini() on close

        '''
        byts = b''
        remain = size
        while remain:
            x = self.recv(remain)
            if not x:
                return None
            byts += x
            remain -= len(x)

        if self.crypto:
            byts = self.crypto.decrypt(byts)

        return byts

    def sendall(self, byts):
        if self.crypto:
            byts = self.crypto.encrypt(byts)
        return self.sock.sendall(byts)

    def sendSockMesg(self, msg):
        '''
        Serialize an object using msgpack and send on the socket.
        Returns True on success and False on socket error.

        Example:

            tufo = ('woot',{'foo':'bar'})
            sock.sendSockMesg(tufo)

        Notes:

            * This method will trigger synFireFini() on errors.

        '''
        try:
            self.sendall( msgpack.dumps(msg, use_bin_type=True) )
            return True
        except socket.error as e:
            self.close()
            return False

    def sendSockErr(self, code, msg, **info):
        info['msg'] = msg
        info['code'] = code
        return self.sendSockMesg( ('err',info) )

    def recvSockMesg(self):
        '''
        Recieve one msgpack'd socket message.
        '''
        while not self.isfini:
            byts = self.recv(102400)
            if not byts:
                return None

            self.unpk.feed(byts)
            for obj in self.unpk:
                return obj

    def recvMesgYield(self):
        '''
        Call recv once and yield any unpacked msgpack objects.
        ( used by selectors to process read events )
        '''
        for obj in self.unpk:
            yield obj

        byts = self.recv(1024000)
        if not byts:
            return
            
        self.unpk.feed(byts)
        for obj in self.unpk:
            yield obj

    def __iter__(self):
        '''
        Receive loop which yields messages until socket close.
        '''
        while not self.isfini:

            byts = self.recv(1024000)
            if not byts:
                self.close()
                return

            self.unpk.feed(byts)
            for obj in self.unpk:
                yield obj

    #def __enter__(self):
        #self.lock.acquire()
        #return self

    #def __exit__(self, t, v, tb):
        #self.close()

    def accept(self):
        conn,addr = self.sock.accept()
        return Socket(conn),addr

    def close(self):
        '''
        Hook the socket close() function to trigger synFireFini()
        '''
        self.synFireFini()

    def recv(self, size):
        '''
        Slighly modified recv function which masks socket errors.
        ( makes them look like a simple close )
        '''
        try:
            byts = self.sock.recv(size)
            if self.crypto:
                byts = self.crypto.decrypt(byts)

            if not byts:
                self.close()

            return byts
        except socket.error as e:
            # synFireFini triggered above.
            return b''

    def _setCryptoProv(self, prov):
        prov.initSockCrypto(self)
        self.crypto = prov

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def _finiSocket(self):
        try:
            self.sock.close()
        except OSError as e:
            pass

class SocketPool(s_link.Linker):
    '''
    A SocketPool uses a single select thread and a pool of handler
    threads to service messages on a group of sockets.

    Additionally, a SocketPool is an instance of a Linker and may
    be used to store and manage persistent link configs.

    '''
    def __init__(self, pool=1, statefd=None):
        self.msgq = queue.Queue()
        self.socks = {}
        self.threads = []
        self.poolinfo = {'pool':pool}

        self.isrun = False

        # these are so we can wake the sleeper
        self.wake1, self.wake2 = socketpair()

        self.wake1.setSockInfo('wake',True)
        self.wake2.setSockInfo('wake',True)

        self.iothr = None
        self.seltor = selectors.DefaultSelector()
        self.seltor.register(self.wake2, selectors.EVENT_READ)

        # Linker is also Dispatcher and StateMachine so
        # it must go after we've got our local data setup
        s_link.Linker.__init__(self, statefd=statefd)
        self.synOn('sockinit', self.addSockToPool )

    def getPoolInfo(self, prop):
        '''
        Retrieve a SocketPool property by name.

        Example:

            woot = pool.getPoolInfo('woot')

        '''
        return self.poolinfo.get(prop)

    @keepstate
    def setPoolInfo(self, prop, valu):
        '''
        Set a SocketPool property by name.

        Example:

            pool.setPoolInfo('woot',30)

        '''
        self.poolinfo[prop] = valu

    def runSockPool(self):
        '''
        Actually begin running the SocketPool.
        '''
        self.isrun = True
        self.iothr = s_threads.worker( self._ioLoopThread )
        pool = self.getPoolInfo('pool')
        self.addPoolWorkers(pool)
        self.runLinkMain()

    @keepstate
    def delPoolLink(self, name):
        '''
        Delete a link from the pool by name.

        Example:

            pool.delPoolLink('woot')

        '''
        return self.links.pop(name,None)

    def getSockById(self, sid):
        '''
        Get a socket from the pool by ID.

        Example:

            sock = pool.getSockById(sid)

        '''
        return self.socks.get(sid)

    def getPoolSocks(self):
        '''
        Get a list of the synapse Socket objects managed by the pool.

        Example:

            for sock in pool.getPoolSocks():
                dostuff()

        '''
        return list(self.socks.values())

    def addSockToPool(self, sock):
        '''
        Add a synapse Socket to the SocketPool to be managed.

        Example:

            pool.addSockToPool(sock)

        '''
        sid = sock.getSockId()

        def popsock():
            self.socks.pop(sid,None)
            self.seltor.unregister(sock)

        sock.synOn('fini',popsock)
        self.synOn('fini', sock.close, weak=True)
        self.socks[ sid ] = sock
        self.seltor.register(sock,selectors.EVENT_READ)

        # wake the sleeper
        self._wakeIoThread()

    def initSockPump(self, sock1, sock2):
        '''
        Use the SocketPool to pump data between two sockets.

        Example:

            pool.initSockPump(sock1,sock2)
            # data recv on either is sent to the other

        Notes:

            * If either sock is not yet in the pool, it is
              added.

        '''
        sock1.setSockInfo('pump',sock2)
        sock2.setSockInfo('pump',sock1)
        if self.socks.get( sock1.getSockId() ) == None:
            self.addSockToPool(sock1)

        if self.socks.get( sock2.getSockId() ) == None:
            self.addSockToPool(sock2)

    def addPoolWorkers(self, count):
        '''
        Increase the number of workers in the pool by count.

        Example:

            pool.addPoolWorkers(3)

        Notes:

            * This is considered a "runtime" adjustment and
              does not modify the stored pool=<num> state.

        '''
        for i in range(count):
            self.threads.append( s_threads.worker( self._sockPoolWorker ) )

    def delPoolWorkers(self, count):
        '''
        Reduce the number of workers in the pool by count.

        Example:

            pool.delPoolWorkers(3)

        Notes:

            * This is considered a "runtime" adjustment and
              does not modify the stored pool=<num> state.

        '''
        count = max(count,len(self.threads))
        for i in range(count):
            self.msgq.put(None)

    def _wakeIoThread(self):
        self.wake1.send(b'\x00')

    def _ioLoopThread(self):
        while not self.isfini:

            for key,events in self.seltor.select(timeout=1):
                if self.isfini:
                    return

                sock = key.fileobj

                if sock.getSockInfo('wake'):
                    sock.recv(1)
                    continue

                pump = sock.getSockInfo('pump')
                if pump:
                    byts = sock.recv(1024000)
                    self.msgq.put((sock,byts))
                    continue

                if sock.getSockInfo('listen'):
                    sock,addr = sock.accept()
                    self.addSockToPool( sock )
                    continue

                for msg in sock.recvMesgYield():
                    self.msgq.put((sock,msg))

    def _sockPoolWorker(self):
        while True:
            todo = self.msgq.get()
            if todo == None:
                return

            sock,msg = todo

            pump = sock.getSockInfo('pump')
            if pump != None:
                pump.sendall(msg)
                return

            self.synFire('sockmesg',sock,msg)

    def _finiSockPool(self):
        self._wakeIoThread()
        self.wake1.close()
        self.wake2.close()

        self.iothr.join()

        for sock in self.getPoolSocks():
            sock.close()

        for i in range(len(self.threads)):
            self.msgq.put(None)

        for t in self.threads:
            t.join()

        self.seltor.close()

def listen(sockaddr):
    '''
    Simplified listening socket contructor.
    '''
    sock = socket.socket()
    try:
        sock.bind(sockaddr)
        sock.listen(120)
        return Socket(sock,listen=True)
    except socket.error as e:
        sock.close()
    return None

def connect(sockaddr):
    '''
    Simplified connected TCP socket constructor.
    '''
    sock = socket.socket()
    try:
        sock.connect(sockaddr)
        return Socket(sock)
    except socket.error as e:
        sock.close()
    return None

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
