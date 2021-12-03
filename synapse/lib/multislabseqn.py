from __future__ import annotations

import os
import heapq
import bisect
import shutil
import asyncio
import logging
import contextlib

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.lmdbslab as s_lmdbslab

from typing import List, Tuple, Dict, Optional, Any, AsyncIterator

logger = logging.getLogger(__name__)

seqnslabre = regex.compile(r'^seqn([0-9a-f]{16})\.lmdb$')

class MultiSlabSeqn(s_base.Base):
    '''
    An append-optimized sequence of byte blobs stored across multiple slabs for fast rotating/culling
    '''

    async def __anit__(self,  # type: ignore
                       dirn: str,
                       opts: Optional[Dict] = None,
                       slabopts: Optional[Dict] = None):
        '''
        Args:
            dirn (str):  directory where to store the slabs
            opts (Optional[Dict]):  options for this multislab
            slabopts (Optional[Dict]):  options to pass through to the slab creation

        '''

        await s_base.Base.__anit__(self)

        if opts is None:
            opts = {}

        self.offsevents: List[Tuple[int, int, asyncio.Event]] = []  # as a heap
        self._waitcounter = 0

        self.dirn: str = dirn
        s_common.gendir(self.dirn)
        self.slabopts: Dict[str, Any] = {} if slabopts is None else slabopts

        # The last/current slab
        self.tailslab: Optional[s_lmdbslab.Slab] = None
        self.tailseqn: Optional[s_slabseqn.SlabSeqn] = None

        # The most recently accessed slab/seqn that isn't the tail
        self._cacheslab: Optional[s_lmdbslab.Slab] = None
        self._cacheseqn: Optional[s_slabseqn.SlabSeqn] = None
        self._cacheridx: Optional[int] = None

        # A startidx -> (Slab, Seqn) dict for all open Slabs, so we don't accidentally open the same Slab twice
        self._openslabs: Dict[int, Tuple[s_lmdbslab.Slab, s_slabseqn.SlabSeqn]] = {}

        # Lock to avoid an open race
        self._openlock = asyncio.Lock()

        await self._discoverRanges()

        async def fini():
            for slab, _ in list(self._openslabs.values()):
                # We incref the slabs, so might have to fini multiple times
                count = 1
                while count:
                    count = await slab.fini()

        self.onfini(fini)

    def __repr__(self):
        return f'MultiSlabSeqn: {self.dirn!r}'

    @staticmethod
    def _getFirstIndx(slab) -> Optional[int]:
        db = slab.initdb('info')
        bytz = slab.get(b'firstindx', db=db)
        if bytz is None:
            return 0
        return s_common.int64un(bytz)

    @staticmethod
    def _setFirstIndx(slab, indx) -> bool:
        db = slab.initdb('info')
        return slab.put(b'firstindx', s_common.int64en(indx), db=db)

    async def _discoverRanges(self):
        '''
        Go through the slabs and get the starting indices of the sequence in each slab
        '''
        fnstartidx = 0
        lastidx = None
        self._ranges: List[int] = []  # Starting offsets of all the slabs in order
        self.firstindx = 0  # persistently-stored indicator of lowest index
        self.indx = 0  # The next place an add() will go
        lowindx = None

        # Make sure the files are in order

        for fn in sorted(s_common.listdir(self.dirn, glob='*seqn' + '[abcdef01234567890]' * 16 + '.lmdb')):

            if not os.path.isdir(fn):
                logger.warning(f'Found a non-directory {fn} where a directory should be')
                continue
            match = seqnslabre.match(os.path.basename(fn))
            assert match

            newstartidx = int(match.group(1), 16)

            assert newstartidx >= fnstartidx

            fnstartidx = newstartidx

            if lowindx is None:
                lowindx = fnstartidx

            if lastidx is not None:
                if fnstartidx <= lastidx:
                    mesg = f'Multislab:  overlapping files ({fn}).  Previous last index is {lastidx}.'
                    raise s_exc.BadCoreStore(mesg=mesg)

                if fnstartidx != lastidx + 1:
                    logger.debug(f'Multislab:  gap in indices at {fn}.  Previous last index is {lastidx}.')

            async with await s_lmdbslab.Slab.anit(fn, **self.slabopts) as slab:
                self.firstindx = self._getFirstIndx(slab)
                # We use the old name of the sequence to ease migration from the old system
                seqn = slab.getSeqn('nexuslog')

                firstitem = seqn.first()

                if firstitem is None:
                    self.indx = fnstartidx
                else:
                    self.indx = seqn.indx

                    firstidx = firstitem[0]  # might not match the separately stored first index due to culling

                    if firstidx < fnstartidx:
                        raise s_exc.BadCoreStore('Multislab:  filename inconsistent with contents')

                    lastidx = seqn.index() - 1

            self._ranges.append(fnstartidx)

        # An admin might have manually culled by rm'ing old slabs.  Update firstidx accordingly.
        if lowindx is not None and lowindx > self.firstindx:
            self.firstindx = lowindx

        if self.firstindx > self.indx:
            raise s_exc.BadCoreStore('Invalid firstindx value')

        await self._initTailSlab(fnstartidx)

    @staticmethod
    def slabFilename(dirn: str, indx: int):
        return s_common.genpath(dirn, f'seqn{indx:016x}.lmdb')

    async def _initTailSlab(self, indx: int) -> int:
        if self.tailslab:
            await self.tailslab.fini()

        self.tailslab, self.tailseqn = await self._makeSlab(indx)

        if not self.tailslab.dbexists('info'):
            self._setFirstIndx(self.tailslab, self.firstindx)
            self.tailseqn.indx = indx
            self._ranges.append(indx)

        return indx

    def _wake_waiters(self) -> None:
        while self.offsevents and self.offsevents[0][0] < self.indx:
            _, _, evnt = heapq.heappop(self.offsevents)
            evnt.set()

    async def rotate(self) -> int:
        '''
        Rotate the Nexus log at the current index.

        Note:
            After this executes the tailseqn will be empty.
            Waiting for this indx to be written will indicate
            when it is possible to cull 1 minus the return value
            such that the rotated seqn is deleted.

        Returns:
            int: The starting index of the new seqn
        '''
        assert self.tailslab and self.tailseqn and self._ranges

        if self.indx <= self._ranges[-1]:
            logger.info('Seqn %s at indx %d is empty', self.tailslab.path, self.indx)
            return self._ranges[-1]

        logger.info('Rotating %s at indx %d', self.tailslab.path, self.indx)
        return await self._initTailSlab(self.indx)

    async def cull(self, offs: int) -> bool:
        '''
        Remove entries up to (and including) the given offset.
        '''

        logger.info('Culling %s at offs %d', self.dirn, offs)

        # Note:  we don't bother deleting the rows from inside a partially culled slab.  We just update self.firstindx
        # so nothing will return those rows anymore.  We only delete from disk entire slabs once they are culled.

        if offs < self.firstindx:
            logger.warning('Unable to cull %s; offs (%d) < starting indx (%d)', self.dirn, offs, self.firstindx)
            return False

        # We keep at least one entry;  this avoids offsets possibly going lower after a restart
        if offs >= self.indx - 1:
            logger.warning('Unable to cull %s at offs %d; must keep at least one entry', self.dirn, offs)
            return False

        if self._cacheridx is not None:
            self._cacheridx = None
            assert self._cacheslab
            await self._cacheslab.fini()
            self._cacheslab = self._cacheseqn = None

        del_ridx = None
        for ridx in range(len(self._ranges) - 1):
            startidx = self._ranges[ridx]

            if self._openslabs.get(startidx):
                raise s_exc.SlabInUse(mesg='Attempt to cull while another task is still using it')

            fn = self.slabFilename(self.dirn, startidx)
            if offs < self._ranges[ridx + 1] - 1:
                logger.warning('Log %s will not be deleted since offs is less than last indx', fn)
                break

            optspath = s_common.switchext(fn, ext='.opts.yaml')
            try:
                os.unlink(optspath)
            except FileNotFoundError:  # pragma: no cover
                pass

            logger.info('Removing log %s with startidx %d', fn, startidx)
            shutil.rmtree(fn)
            del_ridx = ridx

            await asyncio.sleep(0)

        self.firstindx = offs + 1
        self._setFirstIndx(self.tailslab, offs + 1)

        if del_ridx is not None:
            del self._ranges[:del_ridx + 1]

        # Log if there was an attempt to cull into the tailseqn
        if offs >= self._ranges[-1]:
            fn = self.tailslab.path
            logger.warning('Log %s will not be deleted since offs is in the currently active log', fn)

        return True

    async def _makeSlab(self, startidx: int) -> Tuple[s_lmdbslab.Slab, s_slabseqn.SlabSeqn]:

        async with self._openlock:  # Avoid race in two tasks making the same slab

            item = self._openslabs.get(startidx)
            if item is not None:
                item[0].incref()
                return item

            fn = self.slabFilename(self.dirn, startidx)

            slab = await s_lmdbslab.Slab.anit(fn, **self.slabopts)
            seqn = slab.getSeqn('nexuslog')

            self._openslabs[startidx] = slab, seqn

            def fini():
                self._openslabs.pop(startidx, None)

            slab.onfini(fini)

            return slab, seqn

    @contextlib.asynccontextmanager
    async def _getSeqn(self, ridx: int) -> AsyncIterator[s_slabseqn.SlabSeqn]:
        '''
        Get the sequence corresponding to an index into self._ranges
        '''
        if ridx == len(self._ranges) - 1:
            assert self.tailslab and self.tailseqn
            slab, seqn = self.tailslab, self.tailseqn

        elif ridx == self._cacheridx:
            assert self._cacheslab and self._cacheseqn
            slab, seqn = self._cacheslab, self._cacheseqn

        else:
            startidx = self._ranges[ridx]

            self._cacheridx = None

            if self._cacheslab is not None:
                await self._cacheslab.fini()

            slab, seqn = self._cacheslab, self._cacheseqn = await self._makeSlab(startidx)
            self._cacheridx = ridx

        slab.incref()
        try:
            yield seqn
        finally:
            await slab.fini()

    async def add(self, item: Any, indx=None) -> int:
        '''
        Add a single item to the sequence.
        '''
        advances = True

        if indx is not None:
            if indx < self.firstindx:
                raise s_exc.BadIndxValu(mesg=f'indx lower than first index in sequence {self.firstindx}')

            if indx < self._ranges[-1]:
                ridx = self._getRangeIndx(indx)
                assert ridx is not None

                async with self._getSeqn(ridx) as seqn:
                    seqn.add(item, indx=indx)

                return indx

            if indx >= self.indx:
                self.indx = indx
            else:
                advances = False
        else:
            indx = self.indx

        assert self.tailseqn
        retn = self.tailseqn.add(item, indx=indx)

        if advances:
            self.indx += 1

            self._wake_waiters()

        return retn

    async def last(self) -> Optional[Tuple[int, Any]]:
        ridx = self._getRangeIndx(self.indx - 1)
        if ridx is None:
            return None

        async with self._getSeqn(ridx) as seqn:
            return seqn.last()

    def index(self) -> int:
        '''
        Return the current index to be used
        '''
        return self.indx

    def setIndex(self, indx: int) -> None:
        self.indx = indx

    def _getRangeIndx(self, offs: int) -> Optional[int]:
        '''
        Return the index into self._ranges that contains the offset
        '''
        if offs < self.firstindx:
            return None

        indx = bisect.bisect_right(self._ranges, offs)
        assert indx

        return indx - 1

    async def iter(self, offs: int) -> AsyncIterator[Tuple[int, Any]]:
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        offs = max(offs, self.firstindx)

        ri = ridx = self._getRangeIndx(offs)
        assert ridx is not None

        # ranges could get appended while iterating due to a rotation
        while ri < len(self._ranges):
            if ri > ridx:
                offs = self._ranges[ri]

            async with self._getSeqn(ri) as seqn:
                for item in seqn.iter(offs):
                    yield item

            ri += 1

    async def gets(self, offs, wait=True) -> AsyncIterator[Tuple[int, Any]]:
        '''
        Just like iter, but optionally waits for new entries once the end is reached.
        '''
        while True:

            async for (indx, valu) in self.iter(offs):
                yield (indx, valu)
                offs = indx + 1

            if not wait:
                return

            await self.waitForOffset(self.indx)

    async def get(self, offs: int) -> Any:
        '''
        Retrieve a single row by offset
        '''
        ridx = self._getRangeIndx(offs)
        if ridx is None:
            raise s_exc.BadIndxValu(mesg=f'offs lower than first index {self.firstindx}')

        async with self._getSeqn(ridx) as seqn:
            return seqn.get(offs)

    def getOffsetEvent(self, offs: int) -> asyncio.Event:
        '''
        Returns an asyncio Event that will be set when the particular offset is written.  The event will be set if the
        offset has already been reached.
        '''
        evnt = asyncio.Event()

        if offs < self.indx:
            evnt.set()
            return evnt

        # We add a simple counter to the tuple to cause stable (and FIFO) sorting and prevent ties
        heapq.heappush(self.offsevents, (offs, self._waitcounter, evnt))

        self._waitcounter += 1

        return evnt

    async def waitForOffset(self, offs: int, timeout=None) -> bool:
        '''
        Returns:
            true if the event got set, False if timed out
        '''

        if offs < self.indx:
            return True

        evnt = self.getOffsetEvent(offs)
        return await s_coro.event_wait(evnt, timeout=timeout)
