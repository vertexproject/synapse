import time
import unittest
import threading

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.hivemind as s_hivemind
import synapse.mindmeld as s_mindmeld
import synapse.telepath as s_telepath

class FakeErr(Exception):pass

def borked():
    raise FakeErr()

def doit(x):
    return x + 20

def zzzz(x):
    time.sleep(x)
    return x

derpsrc = '''
def hurrdurr(x,y=20):
    return x + y
'''

derpmeld = s_mindmeld.MindMeld()
derpmeld.addPySource('derpderp',derpsrc)

class HiveTest(unittest.TestCase):

    def test_hive_borked(self):
        try:
            task = s_async.newtask(borked)
            s_hivemind.worker(task)

            raise Exception('dont do like that')

        except s_async.JobErr as e:
            self.assertEqual( e._job_err, 'FakeErr' )

    def test_hive_worker(self):
        task = s_async.newtask(doit,30)
        self.assertEqual( s_hivemind.worker(task, timeout=0.2), 50 )

    def test_hive_timeout(self):
        task = s_async.newtask(zzzz,2)
        self.assertRaises( s_async.JobTimedOut, s_hivemind.worker, task, timeout=0.1)

    def getUnitHive(self, melds=None):
        dmon,link = self.getTeleServ()
        queen = s_hivemind.Queen(dmon)

        dmon.addSharedObject('queen',queen)

        port = link[1].get('port')

        link = s_link.chopLinkUrl('tcp://127.0.0.1:%d/queen' % (port,))
        qproxy = s_telepath.Proxy(link)

        drone = s_hivemind.Drone(link, melds=melds)
        worker = s_hivemind.Worker(qproxy, size=1)

        return dmon,queen,drone,worker

    def test_hive_queen(self):
        dmon,queen,drone,worker = self.getUnitHive()

        data = {}
        evt = threading.Event()
        def onfini(job):
            data['job'] = job
            evt.set()

        jid = s_async.jobid()
        dyntask = s_async.newtask('synapse.tests.test_hivemind.doit', 30)

        drone.initAsyncJob(jid, dyntask=dyntask, onfini=onfini)

        evt.wait(timeout=2)

        job = data.get('job')
        self.assertIsNotNone(job)
        self.assertEqual(job[0], jid)

        drone.fini()
        worker.fini()
        queen.fini()
        dmon.fini()

    def test_hive_melds(self):
        melds = [ derpmeld, ]
        dmon,queen,drone,worker = self.getUnitHive(melds=melds)

        jid = s_async.jobid()
        dyntask = s_async.newtask('derpderp.hurrdurr', 10, y=70)

        data = {}
        evt = threading.Event()

        def onfini(job):
            data['job'] = job
            evt.set()

        drone.initAsyncJob(jid, dyntask=dyntask, onfini=onfini)

        evt.wait(timeout=1)

        job = data.get('job')

        self.assertEqual( job[0], jid )
        self.assertEqual( s_async.jobret(job), 80 )

        drone.fini()
        worker.fini()
        queen.fini()
        dmon.fini()

    def getTeleServ(self):
        link = s_link.chopLinkUrl('tcp://127.0.0.1:0/')

        daemon = s_daemon.Daemon()
        daemon.runLinkServer(link)

        return daemon,link
