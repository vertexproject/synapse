import synapse.cortex as s_cortex
import synapse.lib.module as s_module

import synapse.tests.utils as s_t_utils

data = {}

import unittest
raise unittest.SkipTest()

class FooMod(s_module.CoreModule):
    _mod_name = 'foo'
    _mod_iden = 'e8ff3739f5d9dbacafef75a532691420'

class BarMod(s_module.CoreModule):
    def finiCoreModule(self):
        data['fini'] = True

class CoreModTest(s_t_utils.SynTest):

    def test_lib_module_modname(self):
        with self.getRamCore() as core:
            foo = core.initCoreModule('synapse.tests.test_lib_module.FooMod', {})
            self.eq(foo.getModName(), 'foo')
            self.eq(foo.getModIden(), 'e8ff3739f5d9dbacafef75a532691420')

            bar = core.initCoreModule('synapse.tests.test_lib_module.BarMod', {})
            self.eq(bar.getModName(), 'BarMod')
            self.none(bar.getModIden())

    def test_lib_module_modpath(self):

        with self.getRamCore() as core:

            foo = core.initCoreModule('synapse.tests.test_lib_module.FooMod', {})

            self.none(foo.getModPath('woot.txt'))
            self.raises(ReqConfOpt, foo.reqModPath, 'woot.txt')

        with self.getTestDir() as dirn:

            with s_cortex.fromdir(dirn) as core:

                foo = core.initCoreModule('synapse.tests.test_lib_module.FooMod', {})

                self.nn(foo.getModPath('woot.txt'))
                self.nn(foo.reqModPath('woot.txt'))

    def test_lib_module_prop(self):

        with self.getRamCore() as core:

            foo = core.initCoreModule('synapse.tests.test_lib_module.FooMod', {})
            bar = core.initCoreModule('synapse.tests.test_lib_module.BarMod', {})

            foo.setModProp('hehe', 10)
            self.eq(10, foo.getModProp('hehe'))
            self.none(foo.getModProp('haha'))

            self.raises(NoModIden, bar.getModProp, 'hehe')
            self.raises(NoModIden, bar.setModProp, 'hehe', 10)

    def test_lib_module_fini(self):
        # Clear the module local dictionary
        data.clear()
        self.none(data.get('fini'))

        with self.getRamCore() as core:
            bar = core.initCoreModule('synapse.tests.test_lib_module.BarMod', {})
            self.isinstance(bar, s_module.CoreModule)
            bar.fini()

            self.true(data.get('fini'))
