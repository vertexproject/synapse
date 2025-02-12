import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibUtils(s_stormtypes.Lib):
    '''
    A Storm library for working with utility functions.
    '''
    _storm_locals = (
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
            'todo': self._todo,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _todo(self, _todoname, *args, **kwargs):
        _todoname = await s_stormtypes.tostr(_todoname)
        args = await s_stormtypes.toprim(args)
        kwargs = await s_stormtypes.toprim(kwargs)
        return (_todoname, args, kwargs)
