'''
Async/Coroutine related utilities.
'''
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob

class Fini:

    def __init__(self):
        self.finis = []
        self.isfini = False
        self.entered = False
        self.exitinfo = None

    def onfini(self, corofunc):
        '''
        Add a *coroutine* function to be called on fini().
        '''
        self.finis.append(corofunc)

    async def fini(self):
        '''
        Shut down the object and notify any onfini() coroutines.
        '''
        if self.isfini:
            return

        self.isfini = True

        for fini in self.finis:

            try:

                valu = fini()
                if asyncio.iscoroutine(valu):
                    await valu

            except Exception as e:
                logger.exception('fini failed')

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc, cls, tb):
        self.exitinfo = (exc, cls, tb)
        await self.fini()

    def __enter__(self):
        return s_glob.sync(self.__aenter__())

    def __exit__(self, exc, cls, tb):
        s_glob.sync(self.__aexit__(exc, cls, tb))

    def _isExitExc(self):
        # if entered but not exited *or* exitinfo has exc
        if not self.entered:
            return False

        if self.exitinfo is None:
            return True

        return self.exitinfo[0] is not None

class Queue(Fini):
    '''
    An async queue with chunk optimized sync compatible consumer.
    '''
    def __init__(self):
        Fini.__init__(self)
        self.fifo = []
        self.event = asyncio.Event()

    async def fini(self):
        self.event.set()
        return await Fini.fini(self)

    def put(self, item):
        '''
        Add an item to the queue (async only).
        '''
        if self.isfini:
            return

        self.fifo.append(item)

        if len(self.fifo) == 1:
            self.event.set()

    async def slice(self):

        # sync interface to the async queue
        if len(self.fifo) == 0:
            await self.event.wait()

        retn = list(self.fifo)
        self.fifo.clear()
        self.event.clear()
        return retn
