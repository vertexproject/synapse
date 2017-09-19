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
