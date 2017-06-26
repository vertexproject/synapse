from synapse.tests.common import *

import synapse.lib.interval as s_interval

class IvalTest(SynTest):

    def test_ival_init(self):
        vals = [ None , 100, 20, None ]
        self.eq( s_interval.fold(*vals), (20,100) )
        self.none( s_interval.fold() )

    def test_ival_parsetime(self):
        ival = s_interval.parsetime('1970-1980')
        self.eq( s_interval.parsetime('1970-1980'), (0,315532800000) )
