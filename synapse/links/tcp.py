import time
import socket
import threading

import synapse.lib.socket as s_socket

from synapse.common import *
from synapse.links.common import *

def reqValidHost(link):
    host = link[1].get('host')
    if host == None:
        raise PropNotFound('host')

    try:
        socket.gethostbyname(host)
    except socket.error as e:
        raise BadPropValu('host=%r' % host)

def reqValidPort(link):
    port = link[1].get('port')
    if port == None:
        raise PropNotFound('host')

    if port < 0 or port > 65535:
        raise BadPropValue('port=%d' % (port,))

class TcpRelay(LinkRelay):
    '''
    Implements the TCP protocol for synapse.
    '''
    proto = 'tcp'

    def _reqValidLink(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')

        if host == None:
            raise PropNotFound('host')

        if port == None:
            raise PropNotFound('port')

    def _listen(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')
        sock = s_socket.listen((host,port))
        if sock != None:
            self.link[1]['port'] = sock.getsockname()[1]
        return sock

    def _connect(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')
        sock = s_socket.connect((host,port))
        return sock

