import collections

import synapse.link as s_link
import synapse.sched as s_sched
import synapse.queue as s_queue
import synapse.socket as s_socket
import synapse.threads as s_threads

from synapse.eventbus import EventBus

class ImpMixin:
    '''
    The impulse subsystem allows multiple EventBus instances
    to be asynchronously linked over a synapse link.

    '''
    def __init__(self):

        self._imp_q = s_queue.BulkQueue()
        self._imp_up = None # FIXME impulse uplinks
        self._imp_thr = s_threads.worker( self._runImpLoop )

        self.impsocks = collections.defaultdict(set)    # chan:<set-of-socks>

        self.on('link:sock:fini', self._impLinkSockFini )

        self.setMesgMeth('imp:join', self._onMesgImpJoin)
        self.setMesgMeth('imp:leave', self._onMesgImpLeave)
        self.setMesgMeth('imp:pulse', self._onMesgImpPulse)

        self.onfini( self._onImpFini )

    def _onImpFini(self):
        self._imp_q.fini()
        self._imp_thr.join()

    def runImpDist(self, mesg, sock=None, up=False):
        # distribute an imp:pulse message
        chan = mesg[1].get('chan')

        if self._imp_up and not up:
            self._imp_up.dist(event)

        for s in self.impsocks.get(chan,()):
            if s == sock:
                continue

            s.sendobj(mesg)

    def _runImpLoop(self):
        for mesg,sock in self._imp_q:
            self.runImpDist(mesg, sock=sock)

    def distImpEvent(self, event, chan, sock=None):
        '''
        Explicitly distribute an event on a impulse channel.

        Example:

            event = ('woot',{'x':10})
            dmon.distImpEvent(event, chan)

        '''
        mesg = ('imp:pulse',{'chan':chan,'event':event})
        self._imp_q.put( (mesg,sock) )

    def _popSockChan(self, sock, chan):
        chans = sock.getSockInfo('impchans')
        if chans != None:
            chans.discard(chan)

        d = self.impsocks.get(chan)
        if d == None:
            return

        d.discard(sock)
        if not d:
            self.impsocks.pop(chan,None)

    def _impLinkSockFini(self, event):
        sock = event[1].get('sock')

        chans = sock.getSockInfo('impchans')
        if chans == None:
            return

        for chan in list(chans):
            self._popSockChan(sock,chan)

    def _onMesgImpJoin(self, sock, mesg):
        chan = mesg[1].get('chan')

        # get the set of channels the socket has joined
        chans = sock.getSockInfo('impchans')
        if chans == None:
            chans = set()
            sock.setSockInfo('impchans',chans)

        chans.add(chan)
        self.impsocks[chan].add( sock )
        sock.fireobj('imp:join:ack')

    def _onMesgImpLeave(self, sock, mesg):
        chan = mesg[1].get('chan')
        self._popSockChan(sock,chan)
        sock.fireobj('imp:leave:ack')

    def _onMesgImpPulse(self, sock, mesg):
        self._imp_q.put( (mesg,sock) )

class PulseRelay(EventBus):
    '''
    An PulseRelay supports channelized event distribution and async queues.

    Specify abtime to modify the default "abandoned" time for queues.
    '''
    def __init__(self, abtime=8):
        EventBus.__init__(self)
        self.bychan = {}
        self.abtime = abtime
        self.sched = s_sched.getGlobSched()

        self._reapDeadQueues()

    def _reapDeadQueues(self):
        if self.isfini:
            return

        try:
            for q in list( self.bychan.values() ):
                if q.abandoned( self.abtime ):
                    q.fini()
        finally:
            self.sched.insec( 2, self._reapDeadQueues )

    def _getChanQueue(self, chan):
        q = self.bychan.get(chan)
        if q == None:
            q = s_queue.BulkQueue()
            def qfini():
                self.bychan.pop(chan,None)

            q.onfini( qfini )
            self.bychan[chan] = q
        return q

    def poll(self, chan, timeout=2):
        '''
        Retrieve the next list of events for the given channel.

        Example:

            for event in dist.poll(chan):
                dostuff(event)

        '''
        q = self._getChanQueue(chan)
        return q.get(timeout=timeout)

    def relay(self, chan, evt, **evtinfo):
        '''
        Relay an event to the given channel.

        Example:

            dist.relay(chan, 'fooevent', bar=10 )

        '''
        q = self.bychan.get(chan)
        if q == None:
            q = s_queue.BulkQueue()
            self.bychan[chan] = q
        q.put( (evt,evtinfo) )

class Pulser(EventBus):
    '''
    A Pulser is an EventBus instance which also sends/recvs events
    from a channel on an impulse server located at the specified URL.

    Example:

        impurl = 'tcp://1.2.3.4:1337/'
        bus = Pulser(imprul, 'mychan')

        bus.fire('woot',foo=10)

    '''
    def __init__(self, link, chan):
        EventBus.__init__(self)

        self._imp_q = s_queue.BulkQueue()

        self._imp_sock = None
        self._imp_chan = chan
        self._imp_link = link
        self._imp_plex = s_socket.getGlobPlex()
        self._imp_relay = s_link.initLinkRelay(link)

        self._imp_thr = self._disImpEvents()

        self.onfini( self._onPulseFini )

        self._initImpSock()

    def _initImpSock(self):

        if self.isfini:
            return

        self._imp_sock = self._imp_relay.initClientSock()
        if self._imp_sock == None:
            return False

        self._imp_sock.setMesgMeth('imp:pulse', self._impPulseMesg )

        self._imp_sock.onfini( self._initImpSock )
        self._imp_sock.fireobj('imp:join', chan=self._imp_chan)

        joinack = self._imp_sock.recvobj()
        if joinack == None:
            return False

        if joinack[0] != 'imp:join:ack':
            # FIXME normalized synapse exception for proto stuff
            raise Exception('Invalid Protocol Response')

        self._imp_plex.addPlexSock(self._imp_sock)
        return True

    def _impPulseMesg(self, sock, mesg):
        event = mesg[1].get('event')
        self._imp_q.put( event )

    def dist(self, event):
        '''
        See EventBus.dist()
        '''
        ret = EventBus.dist(self, event)
        self._imp_sock.fireobj('imp:pulse', event=event, chan=self._imp_chan)
        return ret

    def _onPulseFini(self):
        self._imp_q.fini()
        self._imp_thr.join()
        self._imp_sock.fini()

    @s_threads.firethread
    def _disImpEvents(self):
        # skip our dist() method to prevent sending
        [ EventBus.dist(self,evt) for evt in self._imp_q ]
