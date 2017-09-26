import unittest

import synapse.cortex as s_cortex
import synapse.lib.session as s_session

from synapse.tests.common import *

class SessTest(SynTest):

    def test_sess_current(self):
        core = s_cortex.openurl('ram:///')
        # Since sessions may store wildcard props in syn:sess nodes we
        # have to ensure enforce is disabled in our session cortex
        core.setConfOpt('enforce', 0)

        cura = s_session.Curator(core=core)

        sess = cura.new()

        iden = sess.iden

        sess.put('woot', 10)

        with sess:

            woot = s_session.current()

            self.eq(sess.iden, woot.iden)
            self.eq(woot.get('woot'), 10)

            sess.put('haha', 30, save=False)
            self.eq(woot.get('haha'), 30)

        cura.fini()

        cura = s_session.Curator(core=core)

        sess = cura.get(iden)

        self.eq(sess.get('woot'), 10)
        self.eq(sess.get('haha'), None)

        core.fini()

    def test_sess_log(self):
        cura = s_session.Curator()
        watr = cura.waiter(1, 'sess:log')
        sess = cura.new()
        sess.log(0, "woot")
