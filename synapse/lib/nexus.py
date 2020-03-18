import asyncio
import logging
import functools
import contextlib

from typing import List, Dict, Any, Callable, Tuple, Optional, AsyncIterator

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro

logger = logging.getLogger(__name__)

# As a mirror follower, amount of time to wait at startup for connection to leader
FOLLOWER_START_WAIT_S = 10.0

# As a mirror follower, amount of time before giving up on a write request
FOLLOWER_WRITE_WAIT_S = 30.0

NexusLogEntryT = Tuple[str, str, List[Any], Dict[str, Any]] # (nexsiden, event, args, kwargs)


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
    '''
    A utility class to distribute new change entries to mirrors/followers
    '''
    async def __anit__(self, nexuslog: Any, offs: int):  # type: ignore
        await s_base.Base.__anit__(self)
        self.event = asyncio.Event()
        self.nexuslog = nexuslog
        self.offs = offs

        async def fini() -> None:
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

    def update(self) -> bool:
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
        self._nexskids: Dict[str, 'Pusher'] = {}

        self.mirrors: List[ChangeDist] = []
        self.dologging = dologging

        # These are used when this cell is a mirror.
        self.ldrurl: Optional[str] = None
        self.ldr: Optional[s_telepath.Proxy] = None  # only set by looptask
        self.looptask: Optional[asyncio.Task] = None
        self.ldrready = asyncio.Event()

        if self.dologging:
            path = s_common.genpath(self.dirn, 'slabs', 'nexus.lmdb')
            self.nexusslab = await s_lmdbslab.Slab.anit(path, map_async=False)
            self.nexuslog = s_slabseqn.SlabSeqn(self.nexusslab, 'nexuslog')

        async def fini():
            if self.looptask:
                self.looptask.cancel()

            if self.ldr:
                self.ldrready.clear()
                await self.ldr.fini()

            if self.dologging:
                await self.nexusslab.fini()

            [(await dist.fini()) for dist in self.mirrors]

        self.onfini(fini)

    async def issue(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        '''
        If I'm not a follower, mutate, otherwise, ask the leader to make the change and return the offset with the
        change to wait for
        '''
        if not self.ldrurl:
            return await self.eat(nexsiden, event, args, kwargs)

        live = await s_coro.event_wait(self.ldrready, FOLLOWER_WRITE_WAIT_S)
        if not live:
            raise s_exc.LinkErr(mesg='Mirror cannot reach leader for write request')

        assert self.ldr is not None

        return await self.ldr.issue(nexsiden, event, args, kwargs)

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        '''
        Actually mutate for the given nexsiden instance.
        '''
        item: NexusLogEntryT = (nexsiden, event, args, kwargs)

        if self.dologging:
            indx = self.nexuslog.add(item)
        else:
            indx = 0

        [dist.update() for dist in tuple(self.mirrors)]

        nexsiden, event, args, kwargs = item

        nexus = self._nexskids[nexsiden]
        func = nexus._nexshands[event]

        return indx, await func(nexus, *args, **kwargs)

    def getOffset(self) -> int:
        '''
        Returns the next offset that would be written.
        '''
        if not self.dologging:
            return 0

        return self.nexuslog.index()

    async def waitForOffset(self, offs: int, timeout=None) -> None:
        '''
        Pends current asyncio task until either the entry at offset offs is written or the timeout occurs.
        '''
        if not self.dologging:
            return

        return await self.nexuslog.waitForOffset(offs, timeout=timeout)

    def getOffsetEvent(self, offs: int) -> asyncio.Event:
        '''
        Returns an asyncio.Event that is set when the offset is written.  The returned event will already be set if
        the offset has already been written.
        '''
        if not self.dologging:
            evnt = asyncio.Event()
            evnt.set()
            return evnt

        return self.nexuslog.getOffsetEvent(offs)

    async def iter(self, offs: int) -> AsyncIterator[Any]:
        '''
        Returns an iterator of change entries in the log
        '''
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
    async def getChangeDist(self, offs: int) -> AsyncIterator[ChangeDist]:

        async with await ChangeDist.anit(self.nexuslog, offs) as dist:

            async def fini():
                self.mirrors.remove(dist)

            dist.onfini(fini)

            self.mirrors.append(dist)

            yield dist

    async def setLeader(self, url: Optional[str], iden: str) -> None:
        '''
        Args:
            url:  if None, sets this nexsroot as leader, otherwise the telepath URL of the leader
            iden: iden of the leader.  Should be the same as my containing cell's iden
        '''
        if url is not None and not self.dologging:
            raise s_exc.BadConfValu(mesg='Mirroring incompatible without logchanges')

        if self.ldrurl == url:
            return

        self.ldrurl = url

        if self.looptask is not None:
            self.looptask.cancel()
            self.looptask = None
            self.ldrready.clear()
            if self.ldr is not None:
                await self.ldr.fini()
            self.ldr = None

        if self.ldrurl is None:
            return

        self.looptask = self.schedCoro(self._followerLoop(iden))
        connected = await s_coro.event_wait(self.ldrready, FOLLOWER_START_WAIT_S)
        if not connected:
            logger.warning('Failed to connect to mirror leader {s}.  Continuing to retry.', self.ldrurl)

    async def _followerLoop(self, iden) -> None:

        while not self.isfini:

            try:
                self.ldrready.clear()
                self.ldr = None

                async with await s_telepath.openurl(self.ldrurl) as proxy:
                    self.ldr = proxy
                    self.ldrready.set()

                    # if we really are a mirror/follower, we have the same iden.
                    if iden != await proxy.getCellIden():
                        logger.error('remote cortex has different iden! (aborting follower, shutting down cortex.).')
                        await self.fini()
                        return

                    logger.warning(f'mirror loop ready ({self.ldrurl} offset={self.getOffset()})')

                    while not proxy.isfini:

                        offs = self.getOffset()

                        # pump them into a queue so we can consume them in chunks
                        q: asyncio.Queue[Tuple[int, NexusLogEntryT]] = asyncio.Queue(maxsize=1000)

                        async def consume(x):
                            try:
                                async for item in proxy.getNexusChanges(x):
                                    await q.put(item)
                            finally:
                                await q.put(None)

                        proxy.schedCoro(consume(offs))

                        done = False
                        while not done:

                            # get the next item so we maybe block...
                            item = await q.get()
                            if item is None:
                                break

                            items = [item]

                            # check if there are more we can eat
                            for _ in range(q.qsize()):

                                nexi = await q.get()
                                if nexi is None:
                                    done = True
                                    break

                                items.append(nexi)

                            for offs, args in items:
                                assert offs == self.nexuslog.index()
                                await self.eat(*args)

            except asyncio.CancelledError: # pragma: no cover
                return

            except Exception:
                logger.exception('error in initCoreMirror loop')

            await self.waitfini(1)

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
            setattr(cls, '_hndl' + func.__name__, func)
            functools.update_wrapper(pushfunc, func)
            return pushfunc

        return decorator

    async def _push(self, event: str, *args: Any, **kwargs: Any) -> Any:
        '''
        Execute the change handler for the mesg

        Note:
            This method is considered 'protected', in that it should not be called from something other than self.
        '''
        nexsiden = self.nexsiden

        if self.nexsroot is not None:  # Distribute through the change root
            offs, retn = await self.nexsroot.issue(nexsiden, event, args, kwargs)
            await self.nexsroot.waitForOffset(offs)
            return retn

        # There's no change distribution, so directly execute
        return await self._nexshands[event](self, *args, **kwargs)
