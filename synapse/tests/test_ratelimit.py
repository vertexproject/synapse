import synapse.lib.ratelimit as s_ratelimit

from synapse.tests.common import *

class RateLimitTest(SynTest):

    def test_ratelimit_allow(self):
        rlim = s_ratelimit.RateLimit( 3, 0.2 )

        self.true( rlim.allows() )
        self.true( rlim.allows() )
        self.true( rlim.allows() )

        self.false( rlim.allows() )

        time.sleep(0.1)

        self.true( rlim.allows() )
