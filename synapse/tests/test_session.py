import unittest

import synapse.session as s_session

class SessTest(unittest.TestCase):

    def test_sess_current(self):
        boss = s_session.SessBoss()

        args = {'sess:woot':10}
        sess = boss.initSess(**args)

        with boss.getSessWith(sess[0]):
            self.assertEqual( s_session.current()[0], sess[0] )

            self.assertEqual( s_session.get('sess:woot'), 10 )

            self.assertTrue( s_session.put('sess:haha',30 ))
            self.assertEqual( s_session.get('sess:haha'), 30 )

