import asyncio
import logging
import functools
import contextlib

from typing import List, Dict, Any, Callable, Tuple, Optional, AsyncIterator

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base

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

    async def __anit__(self, dirn: str, donexslog: bool = True, map_async=False):  # type: ignore

        await s_base.Base.__anit__(self)

        import synapse.lib.lmdbslab as s_lmdbslab  # avoid import cycle

        self.dirn = dirn
        self.client = None
        self.started = False
        self.celliden = None
        self.donexslog = donexslog

        self._mirrors: List[ChangeDist] = []
        self._nexskids: Dict[str, 'Pusher'] = {}

        # Used to match pending follower write requests with the responses arriving on the log
        self._futures: Dict[str, asyncio.Future] = {}

        path = s_common.genpath(self.dirn, 'slabs', 'nexus.lmdb')

        self.map_async = map_async
        self.nexsslab = await s_lmdbslab.Slab.anit(path, map_async=map_async)

        self.nexslog = self.nexsslab.getSeqn('nexuslog')
        self.nexshot = await self.nexsslab.getHotCount('nexs:indx')

        # just in case were previously configured differently
        logindx = self.nexslog.index()
        hotindx = self.nexshot.get('nexs:indx')
        self.nexshot.set('nexs:indx', max(logindx, hotindx))

        async def fini():

            for futu in self._futures.values(): # pragma: no cover
                futu.cancel()

            await self.nexsslab.fini()

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
        if not self.donexslog: # pragma: no cover
            return

        indxitem = self.nexslog.last()
        if indxitem is None:
            # We have a brand new log
            return

        try:
            await self._apply(*indxitem)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception:
            logger.exception('Exception while replaying log')

    async def issue(self, nexsiden: str, event: str, args: Tuple[Any, ...], kwargs: Dict[str, Any],
                    meta: Optional[Dict] = None) -> Any:
        '''
        If I'm not a follower, mutate, otherwise, ask the leader to make the change and wait for the follower loop
        to hand me the result through a future.
        '''
        assert self.started, 'Attempt to issue before nexsroot is started'

        # pick up a reference to avoid race when we eventually can promote
        client = self.client

        if client is None:
            return await self.eat(nexsiden, event, args, kwargs, meta)

        try:
            await client.waitready(timeout=FOLLOWER_WRITE_WAIT_S)
        except asyncio.TimeoutError:
            mesg = 'Mirror cannot reach leader for write request'
            raise s_exc.LinkErr(mesg=mesg) from None

        with self._getResponseFuture() as (iden, futu):

            if meta is None:
                meta = {}

            meta['resp'] = iden

            await self.client.issue(nexsiden, event, args, kwargs, meta)
            return await asyncio.wait_for(futu, timeout=FOLLOWER_WRITE_WAIT_S)

    async def eat(self, nexsiden, event, args, kwargs, meta):
        '''
        Actually mutate for the given nexsiden instance.
        '''
        if meta is None:
            meta = {}

        return await self._eat((nexsiden, event, args, kwargs, meta))

    async def index(self):
        if self.donexslog:
            return self.nexslog.index()
        else:
            return self.nexshot.get('nexs:indx')

    async def _eat(self, item, indx=None):

        if self.donexslog:
            saveindx = self.nexslog.add(item, indx=indx)
            [dist.update() for dist in tuple(self._mirrors)]

        else:
            saveindx = self.nexshot.get('nexs:indx')
            if indx is not None and indx > saveindx: # pragma: no cover
                saveindx = self.nexshot.set('nexs:indx', indx)

            self.nexshot.inc('nexs:indx')

        return await self._apply(saveindx, item)

    async def _apply(self, indx, mesg):

        nexsiden, event, args, kwargs, _ = mesg

        nexus = self._nexskids[nexsiden]
        func, passitem = nexus._nexshands[event]
        if passitem:
            return await func(nexus, *args, nexsitem=(indx, mesg), **kwargs)

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

        for item in self.nexslog.iter(offs):
            if self.isfini: # pragma: no cover
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

        async with await ChangeDist.anit(self.nexslog, offs) as dist:

            async def fini():
                self._mirrors.remove(dist)

            dist.onfini(fini)

            self._mirrors.append(dist)

            yield dist

    async def startup(self, mirurl, celliden=None):

        self.celliden = celliden

        if self.client is not None:
            await self.client.fini()

        self.client = None
        if mirurl is not None:
            self.client = await s_telepath.Client.anit(mirurl, onlink=self._onTeleLink)
            self.onfini(self.client)

        self.started = True

    async def promote(self):

        client = self.client
        if client is None:
            mesg = 'promote() called on non-mirror nexsroot'
            raise s_exc.BadConfValu(mesg=mesg)

        await self.startup(None)

    async def _onTeleLink(self, proxy):
        self.client.schedCoro(self.runMirrorLoop(proxy))

    async def runMirrorLoop(self, proxy):

        if self.celliden is not None:
            if self.celliden != await proxy.getCellIden():
                logger.error('remote cell has different iden!  Aborting mirror sync')
                await proxy.fini()
                await self.fini()
                return

        while not proxy.isfini:

            try:

                offs = self.nexslog.index()
                genr = proxy.getNexusChanges(offs)
                async for item in genr:

                    if proxy.isfini: # pragma: no cover
                        break

                    offs, args = item
                    if offs != self.nexslog.index():  # pragma: no cover
                        logger.error('mirror desync')
                        await self.fini()
                        return

                    meta = args[-1]
                    respiden = meta.get('resp')
                    respfutu = self._futures.get(respiden)

                    try:
                        retn = await self.eat(*args)

                    except asyncio.CancelledError: # pragma: no cover
                        raise

                    except Exception as e:
                        if respfutu is not None:
                            assert not respfutu.done()
                            respfutu.set_exception(e)
                        else: # pragma: no cover
                            logger.exception(e)

                    else:
                        if respfutu is not None:
                            respfutu.set_result(retn)

            except asyncio.CancelledError: # pragma: no cover
                raise

            except Exception: # pragma: no cover
                logger.exception('error in mirror loop')

