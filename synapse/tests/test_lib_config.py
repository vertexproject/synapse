import os
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

import synapse.lib.config as s_config

confdefs = (
    ('ikey', {'type': 'int', 'defval': 1},),
    ('skey', {'type': 'str', 'defval': '1'},),
    ('bkey', {'type': 'bool', 'defval': False},),
    ('dkey', {'type': 'dict', 'defval': {'hehe': 'haha'}},),
    ('lkey1', {'type': 'list', 'defval': [{'hehe': 'haha'}]},),
    ('lkey2', {'type': 'list'}),
    ('fkey', {'type': 'float', 'defval': 1.2}),
    ('namespace:args:key', {'type': 'int', 'defval': None, 'doc': 'words are cool!'}),
    ('namesapce:args:some_key', {'type': 'int', 'defval': None, 'doc': 'another key!'})
)
defvals = {'ikey': 1, 'skey': '1', 'bkey': False, 'fkey': 1.2,
           'dkey': {'hehe': 'haha'},
           'lkey1': [{'hehe': 'haha'}],
           }

class Config2Test(s_test.SynTest):

    async def test_argparse(self):

        parser, parsed_names = s_config.makeArgParser(confdefs)

        halp = parser.format_help()
        print(halp)
        opts = parser.parse_args([])
        print(opts)
        data = vars(opts)

        for k, v in list(data.items()):
            if v is s_common.novalu:
                print(f'dropping: {k} because it was not set and has no default.')
                data.pop(k, None)

        from pprint import pprint
        pprint(data)
        d = {}
        for k, v in data.items():
            d[parsed_names.get(k)] = v
        pprint(d)

    async def test_config2(self):

        conf = s_config.Config2(confdefs=confdefs)
        self.eq(conf.conf, defvals)

        # Simple type norm tests
        await conf.set('ikey', '2')
        self.eq(conf.get('ikey'), 2)

        await conf.set('skey', 3)
        self.eq(conf.get('skey'), '3')

        await conf.set('bkey', 1)
        self.eq(conf.get('bkey'), True)

        await conf.set('bkey', 'yes')
        self.eq(conf.get('bkey'), True)

        await conf.set('bkey', 'no')  # bool() doesn't care
        self.eq(conf.get('bkey'), True)

        await conf.set('bkey', 0)
        self.eq(conf.get('bkey'), False)

        await conf.set('fkey', '3.14')
        self.eq(conf.get('fkey'), 3.14)

        # The mutable types are mutable
        dkey = conf.get('dkey')
        dkey['yup'] = 1
        self.eq(conf.get('dkey'), {'yup': 1, 'hehe': 'haha'})

        lkey1 = conf.get('lkey1')
        lkey1.append('yes!')
        self.len(2, conf.get('lkey1'))

        # lkey2 wasn't set..
        self.none(conf.get('lkey2'))
        self.isinstance(conf.get('lkey2', []), list)
        await conf.set('lkey2', [1, 2, 3])
        self.eq(conf.get('lkey2'), [1, 2, 3])

        # TODO - Test container __setitem__ and __getitem__ methods.
        # TODO - Test dict mimic methods

        # Our original confdefs defvals are unchanged
        conf2 = s_config.Config2(confdefs=confdefs)
        self.eq(conf2.conf, defvals)


class ConfTest(s_test.SynTest):

    async def test_config_base(self):
        confdefs = (
            ('foo', 20, int),
        )

        conf = s_config.Config(confdefs)

        with self.raises(s_exc.NoSuchName):
            await conf.set('hehe', 'haha')

        await conf.loadConfDict({'foo': 30})

        self.eq(conf.get('foo'), 30)

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'foo.yaml')
            with s_common.genfile(path) as fd:
                fd.write(b'foo: 8080')

            await conf.loadConfYaml(path)

        self.eq(conf.get('foo'), 8080)

        with self.setTstEnvars(SYN_CONF_TEST_FOO='31337'):
            await conf.loadConfEnvs('SYN_CONF_TEST')

            self.eq(conf.get('foo'), 31337)

            info = dict(iter(conf))
            self.eq(31337, info.get('foo'))
