import os
import logging
import threading
import traceback
import contextlib
import collections

from functools import wraps

import synapse.common as s_common

import synapse.lib.task as s_task
import synapse.lib.queue as s_queue

from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

def current():
    return threading.currentThread()

def iden():
    return threading.currentThread().ident

def isfini():
    return getattr(current(), 'isfini', False)

def withlock(lock):
    def decor(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            with lock:
                return f(*args, **kwargs)
        return wrap
    return decor

class cancelable:
    '''
    Use these to allow cancelation of blocking calls
    (where possible) to shutdown threads.

    Example:

        with cancelable(sock.close):
            byts = sock.recv(100)

    '''

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            logger.exception('Error executing %s', self.func)

    def __enter__(self):
        current().cancels.append(self)
        return self

    def __exit__(self, exc, cls, tb):
        current().cancels.pop()
        return

class Thread(threading.Thread, EventBus):
    '''
    A thread / EventBus to allow fini() etc.
    '''
    def __init__(self, func, *args, **kwargs):
        EventBus.__init__(self)

        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.iden = s_common.guid()
        self.task = (func, args, kwargs)

        self.cancels = []

        self.onfini(self._onThrFini)

    def run(self):
        func, args, kwargs = self.task
        ret = func(*args, **kwargs)
        self.fire('thread:done', thread=self, ret=ret)
        self.fini()

    def _onThrFini(self):
        [cancel() for cancel in self.cancels]

def worker(func, *args, **kwargs):
    '''
    Fire a worker thread to run the given func(*args,**kwargs)
    '''
    thr = Thread(func, *args, **kwargs)
    thr.start()
    return thr

def newtask(func, *args, **kwargs):
    return (func, args, kwargs)

class Pool(EventBus):
    '''
    A thread pool for firing and cleaning up threads.

    The Pool() class can be used to keep persistant threads
    for work processing as well as optionally spin up new
    threads to handle "bursts" of activity.

    # fixed pool of 16 worker threads
    pool = Pool(size=16)

    # dynamic pool of 5-10 workers
    pool = Pool(size=5, maxsize=10)

    # dynamic pool of 8-<infiniy> workers
    pool = Pool(size=8, maxsize=-1)

    '''
    def __init__(self, size=3, maxsize=None):
        EventBus.__init__(self)

        self.workq = s_queue.Queue()

        self._pool_lock = threading.Lock()
        self._pool_avail = 0

        if maxsize is None:
            maxsize = size

        self._pool_maxsize = maxsize

        self._pool_threads = {}

        self.onfini(self._onPoolFini)

        for i in range(size):
            self._fire_thread(self._run_work)

    def wrap(self, func):
        '''
        Wrap a function to transparently dispatch via the pool.

        Example:

            # dispatch the message handler from a pool

            bus.on('foo', pool.wrap( doFooThing ) )

        '''
        def poolcall(*args, **kwargs):
            self.call(func, *args, **kwargs)
        return poolcall

    def call(self, func, *args, **kwargs):
        '''
        Call the given func(*args,**kwargs) in the pool.
        '''
        self._que_work((func, args, kwargs))

    @contextlib.contextmanager
    def task(self, func, *args, **kwargs):
        '''
        Call the given function in the pool with a task.

        NOTE: Callers *must* use with-block syntax.

        Example:

            def foo(x):
                dostuff()

            def onretn(valu):
                otherstuff()

            with pool.task(foo, 10) as task:
                task.onretn(onretn)

            # the task is queued for execution *after* we
            # leave the with block.
        '''
        call = (func, args, kwargs)
        task = s_task.CallTask(call)

        yield task

        self._que_work((task.run, (), {}))

    def _que_work(self, work):

        with self._pool_lock:

            if self.isfini:
                raise s_common.IsFini(self.__class__.__name__)

            # we're about to put work into the queue
            # lets see if we should also fire another worker

            # if there are available threads, no need to fire
            if self._pool_avail != 0:
                self.workq.put(work)
                return

            # got any breathing room?
            if self._pool_maxsize > len(self._pool_threads):
                self._fire_thread(self._run_work)
                self.workq.put(work)
                return

            # got *all* the breathing room?
            if self._pool_maxsize == -1:
                self._fire_thread(self._run_work)
                self.workq.put(work)
                return

            self.workq.put(work)

    def _fire_thread(self, func, *args, **kwargs):
        thr = Thread(func, *args, **kwargs)
        thr.link(self.dist)

        thr.name = 'SynPool(%d):%s' % (id(self), thr.iden)

        self._pool_threads[thr.iden] = thr

        def onfini():
            self._pool_threads.pop(thr.iden, None)

        thr.onfini(onfini)

        thr.start()
        return thr

    def _run_work(self):

        while not self.isfini:

            self._pool_avail += 1

            work = self.workq.get()

            self._pool_avail -= 1

            if work is None:
                return

            try:

                func, args, kwargs = work
                func(*args, **kwargs)

            except Exception as e:
                logger.exception('error running task for [%s]', work)

    def _onPoolFini(self):
        threads = list(self._pool_threads.values())

        [self.workq.put(None) for i in range(len(threads))]

        [t.fini() for t in threads]
        #[ t.join() for t in threads ]

class RWLock:
    '''
    A multi-reader/exclusive-writer lock.
    '''
    def __init__(self):
        self.lock = threading.Lock()
        self.ident = os.urandom(16)

        self.rw_holder = None
        self.ro_holders = set()

        self.ro_waiters = collections.deque()
        self.rw_waiters = collections.deque()

    def reader(self):
        '''
        Acquire a multi-reader lock.

        Example:
            lock = RWLock()

            with lock.reader():
                # other readers can be here too...
                dowrites()
        '''
        # use thread locals with our GUID for holder ident
        holder = getThreadLocal(self.ident, RWWith, self)

        holder.event.clear()
        holder.writer = False

        with self.lock:

            # if there's no rw holder, off we go!
            if not self.rw_holder and not self.rw_waiters:
                self.ro_holders.add(holder)
                return holder

            self.ro_waiters.append(holder)

        holder.event.wait() # FIXME timeout
        return holder

    def writer(self):
        '''
        Acquire an exclusive-write lock.

        Example:
            lock = RWLock()

            with lock.writer():
                # no readers or other writers but us!
                dowrites()
        '''
        holder = getThreadLocal(self.ident, RWWith, self)

        holder.event.clear()
        holder.writer = True

        with self.lock:

            if not self.rw_holder and not self.ro_holders:
                self.rw_holder = holder
                return holder

            self.rw_waiters.append(holder)

        holder.event.wait() # FIXME timeout
        return holder

    def release(self, holder):
        '''
        Used to release an RWWith holder
        ( you probably shouldn't use this )
        '''
        with self.lock:

            if holder.writer:
                self.rw_holder = None

                # a write lock release should free readers first...
                if self.ro_waiters:
                    while self.ro_waiters:
                        nexthold = self.ro_waiters.popleft()
                        self.ro_holders.add(nexthold)
                        hexthold.event.set()
                    return

                if self.rw_waiters:
                    nexthold = self.rw_waiters.popleft()
                    self.rw_holder = nexthold
                    nexthold.event.set()
                    return

                return

            # releasing a read hold from here down...
            self.ro_holders.remove(holder)
            if self.ro_holders:
                return

            # the last reader should release a writer first
            if self.rw_waiters:
                nexthold = self.rw_waiters.popleft()
                self.rw_holder = nexthold
                nexthold.event.set()
                return

            # there should be no waiting readers here...
            return

class RWWith:
    '''
    The RWWith class implements "with block" syntax for RWLock.
    '''

    def __init__(self, rwlock):
        self.event = threading.Event()
        self.writer = False
        self.rwlock = rwlock

    def __enter__(self):
        return self

    def __exit__(self, exclass, exc, tb):
        self.rwlock.release(self)

def iCantWait(name=None):
    '''
    Mark the current thread as a no-wait thread.

    Any no-wait thread will raise MustNotWait on blocking calls
    within synapse APIs to prevent deadlock bugs.

    Example:

        iCantWait(name='FooThread')

    '''
    curthr = threading.currentThread()
    curthr._syn_cantwait = True

    if name is not None:
        curthr.name = name

def iWillWait():
    '''
    Check if the current thread is a marked no-wait thead and raise MustNotWait.

    Example:

        def doBlockingThing():
            iWillWait()
            waitForThing()

    '''
    if getattr(threading.currentThread(), '_syn_cantwait', False):
        name = threading.currentThread().name
        raise s_common.MustNotWait(name)

def iMayWait():
    '''
    Function for no-wait aware APIs to use while handling no-wait threads.

    Example:

        def mayWaitThing():
            if not iMayWait():
                return False

            waitForThing()

    '''
    return not getattr(threading.currentThread(), '_syn_cantwait', False)
