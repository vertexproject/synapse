import os

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.module as s_module

import synapse.tests.utils as s_t_utils

class FooMod(s_module.CoreModule):
    mod_name = 'foo'

    def preCoreModule(self):
        if os.environ.get('SYN_TEST_MOD_FAIL_PRE'):
            raise Exception('preCoreModuleFail')

    def initCoreModule(self):
        if os.environ.get('SYN_TEST_MOD_FAIL_INIT'):
            raise Exception('initCoreModuleFail')

class BarMod(s_module.CoreModule):
    confdefs = (
        ('hehe', {'defval': 'haha'}),
        ('duck', {}),
    )

    def initCoreModule(self):
        self.data = {}

        def onfini():
            self.data['fini'] = True

        self.core.onfini(onfini)

foo_ctor = 'synapse.tests.test_lib_module.FooMod'
bar_ctor = 'synapse.tests.test_lib_module.BarMod'

class CoreModTest(s_t_utils.SynTest):

    async def test_basics(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex

            testmod = core.getCoreMod('synapse.tests.utils.TestModule')
            self.isinstance(testmod, s_module.CoreModule)
            # modname from class name
            self.eq(testmod.mod_name, 'testmodule')

            foomod = await core.loadCoreModule(foo_ctor)
            # modname from explicit modname
            self.eq(foomod.mod_name, 'foo')
            # modpaths are dynamically made on demand
            self.false(os.path.isdir(foomod._modpath))
            mpath = foomod.getModPath()
            self.isin(os.path.join('mods', 'foo'), mpath)
            self.true(os.path.isdir(foomod._modpath))

            # preload a config file for the BarModule
            dirn = s_common.gendir(core.dirn, 'mods', 'barmod')
            s_common.yamlsave({'test': 1, 'duck': 'quack'}, dirn, 'conf.yaml')

            barmod = await core.loadCoreModule(bar_ctor)

            self.eq(barmod.data, {})
            self.eq(barmod.conf, {'test': 1,
                                  'hehe': 'haha',
                                  'duck': 'quack',
                                  })

        self.eq(barmod.data, {'fini': True})

    async def test_load_failures(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex
            with self.setTstEnvars(SYN_TEST_MOD_FAIL_PRE=1) as cm:
                with self.getAsyncLoggerStream('synapse.cortex', 'preCoreModuleFail') as stream:
                    self.none(await core.loadCoreModule(foo_ctor))
                    self.true(await stream.wait(1))
                    self.none(core.getCoreMod(foo_ctor))

            with self.setTstEnvars(SYN_TEST_MOD_FAIL_INIT=1) as cm:
                with self.getAsyncLoggerStream('synapse.cortex', 'initCoreModuleFail') as stream:
                    self.none(await core.loadCoreModule(foo_ctor))
                    self.true(await stream.wait(1))
                    self.none(core.getCoreMod(foo_ctor))

        with self.getTestDir(mirror='testcore') as dirn:
            conf = s_common.yamlload(dirn, 'cell.yaml')
            conf['modules'].append(foo_ctor)
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            conf = s_common.yamlload(dirn, 'cell.yaml')

            with self.setTstEnvars(SYN_TEST_MOD_FAIL_PRE=1) as cm:
                with self.getAsyncLoggerStream('synapse.cortex', 'preCoreModuleFail') as stream:
                    async with await s_cortex.Cortex.anit(dirn) as core:
                        self.true(await stream.wait(1))
                        self.none(core.getCoreMod(foo_ctor))

            with self.setTstEnvars(SYN_TEST_MOD_FAIL_INIT=1) as cm:
                with self.getAsyncLoggerStream('synapse.cortex', 'initCoreModuleFail') as stream:
                    async with await s_cortex.Cortex.anit(dirn) as core:
                        self.true(await stream.wait(1))
                        self.none(core.getCoreMod(foo_ctor))
