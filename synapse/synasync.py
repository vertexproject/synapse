import time
import logging
import traceback
import threading

import synapse.common as s_common

import synapse.glob as s_glob
import synapse.lib.scope as s_scope
import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

def jobid():
    return s_common.guid()

def jobret(job):
    '''
    Return job result or raise on error.

    Example:

        return jobret(job)

    '''
    err = job[1].get('err')

    # populate errinfo into SynErr
    info = job[1].get('errinfo')
    if info is None:
        info = {}

    if err is not None:
        if err != 'NameErr':
            try:
                info = job[1].get('errinfo', {})
                raise s_common.synerr(err, **info)
            except NameError as e:
                pass
        raise s_common.JobErr(job)
    return job[1].get('ret')

def jobDoneMesg(job):
    '''
    Construct a job:done message for the given job.

    Example:

        def ondone(job):
            otherguy.dist( jobDoneMesg(job) )

    '''
    info = {'jid': job[0], 'ret': job[1].get('ret')}
    if job[1].get('err') is not None:
        info['err'] = job[1].get('err'),
        info['errmsg'] = job[1].get('errmsg'),
        info['errfile'] = job[1].get('errfile'),
        info['errline'] = job[1].get('errline'),

    return s_common.tufo('job:done', **info)

def newtask(meth, *args, **kwargs):
    return (meth, args, kwargs)

class Boss(EventBus):
    '''
    A Boss manages asynchonous jobs.

    ( If given a pool, he will execute them as well )

    Additionally, if given a pool, the boss will assume
    he is responsible for calling fini() on the pool when
    he is notified of fini()
    '''
    def __init__(self):
        EventBus.__init__(self)

        self.onfini(self._onBossFini)

        self.pool = None

        self.joblock = threading.Lock()

        self._boss_jobs = {}
        self.joblocal = {}

        self.on('job:done', self._onJobDone)  # trigger job done
        self.on('job:fini', self._onJobFini)  # job is finished

    def setBossPool(self, pool):
        '''
        Set a thread pool object for the boss.

        Example:

            pool = s_threads.Pool(size=3)
            boss.setBossPool(pool)

        '''
        self.pool = pool

    def runBossPool(self, size, maxsize=None):
        '''
        Create and run a thread pool for this Boss()

        Example:

            boss.runBossPool(3)

        '''
        pool = s_threads.Pool(size=size, maxsize=maxsize)
        self.onfini(pool.fini)
        self.setBossPool(pool)

    def _onJobDone(self, event):
        # used to *trigger* job done processing
        jid = event[1].get('jid')
        if jid is None:
            return

        job = self._boss_jobs.get(jid)
        if job is None:
            return

        job[1].update(event[1])

        job[1]['done'] = True
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
        for job in self.jobs():
            yield job

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
            raise s_common.IsFini()

        if jid is None:
            jid = s_common.guid()

        info['done'] = False
        info['times'] = []

        job = (jid, info)

        self._boss_jobs[jid] = job

        # setup our per job local storage
        # ( for non-serializables )
        joblocal = {
            'ondone': info.pop('ondone', None),
        }
        self.joblocal[jid] = joblocal

        self._addJobTime(job, 'init')

        if self.pool is not None:
            self.pool.call(self._runJob, job)

        # if we have a timeout, setup a sched callback
        timeout = job[1].get('timeout')
        if timeout is not None:

            def hitmax():
                joblocal.pop('schedevt', None)
                self.fire('job:done', jid=jid, err='HitMaxTime')

            joblocal['schedevt'] = s_glob.sched.insec(timeout, hitmax)

        self.fire('job:init', job=job)
        return job

    def sync(self, job, timeout=None):
        '''
        Wait and return the value for the job.
        '''
        if not self.wait(job[0], timeout=timeout):
            raise s_common.HitMaxTime(timeout)

        return jobret(job)

    def done(self, jid, ret):
        self.fire('job:done', jid=jid, ret=ret)

    def err(self, jid, **excinfo):
        self.fire('job:done', jid=jid, **excinfo)

    def _runJob(self, job):
        '''
        Actually execute the given job with the caller thread.
        '''
        task = job[1].get('task')
        if task is None:
            # TODO This attribute is not set, a bad tufo
            # sent to _runJob will have unexpected behavior.
            self.setJobErr(job[0], 'NoJobTask')
            return

        try:

            func, args, kwargs = task
            ret = func(*args, **kwargs)
            self.fire('job:done', jid=job[0], ret=ret)

        except Exception as e:
            self.fire('job:done', jid=job[0], **s_common.excinfo(e))

    def _onJobFini(self, event):

        with self.joblock:
            job = event[1].get('job')
            jid = job[0]

            self._boss_jobs.pop(jid, None)
            joblocal = self.joblocal.pop(jid, None)

            schedevt = joblocal.get('schedevt')
            if schedevt is not None:
                s_glob.sched.cancel(schedevt)

            ondone = joblocal.get('ondone')
            if ondone is not None:
                try:
                    ondone(job)
                except Exception as e:
                    logger.exception('Error executing ondone for jid %s', jid)

            evt = joblocal.get('waitevt')
            if evt is not None:
                evt.set()

    def wait(self, jid, timeout=None):
        '''
        Wait for a job to complete by id.

        Example:

            boss.wait( jid, timeout=10 )

        '''
        s_threads.iWillWait()

        if timeout is None:
            timeout = s_scope.get('syntimeout')

        with self.joblock:
            job = self._boss_jobs.get(jid)
            if job is None:
                return True

            joblocal = self.joblocal.get(jid)
            evt = joblocal.get('waitevt')
            if evt is None:
                evt = threading.Event()
                joblocal['waitevt'] = evt

        evt.wait(timeout=timeout)
        return evt.is_set()

    def _addJobTime(self, job, stage):
        job[1]['times'].append((stage, time.time()))

    def _onBossFini(self):
        for job in self.jobs():
            self.fire('job:done', jid=job[0], err='BossShutDown')
