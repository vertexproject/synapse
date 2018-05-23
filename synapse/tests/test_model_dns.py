import synapse.common as s_common

import synapse.tests.common as s_test

class DnsModelTest(s_test.SynTest):
    def test_forms_dns_simple(self):
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                # inet:dns:a
                node = snap.addNode('inet:dns:a', ('hehe.com', '1.2.3.4'))
                self.eq(node.ndef[1], ('hehe.com', 0x01020304))
                self.eq(node.get('fqdn'), 'hehe.com')
                self.eq(node.get('ipv4'), 0x01020304)

                node = snap.addNode('inet:dns:a', ('www.\u0915\u0949\u092e.com', '1.2.3.4'))
                self.eq(node.ndef[1], ('www.xn--11b4c3d.com', 0x01020304))
                self.eq(node.get('fqdn'), 'www.xn--11b4c3d.com')
                self.eq(node.get('ipv4'), 0x01020304)

                # inet:dns:aaaa
                node = snap.addNode('inet:dns:aaaa', ('localhost', '::1'))
                self.eq(node.ndef[1], ('localhost', '::1'))
                self.eq(node.get('fqdn'), 'localhost')
                self.eq(node.get('ipv6'), '::1')

                node = snap.addNode('inet:dns:aaaa', ('hehe.com', '2001:0db8:85a3:0000:0000:8a2e:0370:7334'))
                self.eq(node.ndef[1], ('hehe.com', '2001:db8:85a3::8a2e:370:7334'))
                self.eq(node.get('fqdn'), 'hehe.com')
                self.eq(node.get('ipv6'), '2001:db8:85a3::8a2e:370:7334')

                # inet:dns:rev
                node = snap.addNode('inet:dns:rev', ('1.2.3.4', 'bebe.com'))
                self.eq(node.ndef[1], (0x01020304, 'bebe.com'))
                self.eq(node.get('ipv4'), 0x01020304)
                self.eq(node.get('fqdn'), 'bebe.com')

                # inet:dns:rev6
                node = snap.addNode('inet:dns:rev6', ('FF::56', 'bebe.com'))
                self.eq(node.ndef[1], ('ff::56', 'bebe.com'))
                self.eq(node.get('ipv6'), 'ff::56')
                self.eq(node.get('fqdn'), 'bebe.com')

                # inet:dns:ns
                node = snap.addNode('inet:dns:ns', ('haha.com', 'ns1.haha.com'))
                self.eq(node.ndef[1], ('haha.com', 'ns1.haha.com'))
                self.eq(node.get('zone'), 'haha.com')
                self.eq(node.get('ns'), 'ns1.haha.com')

                # inet:dns:cname
                node = snap.addNode('inet:dns:cname', ('HAHA.vertex.link', 'vertex.link'))
                self.eq(node.ndef[1], ('haha.vertex.link', 'vertex.link'))
                self.eq(node.get('fqdn'), 'haha.vertex.link')
                self.eq(node.get('cname'), 'vertex.link')

                # inet:dns:mx
                node = snap.addNode('inet:dns:mx', ('vertex.link', 'mail.vertex.link'))
                self.eq(node.ndef[1], ('vertex.link', 'mail.vertex.link'))
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('mx'), 'mail.vertex.link')

                # inet:dns:soa
                valu = ('haha.vertex.link', 'ns1.vertex.link', 'pennywise@vertex.link')
                node = snap.addNode('inet:dns:soa', valu)
                self.eq(node.get('fqdn'), 'haha.vertex.link')
                self.eq(node.get('email'), 'pennywise@vertex.link')
                self.eq(node.get('ns'), 'ns1.vertex.link')

                # inet:dns:txt
                node = snap.addNode('inet:dns:txt', ('clowns.vertex.link', 'we all float down here'))
                self.eq(node.ndef[1], ('clowns.vertex.link', 'we all float down here'))
                self.eq(node.get('fqdn'), 'clowns.vertex.link')
                self.eq(node.get('txt'), 'we all float down here')

class FIXME:

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
