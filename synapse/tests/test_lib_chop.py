import synapse.lib.chop as s_chop

import synapse.tests.common as s_test

class ChopTest(s_test.SynTest):

    def test_chop_digits(self):
        self.eq(s_chop.digits('a1b2c3'), '123')

    def test_chop_intrange(self):
        self.eq(s_chop.intrange('20:30'), (20, 30))
