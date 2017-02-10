import synapse.cortex as s_cortex

from synapse.tests.common import *

class DnsModelTest(SynTest):

    def test_model_dns_a(self):
        with s_cortex.openurl('ram:///') as core:

            t0 = core.formTufoByProp('inet:dns:a','WOOT.com/1.2.3.4')
            self.eq( t0[1].get('inet:dns:a') ,'woot.com/1.2.3.4')
            self.eq( t0[1].get('inet:dns:a:fqdn'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:a:ipv4'), 0x01020304 )

    def test_model_dns_aaaa(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:dns:aaaa','WOOT.com/FF::56')
            self.eq( t0[1].get('inet:dns:aaaa') ,'woot.com/ff::56')
            self.eq( t0[1].get('inet:dns:aaaa:fqdn'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:aaaa:ipv6'), 'ff::56' )

    def test_model_dns_ns(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:dns:ns','WOOT.com/ns.yermom.com')
            self.eq( t0[1].get('inet:dns:ns') ,'woot.com/ns.yermom.com' )
            self.eq( t0[1].get('inet:dns:ns:zone'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:ns:ns'), 'ns.yermom.com')

    def test_model_dns_rev(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:dns:rev','1.002.3.4/WOOT.com')
            self.eq( t0[1].get('inet:dns:rev') ,'1.2.3.4/woot.com' )
            self.eq( t0[1].get('inet:dns:rev:ipv4'), 0x01020304 )
            self.eq( t0[1].get('inet:dns:rev:fqdn'), 'woot.com' )

    def test_model_dns_look(self):
        with s_cortex.openurl('ram:///') as core:

            t0 = core.addTufoEvent('inet:dns:look', a='WOOT.com/1.002.3.4')
            self.eq( t0[1].get('inet:dns:look:a') ,'woot.com/1.2.3.4')
            self.eq( t0[1].get('inet:dns:look:a:fqdn'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:look:a:ipv4'), 0x01020304 )

            t0 = core.addTufoEvent('inet:dns:look', ns='WOOT.com/ns.yermom.com')
            self.eq( t0[1].get('inet:dns:look:ns') ,'woot.com/ns.yermom.com')
            self.eq( t0[1].get('inet:dns:look:ns:ns'), 'ns.yermom.com')
            self.eq( t0[1].get('inet:dns:look:ns:zone'), 'woot.com' )

            t0 = core.addTufoEvent('inet:dns:look', rev='1.2.3.4/WOOT.com')
            self.eq( t0[1].get('inet:dns:look:rev') ,'1.2.3.4/woot.com')
            self.eq( t0[1].get('inet:dns:look:rev:fqdn'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:look:rev:ipv4'), 0x01020304 )

            t0 = core.addTufoEvent('inet:dns:look', aaaa='WOOT.com/FF::56')
            self.eq( t0[1].get('inet:dns:look:aaaa') ,'woot.com/ff::56')
            self.eq( t0[1].get('inet:dns:look:aaaa:fqdn'), 'woot.com' )
            self.eq( t0[1].get('inet:dns:look:aaaa:ipv6'), 'ff::56' ) 
