import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

import json

@s_stormtypes.registry.registerLib
class JsonLib(s_stormtypes.Lib):

    _storm_lib_path = ('json',)

    def getObjLocals(self):
        return {
            'save': self._jsonSave,
            'load': self._jsonLoad,
        }

    async def _jsonSave(self, item):
        '''
        Save an object as a JSON string.
        '''
        try:
            item = await s_stormtypes.toprim(item)
            return json.dumps(item)
        except Exception as e:
            mesg = f'Argument is not JSON compatible: {item}'
            raise s_exc.MustBeJsonSafe(mesg=mesg)

    async def _jsonLoad(self, text):
        '''
        Parse a JSON string and return an object.
        '''
        text = await s_stormtypes.tostr(text)
        try:
            return json.loads(text, strict=True)
        except Exception as e:
            mesg = f'Text is not valid JSON: {text}'
            raise s_exc.BadJsonText(mesg=mesg)
