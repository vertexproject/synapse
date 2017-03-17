from __future__ import absolute_import,unicode_literals

import os
import ssl
import socket
import logging

logger = logging.getLogger(__name__)

import synapse.compat as s_compat
import synapse.lib.socket as s_socket
import synapse.lib.certdir as s_certdir

from OpenSSL import crypto
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
        if cafile != None:
            self.link[1]['cafile'] = reqpath(cafile)

        keyfile = self.link[1].get('keyfile')
        if keyfile != None:
            self.link[1]['keyfile'] = reqpath(keyfile)

        certfile = self.link[1].get('certfile')
        if certfile != None:
            self.link[1]['certfile'] = reqpath(certfile)

    def _listen(self):

        host = self.link[1].get('host')
        port = self.link[1].get('port')

        sock = socket.socket()
        sock.bind( (host,port) )

        sock.listen(100)

        self.link[1]['port'] = sock.getsockname()[1]

        certdir = self.link[1].get('certdir')
        cdir = s_certdir.CertDir(path=certdir)

        hostname = socket.gethostname()

        cafile = self.link[1].get('cafile')
        if cafile == None:
            caname = self.link[1].get('ca')
            if caname != None:
                cafile = cdir.getCaCertPath(caname)

        certfile = self.link[1].get('certfile')
        if certfile == None:
            certfile = cdir.getHostCertPath(hostname)

        keyfile = self.link[1].get('keyfile')
        if keyfile == None:
            keyfile = cdir.getHostKeyPath(hostname)

        sslopts = dict(server_side=True,
                       ca_certs=cafile,
                       keyfile=keyfile,
                       certfile=certfile,
                       cert_reqs=ssl.CERT_NONE,
                       do_handshake_on_connect=False,
                       ssl_version=ssl.PROTOCOL_TLSv1,
                  )

        # if they give a cafile to the server, require client certs
        if cafile != None:
            sslopts['cert_reqs'] = ssl.CERT_REQUIRED

        wrap = ssl.wrap_socket(sock, **sslopts)

        sock = s_socket.Socket(wrap)
        sock.on('link:sock:accept', self._onSslAccept )

        return sock

    def _onSslAccept(self, mesg):

        # handler for link:sock:accept
        sock = mesg[1].get('sock')

        # setup non-blocking, preread, and do_handshake
        sock.setblocking(0)
        sock.set('preread',True)

        sock.on('link:sock:preread', self._onServPreRead )

        # this fails on purpose ( but we must prompt the server to send )
        try:

            sock.do_handshake()

        except ssl.SSLError as e:

            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return

            sock.fini()

        except Exception as e:

            logger.exception(e)
            sock.fini()

    def _onServPreRead(self, mesg):
        # gotta be pretty careful on these....

        sock = mesg[1].get('sock')
        try:
            sock.do_handshake()

            # handshake completed! no more pre-read!
            sock.set('preread',False)

            user = self._getCommonName(sock)
            if user != None:
                sock.set('syn:user',user)

        except ssl.SSLError as e:

            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return

            sock.fini()

        except Exception as e:

            sock.fini()

    def _getCommonName(self, sock):

        cert = sock.getpeercert()
        if not cert:
            return None

        subj = cert.get('subject')
        if subj == None:
            return None

        try:

            info = dict( x[0] for x in subj )
            return info.get('commonName')

        except Exception as e:
            return None

    def _connect(self):
        sock = socket.socket()

        host = self.link[1].get('host')
        port = self.link[1].get('port')

        cafile = None
        keyfile = None
        certfile = None

        user = self.link[1].get('user')
        certdir = self.link[1].get('certdir')

        cdir = s_certdir.CertDir(path=certdir)
        certuser = cdir.getUserForHost(user,host)

        if certuser != None:
            cafile = cdir.getUserCaPath(certuser)
            keyfile = cdir.getUserKeyPath(certuser)
            certfile = cdir.getUserCertPath(certuser)

        cafile = self.link[1].get('cafile',cafile)
        keyfile = self.link[1].get('keyfile',keyfile)
        certfile = self.link[1].get('certfile',certfile)

        sslopts = dict(ca_certs=cafile,
                       keyfile=keyfile,
                       certfile=certfile,
                       cert_reqs=ssl.CERT_REQUIRED,
                       ssl_version=ssl.PROTOCOL_TLSv1)

        if self.link[1].get('nocheck'):
            sslopts['cert_reqs'] = ssl.CERT_NONE

        try:
            sock.connect( (host,port) )
        except s_compat.sockerrs as e:
            sock.close()
            raiseSockError(self.link,e)

        try:
            wrap = ssl.wrap_socket(sock, **sslopts)
        except ssl.SSLError as e:
            sock.close()
            raise LinkErr(self.link,str(e))

        return s_socket.Socket(wrap)
