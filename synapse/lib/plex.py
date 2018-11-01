import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

import synapse.eventbus as s_eventbus

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.threads as s_threads

class Plex(s_eventbus.EventBus):

    def __init__(self):

        s_eventbus.EventBus.__init__(self)

        self.loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop

        self.links = {}

        self.thrd = s_threads.worker(self._runIoLoop)
        self.thrd.setName('SynPlex')

        self.ident = self.thrd.ident

        def fini():
            self.callSoonSafe(self.loop.stop)
            self.thrd.join(0.3)

        self.onfini(fini)

    def iAmLoop(self):
        '''
        Return True if the current thread is the Plex loop thread.

        Returns:
            (bool)

        '''
        return threading.get_ident() == self.ident

    def coroToTask(self, coro):
        '''
        Schedule a coro to run on this loop and return a task.

        Args:
            coro (coroutine): The coroutine instance.

        Notes:
            This API is thread safe.

        Returns:
            concurrent.futures.Future: A Future to wait on.
        '''
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def coroToSync(self, coro, timeout=None):
        '''
        Schedule a coro to run on this loop and return the result.

        NOTE: This API *is* thread safe.

        NOTE: This function must *not* be run from inside the event loop
        '''
        if self.iAmLoop():
            raise s_exc.AlreadyInAsync()

        task = self.coroToTask(coro)
        return task.result(timeout=timeout)

    async def executor(self, func, *args, **kwargs):
        '''
        Execute a function in an executor thread.

        Args:
            todo ((func,args,kwargs)): A todo tuple.
        '''
        def syncfunc():
            return func(*args, **kwargs)

        return await self.loop.run_in_executor(None, syncfunc)

    def coroLoopTask(self, coro):
        '''
        Schedule the coro on the loop.

        Args:
            coro: Coroutine to turn into a task.

        Notes:
            This is not thread safe It should only be called from inside
            the ioloop.

        Returns:
            asyncio.Task: An asyncio.Task object for the coro.
        '''
        return self.loop.create_task(coro)

    def callSoonSafe(self, func):
        return self.loop.call_soon_threadsafe(func)

    def callLater(self, delay, func):
        '''
        Arrange for the function to be called after a given delay.

        Args:
            delay (float): Time to delay the function call for.
            func: Function to call.

        Notes:
            This API is thread safe, as it wraps the underlying ``call_later()``
            via ``call_soon_threadsafe()``. Functions requiring args or kwargs
            should be wrapped via ``functools.partial()``.

        Examples:
            Call a function with a 5 second delay:

                s_glob.plex.callLater(5, func)

            Call a wrapped function using functools.partial:

                import functools
                partial = functools.partial(someFunc, someArg, key=2)
                s_glob.plex.callAt(5, partial)

        Returns:
            None
        '''
        def _func():
            self.loop.call_later(delay, func)

        self.callSoonSafe(_func)

    def callAt(self, when, func):
        '''
        Arrange for the function to be called at a later time.  The time
        reference for this is the IOLoop's time.

        Args:
            when (float): Time to call the function at.
            func: Function to call.

        Notes:
            This API is thread safe, as it wraps the underlying ``call_at()``
            via ``call_soon_threadsafe()``. Functions requiring args or kwargs
            should be wrapped via ``functools.partial()``.

        Examples:
            Call a function 60 seconds from the current loop time:

                t0 = s_glob.plex.time()
                s_glob.plex.callAt(t0 + 60, func)

            Call a wrapped function using functools.partial:

                import functools
                partial = functools.partial(someFunc, someArg, key=2)
                t0 = s_glob.plex.time()
                s_glob.plex.callAt(t0 + 60, partial)

        Returns:
            None
        '''
        def _func():
            self.loop.call_at(when, func)

        self.callSoonSafe(_func)

    def time(self):
        '''
        Get the current loop time.

        Notes:
            This is the loop's monotonically increasing time. It is not a
            substitute for ``time.time``.

        Returns:
            float: The current loop time.
        '''
        return self.loop.time()

    def _runIoLoop(self):

        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()

        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
