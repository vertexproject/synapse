import synapse.cortex as s_cortex
import synapse.lib.module as s_module

from synapse.tests.common import *

class FooMod(s_module.CoreModule):
    _mod_name = 'foo'
    _mod_iden = 'e8ff3739f5d9dbacafef75a532691420'

class BarMod(s_module.CoreModule):
    pass

class CoreModTest(SynTest):

    def test_lib_module_modname(self):
        with self.getRamCore() as core:
            foo = core.initCoreModule('synapse.tests.test_lib_module.FooMod', {})
            bar = core.initCoreModule('synapse.tests.test_lib_module.BarMod', {})

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
