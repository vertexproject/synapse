import shutil
import tempfile

import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

class Spooled(s_base.Base):

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
        self.slab = await s_lmdbslab.Slab.anit(self.slabpath)

class Set(Spooled):
    '''
    A minimal set-like implementation that will spool to a slab on large growth.
    '''
    async def __anit__(self, size=10000):
        await Spooled.__anit__(self, size=size)
        self.realset = set()

    def __contains__(self, valu):
        if self.fallback:
            return self.slab.get(s_msgpack.en(valu)) != None
        return valu in self.realset

    async def add(self, valu):

        if self.fallback:
            self.slab.put(s_msgpack.en(valu), b'\x01')
            return

        self.realset.add(valu)

        if len(self.realset) >= self.size:
            await self._initFallBack()
            [self.slab.put(s_msgpack.en(valu), b'\x01') for valu in self.realset]
            self.realset.clear()

    def discard(self, valu):

        if self.fallback:
            self.slab.pop(s_msgpack.en(valu))
            return

        self.realset.discard(valu)

class Dict(Spooled):

    async def __anit__(self, size=10000):
        await Spooled.__anit__(self, size=size)
        self.info = {}

    async def set(self, name, valu):

        if self.fallback:
            self._set_fallback(name, valu)
            return

        self.info[name] = valu

        if len(self.info) >= self.size:
            await self._initFallBack()
            [ self._set_fallback(k, v) for (k, v) in self.info.items() ]
            self.info.clear()

    def get(self, name, defv=None):

        if self.fallback:
            return self._get_fallback(name, defv=defv)

        return self.info.get(name, defv)

    def _set_fallback(self, name, valu):
        self.slab.put(s_msgpack.en(name), s_msgpack.en(valu))

    def _get_fallback(self, name, defv=None):
        byts = self.slab.get(s_msgpack.en(name))
        if byts is None:
            return defv

        return s_msgpack.un(byts)
