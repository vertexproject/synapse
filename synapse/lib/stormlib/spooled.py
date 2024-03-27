import synapse.exc as s_exc
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibSpooled(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Spooled Objects.
    '''
    _storm_locals = (
        {'name': 'set', 'desc': '''
            Get a Spooled Storm Set object.

            A Spooled Storm Set object is memory-safe to grow to extraordinarily large sizes,
            as it will fallback to file backed storage, with two restrictions. First
            is that all items in the set can be serialized to a file if the set grows too large,
            so all items added must be a serializable Storm primitive. Second is that when an
            item is added to the Set, because it could be immediately written disk,
            do not hold any references to it outside of the Set itself, as the two objects could
            differ.
            ''',
         'type': {'type': 'function', '_funcname': '_methSet',
                  'args': (
                      {'name': '*vals', 'type': 'any', 'desc': 'Initial values to place in the set.', },
                  ),
                  'returns': {'type': 'set', 'desc': 'The new set.'}}},
    )
    _storm_lib_path = ('spooled',)

    def getObjLocals(self):
        return {
            'set': self._methSet,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSet(self, *vals):
        core = self.runt.snap.core
        spool = await s_spooled.Set.anit(dirn=core.dirn, cell=core, size=1000)

        valu = list(vals)
        for item in valu:
            if s_stormtypes.ismutable(item):
                mesg = f'{await s_stormtypes.torepr(item)} is mutable and cannot be used in a set.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            if not s_msgpack.isok(item):
                mesg = f'{await s_stormtypes.torepr(item)} is not safe to be used in a SpooledSet.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            await spool.add(item)

        return SpooledSet(spool)

@s_stormtypes.registry.registerType
class SpooledSet(s_stormtypes.Set):
    '''
    A StormLib API instance of a Storm Set object that can fallback to lmdb.
    '''
    _storm_typename = 'spooled:set'
    _ismutable = True

    def __init__(self, valu, path=None):

        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    async def iter(self):
        async for item in self.valu:
            yield item

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSetAdd(self, *items):
        for i in items:
            if s_stormtypes.ismutable(i):
                mesg = f'{await s_stormtypes.torepr(i)} is mutable and cannot be used in a set.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            if not s_msgpack.isok(i):
                mesg = f'{await s_stormtypes.torepr(i)} is not safe to be used in a SpooledSet.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            await self.valu.add(i)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSetAdds(self, *items):
        for item in items:
            async for i in s_stormtypes.toiter(item):
                if s_stormtypes.ismutable(i):
                    mesg = f'{await s_stormtypes.torepr(i)} is mutable and cannot be used in a set.'
                    raise s_exc.StormRuntimeError(mesg=mesg)

                if not s_msgpack.isok(i):
                    mesg = f'{await s_stormtypes.torepr(i)} is not safe to be used in a SpooledSet.'
                    raise s_exc.StormRuntimeError(mesg=mesg)

                await self.valu.add(i)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSetList(self):
        return [x async for x in self.valu]

    async def stormrepr(self):
        reprs = [await s_stormtypes.torepr(k) async for k in self.valu]
        rval = ', '.join(reprs)
        return f'{{{rval}}}'

    async def value(self):
        return set([x async for x in self.valu])
