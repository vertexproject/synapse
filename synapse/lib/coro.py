'''
Async/Coroutine related utilities.
'''
import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob

class Anit:
    '''
    Base class for async initialization.

    Example:

        class Foo(Anit):

            def __init__(self, x):
                self.x = x

            async def __anit__(self):
                await stuff()

        foo = await Foo.anit(10)

    '''
    @classmethod
    async def anit(ctor, *args, **kwargs):
        self = ctor(*args, **kwargs)
        await self.__anit__()
        return self

def iscoro(item):
    if isinstance(item, (types.AsyncGeneratorType, types.GeneratorType)):
        return False
    return asyncio.iscoroutine(item)

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
        Add an item to the queue.
        '''
        if self.isfini:
            return False

        self.fifo.append(item)

        if len(self.fifo) == 1:
            self.event.set()

        return True

    async def slice(self):

        # sync interface to the async queue
        if len(self.fifo) == 0:
            await self.event.wait()

        retn = list(self.fifo)
        self.fifo.clear()
        self.event.clear()
        return retn

class Genr(Fini):
    '''
    Wrap an async generator for use by a potentially sync caller.
    '''
    def __init__(self, genr):
        Fini.__init__(self)
        self.genr = genr

    def __len__(self):
        return sum(1 for n in self)

    def __iter__(self):

        if s_glob.plex.iAmLoop():
            raise Exception('TODO')

        while not self.isfini:
            try:
                yield s_glob.sync(self.genr.__anext__())
            except StopAsyncIteration as e:
                return

    async def __aiter__(self):

        while not self.isfini:
            try:
                yield await self.genr.__anext__()
            except StopAsyncIteration as e:
                return

def generator(f):
    def wrap(*args, **kwargs):
        return Genr(f(*args, **kwargs))
    return wrap
