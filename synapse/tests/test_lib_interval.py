import synapse.tests.utils as s_t_utils

import synapse.lib.interval as s_interval

class IvalTest(s_t_utils.SynTest):

    def test_ival_fold(self):
        vals = [None, 100, 20, None]
        self.eq(s_interval.fold(*vals), (20, 100))
        self.none(s_interval.fold())

    def test_ival_overlap(self):

        ival0 = s_interval.fold(10, 20)
        ival1 = s_interval.fold(15, 30)
        ival2 = s_interval.fold(30, 50)
        ival3 = s_interval.fold(1, 100)

        self.true(s_interval.overlap(ival0, ival1))
        self.false(s_interval.overlap(ival1, ival2))

        self.true(s_interval.overlap(ival0, ival3))
        self.true(s_interval.overlap(ival1, ival3))
        self.true(s_interval.overlap(ival2, ival3))

    def test_ival_parsetime(self):
        self.eq(s_interval.parsetime('1970-1980'), (0, 315532800000))
