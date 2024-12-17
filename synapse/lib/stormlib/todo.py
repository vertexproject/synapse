import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerType
class Todo(s_stormtypes.Prim):
    _storm_typename = 'todo'
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the todo.', 'type': 'str'},
        {'name': 'args', 'desc': 'The arguments of the todo.', 'type': 'list'},
        {'name': 'kwargs', 'desc': 'The keyword arguments of the todo.', 'type': 'dict'},
    )

    def __init__(self, runt, valu):
        s_stormtypes.Prim.__init__(self, None)
        self.runt = runt
        if isinstance(valu, (list, tuple)):
            self.name = valu[0]
            self.args = () if len(valu) < 2 else valu[1] if isinstance(valu[1], (list, tuple)) else (valu[1],)
            self.kwargs = {} if len(valu) < 3 else valu[2] if isinstance(valu[2], dict) else {}

        self.locls.update({
            'name': self.name,
            'args': self.args,
            'kwargs': self.kwargs,
        })

    def value(self):
        return (self.name, self.args, self.kwargs)

@s_stormtypes.registry.registerLib
class LibTodo(s_stormtypes.Lib):
    '''
    A Storm library for parsing todo strings.
    '''
    _storm_locals = (
        {'name': 'parse', 'desc': 'Parse a todo string into a todo object.',
         'type': {'type': 'function', '_funcname': 'parse',
            'args': (
                {'name': 'valu', 'type': 'str', 'desc': 'The todo string to parse into a todo object.'},
            ),
            'returns': {'type': 'todo', 'desc': 'A todo object.'},
        }},
    )
    _storm_lib_path = ('todo',)

    def getObjLocals(self):
        return {
            'parse': self.parse,
        }

    async def parse(self, valu):
        todo = await s_stormtypes.toprim(valu)
        if isinstance(todo, str):
            parts = todo.split()
            name = parts[0]
            args = []
            kwargs = {}

            for part in parts[1:]:
                if part.startswith('--'):
                    if len(parts) > parts.index(part) + 1:
                        key = part[2:]
                        val = parts[parts.index(part) + 1]
                        kwargs[key] = val
                elif not parts[parts.index(part) - 1].startswith('--'):
                    args.append(part)

            return Todo(self.runt, (name, tuple(args), kwargs))
        return Todo(self.runt, todo)
