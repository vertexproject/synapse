'''
The HiveMind subsystem implements cluster work distribution.
'''
import time
import threading
import traceback

import multiprocessing as mproc

import synapse.async as s_async
import synapse.compat as s_compat
import synapse.threads as s_threads
import synapse.dyndeps as s_dyndeps
import synapse.impulse as s_impulse
import synapse.mindmeld as s_mindmeld
import synapse.telepath as s_telepath

from synapse.common import *
from synapse.eventbus import EventBus

class JobProcErr(Exception):pass    # raised when mp.Process exits non-0

cpus = mproc.cpu_count()

class NoSuchSession(Exception):pass

class Hive(s_async.AsyncBoss):
    '''
    A class which implements the "drone session" awareness
    for both Queen and Worker.

    Note: this class expects to be a mixin to an EventBus.
    '''
    def __init__(self, size=None, queen=None):
        s_async.AsyncBoss.__init__(self, size=size)
        self._hive_sess = {}
        self._hive_queen = queen
        self._hive_lock = threading.Lock()

    def getDroneSess(self, sid):
        with self._hive_lock:
            sess = self._hive_sess.get(sid)
            if sess == None and self._hive_queen:
                sess = self._hive_queen.getDroneSess(sid)
                if sess != None:
                    self._hive_sess[sid] = sess

            return sess

    def addDroneSess(self, sess):
        with self._hive_lock:
            self._hive_sess[sess[0]] = sess

    def initDroneSess(self, **info):
        sid = s_async.jobid()
        info['ctime'] = time.time()
        info.setdefault('melds',())

        sess = (sid,info)
        self.addDroneSess(sess)
        return sid

    def finiDroneSess(self, sid):
        with self._hive_lock:
            sess = self._hive_sess.pop(sid,None)
            return sess

class Queen(Hive):
    '''
    The WorkUnit manager/distributor.
    '''

    def __init__(self, dmon):
        Hive.__init__(self)
        self.dmon = dmon

        self.on('job:fini', self._queenJobFini)

        self._checkSessTimeout()

    def _queenJobFini(self, event):
        job = event[1].get('job')
        chan = job[1].get('impchan')
        if chan == None:
            return

        self.dmon.distImpEvent(event,chan)

    def _checkSessTimeout(self):
        try:
            # FIXME CHECK SESS TIMES
            pass
        finally:
            self.sched.insec(60, self._checkSessTimeout )

class Drone(s_async.AsyncBoss):
    '''
    A Drone requests work to be done via the Queen.
    '''
    def __init__(self, link, melds=None):
        s_async.AsyncBoss.__init__(self)

        self.queen = s_telepath.Proxy(link)
        self.impchan = s_async.jobid()

        self.pulsr = s_impulse.Pulser(link,self.impchan)
        self.pulsr.link(self.dist)

        self.on('job:init', self._droJobInit)

        # if we have MindMelds add them to the sess
        sessmelds = []
        if melds != None:
            for meld in melds:
                sessmelds.append( meld.getMeldDict() )

        # FIXME chan.vs.sid teardown!
        self.sid = self.queen.initDroneSess(melds=sessmelds)

    def _onDroneFini(self):
        self.queen.finiDroneSess( self.sid )

    def _droJobInit(self, event):
        job = event[1].get('job')
        job[1]['sid'] = self.sid
        job[1]['impchan'] = self.impchan
        self.queen.addAsyncJob(job)

class Worker(Hive):
    '''
    The Worker carries out jobs tasked by the Queen.
    '''

    def __init__(self, queen, size=cpus):

        Hive.__init__(self, size=size, queen=queen)

        self.sema = threading.Semaphore(size)

        # all our events got to the queen
        self.on('job:fini', self._workJobDone)

        self._getQueenJobs()

    def _workJobDone(self, event):
        self._hive_queen.dist(event)

    @s_threads.firethread
    def _getQueenJobs(self):
        while not self.isfini:
            with self._hive_queen as queen:
                # FIXME Semaphore with timeout (in compat)

                # block until it's kewl to get more work
                self.sema.acquire()
            
                job = queen.getNextJob()
                if job == None:
                    self.sema.release()
                    continue

                job[1]['autoque'] = True

                self.addAsyncJob(job)

    def _runAsyncJob(self, job):
        try:

            sid = job[1].get('sid')
            sess = self.getDroneSess(sid)
            if sess == None:
                raise NoSuchSession(sid)

            task = s_async.newtask(runjob,job,sess)

            timeout = job[1].get('timeout')
            ret = worker(task,timeout=timeout)

            self.setJobDone(job[0], ret)

        except Exception as e:
            err = e.__class__.__name__
            trace = traceback.format_exc()
            self.setJobErr(job[0], err, trace=trace)

        finally:
            self.sema.release()

def runjob(job,sess):
    '''
    The routine to execute a job ( run within the subprocess )
    '''
    for meld in sess[1].get('melds',()):
        s_mindmeld.loadMindMeld(meld)

    dyntask = job[1].get('dyntask')
    name,args,kwargs = dyntask
    meth = s_dyndeps.getDynLocal(name)
    return meth(*args,**kwargs)

def subtask(task,outq):
    '''
    Execute a task tuple and put the return value in que.
    '''
    meth,args,kwargs = task
    try:
        ret = meth(*args,**kwargs)
        outq.put( ('done',{'ret':ret}) )

    except Exception as e:
        err = e.__class__.__name__
        trace = traceback.format_exc()

        outq.put( ('err',{'err':err,'trace':trace}) )

def worker(task, timeout=None):

    que = mproc.Queue()
    proc = mproc.Process(target=subtask, args=(task,que))

    proc.start()
    proc.join(timeout)

    # did the process complete?
    if proc.exitcode == None:
        proc.terminate()
        raise s_async.JobTimedOut()

    # check proc.exitcode and possibly fail
    if proc.exitcode != 0:
        raise JobProcErr(proc.exitcode)

    # raise s_async.JobTimedOut
    status,retinfo = que.get()
    if status == 'done':
        return retinfo.get('ret')

    err = retinfo.get('err')
    trace = retinfo.get('trace','')

    raise s_async.JobErr(err,trace=trace)
