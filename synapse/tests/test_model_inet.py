import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class InetModelTest(s_t_utils.SynTest):

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
            self.eq(nodes[0].get('client'), 'tcp://5.5.5.5')
            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:22')

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
            self.eq(nodes[0].get('client'), 'tcp://5.5.5.5')
            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:22')
            self.eq(nodes[0].get('client:keyboard:layout'), 'azerty')

            self.len(1, await core.nodes('inet:rdp:handshake :flow -> inet:flow'))
            self.len(1, await core.nodes('inet:rdp:handshake :client:hostname -> it:hostname'))

    async def test_inet_jarm(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:tls:jarmsample=(1.2.3.4:443, 07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1) ]')
            self.len(1, nodes)
            self.eq('tcp://1.2.3.4:443', nodes[0].get('server'))
            self.eq('07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1', nodes[0].get('jarmhash'))
            self.eq(('tcp://1.2.3.4:443', '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1'), nodes[0].ndef[1])

            nodes = await core.nodes('inet:tls:jarmhash=07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')
            self.len(1, nodes)
            self.eq('07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1', nodes[0].ndef[1])
            self.eq('07d14d16d21d21d07c42d41d00041d', nodes[0].get('ciphers'))
            self.eq('24a458a375eef0c576d23a7bab9a9fb1', nodes[0].get('extensions'))

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

            # Proto defaults to tcp
            subs = {'ip': (4, 16909060), 'proto': 'tcp'}
            virts = {'ip': ((4, 16909060), 26)}
            self.eq(await t.norm('1.2.3.4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))

            subs = {'ip': (4, 16909060), 'proto': 'tcp', 'port': 80}
            virts = {'ip': ((4, 16909060), 26), 'port': (80, 9)}
            self.eq(await t.norm('1.2.3.4:80'), ('tcp://1.2.3.4:80', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('https://192.168.1.1:80'))  # bad proto

            # IPv4
            subs = {'ip': (4, 16909060), 'proto': 'tcp'}
            virts = {'ip': ((4, 16909060), 26)}
            self.eq(await t.norm('tcp://1.2.3.4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))
            self.eq(await t.norm('tcp://1[.]2.3[.]4'), ('tcp://1.2.3.4', {'subs': subs, 'virts': virts}))

            subs = {'ip': (4, 16909060), 'proto': 'udp', 'port': 80}
            virts = {'ip': ((4, 16909060), 26), 'port': (80, 9)}
            self.eq(await t.norm('udp://1.2.3.4:80'), ('udp://1.2.3.4:80', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://1.2.3.4:-1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://1.2.3.4:66000'))

            # IPv6
            subs = {'ip': (6, 1), 'proto': 'icmp'}
            virts = {'ip': ((6, 1), 26)}
            self.eq(await t.norm('icmp://::1'), ('icmp://::1', {'subs': subs, 'virts': virts}))

            subs = {'ip': (6, 1), 'proto': 'tcp', 'port': 2}
            virts = {'ip': ((6, 1), 26), 'port': (2, 9)}
            self.eq(await t.norm('tcp://[::1]:2'), ('tcp://[::1]:2', {'subs': subs, 'virts': virts}))

            subs = {'ip': (6, 1), 'proto': 'tcp'}
            virts = {'ip': ((6, 1), 26)}
            self.eq(await t.norm('tcp://[::1]'), ('tcp://[::1]', {'subs': subs, 'virts': virts}))

            subs = {'ip': (6, 0xffff01020304), 'proto': 'tcp', 'port': 2}
            virts = {'ip': ((6, 0xffff01020304), 26), 'port': (2, 9)}
            self.eq(await t.norm('tcp://[::fFfF:0102:0304]:2'),
                    ('tcp://[::ffff:1.2.3.4]:2', {'subs': subs, 'virts': virts}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('tcp://[::1'))  # bad ipv6 w/ port

            # Host
            hstr = 'ffa3e574aa219e553e1b2fc1ccd0180f'
            self.eq(await t.norm('host://vertex.link'), (f'host://{hstr}', {'subs': {'host': hstr, 'proto': 'host'}}))
            self.eq(await t.norm('host://vertex.link:1337'),
                    (f'host://{hstr}:1337', {'subs': {'host': hstr, 'port': 1337, 'proto': 'host'}}))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('vertex.link'))  # must use host proto

    async def test_asn_collection(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:asn=123 :owner:name=COOL :owner={[ ou:org=* ]} ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asn', 123))
            self.eq(node.get('owner:name'), 'cool')
            self.len(1, await core.nodes('inet:asn :owner -> ou:org'))

            nodes = await core.nodes('[ inet:asnet=(54959, (1.2.3.4, 5.6.7.8)) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet', (54959, ((4, 0x01020304), (4, 0x05060708)))))
            self.eq(node.get('asn'), 54959)
            self.eq(node.get('net'), ((4, 0x01020304), (4, 0x05060708)))
            self.eq(node.get('net:min'), (4, 0x01020304))
            self.eq(node.get('net:max'), (4, 0x05060708))
            self.len(1, await core.nodes('inet:ip=1.2.3.4'))
            self.len(1, await core.nodes('inet:ip=5.6.7.8'))

            minv = (6, 0xff0000000000000000000000000000)
            maxv = (6, 0xff0000000000000000000000000100)
            nodes = await core.nodes('[ inet:asnet=(99, (ff::00, ff::0100)) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet', (99, (minv, maxv))))
            self.eq(node.get('asn'), 99)
            self.eq(node.get('net'), (minv, maxv))
            self.eq(node.get('net:min'), minv)
            self.eq(node.get('net:max'), maxv)
            self.len(1, await core.nodes('inet:ip="ff::"'))
            self.len(1, await core.nodes('inet:ip="ff::100"'))

    async def test_cidr4(self):
        formname = 'inet:cidr'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            valu = '0.0.0.0/24'
            expected = ('0.0.0.0/24', {'subs': {
                'broadcast': (4, 255),
                'network': (4, 0),
                'mask': 24,
            }})
            self.eq(await t.norm(valu), expected)

            valu = '192.168.1.101/24'
            expected = ('192.168.1.0/24', {'subs': {
                'broadcast': (4, 3232236031),  # 192.168.1.255
                'network': (4, 3232235776),    # 192.168.1.0
                'mask': 24,
            }})
            self.eq(await t.norm(valu), expected)

            valu = '123.123.0.5/30'
            expected = ('123.123.0.4/30', {'subs': {
                'broadcast': (4, 2071658503),  # 123.123.0.7
                'network': (4, 2071658500),    # 123.123.0.4
                'mask': 30,
            }})
            self.eq(await t.norm(valu), expected)

            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/-1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/33'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1/foo'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('10.0.0.1'))

            # Form Tests ======================================================
            valu = '192[.]168.1.123/24'
            expected_ndef = (formname, '192.168.1.0/24')  # ndef is network/mask, not ip/mask

            nodes = await core.nodes('[inet:cidr=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, expected_ndef)
            self.eq(node.get('network'), (4, 3232235776))  # 192.168.1.0
            self.eq(node.get('broadcast'), (4, 3232236031))  # 192.168.1.255
            self.eq(node.get('mask'), 24)

    async def test_cidr6(self):
        formname = 'inet:cidr'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            valu = '::/0'
            expected = ('::/0', {'subs': {
                'broadcast': (6, 0xffffffffffffffffffffffffffffffff),
                'network': (6, 0),
                'mask': 0,
            }})
            self.eq(await t.norm(valu), expected)

            valu = '2001:db8::/59'
            expected = ('2001:db8::/59', {'subs': {
                'broadcast': (6, 0x20010db80000001fffffffffffffffff),
                'network': (6, 0x20010db8000000000000000000000000),
                'mask': 59,
            }})
            self.eq(await t.norm(valu), expected)

            with self.raises(s_exc.BadTypeValu):
                await t.norm('10.0.0.1/-1')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:cidr=0::10.2.1.1/300')

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
            ('host://vertex.link:12345', 'host://ffa3e574aa219e553e1b2fc1ccd0180f:12345', {
                'host': 'ffa3e574aa219e553e1b2fc1ccd0180f',
                'port': 12345,
                'proto': 'host',
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

    async def test_download(self):
        async with self.getTestCore() as core:

            valu = s_common.guid()
            file = s_common.guid()
            props = {
                'time': 0,
                'file': file,
                'fqdn': 'vertex.link',
                'client': 'tcp://127.0.0.1:45654',
                'server': 'tcp://1.2.3.4:80'
            }
            q = '[(inet:download=$valu :time=$p.time :file=$p.file :fqdn=$p.fqdn :client=$p.client :server=$p.server)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:download', valu))
            self.eq(node.get('time'), 0)
            self.eq(node.get('file'), file)
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('client'), 'tcp://127.0.0.1:45654')
            self.eq(node.get('server'), 'tcp://1.2.3.4:80')

    async def test_email(self):
        formname = 'inet:email'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {'fqdn': 'vertex.link', 'user': 'unittest'}})
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
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('user'), 'unittest')

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
                    :server:txfiles={[ file:attachment=* :name=bar.exe ]}
                    :server:softnames=(FooBar, bazfaz)
                    :server:cpes=("cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*", "cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*")

                    :client=5.5.5.5
                    :client:host=*
                    :client:proc=*
                    :client:txcount=30
                    :client:txbytes=1
                    :client:handshake="Hello There"
                    :client:txfiles={[ file:attachment=* :name=foo.exe ]}
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
            self.eq(nodes[0].get('client'), 'tcp://5.5.5.5')
            self.eq(nodes[0].get('client:txcount'), 30)
            self.eq(nodes[0].get('client:txbytes'), 1)
            self.eq(nodes[0].get('client:handshake'), 'Hello There')
            self.eq(nodes[0].get('client:softnames'), ('haha', 'hehe'))
            self.eq(nodes[0].get('client:cpes'), ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)

            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:443')
            self.eq(nodes[0].get('server:txcount'), 33)
            self.eq(nodes[0].get('server:txbytes'), 2)
            self.eq(nodes[0].get('server:handshake'), 'OHai!')
            self.eq(nodes[0].get('server:softnames'), ('bazfaz', 'foobar'))
            self.eq(nodes[0].get('server:cpes'), ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)

            self.eq(nodes[0].get('tot:txcount'), 63)
            self.eq(nodes[0].get('tot:txbytes'), 3)
            self.eq(nodes[0].get('ip:proto'), 6)
            self.eq(nodes[0].get('ip:tcp:flags'), 0x20)

            self.len(1, await core.nodes('inet:flow :client:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :server:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :client:proc -> it:exec:proc'))
            self.len(1, await core.nodes('inet:flow :server:proc -> it:exec:proc'))

            self.len(1, await core.nodes('inet:flow :client:txfiles -> file:attachment +:name=foo.exe'))
            self.len(1, await core.nodes('inet:flow :server:txfiles -> file:attachment +:name=bar.exe'))

            self.len(1, await core.nodes('inet:flow :capture:host -> it:host'))
            self.len(1, await core.nodes('inet:flow :sandbox:file -> file:bytes'))

    async def test_fqdn(self):
        formname = 'inet:fqdn'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            fqdn = 'example.Vertex.link'
            expected = ('example.vertex.link', {'subs': {'host': 'example', 'domain': 'vertex.link'}})
            self.eq(await t.norm(fqdn), expected)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('!@#$%'))

            # defanging works
            self.eq(await t.norm('example[.]vertex(.)link'), expected)

            # Demonstrate Valid IDNA
            fqdn = 'tèst.èxamplè.link'
            ex_fqdn = 'xn--tst-6la.xn--xampl-3raf.link'
            expected = (ex_fqdn, {'subs': {'domain': 'xn--xampl-3raf.link', 'host': 'xn--tst-6la'}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)  # Calling repr on IDNA encoded domain should result in the unicode

            # Use IDNA2008 if possible
            fqdn = "faß.de"
            ex_fqdn = 'xn--fa-hia.de'
            expected = (ex_fqdn, {'subs': {'domain': 'de', 'host': 'xn--fa-hia'}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Emojis are valid IDNA2003
            fqdn = '👁👄👁.fm'
            ex_fqdn = 'xn--mp8hai.fm'
            expected = (ex_fqdn, {'subs': {'domain': 'fm', 'host': 'xn--mp8hai'}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Variant forms get normalized
            varfqdn = '👁️👄👁️.fm'
            self.eq(await t.norm(varfqdn), expected)
            self.ne(varfqdn, fqdn)

            # Unicode full stops are okay but get normalized
            fqdn = 'foo(．)bar[。]baz｡lol'
            ex_fqdn = 'foo.bar.baz.lol'
            expected = (ex_fqdn, {'subs': {'domain': 'bar.baz.lol', 'host': 'foo'}})
            self.eq(await t.norm(fqdn), expected)

            # Ellipsis shouldn't make it through
            await self.asyncraises(s_exc.BadTypeValu, t.norm('vertex…link'))

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'link'}})
            self.eq(await t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))  # UnicodeError raised and caught and fallback to norm

            fqdn = 'xn--cc.bartmp.l.google.com'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'bartmp.l.google.com'}})
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
            self.eq(node.get('domain'), 'vertex.link')
            self.eq(node.get('host'), 'api')
            self.eq(node.get('issuffix'), 0)
            self.eq(node.get('iszone'), 0)
            self.eq(node.get('zone'), 'vertex.link')

            nodes = await core.nodes('inet:fqdn=vertex.link')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:fqdn', 'vertex.link'))
            self.eq(node.get('domain'), 'link')
            self.eq(node.get('host'), 'vertex')
            self.eq(node.get('issuffix'), 0)
            self.eq(node.get('iszone'), 1)
            self.eq(node.get('zone'), 'vertex.link')

            nodes = await core.nodes('inet:fqdn=link')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:fqdn', 'link'))
            self.eq(node.get('host'), 'link')
            self.eq(node.get('issuffix'), 1)
            self.eq(node.get('iszone'), 0)
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
            self.eq(nodes[0].get('zone'), 'foo.com')

            nodes = await core.nodes('[inet:fqdn=vertex.link :seen=(2020,2021)]')
            self.len(1, nodes)
            self.eq(nodes[0].get('seen'), (1577836800000000, 1609459200000000))

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

    async def test_group(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:group="cool Group"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:group', 'cool Group'))

    async def test_http_cookie(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:cookie="HeHe=HaHa"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:cookie', 'HeHe=HaHa'))
            self.eq(node.get('name'), 'HeHe')
            self.eq(node.get('value'), 'HaHa')

            nodes = await core.nodes('''
                [ inet:http:request=* :cookies={[ inet:http:cookie="foo=bar; baz=faz;" ]} ]
            ''')
            self.eq(nodes[0].get('cookies'), ('baz=faz', 'foo=bar'))

            nodes = await core.nodes('''
                [ inet:http:session=* :cookies={[ inet:http:cookie="foo=bar; baz=faz;" ]} ]
            ''')
            self.eq(nodes[0].get('cookies'), ('baz=faz', 'foo=bar'))

            nodes = await core.nodes('[ inet:http:cookie=(lol, lul) ]')
            self.len(2, nodes)

    async def test_http_request_header(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:request:header=(Cool, Cooler)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:request:header', ('cool', 'Cooler')))
            self.eq(node.get('name'), 'cool')
            self.eq(node.get('value'), 'Cooler')

    async def test_http_response_header(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:http:response:header=(Cool, Cooler)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:http:response:header', ('cool', 'Cooler')))
            self.eq(node.get('name'), 'cool')
            self.eq(node.get('value'), 'Cooler')

    async def test_http_param(self):
        async with self.getTestCore() as core:
            async with self.getTestCore() as core:
                nodes = await core.nodes('[inet:http:param=(Cool, Cooler)]')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, ('inet:http:param', ('Cool', 'Cooler')))
                self.eq(node.get('name'), 'cool')
                self.eq(node.get('value'), 'Cooler')

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
            self.eq(node.get('time'), 1420070400000000)
            self.eq(node.get('flow'), flow)
            self.eq(node.get('method'), 'gEt')
            self.eq(node.get('query'), 'hoho=1&qaz=bar')
            self.eq(node.get('path'), '/woot/hehe/')
            self.eq(node.get('body'), body)
            self.eq(node.get('response:code'), 200)
            self.eq(node.get('response:reason'), 'OK')
            self.eq(node.get('response:headers'), (('baz', 'faz'),))
            self.eq(node.get('response:body'), body)
            self.eq(node.get('session'), sess)
            self.eq(node.get('sandbox:file'), sand)
            self.eq(node.get('client'), 'tcp://1.2.3.4')
            self.eq(node.get('client:host'), client)
            self.eq(node.get('server'), 'tcp://5.5.5.5:443')
            self.eq(node.get('server:host'), server)

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
            self.eq(node.get('host'), host)
            self.eq(node.get('network'), netw)
            self.eq(node.get('type'), 'cool.')
            self.eq(node.get('mac'), 'ff:00:ff:00:ff:00')
            self.eq(node.get('ip'), (4, 0x01020304))
            self.eq(node.get('phone'), '12345678910')
            self.eq(node.get('wifi:ap:ssid'), 'hehe haha')
            self.eq(node.get('wifi:ap:bssid'), '00:ff:00:ff:00:ff')
            self.eq(node.get('mob:imei'), 123456789012347)
            self.eq(node.get('mob:imsi'), 12345678901234)

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

            info = {'subs': {'type': 'unicast', 'version': 4}}
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
            self.eq(info.get('subs').get('type'), 'linklocal')

            norm, info = await t.norm('100.63.255.255')
            self.eq(info.get('subs').get('type'), 'unicast')

            norm, info = await t.norm('100.64.0.0')
            self.eq(info.get('subs').get('type'), 'shared')

            norm, info = await t.norm('100.127.255.255')
            self.eq(info.get('subs').get('type'), 'shared')

            norm, info = await t.norm('100.128.0.0')
            self.eq(info.get('subs').get('type'), 'unicast')

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
            self.eq(nodes[0].get('asn'), 3)
            self.eq(nodes[0].get('type'), 'unicast')
            self.eq(nodes[0].get('dns:rev'), 'vertex.link')
            self.eq(nodes[0].get('place:loc'), 'us')
            self.eq(nodes[0].get('place:latlong'), (-50.12345, 150.56789))
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
            self.eq(nodes[0].get('seen'), (1577836800000000, 1609459200000000))

    async def test_ipv6(self):
        formname = 'inet:ip'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            info = {'subs': {'type': 'loopback', 'scope': 'link-local', 'version': 6}}
            self.eq(await t.norm('::1'), ((6, 1), info))
            self.eq(await t.norm('0:0:0:0:0:0:0:1'), ((6, 1), info))

            addrnorm = (6, 0xff010000000000000000000000000001)
            info = {'subs': {'type': 'multicast', 'scope': 'interface-local', 'version': 6}}
            self.eq(await t.norm('ff01::1'), (addrnorm, info))

            addrnorm = (6, 0x20010db8000000000000ff0000428329)
            info = {'subs': {'type': 'private', 'scope': 'global', 'version': 6}}
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
            self.eq(info.get('subs').get('type'), 'linklocal')

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
            self.eq(node.get('vendor:name'), 'cool')

            self.len(1, await core.nodes('inet:mac -> ou:org'))

    async def test_net4(self):
        tname = 'inet:net'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('1.2.3.4', '5.6.7.8')
            expected = (((4, 16909060), (4, 84281096)), {'subs': {'min': (4, 16909060), 'max': (4, 84281096)}})
            self.eq(await t.norm(valu), expected)

            valu = '1.2.3.4-5.6.7.8'
            self.eq(await t.norm(valu), expected)

            valu = '1.2.3.0/24'
            expected = (((4, 0x01020300), (4, 0x010203ff)), {'subs': {'min': (4, 0x01020300), 'max': (4, 0x010203ff)}})
            self.eq(await t.norm(valu), expected)

            valu = '5.6.7.8-1.2.3.4'
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            valu = ('1.2.3.4', '5.6.7.8', '7.8.9.10')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

    async def test_net6(self):
        tname = 'inet:net'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('0:0:0:0:0:0:0:0', '::Ff')
            expected = (((6, 0), (6, 0xff)), {'subs': {'min': (6, 0), 'max': (6, 0xff)}})
            self.eq(await t.norm(valu), expected)

            valu = '0:0:0:0:0:0:0:0-::Ff'
            self.eq(await t.norm(valu), expected)

            # Test case in which ipaddress ordering is not alphabetical
            minv = (6, 0x33000100000000000000000000000000)
            maxv = (6, 0x3300010000010000000000000000ffff)
            valu = ('3300:100::', '3300:100:1::ffff')
            expected = ((minv, maxv), {'subs': {'min': minv, 'max': maxv}})
            self.eq(await t.norm(valu), expected)

            minv = (6, 0x20010db8000000000000000000000000)
            maxv = (6, 0x20010db8000000000000000007ffffff)
            valu = '2001:db8::/101'
            expected = ((minv, maxv), {'subs': {'min': minv, 'max': maxv}})
            self.eq(await t.norm(valu), expected)

            valu = ('fe00::', 'fd00::')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            valu = ('fd00::', 'fe00::', 'ff00::')
            await self.asyncraises(s_exc.BadTypeValu, t.norm(valu))

            with self.raises(s_exc.BadTypeValu):
                await t.norm(((6, 1), (4, 1)))

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

            self.eq(await t.norm('FooBar'), ('foobar', {'subs': {}}))
            self.eq(await t.norm('visi@vertex.link'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))
            self.eq(await t.norm('foo bar<visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(await t.norm('foo bar <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(await t.norm('"foo bar "   <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(await t.norm('<visi@vertex.link>'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))

            valu = (await t.norm('bob\udcfesmith@woot.com'))[0]
            self.eq(valu, 'bob\udcfesmith@woot.com')

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:rfc2822:addr=$valu]',
                                     opts={'vars': {'valu': '"UnitTest"    <UnitTest@Vertex.link>'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:rfc2822:addr', 'unittest <unittest@vertex.link>'))
            self.eq(node.get('email'), 'unittest@vertex.link')
            self.eq(node.get('name'), 'unittest')

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
            ('host://vertex.link:12345', 'host://ffa3e574aa219e553e1b2fc1ccd0180f:12345', {
                'host': 'ffa3e574aa219e553e1b2fc1ccd0180f',
                'port': 12345,
                'proto': 'host',
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
            self.eq(nodes[0].get('dns:resolvers'), ('udp://0.0.0.1:53',))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=(([6, 1]),)]')
            self.eq(nodes[0].get('dns:resolvers'), ('udp://[::1]:53',))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=("::1",)]')
            self.eq(nodes[0].get('dns:resolvers'), ('udp://[::1]:53',))

            nodes = await core.nodes('[ it:network=* :dns:resolvers=("[::1]",)]')
            self.eq(nodes[0].get('dns:resolvers'), ('udp://[::1]:53',))

            nodes = await core.nodes('[ inet:server=gre://::1 ]')
            self.eq(nodes[0].get('proto'), 'gre')

            nodes = await core.nodes('[ inet:server=gre://1.2.3.4 ]')
            self.eq(nodes[0].get('proto'), 'gre')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server=gre://1.2.3.4:99 ]')

            self.eq(ctx.exception.get('mesg'), 'Protocol gre does not allow specifying ports.')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server="gre://[::1]:99" ]')

            self.eq(ctx.exception.get('mesg'), 'Protocol gre does not allow specifying ports.')

            with self.raises(s_exc.BadTypeValu) as ctx:
                await core.nodes('[ inet:server=newp://1.2.3.4:99 ]')

            self.eq(ctx.exception.get('mesg'), 'inet:sockaddr protocol must be one of: tcp,udp,icmp,host,gre')

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
                    'proto': 'http',
                    'path': '/hehe\udcfestuff.asp',
                    'port': 80,
                    'params': '',
                    'fqdn': 'www.googlesites.com',
                    'base': url
                }})
                self.eq(valu, expected)

            for proto in ('https', 'hxxps', 'hXXps'):
                url = f'https://dummyimage.com/600x400/000/fff.png&text=cat@bam.com'
                valu = await t.norm(f'{proto}://dummyimage.com/600x400/000/fff.png&text=cat@bam.com')
                expected = (url, {'subs': {
                    'base': url,
                    'proto': 'https',
                    'path': '/600x400/000/fff.png&text=cat@bam.com',
                    'port': 443,
                    'params': '',
                    'fqdn': 'dummyimage.com'
                }})
                self.eq(valu, expected)

            url = 'http://0.0.0.0/index.html?foo=bar'
            valu = await t.norm(url)
            expected = (url, {'subs': {
                'proto': 'http',
                'path': '/index.html',
                'params': '?foo=bar',
                'ip': (4, 0),
                'port': 80,
                'base': 'http://0.0.0.0/index.html'
            }})
            self.eq(valu, expected)

            url = '  http://0.0.0.0/index.html?foo=bar  '
            valu = await t.norm(url)
            expected = (url.strip(), {'subs': {
                'proto': 'http',
                'path': '/index.html',
                'params': '?foo=bar',
                'ip': (4, 0),
                'port': 80,
                'base': 'http://0.0.0.0/index.html'
            }})
            self.eq(valu, expected)

            unc = '\\\\0--1.ipv6-literal.net\\share\\path\\to\\filename.txt'
            url = 'smb://::1/share/path/to/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': url,
                'proto': 'smb',
                'params': '',
                'path': '/share/path/to/filename.txt',
                'ip': (6, 1),
            }})
            self.eq(valu, expected)

            unc = '\\\\0--1.ipv6-literal.net@1234\\share\\filename.txt'
            url = 'smb://[::1]:1234/share/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': url,
                'proto': 'smb',
                'path': '/share/filename.txt',
                'params': '',
                'port': 1234,
                'ip': (6, 1),
            }})
            self.eq(valu, expected)

            unc = '\\\\server@SSL@1234\\share\\path\\to\\filename.txt'
            url = 'https://server:1234/share/path/to/filename.txt'
            valu = await t.norm(unc)
            expected = (url, {'subs': {
                'base': url,
                'proto': 'https',
                'fqdn': 'server',
                'params': '',
                'port': 1234,
                'path': '/share/path/to/filename.txt',
            }})
            self.eq(valu, expected)

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:url="https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:url', 'https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1'))
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('passwd'), 'hunter2')
            self.eq(node.get('path'), '/coolthings')
            self.eq(node.get('port'), 1337)
            self.eq(node.get('proto'), 'https')
            self.eq(node.get('user'), 'vertexmc')
            self.eq(node.get('base'), 'https://vertexmc:hunter2@vertex.link:1337/coolthings')
            self.eq(node.get('params'), '?a=1')

            nodes = await core.nodes('[inet:url="https://vertex.link?a=1"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:url', 'https://vertex.link?a=1'))
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('path'), '')

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
            self.eq(nodes[0].get('base'), 'http://[fedc:ba98:7654:3210:fedc:ba98:7654:3210]:80/index.html')
            self.eq(nodes[0].get('proto'), 'http')
            self.eq(nodes[0].get('path'), '/index.html')
            self.eq(nodes[0].get('params'), '')
            self.eq(nodes[0].get('ip'), (6, 0xfedcba9876543210fedcba9876543210))
            self.eq(nodes[0].get('port'), 80)

            self.eq(nodes[1].get('base'), 'http://[1080::8:800:200c:417a]/index.html')
            self.eq(nodes[1].get('proto'), 'http')
            self.eq(nodes[1].get('path'), '/index.html')
            self.eq(nodes[1].get('params'), '?foo=bar')
            self.eq(nodes[1].get('ip'), (6, 0x108000000000000000080800200c417a))
            self.eq(nodes[1].get('port'), 80)

            self.eq(nodes[2].get('base'), 'http://[3ffe:2a00:100:7031::1]')
            self.eq(nodes[2].get('proto'), 'http')
            self.eq(nodes[2].get('path'), '')
            self.eq(nodes[2].get('params'), '')
            self.eq(nodes[2].get('ip'), (6, 0x3ffe2a00010070310000000000000001))
            self.eq(nodes[2].get('port'), 80)

            self.eq(nodes[3].get('base'), 'http://[1080::8:800:200c:417a]/foo')
            self.eq(nodes[3].get('proto'), 'http')
            self.eq(nodes[3].get('path'), '/foo')
            self.eq(nodes[3].get('params'), '')
            self.eq(nodes[3].get('ip'), (6, 0x108000000000000000080800200c417a))
            self.eq(nodes[3].get('port'), 80)

            self.eq(nodes[4].get('base'), 'http://[::192.9.5.5]/ipng')
            self.eq(nodes[4].get('proto'), 'http')
            self.eq(nodes[4].get('path'), '/ipng')
            self.eq(nodes[4].get('params'), '')
            self.eq(nodes[4].get('ip'), (6, 0xc0090505))
            self.eq(nodes[4].get('port'), 80)

            self.eq(nodes[5].get('base'), 'http://[::ffff:129.144.52.38]:80/index.html')
            self.eq(nodes[5].get('proto'), 'http')
            self.eq(nodes[5].get('path'), '/index.html')
            self.eq(nodes[5].get('params'), '')
            self.eq(nodes[5].get('ip'), (6, 0xffff81903426))
            self.eq(nodes[5].get('port'), 80)

            self.eq(nodes[6].get('base'), 'https://[2010:836b:4179::836b:4179]')
            self.eq(nodes[6].get('proto'), 'https')
            self.eq(nodes[6].get('path'), '')
            self.eq(nodes[6].get('params'), '')
            self.eq(nodes[6].get('ip'), (6, 0x2010836b4179000000000000836b4179))
            self.eq(nodes[6].get('port'), 443)

    async def test_url_file(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:////'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file://///'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file://'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:'))

            url = 'file:///'
            expected = (url, {'subs': {
                'base': url,
                'path': '/',
                'proto': 'file',
                'params': '',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///home/foo/Documents/html/index.html'
            expected = (url, {'subs': {
                'base': url,
                'path': '/home/foo/Documents/html/index.html',
                'proto': 'file',
                'params': '',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///c:/path/to/my/file.jpg'
            expected = (url, {'subs': {
                'base': url,
                'path': 'c:/path/to/my/file.jpg',
                'params': '',
                'proto': 'file'
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://localhost/c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': 'c:/Users/BarUser/stuff/moar/stuff.txt',
                'params': '',
                'fqdn': 'localhost',
                'base': url,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:///c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': 'c:/Users/BarUser/stuff/moar/stuff.txt',
                'params': '',
                'base': url,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://localhost/home/visi/synapse/README.rst'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': '/home/visi/synapse/README.rst',
                'params': '',
                'fqdn': 'localhost',
                'base': url,
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/C:/invisig0th/code/synapse/README.rst'
            expected = ('file:///C:/invisig0th/code/synapse/README.rst', {'subs': {
                'proto': 'file',
                'path': 'C:/invisig0th/code/synapse/README.rst',
                'params': '',
                'base': 'file:///C:/invisig0th/code/synapse/README.rst'
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://somehost/path/to/foo.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/path/to/foo.txt',
                'fqdn': 'somehost',
                'base': url
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/c:/foo/bar/baz/single/slash.txt'
            expected = ('file:///c:/foo/bar/baz/single/slash.txt', {'subs': {
                'proto': 'file',
                'params': '',
                'path': 'c:/foo/bar/baz/single/slash.txt',
                'base': 'file:///c:/foo/bar/baz/single/slash.txt',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:c:/foo/bar/baz/txt'
            expected = ('file:///c:/foo/bar/baz/txt', {'subs': {
                'proto': 'file',
                'params': '',
                'path': 'c:/foo/bar/baz/txt',
                'base': 'file:///c:/foo/bar/baz/txt',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file:/home/visi/synapse/synapse/lib/'
            expected = ('file:///home/visi/synapse/synapse/lib/', {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/home/visi/synapse/synapse/lib/',
                'base': 'file:///home/visi/synapse/synapse/lib/',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://foo.vertex.link/home/bar/baz/biz.html'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': '/home/bar/baz/biz.html',
                'params': '',
                'fqdn': 'foo.vertex.link',
                'base': 'file://foo.vertex.link/home/bar/baz/biz.html',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': 'file',
                'fqdn': 'somehost.vertex.link',
                'base': 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/',
                'path': 'c:/invisig0th/code/synapse/',
                'user': 'visi@vertex.link',
                'params': '',
            }})
            self.eq(await t.norm(url), expected)

            url = 'file://foo@bar.com:neato@password@7.7.7.7/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': 'file',
                'base': 'file://foo@bar.com:neato@password@7.7.7.7/c:/invisig0th/code/synapse/',
                'ip': (4, 117901063),
                'path': 'c:/invisig0th/code/synapse/',
                'user': 'foo@bar.com',
                'passwd': 'neato@password',
                'params': '',
            }})
            self.eq(await t.norm(url), expected)

            # not allowed by the rfc
            await self.asyncraises(s_exc.BadTypeValu, t.norm('file:foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/'))

            # Also an invalid URL, but doesn't cleanly fall out, because well, it could be a valid filename
            url = 'file:/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/'
            expected = ('file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/', {'subs': {
                'proto': 'file',
                'path': '/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/',
                'params': '',
                'base': 'file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/',
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.2
            url = 'file://visi@vertex.link:password@somehost.vertex.link:9876/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': 'c:/invisig0th/code/synapse/',
                'user': 'visi@vertex.link',
                'passwd': 'password',
                'fqdn': 'somehost.vertex.link',
                'params': '',
                'port': 9876,
                'base': url,
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.2.2
            url = 'FILE:c|/synapse/synapse/lib/stormtypes.py'
            expected = ('file:///c|/synapse/synapse/lib/stormtypes.py', {'subs': {
                'path': 'c|/synapse/synapse/lib/stormtypes.py',
                'proto': 'file',
                'params': '',
                'base': 'file:///c|/synapse/synapse/lib/stormtypes.py',
            }})
            self.eq(await t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.3.2
            url = 'file:////host.vertex.link/SharedDir/Unc/FilePath'
            expected = ('file:////host.vertex.link/SharedDir/Unc/FilePath', {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/SharedDir/Unc/FilePath',
                'fqdn': 'host.vertex.link',
                'base': 'file:////host.vertex.link/SharedDir/Unc/FilePath',
            }})
            self.eq(await t.norm(url), expected)

            # Firefox's non-standard representation that appears every so often
            # supported because the RFC supports it
            url = 'file://///host.vertex.link/SharedDir/Firefox/Unc/File/Path'
            expected = ('file:////host.vertex.link/SharedDir/Firefox/Unc/File/Path', {'subs': {
                'proto': 'file',
                'params': '',
                'base': 'file:////host.vertex.link/SharedDir/Firefox/Unc/File/Path',
                'path': '/SharedDir/Firefox/Unc/File/Path',
                'fqdn': 'host.vertex.link',
            }})
            self.eq(await t.norm(url), expected)

    async def test_url_fqdn(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            host = 'Vertex.Link'
            norm_host = (await core.model.type('inet:fqdn').norm(host))[0]
            repr_host = core.model.type('inet:fqdn').repr(norm_host)

            self.eq(norm_host, 'vertex.link')
            self.eq(repr_host, 'vertex.link')

            await self._test_types_url_behavior(t, 'fqdn', host, norm_host, repr_host)

    async def test_url_ipv4(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '192[.]168.1[.]1'
            norm_host = (await core.model.type('inet:ip').norm(host))[0]
            repr_host = core.model.type('inet:ip').repr(norm_host)
            self.eq(norm_host, (4, 3232235777))
            self.eq(repr_host, '192.168.1.1')

            await self._test_types_url_behavior(t, 'ipv4', host, norm_host, repr_host)

    async def test_url_ipv6(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '::1'
            norm_host = (await core.model.type('inet:ip').norm(host))[0]
            repr_host = core.model.type('inet:ip').repr(norm_host)
            self.eq(norm_host, (6, 1))
            self.eq(repr_host, '::1')

            await self._test_types_url_behavior(t, 'ipv6', host, norm_host, repr_host)

            # IPv6 Port Special Cases
            weird = await t.norm('http://::1:81/hehe')
            self.eq(weird[1]['subs']['ip'], (6, 0x10081))
            self.eq(weird[1]['subs']['port'], 80)

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
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 1234,
            'base': f'https://user:password@{repr_host_port}:1234/a/b/c/',
            'params': ''
        }})
        self.eq(await t.norm(url), expected)

        # Userinfo user with @ in it
        url = f'lando://visi@vertex.link@{host_port}:40000/auth/gateway'
        expected = (f'lando://visi@vertex.link@{repr_host_port}:40000/auth/gateway', {'subs': {
            'proto': 'lando', 'path': '/auth/gateway',
            'user': 'visi@vertex.link',
            'base': f'lando://visi@vertex.link@{repr_host_port}:40000/auth/gateway',
            'port': 40000,
            'params': '',
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # Userinfo password with @
        url = f'balthazar://root:foo@@@bar@{host_port}:1234/'
        expected = (f'balthazar://root:foo@@@bar@{repr_host_port}:1234/', {'subs': {
            'proto': 'balthazar', 'path': '/',
            'user': 'root', 'passwd': 'foo@@@bar',
            'base': f'balthazar://root:foo@@@bar@{repr_host_port}:1234/',
            'port': 1234,
            'params': '',
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # rfc3986 compliant Userinfo with @ properly encoded
        url = f'calrissian://visi%40vertex.link:surround%40@{host_port}:44343'
        expected = (f'calrissian://visi%40vertex.link:surround%40@{repr_host_port}:44343', {'subs': {
            'proto': 'calrissian', 'path': '',
            'user': 'visi@vertex.link', 'passwd': 'surround@',
            'base': f'calrissian://visi%40vertex.link:surround%40@{repr_host_port}:44343',
            'port': 44343,
            'params': '',
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # unencoded query params are handled nicely
        url = f'https://visi@vertex.link:neato@burrito@{host}/?q=@foobarbaz'
        expected = (f'https://visi@vertex.link:neato@burrito@{repr_host}/?q=@foobarbaz', {'subs': {
            'proto': 'https', 'path': '/',
            'user': 'visi@vertex.link', 'passwd': 'neato@burrito',
            'base': f'https://visi@vertex.link:neato@burrito@{repr_host}/',
            'port': 443,
            'params': '?q=@foobarbaz',
            htype: norm_host,
        }})
        self.eq(await t.norm(url), expected)

        # URL with no port, but default port valu.
        # Port should be in subs, but not normed URL.
        url = f'https://user:password@{host}/a/b/c/?foo=bar&baz=faz'
        expected = (f'https://user:password@{repr_host}/a/b/c/?foo=bar&baz=faz', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 443,
            'base': f'https://user:password@{repr_host}/a/b/c/',
            'params': '?foo=bar&baz=faz',
        }})
        self.eq(await t.norm(url), expected)

        # URL with no port and no default port valu.
        # Port should not be in subs or normed URL.
        url = f'arbitrary://user:password@{host}/a/b/c/'
        expected = (f'arbitrary://user:password@{repr_host}/a/b/c/', {'subs': {
            'proto': 'arbitrary', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host,
            'base': f'arbitrary://user:password@{repr_host}/a/b/c/',
            'params': '',
        }})
        self.eq(await t.norm(url), expected)

        # URL with user but no password.
        # User should still be in URL and subs.
        url = f'https://user@{host_port}:1234/a/b/c/'
        expected = (f'https://user@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', htype: norm_host, 'port': 1234,
            'base': f'https://user@{repr_host_port}:1234/a/b/c/',
            'params': '',
        }})
        self.eq(await t.norm(url), expected)

        # URL with no user/password.
        # User/Password should not be in URL or subs.
        url = f'https://{host_port}:1234/a/b/c/'
        expected = (f'https://{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', htype: norm_host, 'port': 1234,
            'base': f'https://{repr_host_port}:1234/a/b/c/',
            'params': '',
        }})
        self.eq(await t.norm(url), expected)

        # URL with no path.
        url = f'https://{host_port}:1234'
        expected = (f'https://{repr_host_port}:1234', {'subs': {
            'proto': 'https', 'path': '', htype: norm_host, 'port': 1234,
            'base': f'https://{repr_host_port}:1234',
            'params': '',
        }})
        self.eq(await t.norm(url), expected)

        # URL with no path or port or default port.
        url = f'a://{host}'
        expected = (f'a://{repr_host}', {'subs': {
            'proto': 'a', 'path': '', htype: norm_host,
            'base': f'a://{repr_host}',
            'params': '',
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
            self.eq(node.get('url'), 'https://vertex.link/a_cool_program.exe')
            self.eq(node.get('file'), file)

            url = await core.nodes('inet:url')
            self.len(1, url)
            url = url[0]
            self.eq(443, url.get('port'))
            self.eq('', url.get('params'))
            self.eq('vertex.link', url.get('fqdn'))
            self.eq('https', url.get('proto'))
            self.eq('https://vertex.link/a_cool_program.exe', url.get('base'))

    async def test_url_mirror(self):
        url0 = 'http://vertex.link'
        url1 = 'http://vtx.lk'
        opts = {'vars': {'url0': url0, 'url1': url1}}
        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:url:mirror=($url0, $url1) ]', opts=opts)

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:url:mirror', (url0, url1)))
            self.eq(nodes[0].get('at'), 'http://vtx.lk')
            self.eq(nodes[0].get('of'), 'http://vertex.link')

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
            self.eq(node.get('source'), 'https://vertex.link/idk')
            self.eq(node.get('target'), 'https://cool.vertex.newp:443/something_else')
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
            self.eq(node.get('time'), 2554869000000000)
            self.eq(node.get('fqdn'), 'arin.whois.net')
            self.eq(node.get('success'), True)
            self.eq(node.get('rec'), rec)
            self.eq(node.get('ip'), (4, 167772160))

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
            self.eq(node.get('time'), 2554869000000000)
            self.eq(node.get('url'), 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff')
            self.eq(node.get('success'), False)
            self.none(node.get('rec'))
            self.eq(node.get('ip'), (6, 0x3300010000010000000000000000ffff))

    async def test_whois_record(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ inet:whois:record=0c63f6b67c9a3ca40f9f942957a718e9
                    :fqdn=woot.com
                    :text="YELLING AT pennywise@vertex.link LOUDLY"
                    :registrar=' cool REGISTRAR'
                    :registrant=' cool REGISTRANT'
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:record', '0c63f6b67c9a3ca40f9f942957a718e9'))
            self.eq(node.get('fqdn'), 'woot.com')
            self.eq(node.get('text'), 'yelling at pennywise@vertex.link loudly')
            self.eq(node.get('registrar'), 'cool registrar')
            self.eq(node.get('registrant'), 'cool registrant')

            nodes = await core.nodes('inet:whois:email')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:whois:email', ('woot.com', 'pennywise@vertex.link')))

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
                :links=$p.links)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': rec_ipv4, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:iprecord', rec_ipv4))
            self.eq(node.get('net'), ((4, 167772160), (4, 167772175)))
            # FIXME virtual props
            # self.eq(node.get('net*min'), (4, 167772160))
            # self.eq(node.get('net*max'), (4, 167772175))
            self.eq(node.get('created'), 2554858000000000)
            self.eq(node.get('updated'), 2554858000000000)
            self.eq(node.get('text'), 'this is  a bunch of \nrecord text 123123')
            self.eq(node.get('asn'), 12345)
            self.eq(node.get('id'), 'NET-10-0-0-0-1')
            self.eq(node.get('name'), 'vtx')
            self.eq(node.get('parentid'), 'NET-10-0-0-0-0')
            self.eq(node.get('contacts'), (addlcontact,))
            self.eq(node.get('country'), 'us')
            self.eq(node.get('status'), 'validated')
            self.eq(node.get('type'), 'direct allocation')
            self.eq(node.get('links'), ('http://rdap.com/foo', 'http://rdap.net/bar'))

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
            self.eq(node.get('net'), (minv, maxv))
            # FIXME virtual props
            # self.eq(node.get('net*min'), minv)
            # self.eq(node.get('net*max'), maxv)
            self.eq(node.get('created'), 2554858000000000)
            self.eq(node.get('updated'), 2554858000000000)
            self.eq(node.get('text'), 'this is  a bunch of \nrecord text 123123')
            self.eq(node.get('asn'), 12345)
            self.eq(node.get('id'), 'NET-10-0-0-0-0')
            self.eq(node.get('name'), 'EU-VTX-1')
            self.eq(node.get('country'), 'tp')
            self.eq(node.get('status'), 'renew prohibited')
            self.eq(node.get('type'), 'allocated-by-rir')

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
            self.eq(node.get('ssid'), 'The Best SSID2 ')
            self.eq(node.get('bssid'), '00:11:22:33:44:55')
            self.eq(node.get('place:latlong'), (20.0, 30.0))
            self.eq(node.get('place:latlong:accuracy'), 10000000)
            self.eq(node.get('channel'), 99)
            self.eq(node.get('encryption'), 'wpa2')

            self.len(1, await core.nodes('inet:wifi:ap -> geo:place'))

    async def test_banner(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:banner=("tcp://1.2.3.4:443", "Hi There")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('text'), 'Hi There')
            self.eq(node.get('server'), 'tcp://1.2.3.4:443')

            self.len(1, await core.nodes('it:dev:str="Hi There"'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4'))

            nodes = await core.nodes('[inet:banner=("tcp://::ffff:8.7.6.5", sup)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('text'), 'sup')
            self.eq(node.get('server'), 'tcp://::ffff:8.7.6.5')

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
            self.eq(node.get('time'), 200)
            self.eq(node.get('text'), 'hi there')
            self.eq(node.get('engine'), 'roofroof')
            self.eq(node.get('host'), host)
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
            self.eq(node.get('url'), 'http://hehehaha.com/')
            self.eq(node.get('rank'), 0)
            self.eq(node.get('text'), 'woot woot woot')
            self.eq(node.get('title'), 'this is a title')
            self.eq(node.get('query'), iden)

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
                    inet:email:message:attachment=*
                        :file=*
                        :name=sploit.exe
                ]}
            ]
            '''
            nodes = await core.nodes(q, opts={'vars': {'flow': flow}})
            self.len(1, nodes)

            self.eq(nodes[0].get('id'), 'Woot-12345')
            self.eq(nodes[0].get('cc'), ('baz@faz.org', 'foo@bar.com'))
            self.eq(nodes[0].get('received:from:ip'), (4, 0x01020304))
            self.eq(nodes[0].get('received:from:fqdn'), 'smtp.vertex.link')
            self.eq(nodes[0].get('flow'), flow)

            self.len(1, await core.nodes('inet:email:message:to=woot@woot.com'))
            self.len(1, await core.nodes('inet:email:message:date=2015'))
            self.len(1, await core.nodes('inet:email:message:body="there are mad sploitz here!"'))
            self.len(1, await core.nodes('inet:email:message:subject="hi there"'))
            self.len(1, await core.nodes('inet:email:message:replyto=root@root.com'))

            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:header +:name=to +:value="Visi Stark <visi@vertex.link>"'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:message:link +:text=Vertex -> inet:url'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:message:attachment +:name=sploit.exe -> file:bytes'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> file:bytes'))
            self.len(1, await core.nodes('inet:email=foo@bar.com -> inet:email:message'))
            self.len(1, await core.nodes('inet:email=baz@faz.org -> inet:email:message'))
            self.len(1, await core.nodes('inet:email:message -> inet:email:message:link +:url=https://www.vertex.link +:text=Vertex'))
            self.len(1, await core.nodes('inet:email:message -> inet:email:message:attachment +:name=sploit.exe +:file'))

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

            self.eq(True, nodes[0].get('anon'))
            self.eq('vpn.', nodes[0].get('type'))
            self.eq('tcp://5.5.5.5', nodes[0].get('egress'))
            self.eq('tcp://1.2.3.4:443', nodes[0].get('ingress'))

            self.len(1, await core.nodes('inet:tunnel -> entity:contact +:email=visi@vertex.link'))

    async def test_model_inet_proto(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:proto=https :port=443 ]')
            self.len(1, nodes)
            self.eq(('inet:proto', 'https'), nodes[0].ndef)
            self.eq(443, nodes[0].get('port'))

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
            self.eq(nodes[0].get('client'), 'tcp://1.2.3.4')

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
            self.eq(nodes[0].get('server:jarmhash'), '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')

            self.eq(props['ja3'], nodes[0].get('client:ja3'))
            self.eq(props['ja3s'], nodes[0].get('server:ja3s'))

            self.eq(props['client'], nodes[0].get('client'))
            self.eq(props['server'], nodes[0].get('server'))

    async def test_model_inet_ja3(self):

        async with self.getTestCore() as core:

            ja3 = '76e7b0cb0994d60a4b3f360a088fac39'
            nodes = await core.nodes('[ inet:tls:ja3:sample=(tcp://1.2.3.4, $md5) ]', opts={'vars': {'md5': ja3}})
            self.len(1, nodes)
            self.eq(nodes[0].get('client'), 'tcp://1.2.3.4')
            self.eq(nodes[0].get('ja3'), ja3)

            ja3 = '4769ad08107979c719d86270e706fed5'
            nodes = await core.nodes('[ inet:tls:ja3s:sample=(tcp://2.2.2.2, $md5) ]', opts={'vars': {'md5': ja3}})
            self.len(1, nodes)
            self.eq(nodes[0].get('server'), 'tcp://2.2.2.2')
            self.eq(nodes[0].get('ja3s'), ja3)

    async def test_model_inet_tls_certs(self):

        async with self.getTestCore() as core:

            server = 'e4f6db65dbaa7a4598f7379f75dcd5f5'
            client = 'df8d1f7e04f7c4a322e04b0b252e2851'
            nodes = await core.nodes('[inet:tls:servercert=(tcp://1.2.3.4:1234, $server)]', opts={'vars': {'server': server}})
            self.len(1, nodes)
            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:1234')
            self.eq(nodes[0].get('cert'), server)

            nodes = await core.nodes('[inet:tls:clientcert=(tcp://5.6.7.8:5678, $client)]', opts={'vars': {'client': client}})
            self.len(1, nodes)
            self.eq(nodes[0].get('client'), 'tcp://5.6.7.8:5678')
            self.eq(nodes[0].get('cert'), client)

    async def test_model_inet_service(self):

        async with self.getTestCore() as core:

            provname = 'Slack Corp'
            opts = {'vars': {'provname': provname}}
            nodes = await core.nodes(f'gen.ou.org $provname', opts=opts)
            self.len(1, nodes)
            provider = nodes[0]

            q = '''
            [ inet:service:platform=(slack,)
                :url="https://slack.com"
                :urls=(https://slacker.com,)
                :name=Slack
                :names=("slack chat",)
                :desc=' Slack is a team communication platform.\n\n Be less busy.'
                :provider={ ou:org:name=$provname }
                :provider:name=$provname
            ]
            '''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:platform', s_common.guid(('slack',))))
            self.eq(nodes[0].get('url'), 'https://slack.com')
            self.eq(nodes[0].get('urls'), ('https://slacker.com',))
            self.eq(nodes[0].get('name'), 'slack')
            self.eq(nodes[0].get('names'), ('slack chat',))
            self.eq(nodes[0].get('desc'), ' Slack is a team communication platform.\n\n Be less busy.')
            self.eq(nodes[0].get('provider'), provider.ndef[1])
            self.eq(nodes[0].get('provider:name'), provname.lower())
            platform = nodes[0]

            nodes = await core.nodes('[ inet:service:platform=({"name": "slack chat"}) ]')
            self.eq(nodes[0].ndef, platform.ndef)

            nodes = await core.nodes('[ inet:service:platform=({"url": "https://slacker.com"}) ]')
            self.eq(nodes[0].ndef, platform.ndef)

            q = '''
            [ inet:service:instance=(vertex, slack)
                :id='T2XK1223Y'
                :platform={ inet:service:platform=(slack,) }
                :url="https://v.vtx.lk/slack"
                :name="Synapse users slack"
                :tenant={[ inet:service:tenant=({"id": "VS-31337"}) ]}
                :app={[ inet:service:app=({"id": "app00"}) ]}
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].get('tenant'))
            self.nn(nodes[0].get('app'))
            self.eq(nodes[0].ndef, ('inet:service:instance', s_common.guid(('vertex', 'slack'))))
            self.eq(nodes[0].get('id'), 'T2XK1223Y')
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('url'), 'https://v.vtx.lk/slack')
            self.eq(nodes[0].get('name'), 'synapse users slack')
            platinst = nodes[0]
            app00 = nodes[0].get('app')

            self.len(1, await core.nodes('inet:service:instance:id=T2XK1223Y -> inet:service:app [ :provider=* :provider:name=vertex ] :provider -> ou:org'))

            q = '''
            [
                (inet:service:account=(blackout, account, vertex, slack)
                    :id=U7RN51U1J
                    :user=blackout
                    :url=https://vertex.link/users/blackout
                    :email=blackout@vertex.link
                    :banner={[ file:bytes=({"name": "greencat.gif"}) ]}
                    :tenant={[ inet:service:tenant=({"id": "VS-31337"}) ]}
                    :app={[ inet:service:app=({"id": "a001"}) ]}
                )

                (inet:service:account=(visi, account, vertex, slack)
                    :id=U2XK7PUVB
                    :user=visi
                    :email=visi@vertex.link
                )
            ]
            '''
            accounts = await core.nodes(q)
            self.len(2, accounts)

            self.nn(accounts[0].get('banner'))
            self.nn(accounts[0].get('tenant'))
            self.nn(accounts[0].get('app'))

            self.eq(accounts[0].ndef, ('inet:service:account', s_common.guid(('blackout', 'account', 'vertex', 'slack'))))
            self.eq(accounts[0].get('id'), 'U7RN51U1J')
            self.eq(accounts[0].get('user'), 'blackout')
            self.eq(accounts[0].get('url'), 'https://vertex.link/users/blackout')
            self.eq(accounts[0].get('email'), 'blackout@vertex.link')

            self.eq(accounts[1].ndef, ('inet:service:account', s_common.guid(('visi', 'account', 'vertex', 'slack'))))
            self.eq(accounts[1].get('id'), 'U2XK7PUVB')
            self.eq(accounts[1].get('user'), 'visi')
            self.eq(accounts[1].get('email'), 'visi@vertex.link')
            blckacct, visiacct = accounts

            q = '''
            [ inet:service:group=(developers, group, vertex, slack)
                :id=X1234
                :name="developers, developers, developers"
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            self.eq(nodes[0].get('id'), 'X1234')
            self.eq(nodes[0].get('name'), 'developers, developers, developers')
            devsgrp = nodes[0]

            q = '''
            [
                (inet:service:group:member=(blackout, developers, group, vertex, slack)
                    :account=$blckiden
                    :group=$devsiden
                    :period=(20230601, ?)
                    :creator=$visiiden
                    :remover=$visiiden
                )

                (inet:service:group:member=(visi, developers, group, vertex, slack)
                    :account=$visiiden
                    :group=$devsiden
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

            self.eq(nodes[0].get('account'), blckacct.ndef[1])
            self.eq(nodes[0].get('group'), devsgrp.ndef[1])
            self.eq(nodes[0].get('period'), (1685577600000000, 9223372036854775807))
            self.eq(nodes[0].get('creator'), visiacct.ndef[1])
            self.eq(nodes[0].get('remover'), visiacct.ndef[1])

            self.eq(nodes[1].get('account'), visiacct.ndef[1])
            self.eq(nodes[1].get('group'), devsgrp.ndef[1])
            self.eq(nodes[1].get('period'), (1420070400000000, 9223372036854775807))
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
            self.eq(nodes[0].get('creator'), blckacct.ndef[1])
            self.eq(nodes[0].get('period'), (1715850000000000, 1715856900000000))
            blcksess = nodes[0]
            self.len(1, await core.nodes('inet:service:session -> inet:http:session'))

            q = '''
            [ inet:service:login=*
                :method=password
                :session=$blcksess
                :server=tcp://10.10.10.4:443
                :client=tcp://192.168.0.10:12345
                :creds={[auth:passwd=cool]}
            ]
            '''
            opts = {'vars': {'blcksess': blcksess.ndef[1]}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('method'), 'password.')
            self.eq(nodes[0].get('creds'), (('auth:passwd', 'cool'),))

            server = await core.nodes('inet:server=tcp://10.10.10.4:443')
            self.len(1, server)
            server = server[0]

            client = await core.nodes('inet:client=tcp://192.168.0.10:12345')
            self.len(1, client)
            client = client[0]

            self.eq(nodes[0].get('server'), server.ndef[1])
            self.eq(nodes[0].get('client'), client.ndef[1])

            q = '''
            [ inet:service:message:link=(blackout, developers, 1715856900000000, https://www.youtube.com/watch?v=dQw4w9WgXcQ, vertex, slack)
                :title="Deadpool & Wolverine | Official Teaser | In Theaters July 26"
                :url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].get('title'), 'Deadpool & Wolverine | Official Teaser | In Theaters July 26')
            self.eq(nodes[0].get('url'), 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')
            msglink = nodes[0]

            q = '''
            [ inet:service:channel=(general, channel, vertex, slack)
                :id=C1234
                :name=general
                :period=(20150101, ?)
                :creator=$visiiden
                :platform=$platiden
                :instance=$instiden
                :topic=' My Topic   '
                :app={ inet:service:app:id=app00 }
            ]
            '''
            opts = {'vars': {
                'visiiden': visiacct.ndef[1],
                'platiden': platform.ndef[1],
                'instiden': platinst.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:channel', s_common.guid(('general', 'channel', 'vertex', 'slack'))))
            self.eq(nodes[0].get('app'), app00)
            self.eq(nodes[0].get('name'), 'general')
            self.eq(nodes[0].get('topic'), 'my topic')
            self.eq(nodes[0].get('period'), (1420070400000000, 9223372036854775807))
            self.eq(nodes[0].get('creator'), visiacct.ndef[1])
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('instance'), platinst.ndef[1])
            gnrlchan = nodes[0]

            q = '''
            [
                (inet:service:channel:member=(visi, general, channel, vertex, slack)
                    :account=$visiiden
                    :period=(20150101, ?)
                )

                (inet:service:channel:member=(blackout, general, channel, vertex, slack)
                    :account=$blckiden
                    :period=(20230601, ?)
                )

                :platform=$platiden
                :instance=$instiden
                :channel=$chnliden
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'visiiden': visiacct.ndef[1],
                'chnliden': gnrlchan.ndef[1],
                'platiden': platform.ndef[1],
                'instiden': platinst.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:service:channel:member', s_common.guid(('visi', 'general', 'channel', 'vertex', 'slack'))))
            self.eq(nodes[0].get('account'), visiacct.ndef[1])
            self.eq(nodes[0].get('period'), (1420070400000000, 9223372036854775807))
            self.eq(nodes[0].get('channel'), gnrlchan.ndef[1])

            self.eq(nodes[1].ndef, ('inet:service:channel:member', s_common.guid(('blackout', 'general', 'channel', 'vertex', 'slack'))))
            self.eq(nodes[1].get('account'), blckacct.ndef[1])
            self.eq(nodes[1].get('period'), (1685577600000000, 9223372036854775807))
            self.eq(nodes[1].get('channel'), gnrlchan.ndef[1])

            for node in nodes:
                self.eq(node.get('platform'), platform.ndef[1])
                self.eq(node.get('instance'), platinst.ndef[1])
                self.eq(node.get('channel'), gnrlchan.ndef[1])

            nodes = await core.nodes('''
            [ inet:service:message:attachment=(pbjtime.gif, blackout, developers, 1715856900000000, vertex, slack)
                :file={[ file:bytes=({"sha256": "028241d9116a02059e99cb239c66d966e1b550926575ad7dcf0a8f076a352bcd"}) ]}
                :name=pbjtime.gif
                :text="peanut butter jelly time"
            ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'pbjtime.gif')
            self.eq(nodes[0].get('text'), 'peanut butter jelly time')
            self.eq(nodes[0].get('file'), 'ff94f25eddbf0d452ddee5303c8b818e')
            attachment = nodes[0]

            q = '''
            [
                (inet:service:message=(blackout, developers, 1715856900000000, vertex, slack)
                    :type=chat.group
                    :group=$devsiden
                    :public=$lib.false
                    :repost=*
                    :mentions=(
                        (inet:service:group, $devsiden),
                        (inet:service:account, $blckiden),
                        (inet:service:account, $blckiden),
                    )
                )

                (inet:service:message=(blackout, visi, 1715856900000000, vertex, slack)
                    :type=chat.direct
                    :to=$visiiden
                    :public=$lib.false
                    :mentions?=((inet:service:message:attachment, $atchiden),)
                )

                (inet:service:message=(blackout, general, 1715856900000000, vertex, slack)
                    :type=chat.channel
                    :channel=$gnrliden
                    :public=$lib.true
                )

                :account=$blckiden
                :text="omg, can't wait for the new deadpool: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                :links+=$linkiden
                :attachments+=$atchiden

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
                'atchiden': attachment.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(3, nodes)
            for node in nodes:

                self.eq(node.get('account'), blckacct.ndef[1])
                self.eq(node.get('text'), "omg, can't wait for the new deadpool: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                self.eq(node.get('links'), [msglink.ndef[1]])

                self.nn(node.get('client:software'))
                self.eq(node.get('client:software:name'), 'woot')

                self.nn(node.get('place'))
                self.eq(node.get('place:name'), 'nyc')

            self.nn(nodes[0].get('repost'))
            self.eq(nodes[0].get('group'), devsgrp.ndef[1])
            self.false(nodes[0].get('public'))
            self.eq(nodes[0].get('type'), 'chat.group.')
            self.eq(
                nodes[0].get('mentions'),
                (('inet:service:account', blckacct.ndef[1]), ('inet:service:group', devsgrp.ndef[1]))
            )

            self.eq(nodes[1].get('to'), visiacct.ndef[1])
            self.false(nodes[1].get('public'))
            self.eq(nodes[1].get('type'), 'chat.direct.')
            self.none(nodes[1].get('mentions'))

            self.eq(nodes[2].get('channel'), gnrlchan.ndef[1])
            self.true(nodes[2].get('public'))
            self.eq(nodes[2].get('type'), 'chat.channel.')

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
                :instance=$instiden
                :name="Slack Web APIs"
                :platform=$platiden
                :type=slack.web.api
                :url="https://slack.com/api"
            ]
            '''
            opts = {'vars': {
                'platiden': platform.ndef[1],
                'instiden': platinst.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('desc'), 'The Web API supplies a collection of HTTP methods that underpin the majority of Slack app functionality.')
            self.eq(nodes[0].get('instance'), platinst.ndef[1])
            self.eq(nodes[0].get('name'), 'slack web apis')
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('type'), 'slack.web.api.')
            self.eq(nodes[0].get('url'), 'https://slack.com/api')
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
            self.eq('woot.exe', nodes[0].get('file:name'))
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:bucket:item -> file:bytes'))
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:bucket:item -> inet:service:account'))
            self.len(1, await core.nodes('inet:service:bucket -> inet:service:account'))
            self.len(1, await core.nodes('inet:service:bucket:name=foobar'))

            q = '''
            [ inet:service:access=(api, blackout, 1715856900000000, vertex, slack)
                :action=foo.bar
                :account=$blckiden
                :instance=$instiden
                :platform=$platiden
                :resource=$rsrciden
                :success=$lib.true
                :time=(1715856900000000)
                :app={[ inet:service:app=({"name": "slack web"}) ]}
                :client:app={[ inet:service:app=({"name": "slack web"}) :desc="The slack web application"]}
            ]
            '''
            opts = {'vars': {
                'blckiden': blckacct.ndef[1],
                'instiden': platinst.ndef[1],
                'visiiden': visiacct.ndef[1],
                'platiden': platform.ndef[1],
                'rsrciden': resource.ndef[1],
            }}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('action'), 'foo.bar.')
            self.eq(nodes[0].get('account'), blckacct.ndef[1])
            self.eq(nodes[0].get('instance'), platinst.ndef[1])
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('resource'), resource.ndef[1])
            self.true(nodes[0].get('success'))
            self.eq(nodes[0].get('time'), 1715856900000000)
            self.eq(nodes[0].get('app'), nodes[0].get('client:app'))

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
            self.eq('follows.', nodes[0].get('type'))
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
            self.eq(':gothparrot:', nodes[0].get('text'))
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
            self.eq('vertex.synapse.enterprise.', nodes[0].get('level'))
            self.eq('econ:pay:card', nodes[0].get('pay:instrument')[0])
            self.eq('inet:service:tenant', nodes[0].get('subscriber')[0])
            self.len(1, await core.nodes('inet:service:subscription -> inet:service:subscription:level:taxonomy'))
            self.len(1, await core.nodes('inet:service:subscription :pay:instrument -> econ:pay:card'))
            self.len(1, await core.nodes('inet:service:subscription :subscriber -> inet:service:tenant'))

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
            self.eq(nodes[0].get('ja4'), 't13d190900_9dc949149365_97f8aa674fd9')
            self.eq(nodes[0].get('client'), 'tcp://1.2.3.4')
            self.len(1, await core.nodes('inet:tls:ja4:sample -> inet:client'))
            self.len(1, await core.nodes('inet:tls:ja4:sample -> inet:tls:ja4'))

            nodes = await core.nodes('[ inet:tls:ja4s:sample=(1.2.3.4:443, t130200_1301_a56c5b993250) ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('ja4s'), 't130200_1301_a56c5b993250')
            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:443')
            self.len(1, await core.nodes('inet:tls:ja4s:sample -> inet:server'))
            self.len(1, await core.nodes('inet:tls:ja4s:sample -> inet:tls:ja4s'))

            nodes = await core.nodes('''[
                inet:tls:handshake=*
                    :client:ja4=t13d190900_9dc949149365_97f8aa674fd9
                    :server:ja4s=t130200_1301_a56c5b993250
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('client:ja4'), 't13d190900_9dc949149365_97f8aa674fd9')
            self.eq(nodes[0].get('server:ja4s'), 't130200_1301_a56c5b993250')
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
