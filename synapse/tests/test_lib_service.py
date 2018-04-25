import synapse.lib.service as s_service

from synapse.tests.common import *

class TestService(s_service.Service):

    confdefs = (
        ('foo', {'type': 'int', 'defval': 20}),
    )

    def postSvcInit(self):
        self.lulz = 'woot'

class SvcTest(SynTest):

    def test_service_base(self):

        with self.getTestDir() as dirn:

            with TestService(dirn, {}) as tsvc:

                sdir = tsvc.getSvcDir('lol')
                self.true(os.path.isdir(sdir))

                path = tsvc.getSvcPath('lol')
                self.eq(path, sdir)

                self.eq(tsvc.lulz, 'woot')
                self.eq(tsvc.getConfOpt('foo'), 20)
