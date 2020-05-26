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

# As a mirror follower, amount of time before giving up on a write request
FOLLOWER_WRITE_WAIT_S = 30.0

NexusLogEntryT = Tuple[str, str, List[Any], Dict[str, Any], Dict] # (nexsiden, event, args, kwargs, meta)


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

    async def __anit__(self, dirn: str, donexslog: bool = True):  # type: ignore
        await s_base.Base.__anit__(self)

        import synapse.lib.lmdbslab as s_lmdbslab  # avoid import cycle
        import synapse.lib.slabseqn as s_slabseqn  # avoid import cycle

        self.dirn = dirn
        self._nexskids: Dict[str, 'Pusher'] = {}

        self._mirrors: List[ChangeDist] = []
        self.donexslog = donexslog

        self._state_lock = asyncio.Lock()
        self._state_funcs: List[Callable] = [] # External Callbacks for state changes

        # These are used when this cell is a mirror.
        self._ldrurl: Optional[str] = None
        self._ldr: Optional[s_telepath.Proxy] = None  # only set by looptask
        self._looptask: Optional[asyncio.Task] = None
        self._ldrready = asyncio.Event()

        # Used to match pending follower write requests with the responses arriving on the log
        self._futures: Dict[str, asyncio.Future] = {}

        if self.donexslog:
            path = s_common.genpath(self.dirn, 'slabs', 'nexus.lmdb')
            self._nexusslab = await s_lmdbslab.Slab.anit(path, map_async=False)
            self._nexuslog = s_slabseqn.SlabSeqn(self._nexusslab, 'nexuslog')

        async def fini():
            if self._looptask:
                self._looptask.cancel()
                try:
                    await self._looptask
                except Exception:
                    pass

            for futu in self._futures.values():
                futu.cancel()

            if self._ldr:
                self._ldrready.clear()
                await self._ldr.fini()

            if self.donexslog:
                await self._nexusslab.fini()

            [(await dist.fini()) for dist in self._mirrors]

        self.onfini(fini)

    @contextlib.contextmanager
    def _getResponseFuture(self):

        iden = s_common.guid()
        futu = self.loop.create_future()

        self._futures[iden] = futu

        try:
            yield iden, futu

        finally:
            self._futures.pop(iden, None)

    async def recover(self) -> None:
        '''
        Replays the last entry in the nexus log in case we crashed between writing the log and applying it.

        Notes:
            This must be called at cell startup after subsystems are initialized but before any write transactions
            might happen.

            The log can only have recorded 1 entry ahead of what is applied.  All log actions are idempotent, so
            replaying the last action that (might have) already happened is harmless.
        '''
        if not self.donexslog:
            return

        indxitem: Optional[Tuple[int, NexusLogEntryT]] = self._nexuslog.last()
        if indxitem is None:
            # We have a brand new log
            return

        try:
            await self._apply(*indxitem)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception:
            logger.exception('Exception while replaying log')

    async def issue(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any],
                    meta: Optional[Dict] = None) -> Any:
        '''
        If I'm not a follower, mutate, otherwise, ask the leader to make the change and wait for the follower loop
        to hand me the result through a future.
        '''
        if not self._ldrurl:
            return await self.eat(nexsiden, event, args, kwargs, meta)

        live = await s_coro.event_wait(self._ldrready, FOLLOWER_WRITE_WAIT_S)
        if not live:
            raise s_exc.LinkErr(mesg='Mirror cannot reach leader for write request')

        assert self._ldr is not None

        with self._getResponseFuture() as (iden, futu):
            if meta is None:
                meta = {}
            meta['resp'] = iden

            await self._ldr.issue(nexsiden, event, args, kwargs, meta)
            return await asyncio.wait_for(futu, timeout=FOLLOWER_WRITE_WAIT_S)

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any],
                  meta: Optional[Dict] = None) -> Any:
        '''
        Actually mutate for the given nexsiden instance.
        '''
        if meta is None:
            meta = {}

        item: NexusLogEntryT = (nexsiden, event, args, kwargs, meta)

        if self.donexslog:
            indx = self._nexuslog.add(item)
        else:
            indx = None

        [dist.update() for dist in tuple(self._mirrors)]

        retn = await self._apply(indx, item)

        return retn

    async def _apply(self, indx: Optional[int], item: NexusLogEntryT):
        nexsiden, event, args, kwargs, _ = item

        nexus = self._nexskids[nexsiden]
        func, passoff = nexus._nexshands[event]
        if passoff:
            return await func(nexus, *args, nexsoff=indx, **kwargs)

        return await func(nexus, *args, **kwargs)

    async def iter(self, offs: int) -> AsyncIterator[Any]:
        '''
        Returns an iterator of change entries in the log
        '''
        if not self.donexslog:
            return

        if self.isfini:
            raise s_exc.IsFini()

        maxoffs = offs

        for item in self._nexuslog.iter(offs):
            if self.isfini:
                raise s_exc.IsFini()
            maxoffs = item[0] + 1
            yield item

        async with self.getChangeDist(maxoffs) as dist:
            async for item in dist:
                if self.isfini:
                    raise s_exc.IsFini()
                yield item

    @contextlib.asynccontextmanager
    async def getChangeDist(self, offs: int) -> AsyncIterator[ChangeDist]:

        async with await ChangeDist.anit(self._nexuslog, offs) as dist:

            async def fini():
                self._mirrors.remove(dist)

            dist.onfini(fini)

            self._mirrors.append(dist)

            yield dist

    def amLeader(self):
        return self._ldrurl is None

    async def setLeader(self, url: Optional[str], iden: str) -> None:
        '''
        Args:
            url:  if None, sets this nexsroot as leader, otherwise the telepath URL of the leader (must be a Cell)
            iden: iden of the leader.  Should be the same as my containing cell's iden
        '''
        if url is not None and not self.donexslog:
            raise s_exc.BadConfValu(mesg='Mirroring incompatible without nexslog:en')

        former = self._ldrurl

        if former == url:
            return

        self._ldrurl = url

        if self._looptask is not None:
            self._looptask.cancel()
            self._looptask = None
            self._ldrready.clear()
            if self._ldr is not None:
                await self._ldr.fini()
            self._ldr = None

        await self._dostatechange()

        if self._ldrurl is None:
            return

        self._looptask = self.schedCoro(self._followerLoop(iden))

    def onStateChange(self, func):
        '''
        Add a state change callback. Callbacks take a single argument,
        ``leader``, which is a boolean representing the leader status
        at the time the callbacks are executed.
        '''
        self._state_funcs.append(func)

    async def _dostatechange(self):
        amleader = self.amLeader()
        async with self._state_lock:
            for func in self._state_funcs:
                await s_coro.ornot(func, leader=amleader)

    async def _followerLoop(self, iden) -> None:
        while not self.isfini:

            try:
                if self._ldr is not None:
                    await self._ldr.fini()

                proxy = await s_telepath.openurl(self._ldrurl)
                self._ldr = proxy
                self._ldrready.set()

                # if we really are a mirror/follower, we have the same iden.
                if iden != await proxy.getCellIden():
                    logger.error('remote cell has different iden!  Aborting mirror sync')
                    await proxy.fini()  # Address a test race.
                    await self.fini()
                    return

                logger.info(f'mirror loop ready ({self._ldrurl})')

                while not proxy.isfini:

                    offs = self._nexuslog.index()

                    genr = proxy.getNexusChanges(offs)
                    async for item in genr:

                        if proxy.isfini:
                            break

                        offs, args = item
                        if offs != self._nexuslog.index():  # pragma: nocover
                            logger.error('mirror desync')
                            await self.fini()
                            return

                        meta = args[-1]
                        respiden = meta.get('resp')
                        respfutu = self._futures.get(respiden)

                        try:
                            retn = await self.eat(*args)

                        except asyncio.CancelledError:
                            raise

                        except Exception as e:
                            if respfutu is not None:
                                assert not respfutu.done()
                                respfutu.set_exception(e)
                            else:
                                logger.exception(e)

                        else:
                            if respfutu is not None:
                                respfutu.set_result(retn)

            except asyncio.CancelledError: # pragma: no cover
                return

            except Exception:
                logger.exception('error in initCoreMirror loop')

            self._ldrready.clear()
            await self.waitfini(1)

