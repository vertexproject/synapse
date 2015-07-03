import time
import socket

from urllib.parse import urlparse, parse_qsl

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

class TcpProto(LinkProto):
    '''
    Implements the TCP synapse LinkProto.
    '''
    proto = 'tcp'

    def _reqValidLink(self, link):
        lisnaddr = link[1].get('listen')
        connaddr = link[1].get('connect')

        if lisnaddr == None and connaddr == None:
            raise NoLinkProp('listen or connect')

    def _initLinkFromUriParsed(self, parsed, query):
        sockaddr = (parsed.hostname,parsed.port)
        link = tufo('tcp')

        if query.get('listen'):
            link[1]['listen'] = sockaddr
            return link

        link[1]['connect'] = sockaddr
        return link

    def _initLinkSock(self, link):
        sockaddr = link[1].get('connect')
        if sockaddr == None:
            raise NoLinkProp('connect')

        return s_socket.connect( sockaddr, link=link )

    def _initLinkRelay(self, link):
        sockaddr = link[1].get('connect')
        if sockaddr != None:
            return TcpConnectRelay(link)

        sockaddr = link[1].get('listen')
        if sockaddr != None:
            return TcpListenRelay(link)

        raise NoLinkProp()

class TcpConnectRelay(LinkRelay):
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

    def _runConnLoop(self):
        sock = None
        delay = self.link[1].get('delay',0)

        while not self.isfini and sock == None:

            sockaddr = self.link[1].get('connect')
            sock = s_socket.connect(sockaddr)

            if sock == None:
                time.sleep(delay)
                backoff = self.link[1].get('backoff', 0.2)
                maxdelay = self.link[1].get('maxdelay', 2)
                delay = min( maxdelay, delay + backoff )

        return sock

class TcpListenRelay(LinkRelay):
    '''
    Implements a TCP server synapse LinkRelay.
    '''
    def __init__(self, link):
        LinkRelay.__init__(self, link)
        self.synOnFini(self._finiTcpRelay)

    def runLinkRelay(self):
        # steal this method so we can fail synchronously
        sockaddr = self.link[1].get('listen')
        self.lisn = s_socket.listen(sockaddr, link=self.link)
        if self.lisn == None:
            raise Exception('TcpRelay: bind failed: %r' % (sockaddr,))

        # dynamically update the link port ( non-persistent )
        if sockaddr[1] == 0:
            sockaddr = self.lisn.getsockname()
            self.link[1]['listen'] = sockaddr

        return LinkRelay.runLinkRelay(self)

    def _runLinkRelay(self):

        while not self.isfini:
            sock,addr = self.lisn.accept()
            if sock == None:
                break

            if self.isfini:
                sock.close()
                break

            self.boss.worker( self._runSockLoop, sock )

    def _wakeTheSleeper(self):
        sockaddr = self.lisn.getsockname()
        sock = s_socket.connect(sockaddr)
        if sock != None:
            sock.close()

    def _finiTcpRelay(self):
        self._wakeTheSleeper()
        self.lisn.close()
        self.boss.synFini()
