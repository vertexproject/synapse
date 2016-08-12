import unittest

import synapse.cortex as s_cortex
import synapse.lib.session as s_session

from synapse.tests.common import *

class SessTest(SynTest):

    def test_sess_current(self):
        core = s_cortex.openurl('ram:///')
        cura = s_session.Curator(core=core)

        sess = cura.new()

        print(repr(sess))
        iden = sess.iden

        sess.put('woot',10, save=True)

        with sess:

            woot = s_session.current()

            self.eq(sess.iden,woot.iden)
            self.eq( woot.get('woot'), 10 )

            sess.put('haha',30)
            self.eq( woot.get('haha'), 30 )

        cura.fini()

        cura = s_session.Curator(core=core)

        sess = cura.get(iden)

        self.eq(sess.get('woot'), 10)
        self.eq(sess.get('haha'), None)

        core.fini()