class Pusher(s_base.Base, metaclass=RegMethType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regclstupls: List[Tuple[str, Callable, bool]] = []

    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore

        await s_base.Base.__anit__(self)
        self._nexshands: Dict[str, Tuple[Callable, bool]] = {}

        self.nexsiden = iden
        self.nexsroot: Optional[NexsRoot] = None

        if nexsroot is not None:
            self.setNexsRoot(nexsroot)

        for event, func, passitem in self._regclstupls:  # type: ignore
            self._nexshands[event] = func, passitem

    def setNexsRoot(self, nexsroot):

        nexsroot._nexskids[self.nexsiden] = self

        def onfini():
            prev = nexsroot._nexskids.pop(self.nexsiden, None)
            assert prev is not None, f'Failed removing {self.nexsiden}'

        self.onfini(onfini)

        self.nexsroot = nexsroot

    @classmethod
    def onPush(cls, event: str, passitem=False) -> Callable:
        '''
        Decorator that registers a method to be a handler for a named event

        Args:
            event: string that distinguishes one handler from another.  Must be unique per Pusher subclass
            passitem:  whether to pass the (offs, mesg) tuple to the handler as "nexsitem"
        '''
        def decorator(func):
            func._regme = (event, func, passitem)
            return func

        return decorator

    @classmethod
    def onPushAuto(cls, event: str, passitem=False) -> Callable:
        '''
        Decorator that does the same as onPush, except automatically creates the top half method

        Args:
            event: string that distinguishes one handler from another.  Must be unique per Pusher subclass
            passitem:  whether to pass the (offs, mesg) tuple to the handler as "nexsitem"
        '''
        async def pushfunc(self, *args, **kwargs):
            return await self._push(event, *args, **kwargs)

        def decorator(func):
            pushfunc._regme = (event, func, passitem)
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
        assert self.nexsroot
        return await self.nexsroot.issue(self.nexsiden, event, args, kwargs, None)
