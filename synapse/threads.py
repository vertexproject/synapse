import os
import time
import queue
import sched
import functools
import threading
import traceback

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

        self.synOn('thread:init', self._initThread)
        self.synOn('thread:fini', self._finiThread)
        self.synOnFini(self._finiThreadBoss)

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
        self.synFire('thread:init',thread=thread)
        try:
            return meth(*args,**kwargs)
        finally:
            self.synFire('thread:fini',thread=thread)

class Sched(EventBus):
    '''
    Wrap python's scheduler to support fire/forget and cleanup.
    '''
    def __init__(self):
        EventBus.__init__(self)
        self.sema = threading.Semaphore()
        self.sched = sched.scheduler()
        self.thr = self._runSchedMain()
        self.synOnFini(self._finiSched)

    @firethread
    def _runSchedMain(self):
        while not self.isfini:
            try:

                self.sema.acquire()
                self.sched.run()

            except Exception as e:
                traceback.print_exc()

    def synIn(self, delay, meth, *args, **kwargs):
        '''
        Schedule a callback to occur in delay seconds.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            e = sched.synIn(10, woot, 10, 20)

            # woot will be called in 10 seconds..

        '''
        event = self.sched.enter(delay, 1, meth, args, kwargs)
        self.sema.release()
        return event

    def synCancel(self, event):
        '''
        Cancel a previously scheduled call.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            e = sched.synIn(10, woot, 10, 20)

            sched.synCancel(e)

        '''
        self.sched.cancel(event)

    def _finiSched(self):
        [ self.sched.cancel(e) for e in self.sched.queue ]
        self.sema.release()
        self.thr.join()
