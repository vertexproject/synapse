import asyncio
import functools
import contextlib

from typing import List, Dict, Any, Callable, Tuple

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base

class RegMethType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _regclstupls
    '''
    def __init__(cls, name: str, bases: List[type], attrs: Dict[str, Any]):
        # Start with my parents' definitions
        cls._regclstupls: List[Tuple[str, Callable, bool]] = \
            sum((getattr(scls, '_regclstupls', []) for scls in bases), [])

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

    async def __anit__(self, dirn: str, dologging: bool = True):  # type: ignore
        await s_base.Base.__anit__(self)

        import synapse.lib.lmdbslab as s_lmdbslab  # avoid import cycle
        import synapse.lib.slabseqn as s_slabseqn  # avoid import cycle

        self.dirn = dirn
        self.readonly = False
        self._nexskids: Dict[str, 'Pusher'] = {}

        self.mirrors: List[ChangeDist] = []
        self.dologging = dologging

        if self.dologging:
            path = s_common.genpath(self.dirn, 'slabs', 'nexus.lmdb')
            self.nexusslab = await s_lmdbslab.Slab.anit(path, map_async=False)
            self.nexuslog = s_slabseqn.SlabSeqn(self.nexusslab, 'nexuslog')

        async def fini():
            if self.dologging:
                await self.nexusslab.fini()
            [(await dist.fini()) for dist in self.mirrors]

        self.onfini(fini)

    async def issue(self, nexsiden: str, event: str, args: Any, kwargs: Any) -> Any:
        '''
        Issue a change event for the given nexsiden instance.
        '''
        item = (nexsiden, event, args, kwargs)

        if self.dologging:
            indx = self.nexuslog.add(item)
        else:
            indx = 0

        [dist.update() for dist in tuple(self.mirrors)]

        return await self._apply(indx, item)

    async def _apply(self, indx, item):

        nexsiden, event, args, kwargs = item

        nexus = self._nexskids[nexsiden]
        func = nexus._nexshands[event]

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
        if not self.dologging:
            return 0

        return self.nexuslog.index()

    async def waitForOffset(self, offs, timeout=None):
        if not self.dologging:
            return

        return await self.nexuslog.waitForOffset(offs, timeout=timeout)

    async def iter(self, offs: int):
        if not self.dologging:
            return

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
    _regclstupls: List[Tuple[str, Callable]] = []

    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore

        await s_base.Base.__anit__(self)
        self._nexshands: Dict[str, Callable] = {}

        self.nexsiden = iden
        self.nexsroot = None

        if nexsroot is not None:
            self.setNexsRoot(nexsroot)

        for event, func in self._regclstupls:  # type: ignore
            self._nexshands[event] = func

    def setNexsRoot(self, nexsroot):

        nexsroot._nexskids[self.nexsiden] = self

        def onfini():
            prev = nexsroot._nexskids.pop(self.nexsiden, None)
            assert prev is not None, f'Failed removing {self.nexsiden}'

        self.onfini(onfini)

        self.nexsroot = nexsroot

    @classmethod
    def onPush(cls, event: str) -> Callable:
        '''
        Decorator that registers a method to be a handler for a named event

        event: string that distinguishes one handler from another.  Must be unique per Pusher subclass
        '''
        def decorator(func):
            func._regme = (event, func)
            return func

        return decorator

    @classmethod
    def onPushAuto(cls, event: str) -> Callable:
        '''
        Decorator that does the same as onPush, except automatically creates the top half method
        '''
        async def pushfunc(self, *args, **kwargs):
            return await self._push(event, *args, **kwargs)

        def decorator(func):
            pushfunc._regme = (event, func)
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
        nexsiden = self.nexsiden
        if self.nexsroot is not None:  # Distribute through the change root
            if self.nexsroot.readonly:
                raise s_exc.IsReadOnly()

            offs, retn = await self.nexsroot.issue(nexsiden, event, args, kwargs)
            await self.nexsroot.waitForOffset(offs)
            return retn

        # There's no change distribution, so directly execute
        return await self._nexshands[event](self, *args, **kwargs)
