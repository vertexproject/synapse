from __future__ import absolute_import,unicode_literals

import threading

import synapse.glob as s_glob

from synapse.compat import sched
from synapse.eventbus import EventBus

from synapse.common import *

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

def getGlobSched():
    '''
    Retrieve a reference to a global scheduler.
    '''
    if s_glob.sched != None:
        return s_glob.sched

    with s_glob.lock:
        if s_glob.sched == None:
            s_glob.sched = Sched()
    
    return s_glob.sched
