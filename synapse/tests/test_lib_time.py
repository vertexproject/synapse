import synapse.exc as s_exc

import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils

class TimeTest(s_t_utils.SynTest):

    def test_time_delta(self):

        self.eq(s_time.delta('3days'), 259200000)
        self.eq(s_time.delta('3  days'), 259200000)
        self.eq(s_time.delta('  3days'), 259200000)
        self.eq(s_time.delta('  3   days'), 259200000)

        self.eq(s_time.delta('+3days'), 259200000)
        self.eq(s_time.delta('+3  days'), 259200000)
        self.eq(s_time.delta('+  3days'), 259200000)
        self.eq(s_time.delta('+  3   days'), 259200000)

        self.eq(s_time.delta('-3days'), -259200000)
        self.eq(s_time.delta('-3  days'), -259200000)
        self.eq(s_time.delta('-  3days'), -259200000)
        self.eq(s_time.delta('-  3   days'), -259200000)

    def test_time_parse(self):
        self.eq(s_time.parse('2050'), 2524608000000)
        self.eq(s_time.parse('205012'), 2553465600000)
        self.eq(s_time.parse('20501217'), 2554848000000)
        self.eq(s_time.parse('2050121703'), 2554858800000)
        self.eq(s_time.parse('205012170304'), 2554859040000)
        self.eq(s_time.parse('20501217030432'), 2554859072000)
        self.eq(s_time.parse('20501217030432101'), 2554859072101)
        self.eq(s_time.parse('205012170304321015'), 2554859072101)
        self.eq(s_time.parse('20501217030432101567'), 2554859072101)
        self.raises(s_exc.BadTypeValu, s_time.parse, '2050121703043210156789')
