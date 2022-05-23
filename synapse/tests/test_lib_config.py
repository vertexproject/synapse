import copy
import regex
import argparse

import yaml

import synapse.exc as s_exc

import synapse.lib.cell as s_cell

import synapse.lib.config as s_config

import synapse.tests.utils as s_test

class SchemaCell(s_cell.Cell):
    confbase = {
        'apikey': {
            'description': 'fancy apikey',
            'type': 'string',
        },
        'apihost': {
            'description': 'host where the apikey goes too!',
            'type': 'string',
            'default': 'https://httpbin.org/'
        },
    }
    async def __anit__(self, dirn, conf=None, readonly=False, *args, **kwargs):
        await s_cell.Cell.__anit__(self, dirn, conf, readonly, *args, **kwargs)
        # This captures a design pattern that reduces boilerplate
        # code used by Cell implementators.
        self.conf.reqConfValu('apikey')


class ConfTest(s_test.SynTest):

    async def test_config_basics(self):

        conf = s_config.Config(s_test.test_schema, envar_prefixes=('', 'ALT',))
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
            for optname, optinfo in conf.getArgParseArgs():
                pars.add_argument(optname, **optinfo)
            self.true(stream.wait(3))
        hmsg = pars.format_help()

        # Undo pretty-printing
        hmsg = regex.sub(r'\s\s+', ' ', hmsg)

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
        args = ['--key-number', '1234.5678', '--key-bool-defvaltrue', 'false']
        opts = pars.parse_args(args)
        vopts = vars(opts)
        edata = {
            'key_bool_defvalfalse': None,
            'key_bool_defvaltrue': False,
            'key_integer': None,
            'key_number': 1234.5678,
            'key_string': None,
            'beep': 'beep.sys',
            'key_foo': None,
        }
        self.eq(edata, vopts)

        # We can re-inject the opts back into the config object.
        # The s_common.novalu data is skipped, as are opts which
        # were not set by the schema data.
        conf.setConfFromOpts(opts)
        self.eq(conf.asDict(), {
            'key:bool:defvaltrue': False,
            'key:number': 1234.5678,
        })

        # We can also get and load confdef data from environment
        # variables. These must be safe to decode as yaml. This
        # is mainly to faciliate machine base management of envars.
        a1 = yaml.safe_dump(['firetruck', 'spaceship'])
        i1 = yaml.safe_dump(8675309)
        n1 = yaml.safe_dump(9.813)
        f1 = yaml.safe_dump('foo')
        # Load data from envars next - this shows precedence as well
        # where data already set won't be set again via this method.
        with self.setTstEnvars(KEY_ARRAY=a1,
                               KEY_NUMBER=n1,
                               KEY_INTEGER=i1,
                               ):
            updates = conf.setConfFromEnvs()
        self.eq(updates, {'key:array': ('firetruck', 'spaceship'), 'key:integer': 8675309})
        with self.setTstEnvars(KEY_ARRAY=a1,
                               ALT_KEY_FOO=f1
                               ):
            updates = conf.setConfFromEnvs()
        self.eq(updates, {'key:foo': 'foo'})

        self.eq(conf.asDict(), {
            'key:bool:defvaltrue': False,
            'key:number': 1234.5678,
            'key:integer': 8675309,
            'key:array': ['firetruck', 'spaceship'],
            'key:foo': 'foo',
        })

        # we can set some remaining values directly
        conf.setdefault('key:object', {'rubber': 'ducky'})
        conf.setdefault('key:string', 'Funky string time!')
        self.eq(conf.asDict(), {
            'key:bool:defvaltrue': False,
            'key:number': 1234.5678,
            'key:integer': 8675309,
            'key:array': ['firetruck', 'spaceship'],
            'key:object': {'rubber': 'ducky'},
            'key:string': 'Funky string time!',
            'key:foo': 'foo',
        })

        # Once we've built up our config, we can then ensure that it is valid.
        # This validation step also sets vars with defaults.  Keys without defaults
        # are not set at all.
        self.none(conf.reqConfValid())
        self.eq(conf.asDict(), {
            'key:bool:defvalfalse': False,
            'key:bool:defvaltrue': False,
            'key:number': 1234.5678,
            'key:integer': 8675309,
            'key:array': ['firetruck', 'spaceship'],
            'key:object': {'rubber': 'ducky'},
            'key:string': 'Funky string time!',
            'key:foo': 'foo',
        })

        # We can ensure that certain vars are loaded
        self.eq('Funky string time!', conf.reqConfValu('key:string'))
        # And throw if they are not, or if the requested key isn't even schema valid
        self.raises(s_exc.NeedConfValu, conf.reqConfValu, 'key:bool:nodefval')
        self.raises(s_exc.BadArg, conf.reqConfValu, 'key:newp')

        # Since we're an Mutable mapping, we have some dict methods available to us
        self.len(8, conf)  # __len__
        self.eq(set(conf.keys()),  # __iter__
                {'key:bool:defvalfalse', 'key:bool:defvaltrue',
                 'key:number', 'key:integer', 'key:string',
                 'key:array', 'key:object', 'key:foo',
                 })

        del conf['key:object']  # __delitem__
        self.eq(conf.asDict(), {
            'key:bool:defvalfalse': False,
            'key:bool:defvaltrue': False,
            'key:number': 1234.5678,
            'key:integer': 8675309,
            'key:array': ['firetruck', 'spaceship'],
            'key:string': 'Funky string time!',
            'key:foo': 'foo',
        })

        # We have a convenience __repr__ :)
        valu = repr(conf)
        self.isin('<synapse.lib.config.Config at 0x', valu)
        self.isin('conf={', valu)

        # All items are validated when they are set.
        conf.pop('key:array')
        with self.raises(s_exc.BadArg):
            conf['key:newp:newp:newp'] = 'newp'
        with self.raises(s_exc.BadConfValu) as cm:
            conf['key:array'] = 'Totally not an array.'
        with self.raises(s_exc.BadConfValu):
            conf.update({'key:array': 'Totally not an array.'})
        with self.raises(s_exc.BadConfValu):
            conf.setdefault('key:array', 'Totally not an array.')

        # Including envar sets
        with self.raises(s_exc.BadConfValu):
            with self.setTstEnvars(KEY_ARRAY=None,
                                   ):
                conf.setConfFromEnvs()

        # We can do prefix-bassed collection of envar data.
        conf2 = s_config.Config(s_test.test_schema, envar_prefixes=('beeper',))
        with self.setTstEnvars(BEEPER_KEY_ARRAY=a1,
                               KEY_INTEGER=i1,
                               ):
            conf2.setConfFromEnvs()
        # key:array is set, key:integer is not set.
        self.eq(conf2.asDict(), {
            'key:array': ['firetruck', 'spaceship']
        })

    async def test_config_fromcell(self):

        # We can make a conf from a cell ctor directly
        conf = s_config.Config.getConfFromCell(SchemaCell)
        self.isin('apikey', conf.json_schema.get('properties'))
        self.isin('apihost', conf.json_schema.get('properties'))

        # Bad data is bad
        with self.raises(s_exc.BadArg) as cm:
            s_config.Config.getConfFromCell(SchemaCell, {'test:newp': 'haha'})

        with self.raises(s_exc.BadConfValu) as cm:
            s_config.Config.getConfFromCell(SchemaCell, {'apikey': 1234})
        self.eq(cm.exception.get('name'), 'apikey')

        # Assuming we populate that conf with some data
        # we can then use it to make a cell!

        conf['apikey'] = 'deadb33f'

        with self.getTestDir() as dirn:

            async with await SchemaCell.anit(dirn, conf=conf) as cell:
                self.eq(cell.conf.asDict(),
                        {'apikey': 'deadb33f',
                         'apihost': 'https://httpbin.org/'})

            # We can still make a cell with a dictionary being passed in directly.
            # The dictionary value is converted into the conf value.
            async with await SchemaCell.anit(dirn, conf={'apikey': 'deadb33f'}) as cell:
                self.eq(cell.conf.asDict(),
                        {'apikey': 'deadb33f',
                         'apihost': 'https://httpbin.org/'})

            with self.raises(s_exc.NeedConfValu) as cm:
                # Trying to make a cell with a missing key it wants fails
                async with await SchemaCell.anit(dirn, conf={}) as cell:
                    pass
            self.eq(cm.exception.get('key'), 'apikey')

    def test_hideconf(self):
        hide_schema = {
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
                    'hideconf': True,
                },
            }
        }
        conf = s_config.Config(hide_schema)
        pars = argparse.ArgumentParser('synapse.tests.test_lib_config.test_hideconf')
        for optname, optinfo in conf.getArgParseArgs():
            pars.add_argument(optname, **optinfo)

        # key:integer is not present in cmdline
        hmsg = pars.format_help()
        self.isin('--key-string', hmsg)
        self.notin('--key-integer', hmsg)

        s1 = yaml.safe_dump('We all float down here')
        i1 = yaml.safe_dump(8675309)
        # Load data from envars next - this shows that we won't
        # set the key:integer value
        with self.setTstEnvars(KEY_STRING=s1,
                               KEY_INTEGER=i1,
                               ):
            conf.setConfFromEnvs()
        self.eq(conf.get('key:string'), 'We all float down here')
        self.none(conf.get('key:integer'))

        # hidearg instead of hideconf
        hide_schema = {
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
                    'arg': True,
                    'hidecmdl': True,
                },
            }
        }
        conf = s_config.Config(hide_schema)
        pars = argparse.ArgumentParser('synapse.tests.test_lib_config.test_hideconf')
        for optname, optinfo in conf.getArgParseArgs():
            pars.add_argument(optname, **optinfo)

        # key:integer is not present in cmdline
        hmsg = pars.format_help()
        self.isin('--key-string', hmsg)
        self.notin('--key-integer', hmsg)

        s1 = yaml.safe_dump('We all float down here')
        i1 = yaml.safe_dump(8675309)
        # Load data from envars next - this shows we will
        # set the key:integer value
        with self.setTstEnvars(KEY_STRING=s1,
                               KEY_INTEGER=i1,
                               ):
            conf.setConfFromEnvs()
        self.eq(conf.get('key:string'), 'We all float down here')
        self.eq(conf.get('key:integer'), 8675309)

    def test_jsvalidator(self):

        schema = copy.deepcopy(s_test.test_schema)

        validator = s_config.getJsValidator(schema)
        item = validator({'key:number': 123})
        self.eq(item['key:number'], 123)
        self.eq(item['key:string'], 'Default string!')

        validator = s_config.getJsValidator(schema, use_default=False)
        item = validator({'key:number': 123})
        self.eq(item['key:number'], 123)
        self.notin('key:string', item)
