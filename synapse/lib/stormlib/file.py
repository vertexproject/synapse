import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibFile(s_stormtypes.Lib):
    '''
    A Storm Library with various file functions.
    '''
    _storm_locals = (
        {'name': 'frombytes',
         'desc': '''
            Upload supplied data to the configured Axon and create a corresponding file:bytes node.
         ''',
         'type': {'type': 'function', '_funcname': '_libFileFromBytes',
                  'args': (
                      {'name': 'valu', 'type': 'bytes',
                       'desc': 'The file data.'},
                  ),
                  'returns': {'type': 'node', 'desc': 'The file:bytes node representing the supplied data.'},
        }},
    )
    _storm_lib_path = ('file',)

    def getObjLocals(self):
        return {
            'frombytes': self._libFileFromBytes,
        }

    async def _libFileFromBytes(self, valu):
        if not isinstance(valu, bytes):
            mesg = '$lib.file.frombytes() requires a bytes argument.'
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
