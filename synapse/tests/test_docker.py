import synapse.telepath as s_telepath

from synapse.tests.common import *

class DockerTest(SynTest):

    def test_ram_core(self):
        dcker = os.getenv('SYN_DOCKER_RAM')
        if dcker == None:
            raise unittest.SkipTest('no SYN_DOCKER_RAM')

        prox = s_telepath.openurl('tcp://127.0.0.1/core', port=47320)

        job00 = prox.call('formTufoByProp', 'inet:fqdn', 'foo.com')
        job01 = prox.call('formTufoByProp', 'inet:fqdn', 'bar.com')
        tufo00 = prox.syncjob(job00)
        tufo01 = prox.syncjob(job01)

        job02 = prox.call('getTufoByProp', 'inet:fqdn', 'foo.com')
        tufo02 = prox.syncjob(job02)

        self.assertEqual(tufo00[0], tufo02[0])

        prox.fini()

    def test_sqlite_core(self):
        dcker = os.getenv('SYN_DOCKER_SQLITE')
        if dcker == None:
            raise unittest.SkipTest('no SYN_DOCKER_SQLITE')

        prox = s_telepath.openurl('tcp://127.0.0.1/core', port=47321)

        job00 = prox.call('formTufoByProp', 'inet:fqdn', 'foo.com')
        job01 = prox.call('formTufoByProp', 'inet:fqdn', 'bar.com')
        tufo00 = prox.syncjob(job00)
        tufo01 = prox.syncjob(job01)

        job02 = prox.call('getTufoByProp', 'inet:fqdn', 'foo.com')
        tufo02 = prox.syncjob(job02)

        self.assertEqual(tufo00[0], tufo02[0])

        prox.fini()

    def test_pg_core(self):
        dcker = os.getenv('SYN_DOCKER_PG')
        if dcker == None:
            raise unittest.SkipTest('no SYN_DOCKER_PG')

        prox = s_telepath.openurl('tcp://127.0.0.1/core', port=47322)

        job00 = prox.call('formTufoByProp', 'inet:fqdn', 'foo.com')
        job01 = prox.call('formTufoByProp', 'inet:fqdn', 'bar.com')
        tufo00 = prox.syncjob(job00)
        tufo01 = prox.syncjob(job01)

        job02 = prox.call('getTufoByProp', 'inet:fqdn', 'foo.com')
        tufo02 = prox.syncjob(job02)

        self.assertEqual(tufo00[0], tufo02[0])

        prox.fini()

