import asyncio
import threading
import collections

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.eventbus as s_eventbus

import synapse.lib.base as s_base

class Queue(s_eventbus.EventBus):
    '''
    A simple custom queue to address python Queue() issues.
    '''
    def __init__(self, items=()):
        s_eventbus.EventBus.__init__(self)
        self.deq = collections.deque()
        self.lock = threading.Lock()
        self.event = threading.Event()

        self._que_done = False
        self.onfini(self.done)

    def __exit__(self, exc, cls, tb):
        self.done()
        self.waitfini()

    def __iter__(self):
        while not self.isfini:
            try:
                yield self.get()
            except s_exc.IsFini as e:
                return

    def __len__(self):
        return self.size()

    def size(self):
        '''
        Return the number of entries in the Queue.

        Returns:
            int: The number of entries.
        '''
        return len(self.deq)

    def done(self):
        '''
        Gracefully mark this Queue as done.

        This still allows a Queue consumer to finish consuming it. The Queue
        functions ``get()``, ``slice()`` and ``slices()`` will not block when
        .done() has been called on a Queue.

        Returns:
            None
        '''
        self._que_done = True
        self.event.set()

    def get(self, timeout=None):
        '''
        Get the next item from the queue.

        Args:
            timeout (int): Duration, in seconds, to wait for items to be available
                           to the queue before returning.

        Notes:
            This will block if the queue is empty and no timeout value is
            specified, or .done() has not been called on the Queue.

        Examples:
            Get an item and do stuff with it::

                item = q.get(timeout=30)
                dostuff(item)

        Returns:
            Item from the queue, or None if the queue is fini() or timeout occurs.
        '''
        while not self.isfini:

            # for perf, try taking a lockless shot at it
            try:
                return self.deq.popleft()
            except IndexError as e:
                pass

            with self.lock:
                try:
                    return self.deq.popleft()
                except IndexError as e:
                    if self._que_done:
                        self.fini()
                        raise s_exc.IsFini()

                self.event.clear()

            if not self.event.wait(timeout=timeout):

                if self.isfini:
                    raise s_exc.IsFini()

                raise s_exc.TimeOut()

        raise s_exc.IsFini()

    def getn(self, timeout=None):
        '''
        Get the next item using the (ok, retn) convention.
        '''
        while not self.isfini:

            # for perf, try taking a lockless shot at it
            try:
                retn = self.deq.popleft()
                return True, retn

            except IndexError as e:
                pass

            with self.lock:

                try:

                    retn = self.deq.popleft()
                    return True, retn

                except IndexError as e:
                    if self._que_done:
                        self.fini()
                        return False, ('IsFini', {})

                self.event.clear()

            self.event.wait(timeout=timeout)
            if not self.event.is_set():
                return False, ('TimeOut', {})

        return False, ('IsFini', {})

    def put(self, item):
        '''
        Add an item to the queue and wake any consumers waiting on the queue.

        Args:
            item: Item to add to the queue.

        Notes:
            This will not add the item or wake any consumers if .done() has not been called on the Queue.

        Examples:
            Put a string in a queue::

                q.put('woot')

        Returns:
            None
        '''
        if not self._que_done:
            with self.lock:
                self.deq.append(item)
                self.event.set()

    def slice(self, size, timeout=None):
        '''
        Get a slice of the next items from the queue.

        Args:
            size (int): Maximum number of items to get from the queue.
            timeout (int): Duration, in seconds, to wait for items to be available
                           to the queue before returning.

        Examples:
            Return up to 3 items on a 30 second timeout from the queue::

                items = q.slice(3, timeout=30)

        Notes:
            This will block if the queue is empty and no timeout value is
            specified, or .done() has not been called on the Queue.

        Returns:
            list: A list of items from the queue. This will return None on
                  fini() or timeout.

        Raises:
            synapse.exc.IsFini: Once the queue is fini
            synapse.exc.TimeOut: If timeout it specified and has passed.
        '''
        while not self.isfini:

            with self.lock:

                ret = []
                while len(ret) < size and self.deq:
                    ret.append(self.deq.popleft())

                if ret:
                    return ret

                if self._que_done and not self.deq:
                    self.fini()
                    raise s_exc.IsFini()

                self.event.clear()

            if not self.event.wait(timeout=timeout):

                if self.isfini:
                    raise s_exc.IsFini()

                raise s_exc.TimeOut()

        raise s_exc.IsFini()

    def slices(self, size, timeout=None):
        '''
        Yields slices of items from the queue.

        Args:
            size (int): Maximum number of items to yield at a time.
            timeout (int): Duration, in seconds, to wait for items to be added
                           to the queue before exiting.

        Examples:
            Yield 2 items at a time with a 1 second time::

                for items in q.slices(2, timeout=1):
                    dostuff(items)

        Notes:
            This will block if the queue is empty and no timeout value is
            specified, or .done() has not been called on the Queue.


        Yields:
            list: This generator yields a list of items.
        '''
        while not self.isfini:
            try:
                yield self.slice(size, timeout=timeout)
            except s_exc.IsFini as e:
                return

