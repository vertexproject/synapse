import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.impulse as s_impulse
import synapse.eventbus as s_eventbus

from synapse.common import *

class ImpulseTest(unittest.TestCase):

    def test_impulse_relay(self):

        dist = s_impulse.PulseRelay()

        bus0 = s_eventbus.EventBus()

        bus0.feed( dist.poll, 'bus0' )

        evt = threading.Event()
        data = {}
        def onfoo(event):
            data['event'] = event
            evt.set()

        bus0.on('foo', onfoo)

        dist.relay('bus0', tufo('foo', bar=10))

        evt.wait(timeout=2)
        self.assertEqual( data['event'][1].get('bar'), 10 )

        bus0.fini()
        dist.fini()

    def test_impulse_mcast(self):

        chan = guidstr()

        dist = s_impulse.PulseRelay()
        dist.join(chan,'woot')

        bus0 = s_eventbus.EventBus()
        bus0.feed( dist.poll, chan )
        bus0.onfini( dist.shut, chan )

        evt = threading.Event()
        data = {}
        def onfoo(event):
            data['event'] = event
            evt.set()

        bus0.on('foo', onfoo)
        dist.mcast('woot', 'foo', bar=10)

        evt.wait(timeout=2)
        self.assertEqual( data['event'][1].get('bar'), 10 )

        bus0.fini()
        dist.fini()

    def test_impulse_bcast(self):

        chan = guidstr()

        dist = s_impulse.PulseRelay()
        dist.join(chan,'woot')

        bus0 = s_eventbus.EventBus()
        bus0.feed( dist.poll, chan )

        evt = threading.Event()
        data = {}
        def onfoo(event):
            data['event'] = event
            evt.set()

        bus0.on('foo', onfoo)
        dist.bcast('foo',bar=10)

        evt.wait(timeout=3)
        self.assertEqual( data['event'][1].get('bar'), 10 )

        bus0.fini()
        dist.fini()
