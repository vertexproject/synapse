import unittest
from unittest.mock import MagicMock
import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.common as s_common
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
                core = s_cortex.openurl('ram:///')
                core.setConfOpt('axon:url', axonurl)
                dmon.share('core', core, fini=True)
                proxy.runSynSvc('core', core, link=coreurl)

                jobs = Jobs('ram://', sbusurl)
                proxy.runSynSvc('dendrite-jobs', jobs)
                coordinator = Coordinator(svcbus=sbusurl, core='core', axon='axon', jobs='dendrite-jobs')
                yield (core, coordinator)
                coordinator.fini()
                dmon.fini()

    def test_register(self):
        with self.setup() as (cortex, coordinator):
            mimeType = 'text/plain'
            coordinator.register(mimeType, 'somequeue')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])

            coordinator.register(mimeType, 'queuetoo')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

            coordinator.register(mimeType, 'somequeue')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

    def test_unregister(self):
        with self.setup() as (cortex, coordinator):
            mimeType = 'text/plain'
            coordinator.register(mimeType, 'somequeue')
            coordinator.register(mimeType, 'queuetoo')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

            coordinator.unregister(mimeType, 'queuetoo')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])

    def test_process_existing(self):
        with self.setup() as (cortex, coordinator):
            timeBefore = s_common.now()
            origMethod = coordinator._processTufo
            coordinator._processTufo = MagicMock()
            coordinator._processExistingTufos()
            coordinator._processTufo.assert_not_called()
            coordinator._processTufo = origMethod
            coordinator.existingProcessorThread.join() # typically done via fini, but cleaning up explicitly for test

            cortex.formNodeByBytes(b'some bytes')
            cortex.formNodeByBytes(b'some more bytes')

            time.sleep(0.5) # give the callbacks some time to get called from creating nodes above
            coordinator._updateState(timeBefore)
            coordinator._processTufo = MagicMock()
            coordinator._processExistingTufos()
            time.sleep(0.5) # allow the processing thread to do its thing
            self.assertEqual(coordinator._processTufo.call_count, 2)
