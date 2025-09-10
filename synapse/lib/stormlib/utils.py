import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibUtils(s_stormtypes.Lib):
    '''
    A Storm library for working with utility functions.
    '''
    _storm_locals = (
        {'name': 'buid',
         'desc': '''
            Calculate a buid from the provided valu.
         ''',
         'type': {'type': 'function', '_funcname': '_buid',
                  'args': (
                      {'name': 'valu', 'type': 'any',
                       'desc': 'The value to calculate the buid from.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The calculated buid.'},
        }},
        {'name': 'todo',
         'desc': '''
            Create a todo tuple of (name, args, kwargs).
         ''',
         'type': {'type': 'function', '_funcname': '_todo',
                  'args': (
                      {'name': '_todoname', 'type': 'str',
                       'desc': 'The todo name.'},
                      {'name': '*args', 'type': 'any',
                       'desc': 'Positional arguments for the todo.'},
                      {'name': '**kwargs', 'type': 'any',
                       'desc': 'Keyword arguments for the todo.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A todo tuple of (name, args, kwargs).'},
        }},
    )
    _storm_lib_path = ('utils',)

    def getObjLocals(self):
        return {
            'buid': self._buid,
            'todo': self._todo,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _buid(self, valu):
        valu = await s_stormtypes.toprim(valu)
        return s_common.buid(valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _todo(self, _todoname, *args, **kwargs):
        _todoname = await s_stormtypes.tostr(_todoname)
        args = await s_stormtypes.toprim(args)
        kwargs = await s_stormtypes.toprim(kwargs)
        return (_todoname, args, kwargs)
