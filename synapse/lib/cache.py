'''
A few speed optimized (lockless) cache helpers.  Use carefully.
'''
import collections

import synapse.common as s_common

def memoize(size=10000):

    def decor(f):

        def callback(args):
            return f(*args)

        cache = FixedCache(callback, size=size)

        def wrap(*args):
            return cache.get(args)

        wrap.cache = cache

        return wrap

    return decor

class FixedCache:

    def __init__(self, callback, size=10000):
        self.size = size
        self.callback = callback

        self.cache = {}
        self.size = size
        self.fifo = collections.deque()

    def pop(self, key):
        return self.cache.pop(key, None)

    def put(self, key, val):

        self.cache[key] = val
        self.fifo.append(key)

        while len(self.fifo) > self.size:
            key = self.fifo.popleft()
            self.cache.pop(key, None)

    def get(self, key):

        valu = self.cache.get(key, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        valu = self.callback(key)
        if valu is s_common.novalu:
            return valu

        self.cache[key] = valu
        self.fifo.append(key)

        while len(self.fifo) > self.size:
            key = self.fifo.popleft()
            self.cache.pop(key, None)

        return valu

    def clear(self):
        self.fifo.clear()
        self.cache.clear()
