import os
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

import synapse.lib.config as s_config


class Config2Test(s_test.SynTest):
    def setUp(self) -> None:
        self.confdefs = (  # type: ignore

            ('modules', {
                'type': 'list', 'defval': (),
                'doc': 'A list of module classes to load.'
            }),

            ('storm:log', {
                'type': 'bool', 'defval': False,
                'doc': 'Log storm queries via system logger.'
            }),

            ('storm:log:level', {
                'type': 'int',
                'defval': logging.WARNING,
                'doc': 'Logging log level to emit storm logs at.'
            }),

            ('splice:sync', {
                'type': 'str', 'defval': None,
                'doc': 'A telepath URL for an upstream cortex.'
            }),

            ('splice:cryotank', {
                'type': 'str', 'defval': None,
                'doc': 'A telepath URL for a cryotank used to archive splices.'
            }),

            ('feeds', {
                'type': 'dict', 'defval': {},
                'doc': 'A dictionary of things.'
            }),

            ('cron:enable', {
                'type': 'bool',
                'doc': 'Enable cron jobs running.'
            }),

            ('haha', {'doc': 'words', 'defval': 1234})

        )

    def test_config2(self):
        pass

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
