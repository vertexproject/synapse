import os
import time
import queue
import functools
import threading
import traceback

from synapse.dispatch import Dispatcher

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

class ThreadBoss(Dispatcher):
    '''
    A thread manager for firing and cleaning up threads.
    '''
    def __init__(self):
        Dispatcher.__init__(self)
        self.threads = {}

        self.synOn('fini', self._finiThreadBoss )
        self.synOn('thread:init', self._initThread)
        self.synOn('thread:fini', self._finiThread)

    def worker(self, meth, *args, **kwargs):
        self._runWorkThread(meth,args,kwargs)

    def _initThread(self, thr):
        self.threads[thr.ident] = thr

    def _finiThread(self, thr):
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
        self.synFire('thread:init',thread)
        try:
            return meth(*args,**kwargs)
        finally:
            self.synFire('thread:fini',thread)

