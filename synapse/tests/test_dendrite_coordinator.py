import unittest
import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
from synapse.tests.common import *
from synapse.dendrite.jobs import Jobs
import synapse.lib.service as s_service
from synapse.dendrite.coordinator import Coordinator

class DendriteCoordinatorTest(SynTest):

    @contextlib.contextmanager
    def setup(self):
        dmon = s_daemon.Daemon()
        sbus = s_service.SvcBus()
        dmon.share('syn.svcbus', sbus, fini=True)
        link = dmon.listen('tcp://127.0.0.1:0/')
        port = link[1].get('port')
        sbusurl = 'tcp://127.0.0.1:%d/syn.svcbus' % port
        with s_service.openurl(sbusurl) as proxy:
            with self.getTestDir() as dir:
                axon = s_axon.Axon(dir)
                dmon.share('axon', axon, fini=True)
                axonurl = 'tcp://127.0.0.1:%d/axon' % port
                proxy.runSynSvc('axon', axon, link=axonurl)

                coreurl = 'tcp://127.0.0.1:%d/core' % port
                core = s_cortex.openurl('ram:///', **{'axon:url': axonurl})
                dmon.share('core', core, fini=True)
                proxy.runSynSvc('core', core, link=coreurl)

                jobs = Jobs('ram://', sbusurl)
                proxy.runSynSvc('dendrite-jobs', jobs)
                yield Coordinator(svcbus=sbusurl, core='core', axon='axon', jobs='dendrite-jobs')

    def test_register(self):
        with self.setup() as coordinator:
            mimeType = 'text/plain'
            coordinator.register(mimeType, 'somequeue')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])

            coordinator.register(mimeType, 'queuetoo')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

            coordinator.register(mimeType, 'somequeue')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

    def test_unregister(self):
        with self.setup() as coordinator:
            mimeType = 'text/plain'
            coordinator.register(mimeType, 'somequeue')
            coordinator.register(mimeType, 'queuetoo')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

            coordinator.unregister(mimeType, 'queuetoo')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])
