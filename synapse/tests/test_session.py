import unittest

import synapse.session as s_session

class SessTest(unittest.TestCase):

    def test_sess_current(self):
        cura = s_session.Curator()

        sess = cura.getNewSess()
        sess.set('woot',10)

        with sess:

            woot = s_session.current()
            self.assertEqual(sess.sid,woot.sid)
            self.assertEqual( woot.get('woot'), 10 )

            sess.set('haha',30)
            self.assertEqual( sess.get('haha'), 30 )

        cura.fini()

    def test_sess_auth(self):
        cura = s_session.Curator()

        cura.addUserName('visi',root=1)
        cura.addRoleName('root')

        user = cura.getUserByName('visi')
        role = cura.getRoleByName('root')

        self.assertIsNotNone(user)
        self.assertEqual(user[1].get('auth:user'), 'visi')
        self.assertEqual(user[1].get('auth:user:root'), 1)

        self.assertIsNotNone(role)
        self.assertEqual(role[1].get('auth:role'), 'root')

        cura.addAllowRule('visi','hehe')
        name,rule,allow = cura.getUserPerm('visi','hehe')

        self.assertTrue( allow )
        self.assertEqual( name, 'visi' )
        self.assertEqual( rule, 'hehe' )

        cura.addDenyRule('visi','*')

        name,rule,allow = cura.getUserPerm('visi','hehe')
        self.assertFalse( allow )
        self.assertEqual( name, 'visi' )
        self.assertEqual( rule, '*' )

        cura.delUserByName('visi')
        self.assertIsNone( cura.getUserByName('visi') )

        cura.delRoleByName('root')
        self.assertIsNone( cura.getRoleByName('root') )

        cura.fini()

    def test_sess_fini(self):
        cura = s_session.Curator()
        cura.fini()
