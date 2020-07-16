import os
import copy
import logging
import argparse
import collections.abc as c_abc

import yaml
import fastjsonschema

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.const as s_const
import synapse.lib.output as s_output
import synapse.lib.hashitem as s_hashitem

from fastjsonschema.exceptions import JsonSchemaException

logger = logging.getLogger(__name__)

re_iden = '^[0-9a-f]{32}$'

# Cache of validator functions
_JsValidators = {}  # type: ignore

def getJsSchema(confbase, confdefs):
    '''
    Generate a Synapse JSON Schema for a Cell using a pair of confbase and confdef values.

    Args:
        confbase (dict): A JSON Schema dictionary of properties for the object. This content has
                         precedence over the confdefs argument.
        confdefs (dict): A JSON Schema dictionary of properties for the object.

    Notes:
        This generated a JSON Schema draft 7 schema for a single object, which does not allow for
        additional properties to be set on it.  The data in confdefs is implementer controlled and
        is welcome to specify

    Returns:
        dict: A complete JSON schema.
    '''
    props = {}
    schema = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'additionalProperties': False,
        'properties': props,
        'type': 'object'
    }
    props.update(confdefs)
    props.update(confbase)
    return schema

def getJsValidator(schema):
    '''
    Get a fastjsonschema callable.

    Args:
        schema (dict): A JSON Schema object.

    Returns:
        callable: A callable function that can be used to validate data against the json schema.
    '''
    if schema.get('$schema') is None:
        schema['$schema'] = 'http://json-schema.org/draft-07/schema#'

    # It is faster to hash and cache the functions here than it is to
    # generate new functions each time we have the same schema.
    key = s_hashitem.hashitem(schema)
    func = _JsValidators.get(key)
    if func:
        return func

    func = fastjsonschema.compile(schema)

    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except JsonSchemaException as e:
            raise s_exc.SchemaViolation(mesg=e.message, name=e.name)

    _JsValidators[key] = wrap
    return wrap

jsonschematype2argparse = {
    'integer': int,
    'string': str,
    'boolean': bool,
    'number': float,
}

def make_envar_name(key, prefix=None):
    '''
    Convert a colon delimited string into an uppercase, underscore delimited string.

    Args:
        key (str): Config key to convert.
        prefix (str): Optional string prefix to prepend the the config key.

    Returns:
        str: The string to lookup against a envar.
    '''
    nk = f'{key.replace(":", "_")}'
    if prefix:
        nk = f'{prefix}_{nk}'
    return nk.upper()

class Config(c_abc.MutableMapping):
    '''
    Synapse configuration helper based on JSON Schema.

    Args:
        schema (dict): The JSON Schema (draft v7) which to validate
                       configuration data against.
        conf (dict): Optional, a set of configuration data to preload.
        envar_prefix (str): Optional, a prefix used when collecting configuration
                            data from environment variables.

    Notes:
        This class implements the collections.abc.MutableMapping class, so it
        may be used where a dictionary would otherwise be used.

        The default values provided in the schema must be able to be recreated
        from the repr() of their Python value.

        Default values are not loaded into the configuration data until
        the ``reqConfValid()`` method is called.

    '''
    def __init__(self,
                 schema,
                 conf=None,
                 envar_prefix=None,
                 ):
        self.json_schema = schema
        if conf is None:
            conf = {}
        self.conf = conf
        self._argparse_conf_names = {}
        self._argparse_conf_parsed_names = {}
        self.envar_prefix = envar_prefix
        self.validator = getJsValidator(self.json_schema)

    @classmethod
    def getConfFromCell(cls, cell, conf=None, envar_prefix=None):
        '''
        Get a Config object from a Cell directly (either the ctor or the instance thereof).

        Returns:
            Config: A Config object.
        '''
        schema = getJsSchema(cell.confbase, cell.confdefs)
        return cls(schema, conf=conf, envar_prefix=envar_prefix)

    def getArgParseArgs(self):

        argdata = []

        for (name, conf) in self.json_schema.get('properties').items():

            if conf.get('hideconf'):
                continue

            typename = conf.get('type')
            # only allow single-typed values to have command line arguments
            if not isinstance(typename, str):
                continue

            atyp = jsonschematype2argparse.get(conf.get('type'))
            if atyp is None:
                continue

            akwargs = {
                'help': conf.get('description', ''),
                'action': 'store',
                'type': atyp,
            }

            if atyp is bool:

                default = conf.get('default')
                if default is None:
                    logger.debug(f'Boolean type is missing default information. Will not form argparse for [{name}]')
                    continue
                default = bool(default)
                akwargs['type'] = yaml.safe_load
                akwargs['choices'] = [True, False]
                akwargs['help'] = akwargs['help'] + f' This option defaults to {default}.'

            parsed_name = name.replace(':', '-')
            replace_name = name.replace(':', '_')
            self._argparse_conf_names[replace_name] = name
            self._argparse_conf_parsed_names[name] = parsed_name
            argname = '--' + parsed_name
            argdata.append((argname, akwargs))

        return argdata

    def getCmdlineMapping(self):
        if not self._argparse_conf_parsed_names:
            # Giv a shot at populating the data
            _ = self.getArgParseArgs()
        return {k: v for k, v in self._argparse_conf_parsed_names.items()}

    def setConfFromOpts(self, opts):
        '''
        Set the opts for a conf object from a namespace object.

        Args:
            opts (argparse.Namespace): A Namespace object made from parsing args with an ArgumentParser
            made with getArgumentParser.

        Returns:
            None: Returns None.
        '''
        opts_data = vars(opts)
        for k, v in opts_data.items():
            if v is None:
                continue
            nname = self._argparse_conf_names.get(k)
            if nname is None:
                continue
            self.setdefault(nname, v)

    # Envar support methods
    def setConfFromEnvs(self):
        '''
        Set configuration options from environment variables.

        Notes:
            Environment variables are resolved from configuration options after doing the following transform:

            - Replace ``:`` characters with ``_``.
            - Add a config provided prefix, if set.
            - Uppercase the string.
            - Resolve the environment variable
            - If the environment variable is set, set the config value to the results of ``yaml.yaml_safeload()``
              on the value.

            Configuration values which have the ``hideconf`` value set to True are not resolved from environment
            variables.

        Examples:

            For the configuration value ``auth:passwd``, the environment variable is resolved as ``AUTH_PASSWD``.
            With the prefix ``cortex``, the the environment variable is resolved as ``CORTEX_AUTH_PASSWD``.

        Returns:
            None: Returns None.
        '''
        name2envar = self.getEnvarMapping()
        for name, envar in name2envar.items():
            envv = os.getenv(envar)
            if envv is not None:
                envv = yaml.safe_load(envv)
                resp = self.setdefault(name, envv)
                if resp == envv:
                    logger.debug(f'Set config valu from envar: [{envar}]')

    def getEnvarMapping(self):
        '''
        Get a mapping of config values to envars.

        Configuration values which have the ``hideconf`` value set to True are not resolved from environment
        variables.
        '''
        ret = {}
        for name, conf in self.json_schema.get('properties', {}).items():
            if conf.get('hideconf'):
                continue

            envar = make_envar_name(name, prefix=self.envar_prefix)
            ret[name] = envar
        return ret

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
        try:
            self.validator(self.conf)
        except s_exc.SchemaViolation as e:
            logger.exception('Configuration is invalid.')
            raise s_exc.BadConfValu(mesg=f'Invalid configuration found: [{str(e)}]') from None
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

    def asDict(self):
        '''
        Get a copy of configuration data.

        Returns:
            dict: A copy of the configuration data.
        '''
        return copy.deepcopy(self.conf)

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
