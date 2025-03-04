##############################################################################
# Taken from the cpython 3.11 source branch after the 3.11.10 release.
# It has been modified for vendored imports and vendored test harness.
##############################################################################

# Simple test suite for http/cookies.py

from http import cookies

# s_v_utils runs the monkeypatch
import synapse.vendor.utils as s_v_utils

class CookieTests(s_v_utils.VendorTest):

    def test_unquote(self):
        cases = [
            (r'a="b=\""', 'b="'),
            (r'a="b=\\"', 'b=\\'),
            (r'a="b=\="', 'b=='),
            (r'a="b=\n"', 'b=n'),
            (r'a="b=\042"', 'b="'),
            (r'a="b=\134"', 'b=\\'),
            (r'a="b=\377"', 'b=\xff'),
            (r'a="b=\400"', 'b=400'),
            (r'a="b=\42"', 'b=42'),
            (r'a="b=\\042"', 'b=\\042'),
            (r'a="b=\\134"', 'b=\\134'),
            (r'a="b=\\\""', 'b=\\"'),
            (r'a="b=\\\042"', 'b=\\"'),
            (r'a="b=\134\""', 'b=\\"'),
            (r'a="b=\134\042"', 'b=\\"'),
        ]
        for encoded, decoded in cases:
            with self.subTest(encoded):
                C = cookies.SimpleCookie()
                C.load(encoded)
                self.assertEqual(C['a'].value, decoded)

    def test_unquote_large(self):
        n = 10**6
        for encoded in r'\\', r'\134':
            with self.subTest(encoded):
                data = 'a="b=' + encoded * n + ';"'
                C = cookies.SimpleCookie()
                C.load(data)
                value = C['a'].value
                self.assertEqual(value[:3], 'b=\\')
                self.assertEqual(value[-2:], '\\;')
                self.assertEqual(len(value), n + 3)
