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

        with s_daemon.Daemon() as dmon:

            sbus = s_service.SvcBus()
            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_telepath.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                woot = Woot()

                s_service.runSynSvc('syn.woot', woot, prox)

                svcs = prox.getSynSvcs()

                self.eq(len(svcs), 1)
                self.eq(svcs[0][1].get('name'), 'syn.woot')

                dyntask = s_async.newtask('foo', 10, y=30)

                job = prox.callx(svcs[0][0], dyntask)
                self.eq(prox.syncjob(job), 40)

    def test_service_proxy(self):

        with s_daemon.Daemon() as dmon:

            sbus = s_service.SvcBus()
            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_telepath.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                woot0 = Woot()
                woot1 = Woot()

                s_service.runSynSvc('woots.woot0', woot0, prox)
                s_service.runSynSvc('woots.woot1', woot1, prox, tags=('foo.bar',))

                svcp = s_service.SvcProxy(prox)

                foos = svcp.getTagProxy('foo')
                woots = svcp.getTagProxy('woots')

                vals = tuple(sorted(foos.foo(20, y=20)))
                self.eq(vals, (40,))

                vals = tuple(sorted(woots.foo(10, y=20)))
                self.eq(vals, (30, 30))

                def runNewpMeth():
                    for foo in woots.newp(44, y=33):
                        pass

                self.eq(2, len(svcp.getSynSvcs()))
                self.eq(2, len(svcp.getSynSvcsByTag('woots')))

                woots = svcp.getTagProxy('class.synapse.tests.test_service.Woot')

                vals = tuple(sorted(woots.foo(10, y=20)))
                self.eq(vals, (30, 30))

    def test_service_proxysugar(self):

        woot = Woot()

        with s_daemon.Daemon() as dmon:

            sbus = s_service.SvcBus()

            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                iden = prox.runSynSvc('foo0', woot, tags=('hehe.haha',))

                res = list(prox['foo0'].foo(90))

                self.eq(len(res), 1)
                self.eq(res[0], 100)

    def test_service_byname(self):
        sbus = s_service.SvcBus()

        woot0 = Woot()

        with s_daemon.Daemon() as dmon:

            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                iden = prox.runSynSvc('foo0', woot0)

                self.eq(prox.callByName('foo0', gentask('foo', 20)), 30)

    def test_service_getNameProxy(self):

        woot0 = Woot()

        with s_daemon.Daemon() as dmon:

            sbus = s_service.SvcBus()
            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                prox.runSynSvc('foo0', woot0)

                nameprox = prox.getNameProxy('foo0')
                self.eq(nameprox.foo(20), 30)

    def test_service_getTagProxy(self):

        woot0 = Woot()

        with s_daemon.Daemon() as dmon:

            sbus = s_service.SvcBus()
            dmon.share('syn.svcbus', sbus, fini=True)

            link = dmon.listen('tcp://127.0.0.1:0/')

            port = link[1].get('port')

            with s_service.openurl('tcp://127.0.0.1/syn.svcbus', port=port) as prox:

                prox.runSynSvc('foo0', woot0, tags=['bar0'])

                tagprox = prox.getTagProxy('bar0')
                self.eq(next(tagprox.foo(20), None), 30)

    def test_service_dmon_conf(self):

        conf0 = {
            'ctors': [
                ['svcbus', 'ctor://synapse.lib.service.SvcBus()', {}],
            ],
            'share': [
                ['svcbus', {}],
            ],

        }

        with s_daemon.Daemon() as dmon0:

            dmon0.loadDmonConf(conf0)
            link = dmon0.listen('tcp://127.0.0.1:0/')
            port = link[1].get('port')

            conf1 = {

                'ctors': [
                    ['svcbus', 'tcp://127.0.0.1:%d/svcbus' % port, {}],
                    ['ebus', 'ctor://synapse.eventbus.EventBus()', {}],
                ],

                'services': [
                    ['svcbus', [
                        ['ebus', {'woot': 'heh'}],
                    ]],
                ],
            }

            with s_daemon.Daemon() as dmon1:

                dmon1.loadDmonConf(conf1)

                proxy = s_telepath.openurl('tcp://127.0.0.1/svcbus', port=port)
                dmon1.onfini(proxy.fini)

                svcfo = proxy.getSynSvcsByTag('ebus')[0]
                self.eq(svcfo[1].get('woot'), 'heh')
