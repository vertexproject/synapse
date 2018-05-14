import synapse.exc as s_exc
import synapse.lib.chop as s_chop

import synapse.tests.common as s_test

class ChopTest(s_test.SynTest):

    def test_chop_digits(self):
        self.eq(s_chop.digits('a1b2c3'), '123')

    def test_chop_tags(self):
        tags = s_chop.tags('foo.bar.baz')
        self.eq(tags, ('foo', 'foo.bar', 'foo.bar.baz'))

    def test_chop_onespace(self):
        self.eq('foo bar baz', s_chop.onespace('foo   bar baz'))

    def test_chop_tag(self):
        self.eq('foo.bar.ba z', s_chop.tag('#foo  .bar.  BA Z'))

    def test_chop_intrange(self):
        self.eq(s_chop.intrange('20:30'), (20, 30))

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
