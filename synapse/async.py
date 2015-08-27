import time
import threading

from synapse.compat import queue

import synapse.common as s_common
import synapse.threads as s_threads
import synapse.eventbus as s_eventbus

class AsyncError(Exception):pass
class JobTimedOut(AsyncError):pass
class JobHasNoTask(AsyncError):pass
class BossShutDown(AsyncError):pass
class BossHasNoPool(AsyncError):pass

class AsyncJob(s_eventbus.EventBus):
    '''
    A single asynchronous job.
    '''
    def __init__(self, boss):
        s_eventbus.EventBus.__init__(self)
        self.jid = s_common.guid()

        self.boss = boss
        self.info = {}

        self.task = None    # (meth,args,kwargs)

        self.retval = None
        self.retexc = None

    def runInPool(self):
        '''
        Add this AsyncJob to the AsyncBoss work pool.

        Example:

            job.runInPool()

        '''
        self.boss.addPoolJob(self)

    def __getitem__(self, item):
        '''
        MOAR syntax sugar...

            job[item].fooBarThing(20)

        '''
        return AsyncMeth(self,item)

    def setJobTask(self, meth, *args, **kwargs):
        '''
        Inform the AsyncJob of the function and arguments to execute.

        Example:

            job.setJobTask( item.fooBarBaz, 20, blah=True )

        Notes:
            * this does *not* trigger job execution

        '''
        self.task = (meth,args,kwargs)

    def run(self):
        '''
        Uses the calling thread to execute the previously set task.

        Example:

            job.run()

        Notes:

            * Mostly used by AsyncPool

        '''
        if self.task == None:
            return self.err( JobHasNoTask() )

        # FIXME set current job as thread local for update methods?
        meth,args,kwargs = self.task
        stime = time.time()
        try:
            ret = meth(*args,**kwargs)

            self.info['took'] = time.time() - stime
            self.done(ret)

        except Exception as e:
            self.info['took'] = time.time() - stime
            self.err(e)

    def err(self, exc):
        '''
        Complete the AsyncJob as an error.

        Example:

            try:
                doJobStuff()
            except Exception as e:
                job.err(e)

        '''
        if self.isfini:
            return

        self.retexc = exc
        self.fire('job:err',job=self,exc=exc)
        self.fini()

    def done(self, retval):
        '''
        Complete the AsyncJob with return value.

        Example:

            job.done(retval)

        '''
        if self.isfini:
            return

        self.retval = retval
        self.fire('job:done',job=self,ret=retval)
        self.fini()

    def ondone(self, meth):
        '''
        Set an ondone handler for this job.

        Example:

            def donemeth(ret):
                stuff(ret)

            job.ondone( donemeth )

        '''
        def jobdone(event):
            meth( event[1].get('ret') )

        self.on('job:done',jobdone)

    def onerr(self, meth):
        '''
        Add an onerr handler for this job.

        Example:

            def errmeth(exc):
                stuff(exc)

            job.onerr( errmeth )

        '''
        def joberr(event):
            meth( event[1].get('exc') )

        self.on('job:err',joberr)

    def sync(self, timeout=None):
        '''
        Wait for a job to complete and return or raise.

        Example:


            foo = Foo()
            job = boss[foo].bar(20)

            return job.sync()

        Note: 

            * This API cancels the job on timeout

        '''
        done = self.wait(timeout=timeout)
        self.fini()

        if not done:
            self.err( JobTimedOut() )

        if self.retexc != None:
            raise self.retexc

        return self.retval

