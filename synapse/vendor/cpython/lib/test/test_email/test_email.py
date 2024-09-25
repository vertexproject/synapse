##############################################################################
# Taken from the cpython 3.11 source branch after the 3.11.10 release.
# It has been modified for vendored imports and vendored test harness, and
# then downselected for coverage of email.utils / email._parseaddr functions.
##############################################################################
# Copyright (C) 2001-2010 Python Software Foundation
# Contact: email-sig@python.org
# email package unit tests

import time
import unittest

import synapse.vendor.cpython.lib.email.utils as utils

import synapse.vendor.utils as s_v_utils

class TestMiscellaneous(s_v_utils.VendorTest):

    def test_formatdate(self):
        now = time.time()
        self.assertEqual(utils.parsedate(utils.formatdate(now))[:6],
                         time.gmtime(now)[:6])

    def test_formatdate_localtime(self):
        now = time.time()
        self.assertEqual(
            utils.parsedate(utils.formatdate(now, localtime=True))[:6],
            time.localtime(now)[:6])

    def test_formatdate_usegmt(self):
        now = time.time()
        self.assertEqual(
            utils.formatdate(now, localtime=False),
            time.strftime('%a, %d %b %Y %H:%M:%S -0000', time.gmtime(now)))
        self.assertEqual(
            utils.formatdate(now, localtime=False, usegmt=True),
            time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(now)))

    # parsedate and parsedate_tz will become deprecated interfaces someday
    def test_parsedate_returns_None_for_invalid_strings(self):
        # See also test_parsedate_to_datetime_with_invalid_raises_valueerror
        # in test_utils.
        invalid_dates = [
            '',
            ' ',
            '0',
            'A Complete Waste of Time',
            'Wed, 3 Apr 2002 12.34.56.78+0800',
            '17 June , 2022',
            'Friday, -Nov-82 16:14:55 EST',
            'Friday, Nov--82 16:14:55 EST',
            'Friday, 19-Nov- 16:14:55 EST',
        ]
        for dtstr in invalid_dates:
            with self.subTest(dtstr=dtstr):
                self.assertIsNone(utils.parsedate(dtstr))
                self.assertIsNone(utils.parsedate_tz(dtstr))
        # Not a part of the spec but, but this has historically worked:
        self.assertIsNone(utils.parsedate(None))
        self.assertIsNone(utils.parsedate_tz(None))

    def test_parsedate_compact(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58:26 +0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, 28800))
        # The FWS after the comma is optional
        self.assertEqual(utils.parsedate_tz('Wed,3 Apr 2002 14:58:26 +0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, 28800))
        # The comma is optional
        self.assertEqual(utils.parsedate_tz('Wed 3 Apr 2002 14:58:26 +0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, 28800))

    def test_parsedate_no_dayofweek(self):
        eq = self.assertEqual
        eq(utils.parsedate_tz('5 Feb 2003 13:47:26 -0800'),
           (2003, 2, 5, 13, 47, 26, 0, 1, -1, -28800))
        eq(utils.parsedate_tz('February 5, 2003 13:47:26 -0800'),
           (2003, 2, 5, 13, 47, 26, 0, 1, -1, -28800))

    def test_parsedate_no_space_before_positive_offset(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58:26+0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, 28800))

    def test_parsedate_no_space_before_negative_offset(self):
        # Issue 1155362: we already handled '+' for this case.
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58:26-0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, -28800))

    def test_parsedate_accepts_time_with_dots(self):
        eq = self.assertEqual
        eq(utils.parsedate_tz('5 Feb 2003 13.47.26 -0800'),
           (2003, 2, 5, 13, 47, 26, 0, 1, -1, -28800))
        eq(utils.parsedate_tz('5 Feb 2003 13.47 -0800'),
           (2003, 2, 5, 13, 47, 0, 0, 1, -1, -28800))

    def test_parsedate_rfc_850(self):
        self.assertEqual(utils.parsedate_tz('Friday, 19-Nov-82 16:14:55 EST'),
                         (1982, 11, 19, 16, 14, 55, 0, 1, -1, -18000))

    def test_parsedate_no_seconds(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58 +0800'),
                         (2002, 4, 3, 14, 58, 0, 0, 1, -1, 28800))

    def test_parsedate_dot_time_delimiter(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14.58.26 +0800'),
                         (2002, 4, 3, 14, 58, 26, 0, 1, -1, 28800))
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14.58 +0800'),
                         (2002, 4, 3, 14, 58, 0, 0, 1, -1, 28800))

    def test_parsedate_acceptable_to_time_functions(self):
        eq = self.assertEqual
        timetup = utils.parsedate('5 Feb 2003 13:47:26 -0800')
        t = int(time.mktime(timetup))
        eq(time.localtime(t)[:6], timetup[:6])
        eq(int(time.strftime('%Y', timetup)), 2003)
        timetup = utils.parsedate_tz('5 Feb 2003 13:47:26 -0800')
        t = int(time.mktime(timetup[:9]))
        eq(time.localtime(t)[:6], timetup[:6])
        eq(int(time.strftime('%Y', timetup[:9])), 2003)

    def test_mktime_tz(self):
        self.assertEqual(utils.mktime_tz((1970, 1, 1, 0, 0, 0,
                                          -1, -1, -1, 0)), 0)
        self.assertEqual(utils.mktime_tz((1970, 1, 1, 0, 0, 0,
                                          -1, -1, -1, 1234)), -1234)

    def test_parsedate_y2k(self):
        """Test for parsing a date with a two-digit year.

        Parsing a date with a two-digit year should return the correct
        four-digit year. RFC822 allows two-digit years, but RFC2822 (which
        obsoletes RFC822) requires four-digit years.

        """
        self.assertEqual(utils.parsedate_tz('25 Feb 03 13:47:26 -0800'),
                         utils.parsedate_tz('25 Feb 2003 13:47:26 -0800'))
        self.assertEqual(utils.parsedate_tz('25 Feb 71 13:47:26 -0800'),
                         utils.parsedate_tz('25 Feb 1971 13:47:26 -0800'))

    def test_parseaddr_empty(self):
        self.assertEqual(utils.parseaddr('<>'), ('', ''))
        self.assertEqual(utils.formataddr(utils.parseaddr('<>')), '')

    def test_parseaddr_multiple_domains(self):
        self.assertEqual(
            utils.parseaddr('a@b@c'),
            ('', '')
        )
        self.assertEqual(
            utils.parseaddr('a@b.c@c'),
            ('', '')
        )
        self.assertEqual(
            utils.parseaddr('a@172.17.0.1@c'),
            ('', '')
        )

    def test_noquote_dump(self):
        self.assertEqual(
            utils.formataddr(('A Silly Person', 'person@dom.ain')),
            'A Silly Person <person@dom.ain>')

    def test_escape_dump(self):
        self.assertEqual(
            utils.formataddr(('A (Very) Silly Person', 'person@dom.ain')),
            r'"A (Very) Silly Person" <person@dom.ain>')
        self.assertEqual(
            utils.parseaddr(r'"A \(Very\) Silly Person" <person@dom.ain>'),
            ('A (Very) Silly Person', 'person@dom.ain'))
        a = r'A \(Special\) Person'
        b = 'person@dom.ain'
        self.assertEqual(utils.parseaddr(utils.formataddr((a, b))), (a, b))

    def test_escape_backslashes(self):
        self.assertEqual(
            utils.formataddr((r'Arthur \Backslash\ Foobar', 'person@dom.ain')),
            r'"Arthur \\Backslash\\ Foobar" <person@dom.ain>')
        a = r'Arthur \Backslash\ Foobar'
        b = 'person@dom.ain'
        self.assertEqual(utils.parseaddr(utils.formataddr((a, b))), (a, b))

    def test_quotes_unicode_names(self):
        # issue 1690608.  email.utils.formataddr() should be rfc2047 aware.
        name = "H\u00e4ns W\u00fcrst"
        addr = 'person@dom.ain'
        utf8_base64 = "=?utf-8?b?SMOkbnMgV8O8cnN0?= <person@dom.ain>"
        latin1_quopri = "=?iso-8859-1?q?H=E4ns_W=FCrst?= <person@dom.ain>"
        self.assertEqual(utils.formataddr((name, addr)), utf8_base64)
        self.assertEqual(utils.formataddr((name, addr), 'iso-8859-1'),
                         latin1_quopri)

    def test_invalid_charset_like_object_raises_error(self):
        # issue 1690608.  email.utils.formataddr() should be rfc2047 aware.
        name = "H\u00e4ns W\u00fcrst"
        addr = 'person@dom.ain'
        # An object without a header_encode method:
        bad_charset = object()
        self.assertRaises(AttributeError, utils.formataddr, (name, addr),
                          bad_charset)

    def test_unicode_address_raises_error(self):
        # issue 1690608.  email.utils.formataddr() should be rfc2047 aware.
        addr = 'pers\u00f6n@dom.in'
        self.assertRaises(UnicodeError, utils.formataddr, (None, addr))
        self.assertRaises(UnicodeError, utils.formataddr, ("Name", addr))

    def test_name_with_dot(self):
        x = 'John X. Doe <jxd@example.com>'
        y = '"John X. Doe" <jxd@example.com>'
        a, b = ('John X. Doe', 'jxd@example.com')
        self.assertEqual(utils.parseaddr(x), (a, b))
        self.assertEqual(utils.parseaddr(y), (a, b))
        # formataddr() quotes the name if there's a dot in it
        self.assertEqual(utils.formataddr((a, b)), y)

    def test_parseaddr_preserves_quoted_pairs_in_addresses(self):
        # issue 10005.  Note that in the third test the second pair of
        # backslashes is not actually a quoted pair because it is not inside a
        # comment or quoted string: the address being parsed has a quoted
        # string containing a quoted backslash, followed by 'example' and two
        # backslashes, followed by another quoted string containing a space and
        # the word 'example'.  parseaddr copies those two backslashes
        # literally.  Per rfc5322 this is not technically correct since a \ may
        # not appear in an address outside of a quoted string.  It is probably
        # a sensible Postel interpretation, though.
        eq = self.assertEqual
        eq(utils.parseaddr('""example" example"@example.com'),
           ('', '""example" example"@example.com'))
        eq(utils.parseaddr('"\\"example\\" example"@example.com'),
           ('', '"\\"example\\" example"@example.com'))
        eq(utils.parseaddr('"\\\\"example\\\\" example"@example.com'),
           ('', '"\\\\"example\\\\" example"@example.com'))

    def test_parseaddr_preserves_spaces_in_local_part(self):
        # issue 9286.  A normal RFC5322 local part should not contain any
        # folding white space, but legacy local parts can (they are a sequence
        # of atoms, not dotatoms).  On the other hand we strip whitespace from
        # before the @ and around dots, on the assumption that the whitespace
        # around the punctuation is a mistake in what would otherwise be
        # an RFC5322 local part.  Leading whitespace is, usual, stripped as well.
        self.assertEqual(('', "merwok wok@xample.com"),
                         utils.parseaddr("merwok wok@xample.com"))
        self.assertEqual(('', "merwok  wok@xample.com"),
                         utils.parseaddr("merwok  wok@xample.com"))
        self.assertEqual(('', "merwok  wok@xample.com"),
                         utils.parseaddr(" merwok  wok  @xample.com"))
        self.assertEqual(('', 'merwok"wok"  wok@xample.com'),
                         utils.parseaddr('merwok"wok"  wok@xample.com'))
        self.assertEqual(('', 'merwok.wok.wok@xample.com'),
                         utils.parseaddr('merwok. wok .  wok@xample.com'))

    def test_formataddr_does_not_quote_parens_in_quoted_string(self):
        addr = ("'foo@example.com' (foo@example.com)",
                'foo@example.com')
        addrstr = ('"\'foo@example.com\' '
                   '(foo@example.com)" <foo@example.com>')
        self.assertEqual(utils.parseaddr(addrstr), addr)
        self.assertEqual(utils.formataddr(addr), addrstr)

    def test_multiline_from_comment(self):
        x = """\
    Foo
    \tBar <foo@example.com>"""
        self.assertEqual(utils.parseaddr(x), ('Foo Bar', 'foo@example.com'))

    def test_quote_dump(self):
        self.assertEqual(
            utils.formataddr(('A Silly; Person', 'person@dom.ain')),
            r'"A Silly; Person" <person@dom.ain>')

    def test_getaddresses(self):
        eq = self.assertEqual
        eq(utils.getaddresses(['aperson@dom.ain (Al Person)',
                               'Bud Person <bperson@dom.ain>']),
           [('Al Person', 'aperson@dom.ain'),
            ('Bud Person', 'bperson@dom.ain')])

    def test_getaddresses_comma_in_name(self):
        """GH-106669 regression test."""
        self.assertEqual(
            utils.getaddresses(
                [
                    '"Bud, Person" <bperson@dom.ain>',
                    'aperson@dom.ain (Al Person)',
                    '"Mariusz Felisiak" <to@example.com>',
                ]
            ),
            [
                ('Bud, Person', 'bperson@dom.ain'),
                ('Al Person', 'aperson@dom.ain'),
                ('Mariusz Felisiak', 'to@example.com'),
            ],
        )

    def test_parsing_errors(self):
        """Test for parsing errors from CVE-2023-27043 and CVE-2019-16056"""
        alice = 'alice@example.org'
        bob = 'bob@example.com'
        empty = ('', '')

        # Test utils.getaddresses() and utils.parseaddr() on malformed email
        # addresses: default behavior (strict=True) rejects malformed address,
        # and strict=False which tolerates malformed address.
        for invalid_separator, expected_non_strict in (
                ('(', [(f'<{bob}>', alice)]),
                (')', [('', alice), empty, ('', bob)]),
                ('<', [('', alice), empty, ('', bob), empty]),
                ('>', [('', alice), empty, ('', bob)]),
                ('[', [('', f'{alice}[<{bob}>]')]),
                (']', [('', alice), empty, ('', bob)]),
                ('@', [empty, empty, ('', bob)]),
                (';', [('', alice), empty, ('', bob)]),
                (':', [('', alice), ('', bob)]),
                ('.', [('', alice + '.'), ('', bob)]),
                ('"', [('', alice), ('', f'<{bob}>')]),
        ):
            address = f'{alice}{invalid_separator}<{bob}>'
            with self.subTest(address=address):
                self.assertEqual(utils.getaddresses([address]),
                                 [empty])
                self.assertEqual(utils.getaddresses([address], strict=False),
                                 expected_non_strict)

                self.assertEqual(utils.parseaddr([address]),
                                 empty)
                self.assertEqual(utils.parseaddr([address], strict=False),
                                 ('', address))

        # Comma (',') is treated differently depending on strict parameter.
        # Comma without quotes.
        address = f'{alice},<{bob}>'
        self.assertEqual(utils.getaddresses([address]),
                         [('', alice), ('', bob)])
        self.assertEqual(utils.getaddresses([address], strict=False),
                         [('', alice), ('', bob)])
        self.assertEqual(utils.parseaddr([address]),
                         empty)
        self.assertEqual(utils.parseaddr([address], strict=False),
                         ('', address))

        # Real name between quotes containing comma.
        address = '"Alice, alice@example.org" <bob@example.com>'
        expected_strict = ('Alice, alice@example.org', 'bob@example.com')
        self.assertEqual(utils.getaddresses([address]), [expected_strict])
        self.assertEqual(utils.getaddresses([address], strict=False), [expected_strict])
        self.assertEqual(utils.parseaddr([address]), expected_strict)
        self.assertEqual(utils.parseaddr([address], strict=False),
                         ('', address))

        # Valid parenthesis in comments.
        address = 'alice@example.org (Alice)'
        expected_strict = ('Alice', 'alice@example.org')
        self.assertEqual(utils.getaddresses([address]), [expected_strict])
        self.assertEqual(utils.getaddresses([address], strict=False), [expected_strict])
        self.assertEqual(utils.parseaddr([address]), expected_strict)
        self.assertEqual(utils.parseaddr([address], strict=False),
                         ('', address))

        # Invalid parenthesis in comments.
        address = 'alice@example.org )Alice('
        self.assertEqual(utils.getaddresses([address]), [empty])
        self.assertEqual(utils.getaddresses([address], strict=False),
                         [('', 'alice@example.org'), ('', ''), ('', 'Alice')])
        self.assertEqual(utils.parseaddr([address]), empty)
        self.assertEqual(utils.parseaddr([address], strict=False),
                         ('', address))

        # Two addresses with quotes separated by comma.
        address = '"Jane Doe" <jane@example.net>, "John Doe" <john@example.net>'
        self.assertEqual(utils.getaddresses([address]),
                         [('Jane Doe', 'jane@example.net'),
                          ('John Doe', 'john@example.net')])
        self.assertEqual(utils.getaddresses([address], strict=False),
                         [('Jane Doe', 'jane@example.net'),
                          ('John Doe', 'john@example.net')])
        self.assertEqual(utils.parseaddr([address]), empty)
        self.assertEqual(utils.parseaddr([address], strict=False),
                         ('', address))

        # Test email.utils.supports_strict_parsing attribute
        self.assertEqual(utils.supports_strict_parsing, True)

    def test_getaddresses_nasty(self):
        for addresses, expected in (
                (['"Sürname, Firstname" <to@example.com>'],
                 [('Sürname, Firstname', 'to@example.com')]),

                (['foo: ;'],
                 [('', '')]),

                (['foo: ;', '"Jason R. Mastaler" <jason@dom.ain>'],
                 [('', ''), ('Jason R. Mastaler', 'jason@dom.ain')]),

                ([r'Pete(A nice \) chap) <pete(his account)@silly.test(his host)>'],
                 [('Pete (A nice ) chap his account his host)', 'pete@silly.test')]),

                (['(Empty list)(start)Undisclosed recipients  :(nobody(I know))'],
                 [('', '')]),

                (['Mary <@machine.tld:mary@example.net>, , jdoe@test   . example'],
                 [('Mary', 'mary@example.net'), ('', ''), ('', 'jdoe@test.example')]),

                (['John Doe <jdoe@machine(comment).  example>'],
                 [('John Doe (comment)', 'jdoe@machine.example')]),

                (['"Mary Smith: Personal Account" <smith@home.example>'],
                 [('Mary Smith: Personal Account', 'smith@home.example')]),

                (['Undisclosed recipients:;'],
                 [('', '')]),

                ([r'<boss@nil.test>, "Giant; \"Big\" Box" <bob@example.net>'],
                 [('', 'boss@nil.test'), ('Giant; "Big" Box', 'bob@example.net')]),
        ):
            with self.subTest(addresses=addresses):
                self.assertEqual(utils.getaddresses(addresses),
                                 expected)
                self.assertEqual(utils.getaddresses(addresses, strict=False),
                                 expected)

        addresses = ['[]*-- =~$']
        self.assertEqual(utils.getaddresses(addresses),
                         [('', '')])
        self.assertEqual(utils.getaddresses(addresses, strict=False),
                         [('', ''), ('', ''), ('', '*--')])

    def test_getaddresses_embedded_comment(self):
        """Test proper handling of a nested comment"""
        eq = self.assertEqual
        addrs = utils.getaddresses(['User ((nested comment)) <foo@bar.com>'])
        eq(addrs[0][1], 'foo@bar.com')

    def test_iter_escaped_chars(self):
        self.assertEqual(list(utils._iter_escaped_chars(r'a\\b\"c\\"d')),
                         [(0, 'a'),
                          (2, '\\\\'),
                          (3, 'b'),
                          (5, '\\"'),
                          (6, 'c'),
                          (8, '\\\\'),
                          (9, '"'),
                          (10, 'd')])
        self.assertEqual(list(utils._iter_escaped_chars('a\\')),
                         [(0, 'a'), (1, '\\')])

    def test_strip_quoted_realnames(self):
        def check(addr, expected):
            self.assertEqual(utils._strip_quoted_realnames(addr), expected)

        check('"Jane Doe" <jane@example.net>, "John Doe" <john@example.net>',
              ' <jane@example.net>,  <john@example.net>')
        check(r'"Jane \"Doe\"." <jane@example.net>',
              ' <jane@example.net>')

        # special cases
        check(r'before"name"after', 'beforeafter')
        check(r'before"name"', 'before')
        check(r'b"name"', 'b')  # single char
        check(r'"name"after', 'after')
        check(r'"name"a', 'a')  # single char
        check(r'"name"', '')

        # no change
        for addr in (
                'Jane Doe <jane@example.net>, John Doe <john@example.net>',
                'lone " quote',
        ):
            self.assertEqual(utils._strip_quoted_realnames(addr), addr)

    def test_check_parenthesis(self):
        addr = 'alice@example.net'
        self.assertTrue(utils._check_parenthesis(f'{addr} (Alice)'))
        self.assertFalse(utils._check_parenthesis(f'{addr} )Alice('))
        self.assertFalse(utils._check_parenthesis(f'{addr} (Alice))'))
        self.assertFalse(utils._check_parenthesis(f'{addr} ((Alice)'))

        # Ignore real name between quotes
        self.assertTrue(utils._check_parenthesis(f'")Alice((" {addr}'))

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
