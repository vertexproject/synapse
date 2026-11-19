import time
import random
import datetime
import unittest.mock as mock

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

        for text in ('07days', '-days', '-07:00+1day'):
            with self.raises(s_exc.BadTypeValu) as cm:
                s_time.delta(text)

            self.isin('invalid time delta size', cm.exception.get('mesg'))

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
        self.eq(s_time.parse('2050121703043210156789', chop=True), 2554859072101)

        # each field is read at its fixed width, so an invalid one is rejected rather than re-split
        self.eq(s_time.parse('2015-12-01 21:00:17.400'), 1449003617400)
        self.eq(s_time.parse('2015-12-01 21:00:17.4'), 1449003617400)
        self.eq(s_time.parse('20151201210017400'), 1449003617400)
        self.eq(s_time.parse('2015-12-01 21:00:17.400000999', chop=True), 1449003617400)
        for text in ('2015-13-01 21:00:17', '2015-12-32 21:00:17', '2015-02-30 21:00:17', '2015-12-01 24:00:17',
                     '2015-12-01 21:60:17', '0000-12-01 21:00:17'):
            for frac in ('', '.4', '.400', '.400123'):
                for chop in (False, True):
                    for valu in (text + frac, ''.join(c for c in text + frac if c.isdigit())):
                        with self.raises(s_exc.BadTypeValu) as cm:
                            s_time.parse(valu, chop=chop)

                        self.isin(f'Error parsing time "{valu}"', cm.exception.get('mesg'))

        # clean iso 8601 and separator free digit values return the same parse details as the general path
        rand = random.Random(0)
        dates = ('2015', '2015-11', '2015/11', '2015-11-02', '2015/11/02', '2015-11/02', '2015-11-2', '2015:11:02',
                 '2015:11:2', '2015-13-02', '2015-00-02', '2015-11-31', '2015-11-32', '2015-02-29', '2016-02-29',
                 '0000-01-01', '0001-01-01', '9999-12-31', '2015-1-02', '20151102')
        times = ('', 'T05:55', 't05:55', ' 05:55', 'T5:55', ' 5:55', 'T05:55:00', 't23:59:59', ' 05:55:59',
                 'T24:00', 'T05:60', 'T05:55:60', 'T055500', ' 0555', 'T05:55:00,1') + tuple(
                 f'{sep}05:55:00.{"123456789"[:size]}' for sep in 'Tt ' for size in range(1, 10))
        tzs = ('', '', '', 'Z', 'z', ' Z', '+05:30', '-0500', ' -05:00', '-05', '+0000', '+24:00', '-23:59', '+5:30',
               ' EST', 'x', '*', '?')
        digits = '20151102055500123456789'
        vals = [digits[:size] for size in range(1, 24)]
        for size in range(4, 24):
            vals.append(''.join(rand.choice('0123456789') for _ in range(size)))

        for _ in range(600):
            valu = rand.choice(dates) + rand.choice(times) + rand.choice(tzs)
            if rand.random() < 0.1:
                valu = rand.choice((' ', '\t', '')) + valu + rand.choice((' ', '\n', ''))

            vals.append(valu)

        tests = []
        for valu in vals:
            for kwargs in ({}, {'chop': True}, {'base': 7}):
                if (info := s_time._fastparse(valu, kwargs.get('base'), kwargs.get('chop', False))) is not None:
                    tests.append((valu, kwargs, info))

        self.gt(len(tests), 250)
        with mock.patch.object(s_time, '_fastparse', return_value=None):
            for valu, kwargs, info in tests:
                self.eq(s_time._rawparse(valu, **kwargs), info, msg=f'{valu!r} {kwargs}')

        tick = s_time.parse('2015-11-02T05:55:00Z')
        self.eq(s_time._rawparse('2015'), (datetime.datetime(2015, 1, 1), 0, 4))
        self.eq(s_time._rawparse(' 2015-11 '), (datetime.datetime(2015, 11, 1), 0, 6))
        self.eq(s_time._rawparse('2015/11/02'), (datetime.datetime(2015, 11, 2), 0, 8))
        self.eq(s_time._rawparse('2015-11-02 05:55', base=10), (datetime.datetime(2015, 11, 2, 5, 55), 10, 12))
        self.eq(s_time._rawparse('2015-11-02t05:55:00z'), (datetime.datetime(2015, 11, 2, 5, 55), 0, 14))
        self.eq(s_time._rawparse('2015-11-02T05:55:00.12 +05:30'),
                (datetime.datetime(2015, 11, 2, 5, 55, 0, 120000), 330 * s_time.onemin * -1, 16))
        self.eq(s_time._rawparse('2015-11-02T05:55:00.123456789Z', chop=True),
                (datetime.datetime(2015, 11, 2, 5, 55, 0, 123000), 0, 17))
        self.eq(s_time._rawparse('2015110205'), (datetime.datetime(2015, 11, 2, 5), 0, 10))
        self.eq(s_time._rawparse('201511020555001234567', chop=True),
                (datetime.datetime(2015, 11, 2, 5, 55, 0, 123000), 0, 17))
        self.eq(s_time.parse('2015-11-02T00:55:00-0500'), tick)
        self.eq(s_time.parse('2015-11-02T05:55:00+00:00'), tick)
        self.eq(s_time.parse('2015-11-02T05:55:00', base=5), tick + 5)

        # colon separated dates
        self.eq(s_time._fastparse('2015:11:02', None, False), (datetime.datetime(2015, 11, 2), 0, 8))
        self.eq(s_time._fastparse('2015:11:2 5:55:00+00:00', None, False),
                (datetime.datetime(2015, 11, 2, 5, 55), 0, 14))
        self.eq(s_time.parse('2015:11:02 05:55:00'), tick)
        self.eq(s_time.parse('2015:11:02T00:55:00-05:00'), tick)
        self.eq(s_time.parse('2015:11:02 05:55:00.123Z'), tick + 123)

        # colon dates the fast path declines, since mixed separators may read as an offset
        for text in ('2015:11', '2015:11:2', '2015:11-02', '2015-11:02', '2015:11/02 05:55', '2015:11:0205:55'):
            self.none(s_time._fastparse(text, None, False))

        self.eq(s_time._rawparse('2015:11'), (datetime.datetime(2015, 11, 1), 0, 6))
        self.eq(s_time._rawparse('2015:11/02 05:55'), (datetime.datetime(2015, 11, 2, 5, 55), 0, 12))
        self.eq(s_time._rawparse('2015:11:0205:55'), (datetime.datetime(2015, 11, 2, 5, 55), 0, 12))
        for text in ('2015:11:2', '2015-11:02'):
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(text)

        # a colon year and month is not read as a time with an offset
        self.eq(s_time.parsetz('2015:11-02'), ('2015:11-02', 0))
        self.eq(s_time.parse('2015:11-02'), s_time.parse('2015-11-02'))
        self.eq(s_time.parse('2015:11-05'), s_time.parse('2015-11-05'))
        self.eq(s_time.parse('2015:11-05', base=0, chop=True), s_time.parse('2015-11-05'))
        for text in ('20151102 5:55-05', '2015-11-02T05:55-05', '2015/11/02 5:55 -05', '2015:11:02 5:55-05'):
            self.eq(s_time.parse(text), s_time.parse('2015-11-02T10:55Z'))

        # values the fast path declines take the general path
        self.eq(s_time.parse('2015-11-02T05:55:00.123456Z'), tick + 123)
        self.eq(s_time.parse('2015-11-02T05:55:00.123456789Z', chop=True), tick + 123)
        self.eq(s_time.parse('2015-11-02T05:55:00+23:59'), tick - 1439 * s_time.onemin)

        for text in ('2015110', '2015-11-02T05:55:00.1234567Z', '2015-11-02T05:55:00+24:00', '2015-13-02',
                     '20151302', '2015-11-02T05:55:60', '0000-01-01'):
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(text)

        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('2015-11-02T05:55:00Z', base=0)
        self.isin('unexpected text in time value', cm.exception.get('mesg'))

        # malformed times with leftover text are not silently misparsed
        with self.raises(s_exc.BadTypeValu) as cm:
            s_time.parse('2020 jun 10 12:14:34')
        self.isin('unexpected text in time value', cm.exception.get('mesg'))

        # a single digit hour followed by minutes is zero padded
        tick = s_time.parse('2015/11/02 05:55:00.000')
        self.eq(tick, 1446443700000)
        self.eq(s_time.parse('2015/11/02 5:55:00.000'), tick)
        self.eq(s_time.parse('2015/11/02 5:55:00'), tick)
        self.eq(s_time.parse('2015-11-02T5:55:00Z'), tick)
        self.eq(s_time.parse('20151102 5:55:00'), tick)
        self.eq(s_time.parse('2015-11-02t5:55'), tick)
        self.eq(s_time.parse('2015/11/02 5:55:00 -0500'), tick + 5 * s_time.onehour)
        self.eq(s_time.parse('2015/11/02 5:55:07.123'), 1446443707123)
        self.eq(s_time.parse('2015/11/02 5:55:07.123456'), 1446443707123)
        self.eq(s_time.parse('2015/11/02 9:05:30.5'), 1446455130500)

        self.eq(s_time.parse('2015/11/02 15:55:00'), 1446479700000)
        self.eq(s_time.parse('2015'), 1420070400000)
        self.eq(s_time.parse('2015-11'), 1446336000000)
        self.eq(s_time.parse('2015-11-02'), 1446422400000)
        self.eq(s_time.parse('2021-06-07T02:*'), 1623031200000)

        # a single digit day followed by a time is zero padded
        tick = s_time.parse('2015/11/2 1:05:00')
        self.eq(tick, 1446426300000)
        self.eq(s_time.parse('2015-11-2T1:05:00'), tick)
        self.eq(s_time.parse('2015/11/2 1:05:00 -0500'), tick + 5 * s_time.onehour)
        self.eq(s_time.parse('2015/11/2 11:05:00'), 1446462300000)
        self.eq(s_time.parse('2015-11-2 01:05:00.123'), tick + 123)
        self.eq(s_time.parse('2015/11/2@1:05:00'), tick)

        # a single digit hour may end a value with a trailing colon
        for text, padded in (('2015/11/02 5:*', '2015/11/02 05:*'), ('2015/11/02 5:', '2015/11/02 05:'),
                             ('2015/11/2 1:*', '2015/11/02 01:*'), ('2015/11/02 5:?', '2015/11/02 05:?')):
            self.eq(s_time.parse(text), s_time.parse(padded))
            self.eq(s_time.wildrange(text), s_time.wildrange(padded))

        self.eq(s_time.wildrange('2015/11/02 5:*'), (1446440400000, 1446444000000))
        self.eq(s_time.parse('2015/11/02 5:?'), 1446440400000)

        # without a space, the day and hour run together
        self.eq(s_time.parse('2015/11/21:05:00'), 1448082000000)
        self.eq(s_time.parse('2015/11/21 5:55'), 1448085300000)

        # a single digit day with dash separators is not read as a timezone offset
        self.eq(s_time.parse('2015-11-2 1:05'), 1446426300000)
        self.eq(s_time.parse('2015-11-2 9:05'), 1446455100000)

        # a timezone offset is removed from where it matched
        self.eq(s_time.parse('2015-10-05T10:05:00-05'), s_time.parse('2015-10-05T15:05:00Z'))
        self.eq(s_time.parse('2015-10-05 1:05:00 -05'), s_time.parse('2015-10-05T06:05:00Z'))

        # a signed offset may follow a minute precision time, but a bare number may not
        tick = s_time.parse('2015-11-02T10:55:00Z')
        self.eq(s_time.parse('2015/11/02 5:55 -05'), tick)
        self.eq(s_time.parse('2015/11/02 05:55 -05'), tick)
        self.eq(s_time.parse('2015/11/02 05:55:00 -05 00'), tick)
        self.eq(s_time.parse('2015/11/02 05:55:00 -05 00 EST'), tick)
        self.eq(s_time.parse('2015/11/02 05:25:00 UTC-05 30'), tick)
        self.eq(s_time.parse('20151102 055500 -05'), tick)

        # spaces that split separator free digits are ignored
        self.eq(s_time.parse('20151102 055500123'), 1446443700123)
        self.eq(s_time.parse('20 15'), 1420070400000)
        self.eq(s_time.parse('2015/11/02 05:55:00.123 456'), 1446443700123)
        self.eq(s_time.parse('2015/11/02 05 55 00'), 1446443700000)
        self.eq(s_time.parse(' 2015/11/02 \t 05:55:00 \n'), 1446443700000)

        # a space separated offset may not follow the year and month, where it is the end of a date
        tick = s_time.parse('2021-06-07T02:00:00Z')
        self.eq(s_time.parse('2021-06-07 02'), tick)
        self.eq(s_time.parse('2021-06-07 02 UTC'), tick)
        self.eq(s_time.parse('2021-06-07 02Z'), tick)
        self.eq(s_time.parse('2021-06-27 02'), tick + 20 * s_time.oneday)
        self.eq(s_time.wildrange('2021-06-07 02'), (tick, tick + s_time.onehour))
        self.eq(s_time.parse('2021-06-07 02', base=0), tick)
        self.eq(s_time.parsetz('2021-06-07 02 est'), ('2021-06-07 02', 5 * s_time.onehour))
        self.eq(s_time.parsetz('2021-06-07 -05 00'), ('2021-06-07', 5 * s_time.onehour))
        self.eq(s_time.parsetz('202106-07 02'), ('202106-07 02', 0))
        self.eq(s_time.parsetz('2021:06 -07 02 est'), ('2021:06 -07 02', 5 * s_time.onehour))
        self.eq(s_time.parsetz('20151102 0555 -05 00'), ('20151102 0555', 5 * s_time.onehour))
        self.eq(s_time.parsetz('2015/11/02 05:55:00.123 456 -05 00'),
                ('2015/11/02 05:55:00.123 456', 5 * s_time.onehour))
        self.eq(s_time.parsetz('2015/11/02 05:55 -05 00 est'), ('2015/11/02 05:55', 5 * s_time.onehour))

        # ... nor right after the year, or a space separated year and month
        for text, tick in (('2015-11 02', 1446422400000), ('2015-11 25', 1448409600000),
                           ('2015 11-02 05', 1446440400000)):
            self.eq(s_time.parsetz(text), (text, 0))
            self.eq(s_time.parse(text), tick)
            self.eq(s_time.parse(text, base=0, chop=True), tick)

        self.eq(s_time.parsetz('2015 -05 00'), ('2015 -05 00', 0))
        self.eq(s_time.parsetz('2015 11 02 -05 00'), ('2015 11 02', 5 * s_time.onehour))

        with self.raises(s_exc.BadTypeValu):
            s_time.parse('2021-06-07 02 EST')

        # an offset is not read as a time once a zone name applies
        with self.raises(s_exc.BadTypeValu):
            s_time.parse('2021-06-07 -0500 (EST)')

        self.eq(s_time.parsetz('2021-06-07 -0500 (est)'), ('2021-06-07', 5 * s_time.onehour))
        self.eq(s_time.parse('2021-06-07 02:03 -05 (EST)'), s_time.parse('2021-06-07T07:03Z'))

        # a parenthesized comment after a numeric offset is dropped and the offset applies
        tick = s_time.parse('2021-06-07T02:03:04Z')
        self.eq(s_time.parse('2021-06-07 02:03:04 +00:00 (UTC)'), tick)
        self.eq(s_time.parse('2021-06-07 02:03:04 +0000 (UTC)'), tick)
        self.eq(s_time.parse('2021-06-07 02:03:04 -07:00 (PDT)'), tick + 7 * s_time.onehour)
        self.eq(s_time.parse('2021-06-07 02:03:04 -07:00 (Pacific Daylight Time)'), tick + 7 * s_time.onehour)
        self.eq(s_time.parse('Thu, 27 Sep 2018 12:10:44 -0700 (PDT)'), s_time.parse('2018-09-27T19:10:44Z'))
        self.eq(s_time.parse('2021-06-07 02:03:04 (EST)'), tick + 5 * s_time.onehour)
        self.eq(s_time.parsetz('2021-06-07 02:03:04 (pdt)'), ('2021-06-07 02:03:04', 7 * s_time.onehour))
        for text in ('2021-06-07 02:03:04 (nope)', '2021-06-07 02:03:04 (-07:00)'):
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(text)

        # a basic format time may carry an undotted fraction
        self.eq(s_time.parse('20170710t220448480z'), s_time.parse('2017-07-10T22:04:48.480Z'))
        self.eq(s_time.parse('20190425t121011z'), s_time.parse('2019-04-25T12:10:11Z'))

        # an hour offset may follow a basic format time
        tick = s_time.parse('2021-06-07T02:03:04Z')
        self.eq(s_time.parse('2021-06-07T020304+00'), tick)
        self.eq(s_time.parse('20210607T020304.123+00'), tick + 123)
        self.eq(s_time.parse('2021-06-07T020304+05'), s_time.parse('2021-06-06T21:03:04Z'))
        self.eq(s_time.parse('2021/06/07t0203 -05'), tick + 5 * s_time.onehour - 4 * s_time.onesec)
        with self.raises(s_exc.BadTypeValu):
            s_time.parse('2021t0203+05')

        # ... including one after a space
        self.eq(s_time.parse('2021-06-07 020304+00'), tick)
        self.eq(s_time.parse('2021-06-07 020304-05'), tick + 5 * s_time.onehour)
        self.eq(s_time.parse('2021-06-07 020304 -05'), tick + 5 * s_time.onehour)
        self.eq(s_time.parse('2021-06-07 020304.123-05'), tick + 5 * s_time.onehour + 123)
        self.eq(s_time.parse('20210607 020304-05'), tick + 5 * s_time.onehour)
        self.eq(s_time.parse('2021-06-07 0203-05'), tick + 5 * s_time.onehour - 4 * s_time.onesec)
        self.eq(s_time.parse('2021-06-07 0203 -05'), tick + 5 * s_time.onehour - 4 * s_time.onesec)
        self.eq(s_time.parse('2021-06-07 0203+05'), tick - 5 * s_time.onehour - 4 * s_time.onesec)
        self.eq(s_time.parsetz('2021/06/07 0203-05'), ('2021/06/07 0203', 5 * s_time.onehour))

        # ... or a space separated or separator free time of minute precision
        for text in ('2021-06-07 02 03 -05', '2021-06-07 02 03-05', '20210607T02 03-05', '202106070203-05',
                     '202106070203 -05', '2021 06 07 02 03-05'):
            self.eq(s_time.parse(text), tick + 5 * s_time.onehour - 4 * s_time.onesec)

        self.eq(s_time.parse('202106070203+05'), tick - 5 * s_time.onehour - 4 * s_time.onesec)
        self.eq(s_time.parse('2021 06 7 02 03 04-05'), tick + 5 * s_time.onehour)
        self.eq(s_time.parsetz('2021-06-07 02 03 -05'), ('2021-06-07 02 03', 5 * s_time.onehour))
        self.eq(s_time.parsetz('2021060702030-05'), ('2021060702030', 5 * s_time.onehour))

        # ... or a basic time after a one digit day
        for text in ('2021/06/7T0203-05', '2021-06-7 0203-05', '2021/06/7 0203 -05', '2021.06.7t0203-05',
                     '2021/06/7T07:03+00', '2021/06/7T0203-0500'):
            self.eq(s_time.parse(text), tick + 5 * s_time.onehour - 4 * s_time.onesec)

        self.eq(s_time.parse('2021-06-7 020304.123-05'), tick + 5 * s_time.onehour + 123)
        self.eq(s_time.parsetz('2021-06-7 0203-05'), ('2021-06-7 0203', 5 * s_time.onehour))
        with self.raises(s_exc.BadTypeValu):
            s_time.parse('2021060702030-05')

        # ... after any date separator
        for sep in '.:_':
            for text, offs in ((f'2021{sep}06{sep}07 020304', 0), (f'2021{sep}06{sep}07T020304', 0),
                               (f'2021{sep}06{sep}07T020304.123', 123)):
                self.eq(s_time.parse(text + '+00'), tick + offs)
                self.eq(s_time.parse(text + '-05'), tick + offs + 5 * s_time.onehour)

        # a trailing number after a date or an hour is not an offset
        for text in ('2021-06-07-05', '2021-06-05', '2021-06-07 02-05', '2021-06-07 020-05', '20210607-05',
                     '2021060702-05', '2021-06-07 02 -05', '2021 06 07 02-05'):
            self.eq(s_time.parsetz(text), (text, 0))

        # any whitespace separates fields, and a leading byte order mark is ignored
        for text in ('2021-06-07\t02:03:04', '2021-06-07\n02:03:04', '2021-06-07\r\n02:03:04', '2021-06-07\xa002:03:04',
                     '2021-06-07 02:03:04', '2021-06-07　02:03:04', '﻿2021-06-07T02:03:04Z'):
            self.eq(s_time.parse(text), tick)

        self.eq(s_time.parse('﻿2021-06-07'), s_time.parse('2021-06-07'))

        # unicode hyphens and the fullwidth colon are not separators
        for text in ('2021‐06‐07', '2021−06−07', '2021-06-07 02：03'):
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(text)

        # a precision marker may follow a timezone
        for text, offs in (('2021-06-07T02:03:04Z*', 0), ('2021-06-07T02:03:04Z?', 0),
                           ('2021-06-07T02:03:04 EST*', 5), ('2021-06-07T02:03:04 -05:00*', 5)):
            base = offs * s_time.onehour
            self.eq(s_time.parse(text), tick + base)
            self.eq(s_time.wildrange(text), (tick + base, tick + base + s_time.onesec))

        self.eq(s_time.parse('2021-06-07T02:03:04 EST?'), tick + 5 * s_time.onehour)
        self.eq(s_time.parsetz('2021-06-07t02:03:04z?'), ('2021-06-07t02:03:04?', 0))
        self.eq(s_time.parsetz('2021-06-07?'), ('2021-06-07?', 0))

        # a wild card range past the maximum time is rejected
        for text in ('9999-12-31', '9999-12-31 UTC+0', '9999-12-31 (EST)', '9999', '9999-12-31T23:59:59'):
            with self.raises(s_exc.BadTypeValu):
                s_time.wildrange(text)

        # a long run of digits before an hour offset is rejected in linear time
        for text in ('x' + '1 ' * 100000 + '+07', '1 ' * 100000 + 'x+07', '1 ' * 100000 + '+07 (est)'):
            start = time.perf_counter()
            with self.raises(s_exc.BadTypeValu):
                s_time.parse(text)

            self.lt(time.perf_counter() - start, 1)

        self.eq(s_time.parsetz('2015 11 02 05 55 00 -05'), ('2015 11 02 05 55 00', 5 * s_time.onehour))

        for text in ('2015/1/2', '2015/11/02 5:5:00', '2015/11/02 5', '2015/11/2', '2015/1/02 01:05:00',
                     '2015/11/2 5', '2015/11/2:05:00', '2015/11/2/05:00', '2015/11/215:55', '2015/11/215:55:00',
                     '201511215:55', '2015/11/02 5:55 05', '2015/11/02 05:55 05'):
            with self.raises(s_exc.BadTypeValu) as cm:
                s_time.parse(text)

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
