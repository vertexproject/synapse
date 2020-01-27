import os
import copy
import logging
import argparse
import collections.abc as c_abc

import yaml
import fastjsonschema

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cache as s_cache

import synapse.lib.hashitem as s_hashitem

logger = logging.getLogger(__name__)

SCHEMAS = {}

def genSchema(confbase, confdefs):
    props = {}
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
        "properties": props,
        "type": "object"
    }
    props.update(confdefs)
    props.update(confbase)
    return schema

def getSchema(confdefs, confbase):
    key = s_hashitem.hashitem((confdefs, confbase))
    schema = SCHEMAS.get(key)
    if schema:
        return schema
    schema = genSchema(confbase, confdefs)
    SCHEMAS[key] = schema
    return schema

jsonschematype2argparse = {
    'integer': int,
    'string': str,
    'boolean': bool,
    'number': float,
}

def make_envar_name(key, prefix: str =None) -> str:
    nk = f'{key.replace(":", "_")}'.upper()
    if prefix:
        nk = f'{prefix}_{nk}'
    return nk

class Config020(c_abc.MutableMapping):
    '''
    Synapse configuration helper based on JSON Schema.

    Args:
        schema (dict): The JSON Schema (draft v7) which to validate
        configuration data against.
        conf (dict): Optional, a set of configuration data to preload.
        envar_prefix (str): Optional, a prefix used when collecting
        configuration data from environmental variables.

    Notes:
        This class implements the collections.abc.MuttableMapping class, so it
        may be used where a dictionary would otherwise be used.

        The default values provided in the schema must be able to be recreated
        from the repr() of their Python value.

        Default values are not loaded into the configuration data until
        the ``reqConfValid()`` method is called.

    '''
    def __init__(self,
                 schema: dict,
                 conf: dict =None,
                 envar_prefix: str =None,
                 ):
        self.json_schema = schema
        if conf is None:
            conf = {}
        self.conf = conf
        self._argparse_conf_names = {}
        self.envar_prefix = envar_prefix
        # TODO Cache this if FJS does't already cache things...
        self.validator = fastjsonschema.compile(self.json_schema)

    @classmethod
    def getConfFromCell(cls, cell):
        schema = getSchema(cell.confdefs, cell.confbase)
        return cls(schema)

    # Argparse support methods
    def generateArgparser(self, pars: argparse.ArgumentParser =None) -> argparse.ArgumentParser:
        '''
        Add config related arguments group to an argument parser.

        Notes:
            Makes a new argument parser if one is not provided.

            Configuration data is placed in the argument group called ``config``.
        '''
        if pars is None:
            pars = argparse.ArgumentParser()
        agrp = pars.add_argument_group('config', 'Configuration arguments.')
        self._addArgparseArguments(agrp)
        return pars

    def _addArgparseArguments(self, obj: argparse._ArgumentGroup):
        for (name, conf) in self.json_schema.get('properties').items():
            atyp = jsonschematype2argparse.get(conf.get('type'))
            if atyp is None:
                continue
            akwargs = {'help': conf.get('description', ''),
                       'action': 'store',
                       'type': atyp,
                       'default': s_common.novalu
                       }

            if atyp is bool:
                akwargs.pop('type')
                default = conf.get('default')
                if default is None:
                    logger.debug(f'Boolean type is missing default information. Will not form argparse for [{name}]')
                    continue
                default = bool(default)
                # Do not use the default value!
                if default:
                    akwargs['action'] = 'store_false'
                    akwargs['help'] = akwargs['help'] + \
                                      ' Set this value to disable this option.'
                else:
                    akwargs['action'] = 'store_true'
                    akwargs['help'] = akwargs['help'] + \
                                      ' Set this value to enable this option.'

            parsed_name = name.replace(':', '-')
            replace_name = name.replace(':', '_')
            self._argparse_conf_names[replace_name] = name
            argname = '--' + parsed_name
            obj.add_argument(argname, **akwargs)

    def setConfFromOpts(self, opts: argparse.Namespace):
        opts_data = vars(opts)
        for k, v in opts_data.items():
            if v is s_common.novalu:
                continue
            nname = self._argparse_conf_names.get(k)
            if nname is None:
                continue
            self.setdefault(nname, v)

    # Envar support methods
    def setConfEnvs(self):
        for (name, info) in self.json_schema.get('properties', {}).items():
            envar = make_envar_name(name, prefix=self.envar_prefix)
            envv = os.getenv(envar)
            if envv is not None:
                logger.debug(f'Loading config valu from: [{envar}]')
                envv = yaml.safe_load(envv)
                self.setdefault(name, envv)

    # General methods
    def reqConfValid(self):
        '''
        Validate that the loaded configuration data is valid according to the schema.

        Notes:
            The validation set does set any default values which are not currently
            set for configuration options.

        Returns:
            None: This returns nothing.
        '''
        # TODO: Wrap and raise a s_exc.SynErr...
        try:
            self.validator(self.conf)
        except fastjsonschema.exceptions.JsonSchemaException as e:
            logger.exception('Configuration is invalid.')
            raise s_exc.BadConfValu(mesg=str(e)) from None
        else:
            return
    def reqConfValu(self, key):
        '''
        Get a configuration value.  If that value is not present in the schema
        or is not set, then raise an exception.

        Args:
            key (str): The key to require.

        Returns:
            The requested value.
        '''
        # Ensure that the key is in self.json_schema
        if key not in self.json_schema.get('properties', {}):
            raise s_exc.BadArg(mesg='Required key is not present in the configuration schema.',
                               key=key)

        # Ensure that the key is present in self.conf
        if key not in self.conf:
            raise s_exc.NeedConfValu(mesg='Required key is not present in configuration data.',
                                     key=key)

        return self.conf.get(key)

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
