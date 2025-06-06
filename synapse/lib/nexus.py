import os
import shutil
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

leaderversion = 'Leader is a higher version than we are.'

# As a mirror follower, amount of time before giving up on a write request
FOLLOWER_WRITE_WAIT_S = 30.0

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

            async for item in self.nexuslog.iter(self.offs):
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

    async def __anit__(self, cell):

        await s_base.Base.__anit__(self)

        # avoid import cycle
        import synapse.lib.lmdbslab as s_lmdbslab
        import synapse.lib.multislabseqn as s_multislabseqn

        self.cell = cell
        self.dirn = cell.dirn
        self.client = None
        self.started = False
        self.celliden = self.cell.iden
        self.readonly = False
        self.writeholds = set()

        self.applytask = None

        self.ready = asyncio.Event()
        self.donexslog = self.cell.conf.get('nexslog:en')

        self.miruplink = asyncio.Event()
        self._mirready = asyncio.Event()  # for testing

        self._mirrors: List[ChangeDist] = []
        self._nexskids: Dict[str, 'Pusher'] = {}

        # Used to match pending follower write requests with the responses arriving on the log
        self._futures: Dict[str, asyncio.Future] = {}

        path = s_common.genpath(self.dirn, 'slabs', 'nexus.lmdb')
        fresh = not os.path.exists(path)

        logpath = s_common.genpath(self.dirn, 'slabs', 'nexuslog')

        self.nexsslab = await cell._initSlabFile(path)

        self.nexshot = await self.nexsslab.getHotCount('nexs:indx')

        if fresh:
            self.nexshot.set('version', 2)

        vers = self.nexshot.get('version')

        if vers <= 1:
            await self._migrateV1toV2(path, logpath)
        elif vers != 2:
            raise s_exc.BadStorageVersion(mesg=f'Got nexus log version {vers}.  Expected 2.  Accidental downgrade?')

        self.nexslog = await s_multislabseqn.MultiSlabSeqn.anit(logpath, cell=cell)

        # just in case were previously configured differently
        logindx = self.nexslog.index()
        hotindx = self.nexshot.get('nexs:indx')
        maxindx = max(logindx, hotindx)

        self.nexshot.set('nexs:indx', maxindx)
        self.nexslog.setIndex(maxindx)

        async def fini():

            for futu in self._futures.values():  # pragma: no cover
                futu.cancel()

            await self.nexsslab.fini()
            await self.nexslog.fini()

        self.onfini(fini)

    def getNexsKids(self):
        return list(self._nexskids.values())

    async def _migrateV1toV2(self, nexspath, logpath):
        '''
        Close the slab, move it to the new multislab location, then copy out the nexshot
        values, then drop the nexshot db from the multislab
        '''
        logger.warning(f'Migrating Nexus log v1->v2 for {nexspath}')

        if os.path.ismount(nexspath):  # pragma: no cover
            # Fail fast if the nexspath is its own mountpoint.
            mesg = f'The nexpath={nexspath} is located at its own mount point. This configuration cannot be migrated.'
            raise s_exc.BadCoreStore(mesg=mesg, nexspath=nexspath)

        # avoid import cycle
        import synapse.lib.lmdbslab as s_lmdbslab
        import synapse.lib.multislabseqn as s_multislabseqn

        # Grab the initial index value
        seqn = self.nexsslab.getSeqn('nexuslog')
        first = seqn.first()
        if first is None:
            # Nothing in the sequence.  Drop and move along.
            self.nexsslab.dropdb('nexuslog')
            self.nexshot.set('version', 2)
            logger.warning('Nothing in the nexuslog sequence to migrate.')
            logger.warning('...Nexus log migration complete')
            return

        await self.nexsslab.fini()

        firstidx = first[0]

        fn = s_multislabseqn.MultiSlabSeqn.slabFilename(logpath, firstidx)
        logger.warning(f'Existing nexslog will be migrated from {nexspath} to {fn}')

        if os.path.exists(fn):  # pragma: no cover
            logger.warning(f'Removing old migration which may have failed. This should not exist: {fn}')
            shutil.rmtree(fn)

        os.makedirs(fn, exist_ok=True)
        logger.warning(f'Moving existing nexslog')
        try:
            os.replace(nexspath, fn)
        except OSError as e:  # pragma: no cover
            logger.exception('Error during nexslog migration.')
            raise s_exc.BadCoreStore(mesg='Error during nexslogV1toV2', nexspath=nexspath, fn=fn) from e

        # Open a fresh slab where the old one used to be
        logger.warning(f'Re-opening fresh nexslog slab at {nexspath} for nexshot')
        self.nexsslab = await self.cell._initSlabFile(nexspath)

        self.nexshot = await self.nexsslab.getHotCount('nexs:indx')

        logger.warning('Copying nexs:indx data from migrated slab to the fresh nexslog')
        # There's only one value in nexs:indx, so this should be fast
        async with await s_lmdbslab.Slab.anit(fn) as newslab:
            olddb = self.nexsslab.initdb('nexs:indx')
            self.nexsslab.dropdb(olddb)
            db = newslab.initdb('nexs:indx')
            await newslab.copydb('nexs:indx', self.nexsslab, destdbname='nexs:indx')
            newslab.dropdb(db)

        self.nexshot.set('version', 2)

        logger.warning('...Nexus log migration complete')

    @contextlib.contextmanager
    def _getResponseFuture(self, iden=None):

        if iden is None:
            iden = s_common.guid()
        futu = self.loop.create_future()

        self._futures[iden] = futu

        try:
            yield iden, futu

        finally:
            self._futures.pop(iden, None)

    async def enNexsLog(self):

        async with self.cell.nexslock:

            if self.donexslog:
                return

            indx = await self.index()

            self.nexslog.setIndex(indx)
            self.donexslog = True

    async def recover(self) -> None:
        '''
        Replays the last entry in the nexus log in case we crashed between writing the log and applying it.

        Notes:
            This must be called at cell startup after subsystems are initialized but before any write transactions
            might happen.

            The log can only have recorded 1 entry ahead of what is applied.  All log actions are idempotent, so
            replaying the last action that (might have) already happened is harmless.
        '''
        if not self.donexslog:  # pragma: no cover
            return

        indxitem = await self.nexslog.last()
        if indxitem is None:
            # We have a brand new log
            return

        try:
            await self._apply(*indxitem)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception:
            logger.exception(f'Exception while replaying log: {s_common.trimText(repr(indxitem))}')

    async def addWriteHold(self, reason):

        self.readonly = True

        if reason not in self.writeholds:
            logger.error(f'Entering Read-Only Mode: {reason}')
            self.writeholds.add(reason)
            return True

        return False

    async def delWriteHold(self, reason):

        if reason in self.writeholds:

            self.writeholds.remove(reason)

            if not self.writeholds:
                self.readonly = False

            return True

        return False

    def reqNotReadOnly(self):

        if not self.readonly:
            return

        # sets have stable order like dicts, so use the first message...
        for reason in self.writeholds:
            raise s_exc.IsReadOnly(mesg=reason)

        mesg = 'Unable to issue Nexus events when readonly is set.'
        raise s_exc.IsReadOnly(mesg=mesg)

    async def issue(self, nexsiden, event, args, kwargs, meta=None):
        '''
        If I'm not a follower, mutate, otherwise, ask the leader to make the change and wait for the follower loop
        to hand me the result through a future.
        '''
        # pick up a reference to avoid race when we eventually can promote
        client = self.client

        if client is None:
            return await self.eat(nexsiden, event, args, kwargs, meta)

        # check here because we shouldn't be sending an edit upstream if we
        # are in readonly mode because the mirror sync will never complete.
        self.reqNotReadOnly()

        try:
            await client.waitready(timeout=FOLLOWER_WRITE_WAIT_S)
        except asyncio.TimeoutError:
            mesg = 'Mirror cannot reach leader for write request'
            raise s_exc.LinkErr(mesg=mesg) from None

        if meta is None:
            meta = {}

        # If this issue came from a downstream mirror, just in case I'm forwarding to upstream mirror,
        # make my response iden the same as what's coming from downstream

        with self._getResponseFuture(iden=meta.get('resp')) as (iden, futu):
            meta['resp'] = iden
            await client.issue(nexsiden, event, args, kwargs, meta)
            return await s_common.wait_for(futu, timeout=FOLLOWER_WRITE_WAIT_S)

    async def eat(self, nexsiden, event, args, kwargs, meta):
        '''
        Actually mutate for the given nexsiden instance.
        '''
        if meta is None:
            meta = {}

        async with self.cell.nexslock:
            if (nexus := self._nexskids.get(nexsiden)) is None:
                mesg = f'No Nexus Pusher with iden {nexsiden} {event=} args={s_common.trimText(repr(args))} ' \
                       f'kwargs={s_common.trimText(repr(kwargs))}'
                raise s_exc.NoSuchIden(mesg=mesg, iden=nexsiden, event=event)

            if event not in nexus._nexshands:
                mesg = f'No event handler for event {event} args={s_common.trimText(repr(args))} ' \
                       f'kwargs={s_common.trimText(repr(kwargs))}'
                raise s_exc.NoSuchName(mesg=mesg, iden=nexsiden, event=event)

            self.reqNotReadOnly()
            # Keep a reference to the shielded task to ensure it isn't GC'd
            self.applytask = asyncio.create_task(self._eat((nexsiden, event, args, kwargs, meta)))
            return await asyncio.shield(self.applytask)

    async def index(self):
        if self.donexslog:
            return self.nexslog.index()
        else:
            return self.nexshot.get('nexs:indx')

    async def cull(self, offs):
        return await self.nexslog.cull(offs)

    async def rotate(self):
        return await self.nexslog.rotate()

    async def waitOffs(self, offs, timeout=None):
        return await self.nexslog.waitForOffset(offs, timeout)

    async def setindex(self, indx):

        nexsindx = await self.index()
        if indx < nexsindx:
            logger.error(f'setindex ({indx}) is less than current index ({nexsindx})')
            return False

        if self.donexslog:
            self.nexslog.setIndex(indx)
        else:
            self.nexshot.set('nexs:indx', indx)

        return True

    async def _eat(self, item, indx=None):

        if self.donexslog:
            saveindx = await self.nexslog.add(item, indx=indx)
            [dist.update() for dist in tuple(self._mirrors)]

        else:
            saveindx = self.nexshot.get('nexs:indx')
            if indx is not None and indx > saveindx:  # pragma: no cover
                saveindx = self.nexshot.set('nexs:indx', indx)

            self.nexshot.inc('nexs:indx')

        return (saveindx, await self._apply(saveindx, item))

    async def _apply(self, indx, mesg):

        nexsiden, event, args, kwargs, _ = mesg

        nexus = self._nexskids[nexsiden]
        func, passitem = nexus._nexshands[event]

        if passitem:
            return await func(nexus, *args, nexsitem=(indx, mesg), **kwargs)

        return await func(nexus, *args, **kwargs)

    async def iter(self, offs: int, tellready=False, wait=True) -> AsyncIterator[Any]:
        '''
        Returns an iterator of change entries in the log
        '''
        if not self.donexslog:
            return

        if self.isfini:
            raise s_exc.IsFini()

        maxoffs = offs

        async for item in self.nexslog.iter(offs):
            if self.isfini:  # pragma: no cover
                raise s_exc.IsFini()
            maxoffs = item[0] + 1
            yield item

        if tellready:
            yield None

        if not wait:
            return

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

    async def startup(self):

        if self.client is not None:
            await self.client.fini()

        self._mirready.clear()

        self.client = None

        mirurl = self.cell.conf.get('mirror')

        await self.setNexsReady(mirurl is None)

        if mirurl is not None:
            self.client = await s_telepath.Client.anit(mirurl, onlink=self._onTeleLink)
            self.onfini(self.client)

        self.started = True

    async def isNexsReady(self):
        return self.ready.is_set()

    async def setNexsReady(self, status):

        if status:
            self.ready.set()
        else:
            self.ready.clear()

        # TODO maybe bump clients if status True -> False?
        # (or fire a timer that if we're not back to ready soon bump them?)
        await self._tellAhaReady(status)

    async def promote(self):

        client = self.client
        if client is None:
            mesg = 'promote() called on non-mirror nexsroot'
            raise s_exc.BadConfValu(mesg=mesg)

        await self.startup()

    async def _onTeleLink(self, proxy):
        self.miruplink.set()
        proxy.onfini(self.miruplink.clear)
        proxy.schedCoro(self.runMirrorLoop(proxy))

    async def runMirrorLoop(self, proxy):

        cellinfo = None
        try:
            cellinfo = await proxy.getCellInfo()
            features = cellinfo.get('features', {})
            if features.get('dynmirror'):
                await proxy.readyToMirror()

            synvers = cellinfo['synapse']['version']
            cellvers = cellinfo['cell']['version']
            if cellvers > self.cell.VERSION:
                logger.error('Leader is a higher version than we are. Mirrors must be updated first. Entering read-only mode.')
                await self.addWriteHold(leaderversion)
                # this will fire again on reconnect...
                return

            # When we reconnect and the leader version has become ok...
            await self.delWriteHold(leaderversion)

            if self.celliden is not None:
                if self.celliden != await proxy.getCellIden():
                    logger.error('remote cell has different iden!  Aborting mirror sync')
                    await proxy.fini()
                    await self.fini()
                    return

        except Exception as exc:
            logger.exception(f'Unknown error during mirror loop startup: {exc}')
            await proxy.fini()

        while not proxy.isfini:

            if cellinfo:
                ahaname = cellinfo.get('cell').get('aha', {}).get('name')
                if ahaname:
                    logger.info(f'Mirror communicating with aha service {ahaname}')

            try:

                if self.readonly:
                    await self.waitfini(timeout=2)
                    continue

                offs = self.nexslog.index()

                opts = {}
                if synvers >= (2, 95, 0):
                    opts['tellready'] = True

                genr = proxy.getNexusChanges(offs, **opts)
                async for item in genr:

                    if proxy.isfini:  # pragma: no cover
                        break

                    if self.readonly:
                        break

                    # with tellready we move to ready=true when we get a None
                    if item is None:
                        logger.info(f'Entering realtime change window for syncing data at offset={offs}')
                        await self.setNexsReady(True)
                        self._mirready.set()
                        continue

                    offs, args = item
                    if offs != self.nexslog.index():
                        logger.error('Local Nexus offset is out of sync from remote cell! Aborting mirror sync')
                        await self.fini()
                        return

                    meta = args[-1]
                    respiden = meta.get('resp')
                    respfutu = self._futures.get(respiden)

                    try:
                        retn = await self.eat(*args)

                    except Exception as e:
                        if respfutu is not None:
                            assert not respfutu.done()
                            respfutu.set_exception(e)
                        else:  # pragma: no cover
                            logger.exception(e)

                    else:
                        if respfutu is not None:
                            respfutu.set_result(retn)

            except s_exc.LinkShutDown:
                logger.warning(f'mirror loop: leader closed the connection.')

            except Exception as exc:  # pragma: no cover
                logger.exception(f'error in mirror loop: {exc}')

        # If we've left the mirror loop for some reason, we no longer know if we
        # will be in the realtime window or not. So we should try to set the ready
        # value to false and clear our internal flag.
        if not self.isfini:
            await self.setNexsReady(not self.cell.conf.get('mirror'))

    async def _tellAhaReady(self, status):

        if self.cell.ahaclient is None:
            return

        try:
            await self.cell.ahaclient.waitready(timeout=5)
            proxy = await self.cell.ahaclient.proxy(timeout=5)
            ahainfo = await proxy.getCellInfo()
            ahavers = ahainfo['synapse']['version']
            if self.cell.ahasvcname is not None and ahavers >= (2, 95, 0):
                await proxy.modAhaSvcInfo(self.cell.ahasvcname, {'ready': status})

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception as e: # pragma: no cover
            logger.exception(f'Error trying to set aha ready: {status}')

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

    async def modNexsRoot(self, ctor):

        kids = [self]
        if self.nexsroot is not None:
            kids = self.nexsroot.getNexsKids()
            await self.nexsroot.fini()

        nexsroot = await ctor()

        [kid.setNexsRoot(nexsroot) for kid in kids]

        await nexsroot.startup()

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
        saveoffs, retn = await self.nexsroot.issue(self.nexsiden, event, args, kwargs, None)
        return retn

    async def saveToNexs(self, name, *args, **kwargs):
        return await self.nexsroot.issue(self.nexsiden, name, args, kwargs, None)
