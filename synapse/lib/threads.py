import os
import time
import sched
import atexit
import functools
import threading
import traceback

import synapse.glob as s_glob
import synapse.lib.queue as s_queue

from synapse.common import *
from synapse.eventbus import EventBus

class ScopeLocal:
    '''
    Allow a with block to add/remove a thread local by name

    Example:

        import syanpse.lib.threads as s_threads

        with s_threads.ScopeLocal('foo',thing):
            # deep caller may now...
            foo = s_threads.scope('foo')

    '''
    def __init__(self, **locs):
        self.olds = None
        self.locs = locs

    def __enter__(self):
        self.olds = { n:getattr(thrloc,n,None) for n in self.locs.keys() }
        [ setattr(thrloc,n,i) for (n,i) in self.locs.items() ]
        return self

    def __exit__(self, exc, cls, tb):
        [ setattr(thrloc,n,i) for (n,i) in self.olds.items() ]

class PerThread:
    '''
    A helper class for managing thread local variables.

    A PerThread instance may be used to register ctors
    which will fire when a thread attempts to retrieve
    a given per-thread variable.

    Example:

        per = PerThread()
        per.setPerCtor('woot', initwoot, 10, y=30)

        # Each thread has a differnt "woot"
        per.woot.doThing()

    '''
    def __init__(self):
        self.ctors = {}
        self.thrloc = threading.local()

    def setPerCtor(self, name, ctor, *args, **kwargs):
        '''
        Set a constructor for the give thread local variable.

        Example:

            class Woot:
                def dostuff(self, x, y):
                    return x + y

            per.setPerCtor('woot', Woot)

            # later, other threads...
            per.woot.dostuff(10,30)

        Notes:

        '''
        self.ctors[name] = (ctor,args,kwargs)

    def __getattr__(self, name):
        try:
            return getattr(self.thrloc,name)

        except AttributeError as e:
            ctor = self.ctors.get(name)
            if ctor == None:
                raise

            meth,args,kwargs = ctor
            valu = meth(*args,**kwargs)
            setattr(self.thrloc,name,valu)
            return valu

# setup a default PerThread
per = PerThread()
per.setPerCtor('monoq', s_queue.Queue)

thrloc = threading.local()
def local(key,defval=None):
    return getattr(thrloc,key,defval)

def current():
    return threading.currentThread()

def isfini():
    return getattr(current(),'isfini',False)

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
            self.func(*self.args,**self.kwargs)
        except Exception as e:
            traceback.print_exc()

    def __enter__(self):
        current().cancels.append( self )
        return self

    def __exit__(self, exc, cls, tb):
        current().cancels.pop()
        return

class Thread(threading.Thread,EventBus):
    '''
    A thread / EventBus to allow fini() etc.
    '''
    def __init__(self, func, *args, **kwargs):
        EventBus.__init__(self)

        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.iden = guidstr()
        self.task = (func,args,kwargs)

        self.cancels = []

        self.onfini( self._onThrFini )

    def run(self):
        func,args,kwargs = self.task
        ret = func(*args,**kwargs)
        self.fire('thread:done', thread=self, ret=ret)
        self.fini()

    def _onThrFini(self):
        [ cancel() for cancel in self.cancels ]

class MonoMeth:
    '''
    A "callable" used by the MonoThread object to proxy API calls.
    '''

    def __init__(self, mono, meth):
        self.mono = mono
        self.meth = meth

    def __call__(self, *args, **kwargs):
        q = per.monoq
        task = ( self.meth, args, kwargs)
        self.mono._mono_thrq.put( (task,q) )

        ret,exc = q.get()
        if exc != None:
            raise exc

        return ret

class MonoThread:
    '''
    Some APIs such as sqlite and most OS debug APIs are not ok
    with being called from more than one thread.  The MonoThread
    class will wrap an object such that all methods are called from
    only one thread.
    '''
    def __init__(self, item):
        self._mono_item = item
        self._mono_thrq = s_queue.Queue()
        self._mono_thrd = worker( self._runMonoThread )

        if isinstance(item, EventBus):
            item.onfini( self._onMonoFini )

    def _runMonoThread(self):

        while not self._mono_item.isfini:

            todo = self._mono_thrq.get()
            if todo == None:
                break

            task,retq = todo
            func,args,kwargs = task

            try:
                ret = func(*args,**kwargs)
                retq.put( (ret,None) )

            except Exception as e:
                retq.put( (None,e) )

    def _onMonoFini(self):
        self._mono_thrq.put( None )
        #self._mono_thrd.join()

    def __getattr__(self, name):
        meth = getattr(self._mono_item,name,None)
        if meth == None:
            raise AttributeError(name)

        ret = MonoMeth(self,meth)
        setattr(self,name,ret)
        return ret

