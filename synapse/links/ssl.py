from __future__ import absolute_import,unicode_literals

import os
import ssl
import socket

import synapse.lib.socket as s_socket

from synapse.common import *
from synapse.links.common import *

class SslRelay(LinkRelay):

    proto = 'ssl'

    def _reqValidLink(self):
        host = self.link[1].get('host')
        port = self.link[1].get('port')

        if host == None:
            raise PropNotFound('host')

        if port == None:
            raise PropNotFound('port')

        cafile = self.link[1].get('cafile')
        if cafile != None and not os.path.isfile(cafile):
            raise NoSuchFile(cafile)

        keyfile = self.link[1].get('keyfile')
        if keyfile != None and not os.path.isfile(keyfile):
            raise NoSuchFile(keyfile)

        certfile = self.link[1].get('certfile')
        if certfile != None and not os.path.isfile(certfile):
            raise NoSuchFile(certfile)

    def _listen(self):

        host = self.link[1].get('host')
        port = self.link[1].get('port')

        sock = socket.socket()
        sock.bind( (host,port) )

        sock.listen(100)

        self.link[1]['port'] = sock.getsockname()[1]

        cafile = self.link[1].get('cafile')
        keyfile = self.link[1].get('keyfile')
        certfile = self.link[1].get('certfile')

        sslopts = dict(server_side=True,
                       ca_certs=cafile,
                       keyfile=keyfile,
                       certfile=certfile,
                       cert_reqs=ssl.CERT_NONE,
                       ssl_version=ssl.PROTOCOL_TLSv1)

        # if they give a cafile to the server, require client certs
        if cafile != None:
            sslopts['cert_reqs'] = ssl.CERT_REQUIRED

        wrap = ssl.wrap_socket(sock, **sslopts)
        return s_socket.Socket(wrap)

    def _connect(self):
        sock = socket.socket()

        host = self.link[1].get('host')
        port = self.link[1].get('port')

        cafile = self.link[1].get('cafile')
        keyfile = self.link[1].get('keyfile')
        certfile = self.link[1].get('certfile')

        sslopts = dict(ca_certs=cafile,
                       keyfile=keyfile,
                       certfile=certfile,
                       ssl_version=ssl.PROTOCOL_TLSv1)

        if not self.link[1].get('nocheck'):
            sslopts['cert_reqs'] = ssl.CERT_REQUIRED

        try:
            sock.connect( (host,port) )
            wrap = ssl.wrap_socket(sock, **sslopts)
            return s_socket.Socket(wrap)
        except Exception as e:
            sock.close()
            raise LinkErr( str(e) )

        #try:

            #wrap.connect( (host,port) )

        #except Exception as e:
            #sock.close()
            #raise LinkErr( str(e) )

        #return s_socket.Socket(wrap)
