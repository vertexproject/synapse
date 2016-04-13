import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
import synapse.lib.service as s_service
import synapse.swarm.runtime as s_runtime

from synapse.tests.common import *


class SwarmRunTest(SynTest):

    def getSwarmEnv(self):
        tenv = TestEnv()

        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        tenv.add('core0',core0,fini=True)
        tenv.add('core1',core1,fini=True)

        tufo0 = core0.formTufoByProp('foo:bar','baz',vvv='visi')
        tufo1 = core0.formTufoByProp('foo:bar','faz',vvv='visi')
        tufo2 = core1.formTufoByProp('foo:bar','lol',vvv='visi')
        tufo3 = core1.formTufoByProp('foo:bar','hai',vvv='visi')

        tenv.add('tufo0',tufo0)
        tenv.add('tufo1',tufo1)
        tenv.add('tufo2',tufo2)
        tenv.add('tufo3',tufo3)

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0')

        tenv.add('link',link)
        tenv.add('dmon',dmon,fini=True)

        port = link[1].get('port')

        svcbus = s_service.SvcBus()
        tenv.add('svcbus',svcbus,fini=True)

        dmon.share('syn.svcbus',svcbus)

        svcrmi = s_telepath.openurl('tcp://127.0.0.1/syn.svcbus', port=port)
        tenv.add('svcrmi',svcrmi,fini=True)

        s_service.runSynSvc('cortex',core0,svcrmi,tags=('hehe.haha',))
        s_service.runSynSvc('cortex',core1,svcrmi,tags=('hehe.hoho',))

        runt = s_runtime.Runtime(svcrmi)

        tenv.add('runt',runt,fini=True)

        return tenv

    def test_swearm_runtime_lift(self):
        tenv = self.getSwarmEnv()

        answ = tenv.runt.ask('foo:bar="baz"')
        data = answ.get('data')

        self.assertEqual( data[0][0], tenv.tufo0[0] )
        #print(answ)

        # FIXME check for other expected results info!

        answ = tenv.runt.ask('foo:bar:vvv')
        data = answ.get('data')

        self.assertEqual( len(data), 4 )

        tenv.fini()

    def test_swearm_runtime_pivot(self):
        tenv = self.getSwarmEnv()

        answ = tenv.runt.ask('foo:bar="baz" ^foo:bar:vvv')
        data = answ.get('data')

        self.assertEqual( len(data), 4 )

        answ = tenv.runt.ask('foo:bar="baz" ^foo:bar:vvv=foo:bar:vvv')
        data = answ.get('data')

        self.assertEqual( len(data), 4 )

        tenv.fini()

    def test_swearm_runtime_opts(self):
        tenv = self.getSwarmEnv()

        answ = tenv.runt.ask('%foo')
        self.assertEqual( answ['options'].get('foo'), 1 )

        answ = tenv.runt.ask('opts(foo=10)')
        self.assertEqual( answ['options'].get('foo'), 10 )

        answ = tenv.runt.ask('%foo=10')
        self.assertEqual( answ['options'].get('foo'), 10 )

        answ = tenv.runt.ask('opts(foo="bar")')
        self.assertEqual( answ['options'].get('foo'), 'bar' )

        answ = tenv.runt.ask('%foo="bar"')
        self.assertEqual( answ['options'].get('foo'), 'bar' )

        tenv.fini()
