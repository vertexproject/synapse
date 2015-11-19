import unittest

from synapse.dyndeps import getDynMod, getDynLocal, runDynTask

hehe = 'woot'

class Foo:
    def bar(self):
        return 'baz'

class DynDepsTest(unittest.TestCase):

    def test_dyndeps_dynmod(self):
        self.assertIsNone( getDynMod('- -') )
        self.assertIsNotNone( getDynMod('sys') )

    def test_dyndeps_dynloc(self):
        self.assertIsNone( getDynLocal('synapse.tests.test_dyndeps.gronk') )
        self.assertIsNotNone( getDynLocal('synapse.tests.test_dyndeps.hehe') )

    def test_dyndeps_dyntask(self):
        task = ('synapse.tests.test_dyndeps.Foo', (), {})
        foo = runDynTask(task)
        self.assertEqual( foo.bar(), 'baz' )
