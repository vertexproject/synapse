import synapse.common as s_common
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

            props = {'a': 'WOOT.com/1.002.3.4', 'rcode': 0, 'time': tick, 'ipv4': '5.5.5.5', 'udp4': '8.8.8.8:80'}
            t0 = core.formTufoByProp('inet:dns:look', '*', **props)
            self.eq(t0[1].get('inet:dns:look:rcode'), 0)
            self.eq(t0[1].get('inet:dns:look:ipv4'), 0x05050505)
            self.eq(t0[1].get('inet:dns:look:udp4'), 0x080808080050)
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

            # test host execution lookup record
            exe = s_common.guid()
            host = s_common.guid()
            proc = s_common.guid()

            valu = {'host': host, 'proc': proc, 'exe': exe, 'a:fqdn': 'blah.com'}
            t0 = core.formTufoByProp('inet:dns:look', valu)
            self.eq(t0[1].get('inet:dns:look:exe'), exe)
            self.eq(t0[1].get('inet:dns:look:host'), host)
            self.eq(t0[1].get('inet:dns:look:proc'), proc)
            self.eq(t0[1].get('inet:dns:look:a:fqdn'), 'blah.com')

            self.nn(core.getTufoByProp('file:bytes', exe))
            self.nn(core.getTufoByProp('it:host', host))
            self.nn(core.getTufoByProp('it:exec:proc', proc))

            # Ensure tcp4/udp4 values are broken out
            valu = {'time': tick,
                    'a': 'vertex.link/8.8.8.8',
                    'tcp4': '1.2.3.6:53',
                    'udp4': '1.2.3.7:8080'}
            t0 = core.formTufoByProp('inet:dns:look', valu)
            self.eq(t0[1].get('inet:dns:look:a:fqdn'), 'vertex.link')
            self.eq(t0[1].get('inet:dns:look:a:ipv4'), 0x08080808)
            self.eq(core.getTypeRepr('inet:tcp4', t0[1].get('inet:dns:look:tcp4')), '1.2.3.6:53')
            self.eq(core.getTypeRepr('inet:udp4', t0[1].get('inet:dns:look:udp4')), '1.2.3.7:8080')
            # Ensure the tertiary props for tcp4/udp4 are broken out
            self.eq(t0[1].get('inet:dns:look:tcp4:ipv4'), 0x01020306)
            self.eq(t0[1].get('inet:dns:look:tcp4:port'), 53)
            self.eq(t0[1].get('inet:dns:look:udp4:ipv4'), 0x01020307)
            self.eq(t0[1].get('inet:dns:look:udp4:port'), 8080)
            # Ensure our autoadds are made
            self.nn(core.getTufoByProp('inet:tcp4', '1.2.3.6:53'))
            self.nn(core.getTufoByProp('inet:udp4', '1.2.3.7:8080'))

    def test_model_dns_rev6(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:dns:rev6', '2607:f8b0:4004:809::200e/vertex.link')
            self.eq(node[1].get('inet:dns:rev6:fqdn'), 'vertex.link')
            self.eq(node[1].get('inet:dns:rev6:ipv6'), '2607:f8b0:4004:809::200e')

    def test_model_dns_req(self):

        with self.getRamCore() as core:

            now = s_common.now()
            node = core.formTufoByProp('inet:dns:req', ('1.2.3.4', 'VERTEX.link', 'A'), **{'seen:min': now, 'seen:max': now})
            self.eq(node[1].get('inet:dns:req:type'), 'a')
            self.eq(node[1].get('inet:dns:req:client'), 'tcp://1.2.3.4')
            self.eq(node[1].get('inet:dns:req:client:ipv4'), 0x01020304)
            self.eq(node[1].get('inet:dns:req:fqdn'), 'vertex.link')
            self.eq(node[1].get('inet:dns:req:seen:min'), now)
            self.eq(node[1].get('inet:dns:req:seen:max'), now)

            newnow = s_common.now() + 100
            node = core.setTufoProps(node, **{'seen:min': newnow, 'seen:max': newnow})
            self.eq(node[1].get('inet:dns:req:seen:min'), now)
            self.eq(node[1].get('inet:dns:req:seen:max'), newnow)
