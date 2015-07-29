import os
import unittest

from binascii import hexlify

import synapse
import synapse.mindmeld as s_mindmeld

syndir = os.path.dirname( synapse.__file__ )

class MindMeldTests(unittest.TestCase):

    def test_mindmeld_loader(self):
        meld = s_mindmeld.MindMeld()
        meld.addPySource('hehehahahoho','x = 30')

        meldinfo = meld.getMeldDict()
        s_mindmeld.loadMindMeld(meldinfo)

        import hehehahahoho
        self.assertEqual( hehehahahoho.x, 30 )

    def test_mindmeld_pkgwalk(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyPath(syndir)

        modinfo = meld.getMeldMod('synapse.tests.test_mindmeld')
        self.assertIsNotNone( modinfo )

    def test_mindmeld_nosuch(self):
        meld = s_mindmeld.MindMeld()
        self.assertRaises( s_mindmeld.NoSuchPath, meld.addPyPath, '/newp')
