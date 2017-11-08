import synapse.cortex as s_cortex
import synapse.lib.module as s_module

from synapse.tests.common import *

class FooMod(s_module.CoreModule):
    _mod_name = 'foo'

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
