import unittest

import synapse.cortex as s_cortex
import synapse.lib.session as s_session

class SessTest(unittest.TestCase):

    def test_sess_current(self):
        core = s_cortex.openurl('ram:///')
        cura = s_session.Curator(core)

        sess = cura.new()
        sess.put('woot',10)

        with sess:

            woot = s_session.current()
            self.assertEqual(sess.sid,woot.sid)
            self.assertEqual( woot.get('woot'), 10 )

            sess.put('haha',30)
            self.assertEqual( sess.get('haha'), 30 )

        cura.fini()
        core.fini()

    def test_sess_fini(self):
        core = s_cortex.openurl('ram:///')
        cura = s_session.Curator(core)

        cura.fini()
        core.fini()
