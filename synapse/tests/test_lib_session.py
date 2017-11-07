import unittest

import synapse.cortex as s_cortex
import synapse.lib.session as s_session

from synapse.tests.common import *

class SessTest(SynTest):

    def test_lib_session_cura(self):

        with s_session.Curator() as cura:

            sess = cura.get()
            sess.set('foo', 'bar')

            self.eq(sess.get('foo'), 'bar')
            self.none(sess.get('baz'))

            # fake out a maint loop
            sess.tick = 1
            cura._curaMainLoop()
            self.true(sess.isfini)

            # get a new session
            sess = cura.get()
