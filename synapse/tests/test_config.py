from synapse.tests.common import *

import synapse.lib.config as s_config

class ConfTest(SynTest):

    def test_conf_base(self):
        defs = (
            ('fooval', {'type': 'int', 'doc': 'what is foo val?', 'defval': 99}),
            ('enabled', {'type': 'bool', 'doc': 'is thing enabled?', 'defval': 0}),
        )

        data = {}
        def callback(v):
            data['woot'] = v

        with s_config.Config(defs=defs) as conf:

            self.eq(conf.getConfOpt('enabled'), 0)
            self.eq(conf.getConfOpt('fooval'), 99)

            conf.onConfOptSet('enabled', callback)

            conf.setConfOpt('enabled', 'true')

            self.eq(data.get('woot'), 1)

            conf.setConfOpts({'fooval': '0x20'})
            self.eq(conf.getConfOpt('fooval'), 0x20)

            conf.setConfOpts({'fooval': 0x30})
            self.eq(conf.getConfOpt('fooval'), 0x30)

            self.raises(NoSuchOpt, conf.setConfOpts, {'newp': 'hehe'})

    def test_conf_asloc(self):
        with s_config.Config() as conf:
            conf.addConfDef('foo', type='int', defval=0, asloc='_foo_valu')
            self.eq(conf._foo_valu, 0)
            conf.setConfOpt('foo', '0x20')
            self.eq(conf._foo_valu, 0x20)
