import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

import yaml
import yaml.error

@s_stormtypes.registry.registerLib
class LibYaml(s_stormtypes.Lib):
    '''
    A Storm Library for saving/loading YAML data.
    '''
    _storm_locals = (
        {'name': 'save', 'desc': 'Encode data as a YAML string.',
         'type': {'type': 'function', '_funcname': 'save',
                  'args': (
                      {'name': 'valu', 'type': 'object', 'desc': 'The object to encode.'},
                      {'name': 'sort_keys', 'type': 'boolean', 'desc': 'Sort object keys.', 'default': True},
                  ),
                  'returns': {'type': 'str', 'desc': 'A YAML string.'}}},
        {'name': 'load', 'desc': 'Decode a YAML string/bytes into an object.',
         'type': {'type': 'function', '_funcname': 'load',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The string to decode.'},
                  ),
                  'returns': {'type': 'prim', 'desc': 'The decoded primitive object.'}}},
    )
    _storm_lib_path = ('yaml',)

    def getObjLocals(self):
        return {
            'save': self.save,
            'load': self.load,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def save(self, valu, sort_keys=True):
        valu = await s_stormtypes.toprim(valu)
        sort_keys = await s_stormtypes.tobool(sort_keys)
        return yaml.dump(valu, sort_keys=sort_keys, Dumper=s_common.Dumper)

    @s_stormtypes.stormfunc(readonly=True)
    async def load(self, valu):
        valu = await s_stormtypes.tostr(valu)
        try:
            return s_common.yamlloads(valu)
        except yaml.error.YAMLError as e:
            raise s_exc.BadArg(mesg=f'Invalid YAML text: {str(e)}')
