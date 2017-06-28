
import os
import sys

from synapse.docker import getSyncCore
import synapse.telepath as s_telepath

from synapse.tests.common import *

class DockerTest(SynTest):

    def test_getSyncCore(self):
        SYN_UPSTREAM_CORE = os.getenv('SYN_UPSTREAM_CORE', '')
        try:
            os.environ['SYN_UPSTREAM_CORE'] = 'ram:///'
            with getSyncCore() as core:
                tufo = core.formTufoByProp('test', '1', **{})
                self.eq(tufo[1]['tufo:form'], 'test')
        finally:
            os.environ['SYN_UPSTREAM_CORE'] = SYN_UPSTREAM_CORE

    def test_mapped_core(self):
        dcker = os.getenv('SYN_DOCKER')
        if dcker == None:
            raise unittest.SkipTest('no SYN_DOCKER')
        if sys.version_info < (3, 4):
            raise unittest.SkipTest('not python 3')

        prox = s_telepath.openurl('tcp://127.0.0.1/core', port=47322)

        job00 = prox.call('formTufoByProp', 'inet:fqdn', 'foo.com')
        job01 = prox.call('formTufoByProp', 'inet:fqdn', 'bar.com')
        tufo00 = prox.syncjob(job00)
        tufo01 = prox.syncjob(job01)

        job02 = prox.call('getTufoByProp', 'inet:fqdn', 'foo.com')
        tufo02 = prox.syncjob(job02)

        self.eq(tufo00[0], tufo02[0])

        prox.fini()
