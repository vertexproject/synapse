import synapse.exc as s_exc

import synapse.lib.auth as s_auth

import synapse.tests.utils as s_t_utils

class AuthTest(s_t_utils.SynTest):

    async def test_auth_basics(self):

        with self.getTestDir() as dirn:

            async with await s_auth.Auth.anit(dirn) as auth:

                user = auth.addUser('hatguy')
                user.setPasswd('secretsauce')

                self.raises(s_exc.DupRoleName, auth.addRole, 'hatguy')

                self.false(user.tryPasswd(None))
                self.true(user.tryPasswd('secretsauce'))
                self.false(user.tryPasswd('forthelulz'))

                user.addRule((True, ('foo', 'bar')))

                self.true(user.allowed(('foo', 'bar')))
                self.true(user.tryPasswd('secretsauce'))

                user.setLocked(True)

                self.false(user.allowed(('foo', 'bar')))
                self.false(user.tryPasswd('secretsauce'))

                user.setLocked(False)

                self.true(user.allowed(('foo', 'bar')))
                self.true(user.tryPasswd('secretsauce'))

                root = auth.addUser('root')

                self.false(root.admin)
                self.false(root.allowed(('fake', 'perm')))

                root.setAdmin(True)
                self.true(root.allowed(('fake', 'perm')))

                self.true(user.allowed(('foo', 'bar')))
                self.false(user.allowed(('foo', )))
                self.false(user.allowed(('foo', 'baz')))

                role = auth.addRole('ninja')
                self.raises(s_exc.DupUserName, auth.addUser, 'ninja')

                role.addRule((True, ('baz',)))
                role.addRule((False, ('baz', 'faz')))

                self.true(role.allowed(('baz',)))
                self.true(role.allowed(('baz', 'bar')))
                self.false(role.allowed(('baz', 'faz')))

                ############################################
                self.false(user.allowed(('baz',)))
                self.false(user.allowed(('baz', 'faz')))
                self.false(user.allowed(('baz', 'bar')))

                user.addRole('ninja')

                self.true(user.allowed(('baz',)))
                self.true(user.allowed(('baz', 'bar')))
                self.false(user.allowed(('baz', 'faz')))

                user.delRole('ninja')

                self.false(user.allowed(('baz',)))
                self.false(user.allowed(('baz', 'faz')))
                self.false(user.allowed(('baz', 'bar')))
                ############################################

                self.raises(s_exc.NoSuchRole, user.addRole, 'fake')
                self.raises(s_exc.NoSuchUser, auth.delUser, 'fake')
                self.raises(s_exc.DupUserName, auth.addUser, 'hatguy')
                self.raises(s_exc.DupRoleName, auth.addRole, 'ninja')

            async with await s_auth.Auth.anit(dirn) as auth:

                user = auth.users.get('hatguy')
                self.nn(user.shadow)

                root = auth.users.get('root')
                self.true(root.admin)

                self.true(user.allowed(('foo', 'bar')))
                self.false(user.allowed(('foo', )))
                self.false(user.allowed(('foo', 'baz')))

                self.false(user.allowed(('baz',)))
                self.false(user.allowed(('baz', 'faz')))
                self.false(user.allowed(('baz', 'bar')))
