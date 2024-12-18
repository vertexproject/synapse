import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerType
class Todo(s_stormtypes.Prim):
    '''
    A Storm type representing a todo tuple.
    '''
    _storm_typename = 'todo'
    _ismutable = False

    def __init__(self, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)

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
                  'returns': {'type': 'todo', 'desc': 'A todo tuple of (name, args, kwargs).'},
        }},
    )
    _storm_lib_path = ('utils',)

    def getObjLocals(self):
        return {
            'todo': self._todo,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _todo(self, _todoname, *args, **kwargs):
        return Todo((_todoname, args, kwargs))
