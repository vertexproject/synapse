import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.common as s_test

class DnsModelTest(s_test.SynTest):

    def test_model_dns_request(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                props = {
                    'time': '2018',
                    'query': ('1.2.3.4', 'vertex.link', 255),
                    'server': 'udp://5.6.7.8:53',
                    'reply:code': 0,
                }

                node = snap.addNode('inet:dns:request', '*', props)

                self.eq(node.get('time'), 1514764800000)
                self.eq(node.get('reply:code'), 0)
                self.eq(node.get('server'), 'udp://5.6.7.8:53')
                self.eq(node.get('query'), ('tcp://1.2.3.4', 'vertex.link', 255))

                self.nn(snap.getNodeByNdef(('inet:server', 'udp://5.6.7.8:53')))
                self.nn(snap.getNodeByNdef(('inet:server', 'udp://5.6.7.8:53')))
                self.nn(snap.getNodeByNdef(('inet:dns:query', ('tcp://1.2.3.4', 'vertex.link', 255))))

                props = {
                    'request': node.ndef[1],
                    'a': ('vertex.link', '2.3.4.5'),
                }

                answ = snap.addNode('inet:dns:answer', '*', props)
                self.nn(snap.getNodeByNdef(('inet:dns:a', ('vertex.link', 0x02030405))))

            # DNS queries can be quite complex or awkward since the protocol
            # allows for nearly anything to be asked about. This can lead to
            # pivots with non-normable data.
            q = '[inet:dns:query=(tcp://1.2.3.4, "", 1)]'
            self.len(1, core.eval(q))
            q = '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]'
            self.len(1, core.eval(q))
            q = 'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Cannot generate fqdn index bytes for a empty string') as stream:
                self.len(0, core.eval(q))
                self.true(stream.wait(1))

            q = 'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Wild card may only appear at the beginning') as stream:
                self.len(0, core.eval(q))
                self.true(stream.wait(1))

    def test_forms_dns_simple(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
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

    # The inet:dns:answer form has a large number of properties on it,
    def test_model_inet_dns_answer(self):
        tick = s_common.now()
        proc0 = s_common.guid()
        host0 = s_common.guid()
        file0 = 'sha256:' + 'a' * 64
        rcode = 0
        addr0 = 'tcp://1.2.3.4:8080/'
        addr1 = 'udp://[::1]:53/'

        ip0 = 0x01010101
        ip1 = '::2'
        fqdn0 = 'woot.com'
        fqdn1 = 'haha.com'
        email0 = 'pennywise@vertex.ninja'

        with self.getTestCore() as core:

            with core.snap() as snap:
                # a record
                props = {'a': (fqdn0, ip0)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('a'), (fqdn0, ip0))
                # ns record
                props = {'ns': (fqdn0, fqdn1)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('ns'), (fqdn0, fqdn1))
                # rev record
                props = {'rev': (ip0, fqdn0)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('rev'), (ip0, fqdn0))
                # aaaa record
                props = {'aaaa': (fqdn0, ip1)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('aaaa'), (fqdn0, ip1))
                # rev6 record
                props = {'rev6': (ip1, fqdn0)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('rev6'), (ip1, fqdn0))
                # cname record
                props = {'cname': (fqdn0, fqdn1)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('cname'), (fqdn0, fqdn1))
                # mx record
                props = {'mx': (fqdn0, fqdn1)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('mx'), (fqdn0, fqdn1))
                # soa record
                props = {'soa': (fqdn0, fqdn1, email0)}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('soa'), (fqdn0, fqdn1, email0))
                # txt record
                props = {'txt': (fqdn0, 'Oh my!')}
                node = snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('txt'), (fqdn0, 'Oh my!'))
