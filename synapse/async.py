import time
import traceback
import threading
import collections

from synapse.compat import queue

import synapse.sched as s_sched
import synapse.lib.queue as s_queue
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.impulse as s_impulse
import synapse.session as s_session
import synapse.lib.threads as s_threads

from synapse.common import *

def jobid():
    return s_common.guidstr()

def jobret(job):
    '''
    Return job result or raise on error.

    Example:

        return jobret(job)

    '''
    err = job[1].get('err')
    if err != None:
        raise JobErr(job)
    return job[1].get('ret')

def newtask(meth,*args,**kwargs):
    return (meth,args,kwargs)

class Boss(s_impulse.PulseRelay):
    '''
    A Boss manages asynchonous jobs.

    ( If given a pool, he will execute them as well )

    Additionally, if given a pool, the boss will assume
    he is responsible for calling fini() on the pool when
    he is notified of fini()
    '''
    def __init__(self):
        s_impulse.PulseRelay.__init__(self)

        self.onfini( self._onBossFini )

        self.pool = None
        self.sched = s_sched.getGlobSched()

        self.joblock = threading.Lock()

        self._boss_jobs = {}
        self.joblocal = {}

        self.on('job:done', self._onJobDone )  # trigger job done
        self.on('job:fini', self._onJobFini )  # job is finished

    def setBossPool(self, pool):
        '''
        Set a thread pool object for the boss.

        Example:

            pool = s_threads.Pool(size=3)
            boss.setBossPool(pool)

        '''
        self.pool = pool
        self.onfini( self.pool.fini )

    def runBossPool(self, size, maxsize=None):
        '''
        Create and run a thread pool for this Boss()

        Example:

            boss.runBossPool(3)

        '''
        pool = s_threads.Pool(size=size, maxsize=maxsize)
        self.setBossPool(pool)

    def _onJobDone(self, event):
        # used to *trigger* job done processing
        jid = event[1].get('jid')
        if jid == None:
            return

        job = self._boss_jobs.get(jid)
        if job == None:
            return

        job[1].update( event[1] )

        self.fire('job:fini', job=job)

    def jobs(self):
        '''
        Return a list of job tuples.

        Example:

            for job in boss.jobs():
                dostuff(job)

        '''
        return list(self._boss_jobs.values())

    def __iter__(self):
        return self.jobs()

    def job(self, jid):
        '''
        Return a job tuple by ID.

        Example:

            job = boss.job(jid)

        '''
        return self._boss_jobs.get(jid)

    def initJob(self, jid=None, **info):
        '''
        Initialize and return a new job tufo.

        Example:

            jid = jobid()
            task = (meth,args,kwargs)

            job = boss.initJob(jid,task=task,timeout=60)

        Notes:
            Info Conventions:
            * task=(meth,args,kwargs)
            * timeout=<sec> # max runtime
            * ondone=<meth> # def ondone(job):

        '''
        if self.isfini:
            raise BossShutDown()

        if jid == None:
            jid = guidstr()

        info['times'] = []

        job = (jid,info)

        self._boss_jobs[jid] = job

        # setup our per job local storage
        # ( for non-serializables )
        joblocal = {
            'ondone':info.pop('ondone',None),
        }
        self.joblocal[jid] = joblocal

        self._addJobTime(job,'init')

        if self.pool != None:
            self.pool.call( self._runJob, job )

        # if we have a timeout, setup a sched callback
        timeout = job[1].get('timeout')
        if timeout != None:

            def hitmax():
                joblocal.pop('schedevt',None)
                self.fire('job:done', jid=jid, err='HitMaxTime')

            joblocal['schedevt'] = self.sched.insec(timeout,hitmax)

        return job

    def _runJob(self, job):
        '''
        Actually execute the given job with the caller thread.
        '''
        task = job[1].get('task')
        if task == None:
            self.setJobErr(job[0],'NoJobTask')
            return

        try:

            func,args,kwargs = task
            ret = func(*args,**kwargs)
            self.fire('job:done', jid=job[0], ret=ret)

        except Exception as e:
            self.fire('job:done', jid=job[0], **excinfo(e))

    def _onJobFini(self, event):

        with self.joblock:
            job = event[1].get('job')
            jid = job[0]

            self._boss_jobs.pop(jid,None)
            joblocal = self.joblocal.pop(jid,None)

            schedevt = joblocal.get('schedevt')
            if schedevt != None:
                self.sched.cancel(schedevt)

            evt = joblocal.get('waitevt')
            if evt != None:
                evt.set()

            ondone = joblocal.get('ondone')
            if ondone != None:
                try:
                    ondone(job)
                except Exception as e:
                    traceback.print_exc()

    def wait(self, jid, timeout=None):
        '''
        Wait for a job to complete by id.

        Example:

            boss.wait( jid, timeout=10 )

        '''
        with self.joblock:
            job = self._boss_jobs.get(jid)
            if job == None:
                return True

            joblocal = self.joblocal.get(jid)
            evt = joblocal.get('waitevt')
            if evt == None:
                evt = threading.Event()
                joblocal['waitevt'] = evt

        evt.wait(timeout=timeout)
        return evt.is_set()

    def _addJobTime(self, job, stage):
        job[1]['times'].append( (stage,time.time()) )

    def _onBossFini(self):
        for job in self.jobs():
            self.fire('job:done', jid=job[0], err='BossShutDown')

        if self.pool:
            self.pool.fini()
