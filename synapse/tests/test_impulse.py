import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.impulse as s_impulse
import synapse.eventbus as s_eventbus

from synapse.common import *

class ImpulseTest(unittest.TestCase):

    def getUnitDmon(self):
        dmon = s_daemon.Daemon()
        link = s_link.chopLinkUrl('tcp://127.0.0.1:0/')

        dmon = s_daemon.Daemon()
        dmon.runLinkServer(link)

        return dmon,link

    def test_impulse_pulser(self):

        dmon,link = self.getUnitDmon()

        data = {}
        chan = 'woot'

        evt1 = threading.Event()
        evt2 = threading.Event()

        def hehe1(e):
            data['hehe1'] = e[1].get('valu')
            evt1.set()

        def hehe2(e):
            data['hehe2'] = e[1].get('valu')
            evt2.set()

        imp1 = s_impulse.Pulser(link,chan)
        imp2 = s_impulse.Pulser(link,chan)

        imp1.on('he:he', hehe1)
        imp2.on('he:he', hehe2)

        imp1.fire('he:he', valu=10)

        evt1.wait(timeout=1)
        evt2.wait(timeout=1)

        self.assertTrue( evt1.is_set() )
        self.assertTrue( evt2.is_set() )

        self.assertEqual( data['hehe1'], 10)
        self.assertEqual( data['hehe2'], 10)

        evt1.clear()
        evt2.clear()

        imp2.fire('he:he', valu=30)

        evt1.wait(timeout=1)
        evt2.wait(timeout=1)

        self.assertEqual( data['hehe1'], 30)
        self.assertEqual( data['hehe2'], 30)

        evt = threading.Event()
        data = {'count':0}

        def sockfini(event):
            data['count'] += 1
            if data['count'] == 2:
                evt.set()

        dmon.on('link:sock:fini', sockfini)

        imp1.fini()
        imp2.fini()

        evt.wait(timeout=1)

        self.assertTrue( evt.is_set() )
        self.assertEqual( len(dmon.impsocks), 0 )

        dmon.fini()

    def test_impulse_link(self):
        chan = 'woot'
        dmon,link = self.getUnitDmon()

        imp1 = s_impulse.Pulser(link,chan)
        imp2 = s_impulse.Pulser(link,chan)

        d = {}
        evt = threading.Event()

        def allevt(event):
            if event[0] == 'hehe':
                d['hehe'] = event
                evt.set()

        imp2.link( allevt )
        imp1.fire('hehe')

        evt.wait(timeout=1)

        self.assertTrue( evt.is_set() )
        self.assertIsNotNone( d.get('hehe') )

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

        dist.relay('bus0', 'foo', bar=10)

        evt.wait(timeout=2)
        self.assertEqual( data['event'][1].get('bar'), 10 )

        bus0.fini()
        dist.fini()

    def test_impulse_relay(self):

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

