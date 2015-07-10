import time
import socket

import synapse.socket as s_socket

from synapse.common import *
from synapse.links.common import *

def reqValidHost(link):
    host = link[1].get('host')
    if host == None:
        raise NoLinkProp('host')

    try:
        socket.gethostbyname(host)
    except socket.error as e:
        raise BadLinkProp('host')

def reqValidPort(link):
    port = link[1].get('port')
    if port == None:
        raise NoLinkProp('host')

    if port < 0 or port > 65535:
        raise BadLinkProp('port')

class TcpRelay(LinkRelay):
    '''
    Implements the TCP protocol for synapse.
    '''
    proto = 'tcp'

    def _reqValidLink(self, link):
        host = link[1].get('host')
        port = link[1].get('port')

        if host == None:
            raise NoLinkProp('host')

        if port == None:
            raise NoLinkProp('port')

    def _initServerSock(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')
        sock = s_socket.listen((host,port),relay=self)
        if sock != None:
            self.link[1]['port'] = sock.getsockname()[1]
        return sock

    def _initClientSock(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')
        sock = s_socket.connect((host,port),relay=self)
        return sock

    def _initLinkServer(self):
        return TcpServer(self)

    def _initLinkClient(self):
        return TcpClient(self)

    def _initLinkPeer(self):
        return LinkPeer(self)

class TcpClient(LinkClient):
    '''
    Implements a TCP client synapse LinkRelay.
    '''
    def _runLinkClient(self):
        while not self.isfini:
            sock = self._runConnLoop()
            if sock == None:
                break

            self.fire('link:sock:init',sock=sock)

            for mesg in sock:
                self.fire('link:sock:mesg',sock=sock,mesg=mesg)

            self.fire('link:sock:fini',sock=sock)

    def _runConnLoop(self):
        sock = None
        delay = self.relay.link[1].get('delay',0)

        while not self.isfini and sock == None:

            sock = self.relay.initClientSock()

            if sock == None:
                time.sleep(delay)
                backoff = self.link[1].get('backoff', 0.2)
                maxdelay = self.link[1].get('maxdelay', 2)
                delay = min( maxdelay, delay + backoff )

        return sock

class TcpServer(LinkServer):
    '''
    Implements a synapse TCP server.
    '''
    def _initLinkServer(self):
        self.onfini( self._finiTcpServer )
        self.lisn = self.relay.initServerSock()
        if self.lisn == None:
            raise Exception('TcpServer: bind failed: %r' % (self.relay.link,))

    def _runLinkServer(self):
        while not self.isfini:
            sock,addr = self.lisn.accept()
            if sock == None:
                break

            if self.isfini:
                sock.close()
                break

            self.boss.worker( self._runSockLoop, sock )

    def _wakeTheSleeper(self):
        sock = self.relay.initClientSock()
        if sock != None:
            sock.fini()

    def _finiTcpServer(self):
        self._wakeTheSleeper()
        self.lisn.close()
        self.boss.fini()

