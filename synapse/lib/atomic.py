import threading

import synapse.glob as s_glob

class CmpSet:
    '''
    The CmpSet class facilitates atomic compare and set.
    '''
    def __init__(self, valu):
        self.valu = valu

    def set(self, valu):
        '''
        Atomically set the valu and return change status.

        Args:
            valu (obj): The new value

        Returns:
            (bool): True if the value changed.
        '''
        with s_glob.lock:
            retn = self.valu != valu
            self.valu = valu
            return retn

class Ready:
    '''
    Atomic inc/dec state with ready event above a threshold.
    '''
    def __init__(self, size, valu=0, lock=None):

        if lock is None:
            lock = s_glob.lock

        self.lock = lock
        self.valu = valu
        self.size = size
        self.evnt = threading.Event()

        self._maySetEvent()

    def _maySetEvent(self):

        if self.valu >= self.size and not self.evnt.is_set():
            self.evnt.set()
            return

        if self.evnt.is_set():
            self.evnt.clear()

    def wait(self, timeout=None):

        self.evnt.wait(timeout=timeout)
        return self.evnt.is_set()

    def inc(self, valu=1):

        with self.lock:
            self.valu += valu
            self._maySetEvent()

    def dec(self, valu=1):

        with self.lock:
            self.valu -= valu
            self._maySetEvent()

    def __enter__(self):
        self.inc()

    def __exit__(self, exc, cls, tb):
        self.dec()

class Serialize:
    '''
    Implements a todo queue which harnesses only 1 thread at a time.
    '''
    def __init__(self, dist):
        self.dist = dist
        self.todo = collections.deque()
        self.running = False

    def dist(self, mesg):

        with s_glob.lock:
            self.todo.append(mesg)
            want = self._wantCallDist()

        if want:
            self._callDistFunc()

    def _wantCallDist(self):
        if not self.running:
            self.running = True
            return True

    def puts(self, msgs):
        with s_glob.lock:
            self.todo.extend(msgs)
            want = self._wantCallFire()

        if want:
            self._callDistFunc()

    def _callDistFunc(self):

        while self.running:

            while self.todo:
                self.dist(self.todo.popleft())

            with s_glob.lock:
                if not self.todo:
                    self.running = False

#def serialize(f):
    #f._seri_todo = collections.deque()

class Counter:
    '''
    The Counter class facilitates atomic counter incrementing/decrementing.

    Args:
        valu (int): Value to start the counter at.
        lock (threading.Lock): The lock used to protect the counter value.

    Notes:
        This uses the default Synapse global thread lock by default.
    '''
    def __init__(self, valu=0, lock=None):
        if lock is None:
            lock = s_glob.lock
        self._lock = lock
        self._valu = valu

    def inc(self, valu=1):
        '''
        Atomically increment the counter and return the new value.

        Args:
            valu (int): Value too increment the counter by.

        Notes:
            The valu passed to inc may be an negative integer in order to decrement the counter value.

        Returns:
            int: The new value of the counter after the increment operation has been performed.
        '''
        with self._lock:
            self._valu += valu
            return self._valu

    def valu(self):
        '''
        Get the current counter valu

        Returns:
            int: The current counter value
        '''
        with self._lock:
            return self._valu

    def set(self, valu=0):
        '''
        Resets the counter to a value.

        Args:
            valu (int): Value to set the counter too.

        Returns:
            int: The current counter value after setting it.
        '''
        with self._lock:
            self._valu = valu
            return self._valu
