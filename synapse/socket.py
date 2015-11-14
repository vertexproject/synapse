from __future__ import absolute_import,unicode_literals

import os
import atexit
import socket
import logging
import msgpack
import traceback

logger = logging.getLogger(__name__)

from synapse.compat import queue
from synapse.compat import selectors

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.threads as s_threads

from synapse.eventbus import EventBus
from synapse.statemach import keepstate

class SockXform:
    '''
    Base class for a socket bytes transform class.

    Notes:

        * for obj tx/rx, these are called once per.
    '''
    #TODO: maybe make this use bytebuffer and in-band xform
    def init(self, sock):
        pass

    def send(self, byts):
        return byts

    def recv(self, byts):
        return byts

class MesgRouter:
    '''
    The MesgRouter mixin allows registration of callback methods to
    receive link:sock:mesg callbacks.

    Example:

        def myMesgCall(sock, mesg):
            x = dostuff(mesg)
            sock.sendobj(x)

        sock.setMesgFunc('my:mesg', myMesgCall )

    '''
    def __init__(self):
        self._mesg_en = False
        self._mesg_meths = {}

    def _xlateSockMesg(self, event):
        sock = event[1].get('sock')
        mesg = event[1].get('mesg')
        self.runMesgMeth(sock,mesg)

    def setMesgFunc(self, name, meth):
        if not self._mesg_en:
            self._mesg_en = True
            self.on('link:sock:mesg', self._xlateSockMesg )

        self._mesg_meths[name] = meth

    def runMesgMeth(self, sock, mesg):
        name = mesg[0]
        meth = self._mesg_meths.get(name)
        if meth == None:
            return

        try:
            meth(sock,mesg)
        except Exception as e:
            traceback.print_exc()

class Socket(EventBus,MesgRouter):

    def __init__(self, sock, **info):
        EventBus.__init__(self)
        MesgRouter.__init__(self)
        self.sock = sock
        self.unpk = msgpack.Unpacker(use_list=0,encoding='utf8')
        self.iden = s_common.guid()
        self.xforms = []        # list of SockXform instances
        self.crypto = None
        self.sockinfo = info

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
        return self.sockinfo.get(prop)

    def set(self, prop, valu):
        '''
        Set a property on the Socket by name.

        Example:

            sock.set('woot', 30)

        '''
        self.sockinfo[prop] = valu

    def __setitem__(self, prop, valu):
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
            byts = xform.recv(byts)

        return byts


    def sendall(self, byts):
        for xform in self.xforms:
            byts = xform.send(byts)
        return self.sock.sendall(byts)

    def fireobj(self, typ, **info):
        return self.sendobj( (typ,info) )

    def sendobj(self, msg):
        '''
        Serialize an object using msgpack and send on the socket.
        Returns True on success and False on socket error.

        Example:

            tufo = ('woot',{'foo':'bar'})
            sock.sendobj(tufo)

        Notes:

            * This method will trigger fini() on errors.

        '''
        try:
            self.sendall( msgpack.dumps(msg, use_bin_type=True) )
            return True
        except socket.error as e:
            self.close()
            return False

    def recvobj(self):
        '''
        Recieve one msgpack'd socket message.
        '''
        while not self.isfini:
            byts = self.recv(102400)
            if not byts:
                return None

            try:
                self.unpk.feed(byts)
                for mesg in self.unpk:
                    self.fire('link:sock:mesg', sock=self, mesg=mesg)
                    return mesg

            except Exception as e:
                self.close()

    def __iter__(self):
        '''
        Receive loop which yields messages until socket close.
        '''
        while not self.isfini:

            byts = self.recv(1024000)
            if not byts:
                self.close()
                return

            try:
                self.unpk.feed(byts)
                for mesg in self.unpk:
                    self.fire('link:sock:mesg', sock=self, mesg=mesg)
                    yield mesg

            except Exception as e:
                self.close()

    def accept(self):
        try:
            conn,addr = self.sock.accept()
        except ConnectionError as e:
            self.close()
            return None,None
        return Socket(conn),addr

    def close(self):
        '''
        Hook the socket close() function to trigger fini()
        '''
        self.fini()

    def recv(self, size):
        '''
        Slighly modified recv function which masks socket errors.
        ( makes them look like a simple close )
        '''
        try:
            byts = self.sock.recv(size)
            for xform in self.xforms:
                byts = xform.recv(byts)

            if not byts:
                self.close()

            return byts
        except socket.error as e:
            # fini triggered above.
            return b''

    def __getattr__(self, name):
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

        self._plex_sel = selectors.DefaultSelector()
        self._plex_socks = set()

        self._plex_wake, self._plex_s2 = socketpair()

        self._plex_thr = self._plexMainLoop()

        self.onfini( self._onPlexFini )

    def __len__(self):
        return len(self._plex_socks)

    def addPlexSock(self, sock):
        '''
        Add a Socket to the Plex()

        Example:

            plex.addPlexSock(sock)

        '''
        sock['plex'] = self
        self._plex_sel.register(sock, selectors.EVENT_READ)
        self._plex_socks.add(sock)

        sock.link( self.dist )

        def finisock():
            sock['plex'] = None
            self._plex_socks.remove(sock)
            #self._plex_sel.unregister(sock)
            self._plexWake()
            self.fire('link:sock:fini', sock=sock)

        sock.onfini( finisock )
        self._plexWake()

    def _plexWake(self):
        self._plex_wake.sendall(b'\x00')

    @s_threads.firethread
    def _plexMainLoop(self):

        self._plex_sel.register( self._plex_s2, selectors.EVENT_READ )

        while not self.isfini:

            try:

                for key,events in self._plex_sel.select(timeout=1):

                    if self.isfini:
                        break

                    sock = key.fileobj
                    if sock == self._plex_s2:
                        sock.recv(1024)
                        continue

                    if sock.get('listen'):
                        # his sock:conn event handles reg
                        newsock = sock.accept()
                        self.addPlexSock(newsock)
                        continue

                    byts = sock.recv(102400)
                    if not byts:
                        sock.fini()
                        continue

                    sock.unpk.feed(byts)
                    for mesg in sock.unpk:
                        sock.fire('link:sock:mesg', sock=sock, mesg=mesg)

            except OSError as e:
                # just go around again... ( probably a close race )
                continue

            except Exception as e:
                traceback.print_exc()
                logger.error('plexMainLoop: %s' % e)

            if self.isfini:
                break

    def _onPlexFini(self):
        self._plex_s2.fini()
        self._plex_wake.fini()
        self._plex_sel.close()

        for sock in list(self._plex_socks):
            sock.fini()

def getGlobPlex():
    '''
    Get/Init a reference to a singular global Plex() multiplexor.

    Example:

        plex = getGlobPlex()

    '''
    with s_glob.lock:
        if s_glob.plex == None:
            s_glob.plex = Plex()

            atexit.register(s_glob.plex.fini)

        return s_glob.plex

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
    return None

def connect(sockaddr,**sockinfo):
    '''
    Simplified connected TCP socket constructor.
    '''
    sock = socket.socket()
    try:
        sock.connect(sockaddr)
        return Socket(sock,**sockinfo)
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
