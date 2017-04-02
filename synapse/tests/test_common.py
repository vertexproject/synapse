from synapse.tests.common import *

class CommonTest(SynTest):

    def test_common_vertup(self):
        self.assertEqual( vertup('1.3.30'), (1,3,30) )
        self.assertTrue( vertup('30.40.50') > (9,0) )

    def test_common_genfile(self):
        with self.getTestDir() as testdir:
            fd = genfile(testdir,'woot','foo.bin')
            fd.close()

    def test_common_guid(self):
        iden0 = guid()
        iden1 = guid('foo bar baz')
        iden2 = guid('foo bar baz')
        self.ne(iden0,iden1)
        self.eq(iden1,iden2)
