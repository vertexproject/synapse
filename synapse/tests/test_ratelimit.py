import synapse.lib.ratelimit as s_ratelimit

from synapse.tests.common import *

class RateLimitTest(SynTest):

    def test_ratelimit_allow(self):
        rlim = s_ratelimit.RateLimit( 3, 0.2 )

        self.assertTrue( rlim.allows() )
        self.assertTrue( rlim.allows() )
        self.assertTrue( rlim.allows() )

        self.assertFalse( rlim.allows() )

        time.sleep(0.1)

        self.assertTrue( rlim.allows() )
