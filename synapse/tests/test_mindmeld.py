import os
import unittest

from binascii import hexlify

import synapse
import synapse.mindmeld as s_mindmeld

from synapse.tests.common import *

syndir = os.path.dirname( synapse.__file__ )

def foobar(x, y=10):
    return x + y

class Foo:
    def bar(self, x, y):
        return x + y

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

        moddef = meld.getMeldMod('synapse.tests.test_mindmeld')
        self.assertIsNotNone( moddef )

    def test_mindmeld_nosuch(self):
        meld = s_mindmeld.MindMeld()
        self.assertRaises( NoSuchPath, meld.addPyPath, '/newp')

    def test_mindmeld_base64(self):
        meld = s_mindmeld.MindMeld()
        meld.addPySource('hehehahaaaa','x = 40')

        s_mindmeld.loadMeldBase64( meld.getMeldBase64() )

        import hehehahaaaa
        self.assertEqual( hehehahaaaa.x, 40 )

    def test_mindmeld_badsrc(self):
        meld = s_mindmeld.MindMeld()
        badsrc = 'some --<<== shit'
        self.assertRaises( s_mindmeld.BadPySource, meld.addPySource, 'woot', badsrc)

    def test_mindmeld_call(self):
        foo = Foo()
        meld = s_mindmeld.getCallMeld( foo.bar )
        self.assertIsNone( meld.getMeldMod('newp') )
        self.assertIsNone( meld.getMeldMod('binascii') )
        self.assertIsNotNone( meld.getMeldMod('synapse') )
        self.assertIsNotNone( meld.getMeldMod('synapse.mindmeld') )

    def test_mindmeld_pycall(self):

        meld = s_mindmeld.MindMeld()
        meld.addPyCall( foobar )

        self.assertIsNone( meld.getMeldMod('newp') )
        self.assertIsNone( meld.getMeldMod('binascii') )
        self.assertIsNotNone( meld.getMeldMod('synapse') )
        self.assertIsNotNone( meld.getMeldMod('synapse.mindmeld') )

    def test_mindmeld_addpymod(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyMod('synapse')

        self.assertIsNone( meld.getMeldMod('newp') )
        self.assertIsNone( meld.getMeldMod('binascii') )
        self.assertIsNotNone( meld.getMeldMod('synapse') )
        self.assertIsNotNone( meld.getMeldMod('synapse.mindmeld') )
