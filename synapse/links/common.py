import time
import threading

import synapse.crypto as s_crypto
import synapse.threads as s_threads

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

        sock['relay'] = self

        sock['link'] = self.link

        timeout = self.link[1].get('timeout')
        if timeout != None:
            sock.settimeout(timeout)

        # must remain first!
        zerosig = self.link[1].get('zerosig')
        if zerosig != None:
            xform = s_crypto.Rc4Xform(b'')
            sock.addSockXform(xform)

        if sock.get('listen'):
            return

        rc4key = self.link[1].get('rc4key')
        if rc4key != None:
            xform = s_crypto.Rc4Xform(rc4key)
            sock.addSockXform(xform)

        sock['trans'] = self.link[1].get('trans')

        #FIXME support DH KEX

    def listen(self):
        '''
        Create and return a new server Socket()
        '''
        sock = self._listen()

        sock['listen'] = True
        self._prepLinkSock(sock)

        return sock

    def connect(self):
        '''
        Create, connect, and return a new client Socket()
        '''
        sock = self._connect()

        sock['connect'] = True
        self._prepLinkSock(sock)

        return sock