class AsyncQueue(s_base.Base):
    '''
    Multi-async producer, single sync finite consumer queue with blocking at empty and full.
    '''
    async def __anit__(self, max_entries, drain_level=None):
        '''
        Args:
            max_entries (int): the maximum number of entries that can be in the queue.

            drain_level (int): once the queue is full, no more entries will be admitted until the number of entries
                falls below this parameter.
        '''

        await s_base.Base.__anit__(self)
        self.deq = collections.deque()
        self.notdrainingevent = asyncio.Event(loop=self.loop)
        self.notdrainingevent.set()
        self.notemptyevent = threading.Event()
        self.max_entries = max_entries
        self.drain_level = max_entries // 2 if drain_level is None else drain_level

        async def _onfini():
            self.notemptyevent.set()
            self.notdrainingevent.set()
        self.onfini(_onfini)

    def get(self):
        '''
        Pending retrieve on the queue
        '''
        while not self.isfini:
            try:
                val = self.deq.popleft()
                break
            except IndexError:
                self.notemptyevent.clear()
                if len(self.deq):
                    continue
                self.notemptyevent.wait()
        else:
            return None

        if not self.notdrainingevent.is_set():
            if len(self.deq) < self.drain_level:
                s_glob.initloop().call_soon_threadsafe(
                    self.notdrainingevent.set
                )
        return val

    async def put(self, item):
        '''
        Put onto the queue.  It will async pend if the queue is full or draining.
        '''
        while not self.isfini:
            if len(self.deq) >= self.max_entries:
                self.notdrainingevent.clear()
            if not self.notdrainingevent.is_set():
                await self.notdrainingevent.wait()
                continue
            break
        else:
            return

        self.deq.append(item)
        self.notemptyevent.set()

class AQueue(s_base.Base):
    '''
    An async queue with chunk optimized sync compatible consumer.
    '''
    async def __anit__(self):
        await s_base.Base.__anit__(self)

        self.fifo = []
        self.event = asyncio.Event(loop=self.loop)
        self.onfini(self.event.set)

    def put(self, item):
        '''
        Add an item to the queue.
        '''
        if self.isfini:
            return False

        self.fifo.append(item)

        if len(self.fifo) == 1:
            self.event.set()

        return True

    async def slice(self):

        # sync interface to the async queue
        if len(self.fifo) == 0:
            await self.event.wait()

        retn = list(self.fifo)
        self.fifo.clear()
        self.event.clear()
        return retn

class S2AQueue(s_base.Base):
    '''
    Sync single producer, async single consumer finite queue with blocking at empty and full.
    '''
    async def __anit__(self, max_entries, drain_level=None):
        '''
        Args:
            max_entries (int): the maximum number of entries that can be in the queue.

            drain_level (Optional[int]): once the queue is full, no more entries will be admitted until the number of
                entries falls below this parameter.  Defaults to half of max_entries.
        '''

        await s_base.Base.__anit__(self)
        self.deq = collections.deque()
        self.notdrainingevent = threading.Event()
        self.notdrainingevent.set()
        self.notemptyevent = asyncio.Event(loop=self.loop)
        self.max_entries = max_entries
        self.drain_level = max_entries // 2 if drain_level is None else drain_level
        assert self.drain_level

        async def _onfini():
            self.notemptyevent.set()
            self.notdrainingevent.set()
        self.onfini(_onfini)

    async def get(self):
        '''
        Async pend retrieve on the queue
        '''
        while not self.isfini:
            try:
                val = self.deq.popleft()
                break
            except IndexError:
                self.notemptyevent.clear()
                if len(self.deq):
                    continue
                await self.notemptyevent.wait()
        else:
            return None  # Raise fini?

        if not self.notdrainingevent.is_set() and len(self.deq) < self.drain_level:
            self.notdrainingevent.set()

        return val

    def put(self, item):
        '''
        Put onto the queue.  Pend if the queue is full or draining.
        '''
        while not self.isfini:
            if len(self.deq) >= self.max_entries:
                self.notdrainingevent.clear()
            if not self.notdrainingevent.is_set():
                self.notdrainingevent.wait()
                continue
            break
        else:
            return

        self.deq.append(item)

        # N.B. asyncio.Event.is_set is trivially threadsafe, though Event.set is not

        if not self.notemptyevent.is_set():
            self.loop.call_soon_threadsafe(self.notemptyevent.set)

    def __len__(self):
        return len(self.deq)
