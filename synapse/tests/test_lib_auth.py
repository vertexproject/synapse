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

                self.none(auth.users.get('visi@vertex.link'))
                self.none(auth.roles.get('ninjas'))

                auth.addUser('root@vertex.link')
                auth.addUser('visi@vertex.link')
                auth.addRole('ninjas')

                auth.addUser('delme@vertex.link')
                auth.addRole('delmes')

                udel = auth.users.get('delme@vertex.link')
                rdel = auth.roles.get('delmes')

                udel.addRole('delmes')
                self.nn(udel.roles.get('delmes'))

                udel.delRole('delmes')
                self.none(udel.roles.get('delmes'))

                udel.addRole('delmes')
                self.nn(udel.roles.get('delmes'))

                auth.delRole('delmes')
                self.none(udel.roles.get('delmes'))

                auth.delUser('delme@vertex.link')

                self.raises(s_exc.DupUserName, auth.addUser, 'visi@vertex.link')
                self.raises(s_exc.DupRoleName, auth.addRole, 'ninjas')

                root = auth.users.get('root@vertex.link')
                self.nn(root)

                visi = auth.users.get('visi@vertex.link')
                self.nn(visi)

                ninj = auth.roles.get('ninjas')
                self.nn(ninj)

                self.false(visi.allowed(('node:add', {'form': 'inet:ipv4'})))
                self.false(visi.allowed(('node:del', {'form': 'inet:ipv4'})))
                self.false(visi.allowed(('node:prop:set', {'form': 'inet:ipv4', 'prop': 'cc'})))

                self.false(visi.allowed(('node:tag:add', {'tag': 'hehe.haha'})))
                self.false(visi.allowed(('node:tag:del', {'tag': 'hehe.haha'})))

                visi.addRule(('node:add', {'form': 'inet:ipv4'}))
                visi.addRule(('node:del', {'form': 'inet:ipv4'}))
                visi.addRule(('node:prop:set', {'form': 'inet:ipv4', 'prop': 'cc'}))
                visi.addRule(('node:tag:add', {'tag': 'foo.bar'}))
                visi.addRule(('node:tag:del', {'tag': 'baz.faz'}))

                root.setAdmin(True)

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

                visi.addRole('ninjas')
                self.true(visi.allowed(('node:add', {'form': 'inet:fqdn'})))

                visi.delRole('ninjas')
                self.false(visi.allowed(('node:add', {'form': 'inet:fqdn'})))

                visi.addRole('ninjas')

            with s_auth.Auth(dirn) as auth:

                self.none(auth.users.get('delme@vertex.link'))
                self.none(auth.roles.get('delmes'))

                visi = auth.users.get('visi@vertex.link')
                self.true(visi.allowed(('node:add', {'form': 'inet:ipv4'})))

                self.nn(visi.roles.get('ninjas'))
                self.true(visi.allowed(('node:add', {'form': 'inet:fqdn'})))

                root = auth.users.get('root@vertex.link')
                self.true(root.admin)
