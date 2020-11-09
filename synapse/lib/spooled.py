import tempfile

import synapse.common as s_common

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

    async def __anit__(self, dirn=None, size=10000):
        '''
        Args:
            dirn(Optional[str]): base directory used for backing slab.  If None, system temporary directory is used
            size(int):  maximum number of items stored in RAM before spooled to disk
        '''
        await s_base.Base.__anit__(self)

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

        self.slab = await s_lmdbslab.Slab.anit(slabpath, map_size=s_const.mebibyte * 32)

class Set(Spooled):
    '''
    A minimal set-like implementation that will spool to a slab on large growth.
    '''

    async def __anit__(self, dirn=None, size=10000):
        await Spooled.__anit__(self, dirn=dirn, size=size)
        self.realset = set()
        self.len = 0

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

    def discard(self, valu):

        if self.fallback:
            ret = self.slab.pop(s_msgpack.en(valu))
            if ret is None:
                return
            self.len -= 1
            return

        self.realset.discard(valu)
