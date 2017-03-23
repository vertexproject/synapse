import time
import threading
import collections

from synapse.common import *
from synapse.eventbus import EventBus

class QueueShutdown(Exception): pass

class Queue(EventBus):
    '''
    A simple custom queue to address python Queue() issues.
    '''
    def __init__(self, items=()):
        EventBus.__init__(self)
        self.deq = collections.deque()
        self.lock = threading.Lock()
        self.event = threading.Event()

        self._que_done = False
        self.onfini( self.event.set )

    def __exit__(self, exc, cls, tb):
        self.done()
        self.waitfini()

    def __iter__(self):
        while not self.isfini:
            ret = self.get()
            if ret == None:
                return

            yield ret

    def done(self):
        '''
        Gracefully mark this Queue as done
        ( but allow consumers to finish consuming it )
        '''
        self._que_done = True
        self.event.set()

    def get(self, timeout=None):
        '''
        Get the next item from the queue.

        This API will return None on timeout or fini()

        Example:

            item = q.get(timeout=30)

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
                        return None

                self.event.clear()

            self.event.wait(timeout=timeout)
            if not self.event.is_set():
                return None

    def put(self, item):
        '''
        Add an item to the queue and wake the sleeper.

        Example:

            q.put('woot')

        '''
        with self.lock:
            self.deq.append(item)
            self.event.set()

    def slice(self, size, timeout=None):
        '''
        Get a slice of the next items from the queue.

        This API will return None on timeout or fini()

        Example:

            item = q.slice(3, timeout=30)

        '''
        while not self.isfini:

            with self.lock:

                ret = []
                while len(ret) < size and self.deq:
                    ret.append( self.deq.popleft() )

                if ret:
                    return ret

                if self._que_done and not self.deq:
                    self.fini()
                    return None

                self.event.clear()

            self.event.wait(timeout=timeout)
            if not self.event.is_set():
                return None

    def slices(self, size, timeout=None):
        '''
        Yields slices of items from the queue.

        Example:

            for item in q.slices(2, timeout=1):
                dostuff(item)

        '''
        ret = self.slice(size, timeout=timeout)
        while ret != None:
            yield ret
            ret = self.slice(size, timeout=timeout)
