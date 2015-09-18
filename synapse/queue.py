import time
import threading

from synapse.eventbus import EventBus

class QueueShutdown(Exception): pass

class BulkQueue(EventBus):
    '''
    A Queue like object which returns lists of items at once.
    ( to minimize round trips in remote queue retrieval )

    Example:

        q = BulkQueue()

        for x in q.get():
            stuff(x)

    '''
    def __init__(self):
        EventBus.__init__(self)
        self.last = time.time()
        self.lock = threading.Lock()

        self.items = []
        self.event = threading.Event()

        self.onfini( self.event.set )

    def abandoned(self, dtime):
        now = time.time()
        return now > (self.last + dtime)

    def append(self, x):
        if self.isfini:
            raise QueueShutdown()

        with self.lock:
            self.items.append(x)
            self.event.set()

    def prepend(self, x):
        # NOTE: this is heavy, use judiciously
        if self.isfini:
            raise QueueShutdown()

        with self.lock:
            self.items.insert(0,x)
            self.event.set()

    def extend(self, x):
        if self.isfini:
            raise QueueShutdown()

        with self.lock:
            self.items.extend(x)
            self.event.set()

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        try:
            while True:
                for i in self.get(timeout=1):
                    yield i
        except QueueShutdown as e:
            pass

    def put(self, item):
        '''
        Put an item into the BulkQueue.

        Example:

            q.put( foo )

        '''
        if self.isfini:
            raise QueueShutdown()

        self.append( item )

    def get(self, timeout=None):
        '''
        Retrieve the next list of items from the BulkQueue.

        Example:

            for item in q.get():
                dostuff(item)

        '''
        self.last = time.time()
        with self.lock:
            if self.items:
                return self._get_items()

            if self.isfini:
                raise QueueShutdown()

            # Clear the event so we can wait...
            self.event.clear()

        self.event.wait(timeout=timeout)
        if self.isfini:
            raise QueueShutdown()

        with self.lock:
            self.last = time.time()
            if not self.items and self.isfini:
                raise QueueShutdown()
            return self._get_items()

    def peek(self):
        return list(self.items)

    def __len__(self):
        return len(self.items)

    def _get_items(self):
        ret = self.items
        self.items = []
        return ret
