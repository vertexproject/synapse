'''
The HiveMind subsystem implements cluster work distribution.
'''
import time
import logging
import threading
import collections

import multiprocessing as mproc

import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.mindmeld as s_mindmeld
import synapse.telepath as s_telepath

import synapse.lib.sched as s_sched
import synapse.lib.scope as s_scope
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

cpus = mproc.cpu_count()

class Queen(EventBus):
    '''
    The queen manages available workers and work slots.
    '''
    def __init__(self):
        EventBus.__init__(self)
        self.lock = threading.Lock()
        self.sched = s_sched.Sched()

        self.slots = {}

        self.hives = {}
        self.drones = {}

        self.slotq = collections.deque()

    def getSlotsByHive(self, iden):
        '''
        Return a list of slot tuples allocated to a hive.
        '''
        return [ s for s in self.slots.values() if s[1].get('hive') == iden ]

    def getSlotsByDrone(self, iden):
        '''
        Return the list of slot tuples provided by a drone.
        '''
        return [ s for s in self.slots.values() if s[1].get('drone') == iden ]

    def getDrones(self):
        return list(self.drones.values())

    def getHives(self):
        return list(self.hives.values())

    def iAmHive(self, iden, **info):
        hive = (iden,info)
        self.hives[iden] = hive

        sock = s_scope.get('sock')
        def onfini():
            self.fireHiveFini(iden)
        sock.onfini( onfini )

        self.fire('hive:hive:init', hive=hive)

    def iAmDrone(self, iden, **info):

        drone = (iden,info)
        self.drones[iden] = drone

        sock = s_scope.get('sock')
        def onfini():
            self.fireDroneFini(iden)
        sock.onfini(onfini)

        self.fire('hive:drone:init', iden=iden)

    def fireHiveFini(self, iden):
        hive = self.hives.pop(iden,None)
        if hive == None:
            return

        self.fire('hive:hive:fini', hive=hive)
        slots = self.getSlotsByHive(iden)
        [ self.fireSlotFini(s[0]) for s in slots ]

    def fireDroneFini(self, iden):
        drone = self.drones.pop(iden,None)
        if drone == None:
            return

        self.fire('hive:drone:fini', drone=drone)
        slots = self.getSlotsByDrone(iden)
        [ self.fireSlotFini(s[0]) for s in slots ]

    def fireSlotFini(self, iden):
        slot = self.slots.pop(iden,None)
        if slot == None:
            return

        hive = slot[1].get('hive')
        if hive != None:
            self.tell(hive,'hive:slot:fini', slot=slot)

        drone = slot[1].get('drone')
        if drone != None:
            self.tell(drone,'hive:slot:fini',slot=slot)

    def getWorkSlot(self, hive):
        '''
        Return the next slot tuple for worker tasking.

        Notes:

            Returns None if no slots are available.  Also, once
            a work slot has been returned, a Hive *must* task the
            Drone immediately to prevent revokation of the work slot.

        '''
        with self.lock:

            while self.slotq:

                iden = self.slotq.popleft()
                slot = self.slots.get(iden)
                if slot == None:
                    continue

                slot[1]['hive'] = hive
                slot[1]['gave'] = time.time()

                self.fire('hive:slot:give', slot=slot)
                return slot

            return None

    def addWorkSlot(self, slot):
        with self.lock:
            self.slots[slot[0]] = slot
            self.slotq.append(slot[0])

    def runWorkSlot(self, slot, job):
        '''
        Run a "hive compatible" job in the given work slot.
        '''
        item = self.slotgave.get(slot[0])
        self.sched.cancel(item)

    def tell(self, iden, name, **info):
        mesg = (name,info)
        self.fire('hive:tell:%s' % iden, mesg=mesg)