class Pusher(s_base.Base, metaclass=RegMethType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regclstupls: List[Tuple[str, Callable, bool]] = []

    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore

        await s_base.Base.__anit__(self)
        self._nexshands: Dict[str, Tuple[Callable, bool]] = {}

        self.nexsiden = iden
        self.nexsroot = None

        if nexsroot is not None:
            self.setNexsRoot(nexsroot)

        for event, func, passoff in self._regclstupls:  # type: ignore
            self._nexshands[event] = func, passoff

    def setNexsRoot(self, nexsroot):

        nexsroot._nexskids[self.nexsiden] = self

        def onfini():
            prev = nexsroot._nexskids.pop(self.nexsiden, None)
            assert prev is not None, f'Failed removing {self.nexsiden}'

        self.onfini(onfini)

        self.nexsroot = nexsroot

    @classmethod
    def onPush(cls, event: str, passoff=False) -> Callable:
        '''
        Decorator that registers a method to be a handler for a named event

        Args:
            event: string that distinguishes one handler from another.  Must be unique per Pusher subclass
            passoff:  whether to pass the log offset as the parameter "nexsoff" into the handler
        '''
        def decorator(func):
            func._regme = (event, func, passoff)
            return func

        return decorator

    @classmethod
    def onPushAuto(cls, event: str, passoff=False) -> Callable:
        '''
        Decorator that does the same as onPush, except automatically creates the top half method

        Args:
            event: string that distinguishes one handler from another.  Must be unique per Pusher subclass
            passoff:  whether to pass the log offset as the parameter "nexsoff" into the handler
        '''
        async def pushfunc(self, *args, **kwargs):
            return await self._push(event, *args, **kwargs)

        def decorator(func):
            pushfunc._regme = (event, func, passoff)
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
            return await self.nexsroot.issue(nexsiden, event, args, kwargs, None)

        # There's no change distribution, so directly execute
        return await self._nexshands[event][0](self, *args, **kwargs)
