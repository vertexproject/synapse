import synapse.exc as s_exc
import synapse.lib.chop as s_chop

import synapse.lookup.cvss as s_cvss

import synapse.tests.utils as s_t_utils

class ChopTest(s_t_utils.SynTest):
    def test_chop_digits(self):
        self.eq(s_chop.digits('a1b2c3'), '123')

    def test_chop_tags(self):
        tags = s_chop.tags('foo.bar.baz')
        self.eq(tags, ('foo', 'foo.bar', 'foo.bar.baz'))

    def test_chop_tag(self):
        self.eq('foo.bar.ba z', s_chop.tag('#foo  .bar.  BA Z'))

    def test_chop_hexstr(self):
        testvectors = [
            ('0C', '0c'),
            ('10', '10'),
            ('0xffff', 'ffff'),
            ('0x0001', '0001'),
            ('C', s_exc.BadTypeValu),
            ('0xfff', s_exc.BadTypeValu),
            ('10001', s_exc.BadTypeValu),
            ('', s_exc.BadTypeValu),
            ('0x', s_exc.BadTypeValu),
            ('newp', s_exc.BadTypeValu)
        ]

        for v, e in testvectors:
            if isinstance(e, str):
                self.eq(s_chop.hexstr(v), e)
            else:
                self.raises(e, s_chop.hexstr, v)

    def test_chop_onespace(self):
        tvs = [
            ('asdfasdf  asdfasdf ', 'asdfasdf asdfasdf'),
            ('asdfasdf ', 'asdfasdf'),
            ('asdf', 'asdf'),
            ('  asdfasdf  ', 'asdfasdf'),
            (' asdf  asdf    asdf \t \t asdf asdf   ', 'asdf asdf asdf asdf asdf'),
            (' ', ''),
            ('foo   bar baz', 'foo bar baz'),
            ('\t \t asdf   asdf   ', 'asdf asdf'),
            ('\n\t asdf  \n asdf   ', 'asdf asdf'),
        ]
        for iv, ev in tvs:
            rv = s_chop.onespace(iv)
            self.eq(rv, ev)
            # No leading space is left after onespace is applied
            self.eq(ev, ev.lstrip())

    def test_chop_printables(self):
        tvs = [
            ('hehe haha', 'hehe haha'),
            ('hehe\u200bhaha\u200b ', 'hehehaha ')
        ]
        for iv, ev in tvs:
            rv = s_chop.printables(iv)
            self.eq(rv, ev)

    def test_chop_stormstring(self):
        tvs = [
            ('', ''),  # no change
            ('beep', 'beep'),  # no change
            ('''be'ep''', '''be'ep'''),  # no change
            ('beep"', 'beep\\"'),  # Simple case
            ('be"ep', 'be\\"ep'),  # Simple case
            ('"', '\\"'),
            ('""', '\\"\\"'),
            ('\\"', '\\\\\\"'),
            ('"\\""', '\\"\\\\\\"\\"'),
            ('\\', '\\\\'),
            ('be\\"ep', 'be\\\\\\"ep'),
        ]
        for tv, ev in tvs:
            gv = s_chop.stormstring(tv)
            self.eq(gv, ev)

    def test_chop_validatetagmatch(self):
        self.raises(s_exc.BadTag, s_chop.validateTagMatch, ' foo')
        self.raises(s_exc.BadTag, s_chop.validateTagMatch, 'foo&bar')
        self.raises(s_exc.BadTag, s_chop.validateTagMatch, 'foo..bar')
        self.none(s_chop.validateTagMatch('foo.*.bar'))
        self.none(s_chop.validateTagMatch('**foo.*.bar'))

    def test_chop_dashes(self):
        self.eq('a-b-c-d--e',
                s_chop.replaceUnicodeDashes('a\u2011b\u2012c\u2013d-\u2014e'))
        self.eq('a-b-c', s_chop.replaceUnicodeDashes('a-b-c'))
        self.eq('asdf', s_chop.replaceUnicodeDashes('asdf'))

    def test_chop_cvss(self):
        # Just basic tests here to mop up coverage, full coverage tests are in
        # test_lib_stormlib_infosec.py
        vect = '(AV:N/AC:M/Au:N/C:C/I:C/A:C/RC:ND/CR:ND/AR:ND)'
        self.eq('AV:N/AC:M/Au:N/C:C/I:C/A:C', s_chop.cvss2_normalize(vect))

        vect = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H/RL:X/CR:X/IR:X/AR:X'
        self.eq('AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H', s_chop.cvss3x_normalize(vect))

        vdict = s_chop.cvss_validate(vect, s_cvss.cvss3_0)
        self.eq('AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H', s_chop.cvss_normalize(vdict, s_cvss.cvss3_0))

        vect = 'CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H/RL:X/CR:X/IR:X/AR:X'
        self.eq('AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H', s_chop.cvss3x_normalize(vect))

        vdict = s_chop.cvss_validate(vect, s_cvss.cvss3_1)
        self.eq('AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:H', s_chop.cvss_normalize(vdict, s_cvss.cvss3_1))

    def test_chop_uncnorm(self):
        unc = s_chop.uncnorm('\\\\server\\share\\path\\filename.txt')
        self.eq(unc, 'smb://server/share/path/filename.txt')

        unc = s_chop.uncnorm('\\\\server@SSL\\share\\path\\filename.txt')
        self.eq(unc, 'https://server/share/path/filename.txt')

        unc = s_chop.uncnorm('\\\\server@SSL@1234\\share\\path\\filename.txt')
        self.eq(unc, 'https://server:1234/share/path/filename.txt')

        unc = s_chop.uncnorm('\\\\1-2-3-4-5-6-7-8.ipv6-literal.net@SSL@1234\\share\\path\\filename.txt')
        self.eq(unc, 'https://[1:2:3:4:5:6:7:8]:1234/share/path/filename.txt')

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('foo')
        self.eq('Invalid UNC path: Does not start with \\\\.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server')
        self.eq('Invalid UNC path: Host name and share name are required.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server\\')
        self.eq('Invalid UNC path: Share name must be 1-80 characters.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server\\' + ('A' * 81))
        self.eq('Invalid UNC path: Share name must be 1-80 characters.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server\\share\\' + ('A' * 256) + '\\filename.txt')
        self.eq('Invalid UNC path: Path component longer than 255 characters.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server\\share\\' + ('A' * 256))
        self.eq('Invalid UNC path: Filename longer than 255 characters.', exc.exception.get('mesg'))

        with self.raises(s_exc.BadTypeValu) as exc:
            s_chop.uncnorm('\\\\server@asdf\\share\\')
        self.eq('Invalid UNC path: Invalid port.', exc.exception.get('mesg'))
