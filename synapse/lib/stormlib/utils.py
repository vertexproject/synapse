import synapse.exc as s_exc

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
        {'name': 'tofile',
         'desc': '''
            Upload supplied data to the configured Axon and create a corresponding file:bytes node.
         ''',
         'type': {'type': 'function', '_funcname': '_libUtilsToFile',
                  'args': (
                      {'name': 'valu', 'type': 'bytes',
                       'desc': 'The file data.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'The file:bytes node representing the supplied data.'},
        }},
    )
    _storm_lib_path = ('utils',)

    def getObjLocals(self):
        return {
            'todo': self._libUtilsTodo,
            'tofile': self._libUtilsToFile,
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

    async def _libUtilsToFile(self, valu):
        if not isinstance(valu, bytes):
            mesg = '$lib.utils.tofile() requires a bytes argument.'
            raise s_exc.BadArg(mesg=mesg)

        self.runt.confirm(('axon', 'upload'))

        layriden = self.runt.view.layers[0].iden
        self.runt.confirm(('node', 'add', 'file:bytes'), gateiden=layriden)
        self.runt.confirm(('node', 'prop', 'set', 'file:bytes'), gateiden=layriden)

        await self.runt.view.core.getAxon()
        axon = self.runt.view.core.axon

        size, sha256b = await axon.put(valu)

        props = await axon.hashset(sha256b)
        props['size'] = size

        return await self.runt.view.addNode('file:bytes', props['sha256'], props=props)
