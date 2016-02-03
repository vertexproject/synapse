import time
import unittest
import threading

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.hivemind as s_hivemind
import synapse.mindmeld as s_mindmeld
import synapse.telepath as s_telepath

from synapse.tests.common import *

def doit(x):
    return x + 20

derpsrc = '''
def hurrdurr(x,y=20):
    return x + y
'''

class HiveTest(SynTest):

    def getHiveEnv(self):

        #FIXME remove when synapse link local:// supports windows
        self.thisHostMustNot(platform='windows')

        dmon = s_daemon.Daemon()
        queen = s_hivemind.Queen()

        dmon.share('syn.queen', queen)
        link = dmon.listen('tcp://127.0.0.1:0/')

        port = link[1].get('port')
        qprox = s_telepath.openurl('tcp://127.0.0.1/syn.queen', port=port)

        hive = s_hivemind.Hive(qprox, size=32)
        drone = s_hivemind.Drone(qprox, size=2)

        env = TestEnv()

        # order matters for fini calls...
        env.add('hive', hive, fini=True)
        env.add('drone', drone, fini=True)

        env.add('qprox', qprox, fini=True)
        env.add('queen', queen, fini=True)

        env.add('dmon', dmon, fini=True)

        return env

    def test_hivemind_basic(self):
        env = self.getHiveEnv()
        waiter = self.getTestWait(env.drone,1,'hive:slot:fini')

        data = {}
        def ondone(job):
            data['ret'] = s_async.jobret(job)

        dyntask = ('synapse.tests.test_hivemind.doit', (20,), {})

        env.hive.task(dyntask, ondone=ondone)

        waiter.wait()

        self.assertEqual( data.get('ret'), 40 )

        env.fini()

    def test_hivemind_meld(self):
        env = self.getHiveEnv()
        waiter = self.getTestWait(env.drone,1,'hive:slot:fini')

        data = {}
        def ondone(job):
            data['ret'] = s_async.jobret(job)

        dyntask = ('derpderp.hurrdurr', (20,), {'y':30})

        meld = env.hive.genHiveMeld()
        meld.addPySource('derpderp',derpsrc)

        env.hive.task(dyntask, ondone=ondone)

        waiter.wait()

        self.assertEqual( data.get('ret'), 50 )

        env.fini()

    def test_hivemind_queen(self):
        env = self.getHiveEnv()

        hives = env.qprox.getHives()
        drones = env.qprox.getDrones()

        self.assertEqual( len(hives), 1 )
        self.assertEqual( len(drones), 1 )

        hslots = env.qprox.getSlotsByHive( hives[0][0] )
        dslots = env.qprox.getSlotsByDrone( drones[0][0] )

        self.assertEqual( len(hslots), 0 )
        self.assertEqual( len(dslots), 2 )

        slot = env.qprox.getWorkSlot( hives[0][0] )

        self.assertEqual( slot[1].get('hive'), hives[0][0] )
        self.assertEqual( slot[1].get('drone'), drones[0][0] )

        hslots = env.qprox.getSlotsByHive( hives[0][0] )
        self.assertEqual( len(hslots), 1 )

        env.qprox.fireSlotFini( hslots[0][0] )

        hslots = env.qprox.getSlotsByHive( hives[0][0] )
        self.assertEqual( len(hslots), 0 )

        env.fini()
