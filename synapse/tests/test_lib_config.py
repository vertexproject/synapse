from synapse.tests.common import *

import synapse.daemon as s_daemon
import synapse.lib.config as s_config

class Foo(s_config.Config):

    @staticmethod
    @s_config.confdef(name='foo')
    def foodefs():
        defs = (
            ('fooval', {'type': 'int', 'doc': 'what is foo val?', 'defval': 99}),
            ('enabled', {'type': 'bool', 'doc': 'is thing enabled?', 'defval': 0}),
        )
        return defs

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

            instance_defs = conf.getConfDefs()
            self.eq(len(instance_defs), 2)
            self.isin('enabled', instance_defs)
            self.isin('fooval', instance_defs)
            edict = instance_defs.get('enabled')
            self.eq(edict.get('type'), 'bool')
            self.eq(edict.get('defval'), 0)
            self.eq(edict.get('doc'), 'is thing enabled?')

            opts = conf.getConfOpts()
            self.eq(opts, {'enabled': 1, 'fooval': 0x30})

    def test_conf_defval(self):
        defs = (
            ('mutable:dict', {'doc': 'some dictionary', 'defval': {}}),
        )

        with s_config.Config(defs=defs) as conf:
            md = conf.getConfOpt('mutable:dict')
            md['key'] = 1
            md = conf.getConfOpt('mutable:dict')
            self.eq(md.get('key'), 1)

        # Ensure the mutable:dict defval content is not changed
        with s_config.Config(defs=defs) as conf2:
            md = conf2.getConfOpt('mutable:dict')
            self.eq(md, {})

    def test_conf_asloc(self):
        with s_config.Config() as conf:
            conf.addConfDef('foo', type='int', defval=0, asloc='_foo_valu')
            self.eq(conf._foo_valu, 0)
            conf.setConfOpt('foo', '0x20')
            self.eq(conf._foo_valu, 0x20)

    def test_confdef_decorator(self):
        data = {}
        def callback(v):
            data['woot'] = v

        self.true(issubclass(Foo, s_config.Configable))
        self.true(hasattr(Foo.foodefs, '_syn_config'))
        foo_config = Foo.foodefs()
        self.isinstance(foo_config, tuple)

        with Foo() as conf:
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

        with Foo({'enabled': 1}) as conf:
            self.eq(conf.getConfOpt('enabled'), 1)

    def test_config_loadpath(self):
        config0 = {'enabled': 1, 'fooval': 2}
        config1 = {'enabled': 1, 'newp': 'hehe'}

        with self.getTestDir() as fdir:
            fp0 = os.path.join(fdir, 'c0.json')
            fp1 = os.path.join(fdir, 'c1.json')
            fpnull = os.path.join(fdir, 'null.json')
            fpnewp = os.path.join(fdir, 'newp.json')
            jssave(config0, fp0)
            jssave(config1, fp1)
            jssave(None, fpnull)

            with Foo() as conf:
                conf.loadConfPath(fpnewp)
                self.eq(conf.getConfOpt('enabled'), 0)
                self.eq(conf.getConfOpt('fooval'), 99)

                conf.loadConfPath(fpnull)
                self.eq(conf.getConfOpt('enabled'), 0)
                self.eq(conf.getConfOpt('fooval'), 99)

            with Foo() as conf:
                conf.loadConfPath(fp0)
                self.eq(conf.getConfOpt('enabled'), 1)
                self.eq(conf.getConfOpt('fooval'), 2)

            with Foo() as conf:
                self.raises(NoSuchOpt, conf.loadConfPath, fp1)

    def test_configable_proxymethod(self):

        class CoolClass(s_config.Configable):

            def __init__(self, proxy):
                self.proxy = proxy
                s_config.Configable.__init__(self)

        with self.getDmonCore() as core:
            cool = CoolClass(core)
            tufo = cool.proxy.formTufoByProp('intform', 0)
            self.istufo(tufo)

    def test_lib_config_req(self):
        defs = (
            ('foo', {'type': 'int', 'req': True}),
        )

        with s_config.Config(defs=defs) as conf:
            self.raises(ReqConfOpt, conf.reqConfOpts)
            conf.setConfOpt('foo', 20)
            conf.reqConfOpts()
