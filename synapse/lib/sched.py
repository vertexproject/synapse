import time
import atexit
import logging
import threading
import traceback

logger = logging.Logger(__name__)

import synapse.common as s_common

import synapse.lib.task as s_task
import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

class Sched(EventBus):

    def __init__(self, pool=None):

        EventBus.__init__(self)

        if pool is None:
            pool = s_threads.Pool()

        self.pool = pool
        self.root = None

        self.lock = threading.Lock()
        self.wake = threading.Event()

        self.thr = self._runSchedMain()
        self.onfini(self._onSchedFini)

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
        work = (func, args, kwargs)
        mine = [ts, work, None]

        with self.lock:

            # if no root, we're it!
            if self.root is None:
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
                if step[2] is None:
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
        return self.at(time.time() + delay, func, *args, **kwargs)

    def persec(self, count, func, *args, **kwargs):
        '''
        Schedule a callback to occur count times per second.

        Args:
            count: Number of times per second for this to occur. Either an int or a float.
            func: Function to execute.
            *args: Args passed to the function.
            **kwargs: Kwargs passed to the function.

        Examples:
            Scheduled a function to be called 10 times per second::

                def tenpersec(x,y=None):
                    blah()

                sched = Sched()
                sched.persec(10, tenpersec, 10, y='woot')

        Notes:
            This indefinitely calls the scheduled function until the function
            returns False or the Task is fini'd. See the Sched.loop function
            for more details.

        Returns:
            s_task.Task: A Task object representing the object's execution.
        '''
        secs = 1.0 / count
        return self.loop(secs, func, *args, **kwargs)

    def loop(self, secs, func, *args, **kwargs):
        '''
        Call the given function in a delay loop.

        Args:
            secs (int): Seconds between loop calls (can be float)
            func (function): The function to call
            args (list): The call arguments
            kwargs (dict): The call keyword arguments

        Examples:
            Scheduled a function to be called once every 10 seconds::

                def tensec(x,y=None):
                    blah()

                sched = Sched()
                sched.loop(10, tensec, 10, y='woot')

        Notes:
            If the function returns False, the loop will explicitly break.
            If the task object is isfini'd, the loop will explicitly break.
            In either of those scenarios, the task will not be scheduled for further execution.

        Returns:
            s_task.Task: A Task object representing the object's execution.
        '''
        task = s_task.Task()

        def run():

            if task.isfini:
                return

            try:

                if func(*args, **kwargs) is False:
                    task.fini()
                    return

            except Exception as e:
                logger.exception(e)

            if not self.isfini and not task.isfini:
                self.insec(secs, run)

        run()
        return task

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

    @s_common.firethread
    def _runSchedMain(self):
        for task in self.yieldTimeTasks():
            try:
                func, args, kwargs = task
                self.pool.call(func, *args, **kwargs)
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

            if item is not None:
                yield item
