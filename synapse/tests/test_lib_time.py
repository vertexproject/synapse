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

        # malformed times that can still be parsed
        self.eq(s_time.parse('2020 jun 10 12:14:34'), s_time.parse('2020-10-12 14:34'))

    def test_time_parse_tz(self):

        # explicit iso8601
        self.eq(s_time.parse('2020-07-07T16:29:53Z'), 1594139393000)
        self.eq(s_time.parse('2020-07-07T16:29:53.234Z'), 1594139393234)
        self.eq(s_time.parse('2020-07-07T16:29:53.234567Z'), 1594139393234)

        self.eq(s_time.parse('2020-07-07T16:29:53+00:00'), 1594139393000)
        self.eq(s_time.parse('2020-07-07T16:29:53-04:00'), 1594153793000)
        self.eq(s_time.parse('2020-07-07T16:29:53-04:30'), 1594155593000)
        self.eq(s_time.parse('2020-07-07T16:29:53+02:00'), 1594132193000)
        self.eq(s_time.parse('2020-07-07T16:29:53-0430'), 1594155593000)
        self.eq(s_time.parse('2020-07-07T16:29:53+0200'), 1594132193000)
        self.eq(s_time.parse('2021-11-03T08:32:14.506-0400'), 1635942734506)
        self.eq(s_time.parse('2020-07-07T16:29:53.234+02:00'), 1594132193234)
        self.eq(s_time.parse('2020-07-07T16:29:53.234567+02:00'), 1594132193234)
        self.eq(s_time.parse('2020-07-07T16:29:53.234567+10:00'), 1594103393234)

        utc = s_time.parse('2020-07-07 16:29')
        self.eq(s_time.parse('2020-07-07 16:29-06:00'), utc + 6 * s_time.onehour)

        self.eq(s_time.parse('20200707162953+00:00'), 1594139393000)
        self.eq(s_time.parse('20200707162953-04:00'), 1594153793000)

        self.eq(s_time.parse('20200707162953'), 1594139393000)
        self.eq(s_time.parse('20200707162953+423'),
                1594139393000 - s_time.onehour * 4 - s_time.onemin * 23)

        # This partial value is ignored and treated like a millisecond value
        self.eq(s_time.parse('20200707162953+04'), 1594139393040)

        # A partial time (without mm) is ignored as a timestamp.
        self.eq(s_time.parse('202007+04'), s_time.parse('20200704'))

        # invalid range
        with self.raises(s_exc.BadTypeValu):
            s_time.parse('2020-07-07T16:29:53+36:00')

        # invalid shorthand times with timezones are invalid
        tvs = (
            '2020+3:00',
            '2020+300',
            '2020-3:00',
            '2020-300',
            '2020+03:00',
            '2020-03:00',
            '2020-07-04:00',
            '2020-07-07 +4:00',
            '2020-07-07 +04:01',
            '2020-07-07 01 +04:01',
            '2020-07-04:00',
            '2020-07-07 -4:00',
            '2020-07-07 -04:00',
            '2020-07-07 01 -04:01',
        )
        for tv in tvs:
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(tv)

    def test_time_toutc(self):
        tick = s_time.parse('2020-02-11 14:08:00.123')
        self.eq(s_time.toUTC(tick, 'EST'), tick + (s_time.onehour * 5))
