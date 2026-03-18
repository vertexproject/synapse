##############################################################################
# Taken from the cpython 3.11 source branch after the 3.11.10 release.
# It has been modified for vendored imports and vendored test harness.
##############################################################################

import datetime
import time
import unittest
import sys
import os.path
import zoneinfo

from synapse.vendor.cpython.lib.email import utils

import synapse.vendor.utils as s_v_utils
import synapse.vendor.cpython.lib.test.support as t_support


class DateTimeTests(s_v_utils.VendorTest):

    datestring = 'Sun, 23 Sep 2001 20:10:55'
    dateargs = (2001, 9, 23, 20, 10, 55)
    offsetstring = ' -0700'
    utcoffset = datetime.timedelta(hours=-7)
    tz = datetime.timezone(utcoffset)
    naive_dt = datetime.datetime(*dateargs)
    aware_dt = datetime.datetime(*dateargs, tzinfo=tz)

    def test_naive_datetime(self):
        self.assertEqual(utils.format_datetime(self.naive_dt),
                         self.datestring + ' -0000')

    def test_aware_datetime(self):
        self.assertEqual(utils.format_datetime(self.aware_dt),
                         self.datestring + self.offsetstring)

    def test_usegmt(self):
        utc_dt = datetime.datetime(*self.dateargs,
                                   tzinfo=datetime.timezone.utc)
        self.assertEqual(utils.format_datetime(utc_dt, usegmt=True),
                         self.datestring + ' GMT')

    def test_usegmt_with_naive_datetime_raises(self):
        with self.assertRaises(ValueError):
            utils.format_datetime(self.naive_dt, usegmt=True)

    def test_usegmt_with_non_utc_datetime_raises(self):
        with self.assertRaises(ValueError):
            utils.format_datetime(self.aware_dt, usegmt=True)

    def test_parsedate_to_datetime(self):
        self.assertEqual(
            utils.parsedate_to_datetime(self.datestring + self.offsetstring),
            self.aware_dt)

    def test_parsedate_to_datetime_naive(self):
        self.assertEqual(
            utils.parsedate_to_datetime(self.datestring + ' -0000'),
            self.naive_dt)

    def test_parsedate_to_datetime_with_invalid_raises_valueerror(self):
        # See also test_parsedate_returns_None_for_invalid_strings in test_email.
        invalid_dates = [
            '',
            ' ',
            '0',
            'A Complete Waste of Time',
            'Wed, 3 Apr 2002 12.34.56.78+0800'
            'Tue, 06 Jun 2017 27:39:33 +0600',
            'Tue, 06 Jun 2017 07:39:33 +2600',
            'Tue, 06 Jun 2017 27:39:33',
            '17 June , 2022',
            'Friday, -Nov-82 16:14:55 EST',
            'Friday, Nov--82 16:14:55 EST',
            'Friday, 19-Nov- 16:14:55 EST',
        ]
        for dtstr in invalid_dates:
            with self.subTest(dtstr=dtstr):
                self.assertRaises(ValueError, utils.parsedate_to_datetime, dtstr)

class LocaltimeTests(s_v_utils.VendorTest):

    def test_localtime_is_tz_aware_daylight_true(self):
        t_support.patch(self, time, 'daylight', True)
        t = utils.localtime()
        self.assertIsNotNone(t.tzinfo)

    def test_localtime_is_tz_aware_daylight_false(self):
        t_support.patch(self, time, 'daylight', False)
        t = utils.localtime()
        self.assertIsNotNone(t.tzinfo)

    def test_localtime_daylight_true_dst_false(self):
        t_support.patch(self, time, 'daylight', True)
        t0 = datetime.datetime(2012, 3, 12, 1, 1)
        t1 = utils.localtime(t0, isdst=-1)
        t2 = utils.localtime(t1)
        self.assertEqual(t1, t2)

    def test_localtime_daylight_false_dst_false(self):
        t_support.patch(self, time, 'daylight', False)
        t0 = datetime.datetime(2012, 3, 12, 1, 1)
        t1 = utils.localtime(t0, isdst=-1)
        t2 = utils.localtime(t1)
        self.assertEqual(t1, t2)

    @t_support.run_with_tz('Europe/Minsk')
    def test_localtime_daylight_true_dst_true(self):
        t_support.patch(self, time, 'daylight', True)
        t0 = datetime.datetime(2012, 3, 12, 1, 1)
        t1 = utils.localtime(t0, isdst=1)
        t2 = utils.localtime(t1)
        self.assertEqual(t1, t2)

    @t_support.run_with_tz('Europe/Minsk')
    def test_localtime_daylight_false_dst_true(self):
        t_support.patch(self, time, 'daylight', False)
        t0 = datetime.datetime(2012, 3, 12, 1, 1)
        t1 = utils.localtime(t0, isdst=1)
        t2 = utils.localtime(t1)
        self.assertEqual(t1, t2)

    @t_support.run_with_tz('EST+05EDT,M3.2.0,M11.1.0')
    def test_localtime_epoch_utc_daylight_true(self):
        t_support.patch(self, time, 'daylight', True)
        t0 = datetime.datetime(1990, 1, 1, tzinfo=datetime.timezone.utc)
        t1 = utils.localtime(t0)
        t2 = t0 - datetime.timedelta(hours=5)
        t2 = t2.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))
        self.assertEqual(t1, t2)

    @t_support.run_with_tz('EST+05EDT,M3.2.0,M11.1.0')
    def test_localtime_epoch_utc_daylight_false(self):
        t_support.patch(self, time, 'daylight', False)
        t0 = datetime.datetime(1990, 1, 1, tzinfo=datetime.timezone.utc)
        t1 = utils.localtime(t0)
        t2 = t0 - datetime.timedelta(hours=5)
        t2 = t2.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))
        self.assertEqual(t1, t2)

    def test_localtime_epoch_notz_daylight_true(self):
        t_support.patch(self, time, 'daylight', True)
        t0 = datetime.datetime(1990, 1, 1)
        t1 = utils.localtime(t0)
        t2 = utils.localtime(t0.replace(tzinfo=None))
        self.assertEqual(t1, t2)

    def test_localtime_epoch_notz_daylight_false(self):
        t_support.patch(self, time, 'daylight', False)
        t0 = datetime.datetime(1990, 1, 1)
        t1 = utils.localtime(t0)
        t2 = utils.localtime(t0.replace(tzinfo=None))
        self.assertEqual(t1, t2)

    @t_support.run_with_tz('Europe/Kyiv')
    def test_variable_tzname(self):
        t0 = datetime.datetime(1984, 1, 1, tzinfo=datetime.timezone.utc)
        t1 = utils.localtime(t0)
        if t1.tzname() in ('Europe', 'UTC'):
            self.skipTest("Can't find a Kyiv timezone database")
        self.assertEqual(t1.tzname(), 'MSK')
        t0 = datetime.datetime(1994, 1, 1, tzinfo=datetime.timezone.utc)
        t1 = utils.localtime(t0)
        self.assertEqual(t1.tzname(), 'EET')

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
