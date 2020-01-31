import contextlib
from typing import List, Dict, Any, Callable, Tuple

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.queue as s_queue

class RegMethType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _regclsfuncs
    '''
    def __init__(cls, name: str, bases: List[type], attrs: Dict[str, Any]):
        # Start with my parents' definitions
        cls._regclsfuncs = sum((getattr(scls, '_regclsfuncs', []) for scls in bases), [])

        # Add my own definitions
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._regclsfuncs.append(prop)

class NexsRoot(s_base.Base):
    async def __anit__(self, dirn: str):
        await s_base.Base.__anit__(self)

        import synapse.lib.lmdbslab as s_lmdbslab
        import synapse.lib.slabseqn as s_slabseqn

        self.dirn = dirn
        self._nexskids: Dict[str, 'Pusher'] = {}

        self.windows = []

        path = s_common.genpath(self.dirn, 'changelog.lmdb')
        self.changeslab = await s_lmdbslab.Slab.anit(path)

        async def fini():
            await self.changeslab.fini()
            [(await wind.fini()) for wind in self.windows]

        self.onfini(fini)

        self.changelog = s_slabseqn.SlabSeqn(self.changeslab, 'changes')

    async def issue(self, nexsiden: str, event: str, args: Any, kwargs: Any) -> Any:
        # Log the message here
        item = (nexsiden, event, args, kwargs)

        indx = self.changelog.append(item)
        [(await wind.put((indx, item))) for wind in tuple(self.windows)]

        nexus = self._nexskids[nexsiden]
        return await nexus._nexshands[event](nexus, *args, **kwargs)

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        '''
        Called from an external API
        '''
        nexus = self._nexskids[nexsiden]
        return await nexus._push(event, *args, **kwargs)

    def getOffset(self):
        return self.changelog.index()

    async def iter(self, offs: int):
        for item in self.changelog.iter(offs):
            yield item

        async with self.getChangeWindow() as wind:
            async for item in wind:
                yield item

    @contextlib.asynccontextmanager
    async def getChangeWindow(self):

        async with await s_queue.Window.anit(maxsize=10000) as wind:

            async def fini():
                self.windows.remove(wind)

            wind.onfini(fini)

            self.windows.append(wind)

            yield wind

class Pusher(s_base.Base, metaclass=RegMethType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regclsfuncs: List[Tuple[str, Callable]] = []

    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore
        await s_base.Base.__anit__(self)
        self._nexshands: Dict[str, Callable] = {}

        self._nexsiden = iden

        if nexsroot:
            assert iden
            nexsroot._nexskids[iden] = self

            def onfini():
                prev = nexsroot._nexskids.pop(iden, None)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = nexsroot

        for event, func in self._regclsfuncs:  # type: ignore
            self._nexshands[event] = func

    @classmethod
    def onPush(cls, event: str) -> Callable:
        '''
        Decorator that registers a method to be a handler for a named event
        '''
        def decorator(func):
            func._regme = (event, func)
            return func

        return decorator

    async def _push(self, event: str, *args: List[Any], **kwargs: Dict[str, Any]) -> Any:
        '''
        Execute the change handler for the mesg

        Note:
            This method is considered 'protected', in that it should not be called from something other than self.
        '''
        nexsiden = self._nexsiden
        if self._nexsroot:  # I'm below the root
            return await self._nexsroot.issue(nexsiden, event, args, kwargs)

        # There's not change dist
        return await self._nexshands[event](self, *args, **kwargs)
