import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibUtils(s_stormtypes.Lib):
    '''
    A Storm Library with various utility functions.
    '''
    _storm_locals = (
        {'name': 'type', 'desc': 'Get the type of the argument value.',
         'type': {'type': 'function', '_funcname': '_libUtilsType',
                  'args': (
                     {'name': 'valu', 'type': 'any', 'desc': 'Value to inspect.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The type of the argument.'}}},
    )
    _storm_lib_path = ('utils',)

    def getObjLocals(self):
        return {
            'type': self._libUtilsType,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _libUtilsType(self, valu):
        return await s_stormtypes.totype(valu)
