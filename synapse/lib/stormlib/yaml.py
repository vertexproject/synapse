import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes

import yaml

@s_stormtypes.registry.registerLib
class LibYaml(s_stormtypes.Lib):
    '''
    A Storm Library for saving/loading YAML data.
    '''
    _storm_locals = (
        {'name': 'save', 'desc': 'Encode data as a YAML string.',
         'type': {'type': 'function', '_funcname': '_encode',
                  'args': (
                      {'name': 'valu', 'type': 'object', 'desc': 'The object to encode.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'A YAML string.', }}},
        {'name': 'load', 'desc': 'Decode a YAML string/bytes into an object.',
         'type': {'type': 'function', '_funcname': 'load',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The string to decode.', },
                  ),
                  'returns': {'type': 'obj', 'desc': 'A bytes object for the decoded data.', }}},
    )
    _storm_lib_path = ('yaml',)

    def getObjLocals(self):
        return {
            'save': self.save,
            'load': self.load,
        }

    async def save(self, valu):
        valu = await s_stormtypes.toprim(valu)
        return yaml.safe_dump(valu)

    async def load(self, valu):
        valu = await s_stormtypes.tostr(valu)
        return yaml.safe_load(valu)
