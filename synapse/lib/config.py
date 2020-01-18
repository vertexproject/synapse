import os
import functools

import fastjsonschema

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.hashitem as s_hashitem

confdeftype2jsonschema = {
    'int': 'integer',
    'str': 'string',
    'float': 'number',
    'bool': 'boolean',
    'list': 'array',
    'dict': 'object',
}

def confdefs2jsonschema(confdata):
    '''
    Convert a Synaspe Cell config data into a simple json-schema.
    '''
    propdict = {}
    schema = {'type': 'object',
            'properties': propdict,
            "additionalProperties": False,
            '$schema': 'draft-07',  # TODO - make this a proper js-schema url
            }
    for name, info in confdata:
        styp = info.get('type')
        if styp is None:
            raise Exception(f'oh no! {name} is untyped!')
        jtyp = confdeftype2jsonschema.get(styp)
        if jtyp is None:
            raise Exception(f'oh no! {name} has a unknown type!')
        pdict = {'type': jtyp,
                 }
        for key, jskey in (('doc', 'description'),
                           ('defval', 'default'),
                           ):
            valu = info.get(key)
            if valu is not None:
                pdict[jskey] = valu
        # Provide a hook to allow a Cell author to add additional
        # json-schema data into their configurations.
        jshook = info.get('json_schema_hook')
        if jshook is not None:
            for k, v in jshook.items():
                pdict.setdefault(k, v)
        propdict.setdefault(name, pdict)
    return schema

SCHEMAS = {}

def getSchema(confdata):
    # TODO: Don't implement my own cache...
    key = s_hashitem.hashitem(confdata)
    schema = SCHEMAS.get(key)
    if schema:
        return schema
    schema = confdefs2jsonschema(confdata)
    SCHEMAS[key] = schema
    return schema

class Config:

    def __init__(self, confdefs):
        self.conf = {}
        self.norms = {}
        self.confdefs = confdefs

        for name, defval, norm in confdefs:
            self.norms[name] = norm
            self.conf[name] = defval

    def __iter__(self):
        return iter(list(self.conf.items()))

    async def loadConfDict(self, conf):
        for name, valu in conf.items():
            await self.set(name, valu)

    async def loadConfYaml(self, *path):
        conf = s_common.yamlload(*path)
        return await self.loadConfDict(conf)

    async def loadConfEnvs(self, envn):
        for name, defval, norm in self.confdefs:
            envv = os.getenv(f'{envn}_{name}'.upper())
            if envv is not None:
                await self.set(name, envv)

    def get(self, name):
        return self.conf.get(name)

    async def set(self, name, valu):
        norm = self.norms.get(name)
        if norm is None:
            raise s_exc.NoSuchName(name=name)

        self.conf[name] = norm(valu)
