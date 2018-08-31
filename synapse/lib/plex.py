import asyncio
import logging
import threading
import concurrent.futures

logger = logging.getLogger(__name__)

import synapse.eventbus as s_eventbus

import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.threads as s_threads

readsize = 10 * s_const.megabyte

class Plex(s_eventbus.EventBus):

    def __init__(self):

        s_eventbus.EventBus.__init__(self)

        self.loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop

        self.links = {}

        self.thrd = s_threads.worker(self._runIoLoop)
        self.ident = self.thrd.ident

        def fini():
            coro = self._onAsyncFini()
            try:
                self.coroToSync(coro, timeout=.05)
            except concurrent.futures.TimeoutError:
                pass
            self.thrd.join(.1)

        self.onfini(fini)

    def iAmLoop(self):
        '''
        Return True if the current thread is the Plex loop thread.

        Returns:
            (bool)

        '''
        return threading.get_ident() == self.ident

    async def link(self, host, port, ssl=None):
        '''
        Async connect and return a Link().
        '''
        reader, writer = await asyncio.open_connection(host, port, ssl=ssl)

        return self._initPlexLink(reader, writer)

    def connect(self, host, port, ssl=None, timeout=None):
        '''
        Connect to the remote host and return a Link.
        '''
        coro = self.link(host, port, ssl=ssl)
        return self.coroToSync(coro, timeout=timeout)

    def listen(self, host, port, onlink, ssl=None):
        '''
        Listen on the given host/port and fire onlink(Link).

        Returns a server object that contains the listening sockets
        '''
        async def onconn(reader, writer):

            link = self._initPlexLink(reader, writer)

            # if the onlink() function is a coroutine, task it.
            coro = onlink(link)
            if asyncio.iscoroutine(coro):
                await coro

        async def bind():
            server = await asyncio.start_server(onconn, host=host, port=port, ssl=ssl)
            return server

        coro = bind()
        return self.coroToSync(coro)

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
        return asyncio.run_coroutine_threadsafe(coro, loop=self.loop)

    def coroToSync(self, coro, timeout=None):
        '''
        Schedule a coro to run on this loop and return the result.

        NOTE: This API *is* thread safe
        '''
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

    async def sleep(self, delay):
        '''
        A coroutine that suspends for delay seconds.

        Args:
            delay (float): Time to delay the function call for.

        Notes:
            This API must be called on the IOLoop
        '''
        await asyncio.sleep(delay, loop=self.loop)

    async def _onAsyncFini(self):
        # async fini stuff here...
        self.loop.stop()

    def _initPlexLink(self, reader, writer):

        # init a Link from reader, writer

        link = s_link.Link(self, reader, writer)

        self.links[link.iden] = link

        def fini():
            self.links.pop(link.iden, None)

        link.onfini(fini)

        return link

    def initLinkLoop(self, link):
        '''
        Initialize the ioloop for the given link.
        '''
        self.addLoopCoro(self._linkRxLoop(link))

    def addLoopCoro(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def coroLoopTask(self, coro):
        '''
        Schedule the coro on the loop.

        Args:
            coro:

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

    async def _linkRxLoop(self, link):

        try:

            byts = await link.reader.read(readsize)

            while byts:

                for size, mesg in link.feed(byts):
                    await link.rx(mesg)

                byts = await link.reader.read(readsize)

        except BrokenPipeError as e:
            logger.warning('%s', str(e))

        except Exception as e:
            logger.exception('_linkRxLoop Error!')

        finally:
            await link.fini()

    def _runIoLoop(self):

        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()

        finally:
            self.loop.close()
