import tempfile

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

MAX_SPOOL_SIZE = 10000
DEFAULT_MAPSIZE = s_const.mebibyte * 32

class Spooled(s_base.Base):
    '''
    A Base class that can be used to implement objects which fallback to lmdb.

    These objects are intended to fallback from Python to lmbd slabs, which aligns them
    together. Under memory pressure, these objects have a better shot of getting paged out.
    '''

    async def __anit__(self, dirn=None, size=MAX_SPOOL_SIZE, cell=None):
        '''
        Args:
            dirn(Optional[str]): base directory used for backing slab.  If None, system temporary directory is used
            size(int):  maximum number of items stored in RAM before spooled to disk
        '''
        await s_base.Base.__anit__(self)

        self.cell = cell
        self.size = size
        self.dirn = dirn
        self.slab = None
        self.fallback = False

        async def fini():

            if self.slab is not None:
                await self.slab.trash()

        self.onfini(fini)

    async def _initFallBack(self):
        self.fallback = True

        dirn = self.dirn
        if dirn is not None:
            # Consolidate the spooled slabs underneath 'tmp' to make it easy for backup tool to avoid copying
            dirn = s_common.gendir(self.dirn, 'tmp')

        slabpath = tempfile.mkdtemp(dir=dirn, prefix='spooled_', suffix='.lmdb')

        self.slab = await s_lmdbslab.Slab.anit(slabpath, map_size=DEFAULT_MAPSIZE)
        if self.cell is not None:
            self.slab.addResizeCallback(self.cell.checkFreeSpace)

class Set(Spooled):
    '''
    A minimal set-like implementation that will spool to a slab on large growth.
    '''

    async def __anit__(self, dirn=None, size=MAX_SPOOL_SIZE, cell=None):
        await Spooled.__anit__(self, dirn=dirn, size=size, cell=cell)
        self.realset = set()
        self.len = 0

    async def __aiter__(self):

        if not self.fallback:
            for item in self.realset:
                yield item
            return

        for byts in self.slab.scanKeys():
            yield s_msgpack.un(byts)

    def __contains__(self, valu):
        if self.fallback:
            return self.slab.get(s_msgpack.en(valu)) is not None
        return valu in self.realset

    def __len__(self):
        '''
        Returns how many items are in the set, regardless of whether in RAM or backed to slab
        '''
        if self.fallback:
            return self.len

        return len(self.realset)

    async def copy(self):
        newset = await Set.anit(dirn=self.dirn, size=self.size, cell=self.cell)

        if self.fallback:
            await newset._initFallBack()
            await self.slab.copydb(None, newset.slab)
            newset.len = self.len

        else:
            newset.realset = self.realset.copy()

        return newset

    async def clear(self):
        if self.fallback:
            self.len = 0
            await self.slab.trash()
            await self._initFallBack()
        else:
            self.realset.clear()

    async def add(self, valu):

        if self.fallback:
            if self.slab.put(s_msgpack.en(valu), b'\x01', overwrite=False):
                self.len += 1
            return

        self.realset.add(valu)

        if len(self.realset) >= self.size:
            await self._initFallBack()
            [self.slab.put(s_msgpack.en(valu), b'\x01') for valu in self.realset]
            self.len = len(self.realset)
            self.realset.clear()

    def has(self, key):
        if self.fallback:
            return self.slab.has(s_msgpack.en(key))
        return key in self.realset

    def discard(self, valu):

        if self.fallback:
            ret = self.slab.pop(s_msgpack.en(valu))
            if ret is None:
                return
            self.len -= 1
            return

        self.realset.discard(valu)

class Dict(Spooled):

    async def __anit__(self, dirn=None, size=MAX_SPOOL_SIZE, cell=None):

        await Spooled.__anit__(self, dirn=dirn, size=size, cell=cell)
        self.realdict = {}
        self.len = 0

    def __len__(self):
        if self.fallback:
            return self.len
        return len(self.realdict)

    async def set(self, key, val):

        if self.fallback:
            if self.slab.replace(s_msgpack.en(key), s_msgpack.en(val)) is None:
                self.len += 1
            return

        self.realdict[key] = val

        if len(self.realdict) >= self.size:
            await self._initFallBack()
            [self.slab.put(s_msgpack.en(k), s_msgpack.en(v)) for (k, v) in self.realdict.items()]
            self.len = len(self.realdict)
            self.realdict.clear()

    def pop(self, key, defv=None):
        if self.fallback:
            ret = self.slab.pop(s_msgpack.en(key))
            if ret is None:
                return defv
            self.len -= 1
            return s_msgpack.un(ret)
        return self.realdict.pop(key, defv)

    def has(self, key):
        if self.fallback:
            return self.slab.has(s_msgpack.en(key))
        return key in self.realdict

    def get(self, key, defv=None):

        if self.fallback:
            byts = self.slab.get(s_msgpack.en(key))
            if byts is None:
                return defv
            return s_msgpack.un(byts)

        return self.realdict.get(key, defv)

    def keys(self):

        if self.fallback:
            for lkey in self.slab.scanKeys():
                yield s_msgpack.un(lkey)

        # avoid edit while iter issues...
        for key in list(self.realdict.keys()):
            yield key

    def items(self):

        if self.fallback:
            for lkey, lval in self.slab.scanByFull():
                yield s_msgpack.un(lkey), s_msgpack.un(lval)

        for item in list(self.realdict.items()):
            yield item
