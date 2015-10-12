import os
import time
import sched
import functools
import threading
import traceback

import synapse.glob as s_glob

from synapse.compat import queue

from synapse.common import *
from synapse.eventbus import EventBus

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

