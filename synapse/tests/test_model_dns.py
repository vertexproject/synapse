import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class DnsModelTest(s_t_utils.SynTest):

    async def test_model_dns_name_type(self):
        async with self.getTestCore() as core:
            typ = core.model.type('inet:dns:name')
            # ipv4 - good and newp
            iptype = core.model.type('inet:ip')
            ipnorm, ipinfo = await iptype.norm('1.2.3.4')
            ipsub = (iptype.typehash, (4, 0x01020304), ipinfo)

            norm, info = await typ.norm('4.3.2.1.in-addr.ARPA')
            self.eq(norm, '4.3.2.1.in-addr.arpa')
            self.eq(info.get('subs'), {'ip': ipsub})
            norm, info = await typ.norm('newp.in-addr.ARPA')
            self.eq(norm, 'newp.in-addr.arpa')
            self.eq(info.get('subs'), {})

            # Ipv6 - good, newp, and ipv4 included
            ipnorm, ipinfo = await iptype.norm('2001:db8::567:89ab')
            ipsub = (iptype.typehash, (6, 0x20010db80000000000000000056789ab), ipinfo)

            ipv6 = 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.ARPA'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa')
            self.eq(info.get('subs'), {'ip': ipsub})

            ipv6 = 'newp.2.ip6.arpa'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, 'newp.2.ip6.arpa')
            self.eq(info.get('subs'), {})

            ipnorm, ipinfo = await iptype.norm('::ffff:1.2.3.4')
            ipsub = (iptype.typehash, (6, 0xffff01020304), ipinfo)

            ipv6 = '4.0.3.0.2.0.1.0.f.f.f.f.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa'
            norm, info = await typ.norm(ipv6)
            self.eq(norm, ipv6)
            self.eq(info.get('subs'), {'ip': ipsub})

            # fqdn and a invalid fqdn
            fqdntype = core.model.type('inet:fqdn')
            fqdnnorm, fqdninfo = await fqdntype.norm('test.vertex.link')
            fqdnsub = (fqdntype.typehash, 'test.vertex.link', fqdninfo)

            norm, info = await typ.norm('test.vertex.link')
            self.eq(norm, 'test.vertex.link')
            self.eq(info.get('subs'), {'fqdn': fqdnsub})

            ipnorm, ipinfo = await iptype.norm('1.2.3.4')
            ipsub = (iptype.typehash, (4, 0x01020304), ipinfo)

            norm, info = await typ.norm('1.2.3.4')
            self.eq(norm, '1.2.3.4')
            self.eq(info.get('subs'), {'ip': ipsub})

            norm, info = await typ.norm('134744072')  # 8.8.8.8 in integer form
            self.eq(norm, '134744072')
            self.eq(info.get('subs'), {})

            ipnorm, ipinfo = await iptype.norm('::ffff:1.2.3.4')
            ipsub = (iptype.typehash, (6, 0xffff01020304), ipinfo)

            norm, info = await typ.norm('::FFFF:1.2.3.4')
            self.eq(norm, '::ffff:1.2.3.4')
            self.eq(info.get('subs'), {'ip': ipsub})

            ipnorm, ipinfo = await iptype.norm('::1')
            ipsub = (iptype.typehash, (6, 0x1), ipinfo)

            norm, info = await typ.norm('::1')
            self.eq(norm, '::1')
            self.eq(info.get('subs'), {'ip': ipsub})

    async def test_model_dns_request(self):

        async with self.getTestCore() as core:
            file0 = s_common.guid()
            flow0 = s_common.guid()
            props = {
                'time': '2018',
                'query:name': 'vertex.link',
                'query:type': 255,
                'client': 'tcp://1.2.3.4',
                'server': 'udp://5.6.7.8:53',
                'flow': flow0,
                'sandbox:file': file0,
            }
            q = '''[(inet:dns:request=$valu :time=$p.time
                :query:name=$p."query:name" :query:type=$p."query:type"
                :client=$p.client :server=$p.server :flow=$p.flow
                :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': '*', 'p': props}})
            self.len(1, nodes)
            req = nodes[0]
            self.propeq(req, 'time', 1514764800000000)
            self.propeq(req, 'client', 'tcp://1.2.3.4')
            self.propeq(req, 'server', 'udp://5.6.7.8:53')
            self.propeq(req, 'flow', flow0)
            self.propeq(req, 'query:name', 'vertex.link')
            self.propeq(req, 'query:type', 255)
            self.propeq(req, 'sandbox:file', file0)
            self.len(1, await core.nodes('inet:server="udp://5.6.7.8:53"'))
            self.len(1, await core.nodes('inet:flow=$valu', opts={'vars': {'valu': flow0}}))
            self.len(1, await core.nodes('file:bytes=$valu', opts={'vars': {'valu': file0}}))

            # Ensure that lift via prefix for inet:dns:name type works
            self.len(1, await core.nodes('inet:dns:request:query:name^=vertex'))

            # inet:dns:query form still exists independently
            nodes = await core.nodes('[inet:dns:query=("tcp://1.2.3.4", vertex.link, 255)]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'client', 'tcp://1.2.3.4')
            self.propeq(node, 'name', 'vertex.link')
            self.propeq(node, 'type', 255)

            # inet:dns:response with code values
            nodes = await core.nodes('[inet:dns:response=* :code=NOERROR]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'code', 0)
            self.eq(nodes[0].repr('code'), 'NOERROR')

            nodes = await core.nodes('[inet:dns:response=* :code=NXDOMAIN]')
            self.propeq(nodes[0], 'code', 3)
            self.eq(nodes[0].repr('code'), 'NXDOMAIN')

            nodes = await core.nodes('[inet:dns:response=* :code=1138]')
            self.propeq(nodes[0], 'code', 1138)
            self.eq(nodes[0].repr('code'), '1138')

            # Link a request to a response with answers
            ans0 = s_common.guid()
            ans1 = s_common.guid()
            q = '''[
                (inet:dns:answer=$a0 :ttl=300 :record={[ inet:dns:a=(vertex.link, 2.3.4.5) ]})
                (inet:dns:answer=$a1 :ttl=300 :record={[ inet:dns:a=(vertex.link, 2.3.4.6) ]})
            ]'''
            await core.nodes(q, opts={'vars': {'a0': ans0, 'a1': ans1}})

            resp_iden = s_common.guid()
            q = '''[ inet:dns:response=$r
                :time=2018
                :server=udp://5.6.7.8:53
                :client=tcp://1.2.3.4
                :flow=$f
                :code=NOERROR
                :answers=($a0, $a1)
            ]'''
            nodes = await core.nodes(q, opts={'vars': {'r': resp_iden, 'f': flow0, 'a0': ans0, 'a1': ans1}})
            self.len(1, nodes)
            resp = nodes[0]
            self.propeq(resp, 'time', 1514764800000000)
            self.propeq(resp, 'code', 0)
            self.propeq(resp, 'server', 'udp://5.6.7.8:53')
            self.propeq(resp, 'client', 'tcp://1.2.3.4')
            self.propeq(resp, 'flow', flow0)
            self.propeq(resp, 'answers', (ans0, ans1))

            q = 'inet:dns:request [ :response=$r ]'
            nodes = await core.nodes(q, opts={'vars': {'r': resp_iden}})
            self.propeq(nodes[0], 'response', resp_iden)
            self.len(1, await core.nodes('inet:dns:request :response -> inet:dns:response'))

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
            self.propeq(node, 'client:exe', "a" * 32)
            self.propeq(node, 'query:name', 'notac2.someone.com')
            self.propeq(node, 'sandbox:file', "b" * 32)

            # DNS queries can be quite complex or awkward since the protocol
            # allows for nearly anything to be asked about. This can lead to
            # pivots with non-normable data.
            q = '[inet:dns:query=(tcp://1.2.3.4, "", 1)]'
            self.len(1, await core.nodes(q))
            q = '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]'
            self.len(1, await core.nodes(q))

            q = 'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn'
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)
            self.len(0, [m for m in msgs if m[0] == 'node'])

            q = 'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn'
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)
            self.len(0, [m for m in msgs if m[0] == 'node'])

    async def test_forms_dns_simple(self):

        async with self.getTestCore() as core:
            # inet:dns:a
            nodes = await core.nodes('[inet:dns:a=$valu]', opts={'vars': {'valu': ('hehe.com', '1.2.3.4')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('hehe.com', (4, 0x01020304)))
            self.propeq(node, 'fqdn', 'hehe.com')
            self.propeq(node, 'ip', (4, 0x01020304))
            nodes = await core.nodes('[inet:dns:a=$valu]',
                                     opts={'vars': {'valu': ('www.\u0915\u0949\u092e.com', '1.2.3.4')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('www.xn--11b4c3d.com', (4, 0x01020304)))
            self.propeq(node, 'fqdn', 'www.xn--11b4c3d.com')
            self.propeq(node, 'ip', (4, 0x01020304))
            # inet:dns:aaaa
            nodes = await core.nodes('[inet:dns:aaaa=$valu]', opts={'vars': {'valu': ('localhost', '::1')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('localhost', (6, 1)))
            self.propeq(node, 'fqdn', 'localhost')
            self.propeq(node, 'ip', (6, 1))
            nodes = await core.nodes('[inet:dns:aaaa=$valu]',
                                     opts={'vars': {'valu': ('hehe.com', '2001:0db8:85a3:0000:0000:8a2e:0370:7334')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('hehe.com', (6, 0x20010db885a3000000008a2e03707334)))
            self.propeq(node, 'fqdn', 'hehe.com')
            self.propeq(node, 'ip', (6, 0x20010db885a3000000008a2e03707334))
            # inet:dns:rev
            nodes = await core.nodes('[inet:dns:rev=$valu]', opts={'vars': {'valu': ('1.2.3.4', 'bebe.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ((4, 0x01020304), 'bebe.com'))
            self.propeq(node, 'ip', (4, 0x01020304))
            self.propeq(node, 'fqdn', 'bebe.com')
            # inet:dns:rev - ipv6
            nodes = await core.nodes('[inet:dns:rev=$valu]', opts={'vars': {'valu': ('FF::56', 'bebe.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ((6, 0xff0000000000000000000000000056), 'bebe.com'))
            self.propeq(node, 'ip', (6, 0xff0000000000000000000000000056))
            self.propeq(node, 'fqdn', 'bebe.com')
            # inet:dns:ns
            nodes = await core.nodes('[inet:dns:ns=$valu]', opts={'vars': {'valu': ('haha.com', 'ns1.haha.com')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('haha.com', 'ns1.haha.com'))
            self.propeq(node, 'zone', 'haha.com')
            self.propeq(node, 'ns', 'ns1.haha.com')
            # inet:dns:cname
            nodes = await core.nodes('[inet:dns:cname=$valu]',
                                     opts={'vars': {'valu': ('HAHA.vertex.link', 'vertex.link')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('haha.vertex.link', 'vertex.link'))
            self.propeq(node, 'fqdn', 'haha.vertex.link')
            self.propeq(node, 'cname', 'vertex.link')
            # inet:dns:mx
            nodes = await core.nodes('[inet:dns:mx=$valu]',
                                     opts={'vars': {'valu': ('vertex.link', 'mail.vertex.link')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('vertex.link', 'mail.vertex.link'))
            self.propeq(node, 'fqdn', 'vertex.link')
            self.propeq(node, 'mx', 'mail.vertex.link')
            # inet:dns:soa
            guid = s_common.guid()
            props = {'fqdn': 'haha.vertex.link', 'ns': 'ns1.vertex.link', 'email': 'pennywise@vertex.link'}
            nodes = await core.nodes('[inet:dns:soa=$valu :fqdn=$p.fqdn :ns=$p.ns :email=$p.email]',
                                     opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'fqdn', 'haha.vertex.link')
            self.propeq(node, 'email', 'pennywise@vertex.link')
            self.propeq(node, 'ns', 'ns1.vertex.link')
            # inet:dns:soa properties which previously were RO are now writeable
            q = 'inet:dns:soa=$valu [:ns=ns2.vertex.link :fqdn=hehe.vertex.link :email=bobgrey@vertex.link]'
            nodes = await core.nodes(q, opts={'vars': {'valu': guid}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'ns', 'ns2.vertex.link')
            self.propeq(node, 'fqdn', 'hehe.vertex.link')
            self.propeq(node, 'email', 'bobgrey@vertex.link')
            # inet:dns:txt
            nodes = await core.nodes('[inet:dns:txt=$valu]',
                                     opts={'vars': {'valu': ('clowns.vertex.link', 'we all float down here')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], ('clowns.vertex.link', 'we all float down here'))
            self.propeq(node, 'fqdn', 'clowns.vertex.link')
            self.propeq(node, 'txt', 'we all float down here')

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:a=(foo.com, "::")]')
            self.isin('expected an IPv4', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:aaaa=(foo.com, 1.2.3.4)]')
            self.isin('expected an IPv6', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('[inet:dns:aaaa=(foo.com, ([4, 1]))]')
            self.isin('got 4 expected 6', cm.exception.get('mesg'))

    async def test_model_inet_dns_answer(self):
        ip0 = (4, 0x01010101)
        ip1 = (6, 2)
        fqdn0 = 'woot.com'
        fqdn1 = 'haha.com'
        email0 = 'pennywise@vertex.ninja'

        async with self.getTestCore() as core:
            # a record
            nodes = await core.nodes('[inet:dns:answer=* :ttl=300 :record={[ inet:dns:a=$valu ]} ]', opts={'vars': {'valu': (fqdn0, ip0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'ttl', 300)
            self.propeq(node, 'record', (fqdn0, ip0), form='inet:dns:a')
            # ns record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:ns=$valu ]} ]', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (fqdn0, fqdn1), form='inet:dns:ns')
            # rev record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:rev=$valu ]} ]', opts={'vars': {'valu': (ip0, fqdn0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (ip0, fqdn0), form='inet:dns:rev')
            # aaaa record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:aaaa=$valu ]} ]', opts={'vars': {'valu': (fqdn0, ip1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (fqdn0, ip1), form='inet:dns:aaaa')
            # rev ipv6 record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:rev=$valu ]} ]', opts={'vars': {'valu': (ip1, fqdn0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (ip1, fqdn0), form='inet:dns:rev')
            # cname record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:cname=$valu ]} ]', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (fqdn0, fqdn1), form='inet:dns:cname')
            # soa record
            guid = s_common.guid((fqdn0, fqdn1, email0))
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:soa=$valu ]} ]', opts={'vars': {'valu': guid}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', guid, form='inet:dns:soa')
            # txt record
            nodes = await core.nodes('[inet:dns:answer=* :record={[ inet:dns:txt=$valu ]} ]', opts={'vars': {'valu': (fqdn0, 'Oh my!')}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'record', (fqdn0, 'Oh my!'), form='inet:dns:txt')

            # inet:dns:mx:answer extends inet:dns:answer with MX-specific props
            nodes = await core.nodes('''[ inet:dns:mx:answer=*
                :ttl=600
                :priority=10
                :record={[ inet:dns:mx=$valu ]}
            ]''', opts={'vars': {'valu': (fqdn0, fqdn1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'ttl', 600)
            self.propeq(node, 'priority', 10)
            self.propeq(node, 'record', (fqdn0, fqdn1), form='inet:dns:mx')

    async def test_model_dns_wild(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:dns:wild:a=(vertex.link, 1.2.3.4)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:dns:wild:a', ('vertex.link', (4, 0x01020304))))
            self.propeq(node, 'ip', (4, 0x01020304))
            self.propeq(node, 'fqdn', 'vertex.link')

            nodes = await core.nodes('[inet:dns:wild:aaaa=(vertex.link, "2001:db8:85a3::8a2e:370:7334")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:dns:wild:aaaa', ('vertex.link', (6, 0x20010db885a3000000008a2e03707334))))
            self.propeq(node, 'ip', (6, 0x20010db885a3000000008a2e03707334))
            self.propeq(node, 'fqdn', 'vertex.link')

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
            self.propeq(nodes[0], 'created', 1643673600000000)
            self.propeq(nodes[0], 'fqdn', 'vertex.dyndns.com')
            self.propeq(nodes[0], 'client', 'tcp://1.2.3.4')
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('provider'))
            self.propeq(nodes[0], 'provider:name', 'dyndns')
            self.propeq(nodes[0], 'provider:fqdn', 'dyndns.com')
