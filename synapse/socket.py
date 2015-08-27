from __future__ import absolute_import,unicode_literals

import os
import socket
import msgpack
import traceback

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

class Socket(EventBus):

    def __init__(self, sock, **info):
        EventBus.__init__(self)
        self.sock = sock
        self.unpk = msgpack.Unpacker(use_list=0,encoding='utf8')
        self.ident = s_common.guid()
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

    def fireobj(self, name, **info):
        return self.sendobj( (name,info) )

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

    def senderr(self, code, msg, **info):
        info['msg'] = msg
        info['code'] = code
        return self.sendobj( ('err',info) )

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
                for obj in self.unpk:
                    return obj

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
                for obj in self.unpk:
                    yield obj

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
