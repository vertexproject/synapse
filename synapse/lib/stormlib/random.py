import random

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

randinst = random.SystemRandom()


@s_stormtypes.registry.registerType
class Random(s_stormtypes.StormType):
    '''
    A seeded random number generator object.
    '''
    _storm_typename = 'random'
    _storm_locals = (
        {'name': 'seed', 'desc': 'The seed used to make the generator.', 'type': 'str', },
        {'name': 'int', 'desc': 'Generate a random integer.',
         'type': {'type': 'function', '_funcname': '_methInt',
                  'args': (
                      {'name': 'maxval', 'type': 'int', 'desc': 'The maximum random value.'},
                      {'name': 'minval', 'type': 'int', 'desc': 'The minimum random value.', 'default': 0},
                  ),
                  'returns': {'type': 'int', 'desc': 'A random integer in the range min-max inclusive.'}}},
    )
    _ismutable = False

    def __init__(self, runt, seed: str):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self._seed = seed
        self.robj = random.Random()
        self.robj.seed(self._seed, version=2)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'int': self._methInt,
            'seed': self._seed,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methInt(self, maxval, minval=0):
        maxval = await s_stormtypes.toint(maxval)
        minval = await s_stormtypes.toint(minval)
        if minval > maxval:
            raise s_exc.BadArg(mesg=f'Minval must be less than or equal to maxval, minval={minval}, maxval={maxval}',
                               minval=minval, maxval=maxval)
        return self.robj.randint(minval, maxval)

@s_stormtypes.registry.registerLib
class LibRandom(s_stormtypes.Lib):
    '''
    A Storm library for generating random values.
    '''
    _storm_locals = (
        {'name': 'int', 'desc': 'Generate a random integer.',
         'type': {'type': 'function', '_funcname': '_methInt',
                  'args': (
                      {'name': 'maxval', 'type': 'int', 'desc': 'The maximum random value.'},
                      {'name': 'minval', 'type': 'int', 'desc': 'The minimum random value.', 'default': 0},
                  ),
                  'returns': {'type': 'int', 'desc': 'A random integer in the range min-max inclusive.'}}},
        {'name': 'seed', 'desc': 'Make a random generator with a given seed.',
         'type': {'type': 'function', '_funcname': '_methSeed',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The seed value used for the random generator.'},
                  ),
                  'returns': {'type': 'random', 'desc': 'The random generator object.'}}
        }
    )
    _storm_lib_path = ('random',)

    def getObjLocals(self):
        return {
            'int': self._methInt,
            'seed': self._methSeed,
        }

    def _storm_copy(self):
        pass

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSeed(self, valu):
        valu = await s_stormtypes.tostr(valu)
        return Random(self.runt, valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methInt(self, maxval, minval=0):
        maxval = await s_stormtypes.toint(maxval)
        minval = await s_stormtypes.toint(minval)
        if minval > maxval:
            raise s_exc.BadArg(mesg=f'Minval must be less than or equal to maxval, minval={minval}, maxval={maxval}',
                               minval=minval, maxval=maxval)
        return randinst.randint(minval, maxval)
