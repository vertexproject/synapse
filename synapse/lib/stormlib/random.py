import random

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

from typing import Optional

randinst = random.SystemRandom()


@s_stormtypes.registry.registerType
class Random(s_stormtypes.StormType):
    '''
    A random number generator.
    '''
    _storm_typename = 'random'
    _storm_locals = (
        {'name': 'int', 'desc': 'Generate a random integer.',
         'type': {'type': 'function', '_funcname': '_methInt',
                  'args': (
                      {'name': 'maxval', 'type': 'int', 'desc': 'The maximum random value.'},
                      {'name': 'minval', 'type': 'int', 'desc': 'The minimum random value.', 'default': 0},
                  ),
                  'returns': {'type': 'int', 'desc': 'A random integer in the range min-max inclusive.'}}},
        {'name': 'seed', 'desc': 'The seed used for the generator. Setting this value resets the generator state.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storSeed', '_gtorfunc': '_gtorSeed',
                  'returns': {'type': ['str', 'null']}}},
    )
    _ismutable = False

    def __init__(self, runt, seed: Optional[str] =None):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self._seed = seed
        self.robj = random.Random()
        if seed is not None:
            self.robj.seed(self._seed, version=2)
        self.locls.update(self.getObjLocals())
        self.gtors.update({
            'seed': self._gtorSeed,
        })
        self.stors.update({
            'seed': self._storSeed,
        })

    async def stormrepr(self):
        ret = f'{self._storm_typename}'
        if self._seed is not None:
            ret = f'{ret} seed={s_common.trimText(self._seed, n=40)}'
        return ret

    def getObjLocals(self):
        return {
            'int': self._methInt,
        }

    async def _gtorSeed(self):
        return self._seed

    async def _storSeed(self, seed):
        self._seed = await s_stormtypes.tostr(seed, noneok=True)
        self.robj.seed(self._seed)

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
        {'name': 'generator', 'desc': 'Make a random generator with a given seed.',
         'type': {'type': 'function', '_funcname': '_methGenerator',
                  'args': (
                      {'name': 'seed', 'type': 'str', 'default': None,
                       'desc': 'The seed value used for the random generator.'},
                  ),
                  'returns': {'type': 'random', 'desc': 'The random generator object.'}}
        }
    )
    _storm_lib_path = ('random',)

    def getObjLocals(self):
        return {
            'int': self._methInt,
            'generator': self._methGenerator,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGenerator(self, seed=None):
        seed = await s_stormtypes.tostr(seed, noneok=True)
        return Random(self.runt, seed=seed)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methInt(self, maxval, minval=0):
        maxval = await s_stormtypes.toint(maxval)
        minval = await s_stormtypes.toint(minval)
        if minval > maxval:
            raise s_exc.BadArg(mesg=f'Minval must be less than or equal to maxval, minval={minval}, maxval={maxval}',
                               minval=minval, maxval=maxval)
        return randinst.randint(minval, maxval)
