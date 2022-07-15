import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class MathLib(s_stormtypes.Lib):
    '''
    A Storm library for performing math operations.
    '''
    _storm_locals = (
        {'name': 'number', 'desc': 'Convert a value to a Storm Number object.',
         'type': {'type': 'function', '_funcname': '_number',
                  'args': (
                      {'name': 'value', 'type': 'any',
                       'desc': 'Value to convert.', },
                  ),
                  'returns': {'type': 'number', 'desc': 'A Number object.', }}},
    )

    _storm_lib_path = ('math',)

    def getObjLocals(self):
        return {
            'number': self._number,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _number(self, value):
        return s_stormtypes.Number(value)
