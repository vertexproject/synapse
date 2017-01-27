from synapse.tests.common import *

import synapse.lib.env as s_env

class EnvTest(SynTest):

    def test_lib_env(self):

        self.assertIsNotNone( s_env.get('PATH') )

        self.assertIsNone( s_env.get('SYN_FOO_BAR') )

        self.eq( s_env.get('SYN_FOO_BAR', defval='foobar'), 'foobar' )

        s_env.put('SYN_FOO_BAR','foo')

        self.eq( s_env.get('SYN_FOO_BAR'), 'foo')

        with s_env.scope():
            s_env.put('SYN_FOO_BAR','bar')
            self.eq( s_env.get('SYN_FOO_BAR'),'bar')

        self.eq( s_env.get('SYN_FOO_BAR'), 'foo')