class Hive(s_async.Boss):
    '''
    The Hive class provides a Pool like API around a Queen's hive.
    '''
    def __init__(self, queen, size=1024):
        s_async.Boss.__init__(self)

        self.meld = None
        self.iden = guid()

        self.queen = queen

        self.queen.on('hive:tell:%s' % self.iden, self._onHiveTell)

        self.todo = collections.deque()
        self.sema = threading.Semaphore(size)

        self.queen.push(self.iden,self)
        self.queen.iAmHive(self.iden)

        self.onfini( self._tellQueenFini )

    def genHiveMeld(self):
        if self.meld == None:
            self.meld = s_mindmeld.MindMeld()
        return self.meld

    def _tellQueenFini(self):
        self.queen.fireHiveFini(self.iden)

    def _onHiveTell(self, mesg):
        self.dist( mesg[1].get('mesg') )

    def _onJobDone(self, mesg):
        self.sema.release()
        return s_async.Boss._onJobDone(self,mesg)

    def _getWorkSlot(self, timeout=None):
        #FIXME TIMEOUT
        slot = self.queen.getWorkSlot(self.iden)
        while slot == None:
            # FIXME wait on event from queen?
            time.sleep(2)
            slot = self.queen.getWorkSlot(self.iden)
        return slot

    def task(self, dyntask, ondone=None, timeout=None):

        self.sema.acquire()

        slot = self._getWorkSlot()
        drone = slot[1].get('drone')

        jobinfo = {
            'slot':slot,
            'ondone':ondone,
            'dyntask':dyntask,
            'timeout':timeout,
        }

        if self.meld != None:
            jobinfo['meld'] = self.meld.getMeldDict()

        job = self.initJob(**jobinfo)
        self.queen.tell(drone,'hive:slot:run', job=job)
        return job

class Drone(EventBus):
    '''
    The Drone carries out jobs tasked by the Queen.
    '''
    def __init__(self, queen, **config):
        # NOTE: queen must *always* be a telepath proxy

        EventBus.__init__(self)

        self.iden = guid()

        self.slots = {}
        self.slocs = {}

        self.queen = queen
        self.config = config

        # FIXME maybe put our hostname etc in config?

        self.queen.on('tele:sock:init', self._onTeleSockInit )
        self.queen.on('hive:tell:%s' % self.iden, self._onHiveTell)

        self.localurl = 'local://%s/syn.queen' % self.iden

        # each worker has a local:// daemon
        self.dmon = s_daemon.Daemon()
        self.dmon.listen(self.localurl)

        self.dmon.share('syn.queen',queen)

        self.on('hive:slot:run', self._onHiveSlotRun)
        self.on('hive:slot:fini', self._onHiveSlotFini)

        self._initQueenProxy()

    def _initQueenProxy(self):
        self.queen.push(self.iden,self)
        self.queen.iAmDrone(self.iden,**self.config)
        self._addWorkSlots()

    def _onTeleSockInit(self, mesg):
        self._initQueenProxy()

    def _onHiveSlotFini(self, mesg):
        iden = mesg[1].get('slot')[0]

        slot = self.slots.pop(iden,None)
        sloc = self.slocs.pop(iden,None)

        proc = sloc.get('proc')
        if proc != None:
            proc.terminate()

        # add a new work slot for the lost one
        self._addWorkSlot()

    def _onHiveTell(self, mesg):
        self.dist( mesg[1].get('mesg') )

    def _addWorkSlots(self):
        for i in range( self.config.get('size', cpus) ):
            self._addWorkSlot()

    def _addWorkSlot(self):
        iden = guid()
        slot = tufo(iden, drone=self.iden)

        self.slots[iden] = slot
        self.slocs[iden] = {}

        self.queen.addWorkSlot(slot)

    def _onHiveSlotRun(self, mesg):
        job = mesg[1].get('job')
        self._runHiveJob(job)

    @s_threads.firethread
    def _runHiveJob(self, job):
        '''
        Fire a thread to run a job in a seperate Process.
        '''
        slot = job[1].get('slot')
        sloc = self.slocs.get( slot[0] )

        job[1]['queen'] = self.localurl

        try:

            proc = mproc.Process(target=subtask, args=(job,))
            proc.start()

            sloc['proc'] = proc

            timeout = job[1].get('timeout')
            proc.join(timeout)

            if proc.exitcode == None:
                proc.terminate()

            sloc['proc'] = None

        finally:
            self.queen.fireSlotFini(slot[0])

def subtask(job):
    jid = job[0]

    slot = job[1].get('slot')

    meld = job[1].get('meld')
    if meld != None:
        s_mindmeld.loadMindMeld(meld)

    hive = slot[1].get('hive')

    queen = s_telepath.openurl( job[1].get('queen') )

    s_scope.set('syn.queen',queen)

    try:
        dyntask = job[1].get('dyntask')
        ret = s_dyndeps.runDynTask(dyntask)

        queen.tell(hive, 'job:done', jid=jid, ret=ret)

    except Exception as e:
        queen.tell(hive, 'job:done', jid=jid, **excinfo(e))

