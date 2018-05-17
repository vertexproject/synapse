import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

import synapse.eventbus as s_eventbus

import synapse.glob as s_glob

import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.threads as s_threads

readsize = 10 * s_const.megabyte

class Plex(s_eventbus.EventBus):

    def __init__(self):

        s_eventbus.EventBus.__init__(self)

        self.loop = asyncio.new_event_loop()

        self.links = {}

        self.thrd = s_threads.worker(self._runIoLoop)
        self.ident = self.thrd.ident

        def fini():
            coro = self._onAsyncFini()
            self.coroToSync(coro, timeout=2)

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
        '''
        async def onconn(reader, writer):

            link = self._initPlexLink(reader, writer)

            # if the onlink() function is a coroutine, task it.
            coro = onlink(link)
            if asyncio.iscoroutine(coro):
                await coro

        async def bind():
            server = await asyncio.start_server(onconn, host=host, port=port, ssl=ssl)
            return server.sockets[0].getsockname()

        coro = bind()
        return self.coroToSync(coro)

    def coroToTask(self, coro):
        '''
        Schedule a coro to run on this loop and return a task.

        Args:
            coro (coroutine): The coroutine instance.

        Returns:
            (concurrent.futures.Task): A Future/Task to wait on.

        NOTE: This API *is* thread safe
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

    async def _onAsyncFini(self):
        # async fini stuff here...
        return

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
        self.loop.create_task(self._linkRxLoop(link))
        self.loop.create_task(self._linkTxLoop(link))

    def coroLoopTask(self, coro):
        '''
        Schedule the coro on the loop.

        NOTE: NOT THREAD SAFE. ONLY FROM IO LOOP.
        '''
        self.loop.create_task(coro)

    def callSoonSafe(self, func):
        return self.loop.call_soon_threadsafe(func)

    async def _linkRxLoop(self, link):

        try:

            byts = await link.reader.read(readsize)

            while byts:

                for size, mesg in link.feed(byts):
                    await link.rx(mesg)

                byts = await link.reader.read(readsize)

        except Exception as e:
            logger.exception('_linkRxLoop Error!')

        finally:
            await self.executor(link.fini)

    async def _linkTxLoop(self, link):

        try:

            while True:

                byts = await link.txque.get()
                if byts is None:
                    return

                link.writer.write(byts)
                await link.writer.drain()

        except Exception as e:
            logger.exception('_linkTxLoop Error!')

        finally:

            link.writer.close()
            s_glob.inpool(link.fini)()

    def _runIoLoop(self):

        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()

        finally:
            self.loop.close()
