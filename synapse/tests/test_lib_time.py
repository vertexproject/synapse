import synapse.exc as s_exc

import synapse.lib.time as s_time
import synapse.lookup.timezones as s_l_timezones

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

        # malformed times with leftover text are not silently misparsed
        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('2020 jun 10 12:14:34')
        self.isin('unexpected text in time value', cm.exception.get('mesg'))

        # rfc822
        self.eq(s_time.parse('Sat, 17 Dec 2050 03:04:32'), 2554859072000)
        self.eq(s_time.parse('Sat, 03 Dec 2050 03:04:32'), 2554859072000 - 14 * s_time.oneday)
        self.eq(s_time.parse('Sat, 3 Dec 2050 03:04:32'), 2554859072000 - 14 * s_time.oneday)
        self.eq(s_time.parse('17 Dec 2050 03:04:32'), 2554859072000)

        self.eq(s_time.parse('20200106030432'), s_time.parse('Mon, 06 Jan 2020 03:04:32'))
        self.eq(s_time.parse('20200105030432'), s_time.parse('Sun, 05 Jan 2020 03:04:32'))

        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('17 Dec 2050 99:04:32')
        self.isin('Error parsing time as RFC822', cm.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as cm:
            # rfc822 does support 2-digit years,
            # but strptime doesn't so it is excluded
            s_time.parse('Sat, 17 Dec 50 03:04:32')
        self.isin('Error parsing time "Sat, 17 Dec 50 03:04:32"', cm.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as cm:
            # malformed times that don't match the regex will pass
            # through to default parsing
            s_time.parse('17 Nah 2050 03:04:32')
        self.isin('Error parsing time "17 Nah 2050 03:04:32"', cm.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('Wut, 17 Dec 2050 03:04:32')
        self.isin('Error parsing time "Wut, 17 Dec 2050 03:04:32"', cm.exception.get('mesg'))

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

        self.eq(('2020-07-07T16:29:53', s_time.onehour * 4), s_time.parsetz('2020-07-07T16:29:53 -04:00'))
        self.eq(('2020-07-07T16:29:53', s_time.onehour * 4), s_time.parsetz('2020-07-07T16:29:53-04:00'))

        utc = s_time.parse('2020-07-07 16:29')
        self.eq(s_time.parse('2020-07-07 16:29-06:00'), utc + 6 * s_time.onehour)

        self.eq(s_time.parse('20200707162953+00:00'), 1594139393000)
        self.eq(s_time.parse('20200707162953-04:00'), 1594153793000)

        self.eq(s_time.parse('20200707162953'), 1594139393000)
        self.eq(s_time.parse('20200707162953+423'),
                1594139393000 - s_time.onehour * 4 - s_time.onemin * 23)

        # named timezones
        utc = 1594139393000
        self.eq(s_time.parse('2020-07-07T16:29:53 EDT'), utc + s_time.onehour * 4)
        self.eq(s_time.parse('2020-07-07T16:29:53 edt'), utc + s_time.onehour * 4)
        self.eq(s_time.parse('2020-07-07T16:29:53.234 EDT'), utc + s_time.onehour * 4 + 234)
        self.eq(s_time.parse('2020-07-07T16:29:53.234567 EDT'), utc + s_time.onehour * 4 + 234)
        self.eq(s_time.parse('2020-07-07T16:29:53-04:00'), s_time.parse('2020-07-07T16:29:53EDT'))

        self.eq(('2020-07-07T16:29:53', s_time.onehour * 4), s_time.parsetz('2020-07-07T16:29:53 EDT'))
        self.eq(('2020-07-07T16:29:53', s_time.onehour * 4), s_time.parsetz('2020-07-07T16:29:53EDT'))

        self.eq(s_time.parse('2020-07-07T16:29:53 A'), utc + s_time.onehour)
        self.eq(s_time.parse('2020-07-07T16:29:53 CDT'), utc + s_time.onehour * 5)
        self.eq(s_time.parse('2020-07-07T16:29:53 CST'), utc + s_time.onehour * 6)
        self.eq(s_time.parse('2020-07-07T16:29:53 EST'), utc + s_time.onehour * 5)
        self.eq(s_time.parse('2020-07-07T16:29:53 GMT'), utc)
        self.eq(s_time.parse('2020-07-07T16:29:53 M'), utc + s_time.onehour * 12)
        self.eq(s_time.parse('2020-07-07T16:29:53 MDT'), utc + s_time.onehour * 6)
        self.eq(s_time.parse('2020-07-07T16:29:53 MST'), utc + s_time.onehour * 7)
        self.eq(s_time.parse('2020-07-07T16:29:53 N'), utc - s_time.onehour)
        self.eq(s_time.parse('2020-07-07T16:29:53 PDT'), utc + s_time.onehour * 7)
        self.eq(s_time.parse('2020-07-07T16:29:53 PST'), utc + s_time.onehour * 8)
        self.eq(s_time.parse('2020-07-07T16:29:53 UT'), utc)
        self.eq(s_time.parse('2020-07-07T16:29:53 UTC'), utc)
        self.eq(s_time.parse('2020-07-07T16:29:53 Y'), utc - s_time.onehour * 12)
        self.eq(s_time.parse('2020-07-07T16:29:53 Z'), utc)

        # unsupported timezone names are not recognized and are invalid
        for tv in ('ET', 'NEWP', 'Etc/GMT-4', 'America/New_York'):
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(f'2020-07-07T16:29:53 {tv}')

        # coverage for bad args
        self.raises(s_exc.BadArg, s_l_timezones.getTzOffset, 42)

        # invalid multiple timezones do not match
        self.eq(0, s_time.parsetz('2020-07-07T16:29:53 EST -0400')[1])

        # rfc822
        self.eq(s_time.parse('Tue, 7 Jul 2020 16:29:53 EDT'), utc + s_time.onehour * 4)
        self.eq(s_time.parse('Tue, 7 Jul 2020 16:29:53 -0400'), utc + s_time.onehour * 4)

        # A bare ISO 8601 hour offset following a full time is a timezone offset
        self.eq(s_time.parse('20200707162953+04'), 1594139393000 - s_time.onehour * 4)

        # A bare hour offset without a full time is invalid
        with self.raises(s_exc.BadTypeValu):
            s_time.parse('202007+04')

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

        tick0 = s_time.parse('2023-06-12T20:01:23.488627000', chop=True)
        tick1 = s_time.parse('2023-06-12T20:01:23.488627862', chop=True)

        self.nn(tick0)
        self.nn(tick1)

        self.eq(tick0, tick1)

    def test_time_parse_strict(self):

        tick = s_time.parse('2024-01-02T03:04:05Z')

        # leftover text after the zone is parsed must not be silently dropped or glued on
        tvs = (
            '2024-01-02 03:04:05.678+1 fortnight',
            '2024-01-02 03:04:05+1 week',
            '2024-01-05 03:04:05+1y',
            '2024-01-02 03:04:05 PM',
            '2024-01-02 03:04:05 AM',
            '2024-01-02 03:04:05 America/New_York',
            '2024-01-02 03:04:05 Etc/GMT-4',
            '2024-01-02 03:04:05 ET',
            '2024-01-02 03:04:05 NEWP',
            'Tue Jan 02 03:04:05 2024',
            '2024-1-2',
            '2024-01-2',
            '2024-01-02-03-04-05-07',
            '202007+04',
            '2024-01-02,03:04:05',
            '2024-01-02 03:04:05.123.456',
            '-2024-01-02',
            # a fraction may only follow the seconds
            '2024,12',
            '2024-01,02',
            '2024-01-02,03',
            '2024-01-02 03,04',
            '2024-01-02 03:04,123',
            '2024-01-02 03:04.123',
        )
        for tv in tvs:
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(tv, chop=True)

        # a bare ISO 8601 +/-hh offset after a full time is honored
        self.eq(s_time.parse('2024-01-02 03:04:05-07'), tick + s_time.onehour * 7)
        self.eq(s_time.parse('2024-01-02 03:04:05+07'), tick - s_time.onehour * 7)
        self.eq(s_time.parse('2024-01-02 03:04:05.678-07'), tick + s_time.onehour * 7 + 678)
        self.eq(s_time.parse('20240102030405-07'), tick + s_time.onehour * 7)

        # UTC/GMT prefixed offsets, parenthesized zone names, and Go style offset + abbreviation
        self.eq(s_time.parse('2024-01-02 03:04:05 GMT+5'), tick - s_time.onehour * 5)
        self.eq(s_time.parse('2024-01-02 03:04:05 GMT-5'), tick + s_time.onehour * 5)
        self.eq(s_time.parse('2024-01-02 03:04:05 UTC+05:00'), tick - s_time.onehour * 5)
        self.eq(s_time.parse('2024-01-02 03:04:05 UTC-0530'), tick + s_time.onehour * 5 + s_time.onemin * 30)
        self.eq(s_time.parse('2024-01-02 03:04:05 (EST)'), tick + s_time.onehour * 5)
        self.eq(s_time.parse('2024-01-02 03:04:05.123 +0700 UTC'), tick - s_time.onehour * 7 + 123)
        self.eq(s_time.parse('2024-01-02 03:04:05.123 -0500 EST'), tick + s_time.onehour * 5 + 123)

        # inputs which are correct today must keep working
        tvs = (
            '2024-01-02 03:04:05',
            '2024/01/02 03:04:05',
            '2024.01.02 03:04:05',
            '2024_01_02 03:04:05',
            '2024-01-02-03-04-05',
            '2024-01-02@03:04:05',
            '2024-01-02T03:04:05',
            '2024-01-02T03:04:05Z',
            '20240102030405',
            '2024-01-02 03:04:05 (UTC)',
            '2024-01-02 03:04:05 GMT+0',
            '2024-01-02 03:04:05 UTC+00:00',
            '2024-01-02 03:04:05 UTC',
            '2024-01-02 03:04:05 +00:00',
            'Tue, 2 Jan 2024 03:04:05 GMT',
        )
        for tv in tvs:
            self.eq(s_time.parse(tv), tick, msg=tv)

        self.eq(s_time.parse('2024-01-02 03:04:05.123456789 +0000 UTC', chop=True), tick + 123)
        self.eq(s_time.parse('2024-01-02 03:04:05.123'), tick + 123)
        self.eq(s_time.parse('2024-01-02 03:04:05,123'), tick + 123)
        self.eq(s_time.parse('20240102030405123'), tick + 123)
        self.eq(s_time.parse('2024_01_02'), s_time.parse('2024-01-02'))
        self.eq(s_time.parse('2024'), s_time.parse('2024-01-01'))
        self.eq(s_time.parse('2024-01'), s_time.parse('2024-01-01'))
        self.eq(s_time.parse('2024-01-02?'), s_time.parse('2024-01-02'))

        tick, tock = s_time.wildrange('2024-01')
        self.eq(tick, s_time.parse('2024-01-01'))
        self.eq(tock, s_time.parse('2024-02-01'))

        with self.raises(s_exc.BadTypeValu):
            s_time.wildrange('2024-1')

        # a wildcard prefix ending in a separator ( a lift of 2024/01/* or 2024-01-02 03:* )
        self.eq(s_time.wildrange('2024/01/'), s_time.wildrange('2024/01'))
        self.eq(s_time.wildrange('2024-01-02 03:'), s_time.wildrange('2024010203'))
        self.eq(s_time.wildrange('2024-01-02t03:'), s_time.wildrange('2024010203'))

        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('newp')
        self.isin('Unknown time format for newp', cm.exception.get('mesg'))

    def test_time_toutc(self):
        tick = s_time.parse('2020-02-11 14:08:00.123')
        self.eq(s_time.toUTC(tick, 'EST'), tick + (s_time.onehour * 5))
