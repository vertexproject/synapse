import asyncio
import contextlib

from typing import List, Dict, Any, Callable, Tuple

import synapse.common as s_common

import synapse.lib.base as s_base

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

class ChangeDist(s_base.Base):
    async def __anit__(self, changelog, offs):
        await s_base.Base.__anit__(self)
        self.event = asyncio.Event()
        self.changelog = changelog
        self.offs = offs

        async def fini():
            self.event.set()

        self.onfini(fini)

    async def __aiter__(self):

        while True:

            for item in self.changelog.iter(self.offs):
                self.offs = item[0] + 1
                yield item

            if self.isfini:
                return

            self.event.clear()
            await self.event.wait()

    async def update(self):
        if self.isfini:
            return False

        self.event.set()
        return True

class NexsRoot(s_base.Base):
    async def __anit__(self, dirn: str):  # type: ignore
        await s_base.Base.__anit__(self)

        import synapse.lib.lmdbslab as s_lmdbslab  # avoid import cycle
        import synapse.lib.slabseqn as s_slabseqn  # avoid import cycle

        self.dirn = dirn
        self._nexskids: Dict[str, 'Pusher'] = {}

        self.mirrors: List[ChangeDist] = []

        path = s_common.genpath(self.dirn, 'changelog.lmdb')
        self.changeslab = await s_lmdbslab.Slab.anit(path)

        async def fini():
            await self.changeslab.fini()
            [(await dist.fini()) for dist in self.mirrors]

        self.onfini(fini)

        self.changelog = s_slabseqn.SlabSeqn(self.changeslab, 'changes')

    async def issue(self, nexsiden: str, event: str, args: Any, kwargs: Any) -> Any:
        item = (nexsiden, event, args, kwargs)

        nexus = self._nexskids[nexsiden]
        retn = await nexus._nexshands[event](nexus, *args, **kwargs)

        indx = self.changelog.append(item)
        [(await dist.update()) for dist in tuple(self.mirrors)]

        return retn

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        '''
        Called from an external API
        '''
        nexus = self._nexskids[nexsiden]
        return await nexus._push(event, *args, **kwargs)

    def getOffset(self):
        return self.changelog.index()

    async def iter(self, offs: int):
        maxoffs = offs

        for item in self.changelog.iter(offs):
            maxoffs = item[0] + 1
            yield item

        async with self.getChangeDist(maxoffs) as dist:
            async for item in dist:
                yield item

    @contextlib.asynccontextmanager
    async def getChangeDist(self, offs):

        async with await ChangeDist.anit(self.changelog, offs) as dist:

            async def fini():
                self.mirrors.remove(dist)

            dist.onfini(fini)

            self.mirrors.append(dist)

            yield dist

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
