import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps
import synapse.tests.common as s_test

hehe = 'woot'

class Foo:
    def bar(self):
        return 'baz'

def woot(x, y=30):
    return x + y

class DynDepsTest(s_test.SynTest):

    def test_dyndeps_dynmod(self):
        self.none(s_dyndeps.getDynMod('- -'))
        self.nn(s_dyndeps.getDynMod('sys'))

    def test_dyndeps_dynloc(self):
        self.none(s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.gronk'))
        self.nn(s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.hehe'))

    def test_dyndeps_dyntask(self):
        task = ('synapse.tests.test_dyndeps.Foo', (), {})
        foo = s_dyndeps.runDynTask(task)
        self.eq(foo.bar(), 'baz')

    def test_dyndeps_nosuchdyn(self):
        self.raises(s_exc.NoSuchDyn, s_dyndeps.tryDynMod, 'newpnewp')
        self.raises(s_exc.NoSuchDyn, s_dyndeps.tryDynLocal, 'sys.newpnewp')

    def test_dyndeps_meth(self):
        self.nn(s_dyndeps.getDynMeth('synapse.eventbus.EventBus.fini'))
        self.none(s_dyndeps.getDynMeth('synapse.eventbus.EventBus.newp'))
