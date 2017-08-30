from synapse.tests.common import *

class CommonTest(SynTest):

    def test_common_vertup(self):
        self.eq(vertup('1.3.30'), (1, 3, 30))
        self.true(vertup('30.40.50') > (9, 0))

    def test_common_genfile(self):
        with self.getTestDir() as testdir:
            fd = genfile(testdir, 'woot', 'foo.bin')
            fd.close()

    def test_common_intify(self):
        self.eq(intify(20), 20)
        self.eq(intify("20"), 20)
        self.none(intify(None))
        self.none(intify("woot"))

    def test_common_guid(self):
        iden0 = guid()
        iden1 = guid('foo bar baz')
        iden2 = guid('foo bar baz')
        self.ne(iden0, iden1)
        self.eq(iden1, iden2)

class CompatTest(SynTest):

    def test_compat_canstor(self):
        self.true(0xf0f0)
        self.true(0xf0f0f0f0f0f0)
        self.true(canstor('asdf'))
        self.true(canstor(u'asdf'))

        self.false(canstor(True))
        self.false(canstor(('asdf',)))
        self.false(canstor(['asdf', ]))
        self.false(canstor({'asdf': True}))

    def test_compat_quote(self):
        self.eq(url_quote('asdf'), 'asdf')
        self.eq(url_quote('asdf&foo'), 'asdf%26foo')
        self.eq(url_quote('asdf foo'), 'asdf%20foo')

    def test_compat_quote_plus(self):
        self.eq(url_quote_plus('asdf'), 'asdf')
        self.eq(url_quote_plus('asdf&foo'), 'asdf%26foo')
        self.eq(url_quote_plus('asdf foo'), 'asdf+foo')
