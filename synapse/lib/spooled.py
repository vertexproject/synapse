import shutil
import tempfile

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

class Spooled(s_base.Base):
    '''
    A Base class that can be used to implement objects which fallback to lmdb.

    These objects are intended to fallback from Python to lmbd slabs, which aligns them
    together. Under memory pressure, these objects have a better shot of getting paged out.
    '''

    async def __anit__(self, size=10000):

        await s_base.Base.__anit__(self)

        self.size = size
        self.slab = None
        self.slabpath = None
        self.fallback = False

        async def fini():

            if self.slab is not None:
                await self.slab.fini()

            if self.slabpath is not None:
                shutil.rmtree(self.slabpath, ignore_errors=True)

        self.onfini(fini)

    async def _initFallBack(self):
        self.fallback = True
        self.slabpath = tempfile.mkdtemp()
        self.slab = await s_lmdbslab.Slab.anit(self.slabpath,
                                               map_size=s_const.mebibyte * 32)

class Set(Spooled):
    '''
    A minimal set-like implementation that will spool to a slab on large growth.
    '''

    async def __anit__(self, size=10000):
        await Spooled.__anit__(self, size=size)
        self.realset = set()
        self.len = 0

    def __contains__(self, valu):
        if self.fallback:
            return self.slab.get(s_msgpack.en(valu)) is not None
        return valu in self.realset

    def __len__(self):
        if self.fallback:
            return self.len
        return len(self.realset)

    async def add(self, valu):

        if self.fallback:
            self.slab.put(s_msgpack.en(valu), b'\x01')
            self.len += 1
            return

        self.realset.add(valu)

        if len(self.realset) >= self.size:
            await self._initFallBack()
            [self.slab.put(s_msgpack.en(valu), b'\x01') for valu in self.realset]
            self.len = len(self.realset)
            self.realset.clear()

    def discard(self, valu):

        if self.fallback:
            ret = self.slab.pop(s_msgpack.en(valu))
            if ret is None:
                return
            self.len -= 1
            return

        self.realset.discard(valu)
