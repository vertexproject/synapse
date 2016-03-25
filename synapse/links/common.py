import time
import errno
import threading

import synapse.crypto as s_crypto
import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

from synapse.common import *

class NoSuchProto(Exception):pass

class TooManyTries(Exception):pass
class ImplementMe(Exception):pass

class LinkRelay:

    proto = None

    def __init__(self, link):
        self.link = link
        self._reqValidLink()

    def getLinkProp(self, name, defval=None):
        return self.link[1].get(name, defval)

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

    def _connloop(self):

        retry = self.link[1].get('retry',0)

        try:
            return self._connect()
        except LinkErr as e:
            if retry == 0:
                raise

        tries = 0
        while True:

            time.sleep(1)

            try:

                return self._connect()

            except LinkErr as e:

                if not e.retry:
                    raise

                tries += 1
                if tries >= retry:
                    raise

    def connect(self):
        '''
        Create, connect, and return a new client Socket()
        '''
        sock = self._connloop()

        sock.set('relay',self)
        sock.set('link',self.link)

        sock.set('connect',True)
        self._prepLinkSock(sock)

        return sock

def raiseSockError(link,e):
    url = link[1].get('url')
    if e.errno == errno.ECONNREFUSED:
        raise LinkRefused(link)

    if e.errno == errno.ENOENT:
        raise LinkRefused(link)

    raise LinkErr(link)
