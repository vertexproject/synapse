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
        {'name': 'todo',
         'desc': '''
            Create a todo tuple of (name, args, kwargs).
         ''',
         'type': {'type': 'function', '_funcname': '_libUtilsTodo',
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
            'todo': self._libUtilsTodo,
            'type': self._libUtilsType,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _libUtilsType(self, valu):
        return await s_stormtypes.totype(valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _libUtilsTodo(self, _todoname, *args, **kwargs):
        _todoname = await s_stormtypes.tostr(_todoname)
        args = await s_stormtypes.toprim(args)
        kwargs = await s_stormtypes.toprim(kwargs)
        return (_todoname, args, kwargs)
