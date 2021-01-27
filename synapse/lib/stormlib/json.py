import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

import json

@s_stormtypes.registry.registerLib
class JsonLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Json data.
    '''
    _storm_locals = (
        {'name': 'load', 'desc': 'Parse a JSON string and return the deserialized data.',
         'type': {'type': 'function', '_funcname': '_jsonLoad',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The string to be deserialized.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The JSON deserialized object.', }}},
        {'name': 'save', 'desc': 'Save an object as a JSON string.',
         'type': {'type': 'function', '_funcname': '_jsonSave',
                  'args': (
                      {'name': 'item', 'type': 'any', 'desc': 'The item to be serialized as a JSON string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The JSON serialized object.', }}},
    )
    _storm_lib_path = ('json',)

    def getObjLocals(self):
        return {
            'save': self._jsonSave,
            'load': self._jsonLoad,
        }

    async def _jsonSave(self, item):
        try:
            item = await s_stormtypes.toprim(item)
            return json.dumps(item)
        except Exception as e:
            mesg = f'Argument is not JSON compatible: {item}'
            raise s_exc.MustBeJsonSafe(mesg=mesg)

    async def _jsonLoad(self, text):
        text = await s_stormtypes.tostr(text)
        try:
            return json.loads(text, strict=True)
        except Exception as e:
            mesg = f'Text is not valid JSON: {text}'
            raise s_exc.BadJsonText(mesg=mesg)
