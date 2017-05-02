import synapse.cortex as s_cortex

from synapse.tests.common import *

class StormTest(SynTest):

    def test_storm_cmpr_norm(self):
        
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a','woot.com/1.2.3.4')
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4"')), 1 )
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4" -:ipv4="1.2.3.4"')), 0 )
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4" +:ipv4="1.2.3.4"')), 1 )
