from synapse.tests.common import *

import synapse.lib.membrane as s_membrane

import unittest
raise unittest.SkipTest()

class MembraneTest(SynTest):

    def test_membrane(self):

        def fn(mesg):
            return mesg

        rules = (
            (False, ('a', {'a': 'nope'})),
            (False, ('a', {'a': 'z*'})),
            (True, ('a', {})),
            (False, ('b', {})),
            (True, ('c*', {})),
        )

        hits = (
            ('a', {}),
            ('a', {'a': 'yep'}),
            ('c', {'a': 1}),
            ('carrot', {'a': 1}),
        )

        misses = (
            ('a', {'a': 'nope'}),
            ('a', {'a': 'zoo'}),
            ('b', {'a': 1}),
        )

        m = s_membrane.Membrane('test', rules, fn)
        [self.eq(hit, m.filt(hit)) for hit in hits]
        [self.none(m.filt(miss)) for miss in misses]
