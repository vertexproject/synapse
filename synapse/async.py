import time
import queue
import threading

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
        self.boss = boss
        self.task = None    # (meth,args,kwargs)
        self.time = time.time()
        self.lock = threading.Lock()
        self.ident = s_common.guid()

        self.retval = None
        self.retexc = None

        #self.prog = 0
        #self.status = 'new'

    #def synSetJobStatus(self, status):
        #self.synFire('status',status)
    #def synGetJobStatus(self):

    #def synSetJobProgress(self, prog):
        #self.synFire('progress',prog)
    #def synGetJobProgress(self):

    def getJobProxy(self, item):
        '''
        Retrieve a AsyncProxy for this job which wraps item.

        Example:

            # item has method fooBarThing

            p = job.getJobProxy(item)
            p.fooBarThing(20)

        Notes:

            * AsyncProxy is mostly syntax sugar for:

                job.setJobTodo( item.fooBarThing, 20 )
                job.runInPool()

        '''
        return AsyncProxy(self, item)

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
        return self.getJobProxy(item)

    def setJobTask(self, meth, *args, **kwargs):
        '''
        Inform the AsyncJob of the function and arguments to execute.

        Example:

            job.setJobTask( item.fooBarBaz, 20, blah=True )

        Notes:
            * this does *not* trigger job execution

        '''
        self.task = (meth,args,kwargs)

    def runJobTask(self):
        '''
        Uses the calling thread to execute the previously set task.

        Example:

            job.runJobTask()

        Notes:

            * Mostly used by AsyncPool

        '''
        if self.task == None:
            exc = JobHasNoTask()
            self.synFireErr(exc)
            raise exc

        # FIXME set current job as thread local for update methods?
        meth,args,kwargs = self.task
        try:
            self.synFireDone( meth(*args,**kwargs) )
        except Exception as e:
            self.synFireErr(e)

    def synFireErr(self, exc):
        '''
        Complete the AsyncJob as an error.

        Example:

            try:
                doJobStuff()
            except Exception as e:
                job.synFireErr(e)

        '''
        with self.lock:
            if self.isfini:
                return
            self.retexc = exc
            self.synFire('err',exc=exc)
            self.synFini()

    def synFireDone(self, retval):
        '''
        Complete the AsyncJob with return value.

        Example:

            job.synFireDone(retval)

        '''
        with self.lock:
            if self.isfini:
                return
            self.retval = retval
            self.synFire('done',ret=retval)
            self.synFini()

    def getJobId(self):
        '''
        Returns the GUID for this AsyncJob.
        '''
        return self.ident

    def waitForJob(self, timeout=None):
        '''
        Block waiting for job completion.
        '''
        with self.lock:
            if self.isfini:
                return

            event = threading.Event()
            def onfini():
                event.set()

            self.synOnFini(onfini,weak=True)

        return event.wait(timeout=timeout)

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
        self.synOnFini(self._finiAllJobs)
        self.synOnFini(self._finiAllThreads)

        self.jobq = queue.Queue()
        self.threads = []

        self.addPoolWorkers(pool)

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
        Return an AsyncJob by GUID.

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
        jid = job.getJobId()
        self.jobs[jid] = job

        def popjob():
            self.jobs.pop(jid,None)

        job.synOnFini(popjob)
        return job

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

        job = self.initAsyncJob()
        return job.getJobProxy(item)

    def _poolWorker(self):

        while True:

            try:

                job = self.jobq.get()
                if job == None:
                    return

                job.runJobTask()

            except Exception as e:
                traceback.print_exc()

    def _finiAllJobs(self):
        for job in self.getAsyncJobs():
            job.synFireErr(BossShutDown())

class AsyncProxy:
    '''
    AsyncProxy allows simple syntax for AsyncJob methods.
    ( it acts as a transient syntax sugar helper )
    '''
    def __init__(self, job, item):
        self.job = job
        self.item = item
        self.methname = None

    def __getattr__(self, name):
        self.methname = name
        return self

    def __call__(self, *args, **kwargs):
        meth = getattr(self.item, self.methname)
        self.job.setJobTask( meth, *args, **kwargs )
        self.job.runInPool()
        return self.job

