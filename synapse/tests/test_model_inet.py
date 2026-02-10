import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class InetModelTest(s_t_utils.SynTest):

    async def test_mode_inet_basics(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:serverfile=(1.2.3.4:22, *) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:22')
            self.len(1, await core.nodes('inet:serverfile -> file:bytes'))
            self.len(1, await core.nodes('inet:serverfile -> inet:server'))

    async def test_inet_handshakes(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ inet:ssh:handshake=*
                    :flow=*
                    :client=5.5.5.5
                    :server=1.2.3.4:22
                    :client:key={[ crypto:key:rsa=* ]}
                    :server:key={[ crypto:key:rsa=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'client', 'tcp://5.5.5.5')
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:22')

            self.len(1, await core.nodes('inet:ssh:handshake :flow -> inet:flow'))
            self.len(1, await core.nodes('inet:ssh:handshake :client:key -> crypto:key'))
            self.len(1, await core.nodes('inet:ssh:handshake :server:key -> crypto:key'))

            nodes = await core.nodes('''
                [ inet:rdp:handshake=*
                    :flow=*
                    :client=5.5.5.5
                    :server=1.2.3.4:22
                    :client:hostname=SYNCODER
                    :client:keyboard:layout=AZERTY
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'client', 'tcp://5.5.5.5')
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:22')
            self.propeq(nodes[0], 'client:keyboard:layout', 'azerty')

            self.len(1, await core.nodes('inet:rdp:handshake :flow -> inet:flow'))
            self.len(1, await core.nodes('inet:rdp:handshake :client:hostname -> it:hostname'))

    async def test_inet_jarm(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:tls:jarmsample=(1.2.3.4:443, 07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:443')
            self.propeq(nodes[0], 'jarmhash', '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')
            self.eq(('tcp://1.2.3.4:443', '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1'), nodes[0].ndef[1])

            nodes = await core.nodes('inet:tls:jarmhash=07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')
            self.len(1, nodes)
            self.eq('07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1', nodes[0].ndef[1])
            self.propeq(nodes[0], 'ciphers', '07d14d16d21d21d07c42d41d00041d')
            self.propeq(nodes[0], 'extensions', '24a458a375eef0c576d23a7bab9a9fb1')

    async def test_ipv4_lift_range(self):

        async with self.getTestCore() as core:

            for i in range(5):
                valu = f'1.2.3.{i}'
                nodes = await core.nodes('[inet:ip=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)

            self.len(3, await core.nodes('inet:ip=1.2.3.1-1.2.3.3'))
            self.len(3, await core.nodes('[inet:ip=1.2.3.1-1.2.3.3]'))
            self.len(3, await core.nodes('inet:ip +inet:ip=1.2.3.1-1.2.3.3'))
            self.len(3, await core.nodes('inet:ip*range=(1.2.3.1, 1.2.3.3)'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:ip="1.2.3.1-::"')

    async def test_ipv4_filt_cidr(self):

        async with self.getTestCore() as core:

            self.len(5, await core.nodes('[ inet:ip=1.2.3.0/30 inet:ip=5.5.5.5 ]'))
            self.len(4, await core.nodes('inet:ip +inet:ip=1.2.3.0/30'))
            self.len(1, await core.nodes('inet:ip -inet:ip=1.2.3.0/30'))

            self.len(256, await core.nodes('[ inet:ip=192.168.1.0/24]'))
            self.len(256, await core.nodes('[ inet:ip=192.168.2.0/24]'))
            self.len(256, await core.nodes('inet:ip=192.168.1.0/24'))

            # Seed some nodes for bounds checking
            vals = list(range(1, 33))
            q = 'for $v in $vals { [inet:ip=`10.2.1.{$v}` ] }'
            self.len(len(vals), await core.nodes(q, opts={'vars': {'vals': vals}}))

            nodes = await core.nodes('inet:ip=10.2.1.4/32')
            self.len(1, nodes)
            self.len(1, await core.nodes('inet:ip +inet:ip=10.2.1.4/32'))

            nodes = await core.nodes('inet:ip=10.2.1.4/31')
            self.len(2, nodes)
            self.len(2, await core.nodes('inet:ip +inet:ip=10.2.1.4/31'))

            # 10.2.1.1/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=10.2.1.1/30')
            self.len(3, nodes)

            # 10.2.1.2/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=10.2.1.2/30')
            self.len(3, nodes)

            # 10.2.1.1/29 is 10.2.1.0 -> 10.2.1.7 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=10.2.1.1/29')
            self.len(7, nodes)

            # 10.2.1.8/29 is 10.2.1.8 -> 10.2.1.15
            nodes = await core.nodes('inet:ip=10.2.1.8/29')
            self.len(8, nodes)

            # 10.2.1.1/28 is 10.2.1.0 -> 10.2.1.15 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=10.2.1.1/28')
            self.len(15, nodes)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:ip=1.2.3.4/a')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:ip=1.2.3.4/40')

    async def test_sockaddr(self):
        formname = 'inet:sockaddr'
        async with self.getTestCore() as core:
            t = core.model.type(formname)

            ipnorm, ipinfo = await t.iptype.norm('1.2.3.4')
            ipsub = (t.iptype.typehash, (4, 16909060), ipinfo)

            portsub = (t.porttype.typehash, 80, {})

            tcpsub = (t.prototype.typehash, 'tcp', {})
            udpsub = (t.prototype.typehash, 'udp', {})
            icmpsub = (t.prototype.typehash, 'icmp', {})

            # Proto defaults to tcp
            subs = {'ip': ipsub, 'proto': tcpsub}
            virts = {'ip': ((4, 16909060), 26)}
            self.eq(await t.norm('1.2.3.4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))

            subs = {'ip': ipsub, 'proto': tcpsub, 'port': portsub}
            virts = {'ip': ((4, 16909060), 26), 'port': (80, 9)}
            self.eq(await t.norm('1.2.3.4:80'), ('tcp://1.2.3.4:80', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('https://192.168.1.1:80'))  # bad proto

            # IPv4
            subs = {'ip': ipsub, 'proto': tcpsub}
            virts = {'ip': ((4, 16909060), 26)}
            self.eq(await t.norm('tcp://1.2.3.4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))
            self.eq(await t.norm('tcp://1[.]2.3[.]4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))

            subs = {'ip': ipsub, 'proto': udpsub, 'port': portsub}
            virts = {'ip': ((4, 16909060), 26), 'port': (80, 9)}
            self.eq(await t.norm('udp://1.2.3.4:80'), ('udp://1.2.3.4:80', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://1.2.3.4:-1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://1.2.3.4:66000'))

            ipnorm, ipinfo = await t.iptype.norm('::1')
            ipsub = (t.iptype.typehash, (6, 1), ipinfo)
            portsub = (t.porttype.typehash, 2, {})

            # IPv6
            subs = {'ip': ipsub, 'proto': icmpsub}
            virts = {'ip': ((6, 1), 26)}
            self.eq(await t.norm('icmp://::1'), ('icmp://::1', {'subs': subs, 'virts': virts}))

            subs = {'ip': ipsub, 'proto': tcpsub, 'port': portsub}
            virts = {'ip': ((6, 1), 26), 'port': (2, 9)}
            self.eq(await t.norm('tcp://[::1]:2'), ('tcp://[::1]:2', {'subs': subs, 'virts': virts}))

            subs = {'ip': ipsub, 'proto': tcpsub}
            virts = {'ip': ((6, 1), 26)}
            # todo: norm one way for ipv6 w/o port?
            # self.eq(await t.norm('tcp://[::1]'), ('tcp://[::1]', {'subs': subs, 'virts': virts}))
            self.eq(await t.norm('tcp://[::1]'), ('tcp://::1', {'subs': subs, 'virts': virts}))

            ipnorm, ipinfo = await t.iptype.norm('::fFfF:0102:0304')
            ipsub = (t.iptype.typehash, (6, 0xffff01020304), ipinfo)

            subs = {'ip': ipsub, 'proto': tcpsub, 'port': portsub}
            virts = {'ip': ((6, 0xffff01020304), 26), 'port': (2, 9)}
            self.eq(await t.norm('tcp://[::fFfF:0102:0304]:2'),
                    ('tcp://[::ffff:1.2.3.4]:2', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://[::1'))  # bad ipv6 w/ port

            # todo: norm dict test

    async def test_asn_collection(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:asn=123 :owner:name=COOL :owner={[ ou:org=* ]} :seen=(2020, 2021) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asn', 123))
            self.propeq(node, 'owner:name', 'cool')
            self.propeq(nodes[0], 'seen', (1577836800000000, 1609459200000000, 31622400000000))
            self.len(1, await core.nodes('inet:asn :owner -> ou:org'))

            nodes = await core.nodes('[ inet:asnet=(54959, (1.2.3.4, 5.6.7.8)) :seen=2022 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet', (54959, ((4, 0x01020304), (4, 0x05060708)))))
            self.propeq(node, 'asn', 54959)
            self.propeq(node, 'net', ((4, 0x01020304), (4, 0x05060708)))
            self.propeq(node, 'net:min', (4, 0x01020304))
            self.propeq(node, 'net:max', (4, 0x05060708))
            self.nn(node.get('seen'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4'))
            self.len(1, await core.nodes('inet:ip=5.6.7.8'))

            minv = (6, 0xff0000000000000000000000000000)
            maxv = (6, 0xff0000000000000000000000000100)
            nodes = await core.nodes('[ inet:asnet=(99, (ff::00, ff::0100)) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet', (99, (minv, maxv))))
            self.propeq(node, 'asn', 99)
            self.propeq(node, 'net', (minv, maxv))
            self.propeq(node, 'net:min', minv)
            self.propeq(node, 'net:max', maxv)
            self.len(1, await core.nodes('inet:ip="ff::"'))
            self.len(1, await core.nodes('inet:ip="ff::100"'))

            nodes = await core.nodes('[ inet:asnip=(54959, 1.2.3.4) :seen=(2024, 2025) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'ip', (4, 0x01020304))
            self.propeq(nodes[0], 'asn', 54959)

    async def test_client(self):
        data = (
            ('tcp://127.0.0.1:12345', 'tcp://127.0.0.1:12345', {
                'ip': (4, 2130706433),
                'port': 12345,
                'proto': 'tcp',
            }),
            ('tcp://127.0.0.1', 'tcp://127.0.0.1', {
                'ip': (4, 2130706433),
                'proto': 'tcp',
            }),
            ('tcp://[::1]:12345', 'tcp://[::1]:12345', {
                'ip': (6, 1),
                'port': 12345,
                'proto': 'tcp',
            }),
        )

        async with self.getTestCore() as core:
            for valu, expected_valu, expected_props in data:
                nodes = await core.nodes('[inet:client=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, ('inet:client', expected_valu))
                for p, v in expected_props.items():
                    self.eq(node.get(p), v)

    async def test_email(self):
        formname = 'inet:email'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {
                            'fqdn': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                                'domain': (t.fqdntype.typehash, 'link', {'subs': {
                                    'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                                    'issuffix': (t.fqdntype.booltype.typehash, 1, {})}}),
                                'host': (t.fqdntype.hosttype.typehash, 'vertex', {})}}),
                            'user': (t.usertype.typehash, 'unittest', {})}})
            self.eq(await t.norm(email), expected)

            valu = (await t.norm('bob\udcfesmith@woot.com'))[0]

            with self.raises(s_exc.BadTypeValu) as cm:
                await t.norm('hehe')
            self.isin('Email address expected in <user>@<fqdn> format', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                await t.norm('hehe@1.2.3.4')
            self.isin('FQDN Got an IP address instead', cm.exception.get('mesg'))

            # Form Tests ======================================================
            valu = 'UnitTest@Vertex.link'
            expected_ndef = (formname, valu.lower())
            expected_props = {
                'fqdn': 'vertex.link',
                'user': 'unittest',
            }

            nodes = await core.nodes('[inet:email=UnitTest@Vertex.link]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:email', 'unittest@vertex.link'))
            self.propeq(node, 'fqdn', 'vertex.link')
            self.propeq(node, 'user', 'unittest')

            nodes = await core.nodes('[ inet:email=visi+Synapse@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi+synapse@vertex.link')
            self.propeq(nodes[0], 'user', 'visi+synapse')
            self.propeq(nodes[0], 'plus', 'synapse')
            self.propeq(nodes[0], 'base', 'visi@vertex.link')
            self.len(1, await core.nodes('inet:email=visi+synapse@vertex.link :base -> inet:email +inet:email=visi@vertex.link'))

            nodes = await core.nodes('[ inet:email=visi++Synapse@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi++synapse@vertex.link')
            self.propeq(nodes[0], 'user', 'visi++synapse')
            self.propeq(nodes[0], 'plus', '+synapse')
            self.propeq(nodes[0], 'base', 'visi@vertex.link')
            self.len(1, await core.nodes('inet:email=visi++synapse@vertex.link :base -> inet:email +inet:email=visi@vertex.link'))

            nodes = await core.nodes('[ inet:email=visi+Synapse+foo@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi+synapse+foo@vertex.link')
            self.propeq(nodes[0], 'user', 'visi+synapse+foo')
            self.propeq(nodes[0], 'plus', 'synapse+foo')
            self.propeq(nodes[0], 'base', 'visi@vertex.link')
            self.len(1, await core.nodes('inet:email=visi+synapse+foo@vertex.link :base -> inet:email +inet:email=visi@vertex.link'))

            nodes = await core.nodes('[ inet:email=visi+@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi+@vertex.link')
            self.propeq(nodes[0], 'user', 'visi+')
            self.propeq(nodes[0], 'plus', '')
            self.propeq(nodes[0], 'base', 'visi@vertex.link')
            self.len(1, await core.nodes('inet:email=visi+@vertex.link :base -> inet:email +inet:email=visi@vertex.link'))

            nodes = await core.nodes('[ inet:email=+@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '+@vertex.link')
            self.propeq(nodes[0], 'user', '+')
            self.propeq(nodes[0], 'plus', '')
            self.propeq(nodes[0], 'base', '@vertex.link')
            self.len(1, await core.nodes('inet:email="+@vertex.link" :base -> inet:email +inet:email="@vertex.link"'))

            nodes = await core.nodes('[ inet:email=++@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '++@vertex.link')
            self.propeq(nodes[0], 'user', '++')
            self.propeq(nodes[0], 'plus', '+')
            self.propeq(nodes[0], 'base', '@vertex.link')
            self.len(1, await core.nodes('inet:email="++@vertex.link" :base -> inet:email +inet:email="@vertex.link"'))

            nodes = await core.nodes('[ inet:email=+++@vertex.link ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '+++@vertex.link')
            self.propeq(nodes[0], 'user', '+++')
            self.propeq(nodes[0], 'plus', '++')
            self.propeq(nodes[0], 'base', '@vertex.link')
            self.len(1, await core.nodes('inet:email="+++@vertex.link" :base -> inet:email +inet:email="@vertex.link"'))

    async def test_flow(self):
        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ inet:flow=*

                    :period=(20250701, 20250702)

                    :server=1.2.3.4:443
                    :server:host=*
                    :server:proc=*
                    :server:txcount=33
                    :server:txbytes=2
                    :server:handshake="OHai!"
                    :server:txfiles={[ file:attachment=* :path=bar.exe ]}
                    :server:softnames=(FooBar, bazfaz)
                    :server:cpes=("cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*", "cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*")

                    :client=5.5.5.5
                    :client:host=*
                    :client:proc=*
                    :client:txcount=30
                    :client:txbytes=1
                    :client:handshake="Hello There"
                    :client:txfiles={[ file:attachment=* :path=foo.exe ]}
                    :client:softnames=(HeHe, haha)
                    :client:cpes=("cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*", "cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*")

                    :tot:txcount=63
                    :tot:txbytes=3

                    :ip:proto=6
                    :ip:tcp:flags=(0x20)

                    :sandbox:file=*
                    :capture:host=*
                ]
            ''')

            self.len(1, nodes)
            self.propeq(nodes[0], 'client', 'tcp://5.5.5.5')
            self.propeq(nodes[0], 'client:txcount', 30)
            self.propeq(nodes[0], 'client:txbytes', 1)
            self.propeq(nodes[0], 'client:handshake', 'Hello There')
            self.propeq(nodes[0], 'client:softnames', ('haha', 'hehe'))
            self.propeq(nodes[0], 'client:cpes', ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)

            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:443')
            self.propeq(nodes[0], 'server:txcount', 33)
            self.propeq(nodes[0], 'server:txbytes', 2)
            self.propeq(nodes[0], 'server:handshake', 'OHai!')
            self.propeq(nodes[0], 'server:softnames', ('bazfaz', 'foobar'))
            self.propeq(nodes[0], 'server:cpes', ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)

            self.propeq(nodes[0], 'tot:txcount', 63)
            self.propeq(nodes[0], 'tot:txbytes', 3)
            self.propeq(nodes[0], 'ip:proto', 6)
            self.propeq(nodes[0], 'ip:tcp:flags', 0x20)

            self.len(1, await core.nodes('inet:flow :client:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :server:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :client:proc -> it:exec:proc'))
            self.len(1, await core.nodes('inet:flow :server:proc -> it:exec:proc'))

            self.len(1, await core.nodes('inet:flow :client:txfiles -> file:attachment +:path=foo.exe'))
            self.len(1, await core.nodes('inet:flow :server:txfiles -> file:attachment +:path=bar.exe'))

            self.len(1, await core.nodes('inet:flow :capture:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :sandbox:file -> file:bytes'))

    async def test_fqdn(self):
        formname = 'inet:fqdn'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            fqdn = 'example.Vertex.link'
            expected = ('example.vertex.link', {'subs': {
                'host': (t.hosttype.typehash, 'example', {}),
                'domain': (t.typehash, 'vertex.link', {'subs': {
                    'host': (t.hosttype.typehash, 'vertex', {}),
                    'domain': (t.typehash, 'link', {'subs': {
                        'host': (t.hosttype.typehash, 'link', {}),
                        'issuffix': (t.booltype.typehash, 1, {}),
                    }}),
                }}),
            }})
            self.eq(await t.norm(fqdn), expected)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('!@#$%'))

            # defanging works
            self.eq(await t.norm('example[.]vertex(.)link'), expected)

            # Demonstrate Valid IDNA
            fqdn = 'tèst.èxamplè.link'
            ex_fqdn = 'xn--tst-6la.xn--xampl-3raf.link'
            expected = (ex_fqdn, {'subs': {
                'domain': (t.typehash, 'xn--xampl-3raf.link', {'subs': {
                    'host': (t.hosttype.typehash, 'xn--xampl-3raf', {}),
                    'domain': (t.typehash, 'link', {'subs': {
                        'host': (t.hosttype.typehash, 'link', {}),
                        'issuffix': (t.booltype.typehash, 1, {}),
                    }}),
                }}),
                'host': (t.hosttype.typehash, 'xn--tst-6la', {})}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)  # Calling repr on IDNA encoded domain should result in the unicode

            # Use IDNA2008 if possible
            fqdn = "faß.de"
            ex_fqdn = 'xn--fa-hia.de'
            expected = (ex_fqdn, {'subs': {
                'domain': (t.typehash, 'de', {'subs': {
                    'host': (t.hosttype.typehash, 'de', {}),
                    'issuffix': (t.booltype.typehash, 1, {}),
                }}),
                'host': (t.hosttype.typehash, 'xn--fa-hia', {})}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Emojis are valid IDNA2003
            fqdn = '👁👄👁.fm'
            ex_fqdn = 'xn--mp8hai.fm'
            expected = (ex_fqdn, {'subs': {
                'domain': (t.typehash, 'fm', {'subs': {
                    'host': (t.hosttype.typehash, 'fm', {}),
                    'issuffix': (t.booltype.typehash, 1, {}),
                }}),
                'host': (t.hosttype.typehash, 'xn--mp8hai', {})}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Variant forms get normalized
            varfqdn = '👁️👄👁️.fm'
            self.eq(await t.norm(varfqdn), expected)
            self.ne(varfqdn, fqdn)

            # Unicode full stops are okay but get normalized
            fqdn = 'foo(．)bar[。]baz｡lol'
            ex_fqdn = 'foo.bar.baz.lol'
            expected = (ex_fqdn, {'subs': {
                'domain': (t.typehash, 'bar.baz.lol', {'subs': {
                    'host': (t.hosttype.typehash, 'bar', {}),
                    'domain': (t.typehash, 'baz.lol', {'subs': {
                        'host': (t.hosttype.typehash, 'baz', {}),
                        'domain': (t.typehash, 'lol', {'subs': {
                            'host': (t.hosttype.typehash, 'lol', {}),
                            'issuffix': (t.booltype.typehash, 1, {}),
                        }}),
                    }}),
                }}),
                'host': (t.hosttype.typehash, 'foo', {})}})
            self.eq(await t.norm(fqdn), expected)

            # Ellipsis shouldn't make it through
            await self.asyncraises(s_exc.BadTypeValu, t.norm('vertex…link'))

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {
                'host': (t.hosttype.typehash, fqdn.split('.')[0], {}),
                'domain': (t.typehash, 'link', {'subs': {
                    'host': (t.hosttype.typehash, 'link', {}),
                    'issuffix': (t.booltype.typehash, 1, {}),
                }}),
            }})
            self.eq(await t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))  # UnicodeError raised and caught and fallback to norm

            fqdn = 'xn--cc.bartmp.l.google.com'
            expected = (fqdn, {'subs': {
                'host': (t.hosttype.typehash, fqdn.split('.')[0], {}),
                'domain': (t.typehash, 'bartmp.l.google.com', {'subs': {
                    'host': (t.hosttype.typehash, 'bartmp', {}),
                    'domain': (t.typehash, 'l.google.com', {'subs': {
                        'host': (t.hosttype.typehash, 'l', {}),
                        'domain': (t.typehash, 'google.com', {'subs': {
                            'host': (t.hosttype.typehash, 'google', {}),
                            'domain': (t.typehash, 'com', {'subs': {
                                'host': (t.hosttype.typehash, 'com', {}),
                                'issuffix': (t.booltype.typehash, 1, {}),
                            }}),
                        }}),
                    }}),
                }}),
            }})
            self.eq(await t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))

            await self.asyncraises(s_exc.BadTypeValu, t.norm('www.google\udcfesites.com'))

            # IP addresses are NOT valid FQDNs
            await self.asyncraises(s_exc.BadTypeValu, t.norm('1.2.3.4'))

            # Form Tests ======================================================

            # Demonstrate cascading formation
            nodes = await core.nodes('[inet:fqdn=api.vertex.link]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:fqdn', 'api.vertex.link'))
            self.propeq(node, 'domain', 'vertex.link')
            self.propeq(node, 'host', 'api')
            self.propeq(node, 'issuffix', 0)
            self.propeq(node, 'iszone', 0)
            self.propeq(node, 'zone', 'vertex.link')

            nodes = await core.nodes('inet:fqdn=vertex.link')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:fqdn', 'vertex.link'))
            self.propeq(node, 'domain', 'link')
            self.propeq(node, 'host', 'vertex')
            self.propeq(node, 'issuffix', 0)
            self.propeq(node, 'iszone', 1)
            self.propeq(node, 'zone', 'vertex.link')

            nodes = await core.nodes('inet:fqdn=link')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:fqdn', 'link'))
            self.propeq(node, 'host', 'link')
            self.propeq(node, 'issuffix', 1)
            self.propeq(node, 'iszone', 0)
            # Demonstrate wildcard
            self.len(3, await core.nodes('inet:fqdn="*"'))
            self.len(3, await core.nodes('inet:fqdn="*link"'))
            self.len(2, await core.nodes('inet:fqdn="*.link"'))
            self.len(1, await core.nodes('inet:fqdn="*.vertex.link"'))
            with self.raises(s_exc.BadLiftValu):
                await core.nodes('inet:fqdn=api.*.link')

            q = 'inet:fqdn="*.link" +inet:fqdn="*vertex.link"'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq({'vertex.link', 'api.vertex.link'}, {n.ndef[1] for n in nodes})

            q = 'inet:fqdn~=api'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq({'api.vertex.link'}, {n.ndef[1] for n in nodes})

            # Cannot filter on a empty string
            q = 'inet:fqdn="*.link" +inet:fqdn=""'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # Recursion depth test
            fqdn = '.'.join(['x' for x in range(150)]) + '.foo.com'
            q = f'[ inet:fqdn="{fqdn}"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.propeq(nodes[0], 'zone', 'foo.com')

            nodes = await core.nodes('[inet:fqdn=vertex.link :seen=(2020,2021)]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'seen', (1577836800000000, 1609459200000000, 31622400000000))

            self.len(1, await core.nodes('[ inet:fqdn=vertex.link +(uses)> {[ meta:technique=* ]} ]'))

    async def test_fqdn_suffix(self):
        # Demonstrate FQDN suffix/zone behavior

        formname = 'inet:fqdn'

        def iszone(node):
            self.true(node.get('iszone') == 1 and node.get('issuffix') == 0)

        def issuffix(node):
            self.true(node.get('issuffix') == 1 and node.get('iszone') == 0)

        def isboth(node):
            self.true(node.get('iszone') == 1 and node.get('issuffix') == 1)

        def isneither(node):
            self.true(node.get('iszone') == 0 and node.get('issuffix') == 0)

        async with self.getTestCore() as core:
            # Create some nodes and demonstrate zone/suffix behavior
            # Only FQDNs of the lowest level should be suffix
            # Only FQDNs whose domains are suffixes should be zones
            nodes = await core.nodes('[inet:fqdn=abc.vertex.link]')
            n0 = nodes[0]
            nodes = await core.nodes('[inet:fqdn=def.vertex.link]')
            n1 = nodes[0]
            nodes = await core.nodes('[inet:fqdn=g.def.vertex.link]')
            n2 = nodes[0]
            # form again to show g. should not make this a zone
            nodes = await core.nodes('[inet:fqdn=def.vertex.link]')
            n1 = nodes[0]
            nodes = await core.nodes('[inet:fqdn=vertex.link]')
            n3 = nodes[0]
            nodes = await core.nodes('[inet:fqdn=link]')
            n4 = nodes[0]

            isneither(n0)
            isneither(n1)
            isneither(n2)
            iszone(n3)     # vertex.link should be a zone
            issuffix(n4)   # link should be a suffix

            # Make one of the FQDNs a suffix and make sure its children become zones
            nodes = await core.nodes('[inet:fqdn=vertex.link :issuffix=$lib.true]')
            n3 = nodes[0]

            isboth(n3)     # vertex.link should now be both because we made it a suffix

            nodes = await core.nodes('inet:fqdn=abc.vertex.link')
            n0 = nodes[0]
            nodes = await core.nodes('inet:fqdn=def.vertex.link')
            n1 = nodes[0]
            nodes = await core.nodes('inet:fqdn=g.def.vertex.link')
            n2 = nodes[0]
            iszone(n0)     # now a zone because vertex.link is a suffix
            iszone(n1)     # now a zone because vertex.link is a suffix
            isneither(n2)  # still neither as parent is not a suffix

            # Remove the FQDN's suffix status and make sure its children lose zone status
            nodes = await core.nodes('[inet:fqdn=vertex.link :issuffix=$lib.false]')
            n3 = nodes[0]
            iszone(n3)     # vertex.link should now be a zone because we removed its suffix status
            nodes = await core.nodes('inet:fqdn=abc.vertex.link')
            n0 = nodes[0]
            nodes = await core.nodes('inet:fqdn=def.vertex.link')
            n1 = nodes[0]
            nodes = await core.nodes('inet:fqdn=g.def.vertex.link')
            n2 = nodes[0]
            nodes = await core.nodes('inet:fqdn=link')
            n4 = nodes[0]

            isneither(n0)  # loses zone status
            isneither(n1)  # loses zone status
            isneither(n2)  # stays the same
            issuffix(n4)   # stays the same

    async def test_http_cookie(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:cookie="HeHe=HaHa"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:cookie', 'HeHe=HaHa'))
            self.propeq(node, 'name', 'HeHe')
            self.propeq(node, 'value', 'HaHa')

            nodes = await core.nodes('''
                [ inet:http:request=* :cookies={[ inet:http:cookie="foo=bar; baz=faz;" ]} ]
            ''')
            self.propeq(nodes[0], 'cookies', ('baz=faz', 'foo=bar'))

            nodes = await core.nodes('''
                [ inet:http:session=* :cookies={[ inet:http:cookie="foo=bar; baz=faz;" ]} ]
            ''')
            self.propeq(nodes[0], 'cookies', ('baz=faz', 'foo=bar'))

            nodes = await core.nodes('[ inet:http:cookie=(lol, lul) ]')
            self.len(2, nodes)

    async def test_http_request_header(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:request:header=(Cool, Cooler) :seen=2022]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:request:header', ('cool', 'Cooler')))
            self.propeq(node, 'name', 'cool')
            self.propeq(node, 'value', 'Cooler')
            self.nn(node.get('seen'))

    async def test_http_response_header(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:response:header=(Cool, Cooler)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:response:header', ('cool', 'Cooler')))
            self.propeq(node, 'name', 'cool')
            self.propeq(node, 'value', 'Cooler')

    async def test_http_param(self):
        async with self.getTestCore() as core:
            async with self.getTestCore() as core:
                nodes = await core.nodes('[inet:http:param=(Cool, Cooler)]')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, ('inet:http:param', ('Cool', 'Cooler')))
                self.propeq(node, 'name', 'cool')
                self.propeq(node, 'value', 'Cooler')

    async def test_http_request(self):

        async with self.getTestCore() as core:
            sess = s_common.guid()
            client = s_common.guid()
            server = s_common.guid()
            flow = s_common.guid()
            iden = s_common.guid()
            body = s_common.guid()
            sand = s_common.guid()

            props = {
                'body': body,
                'flow': flow,
                'sess': sess,
                'client:host': client,
                'server:host': server,
                'sandbox:file': sand,
            }
            q = '''[inet:http:request=$valu
                :time=2015
                :flow=$p.flow
                :method=gEt
                :query="hoho=1&qaz=bar"
                :path="/woot/hehe/"
                :body=$p.body
                :headers=((foo, bar),)
                :header:host=vertex.link
                :header:referer="https://google.com?s=awesome"
                :response:code=200
                :response:reason=OK
                :response:headers=((baz, faz),)
                :response:body=$p.body
                :client=1.2.3.4
                :client:host=$p."client:host"
                :server="5.5.5.5:443"
                :server:host=$p."server:host"
                :session=$p.sess
                :sandbox:file=$p."sandbox:file"
                ]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': iden, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:request', iden))
            self.propeq(node, 'time', 1420070400000000)
            self.propeq(node, 'flow', flow)
            self.propeq(node, 'method', 'gEt')
            self.propeq(node, 'query', 'hoho=1&qaz=bar')
            self.propeq(node, 'path', '/woot/hehe/')
            self.propeq(node, 'body', body)
            self.propeq(node, 'header:host', 'vertex.link')
            self.propeq(node, 'header:referer', 'https://google.com?s=awesome')
            self.propeq(node, 'response:code', 200)
            self.propeq(node, 'response:reason', 'OK')
            self.propeq(node, 'response:headers', (('baz', 'faz'),))
            self.propeq(node, 'response:body', body)
            self.propeq(node, 'session', sess)
            self.propeq(node, 'sandbox:file', sand)
            self.propeq(node, 'client', 'tcp://1.2.3.4')
            self.propeq(node, 'client:host', client)
            self.propeq(node, 'server', 'tcp://5.5.5.5:443')
            self.propeq(node, 'server:host', server)

            self.len(1, await core.nodes('inet:http:request -> inet:http:request:header'))
            self.len(1, await core.nodes('inet:http:request -> inet:http:response:header'))

            nodes = await core.nodes('inet:http:request -> inet:http:session [ :contact=* ]')
            self.len(1, nodes)
            self.nn(nodes[0].get('contact'))

    async def test_iface(self):
        async with self.getTestCore() as core:
            netw = s_common.guid()
            host = s_common.guid()
            valu = s_common.guid()
            props = {
                'host': host,
                'network': netw
            }
            q = '''[(inet:iface=$valu
                :host=$p.host
                :network=$p.network
                :type=Cool
                :mac="ff:00:ff:00:ff:00"
                :ip=1.2.3.4
                :phone=12345678910
                :wifi:ap:ssid="hehe haha"
                :wifi:ap:bssid="00:ff:00:ff:00:ff"
                :mob:imei=123456789012347
                :mob:imsi=12345678901234
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:iface', valu))
            self.propeq(node, 'host', host)
            self.propeq(node, 'network', netw)
            self.propeq(node, 'type', 'cool.')
            self.propeq(node, 'mac', 'ff:00:ff:00:ff:00')
            self.propeq(node, 'ip', (4, 0x01020304))
            self.propeq(node, 'phone', '12345678910')
            self.propeq(node, 'wifi:ap:ssid', 'hehe haha')
            self.propeq(node, 'wifi:ap:bssid', '00:ff:00:ff:00:ff')
            self.propeq(node, 'mob:imei', 123456789012347)
            self.propeq(node, 'mob:imsi', 12345678901234)

    async def test_ipv4(self):
        formname = 'inet:ip'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)
            ip_tup = (4, 16909060)
            ip_str = '1.2.3.4'
            ip_str_enfanged = '1[.]2[.]3[.]4'
            ip_str_enfanged2 = '1(.)2(.)3(.)4'
            ip_str_unicode = '1\u200b.\u200b2\u200b.\u200b3\u200b.\u200b4'

            info = {'subs': {'type': (t.typetype.typehash, 'unicast', {}),
                             'version': (t.verstype.typehash, 4, {})}}
            self.eq(await t.norm(ip_tup), (ip_tup, info))
            self.eq(await t.norm(ip_str), (ip_tup, info))
            self.eq(await t.norm(ip_str_enfanged), (ip_tup, info))
            self.eq(await t.norm(ip_str_enfanged2), (ip_tup, info))
            self.eq(await t.norm(ip_str_unicode), (ip_tup, info))
            self.eq(t.repr(ip_tup), ip_str)

            # Link local test
            ip_str = '169.254.1.1'
            norm, info = await t.norm(ip_str)
            self.eq((4, 2851995905), norm)
            self.eq(info.get('subs').get('type')[1], 'linklocal')

            norm, info = await t.norm('100.63.255.255')
            self.eq(info.get('subs').get('type')[1], 'unicast')

            norm, info = await t.norm('100.64.0.0')
            self.eq(info.get('subs').get('type')[1], 'shared')

            norm, info = await t.norm('100.127.255.255')
            self.eq(info.get('subs').get('type')[1], 'shared')

            norm, info = await t.norm('100.128.0.0')
            self.eq(info.get('subs').get('type')[1], 'unicast')

            # Don't allow invalid values
            with self.raises(s_exc.BadTypeValu):
                await t.norm(0x00000000 - 1)

            with self.raises(s_exc.BadTypeValu):
                await t.norm(0xFFFFFFFF + 1)

            with self.raises(s_exc.BadTypeValu):
                await t.norm('foo-bar.com')

            with self.raises(s_exc.BadTypeValu):
                await t.norm('bar.com')

            with self.raises(s_exc.BadTypeValu):
                await t.norm((1, 2, 3))

            with self.raises(s_exc.BadTypeValu):
                await t.norm((4, -1))

            with self.raises(s_exc.BadTypeValu):
                await t.norm((6, -1))

            with self.raises(s_exc.BadTypeValu):
                await t.norm((7, 1))

            with self.raises(s_exc.BadTypeValu):
                t.repr((7, 1))

            # Form Tests ======================================================
            nodes = await core.nodes('''
                [ inet:ip=1.2.3.4

                    :asn=3
                    :dns:rev=vertex.link

                    :place=*
                    :place:loc=us
                    :place:latlong=(-50.12345, 150.56789)
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))
            self.propeq(nodes[0], 'asn', 3)
            self.propeq(nodes[0], 'type', 'unicast')
            self.propeq(nodes[0], 'dns:rev', 'vertex.link')
            self.propeq(nodes[0], 'place:loc', 'us')
            self.propeq(nodes[0], 'place:latlong', (-50.12345, 150.56789))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 :place -> geo:place'))

            # > / < lifts and filters
            self.len(4, await core.nodes('[inet:ip=0.0.0.0 inet:ip=0.0.0.1 inet:ip=0.0.0.2 inet:ip=0.0.0.3]'))
            # Lifts
            self.len(0, await core.nodes('inet:ip<0.0.0.0'))
            self.len(1, await core.nodes('inet:ip<=0.0.0.0'))
            self.len(1, await core.nodes('inet:ip<0.0.0.1'))
            self.len(3, await core.nodes('inet:ip<=0.0.0.2'))
            self.len(2, await core.nodes('inet:ip>0.0.0.2'))
            self.len(3, await core.nodes('inet:ip>=0.0.0.2'))
            self.len(0, await core.nodes('inet:ip>=255.0.0.1'))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:ip>=$foo', {'vars': {'foo': 0xFFFFFFFF + 1}})
            # Filters
            self.len(0, await core.nodes('.created +inet:ip<0.0.0.0'))
            self.len(1, await core.nodes('.created +inet:ip<0.0.0.1'))
            self.len(3, await core.nodes('.created +inet:ip<=0.0.0.2'))
            self.len(2, await core.nodes('.created +inet:ip>0.0.0.2'))
            self.len(3, await core.nodes('.created +inet:ip>=0.0.0.2'))
            self.len(0, await core.nodes('.created +inet:ip>=255.0.0.1'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo-bar.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo-bar-duck.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=3.87/nice/index.php]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=3.87/33]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo"] [inet:ip=$node.value()]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo-bar.com"] [inet:ip=$node.value()]')

            self.len(0, await core.nodes('[inet:ip?=foo]'))
            self.len(0, await core.nodes('[inet:ip?=foo-bar.com]'))

            self.len(0, await core.nodes('[test:str="foo"] [inet:ip?=$node.value()] -test:str'))
            self.len(0, await core.nodes('[test:str="foo-bar.com"] [inet:ip?=$node.value()] -test:str'))

            q = '''init { $l = () }
            [inet:ip=192.0.0.9 inet:ip=192.0.0.0 inet:ip=192.0.0.255] $l.append(:type)
            fini { return ( $l ) }'''
            resp = await core.callStorm(q)
            self.eq(resp, ['unicast', 'private', 'private'])

            nodes = await core.nodes('[inet:ip=1.2.3.4 :seen=(2020,2021)]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'seen', (1577836800000000, 1609459200000000, 31622400000000))

    async def test_ipv6(self):
        formname = 'inet:ip'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            info = {'subs': {'type': (t.typetype.typehash, 'loopback', {}),
                             'scope': (t.scopetype.typehash, 'link-local', {}),
                             'version': (t.verstype.typehash, 6, {})}}
            self.eq(await t.norm('::1'), ((6, 1), info))
            self.eq(await t.norm('0:0:0:0:0:0:0:1'), ((6, 1), info))

            addrnorm = (6, 0xff010000000000000000000000000001)
            info = {'subs': {'type': (t.typetype.typehash, 'multicast', {}),
                             'scope': (t.scopetype.typehash, 'interface-local', {}),
                             'version': (t.verstype.typehash, 6, {})}}
            self.eq(await t.norm('ff01::1'), (addrnorm, info))

            addrnorm = (6, 0x20010db8000000000000ff0000428329)
            info = {'subs': {'type': (t.typetype.typehash, 'private', {}),
                             'scope': (t.scopetype.typehash, 'global', {}),
                             'version': (t.verstype.typehash, 6, {})}}
            self.eq(await t.norm('2001:0db8:0000:0000:0000:ff00:0042:8329'), (addrnorm, info))
            self.eq(await t.norm('2001:0db8:0000:0000:0000:ff00:0042\u200b:8329'), (addrnorm, info))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('newp'))

            # Specific examples given in RFC5952
            addrnorm = (6, 0x20010db8000000000001000000000001)
            self.eq((await t.norm('2001:db8:0:0:1:0:0:1'))[0], addrnorm)
            self.eq((await t.norm('2001:0db8:0:0:1:0:0:1'))[0], addrnorm)
            self.eq((await t.norm('2001:db8::1:0:0:1'))[0], addrnorm)
            self.eq((await t.norm('2001:db8::0:1:0:0:1'))[0], addrnorm)
            self.eq((await t.norm('2001:0db8::1:0:0:1'))[0], addrnorm)
            self.eq((await t.norm('2001:db8:0:0:1::1'))[0], addrnorm)
            self.eq((await t.norm('2001:DB8:0:0:1::1'))[0], addrnorm)
            self.eq((await t.norm('2001:DB8:0:0:1:0000:0000:1'))[0], addrnorm)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('::1::'))
            self.eq((await t.norm('2001:0db8::0001'))[0], (6, 0x20010db8000000000000000000000001))
            self.eq((await t.norm('2001:db8:0:0:0:0:2:1'))[0], (6, 0x20010db8000000000000000000020001))
            self.eq((await t.norm('2001:db8:0:1:1:1:1:1'))[0], (6, 0x20010db8000000010001000100010001))
            self.eq((await t.norm('2001:0:0:1:0:0:0:1'))[0], (6, 0x20010000000000010000000000000001))
            self.eq((await t.norm('2001:db8:0:0:1:0:0:1'))[0], (6, 0x20010db8000000000001000000000001))
            self.eq((await t.norm('::ffff:1.2.3.4'))[0], (6, 0xffff01020304))
            self.eq((await t.norm('2001:db8::0:1'))[0], (6, 0x20010db8000000000000000000000001))
            self.eq((await t.norm('2001:db8:0:0:0:0:2:1'))[0], (6, 0x20010db8000000000000000000020001))
            self.eq((await t.norm('2001:db8::'))[0], (6, 0x20010db8000000000000000000000000))

            # Link local test
            ip_str = 'fe80::1'
            norm, info = await t.norm(ip_str)
            self.eq(norm, (6, 0xfe800000000000000000000000000001))
            self.eq(info.get('subs').get('type')[1], 'linklocal')

            # Form Tests ======================================================

            nodes = await core.nodes('[ inet:ip="::fFfF:1.2.3.4" ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (6, 0xffff01020304)))

            nodes = await core.nodes('[inet:ip="::1"]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (6, 1)))

            self.len(1, await core.nodes('inet:ip=0::1'))
            self.len(1, await core.nodes('inet:ip*range=(0::1, 0::1)'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo-bar.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=foo-bar-duck.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo"] [inet:ip=$node.value()]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo-bar.com"] [inet:ip=$node.value()]')

            self.len(0, await core.nodes('[inet:ip?=foo]'))
            self.len(0, await core.nodes('[inet:ip?=foo-bar.com]'))

            self.len(0, await core.nodes('[test:str="foo"] [inet:ip?=$node.value()] -test:str'))
            self.len(0, await core.nodes('[test:str="foo-bar.com"] [inet:ip?=$node.value()] -test:str'))

            await core.nodes('[ inet:ip=2a00:: inet:ip=2a00::1 ]')

            self.len(1, await core.nodes('inet:ip>2a00::'))
            self.len(2, await core.nodes('inet:ip>=2a00::'))
            self.len(2, await core.nodes('inet:ip<2a00::'))
            self.len(3, await core.nodes('inet:ip<=2a00::'))
            self.len(0, await core.nodes('inet:ip>ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'))

            self.len(1, await core.nodes('inet:ip +inet:ip>2a00::'))
            self.len(2, await core.nodes('inet:ip +inet:ip>=2a00::'))
            self.len(2, await core.nodes('inet:ip +inet:ip<2a00::'))
            self.len(3, await core.nodes('inet:ip +inet:ip<=2a00::'))

    async def test_ipv6_lift_range(self):

        async with self.getTestCore() as core:

            for i in range(5):
                valu = f'0::f00{i}'
                nodes = await core.nodes('[inet:ip=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)

            self.len(3, await core.nodes('inet:ip=0::f001-0::f003'))
            self.len(3, await core.nodes('[inet:ip=0::f001-0::f003]'))
            self.len(3, await core.nodes('inet:ip +inet:ip=0::f001-0::f003'))
            self.len(3, await core.nodes('inet:ip*range=(0::f001, 0::f003)'))

    async def test_ipv6_filt_cidr(self):

        async with self.getTestCore() as core:

            self.len(5, await core.nodes('[ inet:ip=0::f000/126 inet:ip=0::ffff:a2c4 ]'))
            self.len(4, await core.nodes('inet:ip +inet:ip=0::f000/126'))
            self.len(1, await core.nodes('inet:ip -inet:ip=0::f000/126'))

            self.len(256, await core.nodes('[ inet:ip=0::ffff:192.168.1.0/120]'))
            self.len(256, await core.nodes('[ inet:ip=0::ffff:192.168.2.0/120]'))
            self.len(256, await core.nodes('inet:ip=0::ffff:192.168.1.0/120'))

            # Seed some nodes for bounds checking
            vals = list(range(1, 33))
            q = 'for $v in $vals { [inet:ip=`0::10.2.1.{$v}` ] }'
            self.len(len(vals), await core.nodes(q, opts={'vars': {'vals': vals}}))

            nodes = await core.nodes('inet:ip=0::10.2.1.4/128')
            self.len(1, nodes)
            self.len(1, await core.nodes('inet:ip +inet:ip=0::10.2.1.4/128'))
            self.len(1, await core.nodes('inet:ip +inet:ip=0::10.2.1.4'))

            nodes = await core.nodes('inet:ip=0::10.2.1.4/127')
            self.len(2, nodes)
            self.len(2, await core.nodes('inet:ip +inet:ip=0::10.2.1.4/127'))

            # 0::10.2.1.0 -> 0::10.2.1.3 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=0::10.2.1.1/126')
            self.len(3, nodes)

            nodes = await core.nodes('inet:ip=0::10.2.1.2/126')
            self.len(3, nodes)

            # 0::10.2.1.0 -> 0::10.2.1.7 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=0::10.2.1.0/125')
            self.len(7, nodes)

            # 0::10.2.1.8 -> 0::10.2.1.15
            nodes = await core.nodes('inet:ip=0::10.2.1.8/125')
            self.len(8, nodes)

            # 0::10.2.1.0 -> 0::10.2.1.15 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ip=0::10.2.1.1/124')
            self.len(15, nodes)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:ip=0::10.2.1.1/300')

    async def test_mac(self):
        formname = 'inet:mac'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.eq(await t.norm('00:00:00:00:00:00'), ('00:00:00:00:00:00', {}))
            self.eq(await t.norm('FF:ff:FF:ff:FF:ff'), ('ff:ff:ff:ff:ff:ff', {}))
            self.eq(await t.norm(' FF:ff:FF:ff:FF:ff'), ('ff:ff:ff:ff:ff:ff', {}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('GG:ff:FF:ff:FF:ff'))

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:mac="00:00:00:00:00:00" :vendor=* :vendor:name=Cool]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:mac', '00:00:00:00:00:00'))
            self.propeq(node, 'vendor:name', 'cool')

            self.len(1, await core.nodes('inet:mac -> ou:org'))

    async def test_net4(self):
        tname = 'inet:net'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('1.2.3.4', '5.6.7.8')
            minsub = (t.subtype.typehash, (4, 16909060), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'version': (t.subtype.verstype.typehash, 4, {})}})

            maxsub = (t.subtype.typehash, (4, 84281096), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'version': (t.subtype.verstype.typehash, 4, {})}})

            expected = (((4, 16909060), (4, 84281096)), {
                'subs': {'min': minsub, 'max': maxsub},
                'virts': {'size': (67372037, 19)}
            })

            self.eq(await t.norm(valu), expected)

            valu = '1.2.3.4-5.6.7.8'
            norm = await t.norm(valu)
            self.eq(norm, expected)

            self.eq('1.2.3.4-5.6.7.8', t.repr(norm[0]))

            valu = '1.2.3.0/24'
            minsub = (t.subtype.typehash, (4, 0x01020300), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'version': (t.subtype.verstype.typehash, 4, {})}})

            maxsub = (t.subtype.typehash, (4, 0x010203ff), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'version': (t.subtype.verstype.typehash, 4, {})}})

            expected = (((4, 0x01020300), (4, 0x010203ff)), {
                'subs': {'min': minsub, 'max': maxsub},
                'virts': {'mask': (24, 2), 'size': (256, 19)}
            })
            self.eq(await t.norm(valu), expected)

            valu = '5.6.7.8-1.2.3.4'
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            valu = ('1.2.3.4', '5.6.7.8', '7.8.9.10')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/-1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/33'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/foo'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1'))

            # Form Tests ======================================================
            valu = '192[.]168.1.123/24'
            expected_ndef = ('inet:net', ((4, 3232235776), (4, 3232236031)))

            nodes = await core.nodes('[inet:net=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, expected_ndef)
            self.propeq(node, 'min', (4, 3232235776))  # 192.168.1.0
            self.propeq(node, 'max', (4, 3232236031))  # 192.168.1.255

            self.eq('192.168.1.0/24', await core.callStorm('inet:net return($node.repr())'))

            await core.nodes('[ inet:net=10.0.0.0/18 ]')

            self.len(1, await core.nodes('inet:net.mask=24'))
            self.len(1, await core.nodes('inet:net.mask>18'))
            self.len(2, await core.nodes('inet:net.mask>17'))
            self.len(1, await core.nodes('inet:net.size=256'))
            self.len(2, await core.nodes('inet:net.size>255'))
            self.len(1, await core.nodes('inet:net.size*in=(1, 256)'))
            self.len(2, await core.nodes('inet:net.size*in=(256, 16384)'))
            self.len(1, await core.nodes('inet:net.size*range=(1, 256)'))
            self.len(1, await core.nodes('inet:net.size*range=(1, 16383)'))
            self.len(2, await core.nodes('inet:net.size*range=(1, 16384)'))

            self.eq(16384, await core.callStorm('inet:net.size>256 return(.size)'))

            # Remove virts from a sode for coverage
            nodes = await core.nodes('inet:net.mask=24')
            valu = nodes[0].sodes[0]['valu']
            valu[2].pop('size')

            self.none(await core.callStorm('inet:net.mask=24 return(.size)'))

            nodes[0].sodes[0]['valu'] = (valu[0], valu[1], None)

            self.none(await core.callStorm('inet:net.mask=24 return(.mask)'))
            self.none(await core.callStorm('inet:net.mask=24 return(.size)'))

    async def test_net6(self):
        tname = 'inet:net'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('0:0:0:0:0:0:0:0', '::Ff')
            minsub = (t.subtype.typehash, (6, 0), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'private', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            maxsub = (t.subtype.typehash, (6, 255), {'subs': {
                        'type': (t.subtype.typetype.typehash, 'reserved', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            expected = (((6, 0), (6, 0xff)), {
                'subs': {'min': minsub, 'max': maxsub},
                'virts': {'mask': (120, 2), 'size': (256, 19)}
            })
            self.eq(await t.norm(valu), expected)

            valu = '0:0:0:0:0:0:0:0-::Ff'
            self.eq(await t.norm(valu), expected)

            # Test case in which ipaddress ordering is not alphabetical
            minv = (6, 0x33000100000000000000000000000000)
            maxv = (6, 0x3300010000010000000000000000ffff)
            valu = ('3300:100::', '3300:100:1::ffff')
            minsub = (t.subtype.typehash, minv, {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            maxsub = (t.subtype.typehash, maxv, {'subs': {
                        'type': (t.subtype.typetype.typehash, 'unicast', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            expected = ((minv, maxv), {
                'subs': {'min': minsub, 'max': maxsub},
                'virts': {'size': (1208925819614629174771712, 19)}
            })
            self.eq(await t.norm(valu), expected)

            minv = (6, 0x20010db8000000000000000000000000)
            maxv = (6, 0x20010db8000000000000000007ffffff)
            valu = '2001:db8::/101'
            minsub = (t.subtype.typehash, minv, {'subs': {
                        'type': (t.subtype.typetype.typehash, 'private', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            maxsub = (t.subtype.typehash, maxv, {'subs': {
                        'type': (t.subtype.typetype.typehash, 'private', {}),
                        'scope': (t.subtype.scopetype.typehash, 'global', {}),
                        'version': (t.subtype.verstype.typehash, 6, {})}})

            expected = ((minv, maxv), {
                'subs': {'min': minsub, 'max': maxsub},
                'virts': {'mask': (101, 2), 'size': (134217728, 19)}
            })
            self.eq(await t.norm(valu), expected)

            valu = ('fe00::', 'fd00::')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            valu = ('fd00::', 'fe00::', 'ff00::')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            with self.raises(s_exc.BadTypeValu):
                await t.norm(((6, 1), (4, 1)))

            valu = '2001:db8::/59'
            norm, info = await t.norm(valu)
            self.eq(norm, ((6, 0x20010db8000000000000000000000000), (6, 0x20010db80000001fffffffffffffffff)))
            self.eq(t.repr(norm), valu)
            self.eq(info['subs']['min'][1], (6, 0x20010db8000000000000000000000000))
            self.eq(info['subs']['max'][1], (6, 0x20010db80000001fffffffffffffffff))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:net=0::10.2.1.1/300')

            await core.nodes('''[
                inet:net=([[6, 0], [6, 0xfffffffffffffffffffffffffffffffe]])
                inet:net=([[6, 0], [6, 0]])
                inet:net=([[6, 0], [6, 0xff]])
                inet:net=([[6, 0], [6, 0xfe]])
            ]''')

            self.len(2, await core.nodes('inet:net -.mask'))
            self.len(2, await core.nodes('inet:net +.mask'))

            self.len(1, await core.nodes('inet:net.mask=128'))
            self.len(2, await core.nodes('inet:net.mask>18'))
            self.len(1, await core.nodes('inet:net.size=0xffffffffffffffffffffffffffffffff'))
            self.len(1, await core.nodes('inet:net.size=1'))
            self.len(3, await core.nodes('inet:net.size>254'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:net="::/0" ]')

    async def test_port(self):
        tname = 'inet:port'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(tname)
            await self.asyncraises(s_exc.BadTypeValu, t.norm(-1))
            self.eq(await t.norm(0), (0, {}))
            self.eq(await t.norm(1), (1, {}))
            self.eq(await t.norm('2'), (2, {}))
            self.eq(await t.norm('0xF'), (15, {}))
            self.eq(await t.norm(65535), (65535, {}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(65536))

    async def test_rfc2822_addr(self):
        formname = 'inet:rfc2822:addr'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            namesub = (t.metatype.typehash, 'foo bar', {})
            emailsub = (t.emailtype.typehash, 'visi@vertex.link', {'subs': {
                            'fqdn': (t.emailtype.fqdntype.typehash, 'vertex.link', {'subs': {
                                'host': (t.emailtype.fqdntype.hosttype.typehash, 'vertex', {}),
                                'domain': (t.emailtype.fqdntype.typehash, 'link', {'subs': {
                                    'host': (t.emailtype.fqdntype.hosttype.typehash, 'link', {}),
                                    'issuffix': (t.emailtype.fqdntype.booltype.typehash, 1, {}),
                                }}),
                            }}),
                            'user': (t.emailtype.usertype.typehash, 'visi', {})}})

            self.eq(await t.norm('FooBar'), ('foobar', {'subs': {}}))
            self.eq(await t.norm('visi@vertex.link'), ('visi@vertex.link', {'subs': {'email': emailsub}}))
            self.eq(await t.norm('foo bar<visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': emailsub, 'name': namesub}}))
            self.eq(await t.norm('foo bar <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': emailsub, 'name': namesub}}))
            self.eq(await t.norm('"foo bar "   <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': emailsub, 'name': namesub}}))
            self.eq(await t.norm('<visi@vertex.link>'), ('visi@vertex.link', {'subs': {'email': emailsub}}))

            valu = (await t.norm('bob\udcfesmith@woot.com'))[0]
            self.eq(valu, 'bob\udcfesmith@woot.com')

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:rfc2822:addr=$valu]',
                                     opts={'vars': {'valu': '"UnitTest"    <UnitTest@Vertex.link>'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:rfc2822:addr', 'unittest <unittest@vertex.link>'))
            self.propeq(node, 'email', 'unittest@vertex.link')
            self.propeq(node, 'name', 'unittest')

            await core.nodes('[inet:rfc2822:addr=$valu]', opts={'vars': {'valu': '"UnitTest1'}})
            await core.nodes('[inet:rfc2822:addr=$valu]', opts={'vars': {'valu': '"UnitTest12'}})

            self.len(3, await core.nodes('inet:rfc2822:addr^=unittest'))
            self.len(2, await core.nodes('inet:rfc2822:addr^=unittest1'))
            self.len(1, await core.nodes('inet:rfc2822:addr^=unittest12'))

            # CVE-2023-27043 related behavior
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:rfc2822:addr="alice@example.org]<bob@example.org>"]')

    async def test_server(self):
        formname = 'inet:server'
        data = (
            ('tcp://127.0.0.1:12345', 'tcp://127.0.0.1:12345', {
                'ip': (4, 2130706433),
                'port': 12345,
                'proto': 'tcp',
            }),
            ('tcp://127.0.0.1', 'tcp://127.0.0.1', {
                'ip': (4, 2130706433),
                'proto': 'tcp',
            }),
            ('tcp://[::1]:12345', 'tcp://[::1]:12345', {
                'ip': (6, 1),
                'port': 12345,
                'proto': 'tcp',
            }),
            ((4, 2130706433), 'tcp://127.0.0.1', {
                'ip': (4, 2130706433),
                'proto': 'tcp',
            }),
        )

        async with self.getTestCore() as core:
            for valu, expected_valu, props in data:
                nodes = await core.nodes('[inet:server=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, ('inet:server', expected_valu))
                for p, v in props.items():
                    self.eq(node.get(p), v)

            nodes = await core.nodes('[ it:network=* :dns:resolvers=(([4, 1]),)]')
            self.propeq(nodes[0], 'dns:resolvers', ('udp://0.0.0.1:53',))

            nodes = await core.nodes('it:network -> inet:server')
            self.propeq(nodes[0], 'ip', (4, 1))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=(([6, 1]),)]')
            self.propeq(nodes[0], 'dns:resolvers', ('udp://[::1]:53',))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=("::1",)]')
            self.propeq(nodes[0], 'dns:resolvers', ('udp://[::1]:53',))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=("[::1]",)]')
            self.propeq(nodes[0], 'dns:resolvers', ('udp://[::1]:53',))

            nodes = await core.nodes('[ inet:server=gre://::1 ]')
            self.propeq(nodes[0], 'proto', 'gre')

            nodes = await core.nodes('[ inet:server=gre://1.2.3.4 ]')
            self.propeq(nodes[0], 'proto', 'gre')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server=gre://1.2.3.4:99 ]')

            self.eq(ctx.exception.get('mesg'), 'Protocol gre does not allow specifying ports.')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server="gre://[::1]:99" ]')

            self.eq(ctx.exception.get('mesg'), 'Protocol gre does not allow specifying ports.')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server=newp://1.2.3.4:99 ]')

            self.eq(ctx.exception.get('mesg'), 'inet:sockaddr protocol must be one of: tcp,udp,icmp,gre')

            # todo: norm dict test

    async def test_url(self):
        formname = 'inet:url'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('http:///wat'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('wat'))  # No Protocol
            await self.asyncraises(s_exc.BadTypeValu, t.norm("file://''"))  # Missing address/url
            await self.asyncraises(s_exc.BadTypeValu, t.norm("file://#"))  # Missing address/url
            await self.asyncraises(s_exc.BadTypeValu, t.norm("file://$"))  # Missing address/url
            await self.asyncraises(s_exc.BadTypeValu, t.norm("file://%"))  # Missing address/url

            await self.asyncraises(s_exc.BadTypeValu, t.norm('www.google\udcfesites.com/hehe.asp'))

            for proto in ('http', 'hxxp', 'hXXp'):
                url = 'http://www.googlesites.com/hehe\udcfestuff.asp'
                valu = await t.norm(f'{proto}://www.googlesites.com/hehe\udcfestuff.asp')
                expected = (url, {'subs': {
                    'proto': (t.lowstrtype.typehash, 'http', {}),
                    'path': (t.strtype.typehash, '/hehe\udcfestuff.asp', {}),
                    'port': (t.porttype.typehash, 80, {}),
                    'params': (t.strtype.typehash, '', {}),
                    'fqdn': (t.fqdntype.typehash, 'www.googlesites.com', {'subs': {
                        'domain': (t.fqdntype.typehash, 'googlesites.com', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'googlesites', {}),
                            'domain': (t.fqdntype.typehash, 'com', {'subs': {
                                'host': (t.fqdntype.hosttype.typehash, 'com', {}),
                                'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                            }}),
                        }}),
                        'host': (t.fqdntype.hosttype.typehash, 'www', {})}}),
                    'base': (t.strtype.typehash, url, {}),
                }})
                self.eq(valu, expected)

            for proto in ('https', 'hxxps', 'hXXps'):
                url = f'https://dummyimage.com/600x400/000/fff.png&text=cat@bam.com'
                valu = await t.norm(f'{proto}://dummyimage.com/600x400/000/fff.png&text=cat@bam.com')
                expected = (url, {'subs': {
                    'base': (t.strtype.typehash, url, {}),
                    'proto': (t.lowstrtype.typehash, 'https', {}),
                    'path': (t.strtype.typehash, '/600x400/000/fff.png&text=cat@bam.com', {}),
                    'port': (t.porttype.typehash, 443, {}),
                    'params': (t.strtype.typehash, '', {}),
                    'fqdn': (t.fqdntype.typehash, 'dummyimage.com', {'subs': {
                        'domain': (t.fqdntype.typehash, 'com', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'com', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                        'host': (t.fqdntype.hosttype.typehash, 'dummyimage', {})}}),
                }})
                self.eq(valu, expected)

            ipsub = (t.iptype.typehash, (4, 0), {'subs': {
                        'type': (t.iptype.typetype.typehash, 'private', {}),
                        'version': (t.iptype.verstype.typehash, 4, {})}})

            url = 'http://0.0.0.0/index.html?foo=bar'
            valu = await t.norm(url)
            expected = (url, {'subs': {
                'proto': (t.lowstrtype.typehash, 'http', {}),
                'path': (t.strtype.typehash, '/index.html', {}),
                'params': (t.strtype.typehash, '?foo=bar', {}),
                'ip': ipsub,
                'port': (t.porttype.typehash, 80, {}),
                'base': (t.strtype.typehash, 'http://0.0.0.0/index.html', {}),
            }})
            self.eq(valu, expected)

            url = '  http://0.0.0.0/index.html?foo=bar  '
            valu = await t.norm(url)
            expected = (url.strip(), {'subs': {
                'proto': (t.lowstrtype.typehash, 'http', {}),
                'path': (t.strtype.typehash, '/index.html', {}),
                'params': (t.strtype.typehash, '?foo=bar', {}),
                'ip': ipsub,
                'port': (t.porttype.typehash, 80, {}),
                'base': (t.strtype.typehash, 'http://0.0.0.0/index.html', {}),
            }})
            self.eq(valu, expected)

            ipsub = (t.iptype.typehash, (6, 1), {'subs': {
                        'type': (t.iptype.typetype.typehash, 'loopback', {}),
                        'scope': (t.iptype.scopetype.typehash, 'link-local', {}),
                        'version': (t.iptype.verstype.typehash, 6, {})}})

            unc = '\\\\0--1.ipv6-literal.net\\share\\path\\to\\filename.txt'
            url = 'smb://::1/share/path/to/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'proto': (t.lowstrtype.typehash, 'smb', {}),
                'params': (t.strtype.typehash, '', {}),
                'path': (t.strtype.typehash, '/share/path/to/filename.txt', {}),
                'ip': ipsub,
            }})
            self.eq(valu, expected)

            unc = '\\\\0--1.ipv6-literal.net@1234\\share\\filename.txt'
            url = 'smb://[::1]:1234/share/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'proto': (t.lowstrtype.typehash, 'smb', {}),
                'path': (t.strtype.typehash, '/share/filename.txt', {}),
                'params': (t.strtype.typehash, '', {}),
                'port': (t.porttype.typehash, 1234, {}),
                'ip': ipsub,
            }})
            self.eq(valu, expected)

            unc = '\\\\server@SSL@1234\\share\\path\\to\\filename.txt'
            url = 'https://server:1234/share/path/to/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'proto': (t.lowstrtype.typehash, 'https', {}),
                'fqdn': (t.fqdntype.typehash, 'server', {'subs': {
                    'host': (t.fqdntype.hosttype.typehash, 'server', {}),
                    'issuffix': (t.fqdntype.booltype.typehash, 1, {})}}),
                'params': (t.strtype.typehash, '', {}),
                'port': (t.porttype.typehash, 1234, {}),
                'path': (t.strtype.typehash, '/share/path/to/filename.txt', {}),
            }})
            self.eq(valu, expected)

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:url="https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:url', 'https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1'))
            self.propeq(node, 'fqdn', 'vertex.link')
            self.propeq(node, 'passwd', 'hunter2')
            self.propeq(node, 'path', '/coolthings')
            self.propeq(node, 'port', 1337)
            self.propeq(node, 'proto', 'https')
            self.propeq(node, 'user', 'vertexmc')
            self.propeq(node, 'base', 'https://vertexmc:hunter2@vertex.link:1337/coolthings')
            self.propeq(node, 'params', '?a=1')

            nodes = await core.nodes('[inet:url="https://vertex.link?a=1"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:url', 'https://vertex.link?a=1'))
            self.propeq(node, 'fqdn', 'vertex.link')
            self.propeq(node, 'path', '')

            # equality comparator behavior
            valu = 'https://vertex.link?a=1'
            q = f'inet:url +inet:url="{valu}"'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'inet:url +inet:url=""'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            nodes = await core.nodes('[ inet:url="https://+:80/woot" ]')
            self.len(1, nodes)

            self.none(nodes[0].get('fqdn'))

            q = '''
            [
                inet:url="http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html"
                inet:url="http://[1080:0:0:0:8:800:200C:417A]/index.html?foo=bar"
                inet:url="http://[3ffe:2a00:100:7031::1]"
                inet:url="http://[1080::8:800:200C:417A]/foo"
                inet:url="http://[::192.9.5.5]/ipng"
                inet:url="http://[::FFFF:129.144.52.38]:80/index.html"
                inet:url="https://[2010:836B:4179::836B:4179]"
            ]
            '''
            nodes = await core.nodes(q)
            self.len(7, nodes)
            self.propeq(nodes[0], 'base', 'http://[fedc:ba98:7654:3210:fedc:ba98:7654:3210]:80/index.html')
            self.propeq(nodes[0], 'proto', 'http')
            self.propeq(nodes[0], 'path', '/index.html')
            self.propeq(nodes[0], 'params', '')
            self.propeq(nodes[0], 'ip', (6, 0xfedcba9876543210fedcba9876543210))
            self.propeq(nodes[0], 'port', 80)

            self.propeq(nodes[1], 'base', 'http://[1080::8:800:200c:417a]/index.html')
            self.propeq(nodes[1], 'proto', 'http')
            self.propeq(nodes[1], 'path', '/index.html')
            self.propeq(nodes[1], 'params', '?foo=bar')
            self.propeq(nodes[1], 'ip', (6, 0x108000000000000000080800200c417a))
            self.propeq(nodes[1], 'port', 80)

            self.propeq(nodes[2], 'base', 'http://[3ffe:2a00:100:7031::1]')
            self.propeq(nodes[2], 'proto', 'http')
            self.propeq(nodes[2], 'path', '')
            self.propeq(nodes[2], 'params', '')
            self.propeq(nodes[2], 'ip', (6, 0x3ffe2a00010070310000000000000001))
            self.propeq(nodes[2], 'port', 80)

            self.propeq(nodes[3], 'base', 'http://[1080::8:800:200c:417a]/foo')
            self.propeq(nodes[3], 'proto', 'http')
            self.propeq(nodes[3], 'path', '/foo')
            self.propeq(nodes[3], 'params', '')
            self.propeq(nodes[3], 'ip', (6, 0x108000000000000000080800200c417a))
            self.propeq(nodes[3], 'port', 80)

            self.propeq(nodes[4], 'base', 'http://[::192.9.5.5]/ipng')
            self.propeq(nodes[4], 'proto', 'http')
            self.propeq(nodes[4], 'path', '/ipng')
            self.propeq(nodes[4], 'params', '')
            self.propeq(nodes[4], 'ip', (6, 0xc0090505))
            self.propeq(nodes[4], 'port', 80)

            self.propeq(nodes[5], 'base', 'http://[::ffff:129.144.52.38]:80/index.html')
            self.propeq(nodes[5], 'proto', 'http')
            self.propeq(nodes[5], 'path', '/index.html')
            self.propeq(nodes[5], 'params', '')
            self.propeq(nodes[5], 'ip', (6, 0xffff81903426))
            self.propeq(nodes[5], 'port', 80)

            self.propeq(nodes[6], 'base', 'https://[2010:836b:4179::836b:4179]')
            self.propeq(nodes[6], 'proto', 'https')
            self.propeq(nodes[6], 'path', '')
            self.propeq(nodes[6], 'params', '')
            self.propeq(nodes[6], 'ip', (6, 0x2010836b4179000000000000836b4179))
            self.propeq(nodes[6], 'port', 443)

            self.len(1, await core.nodes('[ inet:url=https://vertex.link +(uses)> {[ meta:technique=* ]} ]'))

    async def test_url_file(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:////'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file://///'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file://'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:'))

            paramsub = (t.strtype.typehash, '', {})
            protosub = (t.lowstrtype.typehash, 'file', {})

            url = 'file:///'
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'path': (t.strtype.typehash, '/', {}),
                'proto': protosub,
                'params': paramsub,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///home/foo/Documents/html/index.html'
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'path': (t.strtype.typehash, '/home/foo/Documents/html/index.html', {}),
                'proto': protosub,
                'params': paramsub,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///c:/path/to/my/file.jpg'
            expected = (url, {'subs': {
                'base': (t.strtype.typehash, url, {}),
                'path': (t.strtype.typehash, 'c:/path/to/my/file.jpg', {}),
                'params': paramsub,
                'proto': protosub,
            }})
            self.eq(await t.norm(url), expected)

            lhostsub = {
                'host': (t.fqdntype.hosttype.typehash, 'localhost', {}),
                'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
            }
            url = 'file://localhost/c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, 'c:/Users/BarUser/stuff/moar/stuff.txt', {}),
                'params': paramsub,
                'fqdn': (t.fqdntype.typehash, 'localhost', {'subs': lhostsub}),
                'base': (t.strtype.typehash, url, {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, 'c:/Users/BarUser/stuff/moar/stuff.txt', {}),
                'params': paramsub,
                'base': (t.strtype.typehash, url, {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://localhost/home/visi/synapse/README.rst'
            expected = (url, {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, '/home/visi/synapse/README.rst', {}),
                'params': paramsub,
                'fqdn': (t.fqdntype.typehash, 'localhost', {'subs': lhostsub}),
                'base': (t.strtype.typehash, url, {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/C:/invisig0th/code/synapse/README.rst'
            expected = ('file:///C:/invisig0th/code/synapse/README.rst', {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, 'C:/invisig0th/code/synapse/README.rst', {}),
                'params': paramsub,
                'base': (t.strtype.typehash, 'file:///C:/invisig0th/code/synapse/README.rst', {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://somehost/path/to/foo.txt'
            expected = (url, {'subs': {
                'proto': protosub,
                'params': paramsub,
                'path': (t.strtype.typehash, '/path/to/foo.txt', {}),
                'fqdn': (t.fqdntype.typehash, 'somehost', {'subs': {
                    'host': (t.fqdntype.hosttype.typehash, 'somehost', {}),
                    'issuffix': (t.fqdntype.booltype.typehash, 1, {})}}),
                'base': (t.strtype.typehash, url, {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/c:/foo/bar/baz/single/slash.txt'
            expected = ('file:///c:/foo/bar/baz/single/slash.txt', {'subs': {
                'proto': protosub,
                'params': paramsub,
                'path': (t.strtype.typehash, 'c:/foo/bar/baz/single/slash.txt', {}),
                'base': (t.strtype.typehash, 'file:///c:/foo/bar/baz/single/slash.txt', {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:c:/foo/bar/baz/txt'
            expected = ('file:///c:/foo/bar/baz/txt', {'subs': {
                'proto': protosub,
                'params': paramsub,
                'path': (t.strtype.typehash, 'c:/foo/bar/baz/txt', {}),
                'base': (t.strtype.typehash, 'file:///c:/foo/bar/baz/txt', {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/home/visi/synapse/synapse/lib/'
            expected = ('file:///home/visi/synapse/synapse/lib/', {'subs': {
                'proto': protosub,
                'params': paramsub,
                'path': (t.strtype.typehash, '/home/visi/synapse/synapse/lib/', {}),
                'base': (t.strtype.typehash, 'file:///home/visi/synapse/synapse/lib/', {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://foo.vertex.link/home/bar/baz/biz.html'
            expected = (url, {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, '/home/bar/baz/biz.html', {}),
                'params': paramsub,
                'fqdn': (t.fqdntype.typehash, 'foo.vertex.link', {'subs': {
                    'domain': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                        'host': (t.fqdntype.hosttype.typehash, 'vertex', {}),
                        'domain': (t.fqdntype.typehash, 'link', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                    }}),
                    'host': (t.fqdntype.hosttype.typehash, 'foo', {})}}),
                'base': (t.strtype.typehash, 'file://foo.vertex.link/home/bar/baz/biz.html', {}),
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': protosub,
                'fqdn': (t.fqdntype.typehash, 'somehost.vertex.link', {'subs': {
                    'domain': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                        'host': (t.fqdntype.hosttype.typehash, 'vertex', {}),
                        'domain': (t.fqdntype.typehash, 'link', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                    }}),
                    'host': (t.fqdntype.hosttype.typehash, 'somehost', {})}}),
                'base': (t.strtype.typehash, 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/', {}),
                'path': (t.strtype.typehash, 'c:/invisig0th/code/synapse/', {}),
                'user': (t.lowstrtype.typehash, 'visi@vertex.link', {}),
                'params': paramsub,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://foo@bar.com:neato@burrito@7.7.7.7/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': protosub,
                'base': (t.strtype.typehash, 'file://foo@bar.com:neato@burrito@7.7.7.7/c:/invisig0th/code/synapse/', {}),
                'ip': (t.iptype.typehash, (4, 117901063), {'subs': {
                    'type': (t.iptype.typetype.typehash, 'unicast', {}),
                    'version': (t.iptype.verstype.typehash, 4, {})}}),
                'path': (t.strtype.typehash, 'c:/invisig0th/code/synapse/', {}),
                'user': (t.lowstrtype.typehash, 'foo@bar.com', {}),
                'passwd': (t.passtype.typehash, 'neato@burrito', {'subs': {
                    'md5': (t.passtype.md5.typehash, 'a8e174c5a70f75a78173b6f056e6391b', {}),
                    'sha1': (t.passtype.sha1.typehash, '3d7b1484dd08034c00c4194b4b51625b55128982', {}),
                    'sha256': (t.passtype.sha256.typehash, '4fb24561bf3fa8f5ed05e33ab4d883f0bfae7d61d5d58fe1aec9a347227c0dc3', {})}}),
                'params': paramsub,
            }})
            self.eq(await t.norm(url), expected)

            # not allowed by the rfc
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/'))

            # Also an invalid URL, but doesn't cleanly fall out, because well, it could be a valid filename
            url = 'file:/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/'
            expected = ('file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/', {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, '/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/', {}),
                'params': paramsub,
                'base': (t.strtype.typehash, 'file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/', {}),
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.2
            url = 'file://visi@vertex.link:password@somehost.vertex.link:9876/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': protosub,
                'path': (t.strtype.typehash, 'c:/invisig0th/code/synapse/', {}),
                'user': (t.lowstrtype.typehash, 'visi@vertex.link', {}),
                'passwd': (t.passtype.typehash, 'password', {'subs': {
                    'md5': (t.passtype.md5.typehash, '5f4dcc3b5aa765d61d8327deb882cf99', {}),
                    'sha1': (t.passtype.sha1.typehash, '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', {}),
                    'sha256': (t.passtype.sha256.typehash, '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', {})}}),
                'fqdn': (t.fqdntype.typehash, 'somehost.vertex.link', {'subs': {
                    'domain': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                        'host': (t.fqdntype.hosttype.typehash, 'vertex', {}),
                        'domain': (t.fqdntype.typehash, 'link', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                    }}),
                    'host': (t.fqdntype.hosttype.typehash, 'somehost', {})}}),
                'params': paramsub,
                'port': (t.porttype.typehash, 9876, {}),
                'base': (t.strtype.typehash, url, {}),
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.2.2
            url = 'FILE:c|/synapse/synapse/lib/stormtypes.py'
            expected = ('file:///c|/synapse/synapse/lib/stormtypes.py', {'subs': {
                'path': (t.strtype.typehash, 'c|/synapse/synapse/lib/stormtypes.py', {}),
                'proto': protosub,
                'params': paramsub,
                'base': (t.strtype.typehash, 'file:///c|/synapse/synapse/lib/stormtypes.py', {}),
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.3.2
            url = 'file:////host.vertex.link/SharedDir/Unc/FilePath'
            expected = ('file:////host.vertex.link/SharedDir/Unc/FilePath', {'subs': {
                'proto': protosub,
                'params': paramsub,
                'path': (t.strtype.typehash, '/SharedDir/Unc/FilePath', {}),
                'fqdn': (t.fqdntype.typehash, 'host.vertex.link', {'subs': {
                    'domain': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                        'host': (t.fqdntype.hosttype.typehash, 'vertex', {}),
                        'domain': (t.fqdntype.typehash, 'link', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                    }}),
                    'host': (t.fqdntype.hosttype.typehash, 'host', {})}}),
                'base': (t.strtype.typehash, 'file:////host.vertex.link/SharedDir/Unc/FilePath', {}),
            }})
            self.eq(await t.norm(url), expected)

            # Firefox's non-standard representation that appears every so often
            # supported because the RFC supports it
            url = 'file://///host.vertex.link/SharedDir/Firefox/Unc/File/Path'
            expected = ('file:////host.vertex.link/SharedDir/Firefox/Unc/File/Path', {'subs': {
                'proto': protosub,
                'params': paramsub,
                'base': (t.strtype.typehash, 'file:////host.vertex.link/SharedDir/Firefox/Unc/File/Path', {}),
                'path': (t.strtype.typehash, '/SharedDir/Firefox/Unc/File/Path', {}),
                'fqdn': (t.fqdntype.typehash, 'host.vertex.link', {'subs': {
                    'domain': (t.fqdntype.typehash, 'vertex.link', {'subs': {
                        'host': (t.fqdntype.hosttype.typehash, 'vertex', {}),
                        'domain': (t.fqdntype.typehash, 'link', {'subs': {
                            'host': (t.fqdntype.hosttype.typehash, 'link', {}),
                            'issuffix': (t.fqdntype.booltype.typehash, 1, {}),
                        }}),
                    }}),
                    'host': (t.fqdntype.hosttype.typehash, 'host', {})}}),
            }})
            self.eq(await t.norm(url), expected)

    async def test_url_fqdn(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            host = 'Vertex.Link'
            fqdntype = core.model.type('inet:fqdn')
            norm_host = await fqdntype.norm(host)
            repr_host = core.model.type('inet:fqdn').repr(norm_host[0])

            self.eq(norm_host[0], 'vertex.link')
            self.eq(repr_host, 'vertex.link')

            hostsub = (fqdntype.typehash, norm_host[0], norm_host[1])
            await self._test_types_url_behavior(t, 'fqdn', host, hostsub, repr_host)

    async def test_url_ipv4(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '192[.]168.1[.]1'
            iptype = core.model.type('inet:ip')
            norm_host = await iptype.norm(host)
            repr_host = core.model.type('inet:ip').repr(norm_host[0])
            self.eq(norm_host[0], (4, 3232235777))
            self.eq(repr_host, '192.168.1.1')

            hostsub = (iptype.typehash, norm_host[0], norm_host[1])
            await self._test_types_url_behavior(t, 'ipv4', host, hostsub, repr_host)

    async def test_url_ipv6(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '::1'
            iptype = core.model.type('inet:ip')
            norm_host = await iptype.norm(host)
            repr_host = core.model.type('inet:ip').repr(norm_host[0])
            self.eq(norm_host[0], (6, 1))
            self.eq(repr_host, '::1')

            hostsub = (iptype.typehash, norm_host[0], norm_host[1])
            await self._test_types_url_behavior(t, 'ipv6', host, hostsub, repr_host)

            # IPv6 Port Special Cases
            weird = await t.norm('http://::1:81/hehe')
            ipsubs = {
                'type': (iptype.typetype.typehash, 'reserved', {}),
                'scope': (iptype.scopetype.typehash, 'global', {}),
                'version': (iptype.verstype.typehash, 6, {})
            }
            self.eq(weird[1]['subs']['ip'], (iptype.typehash, (6, 0x10081), {'subs': ipsubs}))
            self.eq(weird[1]['subs']['port'], (core.model.type('inet:port').typehash, 80, {}))

            await self.asyncraises(s_exc.BadTypeValu, t.norm('http://0:0:0:0:0:0:0:0:81/'))

    async def _test_types_url_behavior(self, t, htype, host, norm_host, repr_host):

        # Handle IPv6 Port Brackets
        host_port = host
        repr_host_port = repr_host

        if htype == 'ipv6':
            host_port = f'[{host}]'
            repr_host_port = f'[{repr_host}]'

        if htype in ('ipv4', 'ipv6'):
            htype = 'ip'

        # URL with auth and port.
        url = f'https://user:password@{host_port}:1234/a/b/c/'
        expected = (f'https://user:password@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '/a/b/c/', {}),
            'user': (t.lowstrtype.typehash, 'user', {}),
            'passwd': (t.passtype.typehash, 'password', {'subs': {
                'md5': (t.passtype.md5.typehash, '5f4dcc3b5aa765d61d8327deb882cf99', {}),
                'sha1': (t.passtype.sha1.typehash, '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', {}),
                'sha256': (t.passtype.sha256.typehash, '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', {})}}),
            htype: norm_host,
            'port': (t.porttype.typehash, 1234, {}),
            'base': (t.strtype.typehash, f'https://user:password@{repr_host_port}:1234/a/b/c/', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

        # Userinfo user with @ in it
        url = f'lando://visi@vertex.link@{host_port}:40000/auth/gateway'
        expected = (f'lando://visi@vertex.link@{repr_host_port}:40000/auth/gateway', {'subs': {
            'proto': (t.lowstrtype.typehash, 'lando', {}),
            'path': (t.strtype.typehash, '/auth/gateway', {}),
            'user': (t.lowstrtype.typehash, 'visi@vertex.link', {}),
            'base': (t.strtype.typehash, f'lando://visi@vertex.link@{repr_host_port}:40000/auth/gateway', {}),
            'port': (t.porttype.typehash, 40000, {}),
            'params': (t.strtype.typehash, '', {}),
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # Userinfo password with @
        url = f'balthazar://root:foo@@@bar@{host_port}:1234/'
        expected = (f'balthazar://root:foo@@@bar@{repr_host_port}:1234/', {'subs': {
            'proto': (t.lowstrtype.typehash, 'balthazar', {}),
            'path': (t.strtype.typehash, '/', {}),
            'user': (t.lowstrtype.typehash, 'root', {}),
            'passwd': (t.passtype.typehash, 'foo@@@bar', {'subs': {
                'md5': (t.passtype.md5.typehash, '43947b88f0eb686bfc5c4237ffd36beb', {}),
                'sha1': (t.passtype.sha1.typehash, 'd29614eb55f9aa29efd8f3105ed60b8881dc81dd', {}),
                'sha256': (t.passtype.sha256.typehash, 'd5547965c7f16db873d22ddbcc333f002c94913330801d84b2ab899ca76fa101', {})}}),
            'base': (t.strtype.typehash, f'balthazar://root:foo@@@bar@{repr_host_port}:1234/', {}),
            'port': (t.porttype.typehash, 1234, {}),
            'params': (t.strtype.typehash, '', {}),
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # rfc3986 compliant Userinfo with @ properly encoded
        url = f'calrissian://visi%40vertex.link:surround%40@{host_port}:44343'
        expected = (f'calrissian://visi%40vertex.link:surround%40@{repr_host_port}:44343', {'subs': {
            'proto': (t.lowstrtype.typehash, 'calrissian', {}),
            'path': (t.strtype.typehash, '', {}),
            'user': (t.lowstrtype.typehash, 'visi@vertex.link', {}),
            'passwd': (t.passtype.typehash, 'surround@', {'subs': {
                'md5': (t.passtype.md5.typehash, '494346410c1c4a4b98feb1b1956a71ae', {}),
                'sha1': (t.passtype.sha1.typehash, 'ba9b515889b5d7f1bb1d13f13409e1f7518f7c20', {}),
                'sha256': (t.passtype.sha256.typehash, '5058c40473c5e4e2a174f8837d4295d19ca1542d2fb45017f54d89f80da6897d', {})}}),
            'base': (t.strtype.typehash, f'calrissian://visi%40vertex.link:surround%40@{repr_host_port}:44343', {}),
            'port': (t.porttype.typehash, 44343, {}),
            'params': (t.strtype.typehash, '', {}),
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # unencoded query params are handled nicely
        url = f'https://visi@vertex.link:neato@burrito@{host}/?q=@foobarbaz'
        expected = (f'https://visi@vertex.link:neato@burrito@{repr_host}/?q=@foobarbaz', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '/', {}),
            'user': (t.lowstrtype.typehash, 'visi@vertex.link', {}),
            'passwd': (t.passtype.typehash, 'neato@burrito', {'subs': {
                'md5': (t.passtype.md5.typehash, 'a8e174c5a70f75a78173b6f056e6391b', {}),
                'sha1': (t.passtype.sha1.typehash, '3d7b1484dd08034c00c4194b4b51625b55128982', {}),
                'sha256': (t.passtype.sha256.typehash, '4fb24561bf3fa8f5ed05e33ab4d883f0bfae7d61d5d58fe1aec9a347227c0dc3', {})}}),
            'base': (t.strtype.typehash, f'https://visi@vertex.link:neato@burrito@{repr_host}/', {}),
            'port': (t.porttype.typehash, 443, {}),
            'params': (t.strtype.typehash, '?q=@foobarbaz', {}),
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # URL with no port, but default port valu.
        # Port should be in subs, but not normed URL.
        url = f'https://user:password@{host}/a/b/c/?foo=bar&baz=faz'
        expected = (f'https://user:password@{repr_host}/a/b/c/?foo=bar&baz=faz', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '/a/b/c/', {}),
            'user': (t.lowstrtype.typehash, 'user', {}),
            'passwd': (t.passtype.typehash, 'password', {'subs': {
                'md5': (t.passtype.md5.typehash, '5f4dcc3b5aa765d61d8327deb882cf99', {}),
                'sha1': (t.passtype.sha1.typehash, '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', {}),
                'sha256': (t.passtype.sha256.typehash, '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', {})}}),
            htype: norm_host,
            'port': (t.porttype.typehash, 443, {}),
            'base': (t.strtype.typehash, f'https://user:password@{repr_host}/a/b/c/', {}),
            'params': (t.strtype.typehash, '?foo=bar&baz=faz', {})
        }})
        self.eq(await t.norm(url), expected)

        # URL with no port and no default port valu.
        # Port should not be in subs or normed URL.
        url = f'arbitrary://user:password@{host}/a/b/c/'
        expected = (f'arbitrary://user:password@{repr_host}/a/b/c/', {'subs': {
            'proto': (t.lowstrtype.typehash, 'arbitrary', {}),
            'path': (t.strtype.typehash, '/a/b/c/', {}),
            'user': (t.lowstrtype.typehash, 'user', {}),
            'passwd': (t.passtype.typehash, 'password', {'subs': {
                'md5': (t.passtype.md5.typehash, '5f4dcc3b5aa765d61d8327deb882cf99', {}),
                'sha1': (t.passtype.sha1.typehash, '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', {}),
                'sha256': (t.passtype.sha256.typehash, '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', {})}}),
            htype: norm_host,
            'base': (t.strtype.typehash, f'arbitrary://user:password@{repr_host}/a/b/c/', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

        # URL with user but no password.
        # User should still be in URL and subs.
        url = f'https://user@{host_port}:1234/a/b/c/'
        expected = (f'https://user@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '/a/b/c/', {}),
            'user': (t.lowstrtype.typehash, 'user', {}),
            htype: norm_host,
            'port': (t.porttype.typehash, 1234, {}),
            'base': (t.strtype.typehash, f'https://user@{repr_host_port}:1234/a/b/c/', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

        # URL with no user/password.
        # User/Password should not be in URL or subs.
        url = f'https://{host_port}:1234/a/b/c/'
        expected = (f'https://{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '/a/b/c/', {}),
            htype: norm_host,
            'port': (t.porttype.typehash, 1234, {}),
            'base': (t.strtype.typehash, f'https://{repr_host_port}:1234/a/b/c/', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

        # URL with no path.
        url = f'https://{host_port}:1234'
        expected = (f'https://{repr_host_port}:1234', {'subs': {
            'proto': (t.lowstrtype.typehash, 'https', {}),
            'path': (t.strtype.typehash, '', {}),
            htype: norm_host,
            'port': (t.porttype.typehash, 1234, {}),
            'base': (t.strtype.typehash, f'https://{repr_host_port}:1234', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

        # URL with no path or port or default port.
        url = f'a://{host}'
        expected = (f'a://{repr_host}', {'subs': {
            'proto': (t.lowstrtype.typehash, 'a', {}),
            'path': (t.strtype.typehash, '', {}),
            htype: norm_host,
            'base': (t.strtype.typehash, f'a://{repr_host}', {}),
            'params': (t.strtype.typehash, '', {})
        }})
        self.eq(await t.norm(url), expected)

    async def test_urlfile(self):
        async with self.getTestCore() as core:
            file = s_common.guid()
            valu = ('https://vertex.link/a_cool_program.exe', file)
            nodes = await core.nodes('[inet:urlfile=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:urlfile', (valu[0], file)))
            self.propeq(node, 'url', 'https://vertex.link/a_cool_program.exe')
            self.propeq(node, 'file', file)

            url = await core.nodes('inet:url')
            self.len(1, url)
            url = url[0]
            self.propeq(url, 'port', 443)
            self.propeq(url, 'params', '')
            self.propeq(url, 'fqdn', 'vertex.link')
            self.propeq(url, 'proto', 'https')
            self.propeq(url, 'base', 'https://vertex.link/a_cool_program.exe')

    async def test_url_mirror(self):
        url0 = 'http://vertex.link'
        url1 = 'http://vtx.lk'
        opts = {'vars': {'url0': url0, 'url1': url1}}
        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:url:mirror=($url0, $url1) ]', opts=opts)

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:url:mirror', (url0, url1)))
            self.propeq(nodes[0], 'at', 'http://vtx.lk')
            self.propeq(nodes[0], 'of', 'http://vertex.link')

            with self.raises(s_exc.ReadOnlyProp):
                nodes = await core.nodes('inet:url:mirror=($url0, $url1) [ :at=http://newp.com ]', opts=opts)

            with self.raises(s_exc.ReadOnlyProp):
                nodes = await core.nodes('inet:url:mirror=($url0, $url1) [ :of=http://newp.com ]', opts=opts)

    async def test_urlredir(self):
        async with self.getTestCore() as core:
            valu = ('https://vertex.link/idk', 'https://cool.vertex.newp:443/something_else')
            nodes = await core.nodes('[inet:url:redir=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:url:redir', valu))
            self.propeq(node, 'source', 'https://vertex.link/idk')
            self.propeq(node, 'target', 'https://cool.vertex.newp:443/something_else')
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))
            self.len(1, await core.nodes('inet:fqdn=cool.vertex.newp'))

    async def test_user(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:user="cool User "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:user', 'cool user'))

    async def test_whois_collection(self):

        async with self.getTestCore() as core:

            valu = s_common.guid()
            rec = s_common.guid()
            props = {
                'time': 2554869000000000,
                'fqdn': 'arin.whois.net',
                'ip': (4, 167772160),
                'success': True,
                'rec': rec,
            }
            q = '[(inet:whois:ipquery=$valu :time=$p.time :fqdn=$p.fqdn :success=$p.success :rec=$p.rec :ip=$p.ip)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:ipquery', valu))
            self.propeq(node, 'time', 2554869000000000)
            self.propeq(node, 'fqdn', 'arin.whois.net')
            self.propeq(node, 'success', True)
            self.propeq(node, 'rec', rec)
            self.propeq(node, 'ip', (4, 167772160))

            valu = s_common.guid()
            props = {
                'time': 2554869000000000,
                'url': 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff',
                'ip': '3300:100:1::ffff',
                'success': False,
            }
            q = '[(inet:whois:ipquery=$valu :time=$p.time :url=$p.url :success=$p.success :ip=$p.ip)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:ipquery', valu))
            self.propeq(node, 'time', 2554869000000000)
            self.propeq(node, 'url', 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff')
            self.propeq(node, 'success', False)
            self.none(node.get('rec'))
            self.propeq(node, 'ip', (6, 0x3300010000010000000000000000ffff))

    async def test_whois_record(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ inet:whois:record=0c63f6b67c9a3ca40f9f942957a718e9
                    :fqdn=woot.com
                    :text="YELLING AT pennywise@vertex.link LOUDLY"
                    :registrar=' cool REGISTRAR'
                    :registrant=' cool REGISTRANT'
                    :seen=2022
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:record', '0c63f6b67c9a3ca40f9f942957a718e9'))
            self.propeq(node, 'fqdn', 'woot.com')
            self.propeq(node, 'text', 'yelling at pennywise@vertex.link loudly')
            self.propeq(node, 'registrar', 'cool registrar')
            self.propeq(node, 'registrant', 'cool registrant')
            self.nn(node.get('seen'))

            with self.getLoggerStream('synapse.datamodel') as stream:
                nodes = await core.nodes('[ inet:whois:record=* :text="Contact: pennywise@vertex.link" ]')
                self.len(1, nodes)
                self.propeq(nodes[0], 'text', 'contact: pennywise@vertex.link')
                self.none(nodes[0].get('fqdn'))

            stream.seek(0)
            data = stream.read()
            self.notin('onset() error for inet:whois:record:text', data)

    async def test_whois_iprecord(self):
        async with self.getTestCore() as core:
            contact = s_common.guid()
            addlcontact = s_common.guid()
            rec_ipv4 = s_common.guid()
            props = {
                'net': '10.0.0.0/28',
                'created': 2554858000000000,
                'updated': 2554858000000000,
                'text': 'this is  a bunch of \nrecord text 123123',
                'asn': 12345,
                'id': 'NET-10-0-0-0-1',
                'name': 'vtx',
                'parentid': 'NET-10-0-0-0-0',
                'contacts': (addlcontact, ),
                'country': 'US',
                'status': 'validated',
                'type': 'direct allocation',
                'links': ('http://rdap.com/foo', 'http://rdap.net/bar'),
            }
            q = '''[(inet:whois:iprecord=$valu :net=$p.net :created=$p.created :updated=$p.updated
                :text=$p.text :asn=$p.asn :id=$p.id :name=$p.name :parentid=$p.parentid
                :contacts=$p.contacts :country=$p.country :status=$p.status :type=$p.type
                :links=$p.links :seen=2022)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': rec_ipv4, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:iprecord', rec_ipv4))
            self.propeq(node, 'net', ((4, 167772160), (4, 167772175)))
            # FIXME virtual props
            # self.propeq(node, 'net*min', (4, 167772160))
            # self.propeq(node, 'net*max', (4, 167772175))
            self.propeq(node, 'created', 2554858000000000)
            self.propeq(node, 'updated', 2554858000000000)
            self.propeq(node, 'text', 'this is  a bunch of \nrecord text 123123')
            self.propeq(node, 'asn', 12345)
            self.propeq(node, 'id', 'NET-10-0-0-0-1')
            self.propeq(node, 'name', 'vtx')
            self.propeq(node, 'parentid', 'NET-10-0-0-0-0')
            self.propeq(node, 'contacts', (addlcontact,))
            self.propeq(node, 'country', 'us')
            self.propeq(node, 'status', 'validated')
            self.propeq(node, 'type', 'direct allocation')
            self.propeq(node, 'links', ('http://rdap.com/foo', 'http://rdap.net/bar'))
            self.nn(node.get('seen'))

            rec_ipv6 = s_common.guid()
            props = {
                'net': '2001:db8::/101',
                'created': 2554858000000000,
                'updated': 2554858000000000,
                'text': 'this is  a bunch of \nrecord text 123123',
                'asn': 12345,
                'id': 'NET-10-0-0-0-0',
                'name': 'EU-VTX-1',
                'country': 'tp',
                'status': 'renew prohibited',
                'type': 'allocated-BY-rir',
            }

            minv = (6, 0x20010db8000000000000000000000000)
            maxv = (6, 0x20010db8000000000000000007ffffff)

            q = '''[(inet:whois:iprecord=$valu :net=$p.net :created=$p.created :updated=$p.updated
                :text=$p.text :asn=$p.asn :id=$p.id :name=$p.name
                :country=$p.country :status=$p.status :type=$p.type)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': rec_ipv6, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:iprecord', rec_ipv6))
            self.propeq(node, 'net', (minv, maxv))
            # FIXME virtual props
            # self.propeq(node, 'net*min', minv)
            # self.propeq(node, 'net*max', maxv)
            self.propeq(node, 'created', 2554858000000000)
            self.propeq(node, 'updated', 2554858000000000)
            self.propeq(node, 'text', 'this is  a bunch of \nrecord text 123123')
            self.propeq(node, 'asn', 12345)
            self.propeq(node, 'id', 'NET-10-0-0-0-0')
            self.propeq(node, 'name', 'EU-VTX-1')
            self.propeq(node, 'country', 'tp')
            self.propeq(node, 'status', 'renew prohibited')
            self.propeq(node, 'type', 'allocated-by-rir')

            # check regid pivot
            scmd = f'inet:whois:iprecord={rec_ipv4} :parentid -> inet:whois:iprecord:id'
            nodes = await core.nodes(scmd)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:whois:iprecord', rec_ipv6))

    async def test_wifi_collection(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:wifi:ssid="The Best SSID"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:wifi:ssid', "The Best SSID"))

            nodes = await core.nodes('''
                [ inet:wifi:ap=*
                    :ssid="The Best SSID2 "
                    :bssid=00:11:22:33:44:55
                    :place=*
                    :channel=99
                    :place:latlong=(20, 30)
                    :place:latlong:accuracy=10km
                    :encryption=wpa2
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'ssid', 'The Best SSID2 ')
            self.propeq(node, 'bssid', '00:11:22:33:44:55')
            self.propeq(node, 'place:latlong', (20.0, 30.0))
            self.propeq(node, 'place:latlong:accuracy', 10000000)
            self.propeq(node, 'channel', 99)
            self.propeq(node, 'encryption', 'wpa2')

            self.len(1, await core.nodes('inet:wifi:ap -> geo:place'))

    async def test_banner(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:banner=("tcp://1.2.3.4:443", "Hi There")]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'text', 'Hi There')
            self.propeq(node, 'server', 'tcp://1.2.3.4:443')

            self.len(1, await core.nodes('it:dev:str="Hi There"'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4'))

            nodes = await core.nodes('[inet:banner=("tcp://::ffff:8.7.6.5", sup)]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'text', 'sup')
            self.propeq(node, 'server', 'tcp://::ffff:8.7.6.5')

            self.len(1, await core.nodes('it:dev:str="sup"'))
            self.len(1, await core.nodes('inet:ip="::ffff:8.7.6.5"'))

    async def test_search_query(self):
        async with self.getTestCore() as core:
            iden = s_common.guid()
            host = s_common.guid()
            props = {
                'time': 200,
                'text': 'hi there',
                'engine': 'roofroof',
                'host': host,
            }

            q = '''[
                inet:search:query=$valu
                    :time=$p.time
                    :text=$p.text
                    :engine=$p.engine
                    :host=$p.host
                    :account=*
            ]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': iden, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:search:query', iden))
            self.propeq(node, 'time', 200)
            self.propeq(node, 'text', 'hi there')
            self.propeq(node, 'engine', 'roofroof')
            self.propeq(node, 'host', host)
            self.len(1, await core.nodes('inet:search:query :account -> inet:service:account'))

            residen = s_common.guid()
            props = {
                'query': iden,
                'url': 'http://hehehaha.com/',
                'rank': 0,
                'text': 'woot woot woot',
                'title': 'this is a title',
            }
            q = '[inet:search:result=$valu :query=$p.query :url=$p.url :rank=$p.rank :text=$p.text :title=$p.title]'
            nodes = await core.nodes(q, opts={'vars': {'valu': residen, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:search:result', residen))
            self.propeq(node, 'url', 'http://hehehaha.com/')
            self.propeq(node, 'rank', 0)
            self.propeq(node, 'text', 'woot woot woot')
            self.propeq(node, 'title', 'this is a title')
            self.propeq(node, 'query', iden)

    async def test_model_inet_email_message(self):

        async with self.getTestCore() as core:

            flow = s_common.guid()

            q = '''
            [
            inet:email:message="*"
                :id="Woot-12345 "
                :to=woot@woot.com
                :from=visi@vertex.link
                :replyto=root@root.com
                :subject="hi there"
                :date=2015
                :body="there are mad sploitz here!"
                :headers=(('to', 'Visi Stark <visi@vertex.link>'),)
                :cc=(baz@faz.org, foo@bar.com, baz@faz.org)
                :bytes="*"
                :received:from:ip=1.2.3.4
                :received:from:fqdn=smtp.vertex.link
                :flow=$flow
                :links={[
                    inet:email:message:link=*
                        :url=https://www.vertex.link
                        :text=Vertex
                ]}
                :attachments={[
                    file:attachment=*
                        :file=*
                        :path=sploit.exe
                ]}
            ]
            '''
            nodes = await core.nodes(q, opts={'vars': {'flow': flow}})
            self.len(1, nodes)

            self.propeq(nodes[0], 'id', 'Woot-12345')
            self.propeq(nodes[0], 'cc', ('baz@faz.org', 'foo@bar.com'))
            self.propeq(nodes[0], 'received:from:ip', (4, 0x01020304))
            self.propeq(nodes[0], 'received:from:fqdn', 'smtp.vertex.link')
            self.propeq(nodes[0], 'flow', flow)

            self.len(1, await core.nodes('inet:email:message:to=woot@woot.com'))
            self.len(1, await core.nodes('inet:email:message:date=2015'))
            self.len(1, await core.nodes('inet:email:message:body="there are mad sploitz here!"'))
            self.len(1, await core.nodes('inet:email:message:subject="hi there"'))
            self.len(1, await core.nodes('inet:email:message:replyto=root@root.com'))

            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:header +:name=to +:value="Visi Stark <visi@vertex.link>"'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:message:link +:text=Vertex -> inet:url'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> file:attachment +:path=sploit.exe -> file:bytes'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> file:bytes'))
            self.len(1, await core.nodes('inet:email=foo@bar.com -> inet:email:message'))
            self.len(1, await core.nodes('inet:email=baz@faz.org -> inet:email:message'))
            self.len(1, await core.nodes('inet:email:message -> inet:email:message:link +:url=https://www.vertex.link +:text=Vertex'))
            self.len(1, await core.nodes('inet:email:message -> file:attachment +:path=sploit.exe +:file'))

            self.len(1, await core.nodes('inet:email:header limit 1 | [:seen=2022]'))

    async def test_model_inet_tunnel(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
            [ inet:tunnel=*
                :ingress=1.2.3.4:443
                :egress=5.5.5.5
                :type=vpn
                :anon=$lib.true
                :operator = {[ entity:contact=* :email=visi@vertex.link ]}
            ]''')
            self.len(1, nodes)

            self.propeq(nodes[0], 'anon', True)
            self.propeq(nodes[0], 'type', 'vpn.')
            self.propeq(nodes[0], 'egress', 'tcp://5.5.5.5')
            self.propeq(nodes[0], 'ingress', 'tcp://1.2.3.4:443')

            self.len(1, await core.nodes('inet:tunnel -> entity:contact +:email=visi@vertex.link'))

    async def test_model_inet_proto(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:proto=https :port=443 ]')
            self.len(1, nodes)
            self.eq(('inet:proto', 'https'), nodes[0].ndef)
            self.propeq(nodes[0], 'port', 443)

    async def test_model_inet_egress(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
            [ inet:egress=*
                :host = *
                :host:iface = *
                :client=1.2.3.4
            ]
            ''')

            self.len(1, nodes)
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('host:iface'))
            self.propeq(nodes[0], 'client', 'tcp://1.2.3.4')

            self.len(1, await core.nodes('inet:egress -> it:host'))
            self.len(1, await core.nodes('inet:egress -> inet:iface'))

    async def test_model_inet_tls_handshake(self):

        async with self.getTestCore() as core:
            props = {
                'ja3': '1' * 32,
                'ja3s': '2' * 32,
                'client': 'tcp://1.2.3.4:8888',
                'server': 'tcp://5.6.7.8:9999'
            }

            nodes = await core.nodes('''
                [
                    inet:tls:handshake=*
                        :time=now
                        :flow=*
                        :server=$server
                        :server:cert=*
                        :server:ja3s=$ja3s
                        :server:jarmhash=07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1
                        :client=$client
                        :client:cert=*
                        :client:ja3=$ja3
                ]
            ''', opts={'vars': props})
            self.len(1, nodes)
            self.nn(nodes[0].get('time'))
            self.nn(nodes[0].get('flow'))
            self.nn(nodes[0].get('server:cert'))
            self.nn(nodes[0].get('client:cert'))
            self.propeq(nodes[0], 'server:jarmhash', '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')

            self.propeq(nodes[0], 'client:ja3', props['ja3'])
            self.propeq(nodes[0], 'server:ja3s', props['ja3s'])

            self.propeq(nodes[0], 'client', props['client'])
            self.propeq(nodes[0], 'server', props['server'])

    async def test_model_inet_ja3(self):

        async with self.getTestCore() as core:

            ja3 = '76e7b0cb0994d60a4b3f360a088fac39'
            nodes = await core.nodes('[ inet:tls:ja3:sample=(tcp://1.2.3.4, $md5) ]', opts={'vars': {'md5': ja3}})
            self.len(1, nodes)
            self.propeq(nodes[0], 'client', 'tcp://1.2.3.4')
            self.propeq(nodes[0], 'ja3', ja3)

            ja3 = '4769ad08107979c719d86270e706fed5'
            nodes = await core.nodes('[ inet:tls:ja3s:sample=(tcp://2.2.2.2, $md5) ]', opts={'vars': {'md5': ja3}})
            self.len(1, nodes)
            self.propeq(nodes[0], 'server', 'tcp://2.2.2.2')
            self.propeq(nodes[0], 'ja3s', ja3)

    async def test_model_inet_tls_certs(self):

        async with self.getTestCore() as core:

            server = 'e4f6db65dbaa7a4598f7379f75dcd5f5'
            client = 'df8d1f7e04f7c4a322e04b0b252e2851'
            nodes = await core.nodes('[inet:tls:servercert=(tcp://1.2.3.4:1234, $server)]', opts={'vars': {'server': server}})
            self.len(1, nodes)
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:1234')
            self.propeq(nodes[0], 'cert', server)

            nodes = await core.nodes('[inet:tls:clientcert=(tcp://5.6.7.8:5678, $client)]', opts={'vars': {'client': client}})
            self.len(1, nodes)
            self.propeq(nodes[0], 'client', 'tcp://5.6.7.8:5678')
            self.propeq(nodes[0], 'cert', client)

    async def test_model_inet_service(self):

        async with self.getTestCore() as core:

            provname = 'Slack Corp'
            opts = {'vars': {'provname': provname}}
            nodes = await core.nodes(f'gen.ou.org $provname', opts=opts)
            self.len(1, nodes)
            provider = nodes[0]

            q = '''
            [ inet:service:platform=(slack,)
                :id=foo
                :url="https://slack.com"
                :urls=(https://slacker.com,)
                :zones=(slack.com, slacker.com)
                :name=Slack
                :names=("slack chat",)
                :desc=' Slack is a team communication platform.\n\n Be less busy.'
                :parent={[ inet:service:platform=({"name": "salesforce"}) ]}
                :status=available
                :family="  FooFam  "
                :period=(2022, 2023)
                :creator={[ inet:service:account=({"id": "bar"}) ]}
                :remover={[ inet:service:account=({"id": "baz"}) ]}
                :provider={ ou:org:name=$provname }
                :provider:name=$provname
                :type=foo.bar
                :seen=(2022, 2023)
            ]
            '''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:platform', s_common.guid(('slack',))))
            self.propeq(nodes[0], 'id', 'foo')
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'family', 'foofam')
            self.propeq(nodes[0], 'url', 'https://slack.com')
            self.propeq(nodes[0], 'urls', ('https://slacker.com',))
            self.propeq(nodes[0], 'zones', ('slack.com', 'slacker.com'))
            self.propeq(nodes[0], 'name', 'slack')
            self.propeq(nodes[0], 'names', ('slack chat',))
            self.propeq(nodes[0], 'desc', ' Slack is a team communication platform.\n\n Be less busy.')
            self.eq(nodes[0].repr('status'), 'available')
            self.eq(nodes[0].repr('period'), ('2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'))
            self.propeq(nodes[0], 'provider', provider.ndef[1])
            self.propeq(nodes[0], 'provider:name', provname.lower())
            self.eq(nodes[0].repr('seen'), ('2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'))
            platform = nodes[0]

            nodes = await core.nodes('inet:service:platform=(slack,) :parent -> *')
            self.eq(['salesforce'], [n.get('name') for n in nodes])

            nodes = await core.nodes('inet:service:platform=(slack,) :creator -> *')
            self.eq(['bar'], [n.get('id') for n in nodes])

            nodes = await core.nodes('inet:service:platform=(slack,) :remover -> *')
            self.eq(['baz'], [n.get('id') for n in nodes])

            nodes = await core.nodes('[ inet:service:platform=({"name": "slack chat"}) ]')
            self.eq(nodes[0].ndef, platform.ndef)

            nodes = await core.nodes('[ inet:service:platform=({"url": "https://slacker.com"}) ]')
            self.eq(nodes[0].ndef, platform.ndef)

            nodes = await core.nodes('[ inet:service:platform=({"zone": "slacker.com"}) ]')
            self.eq(nodes[0].ndef, platform.ndef)

            nodes = await core.nodes('inet:service:platform:type:taxonomy')
            self.sorteq(['foo.', 'foo.bar.'], [n.ndef[1] for n in nodes])

            opts = {
                'vars': {
                    'rule00': (rule00 := 'a' * 32),
                    'rule01': (rule01 := 'b' * 32),
                },
            }

            q = '''
            $profile = {[
                entity:contact=({"email": "foo@bar.com"})
                    :banner={[ file:bytes=({"name": "greencat.gif"}) ]}
            ]}
            [
                (inet:service:account=(blackout, account, vertex, slack)
                    :id=U7RN51U1J
                    :user=blackout
                    :url=https://vertex.link/users/blackout
                    :email=blackout@vertex.link
                    :profile=$profile
                    :tenant={[
                        inet:service:tenant=({"id": "VS-31337"})
                            :profile=$profile
                    ]}
                    :rules=($rule01, $rule00, $rule01)
                    :seen=(2022, 2023)
                )

                (inet:service:account=(visi, account, vertex, slack)
                    :id=U2XK7PUVB
                    :user=visi
                    :email=visi@vertex.link
                    :parent=*
                )
            ]
            '''
            accounts = await core.nodes(q, opts=opts)
            self.len(2, accounts)

            self.nn(accounts[0].get('tenant'))
            self.eq(accounts[0].repr('seen'), ('2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'))

            self.eq(accounts[0].ndef, ('inet:service:account', s_common.guid(('blackout', 'account', 'vertex', 'slack'))))
            self.propeq(accounts[0], 'id', 'U7RN51U1J')
            self.propeq(accounts[0], 'user', 'blackout')
            self.propeq(accounts[0], 'url', 'https://vertex.link/users/blackout')
            self.propeq(accounts[0], 'email', 'blackout@vertex.link')
            self.propeq(accounts[0], 'rules', (rule01, rule00, rule01))

            self.eq(accounts[1].ndef, ('inet:service:account', s_common.guid(('visi', 'account', 'vertex', 'slack'))))
            self.propeq(accounts[1], 'id', 'U2XK7PUVB')
            self.propeq(accounts[1], 'user', 'visi')
            self.propeq(accounts[1], 'email', 'visi@vertex.link')
            blckacct, visiacct = accounts

            self.len(1, await core.nodes('inet:service:account:email=visi@vertex.link :parent -> inet:service:account'))

            nodes = await core.nodes('inet:service:account:email=blackout@vertex.link :profile -> entity:contact')
            self.len(1, nodes)
            self.nn(nodes[0].get('banner'))

            nodes = await core.nodes('entity:contact:email=foo@bar.com -> (inet:service:account, inet:service:tenant)')
            self.sorteq(['inet:service:account', 'inet:service:tenant'], [n.ndef[0] for n in nodes])

            q = '''
            [ inet:service:role=(developers, group, vertex, slack)
                :id=X1234
                :name="developers, developers, developers"
                :rules=($rule01, $rule00, $rule01)
            ]
            '''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            self.propeq(nodes[0], 'id', 'X1234')
            self.propeq(nodes[0], 'name', 'developers, developers, developers')
            self.propeq(nodes[0], 'rules', (rule01, rule00, rule01))
            devsgrp = nodes[0]

            q = '''
            $role = {[ inet:service:role=$devsiden ]}
            [
                (inet:service:member=(blackout, developers, group, vertex, slack)
                    :account=$blckiden
                    :of=$role
                    :period=(20230601, ?)
                    :creator=$visiiden
                    :remover=$visiiden
                )

                (inet:service:member=(visi, developers, group, vertex, slack)
                    :account=$visiiden
                    :of=$role
                    :period=(20150101, ?)
                )
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'visiiden': visiacct.ndef[1],
                'devsiden': devsgrp.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(2, nodes)

            self.propeq(nodes[0], 'account', blckacct.ndef[1])
            self.propeq(nodes[0], 'of', devsgrp.ndef)
            self.propeq(nodes[0], 'period', (1685577600000000, 9223372036854775807, 0xffffffffffffffff))
            self.propeq(nodes[0], 'creator', visiacct.ndef[1])
            self.propeq(nodes[0], 'remover', visiacct.ndef[1])

            self.propeq(nodes[1], 'account', visiacct.ndef[1])
            self.propeq(nodes[1], 'of', devsgrp.ndef)
            self.propeq(nodes[1], 'period', (1420070400000000, 9223372036854775807, 0xffffffffffffffff))
            self.none(nodes[1].get('creator'))
            self.none(nodes[1].get('remover'))

            q = '''
            [ inet:service:session=*
                :creator=$blckiden
                :period=(202405160900, 202405161055)
                :http:session=*
            ]
            '''
            opts = {'vars': {'blckiden': blckacct.ndef[1]}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.nn(nodes[0].get('http:session'))
            self.propeq(nodes[0], 'creator', blckacct.ndef[1])
            self.propeq(nodes[0], 'period', (1715850000000000, 1715856900000000, 6900000000))
            blcksess = nodes[0]
            self.len(1, await core.nodes('inet:service:session -> inet:http:session'))

            q = '''
            [ inet:service:login=*
                :method=password
                :url=https://vertex.link/api/v1/login
                :session=$blcksess
                :server=tcp://10.10.10.4:443
                :client=tcp://192.168.0.10:12345
                :creds={[auth:passwd=cool]}
            ]
            '''
            opts = {'vars': {'blcksess': blcksess.ndef[1]}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'method', 'password.')
            self.propeq(nodes[0], 'creds', (('auth:passwd', 'cool'),))
            self.propeq(nodes[0], 'url', 'https://vertex.link/api/v1/login')

            server = await core.nodes('inet:server=tcp://10.10.10.4:443')
            self.len(1, server)
            server = server[0]

            client = await core.nodes('inet:client=tcp://192.168.0.10:12345')
            self.len(1, client)
            client = client[0]

            self.propeq(nodes[0], 'server', server.ndef[1])
            self.propeq(nodes[0], 'client', client.ndef[1])

            q = '''
            [ inet:service:message:link=(blackout, developers, 1715856900000000, https://www.youtube.com/watch?v=dQw4w9WgXcQ, vertex, slack)
                :title="Deadpool & Wolverine | Official Teaser | In Theaters July 26"
                :url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.propeq(nodes[0], 'title', 'Deadpool & Wolverine | Official Teaser | In Theaters July 26')
            self.propeq(nodes[0], 'url', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')
            msglink = nodes[0]

            q = '''
            [ inet:service:channel=(general, channel, vertex, slack)
                :id=C1234
                :name=general
                :period=(20150101, ?)
                :creator=$visiiden
                :platform=$platiden
                :topic=' My Topic   '
                :profile={[ entity:contact=({"email": "foo@bar.com"}) ]}
            ]
            '''
            opts = {'vars': {
                'visiiden': visiacct.ndef[1],
                'platiden': platform.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:channel', s_common.guid(('general', 'channel', 'vertex', 'slack'))))
            self.propeq(nodes[0], 'name', 'general')
            self.propeq(nodes[0], 'topic', 'my topic')
            self.propeq(nodes[0], 'period', (1420070400000000, 9223372036854775807, 0xffffffffffffffff))
            self.propeq(nodes[0], 'creator', visiacct.ndef[1])
            self.propeq(nodes[0], 'platform', platform.ndef[1])
            self.len(1, await core.nodes('inet:service:channel:id=C1234 :profile -> entity:contact'))
            gnrlchan = nodes[0]

            q = '''
            [
                (inet:service:member=(visi, general, channel, vertex, slack)
                    :account=$visiiden
                    :period=(20150101, ?)
                )

                (inet:service:member=(blackout, general, channel, vertex, slack)
                    :account=$blckiden
                    :period=(20230601, ?)
                )

                :platform=$platiden
                :of={[ inet:service:channel=$chnliden ]}
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'visiiden': visiacct.ndef[1],
                'chnliden': gnrlchan.ndef[1],
                'platiden': platform.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:service:member', s_common.guid(('visi', 'general', 'channel', 'vertex', 'slack'))))
            self.propeq(nodes[0], 'account', visiacct.ndef[1])
            self.propeq(nodes[0], 'period', (1420070400000000, 9223372036854775807, 0xffffffffffffffff))

            self.eq(nodes[1].ndef, ('inet:service:member', s_common.guid(('blackout', 'general', 'channel', 'vertex', 'slack'))))
            self.propeq(nodes[1], 'account', blckacct.ndef[1])
            self.propeq(nodes[1], 'period', (1685577600000000, 9223372036854775807, 0xffffffffffffffff))

            for node in nodes:
                self.propeq(node, 'platform', platform.ndef[1])
                self.propeq(node, 'of', gnrlchan.ndef)

            q = '''
            [
                (inet:service:message=(blackout, developers, 1715856900000000, vertex, slack)
                    :type=chat.group
                    :role=$devsiden
                    :public=$lib.false
                    :repost=*
                    :mentions=(
                        (inet:service:role, $devsiden),
                        (inet:service:account, $blckiden),
                        (inet:service:account, $blckiden),
                    )
                )

                (inet:service:message=(blackout, visi, 1715856900000000, vertex, slack)
                    :type=chat.direct
                    :to=$visiiden
                    :public=$lib.false
                    :mentions?=((file:attachment, *),)
                )

                (inet:service:message=(blackout, general, 1715856900000000, vertex, slack)
                    :type=chat.channel
                    :channel=$gnrliden
                    :public=$lib.true
                )

                :account=$blckiden
                :text="omg, can't wait for the new deadpool: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                :links+=$linkiden
                :attachments+={[ file:attachment=* ]}

                :place:name=nyc
                :place = { gen.geo.place nyc }
                :file=*

                :client:software = {[ it:software=* :name=woot ]}
                :client:software:name = woot
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'visiiden': visiacct.ndef[1],
                'devsiden': devsgrp.ndef[1],
                'gnrliden': gnrlchan.ndef[1],
                'linkiden': msglink.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(3, nodes)
            for node in nodes:

                self.propeq(node, 'account', blckacct.ndef[1])
                self.propeq(node, 'text', "omg, can't wait for the new deadpool: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                self.propeq(node, 'links', [msglink.ndef[1]])

                self.nn(node.get('client:software'))
                self.propeq(node, 'client:software:name', 'woot')

                self.nn(node.get('place'))
                self.propeq(node, 'place:name', 'nyc')

            self.nn(nodes[0].get('repost'))
            self.propeq(nodes[0], 'role', devsgrp.ndef[1])
            self.false(nodes[0].get('public'))
            self.propeq(nodes[0], 'type', 'chat.group.')
            self.eq(
                nodes[0].get('mentions'),
                (('inet:service:account', blckacct.ndef[1]), ('inet:service:role', devsgrp.ndef[1]))
            )

            self.propeq(nodes[1], 'to', visiacct.ndef[1])
            self.false(nodes[1].get('public'))
            self.propeq(nodes[1], 'type', 'chat.direct.')
            self.none(nodes[1].get('mentions'))

            self.propeq(nodes[2], 'channel', gnrlchan.ndef[1])
            self.true(nodes[2].get('public'))
            self.propeq(nodes[2], 'type', 'chat.channel.')

            svcmsgs = await core.nodes('inet:service:message:type:taxonomy -> inet:service:message')
            self.len(3, svcmsgs)
            self.sorteq(
                [k.ndef for k in svcmsgs],
                [k.ndef for k in nodes],
            )

            nodes = await core.nodes('inet:service:message:type:taxonomy')
            self.len(4, nodes)
            self.sorteq(
                [k.ndef[1] for k in nodes],
                ('chat.', 'chat.channel.', 'chat.direct.', 'chat.group.'),
            )

            nodes = await core.nodes('inet:service:message:type:taxonomy=chat.channel -> inet:service:message')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:message', 'aa59b0c26bd8ce4af627af6326772384'))
            self.len(1, await core.nodes('inet:service:message:repost :repost -> inet:service:message'))

            q = '''
            [ inet:service:resource=(web, api, vertex, slack)
                :desc="The Web API supplies a collection of HTTP methods that underpin the majority of Slack app functionality."
                :name="Slack Web APIs"
                :platform=$platiden
                :type=slack.web.api
                :url="https://slack.com/api"
            ]
            '''
            opts = {'vars': {
                'platiden': platform.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'desc', 'The Web API supplies a collection of HTTP methods that underpin the majority of Slack app functionality.')
            self.propeq(nodes[0], 'name', 'slack web apis')
            self.propeq(nodes[0], 'platform', platform.ndef[1])
            self.propeq(nodes[0], 'type', 'slack.web.api.')
            self.propeq(nodes[0], 'url', 'https://slack.com/api')
            resource = nodes[0]

            nodes = await core.nodes('''
                [ inet:service:bucket:item=*
                    :creator={ inet:service:account:user=visi }
                    :bucket={[ inet:service:bucket=* :name=foobar
                        :creator={ inet:service:account:user=visi }
                    ]}
                    :file=*
                    :file:name=woot.exe
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('bucket'))
            self.nn(nodes[0].get('creator'))
            self.propeq(nodes[0], 'file:name', 'woot.exe')
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:bucket:item -> file:bytes'))
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:bucket:item -> inet:service:account'))
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:account'))
            self.len(1, await core.nodes('inet:service:bucket:name=foobar'))

            q = '''
            [ inet:service:access=(api, blackout, 1715856900000000, vertex, slack)
                :action=foo.bar
                :account=$blckiden
                :platform=$platiden
                :resource=$rsrciden
                :success=$lib.true
                :time=(1715856900000000)
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'visiiden': visiacct.ndef[1],
                'platiden': platform.ndef[1],
                'rsrciden': resource.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'action', 'foo.bar.')
            self.propeq(nodes[0], 'account', blckacct.ndef[1])
            self.propeq(nodes[0], 'platform', platform.ndef[1])
            self.propeq(nodes[0], 'resource', resource.ndef[1])
            self.true(nodes[0].get('success'))
            self.propeq(nodes[0], 'time', 1715856900000000)

            q = '''
            [ inet:service:message=(visi, says, relax)
                :title="Hehe Haha"
                :hashtags="#hehe,#haha,#hehe"
                :thread={[
                    inet:service:thread=*
                        :title="Woot  Woot"
                        :message=(visi, says, hello)
                        :channel={[
                            inet:service:channel=(synapse, subreddit)
                                :name="/r/synapse"
                        ]}
                ]}
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(['#haha', '#hehe'], nodes[0].get('hashtags'))
            self.len(1, await core.nodes('inet:service:message=(visi, says, hello) -> inet:service:thread:message'))
            self.len(1, await core.nodes('''
                inet:service:message:title="hehe haha"
                :thread -> inet:service:thread
                +:title="woot woot"
            '''))
            self.len(2, await core.nodes('inet:service:thread -> inet:service:message'))

            self.len(1, await core.nodes('''
                inet:service:message:title="hehe haha"
                :thread -> inet:service:thread
                :channel -> inet:service:channel
                +:name="/r/synapse"
            '''))

            nodes = await core.nodes('''
                [ inet:service:relationship=*
                    :source={ inet:service:account:user=visi }
                    :target={ inet:service:account:user=visi }
                    :type=follows
                ]
            ''')
            self.nn(nodes[0].get('source'))
            self.nn(nodes[0].get('target'))
            self.propeq(nodes[0], 'type', 'follows.')
            self.len(1, await core.nodes('inet:service:relationship :source -> inet:service:account +:user=visi'))
            self.len(1, await core.nodes('inet:service:relationship :target -> inet:service:account +:user=visi'))

            nodes = await core.nodes('''
                [ inet:service:emote=*
                    :creator={ inet:service:account:user=visi }
                    :about={[ it:dev:repo=* :name=vertex ]}
                    :text=":gothparrot:"
                ]
            ''')
            self.nn(nodes[0].get('about'))
            self.nn(nodes[0].get('creator'))
            self.propeq(nodes[0], 'text', ':gothparrot:')
            self.len(1, await core.nodes('inet:service:emote :about -> it:dev:repo +:name=vertex'))
            self.len(1, await core.nodes('inet:service:emote :creator -> inet:service:account +:user=visi'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:service:relationship=* :source={[it:dev:str=foo]} ]')

            nodes = await core.nodes('''
                [ inet:service:subscription=*
                    :level=vertex.synapse.enterprise
                    :pay:instrument={[ econ:pay:card=* ]}
                    :subscriber={[ inet:service:tenant=({"id": "VS-31337"}) ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'level', 'vertex.synapse.enterprise.')
            self.eq('econ:pay:card', nodes[0].get('pay:instrument')[0])
            self.eq('inet:service:tenant', nodes[0].get('subscriber')[0])
            self.len(1, await core.nodes('inet:service:subscription -> inet:service:subscription:level:taxonomy'))
            self.len(1, await core.nodes('inet:service:subscription :pay:instrument -> econ:pay:card'))
            self.len(1, await core.nodes('inet:service:subscription :subscriber -> inet:service:tenant'))

            nodes = await core.nodes('''
                [ inet:service:agent=*
                    :name=woot
                    :names=(foo, bar)
                    :desc="Foo Bar"
                    :software={[ it:software=(hehe, haha) ]}
                    :platform={inet:service:platform | limit 1}

                    // ensure we got the interface...
                    :creator={ inet:service:account | limit 1 }
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'woot')
            self.propeq(nodes[0], 'names', ('bar', 'foo'))
            self.propeq(nodes[0], 'desc', 'Foo Bar')
            self.nn(nodes[0].get('creator'))
            self.nn(nodes[0].get('platform'))

            self.len(1, await core.nodes('inet:service:action | limit 1 | [ :agent={ inet:service:agent } ]'))
            self.len(1, await core.nodes('inet:service:platform | limit 1 | [ :software={[ it:software=(hehe, haha) ]} ]'))

    async def test_ipv4_fallback(self):

        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[inet:ip=192.168.1.1]'))

            self.len(1, await core.nodes('[inet:ip=3.0.000.115]'))
            self.len(1, await core.nodes('[inet:ip=192.168.001.001]'))
            self.len(1, await core.nodes('[inet:ip=10.0.0.001]'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=256.256.256.256]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=192.168.001.001.001]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ip=192.168.001.001.abc]')

    async def test_model_inet_tls_ja4(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:tls:ja4:sample=(1.2.3.4, t13d190900_9dc949149365_97f8aa674fd9) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'ja4', 't13d190900_9dc949149365_97f8aa674fd9')
            self.propeq(nodes[0], 'client', 'tcp://1.2.3.4')
            self.len(1, await core.nodes('inet:tls:ja4:sample -> inet:client'))
            self.len(1, await core.nodes('inet:tls:ja4:sample -> inet:tls:ja4'))

            nodes = await core.nodes('[ inet:tls:ja4s:sample=(1.2.3.4:443, t130200_1301_a56c5b993250) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'ja4s', 't130200_1301_a56c5b993250')
            self.propeq(nodes[0], 'server', 'tcp://1.2.3.4:443')
            self.len(1, await core.nodes('inet:tls:ja4s:sample -> inet:server'))
            self.len(1, await core.nodes('inet:tls:ja4s:sample -> inet:tls:ja4s'))

            nodes = await core.nodes('''[
                inet:tls:handshake=*
                    :client:ja4=t13d190900_9dc949149365_97f8aa674fd9
                    :server:ja4s=t130200_1301_a56c5b993250
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'client:ja4', 't13d190900_9dc949149365_97f8aa674fd9')
            self.propeq(nodes[0], 'server:ja4s', 't130200_1301_a56c5b993250')
            self.len(1, await core.nodes('inet:tls:handshake :client:ja4 -> inet:tls:ja4'))
            self.len(1, await core.nodes('inet:tls:handshake :server:ja4s -> inet:tls:ja4s'))

            ja4_t = core.model.type('inet:tls:ja4')
            ja4s_t = core.model.type('inet:tls:ja4s')
            self.eq('t13d1909Tg_9dc949149365_97f8aa674fd9', (await ja4_t.norm(' t13d1909Tg_9dc949149365_97f8aa674fd9 '))[0])
            self.eq('t1302Tg_1301_a56c5b993250', (await ja4s_t.norm(' t1302Tg_1301_a56c5b993250 '))[0])
            with self.raises(s_exc.BadTypeValu):
                await ja4_t.norm('t13d190900_9dc949149365_97f8aa674fD9')
            with self.raises(s_exc.BadTypeValu):
                await ja4s_t.norm('t130200_1301_a56c5B993250')
