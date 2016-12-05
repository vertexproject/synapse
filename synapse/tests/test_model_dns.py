import synapse.cortex as s_cortex

from synapse.tests.common import *

class DnsModelTest(SynTest):

    def test_model_dns_a(self):
        with s_cortex.openurl('ram:///') as core:

            t0 = core.formTufoByProp('dns:a','WOOT.com/1.2.3.4')
            self.eq( t0[1].get('dns:a') ,'woot.com/1.2.3.4')
            self.eq( t0[1].get('dns:a:fqdn'), 'woot.com' )
            self.eq( t0[1].get('dns:a:ipv4'), 0x01020304 )

    def test_model_dns_aaaa(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('dns:aaaa','WOOT.com/FF::56')
            self.eq( t0[1].get('dns:aaaa') ,'woot.com/ff::56')
            self.eq( t0[1].get('dns:aaaa:fqdn'), 'woot.com' )
            self.eq( t0[1].get('dns:aaaa:ipv6'), 'ff::56' )

    def test_model_dns_ns(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('dns:ns','WOOT.com/ns.yermom.com')
            self.eq( t0[1].get('dns:ns') ,'woot.com/ns.yermom.com' )
            self.eq( t0[1].get('dns:ns:zone'), 'woot.com' )
            self.eq( t0[1].get('dns:ns:ns'), 'ns.yermom.com')

    def test_model_dns_rev(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('dns:rev','1.002.3.4/WOOT.com')
            self.eq( t0[1].get('dns:rev') ,'1.2.3.4/woot.com' )
            self.eq( t0[1].get('dns:rev:ipv4'), 0x01020304 )
            self.eq( t0[1].get('dns:rev:fqdn'), 'woot.com' )

    def test_model_dns_look(self):
        with s_cortex.openurl('ram:///') as core:

            t0 = core.addTufoEvent('dns:look', a='WOOT.com/1.002.3.4')
            self.eq( t0[1].get('dns:look:a') ,'woot.com/1.2.3.4')
            self.eq( t0[1].get('dns:look:a:fqdn'), 'woot.com' )
            self.eq( t0[1].get('dns:look:a:ipv4'), 0x01020304 )

            t0 = core.addTufoEvent('dns:look', ns='WOOT.com/ns.yermom.com')
            self.eq( t0[1].get('dns:look:ns') ,'woot.com/ns.yermom.com')
            self.eq( t0[1].get('dns:look:ns:ns'), 'ns.yermom.com')
            self.eq( t0[1].get('dns:look:ns:zone'), 'woot.com' )

            t0 = core.addTufoEvent('dns:look', rev='1.2.3.4/WOOT.com')
            self.eq( t0[1].get('dns:look:rev') ,'1.2.3.4/woot.com')
            self.eq( t0[1].get('dns:look:rev:fqdn'), 'woot.com' )
            self.eq( t0[1].get('dns:look:rev:ipv4'), 0x01020304 )

            t0 = core.addTufoEvent('dns:look', aaaa='WOOT.com/FF::56')
            self.eq( t0[1].get('dns:look:aaaa') ,'woot.com/ff::56')
            self.eq( t0[1].get('dns:look:aaaa:fqdn'), 'woot.com' )
            self.eq( t0[1].get('dns:look:aaaa:ipv6'), 'ff::56' ) 
