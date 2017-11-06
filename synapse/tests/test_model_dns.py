import synapse.cortex as s_cortex

from synapse.tests.common import *

class DnsModelTest(SynTest):

    def test_model_dns_a(self):
        with self.getRamCore() as core:

            t0 = core.formTufoByProp('inet:dns:a', 'WOOT.com/1.2.3.4')
            self.eq(t0[1].get('inet:dns:a'), 'woot.com/1.2.3.4')
            self.eq(t0[1].get('inet:dns:a:fqdn'), 'woot.com')
            self.eq(t0[1].get('inet:dns:a:ipv4'), 0x01020304)

            t1 = core.formTufoByProp('inet:dns:a', ('foo.com', 0x05060708))
            self.eq(t1[1].get('inet:dns:a'), 'foo.com/5.6.7.8')
            self.eq(t1[1].get('inet:dns:a:fqdn'), 'foo.com')
            self.eq(t1[1].get('inet:dns:a:ipv4'), 0x05060708)

            t2 = core.formTufoByProp('inet:dns:a', 'www.\u0915\u0949\u092e/1.2.3.4')
            self.eq(t2[1].get('inet:dns:a'), 'www.\u0915\u0949\u092e/1.2.3.4')
            self.eq(t2[1].get('inet:dns:a:fqdn'), 'www.xn--11b4c3d')
            self.eq(t2[1].get('inet:dns:a:ipv4'), 0x01020304)

    def test_model_dns_aaaa(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:dns:aaaa', 'WOOT.com/FF::56')
            self.eq(t0[1].get('inet:dns:aaaa'), 'woot.com/ff::56')
            self.eq(t0[1].get('inet:dns:aaaa:fqdn'), 'woot.com')
            self.eq(t0[1].get('inet:dns:aaaa:ipv6'), 'ff::56')

    def test_model_dns_ns(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:dns:ns', 'WOOT.com/ns.yermom.com')
            self.eq(t0[1].get('inet:dns:ns'), 'woot.com/ns.yermom.com')
            self.eq(t0[1].get('inet:dns:ns:zone'), 'woot.com')
            self.eq(t0[1].get('inet:dns:ns:ns'), 'ns.yermom.com')

    def test_model_dns_rev(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:dns:rev', '1.002.3.4/WOOT.com')
            self.eq(t0[1].get('inet:dns:rev'), '1.2.3.4/woot.com')
            self.eq(t0[1].get('inet:dns:rev:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:dns:rev:fqdn'), 'woot.com')

    def test_model_dns_look(self):
        with self.getRamCore() as core:

            tick = now()

            t0 = core.formTufoByProp('inet:dns:look', '*', a='WOOT.com/1.002.3.4', time=tick)
            self.eq(t0[1].get('inet:dns:look:time'), tick)
            self.eq(t0[1].get('inet:dns:look:a'), 'woot.com/1.2.3.4')
            self.eq(t0[1].get('inet:dns:look:a:fqdn'), 'woot.com')
            self.eq(t0[1].get('inet:dns:look:a:ipv4'), 0x01020304)

            t0 = core.formTufoByProp('inet:dns:look', '*', ns='WOOT.com/ns.yermom.com', time=tick)
            self.eq(t0[1].get('inet:dns:look:time'), tick)
            self.eq(t0[1].get('inet:dns:look:ns'), 'woot.com/ns.yermom.com')
            self.eq(t0[1].get('inet:dns:look:ns:ns'), 'ns.yermom.com')
            self.eq(t0[1].get('inet:dns:look:ns:zone'), 'woot.com')

            t0 = core.formTufoByProp('inet:dns:look', '*', rev='1.2.3.4/WOOT.com', time=tick)
            self.eq(t0[1].get('inet:dns:look:time'), tick)
            self.eq(t0[1].get('inet:dns:look:rev'), '1.2.3.4/woot.com')
            self.eq(t0[1].get('inet:dns:look:rev:fqdn'), 'woot.com')
            self.eq(t0[1].get('inet:dns:look:rev:ipv4'), 0x01020304)

            t0 = core.formTufoByProp('inet:dns:look', '*', aaaa='WOOT.com/FF::56', time=tick)
            self.eq(t0[1].get('inet:dns:look:time'), tick)
            self.eq(t0[1].get('inet:dns:look:aaaa'), 'woot.com/ff::56')
            self.eq(t0[1].get('inet:dns:look:aaaa:fqdn'), 'woot.com')
            self.eq(t0[1].get('inet:dns:look:aaaa:ipv6'), 'ff::56')

    def test_model_dns_rev6(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:dns:rev6', '2607:f8b0:4004:809::200e/vertex.link')
            self.eq(node[1].get('inet:dns:rev6:fqdn'), 'vertex.link')
            self.eq(node[1].get('inet:dns:rev6:ipv6'), '2607:f8b0:4004:809::200e')
