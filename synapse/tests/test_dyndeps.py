from synapse.tests.common import *

import synapse.dyndeps as s_dyndeps

hehe = 'woot'

class Foo:
    def bar(self):
        return 'baz'

def woot(x, y=30):
    return x + y

class DynDepsTest(SynTest):

    def test_dyndeps_dynmod(self):
        self.none( s_dyndeps.getDynMod('- -') )
        self.nn( s_dyndeps.getDynMod('sys') )

    def test_dyndeps_dynloc(self):
        self.none( s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.gronk') )
        self.nn( s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.hehe') )

    def test_dyndeps_dyntask(self):
        task = ('synapse.tests.test_dyndeps.Foo', (), {})
        foo = s_dyndeps.runDynTask(task)
        self.eq( foo.bar(), 'baz' )

    def test_dyndeps_eval(self):
        valu = s_dyndeps.runDynEval('synapse.tests.test_dyndeps.woot(40,y=10)')
        self.eq( valu, 50 )

    def test_dyndeps_nosuchdyn(self):
        self.raises( NoSuchDyn, s_dyndeps.tryDynMod, 'newpnewp' )
        self.raises( NoSuchDyn, s_dyndeps.tryDynLocal, 'sys.newpnewp' )

    def test_dyndeps_alias(self):

        s_dyndeps.addDynAlias('unit_test_woot',woot)

        self.eq( s_dyndeps.getDynLocal('unit_test_woot'), woot )
        self.eq( s_dyndeps.tryDynFunc('unit_test_woot', 20, y=40 ), 60 )

        self.eq( s_dyndeps.delDynAlias('unit_test_woot'), woot )
        self.none( s_dyndeps.getDynLocal('unit_test_woot') )

        self.raises( NoSuchDyn, s_dyndeps.tryDynFunc, 'unit_test_woot', 20, y=40 )
