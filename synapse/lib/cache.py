'''
A few speed optimized (lockless) cache helpers.  Use carefully.
'''
import re
import asyncio
import collections

import regex

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

@memoize()
def getTagGlobRegx(name):

    parts = []
    for part in name.split('.'):
        part = re.escape(part).replace('\\*', '([^.]+)')
        parts.append(part)

    regq = '\\.'.join(parts)
    return regex.compile(regq)

class TagGlobs:
    '''
    An object that manages multiple tag globs and values for caching.
    '''
    def __init__(self):
        self.globs = []
        self.cache = FixedCache(self._getGlobMatches)

    def add(self, name, valu, base=None):

        self.cache.clear()

        regx = getTagGlobRegx(name)

        glob = (regx, (name, valu))

        self.globs.append(glob)

        if base:
            def fini():
                try:
                    self.globs.remove(glob)
                except ValueError:
                    pass
                self.cache.clear()
            base.onfini(fini)

    def rem(self, name, valu):
        self.globs = [g for g in self.globs if g[1] != (name, valu)]
        self.cache.clear()

    def get(self, name):
        return self.cache.get(name)

    def _getGlobMatches(self, name):
        return [g[1] for g in self.globs if g[0].fullmatch(name) is not None]
