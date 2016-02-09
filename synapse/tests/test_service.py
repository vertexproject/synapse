import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.service as s_service

from synapse.tests.common import *

class Woot:
    def foo(self, x, y=10):
        return x + y

class SvcTest(SynTest):

    def test_service_base(self):
        sbus = s_service.SvcBus()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_telepath.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        woot = Woot()

        s_service.runSynSvc('syn.woot', woot, prox)

        svcs = prox.getSynSvcs()

        self.assertEqual( len(svcs), 1 )
        self.assertEqual( svcs[0][0], 'syn.woot' )

        dyntask = s_async.newtask('foo',10,y=30)

        job = prox.callx('syn.woot', dyntask)
        self.assertEqual( prox.sync(job), 40 )

        prox.fini()
        dmon.fini()
        sbus.fini()

    def test_service_proxy(self):
        sbus = s_service.SvcBus()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_telepath.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        woot0 = Woot()
        woot1 = Woot()

        s_service.runSynSvc('woots.woot0', woot0, prox)
        s_service.runSynSvc('woots.woot1', woot1, prox, tags=('foo.bar',))

        svcp = s_service.SvcProxy(prox)

        foos = svcp.getTagProxy('foo')
        woots = svcp.getTagProxy('woots')

        vals = tuple( sorted( foos.foo(20,y=20) ) )
        self.assertEqual( vals, (40,) )

        vals = tuple( sorted( woots.foo(10,y=20) ) )
        self.assertEqual( vals, (30,30) )

        def runNewpMeth():
            for foo in woots.newp(44,y=33):
                pass

        self.assertRaises( JobErr, runNewpMeth )

        prox.fini()
        dmon.fini()
        sbus.fini()
