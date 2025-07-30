import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class DnsModelTest(s_t_utils.SynTest):

    async def test_model_dns_name_type(self):
        async with self.getTestCore() as core:
            typ = core.model.type('inet:dns:name')
            # ipv4 - good and newp
            norm, info = await typ.norm('4.3.2.1.in-addr.ARPA')
            self.eq(norm, '4.3.2.1.in-addr.arpa')
            self.eq(info.get('subs'), {'ip': (4, 0x01020304)})
            norm, info = await typ.norm('newp.in-addr.ARPA')
            self.eq(norm, 'newp.in-addr.arpa')
            self.eq(info.get('subs'), {})

            # Ipv6 - good, newp, and ipv4 included
            ipv6 = 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.ARPA'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa')
            self.eq(info.get('subs'), {'ip': (6, 0x20010db80000000000000000056789ab)})

            ipv6 = 'newp.2.ip6.arpa'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, 'newp.2.ip6.arpa')
            self.eq(info.get('subs'), {})

            ipv6 = '4.0.3.0.2.0.1.0.f.f.f.f.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, ipv6)
            self.eq(info.get('subs'), {'ip': (6, 0xffff01020304)})

            # fqdn and a invalid fqdn
            norm, info = await typ.norm('test.vertex.link')
            self.eq(norm, 'test.vertex.link')
            self.eq(info.get('subs'), {'fqdn': 'test.vertex.link'})

            norm, info = await typ.norm('1.2.3.4')
            self.eq(norm, '1.2.3.4')
            self.eq(info.get('subs'), {'ip': (4, 0x01020304)})

            norm, info = await typ.norm('134744072')  # 8.8.8.8 in integer form
            self.eq(norm, '134744072')
            self.eq(info.get('subs'), {})

            norm, info = await typ.norm('::FFFF:1.2.3.4')
            self.eq(norm, '::ffff:1.2.3.4')
            self.eq(info.get('subs'), {'ip': (6, 0xffff01020304)})

            norm, info = await typ.norm('::1')
            self.eq(norm, '::1')
            self.eq(info.get('subs'), {'ip': (6, 1)})

    async def test_model_dns_request(self):

        async with self.getTestCore() as core:
            file0 = s_common.guid()
            props = {
                'time': '2018',
                'query': ('1.2.3.4', 'vertex.link', 255),
                'server': 'udp://5.6.7.8:53',
                'reply:code': 0,
                'sandbox:file': file0,
            }
            q = '''[(inet:dns:request=$valu :time=$p.time :query=$p.query :server=$p.server
                :reply:code=$p."reply:code" :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': '*', 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            req_ndef = node.ndef
            self.eq(node.get('time'), 1514764800000000)
            self.eq(node.get('reply:code'), 0)
            self.eq(node.get('server'), 'udp://5.6.7.8:53')
            self.eq(node.get('query'), ('tcp://1.2.3.4', 'vertex.link', 255))
            self.eq(node.get('query:name'), 'vertex.link')
            self.eq(node.get('query:name:fqdn'), 'vertex.link')
            self.eq(node.get('query:type'), 255)
            self.eq(node.get('sandbox:file'), file0)
            self.none(node.get('query:client'))
            self.len(1, await core.nodes('inet:server="udp://5.6.7.8:53"'))
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))
            self.len(1, await core.nodes('file:bytes=$valu', opts={'vars': {'valu': file0}}))
            # Ensure some remaining inet:dns:query:name:* props are broken out
            nodes = await core.nodes('[(inet:dns:request=* :query:name=4.3.2.1.in-addr.arpa)]')
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('query:name:fqdn'))
            self.eq(node.get('query:name:ip'), (4, 0x01020304))
            self.eq(node.get('query:name'), '4.3.2.1.in-addr.arpa')
            # A bit of a bunk example but sometimes people query for raw ipv4/ipv6 addresses
            # and we'll try to extract them if possible :)
            nodes = await core.nodes('[(inet:dns:request=* :query:name="::ffff:1.2.3.4")]')
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('query:name:fqdn'))
            self.eq(node.get('query:name'), '::ffff:1.2.3.4')
            self.eq(node.get('query:name:ip'), (6, 0xffff01020304))
            # Ensure that lift via prefix for inet:dns:name type works
            self.len(1, await core.nodes('inet:dns:request:query:name^=vertex'))
            # Ensure that subs are broken out for inet:dns:query
            nodes = await core.nodes('inet:dns:query=("tcp://1.2.3.4", vertex.link, 255)')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('client'), 'tcp://1.2.3.4')
            self.eq(node.get('name'), 'vertex.link')
            self.eq(node.get('name:fqdn'), 'vertex.link')
            self.eq(node.get('type'), 255)

            nodes = await core.nodes('[inet:dns:request=* :reply:code=NXDOMAIN]')
            self.eq(nodes[0].get('reply:code'), 3)
            self.eq(nodes[0].repr('reply:code'), 'NXDOMAIN')

            nodes = await core.nodes('[inet:dns:request=* :reply:code=1138]')
            self.eq(nodes[0].get('reply:code'), 1138)
            self.eq(nodes[0].repr('reply:code'), '1138')

            nodes = await core.nodes('[inet:dns:query=("tcp://1.2.3.4", 4.3.2.1.in-addr.arpa, 255)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('name'), '4.3.2.1.in-addr.arpa')
            self.none(node.get('name:fqdn'))
            self.eq(node.get('name:ip'), (4, 0x01020304))

            valu = ('tcp://1.2.3.4',
                    '4.0.3.0.2.0.1.0.f.f.f.f.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa',
                    255)
            nodes = await core.nodes('[inet:dns:query=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('name:fqdn'))
            self.eq(node.get('name:ip'), (6, 0xffff01020304))
            # Try inet:dns:answer now
            nodes = await core.nodes('[inet:dns:answer=* :request=$valu :record=(inet:dns:a, (vertex.link, 2.3.4.5))]',
                                     opts={'vars': {'valu': req_ndef[1]}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('request'), req_ndef[1])
            self.eq(node.get('record'), ('inet:dns:a', ('vertex.link', (4, 0x02030405))))
            self.len(1, await core.nodes('inet:dns:a=(vertex.link, 2.3.4.5)'))
            # It is also possible for us to record a request from imperfect data
            # An example of that is dns data from a malware sandbox where the client
            # IP is unknown
            props = {
                'time': '2018',
                'exe': "a" * 32,
                'query:name': 'notac2.someone.com',
                'sandbox:file': "b" * 32,
            }
            q = '''[(inet:dns:request=$valu :time=$p.time :query:name=$p."query:name"
                    :client:exe=$p.exe :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': '*', 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('query'))
            self.eq(node.get('client:exe'), "a" * 32)
            self.eq(node.get('query:name'), 'notac2.someone.com')
            self.eq(node.get('sandbox:file'), "b" * 32)

            nodes = await core.nodes('[inet:dns:request=(test,) :query:name="::ffff:8.7.6.5"]')
            self.len(1, nodes)
            expected_nodes = (
                ('inet:ip', (6, 0xffff08070605)),
            )
            await self.checkNodes(core, expected_nodes)

            # DNS queries can be quite complex or awkward since the protocol
            # allows for nearly anything to be asked about. This can lead to
            # pivots with non-normable data.
            q = '[inet:dns:query=(tcp://1.2.3.4, "", 1)]'
            self.len(1, await core.nodes(q))
            q = '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]'
            self.len(1, await core.nodes(q))
            q = 'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Cannot generate fqdn index bytes for a empty string') as stream:
                self.len(0, await core.nodes(q))
                self.true(stream.wait(1))

            q = 'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Wild card may only appear at the beginning') as stream:
                self.len(0, await core.nodes(q))
                self.true(stream.wait(1))

    async def test_forms_dns_simple(self):

        async with self.getTestCore() as core:
            # inet:dns:a
            nodes = await core.nodes('[inet:dns:a=$valu]', opts={'vars': {'valu': ('hehe.com', '1.2.3.4')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('hehe.com', (4, 0x01020304)))
            self.eq(node.get('fqdn'), 'hehe.com')
            self.eq(node.get('ip'), (4, 0x01020304))
            nodes = await core.nodes('[inet:dns:a=$valu]',
                                     opts={'vars': {'valu': ('www.\u0915\u0949\u092e.com', '1.2.3.4')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('www.xn--11b4c3d.com', (4, 0x01020304)))
            self.eq(node.get('fqdn'), 'www.xn--11b4c3d.com')
            self.eq(node.get('ip'), (4, 0x01020304))
            # inet:dns:aaaa
            nodes = await core.nodes('[inet:dns:aaaa=$valu]', opts={'vars': {'valu': ('localhost', '::1')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('localhost', (6, 1)))
            self.eq(node.get('fqdn'), 'localhost')
            self.eq(node.get('ip'), (6, 1))
            nodes = await core.nodes('[inet:dns:aaaa=$valu]',
                                     opts={'vars': {'valu': ('hehe.com', '2001:0db8:85a3:0000:0000:8a2e:0370:7334')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('hehe.com', (6, 0x20010db885a3000000008a2e03707334)))
            self.eq(node.get('fqdn'), 'hehe.com')
            self.eq(node.get('ip'), (6, 0x20010db885a3000000008a2e03707334))
            # inet:dns:rev
            nodes = await core.nodes('[inet:dns:rev=$valu]', opts={'vars': {'valu': ('1.2.3.4', 'bebe.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ((4, 0x01020304), 'bebe.com'))
            self.eq(node.get('ip'), (4, 0x01020304))
            self.eq(node.get('fqdn'), 'bebe.com')
            # inet:dns:rev - ipv6
            nodes = await core.nodes('[inet:dns:rev=$valu]', opts={'vars': {'valu': ('FF::56', 'bebe.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ((6, 0xff0000000000000000000000000056), 'bebe.com'))
            self.eq(node.get('ip'), (6, 0xff0000000000000000000000000056))
            self.eq(node.get('fqdn'), 'bebe.com')
            # inet:dns:ns
            nodes = await core.nodes('[inet:dns:ns=$valu]', opts={'vars': {'valu': ('haha.com', 'ns1.haha.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('haha.com', 'ns1.haha.com'))
            self.eq(node.get('zone'), 'haha.com')
            self.eq(node.get('ns'), 'ns1.haha.com')
            # inet:dns:cname
            nodes = await core.nodes('[inet:dns:cname=$valu]',
                                     opts={'vars': {'valu': ('HAHA.vertex.link', 'vertex.link')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('haha.vertex.link', 'vertex.link'))
            self.eq(node.get('fqdn'), 'haha.vertex.link')
            self.eq(node.get('cname'), 'vertex.link')
            # inet:dns:mx
            nodes = await core.nodes('[inet:dns:mx=$valu]',
                                     opts={'vars': {'valu': ('vertex.link', 'mail.vertex.link')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('vertex.link', 'mail.vertex.link'))
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('mx'), 'mail.vertex.link')
            # inet:dns:soa
            guid = s_common.guid()
            props = {'fqdn': 'haha.vertex.link', 'ns': 'ns1.vertex.link', 'email': 'pennywise@vertex.link'}
            nodes = await core.nodes('[inet:dns:soa=$valu :fqdn=$p.fqdn :ns=$p.ns :email=$p.email]',
                                     opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('fqdn'), 'haha.vertex.link')
            self.eq(node.get('email'), 'pennywise@vertex.link')
            self.eq(node.get('ns'), 'ns1.vertex.link')
            # inet:dns:soa properties which previously were RO are now writeable
            q = 'inet:dns:soa=$valu [:ns=ns2.vertex.link :fqdn=hehe.vertex.link :email=bobgrey@vertex.link]'
            nodes = await core.nodes(q, opts={'vars': {'valu': guid}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('ns'), 'ns2.vertex.link')
            self.eq(node.get('fqdn'), 'hehe.vertex.link')
            self.eq(node.get('email'), 'bobgrey@vertex.link')
            # inet:dns:txt
            nodes = await core.nodes('[inet:dns:txt=$valu]',
                                     opts={'vars': {'valu': ('clowns.vertex.link', 'we all float down here')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('clowns.vertex.link', 'we all float down here'))
            self.eq(node.get('fqdn'), 'clowns.vertex.link')
            self.eq(node.get('txt'), 'we all float down here')

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:a=(foo.com, "::")]')
            self.isin('expected an IPv4', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:aaaa=(foo.com, 1.2.3.4)]')
            self.isin('expected an IPv6', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:aaaa=(foo.com, ([4, 1]))]')
            self.isin('got 4 expected 6', cm.exception.get('mesg'))

    # The inet:dns:answer form has a large number of properties on it,
    async def test_model_inet_dns_answer(self):
        ip0 = (4, 0x01010101)
        ip1 = (6, 2)
        fqdn0 = 'woot.com'
        fqdn1 = 'haha.com'
        email0 = 'pennywise@vertex.ninja'

        async with self.getTestCore() as core:
            # a record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:a, $valu)]', opts={'vars': {'valu': (fqdn0, ip0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:a', (fqdn0, ip0)))
            # ns record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:ns, $valu)]', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:ns', (fqdn0, fqdn1)))
            # rev record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:rev, $valu)]', opts={'vars': {'valu': (ip0, fqdn0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:rev', (ip0, fqdn0)))
            # aaaa record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:aaaa, $valu)]', opts={'vars': {'valu': (fqdn0, ip1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:aaaa', (fqdn0, ip1)))
            # rev ipv6 record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:rev, $valu)]', opts={'vars': {'valu': (ip1, fqdn0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:rev', (ip1, fqdn0)))
            # cname record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:cname, $valu)]', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:cname', (fqdn0, fqdn1)))
            # mx record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:mx, $valu)]', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:mx', (fqdn0, fqdn1)))
            # soa record
            guid = s_common.guid((fqdn0, fqdn1, email0))
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:soa, $valu)]', opts={'vars': {'valu': guid}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:soa', guid))
            # txt record
            nodes = await core.nodes('[inet:dns:answer=* :record=(inet:dns:txt, $valu)]', opts={'vars': {'valu': (fqdn0, 'Oh my!')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('record'), ('inet:dns:txt', (fqdn0, 'Oh my!')))
            # time prop
            nodes = await core.nodes('[inet:dns:answer=* :time=2018]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('time'), 1514764800000000)

    async def test_model_dns_wild(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:dns:wild:a=(vertex.link, 1.2.3.4)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:dns:wild:a', ('vertex.link', (4, 0x01020304))))
            self.eq(node.get('ip'), (4, 0x01020304))
            self.eq(node.get('fqdn'), 'vertex.link')

            nodes = await core.nodes('[inet:dns:wild:aaaa=(vertex.link, "2001:db8:85a3::8a2e:370:7334")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:dns:wild:aaaa', ('vertex.link', (6, 0x20010db885a3000000008a2e03707334))))
            self.eq(node.get('ip'), (6, 0x20010db885a3000000008a2e03707334))
            self.eq(node.get('fqdn'), 'vertex.link')

    async def test_model_dyndns(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ inet:dns:dynreg=*
                    :created=202202
                    :fqdn=vertex.dyndns.com
                    :contact={[ entity:contact=* :name=visi ]}
                    :client=tcp://1.2.3.4
                    :provider={[ ou:org=* :name=dyndns ]}
                    :provider:name=dyndns
                    :provider:fqdn=dyndns.com
                ]
            ''')
            self.len(1, nodes)
            self.eq(1643673600000000, nodes[0].get('created'))
            self.eq('vertex.dyndns.com', nodes[0].get('fqdn'))
            self.eq('tcp://1.2.3.4', nodes[0].get('client'))
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('provider'))
            self.eq('dyndns', nodes[0].get('provider:name'))
            self.eq('dyndns.com', nodes[0].get('provider:fqdn'))
