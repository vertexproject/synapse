import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class DnsModelTest(s_t_utils.SynTest):

    async def test_model_dns_name_type(self):
        async with self.getTestCore() as core:
            typ = core.model.type('inet:dns:name')
            # ipv4 - good and newp
            norm, info = typ.norm('4.3.2.1.in-addr.ARPA')
            self.eq(norm, '4.3.2.1.in-addr.arpa')
            self.eq(info.get('subs'), {'ipv4': 0x01020304})
            norm, info = typ.norm('newp.in-addr.ARPA')
            self.eq(norm, 'newp.in-addr.arpa')
            self.eq(info.get('subs'), {})

            # Ipv6 - good, newp, and ipv4 included
            ipv6 = 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.ARPA'
            norm, info = typ.norm(ipv6)
            self.eq(norm, 'b.a.9.8.7.6.5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa')
            self.eq(info.get('subs'), {'ipv6': '2001:db8::567:89ab'})

            ipv6 = 'newp.2.ip6.arpa'
            norm, info = typ.norm(ipv6)
            self.eq(norm, 'newp.2.ip6.arpa')
            self.eq(info.get('subs'), {})

            ipv6 = '4.0.3.0.2.0.1.0.f.f.f.f.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa'
            norm, info = typ.norm(ipv6)
            self.eq(norm, ipv6)
            self.eq(info.get('subs'), {'ipv6': '::ffff:1.2.3.4', 'ipv4': 0x01020304})

            # fqdn and a invalid fqdn
            norm, info = typ.norm('test.vertex.link')
            self.eq(norm, 'test.vertex.link')
            self.eq(info.get('subs'), {'fqdn': 'test.vertex.link'})

            norm, info = typ.norm('1.2.3.4')
            self.eq(norm, '1.2.3.4')
            self.eq(info.get('subs'), {'ipv4': 0x01020304})

            norm, info = typ.norm('134744072')  # 8.8.8.8 in integer form
            self.eq(norm, '134744072')
            self.eq(info.get('subs'), {})

            norm, info = typ.norm('::FFFF:1.2.3.4')
            self.eq(norm, '::ffff:1.2.3.4')
            self.eq(info.get('subs'), {'ipv6': '::ffff:1.2.3.4', 'ipv4': 0x01020304})

            norm, info = typ.norm('::1')
            self.eq(norm, '::1')
            self.eq(info.get('subs'), {'ipv6': '::1'})

    async def test_model_dns_request(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                props = {
                    'time': '2018',
                    'query': ('1.2.3.4', 'vertex.link', 255),
                    'server': 'udp://5.6.7.8:53',
                    'reply:code': 0,
                    'sandbox:file': 'a' * 64,
                }
                expected_nodes = (
                    ('inet:server', 'udp://5.6.7.8:53'),
                    ('inet:fqdn', 'vertex.link'),
                    ('file:bytes', 'sha256:' + 64 * 'a'),
                )
                node = await snap.addNode('inet:dns:request', '*', props)
                req_ndef = node.ndef
                self.eq(node.get('time'), 1514764800000)
                self.eq(node.get('reply:code'), 0)
                self.eq(node.get('server'), 'udp://5.6.7.8:53')
                self.eq(node.get('query'), ('tcp://1.2.3.4', 'vertex.link', 255))
                self.eq(node.get('query:name'), 'vertex.link')
                self.eq(node.get('query:name:fqdn'), 'vertex.link')
                self.eq(node.get('query:type'), 255)
                self.eq(node.get('sandbox:file'), 'sha256:' + 64 * 'a')
                self.none(node.get('query:client'))
                await self.checkNodes(core, expected_nodes)

                # Ensure some remaining inet:dns:query:name:* props are broken out
                node = await snap.addNode('inet:dns:request', '*', {'query:name': '4.3.2.1.in-addr.arpa'})
                self.none(node.get('query:name:fqdn'))
                self.eq(node.get('query:name:ipv4'), 0x01020304)
                self.eq(node.get('query:name'), '4.3.2.1.in-addr.arpa')

                # A bit of a bunk example but sometimes people query for raw ipv4/ipv6 addresses
                # and we'll try to extract them if possible :)
                node = await snap.addNode('inet:dns:request', '*', {'query:name': '::ffff:1.2.3.4'})
                self.none(node.get('query:name:fqdn'))
                self.eq(node.get('query:name'), '::ffff:1.2.3.4')
                self.eq(node.get('query:name:ipv4'), 0x01020304)
                self.eq(node.get('query:name:ipv6'), '::ffff:1.2.3.4')

                # Ensure that lift via prefix for inet:dns:name type works
                nodes = await snap.nodes('inet:dns:request:query:name^=vertex')
                self.len(1, nodes)

                # Ensure that subs are broken out for inet:dns:query
                node = await snap.getNodeByNdef(('inet:dns:query', ('tcp://1.2.3.4', 'vertex.link', 255)))
                self.eq(node.get('client'), 'tcp://1.2.3.4')
                self.eq(node.get('name'), 'vertex.link')
                self.eq(node.get('name:fqdn'), 'vertex.link')
                self.eq(node.get('type'), 255)

                node = await snap.addNode('inet:dns:query', ('tcp://1.2.3.4', '4.3.2.1.in-addr.arpa', 255))
                self.eq(node.get('name'), '4.3.2.1.in-addr.arpa')
                self.none(node.get('name:fqdn'))
                self.eq(node.get('name:ipv4'), 0x01020304)
                self.none(node.get('name:ipv6'))
                valu = ('tcp://1.2.3.4',
                        '4.0.3.0.2.0.1.0.f.f.f.f.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.ip6.arpa',
                        255)
                node = await snap.addNode('inet:dns:query', valu)
                self.none(node.get('name:fqdn'))
                self.eq(node.get('name:ipv4'), 0x01020304)
                self.eq(node.get('name:ipv6'), '::ffff:1.2.3.4')

                # Try inet:dns:answer now
                props = {
                    'request': req_ndef[1],
                    'a': ('vertex.link', '2.3.4.5'),
                }

                await snap.addNode('inet:dns:answer', '*', props)
                self.nn(await snap.getNodeByNdef(('inet:dns:a', ('vertex.link', 0x02030405))))

                # It is also possible for us to record a request from imperfect data
                # An example of that is dns data from a malware sandbox where the client
                # IP is unknown
                props = {
                    'time': '2018',
                    'exe': f'guid:{"a" * 32}',
                    'query:name': 'notac2.someone.com',
                    'sandbox:file': f'guid:{"b" * 32}',
                }
                node = await snap.addNode('inet:dns:request', '*', props)
                self.none(node.get('query'))
                self.eq(node.get('exe'), f'guid:{"a" * 32}')
                self.eq(node.get('query:name'), 'notac2.someone.com')
                self.eq(node.get('sandbox:file'), f'guid:{"b" * 32}')

            nodes = await core.nodes('[inet:dns:request=(test,) :query:name="::ffff:8.7.6.5"]')
            self.len(1, nodes)
            expected_nodes = (
                ('inet:ipv4', 0x08070605),
                ('inet:ipv6', '::ffff:8.7.6.5'),
            )
            await self.checkNodes(core, expected_nodes)

            # DNS queries can be quite complex or awkward since the protocol
            # allows for nearly anything to be asked about. This can lead to
            # pivots with non-normable data.
            q = '[inet:dns:query=(tcp://1.2.3.4, "", 1)]'
            await self.agenlen(1, core.eval(q))
            q = '[inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1)]'
            await self.agenlen(1, core.eval(q))
            q = 'inet:dns:query=(tcp://1.2.3.4, "", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Cannot generate fqdn index bytes for a empty string') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

            q = 'inet:dns:query=(tcp://1.2.3.4, "foo*.haha.com", 1) :name -> inet:fqdn'
            with self.getLoggerStream('synapse.lib.ast',
                                      'Wild card may only appear at the beginning') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

    async def test_forms_dns_simple(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                # inet:dns:a
                node = await snap.addNode('inet:dns:a', ('hehe.com', '1.2.3.4'))
                self.eq(node.ndef[1], ('hehe.com', 0x01020304))
                self.eq(node.get('fqdn'), 'hehe.com')
                self.eq(node.get('ipv4'), 0x01020304)

                node = await snap.addNode('inet:dns:a', ('www.\u0915\u0949\u092e.com', '1.2.3.4'))
                self.eq(node.ndef[1], ('www.xn--11b4c3d.com', 0x01020304))
                self.eq(node.get('fqdn'), 'www.xn--11b4c3d.com')
                self.eq(node.get('ipv4'), 0x01020304)

                # inet:dns:aaaa
                node = await snap.addNode('inet:dns:aaaa', ('localhost', '::1'))
                self.eq(node.ndef[1], ('localhost', '::1'))
                self.eq(node.get('fqdn'), 'localhost')
                self.eq(node.get('ipv6'), '::1')

                node = await snap.addNode('inet:dns:aaaa', ('hehe.com', '2001:0db8:85a3:0000:0000:8a2e:0370:7334'))
                self.eq(node.ndef[1], ('hehe.com', '2001:db8:85a3::8a2e:370:7334'))
                self.eq(node.get('fqdn'), 'hehe.com')
                self.eq(node.get('ipv6'), '2001:db8:85a3::8a2e:370:7334')

                # inet:dns:rev
                node = await snap.addNode('inet:dns:rev', ('1.2.3.4', 'bebe.com'))
                self.eq(node.ndef[1], (0x01020304, 'bebe.com'))
                self.eq(node.get('ipv4'), 0x01020304)
                self.eq(node.get('fqdn'), 'bebe.com')

                # inet:dns:rev6
                node = await snap.addNode('inet:dns:rev6', ('FF::56', 'bebe.com'))
                self.eq(node.ndef[1], ('ff::56', 'bebe.com'))
                self.eq(node.get('ipv6'), 'ff::56')
                self.eq(node.get('fqdn'), 'bebe.com')

                # inet:dns:ns
                node = await snap.addNode('inet:dns:ns', ('haha.com', 'ns1.haha.com'))
                self.eq(node.ndef[1], ('haha.com', 'ns1.haha.com'))
                self.eq(node.get('zone'), 'haha.com')
                self.eq(node.get('ns'), 'ns1.haha.com')

                # inet:dns:cname
                node = await snap.addNode('inet:dns:cname', ('HAHA.vertex.link', 'vertex.link'))
                self.eq(node.ndef[1], ('haha.vertex.link', 'vertex.link'))
                self.eq(node.get('fqdn'), 'haha.vertex.link')
                self.eq(node.get('cname'), 'vertex.link')

                # inet:dns:mx
                node = await snap.addNode('inet:dns:mx', ('vertex.link', 'mail.vertex.link'))
                self.eq(node.ndef[1], ('vertex.link', 'mail.vertex.link'))
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('mx'), 'mail.vertex.link')

                # inet:dns:soa
                guid = s_common.guid()
                props = {'fqdn': 'haha.vertex.link', 'ns': 'ns1.vertex.link', 'email': 'pennywise@vertex.link'}
                node = await snap.addNode('inet:dns:soa', guid, props)
                self.eq(node.get('fqdn'), 'haha.vertex.link')
                self.eq(node.get('email'), 'pennywise@vertex.link')
                self.eq(node.get('ns'), 'ns1.vertex.link')

                # inet:dns:txt
                node = await snap.addNode('inet:dns:txt', ('clowns.vertex.link', 'we all float down here'))
                self.eq(node.ndef[1], ('clowns.vertex.link', 'we all float down here'))
                self.eq(node.get('fqdn'), 'clowns.vertex.link')
                self.eq(node.get('txt'), 'we all float down here')

    # The inet:dns:answer form has a large number of properties on it,
    async def test_model_inet_dns_answer(self):
        ip0 = 0x01010101
        ip1 = '::2'
        fqdn0 = 'woot.com'
        fqdn1 = 'haha.com'
        email0 = 'pennywise@vertex.ninja'

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                # a record
                props = {'a': (fqdn0, ip0)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('a'), (fqdn0, ip0))
                # ns record
                props = {'ns': (fqdn0, fqdn1)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('ns'), (fqdn0, fqdn1))
                # rev record
                props = {'rev': (ip0, fqdn0)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('rev'), (ip0, fqdn0))
                # aaaa record
                props = {'aaaa': (fqdn0, ip1)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('aaaa'), (fqdn0, ip1))
                # rev6 record
                props = {'rev6': (ip1, fqdn0)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('rev6'), (ip1, fqdn0))
                # cname record
                props = {'cname': (fqdn0, fqdn1)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('cname'), (fqdn0, fqdn1))
                # mx record
                props = {'mx': (fqdn0, fqdn1)}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('mx'), (fqdn0, fqdn1))
                # soa record
                guid = s_common.guid((fqdn0, fqdn1, email0))
                props = {'soa': guid}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('soa'), guid)
                # txt record
                props = {'txt': (fqdn0, 'Oh my!')}
                node = await snap.addNode('inet:dns:answer', '*', props)
                self.eq(node.get('txt'), (fqdn0, 'Oh my!'))

    async def test_model_dns_wild(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                wild = await snap.addNode('inet:dns:wild:a', ('vertex.link', '1.2.3.4'))
                self.eq(wild.ndef, ('inet:dns:wild:a', ('vertex.link', 0x01020304)))
                self.eq(wild.get('ipv4'), 0x01020304)
                self.eq(wild.get('fqdn'), 'vertex.link')

                wild = await snap.addNode('inet:dns:wild:aaaa', ('vertex.link', '2001:db8:85a3::8a2e:370:7334'))
                self.eq(wild.ndef, ('inet:dns:wild:aaaa', ('vertex.link', '2001:db8:85a3::8a2e:370:7334')))
                self.eq(wild.get('ipv6'), '2001:db8:85a3::8a2e:370:7334')
                self.eq(wild.get('fqdn'), 'vertex.link')
