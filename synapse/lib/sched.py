from __future__ import absolute_import,unicode_literals

import time
import atexit
import threading

import synapse.glob as s_glob

from synapse.eventbus import EventBus

from synapse.common import *

class Sched(EventBus):

    def __init__(self):
        EventBus.__init__(self)

        self.root = None
        self.running = None

        self.lock = threading.Lock()
        self.wake = threading.Event()

        self.thr = self._runSchedMain()
        self.onfini( self._onSchedFini )

    def _onSchedFini(self):
        self.wake.set()
        self.thr.join()

    def at(self, ts, func, *args, **kwargs):
        '''
        Schedule a function to run at a specific time.

        Example:

            # call foo(bar,baz=10) at ts
            sched.at(ts, foo, bar, baz=10)

        '''
        task = (func,args,kwargs)
        mine = [ ts, task, None ]
        with self.lock:

            # if no root, we're it!
            if self.root == None:
                self.root = mine
                self.wake.set()
                return mine

            # if we're sooner, push and wake!
            if self.root[0] >= ts:
                mine[2] = self.root
                self.root = mine
                self.wake.set()
                return mine

            # we know we're past this one
            step = self.root
            while True:

                # if no next, we're it!
                if step[2] == None:
                    step[2] = mine
                    return mine

                # if we're sooner than next, insert!
                if step[2][0] > ts:
                    mine[2] = step[2]
                    step[2] = mine
                    return mine

                # move along to next
                step = step[2]

    def insec(self, delay, func, *args, **kwargs):
        '''
        Schedule a callback to occur in delay seconds.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            e = sched.insec(10, woot, 10, 20)

            # woot will be called in 10 seconds..

        '''
        return self.at( time.time() + delay, func, *args, **kwargs)

    def persec(self, count, func, *args, **kwargs):
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

                ret = func(*args,**kwargs)
                if ret == False:
                    return

            except Exception as e:
                self.fire('err:exc', exc=e, msg='persec fail: %s' % (func,))

            if not self.isfini:
                self.insec(dt,cb)

        cb()

    def cancel(self, item):
        '''
        Cancel a previously scheduled call.

        Example:

            def woot(x,y):
                stuff()

            sched = Sched()
            item = sched.insec(10, woot, 10, 20)

            sched.cancel(item)

        '''
        item[1] = None

    @firethread
    def _runSchedMain(self):
        for task in self.yieldTimeTasks():
            try:
                self.running = task
                func,args,kwargs = task
                func(*args,**kwargs)
                self.running = None
            except Exception as e:
                traceback.format_exc()

    def _getNextWait(self):
        timeout = None

        if self.root:
            timeout = self.root[0] - time.time()
            if timeout <= 0:
                timeout = 0

        return timeout

    def yieldTimeTasks(self):

        # a blocking yield generator for sched tasks
        while not self.isfini:

            with self.lock:
                timeout = self._getNextWait()
                self.wake.clear()

            if timeout != 0:
                self.wake.wait(timeout=timeout)

            if self.isfini:
                return

            item = None
            with self.lock:
                now = time.time()
                if self.root and self.root[0] <= now:
                    item = self.root[1]
                    self.root = self.root[2]

            if item != None:
                yield item

def getGlobSched():
    '''
    Retrieve a reference to a global scheduler.
    '''
    if s_glob.sched != None:
        return s_glob.sched

    with s_glob.lock:
        if s_glob.sched == None:
            s_glob.sched = Sched()
            atexit.register( s_glob.sched.fini )
    
    return s_glob.sched
