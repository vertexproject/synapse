import synapse.exc as s_exc
import synapse.lib.dyndeps as s_dyndeps
import synapse.tests.utils as s_t_utils

hehe = 'woot'

class Foo:
    def bar(self):
        return 'baz'

def woot(x, y=30):
    return x + y

async def awaitable():
    return 12345

class DynDepsTest(s_t_utils.SynTest):

    def test_dyndeps_dynmod(self):
        with self.getLoggerStream('synapse.lib.dyndeps', 'Failed to import "- -"') as stream:
            self.none(s_dyndeps.getDynMod('- -'))
            self.true(stream.wait(1))
        self.nn(s_dyndeps.getDynMod('sys'))

    def test_dyndeps_dynloc(self):
        self.none(s_dyndeps.getDynLocal('synapse.tests.test_lib_dyndeps.gronk'))
        self.nn(s_dyndeps.getDynLocal('synapse.tests.test_lib_dyndeps.hehe'))

    def test_dyndeps_dyntask(self):
        task = ('synapse.tests.test_lib_dyndeps.Foo', (), {})
        foo = s_dyndeps.runDynTask(task)
        self.eq(foo.bar(), 'baz')
        self.raises(s_exc.NoSuchFunc, s_dyndeps.runDynTask, ('synapse.tests.test_lib_dyndeps.newp', (), {}))

    def test_dyndeps_nosuchdyn(self):
        self.raises(s_exc.NoSuchDyn, s_dyndeps.reqDynMod, 'newpnewp')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.reqDynLocal, 'sys.newpnewp')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.reqDynFunc, 'sys.newpnewp', (), {})

        # Deprecated
        self.raises(s_exc.NoSuchDyn, s_dyndeps.tryDynMod, 'newpnewp')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.tryDynLocal, 'sys.newpnewp')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.tryDynFunc, 'sys.newpnewp', (), {})

    def test_dyndeps_meth(self):
        self.nn(s_dyndeps.getDynMeth('synapse.lib.base.Base.fini'))
        self.none(s_dyndeps.getDynMeth('synapse.lib.base.Base.newp'))

    async def test_dyndeps_coro(self):
        func = s_dyndeps.getDynCoro('synapse.tests.test_lib_dyndeps.awaitable')
        self.nn(func)
        self.eq(await func(), 12345)
        rfunc = s_dyndeps.reqDynCoro('synapse.tests.test_lib_dyndeps.awaitable')
        self.true(func is rfunc)

        self.none(s_dyndeps.getDynCoro('synapse.tests.test_lib_dyndeps.woot'))
        self.none(s_dyndeps.getDynCoro('synapse.tests.test_lib_dyndeps.newp'))

        self.raises(s_exc.NoSuchDyn, s_dyndeps.reqDynCoro, 'synapse.tests.test_lib_dyndeps.woot')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.reqDynCoro, 'synapse.tests.test_lib_dyndeps.newp')
