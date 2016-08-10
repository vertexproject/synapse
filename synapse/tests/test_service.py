import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.service as s_service

from synapse.tests.common import *

class Woot:
    def foo(self, x, y=10):
        return x + y

class Blah(Woot):pass

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
        self.assertEqual( svcs[0][1].get('name'), 'syn.woot' )

        dyntask = s_async.newtask('foo',10,y=30)

        job = prox.callx(svcs[0][0], dyntask)
        self.assertEqual( prox.syncjob(job), 40 )

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

        self.assertEqual( 2, len(svcp.getSynSvcs()) )
        self.assertEqual( 2, len(svcp.getSynSvcsByTag('woots')) )

        #self.assertRaises( JobErr, runNewpMeth )

        woots = svcp.getTagProxy('class.synapse.tests.test_service.Woot')

        vals = tuple( sorted( woots.foo(10,y=20) ) )
        self.assertEqual( vals, (30,30) )

        prox.fini()
        dmon.fini()
        sbus.fini()

    def test_service_getclsnames(self):
        b = Blah()
        names = tuple( sorted( s_service.getClsNames(b) ) )
        self.assertEqual( names, ('synapse.tests.test_service.Blah','synapse.tests.test_service.Woot') )

    def test_service_proxysugar(self):
        sbus = s_service.SvcBus()

        woot0 = Woot()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus, fini=True)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        iden = prox.runSynSvc('foo0', woot0, tags=('hehe.haha',))

        res = list( prox['foo0'].foo(90) )

        self.assertEqual( len(res), 1 )
        self.assertEqual( res[0], 100 )

        dmon.fini()

    def test_service_byname(self):
        sbus = s_service.SvcBus()

        woot0 = Woot()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus, fini=True)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        iden = prox.runSynSvc('foo0', woot0)

        self.assertEqual( prox.callByName('foo0', gentask('foo',20)), 30 )

        dmon.fini()

    def test_service_getNameProxy(self):
        sbus = s_service.SvcBus()

        woot0 = Woot()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus, fini=True)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        prox.runSynSvc('foo0', woot0)

        nameprox = prox.getNameProxy('foo0')
        self.assertEqual(nameprox.foo(20), 30)

        dmon.fini()

    def test_service_getTagProxy(self):
        sbus = s_service.SvcBus()

        woot0 = Woot()

        dmon = s_daemon.Daemon()
        dmon.share('syn.svcbus', sbus, fini=True)

        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')

        prox = s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port)

        prox.runSynSvc('foo0', woot0, tags=['bar0'])

        tagprox = prox.getTagProxy('bar0')
        self.assertEqual(next(tagprox.foo(20), None), 30)

        dmon.fini()
