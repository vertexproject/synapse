import copy
import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

def runJsSchema(schema, item, use_default=True):
    # This is a target function for multiprocessing
    func = s_config.getJsValidator(schema, use_default=use_default, handlers=None)
    resp = func(item)
    return resp

def compileJsSchema(schema, use_default=True):
    # This is a target function for multiprocessing
    _ = s_config.getJsValidator(schema, use_default=use_default, handlers=None)
    return True

@s_stormtypes.registry.registerType
class JsonSchema(s_stormtypes.StormType):
    '''
    A JsonSchema validation object for use in validating data structures in Storm.
    '''
    _storm_typename = 'json:schema'
    _storm_locals = (
        {'name': 'schema',
         'desc': 'The schema belonging to this object.',
         'type': {'type': 'function', '_funcname': '_schema',
                  'returns': {'type': 'dict', 'desc': 'A copy of the schema used for this object.', }}},
        {'name': 'validate',
         'desc': 'Validate a structure against the Json Schema',
         'type': {'type': 'function', '_funcname': '_validate',
                  'args': ({'name': 'item', 'type': 'prim',
                            'desc': 'A JSON structure to validate (dict, list, etc...)', },
                  ),
                  'returns': {'type': 'list',
                              'desc': 'An ($ok, $valu) tuple. If $ok is True, then $valu should be used as the '
                                      'validated data structure. If $ok is False, $valu is a dictionary with a "mesg" '
                                      'key.'}}},
    )
    _ismutable = False

    def __init__(self, runt, schema, use_default=True):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt
        self.schema = schema
        self.use_default = use_default
        self.locls.update(self.getObjLocals())

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.schema}'

    def getObjLocals(self):
        return {
            'schema': self._schema,
            'validate': self._validate,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _schema(self):
        return copy.deepcopy(self.schema)

    @s_stormtypes.stormfunc(readonly=True)
    async def _validate(self, item):
        item = await s_stormtypes.toprim(item)

        try:
            result = await s_coro.semafork(runJsSchema, self.schema, item, use_default=self.use_default)
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
                      {'name': 'indent', 'type': 'boolean', 'desc': 'Indent serialized data with two spaces.', 'default': False},
                  ),
                  'returns': {'type': 'str', 'desc': 'The JSON serialized object.', }}},
        {'name': 'schema', 'desc': 'Get a JS schema validation object.',
         'type': {'type': 'function', '_funcname': '_jsonSchema',
                  'args': (
                      {'name': 'schema', 'type': 'dict', 'desc': 'The JsonSchema to use.'},
                      {'name': 'use_default', 'type': 'boolean', 'default': True,
                       'desc': 'Whether to insert default schema values into the validated data structure.'},
                  ),
                  'returns': {'type': 'json:schema',
                              'desc': 'A validation object that can be used to validate data structures.'}}},
    )
    _storm_lib_path = ('json',)

    def getObjLocals(self):
        return {
            'save': self._jsonSave,
            'load': self._jsonLoad,
            'schema': self._jsonSchema,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _jsonSave(self, item, indent=False):
        indent = await s_stormtypes.tobool(indent)

        try:
            item = await s_stormtypes.toprim(item)
        except Exception:
            mesg = f'Argument is not JSON compatible: {item}'
            raise s_exc.MustBeJsonSafe(mesg=mesg)

        return s_json.dumps(item, indent=indent).decode()

    @s_stormtypes.stormfunc(readonly=True)
    async def _jsonLoad(self, text):
        text = await s_stormtypes.tostr(text)
        return s_json.loads(text)

    @s_stormtypes.stormfunc(readonly=True)
    async def _jsonSchema(self, schema, use_default=True):
        schema = await s_stormtypes.toprim(schema)
        use_default = await s_stormtypes.tobool(use_default)
        # We have to ensure that we have a valid schema for making the object.
        try:
            await s_coro.semafork(compileJsSchema, schema, use_default=use_default)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            raise s_exc.StormRuntimeError(mesg=f'Unable to compile Json Schema: {str(e)}', schema=schema) from e
        return JsonSchema(self.runt, schema, use_default=use_default)
