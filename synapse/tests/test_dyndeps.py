import unittest

import synapse.dyndeps as s_dyndeps

hehe = 'woot'

class Foo:
    def bar(self):
        return 'baz'

def woot(x, y=30):
    return x + y

class DynDepsTest(unittest.TestCase):

    def test_dyndeps_dynmod(self):
        self.assertIsNone( s_dyndeps.getDynMod('- -') )
        self.assertIsNotNone( s_dyndeps.getDynMod('sys') )

    def test_dyndeps_dynloc(self):
        self.assertIsNone( s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.gronk') )
        self.assertIsNotNone( s_dyndeps.getDynLocal('synapse.tests.test_dyndeps.hehe') )

    def test_dyndeps_dyntask(self):
        task = ('synapse.tests.test_dyndeps.Foo', (), {})
        foo = s_dyndeps.runDynTask(task)
        self.assertEqual( foo.bar(), 'baz' )

    def test_dyndeps_eval(self):
        valu = s_dyndeps.runDynEval('synapse.tests.test_dyndeps.woot(40,y=10)')
        self.assertEqual( valu, 50 )
