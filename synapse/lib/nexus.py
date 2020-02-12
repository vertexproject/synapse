import asyncio
import functools
import contextlib

from typing import List, Dict, Any, Callable, Tuple

import synapse.common as s_common

import synapse.lib.base as s_base

class RegMethType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _regclstupls
    '''
    def __init__(cls, name: str, bases: List[type], attrs: Dict[str, Any]):
        # Start with my parents' definitions
        cls._regclstupls = sum((getattr(scls, '_regclstupls', []) for scls in bases), [])

        # Add my own definitions
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._regclstupls.append(prop)

class ChangeDist(s_base.Base):
    async def __anit__(self, nexuslog, offs):
        await s_base.Base.__anit__(self)
        self.event = asyncio.Event()
        self.nexuslog = nexuslog
        self.offs = offs

        async def fini():
            self.event.set()

        self.onfini(fini)

    async def __aiter__(self):

        while not self.isfini:

            for item in self.nexuslog.iter(self.offs):
                self.offs = item[0] + 1
                yield item

            if self.isfini:
                return

            self.event.clear()
            await self.event.wait()

    def update(self):
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

        path = s_common.genpath(self.dirn, 'nexus.lmdb')
        self.nexusslab = await s_lmdbslab.Slab.anit(path)

        async def fini():
            await self.nexusslab.fini()
            [(await dist.fini()) for dist in self.mirrors]

        self.onfini(fini)

        self.nexuslog = s_slabseqn.SlabSeqn(self.nexusslab, 'nexuslog')

    async def issue(self, nexsiden: str, event: str, args: Any, kwargs: Any) -> Any:
        item = (nexsiden, event, args, kwargs)

        nexus = self._nexskids[nexsiden]
        indx = self.nexuslog.add(item)
        [dist.update() for dist in tuple(self.mirrors)]

        func, passoff = nexus._nexshands[event]
        if passoff:
            return indx, await func(nexus, *args, nexsoff=indx, **kwargs)

        return indx, await func(nexus, *args, **kwargs)

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        '''
        Called from an external API
        '''
        nexus = self._nexskids[nexsiden]
        return await nexus._push(event, *args, **kwargs)

    def getOffset(self):
        '''
        Returns the next offset that would be written
        '''
        return self.nexuslog.index()

    async def iter(self, offs: int):
        maxoffs = offs

        for item in self.nexuslog.iter(offs):
            maxoffs = item[0] + 1
            yield item

        async with self.getChangeDist(maxoffs) as dist:
            async for item in dist:
                yield item

    @contextlib.asynccontextmanager
    async def getChangeDist(self, offs):

        async with await ChangeDist.anit(self.nexuslog, offs) as dist:

            async def fini():
                self.mirrors.remove(dist)

            dist.onfini(fini)

            self.mirrors.append(dist)

            yield dist

class Pusher(s_base.Base, metaclass=RegMethType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regclstupls: List[Tuple[str, Callable, bool]] = []

    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore
        await s_base.Base.__anit__(self)
        self._nexshands: Dict[str, Tuple[Callable, bool]] = {}

        self._nexsiden = iden

        if nexsroot:
            assert iden
            nexsroot._nexskids[iden] = self

            def onfini():
                prev = nexsroot._nexskids.pop(iden, None)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = nexsroot

        for event, func, passoff in self._regclstupls:  # type: ignore
            self._nexshands[event] = func, passoff

    @classmethod
    def onPush(cls, event: str, passoff=False) -> Callable:
        '''
        Decorator that registers a method to be a handler for a named event

        event: string that distinguishes one handler from another.  Must be unique per Nexus subclass
        postcb:  whether to pass the log offset as the parameter "nexsoff" into the handler
        '''
        def decorator(func):
            func._regme = (event, func, passoff)
            return func

        return decorator

    @classmethod
    def onPushAuto(cls, event: str, passoff=False) -> Callable:
        '''
        Decorator that does the same as onPush, except automatically creates the top half method
        '''
        async def pushfunc(self, *args, **kwargs):
            return await self._push(event, *args, **kwargs)

        def decorator(func):
            pushfunc._regme = (event, func, passoff)
            setattr(cls, '_hndl' + func.__name__, pushfunc)
            functools.update_wrapper(pushfunc, func)
            return pushfunc

        return decorator

    async def _push(self, event: str, *args: List[Any], **kwargs: Dict[str, Any]) -> Any:
        '''
        Execute the change handler for the mesg

        Note:
            This method is considered 'protected', in that it should not be called from something other than self.
        '''
        nexsiden = self._nexsiden
        if self._nexsroot:  # Distribute through the change root
            offs, retn = await self._nexsroot.issue(nexsiden, event, args, kwargs)
            await self._nexsroot.nexuslog.waitForOffset(offs)
            return retn

        # There's no change distribution, so directly execute
        return await self._nexshands[event][0](self, *args, **kwargs)
