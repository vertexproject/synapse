from synapse.tests.common import *

import synapse.lib.interval as s_interval

class IvalTest(SynTest):

    def test_ival_init(self):
        vals = [ None , 100, 20, None ]
        self.eq( s_interval.initIval(*vals), (20,100) )
        self.none( s_interval.initIval() )
