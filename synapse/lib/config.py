import os
import logging
import argparse
import collections.abc as c_abc

import yaml
import fastjsonschema

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.hashitem as s_hashitem

logger = logging.getLogger(__name__)


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

confdeftype2jargparse = {
    'int': int,
    'str': str,
    'bool': bool,
    'float': float,
}

def make_envar_name(key, prefix: str =None) -> str:
    nk = f'{key.replace(":", "_")}'.upper()
    if prefix:
        nk = f'{prefix}_{nk}'
    return nk

class Config020(c_abc.MutableMapping):
    def __init__(self, confdata, conf=None, reqvalid=True, envar_prefix=None,):
        self.confdata = confdata
        if conf is None:
            conf = {}
        self.conf = conf
        self.reqvalid = reqvalid
        self._argparse_conf_names = {}
        self.envar_prefix = envar_prefix

    # Argparse support methods
    def generateArgparser(self, pars=None):
        if pars is None:
            pars = argparse.ArgumentParser()
        agrp = pars.add_argument_group('config', 'Configuration arguments.')
        self._addArgparseArguements(agrp)
        return pars

    def _addArgparseArguements(self, obj: argparse._ArgumentGroup):
        for (name, conf) in self.confdata:
            akwargs = {'help': conf.get('doc'),
                       'action': 'store',
                       }
            atyp = confdeftype2jargparse.get(conf.get('type'))
            if atyp is None:
                continue
            akwargs['type'] = atyp

            parsed_name = name.replace(':', '-')
            replace_name = name.replace(':', '_')
            self._argparse_conf_names[replace_name] = name
            argname = '--' + parsed_name
            obj.add_argument(argname, **akwargs)

    def setConfFromOpts(self, opts: argparse.Namespace):
        opts_data = vars(opts)
        for k, v in opts_data.items():
            nname = self._argparse_conf_names.get(k)
            if nname is None:
                continue
            self.setdefault(nname, v)

    # Envar support methods
    def loadConfEnvs(self):
        for (k, info) in self.confdata:
            envar = make_envar_name(k, prefix=self.envar_prefix)
            envv = os.getenv(envar)
            if envv is not None:
                logger.debug(f'Loading config valu from: [{envar}]')
                envv = yaml.safe_load(envv)
                self.setdefault(k, envv)

    # General methods
    def reqValidConf(self):
        if not self.reqvalid:
            return None
        # TODO - Make this raise on a invalid configuration
        # when we are doing type validation.
        return None

    # be nice...
    def __repr__(self):
        info = [self.__class__.__module__ + '.' + self.__class__.__name__]
        info.append(f'at {hex(id(self))}')
        info.append(f'conf={self.conf}')
        return '<{}>'.format(' '.join(info))

    # ABC methods
    def __len__(self):
        return len(self.conf)

    def __iter__(self):
        return self.conf.__iter__()

    def __delitem__(self, key):
        return self.conf.__delitem__(key)

    def __setitem__(self, key, value):
        # This explicitly doesn't do any type validation.
        # The type validation is done on-demand, in order to
        # allow a user to incrementally construct the config
        # from different sources before turning around and
        # doing a validation pass which may fail.
        return self.conf.__setitem__(key, value)

    def __getitem__(self, item):
        return self.conf.__getitem__(item)

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