class AsyncBoss(s_eventbus.EventBus):
    '''
    An AsyncBoss manages AsyncJobs.

    An AsyncBoss has two main use cases:

    1. State Tracking Only ( pool = 0 )
    2. Acutally Doing Work ( pool = # )

    '''
    def __init__(self, pool=0):
        s_eventbus.EventBus.__init__(self)
        self.jobs = {}
        self.pool = pool
        self.onfini(self._finiAllJobs)
        self.onfini(self._finiAllThreads)

        self.jobq = queue.Queue()
        self.threads = []

        self.addPoolWorkers(pool)

    def setPoolSize(self, pool):
        '''
        Update the size of the thread worker pool.

        Example:

            boss.setPoolSize(10)

        '''
        delta = pool - self.pool
        if delta == 0:
            return

        self.pool = pool
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

    def addPoolJob(self, job):
        '''
        Add an AsyncJob to the work queue.

        Example:

            boss.addPoolJob(job)

        Notes:

            * raises BossHasNoPool if there are no pool threads

        '''
        if self.isfini:
            raise BossShutDown()

        if not len(self.threads):
            raise BossHasNoPool()

        self.jobq.put( job )

    def getAsyncJobs(self):
        '''
        Return a list of AsyncJobs.

        Example:

            for job in boss.getAsyncJobs():
                dostuff(job)

        '''
        return list(self.jobs.values())

    def getAsyncJob(self, jid):
        '''
        Return an AsyncJob by ID.

        Example:

            job = boss.getAsyncJob(jid)

        '''
        return self.jobs.get(jid)

    def initAsyncJob(self):
        '''
        Initialize and return a new AsyncJob.

        Example:

            job = boss.initAsyncJob()

        '''
        if self.isfini:
            raise BossShutDown()

        job = AsyncJob(self)
        self.jobs[job.jid] = job

        job.on('job:err',self.dist)
        job.on('job:done',self.dist)
        job.on('job:status',self.dist)

        def popjob():
            self.jobs.pop(job.jid,None)

        job.onfini(popjob)
        return job

    def setJobDone(self, jid, retval):
        '''
        Call the done(retval) routine for the given job id.

        Example:

            boss.setJobDone(jid,10)

        '''
        job = self.getAsyncJob(jid)
        if job != None:
            job.done(retval)

    def setJobErr(self, jid, exc):
        '''
        Call the err(exc) routine for the given job id.

        Example:

            boss.setJobErr( jid, Exception('woot') )

        '''
        job = self.getAsyncJob(jid)
        if job != None:
            job.err(exc)

    def waitForJob(self, jid, timeout=None):
        '''
        Wait for a job to complete by id.

        Example:

            boss.waitForJob( jid, timeout=10 )

        '''
        job = self.getAsyncJob(jid)
        if job == None:
            return True

        return job.wait(timeout=timeout)

    def _initPoolThread(self):
        thr = s_threads.worker( self._poolWorker )
        self.threads.append( thr )

    def _finiAllThreads(self):

        for i in range(len(self.threads)):
            self.jobq.put(None)

        for thr in self.threads:
            thr.join()

    def __getitem__(self, item):
        '''
        Syntax sugar to que an async call...

            boss[thing].fooThingMeth(10)

        '''
        if not len(self.threads):
            raise BossHasNoPool()

        return AsyncApi(self, item)

    def _poolWorker(self):

        while True:

            try:

                job = self.jobq.get()
                if job == None:
                    return

                job.run()

            except Exception as e:
                traceback.print_exc()

    def _finiAllJobs(self):
        for job in self.getAsyncJobs():
            job.err(BossShutDown())

class AsyncMeth:
    '''
    AsyncMeth allows simple syntax for AsyncJob methods.
    ( it acts as a transient syntax sugar helper )
    '''
    def __init__(self, job, item, name=None):
        self.job = job
        self.item = item
        self.name = name

    def __getattr__(self, name):
        self.name = name
        return self

    def __call__(self, *args, **kwargs):
        meth = getattr(self.item, self.name)
        self.job.setJobTask( meth, *args, **kwargs )
        self.job.runInPool()
        return self.job

class AsyncApi:
    '''
    Wrap an object to allow all API calls to be async.

    Example:

        foo = Foo()

        async = AsyncApi(foo)
        async.bar(20) # calls foo.bar(20) as a job

    '''
    def __init__(self, boss, item):
        self.item = item
        self.boss = boss

    def __getattr__(self, name):
        job = self.boss.initAsyncJob()
        return AsyncMeth(job,self.item,name)

