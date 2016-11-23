from synapse.tests.common import *

import synapse.compat as s_compat

class CompatTest(SynTest):

    def test_compat_canstor(self):
        self.assertTrue( 0xf0f0 )
        self.assertTrue( 0xf0f0f0f0f0f0 )
        self.assertTrue( s_compat.canstor('asdf') )
        self.assertTrue( s_compat.canstor(u'asdf') )

        self.assertFalse( s_compat.canstor(True ) )
        self.assertFalse( s_compat.canstor(('asdf',)) )
        self.assertFalse( s_compat.canstor(['asdf',]) )
        self.assertFalse( s_compat.canstor({'asdf':True}) )
