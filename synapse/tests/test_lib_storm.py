import synapse.cortex as s_cortex

from synapse.tests.common import *

class StormTest(SynTest):

    def test_storm_cmpr_norm(self):
        
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a','woot.com/1.2.3.4')
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4"')), 1 )
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4" -:ipv4="1.2.3.4"')), 0 )
            self.eq( len( core.eval('inet:dns:a:ipv4="1.2.3.4" +:ipv4="1.2.3.4"')), 1 )

    def test_storm_pivot(self):

        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('inet:dns:a','woot.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a','vertex.vis/5.6.7.8')
            core.formTufoByProp('inet:dns:a','vertex.link/5.6.7.8')

            node = core.eval('inet:ipv4="1.2.3.4" inet:ipv4->inet:dns:a:ipv4')[0]

            self.nn( node )
            self.eq( node[1].get('inet:dns:a'), 'woot.com/1.2.3.4' )

            node = core.eval('inet:dns:a="woot.com/1.2.3.4" :ipv4->inet:ipv4')[0]

            self.nn( node )
            self.eq( node[1].get('inet:ipv4'), 0x01020304 )

            node = core.eval('inet:fqdn="woot.com" ->inet:dns:a:fqdn')[0]

            self.nn( node )
            self.eq( node[1].get('inet:dns:a'), 'woot.com/1.2.3.4' )

            self.eq( len(core.eval('inet:dns:a:ipv4="5.6.7.8" :fqdn->inet:fqdn')), 2 )

            self.eq( len(core.eval('inet:ipv4="5.6.7.8" -> inet:dns:a:ipv4')), 2 )
            self.eq( len(core.eval('inet:ipv4="5.6.7.8" inet:ipv4->inet:dns:a:ipv4')), 2 )
