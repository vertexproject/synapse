import time
import errno

import synapse.common as s_common

class NoSuchProto(Exception): pass

class TooManyTries(Exception): pass
class ImplementMe(Exception): pass

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
        if timeout is not None:
            sock.settimeout(timeout)

        if sock.get('listen'):
            return

    def listen(self):
        '''
        Create and return a new server Socket()
        '''
        sock = self._listen()

        sock.set('relay', self)
        sock.set('link', self.link)

        sock.set('listen', True)
        self._prepLinkSock(sock)

        return sock

    def _connloop(self):

        retry = self.link[1].get('retry', 0)

        try:
            return self._connect()
        except s_common.LinkErr as e:
            if retry == 0:
                raise

        tries = 0
        while True:

            time.sleep(1)

            try:

                return self._connect()

            except s_common.LinkErr as e:

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

        sock.set('relay', self)
        sock.set('link', self.link)

        sock.set('connect', True)
        self._prepLinkSock(sock)

        return sock

def raiseSockError(link, e):
    url = link[1].get('url')
    if e.errno == errno.ECONNREFUSED:
        raise s_common.LinkRefused(link)

    if e.errno == errno.ENOENT:
        raise s_common.LinkRefused(link)

    raise s_common.LinkErr(link)
