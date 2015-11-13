import collections

import synapse.sched as s_sched
import synapse.queue as s_queue

from synapse.eventbus import EventBus

class PulseRelay(EventBus):
    '''
    An PulseRelay supports channelized event distribution using async queues.

    Specify abtime to modify the default "abandoned" time for queues.
    '''
    def __init__(self, abtime=60):
        EventBus.__init__(self)
        self.bychan = {}
        self.abtime = abtime
        self.byname = collections.defaultdict(set)

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
            self.sched.insec( 10, self._reapDeadQueues )

    def _getChanQueue(self, chan):
        q = self.bychan.get(chan)
        if q == None:
            q = s_queue.BulkQueue()
            def qfini():
                self.bychan.pop(chan,None)
                self.fire('imp:relay:chan:fini', chan=chan)

            q.onfini( qfini )
            self.bychan[chan] = q
            self.fire('imp:relay:chan:init', chan=chan)
        return q

    def openchan(self, chan):
        '''
        Ensure that a new chan is active.
        '''
        q = self._getChanQueue(chan)

    def poll(self, chan, timeout=2):
        '''
        Retrieve the next list of events for the given channel.

        Example:

            for event in dist.poll(chan):
                dostuff(event)

        '''
        q = self._getChanQueue(chan)
        return q.get(timeout=timeout)

    def relay(self, chan, event):
        '''
        Relay an event to the given channel.

        Example:

            dist.relay(chan, 'fooevent', bar=10 )

        '''
        q = self.bychan.get(chan)
        if q != None:
            q.put(event)
            return True
        return False

    def join(self, chan, *names):
        '''
        Join the given channel to a list of named multicast groups.

        Example:

            # join the "foo" and the "bar" multicast groups
            pr.join(chanid, 'foo', 'bar')

        Notes:

            * Use mcast() to fire an event to a named dist list.

        '''
        # possibly initialize the chan
        q = self._getChanQueue(chan)

        def onfini():
            for name in names:
                self.byname[name].discard(q)

        for name in names:
            self.byname[name].add(q)

        q.onfini(onfini)

    def mcast(self, name, evt, **evtinfo):
        '''
        Fire an event to a named multicast group.

        Example:

            pr.mcast('woot', 'foo', bar=10)

        Notes:

            * Event is sent to any chan which join()'d the group
        '''
        event = (evt,evtinfo)
        [ q.put(event) for q in self.byname.get(name,()) ]

    def bcast(self, evt, **evtinfo):
        '''
        Fire an event to *all* channels.

        Example:

            pr.bcast('foo',bar=10)

        '''
        event = (evt,evtinfo)
        [ q.put(event) for q in self.bychan.values() ]

    def shut(self, chan):
        '''
        Inform the PulseRelay that a channel will no longer be polled.
        '''
        q = self.bychan.get(chan)
        if q != None:
            q.fini()

# FIXME: WORK IN PROGRESS...
class PulseArchive(EventBus):
    '''
    A PulseArchive is a durable/restartable event stream.

    It facilitates session oriented "resumable" events
    via providing (off,event) tuples.
    '''
    def __init__(self, core, fd):
        EventBus.__init__(self)
        self.link( self._saveBusEvent )

        fd.seek(0, os.SEEK_END)

        self.size = fd.tell()
        self.lock = threading.Lock()

        self.core = core
        self.cura = s_session.Curator(core)

        self.synfd = SynFile(fd)

    def open(self, off):
        sess = self.cura.getNewSess()

        with self.lock:
            sess.local['queue'] = s_queue.BulkQueue()
            if off == self.size:
                return

            self.fd.seek(off)
            sess.local['off'] = off

        return sess.sid

    def next(self, sid):
        '''
        '''
        sess = self.cura.getSessBySid(sid)
        if sess == None:
            raise NoSuchSess(sess)

        #q = sess.local.get('queue')
        #if q == None:

        off = sess.local.get('off')

        if off == None:
            return q.get(timeout=8)

    #def _loadQueChunk(self, q, off):

    def _savePulse(self, event):
        byts = msgenpack(event)
        with self.lock:
            self.fd.write(byts)
            self.size += len(byts)

            item = (self.size,event)

            for sess in self.cura:
                if sess.local.get('off') != None:
                    continue

                q = sess.local.get('queue')
                if q == None:
                    continue

                q.put( item )
