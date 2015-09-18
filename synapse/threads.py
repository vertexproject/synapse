import os
import time
import sched
import functools
import threading
import traceback

from synapse.compat import queue
from synapse.compat import sched

from synapse.eventbus import EventBus

def worker(meth, *args, **kwargs):
    thr = threading.Thread(target=meth,args=args,kwargs=kwargs)
    thr.setDaemon(True)
    thr.start()
    return thr

def firethread(f):
    @functools.wraps(f)
    def callmeth(*args,**kwargs):
        thr = worker(f,*args,**kwargs)
        return thr
    return callmeth

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

class ThreadBoss(EventBus):
    '''
    A thread manager for firing and cleaning up threads.

    EventBus Events:

        ('thread:init',{'thread':<thread>})
        ('thread:fini',{'thread':<thread>})

    '''
    def __init__(self):
        EventBus.__init__(self)
        self.threads = {}

        self.on('thread:init', self._initThread)
        self.on('thread:fini', self._finiThread)
        self.onfini(self._finiThreadBoss)

    def worker(self, meth, *args, **kwargs):
        '''
        Fire and manage a worker thread for the given call.

        Example:

            class Foo():
                def bar(self, x, y):
                    stuff()

            foo = Foo()

            boss = ThreadBoss()
            boss.worker(foo.bar, 10, 20)

        '''
        self._runWorkThread(meth,args,kwargs)

    def _initThread(self, event):
        thr = event[1].get('thread')
        self.threads[thr.ident] = thr

    def _finiThread(self, event):
        thr = event[1].get('thread')
        self.threads.pop(thr.ident,None)

    def _finiThreadBoss(self):
        pass
        #for thr in list(self.threads.values()):
            #print(thr)
            #print(threading.currentThread())
            #thr.join()

    @firethread
    def _runWorkThread(self, meth, args, kwargs):
        thread = threading.currentThread()
        self.fire('thread:init',thread=thread)
        try:
            return meth(*args,**kwargs)
        finally:
            self.fire('thread:fini',thread=thread)

class Sched(EventBus):
    '''
    Wrap python's scheduler to support fire/forget and cleanup.
    '''
    def __init__(self):
        EventBus.__init__(self)
        self.sema = threading.Semaphore()
        self.sched = sched.scheduler()
        self.thr = self._runSchedMain()
        self.onfini(self._finiSched)

    @firethread
    def _runSchedMain(self):
        while not self.isfini:
            try:

                self.sema.acquire()
                self.sched.run()

            except Exception as e:
                traceback.print_exc()

    def insec(self, delay, meth, *args, **kwargs):
        '''
        Schedule a callback to occur in delay seconds.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            e = sched.insec(10, woot, 10, 20)

            # woot will be called in 10 seconds..

        '''
        event = self.sched.enter(delay, 1, meth, args, kwargs)
        self.sema.release()
        return event

    def persec(self, count, meth, *args, **kwargs):
        '''
        Scedule a callback to occur count times per second.

        Example:

            def tenpersec(x,y=None):
                blah()

            sched = Sched()
            sched.persec(10, tenpersec, 10, y='woot')
        '''
        dt = 1.0 / count
        def cb():
            try:

                ret = meth(*args,**kwargs)
                if ret == False:
                    return

            except Exception as e:
                self.fire('err:exc', exc=e, msg='persec fail: %s' % (meth,))

            if not self.isfini:
                self.insec(dt,cb)

        cb()

    def cancel(self, event):
        '''
        Cancel a previously scheduled call.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            e = sched.insec(10, woot, 10, 20)

            sched.cancel(e)

        '''
        self.sched.cancel(event)

    def _finiSched(self):
        pass
        # FIXME
        #[ self.sched.cancel(e) for e in self.sched.queue ]
        #self.sema.release()
        #self.thr.join()
