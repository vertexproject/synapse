'''
A few speed optimized (lockless) cache helpers.  Use carefully.
'''
import asyncio
import collections

import synapse.exc as s_exc
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
        self.iscorocall = asyncio.iscoroutinefunction(self.callback)

        self.cache = {}
        self.fifo = collections.deque()

    def __len__(self):
        return len(self.cache)

    def pop(self, key):
        return self.cache.pop(key, None)

    def put(self, key, val):

        self.cache[key] = val
        self.fifo.append(key)

        while len(self.fifo) > self.size:
            key = self.fifo.popleft()
            self.cache.pop(key, None)

    def get(self, key):
        if self.iscorocall:
            raise s_exc.BadOperArg('cache was initialized with coroutine.  Must use aget')

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

    async def aget(self, key):
        if not self.iscorocall:
            raise s_exc.BadOperArg('cache was initialized with non coroutine.  Must use get')

        valu = self.cache.get(key, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        valu = await self.callback(key)
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
