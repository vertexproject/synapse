import time
import socket

import synapse.lib.socket as s_socket

from synapse.common import *
from synapse.links.common import *

class TcpRelay(LinkRelay):
    '''
    Implements the TCP protocol for synapse.

    tcp://[user[:passwd]@]<host>[:port]/<path>

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

