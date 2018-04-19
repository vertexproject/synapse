import lmdb
from synapse.tests.common import *

import synapse.lib.auth as s_auth

class AuthTest(SynTest):

    def test_auth_rules(self):

        rules = (
            (True, ('foo:bar', {'baz': 'faz'})),
            (False, ('foo:bar', {'baz': 'woot*'})),

            (True, ('hehe:*', {})),
        )

        rulz = s_auth.Rules(rules)

        self.true(rulz.allow(('hehe:ha', {})))
        self.true(rulz.allow(('foo:bar', {'baz': 'faz'})))

        self.false(rulz.allow(('foo:bar', {'baz': 'wootwoot'})))
        self.false(rulz.allow(('newp:newp', {})))

    def test_auth_runas(self):
        self.eq(s_auth.whoami(), 'root@localhost')
        with s_auth.runas('visi@vertex.link'):
            self.eq(s_auth.whoami(), 'visi@vertex.link')
        self.eq(s_auth.whoami(), 'root@localhost')

    def test_auth_tagtree(self):

        tree = s_auth.TagTree()

        tree.add('foo.bar.baz')

        self.false(tree.get('foo'))
        self.false(tree.get('foo.bar'))

        self.true(tree.get('foo.bar.baz'))
        self.true(tree.get('foo.bar.baz.faz'))

        tree.add('foo')

        self.true(tree.get('foo'))
        self.true(tree.get('foo.bar'))

    def test_auth_rbac(self):

        with self.getTestDir() as dirn:

            with s_auth.Auth(dirn) as auth:

                # Ensure our default lmdb size is correct
                self.eq(auth.getConfOpt('lmdb:mapsize'),
                        s_const.gigabyte)

                self.none(auth.users.get('visi@vertex.link'))
                self.none(auth.roles.get('ninjas'))

                self.nn(auth.addUser('root@vertex.link'))
                self.nn(auth.addUser('visi@vertex.link'))
                self.nn(auth.addRole('ninjas'))

                self.true(auth.addUser('delme@vertex.link'))
                self.true(auth.addRole('delmes'))

                udel = auth.users.get('delme@vertex.link')  # type: s_auth.User
                rdel = auth.roles.get('delmes')  # type: s_auth.Role

                self.true(udel.addRole('delmes'))
                self.nn(udel.roles.get('delmes'))

                self.true(udel.delRole('delmes'))
                self.none(udel.roles.get('delmes'))

                self.true(udel.addRole('delmes'))
                self.nn(udel.roles.get('delmes'))

                self.true(auth.delRole('delmes'))
                self.none(udel.roles.get('delmes'))
                self.raises(NoSuchRole, auth.delRole, 'delmes')

                self.true(auth.delUser('delme@vertex.link'))

                self.raises(s_exc.NoSuchUser, auth.delUser, 'delme@vertex.link')
                self.raises(s_exc.DupUserName, auth.addUser, 'visi@vertex.link')
                self.raises(s_exc.DupRoleName, auth.addRole, 'ninjas')

                root = auth.users.get('root@vertex.link')  # type: s_auth.User
                self.nn(root)

                visi = auth.users.get('visi@vertex.link')  # type: s_auth.User
                self.nn(visi)

                ninj = auth.roles.get('ninjas')  # type: s_auth.Role
                self.nn(ninj)

                self.false(visi.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(visi.allowed(('node:del', {'form': 'inet:ipv4'})))
                self.false(visi.allowed(('node:prop:set', {'form': 'inet:ipv4', 'prop': 'cc'})))

                self.false(visi.allowed(('node:tag:add', {'tag': 'hehe.haha'})))
                self.false(visi.allowed(('node:tag:del', {'tag': 'hehe.haha'})))

                self.true(visi.addRule(('node:add', {'form': 'inet:ipv4'})))
                visi.addRule(('node:del', {'form': 'inet:ipv4'}))
                visi.addRule(('node:prop:set', {'form': 'inet:ipv4', 'prop': 'cc'}))
                visi.addRule(('node:tag:add', {'tag': 'foo.bar'}))
                visi.addRule(('node:tag:del', {'tag': 'baz.faz'}))

                root.setAdmin(True)
                self.true(root.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(root.allowed(('node:add', {'form': 'inet:ipv4'}), elev=False))
                # Setting the admin flag to the same value is a no-op
                root.setAdmin(True)
                # We can twiddle the admin privs
                root.setAdmin(False)
                self.false(root.admin)
                self.false(root.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(root.allowed(('node:add', {'form': 'inet:ipv4'}), elev=False))
                # And setting back to true restores the previous behavior.
                root.setAdmin(True)
                self.true(root.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(root.allowed(('node:add', {'form': 'inet:ipv4'}), elev=False))

                self.true(root.admin)
                self.false(visi.admin)

                ninj.addRule(('node:add', {'form': 'inet:fqdn'}))

                self.true(visi.allowed(('node:tag:add', {'tag': 'foo.bar'})))

                self.true(visi.allowed(('node:tag:add', {'tag': 'foo.bar'})))
                self.true(visi.allowed(('node:tag:del', {'tag': 'baz.faz'})))

                self.true(visi.allowed(('node:tag:add', {'tag': 'foo.bar.yep'})))
                self.true(visi.allowed(('node:tag:del', {'tag': 'baz.faz.yep'})))

                self.false(visi.allowed(('node:tag:add', {'tag': 'hehe.haha'})))
                self.false(visi.allowed(('node:tag:del', {'tag': 'hehe.haha'})))

                self.true(visi.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(ninj.allowed(('node:add', {'form': 'inet:ipv4'})))

                self.true(ninj.allowed(('node:add', {'form': 'inet:fqdn'})))
                self.false(visi.allowed(('node:add', {'form': 'inet:fqdn'})))

                self.true(visi.addRole('ninjas'))
                self.true(visi.allowed(('node:add', {'form': 'inet:fqdn'})))
                self.raises(NoSuchRole, visi.addRole, 'bladerunner')

                self.true(visi.delRole('ninjas'))
                self.false(visi.allowed(('node:add', {'form': 'inet:fqdn'})))
                self.false(visi.delRole('ninjas'))

                visi.addRole('ninjas')

                # Sad path testing
                with self.getLoggerStream('synapse.lib.auth', 'no such rule func') as stream:
                    self.false(visi.addRule(('node:nonexistent', {'form': 'lulz'})))
                    self.true(stream.wait(1))

                with self.getLoggerStream('synapse.lib.auth', 'rule function error') as stream:
                    self.false(visi.addRule(('node:add', ['this', 'will', 'fail'])))
                    self.true(stream.wait(1))

                with self.getLoggerStream('synapse.lib.auth', 'unknown perm') as stream:
                    self.false(visi.allowed(('node:nonexistent', {'form': 'inet:fqdn'})))
                    self.true(stream.wait(1))

                with self.getLoggerStream('synapse.lib.auth', 'AuthBase "may" func error') as stream:
                    self.false(visi.allowed(('node:add', ['this', 'will', 'fail'])))
                    self.true(stream.wait(1))

            with s_auth.Auth(dirn) as auth:  # type: s_auth.Auth

                self.none(auth.users.get('delme@vertex.link'))
                self.none(auth.roles.get('delmes'))

                visi = auth.users.get('visi@vertex.link')  # type: s_auth.User
                self.true(visi.allowed(('node:add', {'form': 'inet:ipv4'})))

                self.nn(visi.roles.get('ninjas'))
                self.true(visi.allowed(('node:add', {'form': 'inet:fqdn'})))

                root = auth.users.get('root@vertex.link')  # type: s_auth.User
                self.true(root.admin)

                # These are destructive tests
                erule = ('node:add', {'form': 'inet:ipv4'})
                visi.delRule(erule)
                self.false(visi.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.raises(s_exc.NoSuchRule, visi.delRule, erule)
