import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.common as s_test

class DnsModelTest(s_test.SynTest):
    def test_forms_dns_simple(self):
        with self.getTestCore() as core:
            # enum values on inet:dns:type
            t = core.model.type('inet:dns:type')
            self.eq('soa', t.norm(' SOA ')[0])
            self.eq('ns', t.norm('ns')[0])
            self.eq('mx', t.norm('mx')[0])
            self.eq('a', t.norm('a')[0])
            self.eq('aaaa', t.norm('aaaa')[0])
            self.eq('txt', t.norm('txt')[0])
            self.eq('srv', t.norm('srv')[0])
            self.eq('ptr', t.norm('ptr')[0])
            self.eq('cname', t.norm('cname')[0])
            self.eq('hinfo', t.norm('hinfo')[0])
            self.eq('isdn', t.norm('isdn')[0])
            self.raises(s_exc.BadTypeValu, t.norm, 'newpnotreal')

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

                # inet:dns:req
                addr0 = 'tcp://1.2.3.4:8080'
                addr1 = 'tcp://[::1]:2'
                node = snap.addNode('inet:dns:req', (addr0, 'vertex.link', ' A '))
                self.eq(node.ndef[1], (addr0, 'vertex.link', 'a'))
                self.eq(node.get('client'), addr0)
                self.eq(node.get('client:ipv4'), 0x01020304)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('type'), 'a')

                node = snap.addNode('inet:dns:req', (addr1, 'vertex.link', 'aaaa'))
                self.eq(node.ndef[1], (addr1, 'vertex.link', 'aaaa'))
                self.eq(node.get('client'), addr1)
                self.eq(node.get('client:ipv6'), '::1')
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('type'), 'aaaa')

    # The inet:dns:look form has a large number of properties on it,
    # its worth testing them separately.
    def test_froms_dns_look(self):
        tick = s_common.now()
        proc0 = s_common.guid()
        host0 = s_common.guid()
        file0 = 'sha256:' + 'a' * 64
        rcode = 0
        addr0 = 'tcp://1.2.3.4:8080/'
        addr1 = 'udp://[::1]:53/'

        bprops = {
            'time': tick,
            'client': addr0,
            'server': addr1,
            'proc': proc0,
            'exe': file0,
            'host': host0,
            'rcode': rcode,
        }

        ip0 = 0x01010101
        ip1 = '::2'
        fqdn0 = 'woot.com'
        fqdn1 = 'haha.com'
        email0 = 'pennywise@vertex.ninja'

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                # test a base set of props once
                node = snap.addNode('inet:dns:look', '*', bprops)
                self.true(s_common.isguid(node.ndef[1]))
                self.eq(node.get('exe'), file0)
                self.eq(node.get('time'), tick)
                self.eq(node.get('host'), host0)
                self.eq(node.get('proc'), proc0)
                self.eq(node.get('client:port'), 8080)
                self.eq(node.get('client:ipv4'), 0x01020304)
                self.eq(node.get('client'), 'tcp://1.2.3.4:8080')
                self.eq(node.get('server:port'), 53)
                self.eq(node.get('server:ipv6'), '::1')
                self.eq(node.get('server'), 'udp://[::1]:53')
                # swap client / server props and ensure the ipv4/ipv6 props
                # are set when they were not in the previous node
                props = bprops.copy()
                props['client'] = addr1
                props['server'] = addr0
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('server:ipv4'), 0x01020304)
                self.eq(node.get('client:ipv6'), '::1')
                # a record
                props = {'a': (fqdn0, ip0),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('a'), (fqdn0, ip0))
                self.eq(node.get('a:fqdn'), fqdn0)
                self.eq(node.get('a:ipv4'), ip0)
                # ns record
                props = {'ns': (fqdn0, fqdn1),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('ns'), (fqdn0, fqdn1))
                self.eq(node.get('ns:zone'), fqdn0)
                self.eq(node.get('ns:ns'), fqdn1)
                # rev record
                props = {'rev': (ip0, fqdn0),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('rev'), (ip0, fqdn0))
                self.eq(node.get('rev:ipv4'), ip0)
                self.eq(node.get('rev:fqdn'), fqdn0)
                # aaaa record
                props = {'aaaa': (fqdn0, ip1),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('aaaa'), (fqdn0, ip1))
                self.eq(node.get('aaaa:fqdn'), fqdn0)
                self.eq(node.get('aaaa:ipv6'), ip1)
                # rev6 record
                props = {'rev6': (ip1, fqdn0),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('rev6'), (ip1, fqdn0))
                self.eq(node.get('rev6:ipv6'), ip1)
                self.eq(node.get('rev6:fqdn'), fqdn0)
                # cname record
                props = {'cname': (fqdn0, fqdn1),
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('cname'), (fqdn0, fqdn1))
                self.eq(node.get('cname:fqdn'), fqdn0)
                self.eq(node.get('cname:cname'), fqdn1)
                # mx record
                props = {'mx': (fqdn0, fqdn1)}
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('mx'), (fqdn0, fqdn1))
                self.eq(node.get('mx:fqdn'), fqdn0)
                self.eq(node.get('mx:mx'), fqdn1)
                # soa record
                props = {'soa': (fqdn0, fqdn1, email0),
                         'soa:serial': 1,
                         'soa:refresh': 2,
                         'soa:retry': 3,
                         'soa:expire': 4,
                         'soa:min': 5,
                         }
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('soa'), (fqdn0, fqdn1, email0))
                self.eq(node.get('soa:fqdn'), fqdn0)
                self.eq(node.get('soa:ns'), fqdn1)
                self.eq(node.get('soa:email'), email0)
                self.eq(node.get('soa:serial'), 1)
                self.eq(node.get('soa:refresh'), 2)
                self.eq(node.get('soa:retry'), 3)
                self.eq(node.get('soa:expire'), 4)
                self.eq(node.get('soa:min'), 5)
                # txt record
                props = {'txt': (fqdn0, 'Oh my!')}
                node = snap.addNode('inet:dns:look', '*', props)
                self.eq(node.get('txt'), (fqdn0, 'Oh my!'))
                self.eq(node.get('txt:fqdn'), fqdn0)
                self.eq(node.get('txt:txt'), 'Oh my!')
