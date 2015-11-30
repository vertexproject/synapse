import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.impulse as s_impulse
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

from synapse.tests.common import *

class ImpulseTest(SynTest):

    def test_impulse_relay(self):

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/pulser')

        puls = s_impulse.PulseRelay()
        dmon.share('pulser', puls)

        prox0 = s_telepath.openlink(link)
        prox1 = s_telepath.openlink(link)

        wait = self.getTestWait(prox0, 1, 'hehe')

        sid0 = prox0.join('foo','bar','baz')

        self.assertTrue( prox1.relay(sid0, tufo('hehe',haha='haha') ) )

        wait.wait()

        prox0.fini()
        prox1.fini()

        dmon.fini()

    def test_impulse_mcast(self):

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/pulser')

        puls = s_impulse.PulseRelay()
        dmon.share('pulser', puls)

        prox = s_telepath.openlink(link)
        wait = self.getTestWait(prox, 1, 'hehe')

        prox.join('foo','bar','baz')

        prox.mcast('foo','hehe',haha='haha')

        wait.wait()

        prox.fini()
        dmon.fini()

    def test_impulse_bcast(self):

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/pulser')

        puls = s_impulse.PulseRelay()
        dmon.share('pulser', puls)

        prox = s_telepath.openlink(link)
        wait = self.getTestWait(prox, 1, 'hehe')

        prox.join('foo','bar','baz')

        prox.bcast('hehe',haha='haha')

        wait.wait()

        prox.fini()
        dmon.fini()

