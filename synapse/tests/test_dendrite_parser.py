import unittest
import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
from synapse.tests.common import *
from synapse.dendrite.jobs import Jobs
import synapse.lib.service as s_service
from synapse.dendrite.coordinator import Coordinator
from synapse.dendrite.parser import Parser

class DendriteParserTest(SynTest):

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
                coordinator = Coordinator(svcbus=sbusurl, core='core', axon='axon', jobs='dendrite-jobs')
                proxy.runSynSvc('dendrite-coordinator', coordinator)
                opts = {'svcbus': sbusurl, 'coordinator': 'dendrite-coordinator', 'jobs': 'dendrite-jobs'}
                yield (opts, coordinator, jobs)
                dmon.fini()

    def test_register(self):
        with self.setup() as (opts, coordinator, jobs):
            parser = Parser(**opts)
            mimeType = 'text/plain'
            parser.register(mimeType, 'somequeue')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])

            parser.register(mimeType, 'queuetoo')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

            parser.register(mimeType, 'somequeue')
            self.assertEqual(sorted(coordinator.queues(mimeType)), sorted(['somequeue', 'queuetoo']))

    def test_unregister(self):
        with self.setup() as (opts, coordinator, jobs):
            parser = Parser(**opts)
            mimeType = 'text/plain'
            parser.register(mimeType, 'somequeue')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])

            parser.unregister(mimeType, 'queuetoo')
            self.assertEqual(coordinator.queues(mimeType), ['somequeue'])
            parser.unregister(mimeType, 'somequeue')
            self.assertEqual(coordinator.queues(mimeType), [])

    class SomeParser(Parser):
        def __init__(self, **kwargs):
            Parser.__init__(self, **kwargs)
            self.results = []
        def _process(self, queue, job):
            del(job['iden'])
            self.results.append((queue, job))

    def test_process(self):
        with self.setup() as (opts, coordinator, jobs):
            parser = DendriteParserTest.SomeParser(**opts)
            mimeType = 'text/plain'
            parser.register(mimeType, 'somequeue')

            job = {'some': 'prop', 'woot': 'val'}
            jobs.put('somequeue', job)
            time.sleep(0.1) # give the EventBus thread(used by Parser) a chance to consume message
            self.assertEqual(parser.results, [('somequeue', job)])

    def test_processAll(self):
        with self.setup() as (opts, coordinator, jobs):
            jobBeforeRegister = {'still': 'need', 'this': 1}
            jobs.put('somequeue', jobBeforeRegister)

            parser = DendriteParserTest.SomeParser(**opts)
            mimeType = 'text/plain'
            parser.register(mimeType, 'somequeue')

            job = {'some': 'prop', 'woot': 'val'}
            jobs.put('somequeue', job)
            time.sleep(0.1) # give the EventBus thread(used by Parser) a chance to consume message
            self.assertEqual(parser.results, [('somequeue', jobBeforeRegister), ('somequeue', job)])
