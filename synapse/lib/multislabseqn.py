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

from typing import List, Tuple, Dict, Optional, Any

logger = logging.getLogger(__name__)

seqnslabre = regex.compile(r'^seqn([0-9a-f]{16})\.lmdb$')

# Average of 1.26KiB per entry means roughly 1.2 GiB / slab file
DEF_MAX_IDX_PER_SLAB = 0x1000000

class MultiSlabSeqn(s_base.Base):
    '''
    An append-optimized sequence of byte blobs stored across multiple slabs for fast rotating/culling
    '''

    async def __anit__(self, dirn, slabopts=None):

        self.MAX_IDX_PER_SLAB = int(os.environ.get('SYN_MULTISLAB_MAX_INDEX', DEF_MAX_IDX_PER_SLAB))
        self.offsevents: List[Tuple[int, int, asyncio.Event]] # as a heap
        self._waitcounter = 0
        self.dirn: str = dirn
        self.slabopts: Dict[Any] = {} if slabopts is None else slabopts

        # The last/current slab
        self.tailslab: Optional[s_lmdbslab.Slab] = None
        self.tailseqn: Optional[s_slabseqn.SlabSeqn] = None

        # The most recently accessed slab/seqn that isn't the last
        self._cacheslab: Optional[s_lmdbslab.Slab] = None
        self._cacheseqn: Optional[s_slabseqn.SlabSeqn] = None
        self._cacheridx = None

        # A startidx -> Slab, Seqn for all open Slabs, so we don't accidentally open the same Slab twice
        self._openslabs: Dict[int, Tuple[s_lmdbslab.Slab, s_slabseqn.SlabSeqn]] = {}

        self._openlock = asyncio.Lock()

        self._discoverRanges(self)

        async def fini():
            for slab, _ in self._openslabs:
                count = 1
                while count:
                    count = await slab.fini()

        self.onfini(fini)

    @staticmethod
    def _getFirstIndx(slab):
        db = slab.initdb('info')
        return slab.get('firstindx', db=db)

    @staticmethod
    def _putFirstIndx(slab):
        db = slab.initdb('info')
        return slab.put('firstindx', db=db)

    async def _discoverRanges(self):
        '''
        Go through the slabs and get the starting indices of the sequence in each slab
        '''
        fnstartidx = 0
        lastidx = None
        self._ranges: List[int] = []
        self.firstindx = 0
        lowindx = None

        # Make sure the files are in order

        for fn in sorted(s_common.listdir(self.dirn, 'seqn*.lmdb')):

            if not os.path.isdir(fn):
                logger.warning(f'Found a non-directory {fn} where a directory should be')
                continue
            match = seqnslabre.match(fn)
            if match is None:
                logger.warning(f"File {fn} has invalid name")
                continue

            newstartidx = int.from_bytes(s_common.uhex(match.group(1)), 'big')

            if newstartidx < fnstartidx:
                raise s_exc.BadCoreStore(mesg=f'Multislab:  index out of order ({fn})')

            fnstartidx = newstartidx

            if lowindx is None:
                lowindx = fnstartidx

            if lastidx is not None:
                if fnstartidx <= lastidx:
                    mesg = f'Multislab:  overlapping files ({fn}).  Previous last index is {lastidx}.'
                    raise s_exc.BadCoreStore(mesg=mesg)

                if fnstartidx != lastidx + 1:
                    logger.debug(f'Multislab:  gap in indices at {fn}.  Previous last index is {lastidx}.')

            async with s_lmdbslab.Slab.anit(fn, **self.slabopts) as slab:
                self.firstidx = self.getFirstIndx(slab)
                # We use the old name of the sequence to ease migration from the old system
                seqn = s_slabseqn.SlabSeqn('nexuslog', slab)

                first = seqn.first()
                if first is None:
                    logger.warning(f'Multislab:  found empty seqn in {fn}.  Deleting.')
                    await slab.trash()
                    continue

                firstidx = first[0]

                if firstidx != fnstartidx:
                    raise s_exc.BadCoreStore('Multislab:  filename inconsistent with contents')

                lastidx = seqn.index()
            self.idxranges.append((fnstartidx, fn))

        # An admin might have manually culled by removing old slabs.  Update firstidx accordingly.
        if lowindx > self.firstidx:
            self.firstidx = lowindx

        await self._startTailSlab(fnstartidx)

    @staticmethod
    def slabFilename(dirn: str, indx: int):
        return s_common.genpath(dirn, 'seqn{indx:016x}.lmdb')

    async def _startTailSlab(self, indx):
        if self.tailslab:
            await self.tailslab.fini()

        self.tailslab, self.tailseqn = await self._makeSlab(indx)

        if not self.tailslab.dbexists('info'):
            self._setFirstIndx(self.tailslab, self.firstindx)

        if not self.tailseqn.index():
            self.tailseqn.indx = indx

        return indx

    async def _appendSlab(self):
        self._ranges.append(await self._startTailSlab(self.indx))

    def _wake_waiters(self):
        while self.offsevents and self.offsevents[0][0] < self.indx:
            _, _, evnt = heapq.heappop(self.offsevents)
            evnt.set()

    async def cull(self, offs):
        '''
        Remove entries up to (and including) the given offset.

        Note:  don't bother deleting the ro
        '''
        if offs < self.firstindx:
            return

        self._cacheridx = None
        await self._cacheslab.fini()
        self._cacheslab = self._cacheseqn = None

        if offs > self.indx:
            return

        for ridx in range(len(self._ranges) - 1):
            startidx = self._ranges[ridx]

            if self._openslabs.get(startidx):
                raise s_exc.SynErr(mesg='Attempt to cull while another task is still using it')

            fn = self.slabFilename(self.dirn, startidx)
            if offs < self._ranges[ridx + 1] - 1:
                break

            optspath = s_common.switchext(fn, ext='.opts.yaml')
            try:
                os.unlink(optspath)
            except FileNotFoundError:  # pragma: no cover
                pass

            shutil.rmtree(fn)

            await asyncio.sleep(0)

        self.firstindx = offs + 1
        await self._setFirstIndx(self.tailslab, offs + 1)

        del self.idxranges[:ridx]

    def _isTimeToRotate(self, indx):
        return indx > self._ranges[-1] and indx % self.IDX_PER_SLAB == 0

    async def _makeSlab(self, startidx: int) -> Tuple[s_lmdbslab.Slab, s_slabseqn.SlabSeqn]:

        async with self._openlock:  # Avoid race in two tasks making the same slab

            item = self._openslabs.get(startidx)
            if item is not None:
                item[0].incref()
                return item
            fn = self.slabFilename(self.dirn, startidx)

            slab = await s_lmdbslab.Slab.anit(fn, **self.slabopts)
            seqn = slab.getSeqn('nexuslog')  # type: ignore

            self._openslabs[startidx] = slab, seqn

            def fini():
                self._openslabs.pop(startidx)

            slab.onfini(fini)

            return slab, seqn

    @contextlib.asynccontextmanager
    async def _getSeqn(self, ridx: int):
        '''
        Get the sequence corresponding to an index into self._ranges
        '''
        # Problem:  what happens if tail is being closed
        if ridx == len(self._ranges) - 1:
            try:
                self.tailslab.incref()  # type: ignore
                yield self.tailseqn
            finally:
                await self.tailslab.fini()  # type: ignore
            return

        if ridx == self._cacheridx:
            try:
                self._cacheslab.incref()  # type: ignore
                yield self._cacheseqn
            finally:
                await self._cacheslab.fini()  # type: ignore
            return

        startidx = self._ranges[ridx]

        if self._cacheslab is not None:
            self._cacheridx = None

            await self._cacheslab.fini()

        self._cacheslab, self._cacheseqn = await self._makeSlab(startidx)
        self._cacheridx = ridx
        yield self._cacheseqn

    async def add(self, item, indx=None):
        '''
        Add a single item to the sequence.
        '''
        advances = True

        if indx is not None:
            if indx < self.firstidx:
                raise s_exc.BadLiftValu(mesg=f'indx lower than first index in sequence {self.firstidx}')

            if indx < self.ranges[-1]:
                ridx = self._getRangeIndx(indx)
                async with self._getSeqn(ridx) as seqn:
                    seqn.add(item, indx=indx)
                return indx

            if indx >= self.indx:
                self.indx = indx
            else:
                advances = False

        if advances and self._isTimeToRotate(self.indx):
            await self._appendSlab()

        retn = self.tailseqn.put(item, indx=indx)

        if advances:
            self.indx += 1

        self._wake_waiters()

        return retn

    def last(self):
        return self.tailseqn.last()

    def stat(self):
        return self.tailslab.stat()

    def index(self):
        '''
        Return the current index to be used
        '''
        return self.indx

    def _getRangeIndx(self, offs):
        '''
        Return the index into self._ranges that contains the offset
        '''
        if offs < self.firstidx:
            raise s_exc.BadLiftValu(mesg=f'offs lower than first index in sequence {self.firstidx}')

        indx = bisect.bisect_left(self.ranges, offs)
        if indx == 0:
            return None

        return indx - 1

    async def iter(self, offs):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        offs = max(offs, self.firstidx)

        ridx = self._getRangeIndx(offs)
        if ridx is None:
            ridx = 0

        for ri in range(ridx, len(self.ranges)):

            async with self._getSeqn(ri) as seqn:
                for item in seqn.iter(offs):
                    yield item

            offs = self.ranges[ri + 1]

    async def gets(self, offs, wait=True):
        '''
        Just like iter, but optionally waits for new entries once then end is reached.
        '''
        while True:

            for (indx, valu) in self.iter(offs):
                yield (indx, valu)
                offs = indx + 1

            if not wait:
                return

            await self.waitForOffset(self.indx)

    def get(self, offs):
        '''
        Retrieve a single row by offset
        '''
        ridx = self._getRangeIndx(offs)
        if ridx is None:
            raise s_exc.BadLiftValu(mesg=f'offs lower than first index in sequence {self.firstidx}')

        async with self._getSeqn(ridx) as seqn:
            return seqn.get(offs)

    def getOffsetEvent(self, offs):
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

    async def waitForOffset(self, offs, timeout=None):
        '''
        Returns:
            true if the event got set, False if timed out
        '''

        if offs < self.indx:
            return True

        evnt = self.getOffsetEvent(offs)
        return await s_coro.event_wait(evnt, timeout=timeout)
