import weakref
import collections

import synapse.lib.sched as s_sched
import synapse.lib.queue as s_queue
import synapse.session as s_session

from synapse.common import *
from synapse.eventbus import EventBus

class PulseRelay(EventBus):
    '''
    An PulseRelay supports session based event distribution.
    '''
    def __init__(self):
        EventBus.__init__(self)
        self.bysid = weakref.WeakValueDictionary()
        self.byname = collections.defaultdict(weakref.WeakSet)

    def relay(self, dest, mesg):
        '''
        Relay a tufo mesg to the given session.

        Example:

            mesg = tufo('woot',foo='bar')
            puls.relay(sid, mesg)

        '''
        # FIXME sess perms ( app fwall )
        sess = s_session.current()

        mesg[1]['imp:from'] = sess.sid

        targ = self.bysid.get(dest)
        if targ == None:
            return False

        targ.relay( tufo('imp:dist', mesg=mesg) )
        return True

    def join(self, *names):
        '''
        Join the current session to a list of named multicast groups.

        Example:

            # join the "foo" and the "bar" multicast groups
            puls.join('foo','bar')

        Notes:

            * Use mcast() to fire an event to a named dist list.

        '''
        sess = s_session.current()

        self.bysid[sess.sid] = sess

        for name in names:
            self.byname[name].add( sess )

        def onfini():
            self.bysid.pop( sess.sid, None )
            for name in names:
                nameset = self.byname[name]
                nameset.discard( sess )
                if not nameset:
                    self.byname.pop(name,None)

        sess.onfini(onfini)
        return sess.sid

    def mcast(self, name, evt, **evtinfo):
        '''
        Fire an event to a named multicast group.

        Example:

            pr.mcast('woot', 'foo', bar=10)

        Notes:

            * Event is sent to any sess which join()'d the group
        '''
        sess = s_session.current()
        if sess == None:
            raise NoCurrSess()

        # FIXME session auth/allow?

        evtinfo['imp:cast'] = name
        evtinfo['imp:from'] = sess.sid

        mesg = (evt,evtinfo)
        event = tufo('imp:dist',mesg=mesg)
        [ sess.relay(event) for sess in self.byname.get(name,()) ]

    def bcast(self, evt, **evtinfo):
        '''
        Fire an event to *all* channels.

        Example:

            pr.bcast('foo',bar=10)

        '''
        sess = s_session.current()
        if sess == None:
            raise NoCurrSess()

        # FIXME session auth/allow?

        evtinfo['imp:from'] = sess.sid
        #evtinfo['imp:bcast'] = True

        mesg = (evt,evtinfo)
        event = tufo('imp:dist', mesg=mesg)

        [ sess.relay(event) for sess in self.bysid.values() ]
