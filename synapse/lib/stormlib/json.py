import json
import logging

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerType
class JsonSchema(s_stormtypes.StormType):
    '''
    JsonSchema validation object WORDS GO HERE
    '''
    _storm_typename = 'storm:json:schema'
    _storm_locals = (
        {'name': 'validate',
         'desc': 'Validate a structure against the Json Schema',
         'type': {'type': 'function', '_funcname': '_validate',
                  'args': ({'name': 'item', 'type': 'prim',
                            'desc': 'A JSON structure to validate (dict, list, etc...)', },
                  ),
                  'returns': {'type': 'list',
                              'desc': 'An ($ok, $valu) tuple. If $ok is False, $valu is a dictiony with a "mesg" key.'}}},
    )
    _ismutable = False

    def __init__(self, runt, func, schema):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt
        self.func = func
        self.schema = schema
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'validate': self._validate,
        }

    async def _validate(self, item):
        item = await s_stormtypes.toprim(item)

        try:
            result = self.func(item)
        except s_exc.SchemaViolation as e:
            return False, {'mesg': e.get('mesg')}
        else:
            return True, result

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
        {'name': 'schema', 'desc': 'Get a JS schema validation object.',
         'type': {'type': 'function', '_funcname': '_jsonSchema',
                  'args': ({'name': 'schema', 'type': 'dict',
                            'desc': 'The JsonSchema to use.'},),
                  'returns': {'type': 'storm:json:schema',
                              'desc': 'WORDS GO HERE'}}},
    )
    _storm_lib_path = ('json',)

    def getObjLocals(self):
        return {
            'save': self._jsonSave,
            'load': self._jsonLoad,
            'schema': self._jsonSchema,
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

    async def _jsonSchema(self, schema):
        schema = await s_stormtypes.toprim(schema)
        try:
            func = s_config.getJsValidator(schema)
        except Exception as e:
            raise s_exc.StormRuntimeError(mesg='Unable to compile JsonSchema', schema=schema) from e
        return JsonSchema(self.runt, func, schema)