class SafeMeth:
    '''
    A "callable" used by the ThreadSafe object to proxy API calls.
    '''

    def __init__(self, safe, meth):
        self.safe = safe
        self.meth = meth

    def __call__(self, *args, **kwargs):
        with self.safe._safe_lock:
            return self.meth(*args,**kwargs)

class ThreadSafe:
    '''
    The ThreadSafe class implements a mutual exclusion lock around method calls.


    Example:

        item = NotThreadSafeThing()

        safe = ThreadSafe(item)

        # from any thread....
        safe.doFooByBar(10)

        # no 2 threads will be in any NotThreadSafeThing method at one time

    '''

    def __init__(self, item):
        self._safe_item = item
        self._safe_lock = threading.Lock()

    def __getattr__(self, name):
        meth = getattr(self._safe_item,name,None)
        if meth == None:
            raise AttributeError(name)

        ret = SafeMeth(self,meth)
        setattr(self,name,ret)
        return ret

def worker(func,*args,**kwargs):
    '''
    Fire a worker thread to run the given func(*args,**kwargs)
    '''
    thr = Thread(func,*args,**kwargs)
    thr.start()
    return thr

def newtask(func, *args, **kwargs):
    return (func,args,kwargs)

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
        self._pool_maxsize = maxsize

        self._pool_threads = {}

        self.onfini( self._onPoolFini )

        for i in range(size):
            self._fire_thread( self._run_work )

    def call(self, func, *args, **kwargs):
        '''
        Call the given func(*args,**kwargs) in the pool.
        '''
        self.task( newtask(func,*args,**kwargs) )

    def task(self, task, jid=None):
        '''
        Run the given task in the pool.

        Example:
            task = newtask( x.getFooByBar, bar )
            pool.task(task, jid=None)

        Notes:

            * Specify jid=<iden> to generate job:done events.

        '''
        work = tufo(task, jid=jid)
        with self._pool_lock:

            if self.isfini:
                raise IsFini(self.__class__.__name__)

            # we're about to put work into the queue
            # lets see if we should also fire another worker

            # if there are available threads, no need to fire
            if self._pool_avail != 0:
                self.workq.put(work)
                return

            # if maxsize is none, nothing to do.
            if self._pool_maxsize == None:
                self.workq.put(work)
                return

            # got any breathing room?
            if self._pool_maxsize > len(self._pool_threads):
                self._fire_thread( self._run_work )
                self.workq.put(work)
                return

            # got *all* the breathing room?
            if self._pool_maxsize == -1:
                self._fire_thread( self._run_work )
                self.workq.put(work)
                return

            self.workq.put(work)

    def _fire_thread(self, func, *args, **kwargs):
        thr = Thread( func, *args, **kwargs)
        thr.link( self.dist )

        self._pool_threads[ thr.iden ] = thr

        def onfini():
            self._pool_threads.pop(thr.iden,None)

        thr.onfini(onfini)

        thr.start()
        return thr

    def _run_work(self):

        while not self.isfini:

            self._pool_avail += 1

            work = self.workq.get()

            self._pool_avail -= 1

            if work == None:
                return

            self.fire('pool:work:init', work=work)

            task,info = work

            jid = info.get('jid')
            try:

                func,args,kwargs = task
                ret = func(*args,**kwargs)

                # optionally generate a job event
                if jid != None:
                    self.fire('job:done',jid=jid,ret=ret)

            except Exception as e:

                if jid != None:
                    self.fire('job:done',jid=jid,**excinfo(e))

            self.fire('pool:work:fini', work=work)

    def _onPoolFini(self):
        threads = list(self._pool_threads.values())

        [ self.workq.put(None) for i in range(len(threads)) ]

        [ t.fini() for t in threads ]
        #[ t.join() for t in threads ]

def getGlobPool():
    '''
    Get/Init a reference to a singular global thread Pool().

    Example:

        plex = getGlobPool()

    '''
    with s_glob.lock:
        if s_glob.pool == None:
            s_glob.pool = Pool()

            atexit.register(s_glob.pool.fini)

        return s_glob.pool

def setGlobPool(pool):
    with s_glob.lock:
        s_glob.pool = pool

