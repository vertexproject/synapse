import random

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

randinst = random.SystemRandom()

@s_stormtypes.registry.registerLib
class LibRandom(s_stormtypes.Lib):
    '''
    A Storm library for generating random values.
    '''
    _storm_locals = (
        {'name': 'int', 'desc': 'Generate a random integer.',
         'type': {'type': 'function', '_funcname': '_int',
                  'args': (
                      {'name': 'maxval', 'type': 'int', 'desc': 'The maximum random value.'},
                      {'name': 'minval', 'type': 'int', 'desc': 'The minimum random value.', 'default': 0},
                  ),
                  'returns': {'type': 'int', 'desc': 'A random integer in the range min-max inclusive.'}}},
    )
    _storm_lib_path = ('random',)

    def getObjLocals(self):
        return {
            'int': self._int,
        }

    async def _int(self, maxval, minval=0):
        maxval = await s_stormtypes.toint(maxval)
        minval = await s_stormtypes.toint(minval)
        if minval > maxval:
            raise s_exc.BadArg(mesg=f'Minval must be less than or equal to maxval, minval={minval}, maxval={maxval}',
                               minval=minval, maxval=maxval)
        return randinst.randint(minval, maxval)
