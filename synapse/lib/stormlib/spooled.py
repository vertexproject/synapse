import synapse.exc as s_exc
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled
import synapse.lib.stormtypes as s_stormtypes

LIB_SPOOLED_INMEMORY_OBJECTS = 1000

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
        {'name': 'dict', 'desc': '''
            Get a Spooled Storm Dict object.

            A Spooled Storm Dict object is memory-safe to grow to extraordinarily large sizes,
            as it will fallback to file backed storage, with two restrictions. First
            is that all items in the dict can be serialized to a file if the dict grows too large,
            so all items added must be a serializable Storm primitive. Second is that when an
            item is added to the Dict, because it could be immediately written disk,
            do not hold any references to it outside of the Dict itself, as the two objects could
            differ.
            ''',
         'type': {'type': 'function', '_funcname': '_methDict',
                  'args': (
                      {'name': 'other', 'type': 'dict', 'default': None,
                       'desc': 'Initial values to place in the dict.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The new dict.'}}},
    )
    _storm_lib_path = ('spooled',)

    def getObjLocals(self):
        return {
            'set': self._methSet,
            'dict': self._methDict,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSet(self, *vals):
        core = self.runt.snap.core
        spool = await s_spooled.Set.anit(dirn=core.dirn, cell=core, size=LIB_SPOOLED_INMEMORY_OBJECTS)

        valu = await s_stormtypes.toprim(vals)
        for item in valu:
            if s_stormtypes.ismutable(item):
                mesg = f'{await s_stormtypes.torepr(item)} is mutable and cannot be used in a set.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            if not s_msgpack.isok(item):
                mesg = f'{await s_stormtypes.torepr(item)} is not safe to be used in a SpooledSet.'
                raise s_exc.StormRuntimeError(mesg=mesg)

            await spool.add(item)

        return SpooledSet(spool)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methDict(self, other=None):
        core = self.runt.snap.core
        spool = await s_spooled.Dict.anit(dirn=core.dirn, cell=core, size=LIB_SPOOLED_INMEMORY_OBJECTS)

        other = await s_stormtypes.toprim(other)
        if other is not None and not isinstance(other, dict):
            await spool.update(other)

        return SpooledDict(spool)

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

@s_stormtypes.registry.registerType
class SpooledDict(s_stormtypes.Dict):
    '''
    A StormLib API instance of a Storm Dict object that can fallback to lmdb.
    '''
    _storm_typename = 'spooled:dict'
    _ismutable = True

    @s_stormtypes.stormfunc(readonly=True)
    async def setitem(self, name, valu):
        name = await s_stormtypes.toprim(name)

        if s_stormtypes.ismutable(name):
            raise s_exc.BadArg(mesg='Mutable values are not allowed as dictionary keys', name=await s_stormtypes.torepr(name))

        if not s_msgpack.isok(name):
            mesg = f'{await s_stormtypes.torepr(name)} is not safe to be used in a SpooledDict key.'
            raise s_exc.BadArg(mesg=mesg, type=await s_stormtypes.totype(valu))

        if valu is s_stormtypes.undef:
            self.valu.pop(name, None)
            return

        valu = await s_stormtypes.toprim(valu)
        if not s_msgpack.isok(valu):
            mesg = f'{await s_stormtypes.torepr(valu)} is not safe to be used in a SpooledDict value.'
            raise s_exc.BadArg(mesg=mesg, type=await s_stormtypes.totype(valu))

        await self.valu.set(name, valu)
