import unittest

from synapse.dyndeps import getDynMod, getDynLocal

hehe = 'woot'

class DynDepsTest(unittest.TestCase):

    def test_dyndeps_dynmod(self):
        self.assertIsNone( getDynMod('- -') )
        self.assertIsNotNone( getDynMod('sys') )

    def test_dyndeps_dynloc(self):
        self.assertIsNone( getDynLocal('synapse.tests.test_dyndeps.gronk') )
        self.assertIsNotNone( getDynLocal('synapse.tests.test_dyndeps.hehe') )
