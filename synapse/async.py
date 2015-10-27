import time
import traceback
import threading
import collections

from synapse.compat import queue

import synapse.sched as s_sched
import synapse.queue as s_queue
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.impulse as s_impulse
import synapse.threads as s_threads

class AsyncError(Exception):pass
class NoSuchJob(AsyncError):pass
class JobTimedOut(AsyncError):pass
class BossShutDown(AsyncError):pass

class JobErr(Exception):
    def __init__(self, err, errmsg='', trace=''):
        self._job_err = err
        self._job_trace = trace
        self._job_errmsg = errmsg
        Exception.__init__(self, '%s\n(%s: %s)' % (trace,err,errmsg))

def jobid():
    return s_common.guidstr()

def jobret(job):
    '''
    Use the job status to either return or raise.

    Example:

        return jobret(job)

    '''
    err = job[1].get('err')
    if err != None:
        errmsg = job[1].get('errmsg')
        raise JobErr(err,errmsg=errmsg)
    return job[1].get('ret')

def newtask(meth,*args,**kwargs):
    return (meth,args,kwargs)

class AsyncBoss(s_impulse.PulseRelay):
    '''
    An AsyncBoss manages AsyncJobs.

    An AsyncBoss has two main use cases:

    1. State Tracking Only ( size = None )
    2. Acutally Doing Work ( size = <int> )

    '''
    def __init__(self, size=None):
        s_impulse.PulseRelay.__init__(self)

        self.onfini(self._finiAllJobs)
        self.onfini(self._finiAllThreads)

        self.size = size
        self.jobq = queue.Queue()

        self.sched = s_sched.Sched()
        self.threads = []

        self.joblock = threading.RLock()

        self.jobs = {}
        self.jobfini = collections.defaultdict(list)
        self.jobevt = {}
        self.jobtask = {}   # jid:(meth,args,kwargs) "task tuple"
        self.jobtimeo = {}  # jid:<event> ( for sched.cancel() )

        self.on('job:fini', self._myOnJobFini )

        if size != None:
            self.addPoolWorkers(size)

    def setPoolSize(self, size):
        '''
        Update the size of the thread worker pool.

        Example:

            boss.setPoolSize(10)

        '''
        with self.joblock:

            if self.size == None:
                self.size = 0

            delta = size - self.size
            if delta == 0:
                return

            if delta < 0:
                self.delPoolWorkers(abs(delta))
                return

            self.addPoolWorkers(delta)

    def addPoolWorkers(self, count):
        '''
        Spin up additional worker threads.

        Example:

            boss.addPoolWorkers(8)

        '''
        for i in range(count):
            self._initPoolThread()

    def delPoolWorkers(self, count):
        '''
        Spin down some worker threads.

        Example:

            boss.delPoolWorkers(2)

        '''
        count = min(count,len(self.threads))
        for i in range(count):
            self.jobq.put(None)

    def getAsyncJobs(self):
        '''
        Return a list of job tuples.

        Example:

            for job in boss.getAsyncJobs():
                dostuff(job)

        '''
        return list(self.jobs.values())

    def getAsyncJob(self, jid):
        '''
        Return a job tuple by ID.

        Example:

            job = boss.getAsyncJob(jid)

        '''
        return self.jobs.get(jid)

    def setJobInfo(self, jid, prop, valu):
        '''
        Set a property in the job info dictionary.

        Example:

            boss.setJobInfo(jid,'woot',10)

        '''
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                return

            old = job[1].get(prop)
            job[1][prop] = valu

        #self.fire('job:set', job=job, prop=prop, valu=valu, old=old)

    def setJobTask(self, jid, meth, *args, **kwargs):
        '''
        Set the task tuple (meth, args, kwargs) for the job.

        Example:

            boss.setJobTask( jid, foo.bar, 10, y=30 )

        '''
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                return

            self.jobtask[jid] = (meth,args,kwargs)

    def initAsyncJob(self, jid, **info):
        '''
        Initialize and return a new AsyncJob.

        Example:

            jid = jobid()
            task = (meth,args,kwargs)

            job = boss.initAsyncJob(jid,task=task,timeout=60)

        Notes:
            Info Conventions:
            * task=(meth,args,kwargs)
            * dyntask=('mod.func',args,kwargs)
            * autoque=True # init *and* queue job (default)
            * timeout=<sec> # max runtime
            * onfini=<meth> # def onfini(job):

        '''
        if self.isfini:
            raise BossShutDown()

        times = {'init':time.time()}

        info['times'] = times
        info['status'] = 'new'

        job = (jid,info)
        return self.addAsyncJob(job)

    def addAsyncJob(self, job):
        '''
        Add an existing async job tuple to this AsyncBoss.

        Notes:

            This API is mostly for use in synchronizing 
            multiple AsyncBoss instances.

        '''
        jid,jinfo = job
        jinfo.setdefault('autoque', True)

        task = jinfo.pop('task',None)
        if task != None:
            self.jobtask[jid] = task

        onfini = jinfo.pop('onfini',None)
        if onfini != None:
            self.jobfini[jid].append(onfini)

        self.jobs[jid] = job

        self.fire('job:init',job=job)

        if job[1].get('autoque'):
            self._putJobQue(job)

        return job

    def queAsyncJob(self, jid):
        '''
        Inform the boss that a job is ready to queue
        for execution.

        Example:

            boss.queAsyncJob(jid)

        '''
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                return

            self._putJobQue(job)

    def _putJobQue(self, job):
        job[1]['status'] = 'queue'
        job[1]['times']['putq'] = time.time()

        self.jobq.put(job)

    def _runPoolWork(self):
        '''
        Run the next job from the job queue.

        Example:

            while go:
                boss._runNextJob()

        Notes:

            This API is used internally by the pool.

        '''
        while not self.isfini:
            job = self.getNextJob()
            if job == None:
                return

            self._runAsyncJob(job)

    def _runAsyncJob(self, job):
        '''
        Actually execute the given job with the caller thread.
        '''
        task = self.jobtask.get(job[0])
        if task == None:

            dyntask = job[1].get('dyntask')
            if dyntask != None:
                methname, args, kwargs = dyntask
                meth = s_dyndeps.getDynLocal(methname)
                if meth == None:
                    self.setJobErr(job[0],'NoSuchMeth')
                    return

                task = (meth,args,kwargs)

            selftask = job[1].get('selftask')
            if selftask != None:
                methname, args, kwargs = selftask
                meth = getattr(self, methname, None)
                if meth == None:
                    self.setJobErr(job[0],'NoSuchMeth')
                    return

                task = (meth,args,kwargs)

        if task == None:
            self.setJobErr(job[0],'NoJobTask')
            return

        try:

            ret = self._runJobTask(job,task)
            self.setJobDone(job[0],ret)

        except Exception as e:
            err = e.__class__.__name__
            props = {'trace':traceback.format_exc(), 'errmsg':str(e)}
            self.setJobErr(job[0], err, **props)

    def _runJobTask(self, job, task):
        meth,args,kwargs = task
        return meth(*args,**kwargs)

    def setJobDone(self, jid, ret, **info):
        '''
        Complete an async job with success!

        Example:

            boss.setJobDone(jid, retval)

        '''
        with self.joblock:
            info['ret'] = ret
            info['status'] = 'done'
            return self._setJobFini(jid,**info)

    def setJobErr(self, jid, err, **info):
        '''
        Complete an async job with an error name.

        Example:

            boss.setJobErr(jid,'FooFailure')

        '''
        info['err'] = err
        info['status'] = 'err'
        return self._setJobFini(jid,**info)

    def _setJobFini(self, jid, **info):
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                return

            job[1].update(info)
            job[1]['times']['fini'] = time.time()

            self.fire('job:fini', job=job)

    def onJobFini(self, jid, meth):
        '''
        Register a fini handler for the given job.

        Example:

            def myfini(job):
                dostuff(job)

            boss.onJobFini( jid, myfini )

        '''
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                raise NoSuchJob(jid)

            self.jobfini[jid].append( meth )

    def _myOnJobFini(self, event):

        with self.joblock:
            job = event[1].get('job')
            jid = job[0]

            sch = self.jobtimeo.pop(jid,None)
            if sch is not None:
                try:
                    self.sched.cancel(sch)
                except ValueError as e:
                    # STUPID CANCEL API
                    pass # NEVER EVER DO THIS

            self.jobs.pop(jid,None)
            self.jobtask.pop(jid,None)
            evt = self.jobevt.pop(jid,None)
            jobfinis = self.jobfini.pop(jid,())

            if evt != None:
                evt.set()

            for fini in jobfinis:
                try:
                    fini(job)
                except Exception as e:
                    traceback.print_exc()

    def waitAsyncJob(self, jid, timeout=None):
        '''
        Wait for a job to complete by id.

        Example:

            boss.waitAsyncJob( jid, timeout=10 )

        '''
        with self.joblock:
            job = self.jobs.get(jid)
            if job == None:
                return True

            evt = self.jobevt.get(jid)
            if evt == None:
                evt = threading.Event()
                self.jobevt[jid] = evt

        evt.wait(timeout=timeout)
        return evt.is_set()

    def _initPoolThread(self):
        thr = s_threads.worker( self._runPoolWork )
        self.threads.append( thr )

    def _finiAllThreads(self):

        for i in range(len(self.threads)):
            self.jobq.put(None)

        for thr in self.threads:
            thr.join()

    def getNextJob(self):
        '''
        Retrieve the next queue'd job to run.
        '''
        while True:
            job = self.jobq.get()
            if job == None:
                return

            # if we get a job from the que that has
            # already been canceled...
            if job[1]['status'] != 'queue':
                continue

            job[1]['status'] = 'run'
            job[1]['times']['getq'] = time.time()

            timeout = job[1].get('timeout')
            if timeout != None:
                jid = job[0]
                evt = self.sched.insec( timeout, self.setJobErr, jid, 'JobTimedOut' )
                self.jobtimeo[job[0]] = evt

            return job

    def _finiAllJobs(self):
        for job in self.getAsyncJobs():
            self.setJobErr(job[0],'BossShutDown')

class AsyncMeth:
    '''
    AsyncMeth allows simple syntax for AsyncJob methods.
    ( it acts as a transient syntax sugar helper )
    '''
    def __init__(self, boss, meth):
        self.boss = boss
        self.meth = meth

    def __call__(self, *args, **kwargs):
        jid = jobid()
        task = (self.meth, args, kwargs)

        job = self.boss.initAsyncJob(jid, task=task)
        return job

class AsyncApi:
    '''
    Wrap an object to allow all API calls to be async.

    Example:

        class Foo:
            def bar(self, x):
                return x + 20

        foo = Foo()

        async = AsyncApi(foo)
        async.bar(20) # calls foo.bar(20) as a job

    '''
    def __init__(self, boss, item):
        self.item = item
        self.boss = boss

    def __getattr__(self, name):
        meth = getattr(self.item, name)
        return AsyncMeth(self.boss, meth)


