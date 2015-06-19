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

    def initLinkFromUri(self, uri):
        link = self._initLinkFromUri(uri)
        self.reqValidLink(link)
        return link

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
        return self._initLinkSock(link)

    def _initLinkSock(self, link):
        raise ImplementMe()

    def _initLinkRelay(self, link):
        raise ImplementMe()

    def _reqValidLink(self, link):
        raise ImplementMe()

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
        self.synOn('link:sock:init', self._onLinkSockInit)

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

