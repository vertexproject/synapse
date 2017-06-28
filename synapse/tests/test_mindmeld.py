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

class MindMeldTests(SynTest):

    def test_mindmeld_loader(self):
        meld = s_mindmeld.MindMeld()
        meld.addPySource('hehehahahoho','x = 30')

        meldinfo = meld.getMeldDict()
        s_mindmeld.loadMindMeld(meldinfo)

        import hehehahahoho
        self.eq( hehehahahoho.x, 30 )

    def test_mindmeld_pkgwalk(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyPath(syndir)

        moddef = meld.getMeldMod('synapse.tests.test_mindmeld')
        self.nn( moddef )

    def test_mindmeld_nosuch(self):
        meld = s_mindmeld.MindMeld()
        self.raises( NoSuchPath, meld.addPyPath, '/newp')

    def test_mindmeld_base64(self):
        meld = s_mindmeld.MindMeld()
        meld.addPySource('hehehahaaaa','x = 40')

        s_mindmeld.loadMeldBase64( meld.getMeldBase64() )

        import hehehahaaaa
        self.eq( hehehahaaaa.x, 40 )

    def test_mindmeld_badsrc(self):
        meld = s_mindmeld.MindMeld()
        badsrc = 'some --<<== shit'
        self.raises( s_mindmeld.BadPySource, meld.addPySource, 'woot', badsrc)

    def test_mindmeld_call(self):
        foo = Foo()
        meld = s_mindmeld.getCallMeld( foo.bar )
        self.none( meld.getMeldMod('newp') )
        self.none( meld.getMeldMod('binascii') )
        self.nn( meld.getMeldMod('synapse') )
        self.nn( meld.getMeldMod('synapse.mindmeld') )

    def test_mindmeld_pycall(self):

        meld = s_mindmeld.MindMeld()
        meld.addPyCall( foobar )

        self.none( meld.getMeldMod('newp') )
        self.none( meld.getMeldMod('binascii') )
        self.nn( meld.getMeldMod('synapse') )
        self.nn( meld.getMeldMod('synapse.mindmeld') )

    def test_mindmeld_addpymod(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyMod('synapse')

        self.none( meld.getMeldMod('newp') )
        self.none( meld.getMeldMod('binascii') )
        self.nn( meld.getMeldMod('synapse') )
        self.nn( meld.getMeldMod('synapse.mindmeld') )
