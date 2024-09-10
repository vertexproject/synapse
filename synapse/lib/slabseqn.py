import heapq
import asyncio

import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.msgpack as s_msgpack

class SlabSeqn:
    '''
    An append optimized sequence of byte blobs.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the sequence.
    '''
    def __init__(self, slab, name: str) -> None:

        self.slab = slab
        self.db = self.slab.initdb(name)

        self.indx = self.nextindx()
        self.addevents = []
        self.offsevents = []  # type: ignore # List[Tuple[int, int, asyncio.Event]] as a heap
        self._waitcounter = 0

        # NOTE: This is intended to be publicly accessible
        # and therefore must always represent the true size.
        self.size = self.stat()['entries']

    def _wake_waiters(self):

        for evnt in self.addevents:
            evnt.set()

        while self.offsevents and self.offsevents[0][0] < self.indx:
            _, _, evnt = heapq.heappop(self.offsevents)
            evnt.set()

    def pop(self, offs):
        '''
        Pop a single entry at the given offset.
        '''
        byts = self.slab.pop(s_common.int64en(offs), db=self.db)
        if byts is not None:
            self.size -= 1
            return (offs, s_msgpack.un(byts))

    async def cull(self, offs):
        '''
        Remove entries up to (and including) the given offset.
        '''
        for itemoffs, valu in self.iter(0):

            if itemoffs > offs:
                return

            if self.slab.delete(s_common.int64en(itemoffs), db=self.db):
                self.size -= 1
            await asyncio.sleep(0)

    def add(self, item, indx=None):
        '''
        Add a single item to the sequence.
        '''
        if indx is not None:
            if indx >= self.indx:
                self.slab.put(s_common.int64en(indx), s_msgpack.en(item), append=True, db=self.db)
                self.indx = indx + 1
                self.size += 1
                self._wake_waiters()
                return indx

            oldv = self.slab.replace(s_common.int64en(indx), s_msgpack.en(item), db=self.db)
            if oldv is None:
                self.size += 1
            return indx

        indx = self.indx
        retn = self.slab.put(s_common.int64en(indx), s_msgpack.en(item), append=True, db=self.db)
        assert retn, "Not adding the largest index"

        self.indx += 1
        self.size += 1

        self._wake_waiters()

        return indx

    def first(self):

        for lkey, lval in self.slab.scanByFull(db=self.db):
            return s_common.int64un(lkey), s_msgpack.un(lval)

        return None

    def last(self):

        last = self.slab.last(db=self.db)
        if last is None:
            return None

        lkey, lval = last

        indx = s_common.int64un(lkey)
        return indx, s_msgpack.un(lval)

    def stat(self):
        return self.slab.stat(db=self.db)

    async def save(self, items):
        '''
        Save a series of items to a sequence.

        Args:
            items (tuple): The series of items to save into the sequence.

        Returns:
            The index of the first item
        '''
        rows = []
        indx = self.indx

        size = 0
        tick = s_common.now()
        abstick = s_common.mononow()

        for item in items:

            byts = s_msgpack.en(item)

            size += len(byts)

            lkey = s_common.int64en(indx)
            indx += 1

            rows.append((lkey, byts))

        retn = await self.slab.putmulti(rows, append=True, db=self.db)
        took = s_common.mononow() - abstick

        assert retn, "Not adding the largest indices"

        self.size += retn[1]

        origindx = self.indx
        self.indx = indx

        self._wake_waiters()

        return {'indx': indx, 'size': size, 'count': len(items), 'time': tick, 'took': took, 'orig': origindx}

    def index(self):
        '''
        Return the current index to be used
        '''
        return self.indx

    def nextindx(self):
        '''
        Determine the next insert offset according to storage.

        Returns:
            int: The next insert offset.
        '''
        byts = self.slab.lastkey(db=self.db)
        if byts is None:
            return 0

        return s_common.int64un(byts) + 1

    def iter(self, offs, reverse=False):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        startkey = s_common.int64en(offs)
        if reverse:
            for lkey, lval in self.slab.scanByRangeBack(startkey, db=self.db):
                offs = s_common.int64un(lkey)
                valu = s_msgpack.un(lval)
                yield offs, valu
        else:
            for lkey, lval in self.slab.scanByRange(startkey, db=self.db):
                offs = s_common.int64un(lkey)
                valu = s_msgpack.un(lval)
                yield offs, valu

    async def aiter(self, offs, wait=False, timeout=None):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.
            wait (boolean): Once caught up, yield new results in realtime.
            timeout (int): Max time to wait for a new item.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        startkey = s_common.int64en(offs)
        scanoffs = None
        for lkey, lval in self.slab.scanByRange(startkey, db=self.db):
            scanoffs = s_common.int64un(lkey)
            valu = s_msgpack.un(lval)
            yield scanoffs, valu

        # no awaiting between here and evnt.timewait()
        if wait:

            if scanoffs is None:
                offs -= 1
            else:
                offs = scanoffs

            evnt = s_coro.Event()
            try:
                self.addevents.append(evnt)
                while True:
                    evnt.clear()
                    if not await evnt.timewait(timeout=timeout):
                        return

                    startkey = s_common.int64en(offs + 1)
                    for lkey, lval in self.slab.scanByRange(startkey, db=self.db):
                        offs = s_common.int64un(lkey)
                        valu = s_msgpack.un(lval)
                        yield offs, valu
            finally:
                self.addevents.remove(evnt)

    async def gets(self, offs, wait=True):
        '''
        Returns an async generator of indx/valu tuples, optionally waiting and continuing to yield them as new entries
        are added

        Args:
            offs (int): The offset to begin iterating from.
            wait (bool):  Whether to continue yielding tupls when it hits the end of the sequence.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        while True:

            for (indx, valu) in self.iter(offs):
                yield (indx, valu)
                offs = indx + 1

            if not wait:
                return

            await self.waitForOffset(self.indx)

    def trim(self, offs):
        '''
        Delete entries starting at offset and moving forward.
        '''
        retn = False

        startkey = s_common.int64en(offs)
        for lkey, _ in self.slab.scanByRange(startkey, db=self.db):
            retn = True
            if self.slab.delete(lkey, db=self.db):
                self.size -= 1

        if retn:
            self.indx = self.nextindx()

        return retn

    def iterBack(self, offs):
        '''
        Iterate backwards over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        startkey = s_common.int64en(offs)

        for lkey, lval in self.slab.scanByRangeBack(startkey, db=self.db):
            indx = s_common.int64un(lkey)
            valu = s_msgpack.un(lval)
            yield indx, valu

    def rows(self, offs):
        '''
        Iterate over raw indx, bytes tuples from a given offset.
        '''
        lkey = s_common.int64en(offs)
        for lkey, byts in self.slab.scanByRange(lkey, db=self.db):
            indx = s_common.int64un(lkey)
            yield indx, byts

    def get(self, offs):
        '''
        Retrieve a single row by offset
        '''
        lkey = s_common.int64en(offs)
        valu = self.slab.get(lkey, db=self.db)
        if valu is not None:
            return s_msgpack.un(valu)

    def getraw(self, byts):
        valu = self.slab.get(byts, db=self.db)
        if valu is not None:
            return s_msgpack.un(valu)

    def slice(self, offs, size):

        imax = size - 1

        for i, item in enumerate(self.iter(offs)):

            yield item

            if i == imax:
                break

    def sliceBack(self, offs, size):

        imax = size - 1

        for i, item in enumerate(self.iterBack(offs)):

            yield item

            if i == imax:
                break

    def getByIndxByts(self, indxbyts):
        byts = self.slab.get(indxbyts, db=self.db)
        if byts is not None:
            return s_msgpack.un(byts)

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
