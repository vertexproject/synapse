import os
import argparse

import yaml

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

import synapse.lib.config as s_config

test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
        "properties": {
            'key:string': {
                'description': 'Key String. I have a defval!',
                'type': 'string',
                'default': 'Default string!'
            },
            'key:integer': {
                'description': 'Key Integer',
                'type': 'integer',
            },
            'key:number': {
                'description': 'Key Number',
                'type': 'number',
            },
            'key:object': {
                'description': 'Key Object',
                'type': 'object',
            },
            'key:array': {
                'description': 'Key Array',
                'type': 'array',
            },
            'key:bool:defvalfalse': {
                'description': 'Key Bool, defval false.',
                'type': 'boolean',
                'default': True,
            },
            'key:bool:defvaltrue': {
                'description': 'Key Bool, defval true.',
                'type': 'boolean',
                'default': False,
            },

            'key:bool:nodefval': {
                'description': 'Key Bool, no default.',
                'type': 'boolean',
            },
        },
        'type': 'object',
    }

class ConfTest(s_test.SynTest):

    async def test_config_basics(self):

        conf = s_config.Config(test_schema)
        # Start out empty
        self.eq(conf.asDict(), {})

        # We can make an argparser that has config options populated in it
        # We explicitly skip boolean options without a default value so we
        # done end up in a ambiguous toggle case down the road.
        mesg = 'Boolean type is missing default information. ' \
               'Will not form argparse for [key:bool:nodefval]'
        pars = argparse.ArgumentParser('synapse.tests.test_lib_config.basics')
        pars.add_argument('--beep', type=str, help='beep option', default='beep.sys')
        with self.getLoggerStream('synapse.lib.config', mesg) as stream:
            pars = conf.generateArgparser(pars=pars)
            self.true(stream.wait(3))
        hmsg = pars.format_help()

        # Multiple types are supported for argparse and descriptions
        # are used to generate the argparse help
        self.isin('--key-string KEY_STRING', hmsg)
        self.isin('Key String. I have a defval!', hmsg)
        self.isin('--key-integer KEY_INTEGER', hmsg)
        self.isin('--key-number KEY_NUMBER', hmsg)
        self.isin('--key-bool-defvalfalse', hmsg)
        self.isin('--key-bool-defvaltrue', hmsg)
        # The pre-existing parse is modified
        self.isin('--beep', hmsg)
        # We do not populate options for complex types
        self.notin('Key Array', hmsg)
        self.notin('Key Object', hmsg)
        # We do not populate options for bools with missing defaults
        self.notin('Key Bool, no default', hmsg)

        # And we can get the data too!  Unspecified values are set to
        # s_common.novalu so we know that they were NOT set at all.
        # This differs from the default argparse case of defaults being
        # set to None, and allows us to defer the injection of default
        # values to the jsonschema validation phase.
        args = ['--key-number', '1234.5678', '--key-bool-defvaltrue']
        opts = pars.parse_args(args)
        vopts = vars(opts)
        edata = {
            'key_bool_defvalfalse': s_common.novalu,
            'key_bool_defvaltrue': True,
            'key_integer': s_common.novalu,
            'key_number': 1234.5678,
            'key_string': s_common.novalu,
            'beep': 'beep.sys'
        }
        self.eq(edata, vopts)

        # We can re-inject the opts back into the config object.
        # The s_common.novalu data is skipped, as are opts which
        # were not set by the schema data.
        conf.setConfFromOpts(opts)
        self.eq(conf.asDict(), {
            'key:bool:defvaltrue': True,
            'key:number': 1234.5678,
        })

        # We can also get and load confdef data from environmental
        # variables. These must be safe to decode as yaml. This
        # is mainly to faciliate machine base management of envars.
        a1 = yaml.safe_dump(['firetruck', 'spaceship'])
        i1 = yaml.safe_dump(8675309)
        n1 = yaml.safe_dump(9.813)
        # Load data from envars next - this shows precedence as well
        # where data already set won't be set again via this method.
        with self.setTstEnvars(KEY_ARRAY=a1,
                               KEY_NUMBER=n1,
                               KEY_INTEGER=i1,
                               ):
            conf.setConfEnvs()

        self.eq(conf.asDict(), {
            'key:bool:defvaltrue': True,
            'key:number': 1234.5678,
            'key:integer': 8675309,
            'key:array': ['firetruck', 'spaceship']
        })
