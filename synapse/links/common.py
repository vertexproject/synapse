from urllib.parse import urlparse, parse_qsl

import synapse.crypto as s_crypto
import synapse.threads as s_threads

from synapse.eventbus import EventBus

class BadLinkInfo(Exception):pass
class NoLinkProp(BadLinkInfo):pass
class BadLinkProp(BadLinkInfo):pass
class NoSuchLinkProto(Exception):pass

class ImplementMe(Exception):pass

class LinkProto:

    proto = None

    def __init__(self):
        pass

    def reqValidLink(self, link):
        '''
        Check the link tuple for errors and raise.
        '''
        return self._reqValidLink(link)

    def initLinkRelay(self, link):
        '''
        Construct and return a new LinkRelay for the link.
        '''
        return self._initLinkRelay(link)

    def initLinkSock(self, link):
        '''
        Construct and return a client sock for the link.
        '''
        sock = self._initLinkSock(link)
        return _prepLinkSock(sock,link)

    def initLinkFromUri(self, uri):
        p = urlparse(uri)
        q = dict(parse_qsl(p.query))
        link = self._initLinkFromUriParsed(p,q)

        # fill in props handled by all links
        timeout = q.get('timeout')
        if timeout != None:
            link[1]['timeout'] = int(timeout,0)

        rc4key = q.get('rc4key')
        if rc4key != None:
            link[1]['rc4key'] = rc4key.encode('utf8')

        return link

    def _initLinkFromUriParsed(self, parsed, query):
        raise ImplementMe()

    def _initLinkSock(self, link):
        raise ImplementMe()

    def _initLinkRelay(self, link):
        raise ImplementMe()

    def _reqValidLink(self, link):
        raise ImplementMe()

def _prepLinkSock(sock,link):
    '''
    Used by LinkProto and LinkRelay to handle universal link options.
    '''
    rc4key = link[1].get('rc4key')
    if rc4key != None:
        prov = s_crypto.RC4Crypto(link)
        sock._setCryptoProv( prov )

    timeout = link[1].get('timeout')
    if timeout != None:
        sock.settimeout(timeout)

    #FIXME support DH KEX
    return sock

class LinkRelay(EventBus):
    '''
    A synapse LinkRelay ( link runtime ).

    Each synapse LinkRelay is capable of producing newly
    connected Socket() objects:

    Example:

        def linksock(sock):
            stuff()

        def linkmesg(sock,mesg):
            stuff()

        link = ('tcpd',{'host':'0.0.0.0','port':'0.0.0.0'})

        relay = LinkRelay(link)
        relay.synOn('link:sock:init',linksock)
        relay.runLinkRelay()

    EventBus Events:

        ('link:sock:init',{'sock':sock})
        ('link:sock:fini',{'sock':sock})
        ('link:sock:mesg',{'sock':sock, 'mesg':mesg})

    Notes:

        * Any Socket() from a link relay should have:

            sock.getSockInfo('link')
            sock.getSockInfo('relay')

    '''
    def __init__(self, link):
        EventBus.__init__(self)
        self.link = link

        # For now, these support threading...
        self.boss = s_threads.ThreadBoss()
        self.synOnFini(self.boss.synFini)

        # we get the sock first to fill in info
        self.synOn('link:sock:init', self._onLinkSockInit)

    def _prepRelaySock(self, sock):
        '''
        Used by LinkRelay implementors to handle universal link options.
        '''
        return _prepLinkSock(sock,self.link)

    def _onLinkSockInit(self, event):
        sock = event[1].get('sock')
        sock.setSockInfo('relay',self)
        sock.setSockInfo('link',self.link)

    def runLinkRelay(self):
        '''
        Run a thread to handle this LinkRelay.
        '''
        self.boss.worker( self._runLinkRelay )

    def _runLinkRelay(self):
        raise ImplementMe()

    def _runSockLoop(self, sock):

        # apply universal link properties
        sock = self._prepRelaySock(sock)

        self.synOnFini(sock.close,weak=True)
        self.synFire('link:sock:init',sock=sock)

        for mesg in sock:
            self.synFire('link:sock:mesg',sock=sock,mesg=mesg)

        self.synFire('link:sock:fini',sock=sock)

