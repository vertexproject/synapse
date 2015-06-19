import time
import socket

from urllib.parse import urlparse, parse_qsl

import synapse.socket as s_socket

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

class TcpProto(LinkProto):
    '''
    Implements a TCP client synapse LinkProto.
    '''
    proto = 'tcp'

    def _reqValidLink(self, link):
        reqValidHost(link)
        reqValidPort(link)

    def _initLinkFromUri(self, uri):
        p = urlparse(uri)    

        port = p.port
        host = p.hostname

        info = dict( parse_qsl( p.query ) )
        info['host'] = host
        info['port'] = port

        link = (p.scheme,info)
        self.reqValidLink(link)
        return link

    def _initLinkSock(self, link):
        host = link[1].get('host')
        port = link[1].get('port')
        return s_socket.connect( (host,port) )

    def _initLinkRelay(self, link):
        return TcpRelay(link)

class TcpRelay(LinkRelay):
    '''
    Implements a TCP client synapse LinkRelay.
    '''

    def _runLinkRelay(self):
        while not self.isfini:
            sock = self._runConnLoop()
            if sock == None:
                break

            self.synFire('link:sock:init',sock=sock)

            for mesg in sock:
                self.synFire('link:sock:mesg',sock=sock,mesg=mesg)

            self.synFire('link:sock:fini',sock=sock)

    def _getSockAddr(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')
        return (host,port)

    def _runConnLoop(self):
        sock = None
        delay = self.link[1].get('delay',0)

        while not self.isfini and sock == None:

            sockaddr = self._getSockAddr()
            sock = s_socket.connect(sockaddr)

            if sock == None:
                time.sleep(delay)
                backoff = self.link[1].get('backoff', 0.2)
                maxdelay = self.link[1].get('maxdelay', 2)
                delay = min( maxdelay, delay + backoff )

        return sock

class TcpdProto(TcpProto):
    '''
    Implements a TCP server synapse LinkProto.
    '''
    name = 'tcpd'

    def _initLinkRelay(self, link):
        return TcpdRelay(link)

class TcpdRelay(TcpRelay):
    '''
    Implements a TCP server synapse LinkRelay.
    '''
    def __init__(self, link):

        LinkRelay.__init__(self, link)
        self.synOnFini(self._finiTcpdRelay)

    def runLinkRelay(self):
        # steal this method so we can fail synchronously
        sockaddr = self._getSockAddr()
        self.lisn = s_socket.listen(sockaddr)
        if self.lisn == None:
            raise Exception('TcpRelay: bind failed: %r' % (sockaddr,))

        # dynamically update the link port ( non-persistent )
        if self.link[1].get('port') == 0:
            bindaddr = self.lisn.getsockname()
            self.link[1]['port'] = bindaddr[1]

        return LinkRelay.runLinkRelay(self)

    def _runLinkRelay(self):

        while not self.isfini:
            sock,addr = self.lisn.accept()

            if self.isfini:
                sock.close()
                break

            self.boss.worker( self._runSockThread, sock )

    def _runSockThread(self, sock):

        timeout = self.link[1].get('timeout')
        if timeout != None:
            sock.settimeout(timeout)

        self.synOnFini(sock.close,weak=True)
        self.synFire('link:sock:init',sock=sock)

        for mesg in sock:
            self.synFire('link:sock:mesg',sock=sock,mesg=mesg)

        self.synFire('link:sock:fini',sock=sock)

    def _wakeTheSleeper(self):
        sockaddr = self.lisn.getsockname()
        sock = s_socket.connect(sockaddr)
        if sock != None:
            sock.close()

    def _finiTcpdRelay(self):
        self._wakeTheSleeper
        self.lisn.close()
        self.boss.synFini()
