import time
import threading

import synapse.crypto as s_crypto
import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

class NoSuchProto(Exception):pass

class TooManyTries(Exception):pass
class ImplementMe(Exception):pass

class LinkRelay:

    proto = None

    def __init__(self, link):
        self.link = link
        self._reqValidLink()

    def _reqValidLink(self):
        pass

    def _prepLinkSock(self, sock):

        sock.set('relay', self)
        sock.set('link', self.link)

        timeout = self.link[1].get('timeout')
        if timeout != None:
            sock.settimeout(timeout)

        if sock.get('listen'):
            return

        rc4key = self.link[1].get('rc4key',b'')
        zerosig = self.link[1].get('zerosig')
        if rc4key or zerosig != None:
            xform = s_crypto.Rc4Xform(rc4key)
            sock.addSockXform(xform)

    def listen(self):
        '''
        Create and return a new server Socket()
        '''
        sock = self._listen()

        sock.set('relay',self)
        sock.set('link',self.link)

        sock.set('listen',True)
        self._prepLinkSock(sock)

        return sock

    def connect(self):
        '''
        Create, connect, and return a new client Socket()
        '''
        sock = self._connect()
        if sock == None:
            return None

        sock.set('relay',self)
        sock.set('link',self.link)

        sock.set('connect',True)
        self._prepLinkSock(sock)

        return sock

