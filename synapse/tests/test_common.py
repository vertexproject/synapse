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
