import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class InetModelTest(s_t_utils.SynTest):

    async def test_model_inet_basics(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[ inet:web:hashtag="#🫠" ]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#🫠🫠" ]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#·bar"]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#foo·"]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#foo〜"]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#hehe" ]'))
            self.len(1, await core.nodes('[ inet:web:hashtag="#foo·bar"]'))  # note the interpunct
            self.len(1, await core.nodes('[ inet:web:hashtag="#foo〜bar"]'))  # note the wave dash
            self.len(1, await core.nodes('[ inet:web:hashtag="#fo·o·······b·ar"]'))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:web:hashtag="foo" ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:web:hashtag="#foo#bar" ]')

            # All unicode whitespace from:
            # https://www.compart.com/en/unicode/category/Zl
            # https://www.compart.com/en/unicode/category/Zp
            # https://www.compart.com/en/unicode/category/Zs
            whitespace = [
                '\u0020', '\u00a0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
                '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a', '\u202f', '\u205f',
                '\u3000', '\u2028', '\u2029',
            ]
            for char in whitespace:
                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ inet:web:hashtag="#foo{char}bar" ]')

                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ inet:web:hashtag="#{char}bar" ]')

                # These are allowed because strip=True
                await core.callStorm(f'[ inet:web:hashtag="#foo{char}" ]')
                await core.callStorm(f'[ inet:web:hashtag=" #foo{char}" ]')

            nodes = await core.nodes('''
                [ inet:web:instance=(foo,)
                    :url=https://app.slack.com/client/T2XK1223Y
                    :id=T2XK1223Y
                    :name="vertex synapse"
                    :created=20220202
                    :creator=synapsechat.slack.com/visi
                    :owner={[ ou:org=* :name=vertex ]}
                    :owner:fqdn=vertex.link
                    :owner:name=vertex
                    :operator={[ ou:org=* :name=slack ]}
                    :operator:fqdn=slack.com
                    :operator:name=slack
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('url'), 'https://app.slack.com/client/T2XK1223Y')
            self.eq(node.get('id'), 'T2XK1223Y')
            self.eq(node.get('name'), 'vertex synapse')
            self.eq(node.get('created'), 1643760000000)
            self.eq(node.get('creator'), ('synapsechat.slack.com', 'visi'))
            self.nn(node.get('owner'))
            self.eq(node.get('owner:fqdn'), 'vertex.link')
            self.eq(node.get('owner:name'), 'vertex')
            self.nn(node.get('operator'))
            self.eq(node.get('operator:fqdn'), 'slack.com')
            self.eq(node.get('operator:name'), 'slack')

            nodes = await core.nodes('''
                [ inet:web:channel=(bar,)
                    :url=https://app.slack.com/client/T2XK1223Y/C2XHHNDS7
                    :id=C2XHHNDS7
                    :name=general
                    :instance={ inet:web:instance:url=https://app.slack.com/client/T2XK1223Y }
                    :created=20220202
                    :creator=synapsechat.slack.com/visi
                    :topic="Synapse Discussion - Feel free to invite others!"
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('url'), 'https://app.slack.com/client/T2XK1223Y/C2XHHNDS7')
            self.eq(node.get('id'), 'C2XHHNDS7')
            self.eq(node.get('name'), 'general')
            self.eq(node.get('topic'), 'Synapse Discussion - Feel free to invite others!')
            self.eq(node.get('created'), 1643760000000)
            self.eq(node.get('creator'), ('synapsechat.slack.com', 'visi'))
            self.nn(node.get('instance'))

            opts = {'vars': {'mesg': (('synapsechat.slack.com', 'visi'), ('synapsechat.slack.com', 'whippit'), 1643760000000)}}
            self.len(1, await core.nodes('[ inet:web:mesg=$mesg :instance=(foo,) ] -> inet:web:instance +:name="vertex synapse"', opts=opts))
            self.len(1, await core.nodes('[ inet:web:post=* :channel=(bar,) ] -> inet:web:channel +:name=general -> inet:web:instance'))

    async def test_inet_jarm(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:ssl:jarmsample=(1.2.3.4:443, 07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1) ]')
            self.len(1, nodes)
            self.eq('tcp://1.2.3.4:443', nodes[0].get('server'))
            self.eq('07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1', nodes[0].get('jarmhash'))
            self.eq(('tcp://1.2.3.4:443', '07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1'), nodes[0].ndef[1])

            nodes = await core.nodes('inet:ssl:jarmhash=07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1')
            self.len(1, nodes)
            self.eq('07d14d16d21d21d07c42d41d00041d24a458a375eef0c576d23a7bab9a9fb1', nodes[0].ndef[1])
            self.eq('07d14d16d21d21d07c42d41d00041d', nodes[0].get('ciphers'))
            self.eq('24a458a375eef0c576d23a7bab9a9fb1', nodes[0].get('extensions'))

    async def test_ipv4_lift_range(self):

        async with self.getTestCore() as core:

            for i in range(5):
                valu = f'1.2.3.{i}'
                nodes = await core.nodes('[inet:ipv4=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)

            self.len(3, await core.nodes('inet:ipv4=1.2.3.1-1.2.3.3'))
            self.len(3, await core.nodes('[inet:ipv4=1.2.3.1-1.2.3.3]'))
            self.len(3, await core.nodes('inet:ipv4 +inet:ipv4=1.2.3.1-1.2.3.3'))
            self.len(3, await core.nodes('inet:ipv4*range=(1.2.3.1, 1.2.3.3)'))

    async def test_ipv4_filt_cidr(self):

        async with self.getTestCore() as core:

            self.len(5, await core.nodes('[ inet:ipv4=1.2.3.0/30 inet:ipv4=5.5.5.5 ]'))
            self.len(4, await core.nodes('inet:ipv4 +inet:ipv4=1.2.3.0/30'))
            self.len(1, await core.nodes('inet:ipv4 -inet:ipv4=1.2.3.0/30'))

            self.len(256, await core.nodes('[ inet:ipv4=192.168.1.0/24]'))
            self.len(256, await core.nodes('[ inet:ipv4=192.168.2.0/24]'))
            self.len(256, await core.nodes('inet:ipv4=192.168.1.0/24'))

            # Seed some nodes for bounds checking
            vals = list(range(1, 33))
            q = 'for $v in $vals { [inet:ipv4=`10.2.1.{$v}` ] }'
            self.len(len(vals), await core.nodes(q, opts={'vars': {'vals': vals}}))

            nodes = await core.nodes('inet:ipv4=10.2.1.4/32')
            self.len(1, nodes)
            self.len(1, await core.nodes('inet:ipv4 +inet:ipv4=10.2.1.4/32'))

            nodes = await core.nodes('inet:ipv4=10.2.1.4/31')
            self.len(2, nodes)
            self.len(2, await core.nodes('inet:ipv4 +inet:ipv4=10.2.1.4/31'))

            # 10.2.1.1/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv4=10.2.1.1/30')
            self.len(3, nodes)

            # 10.2.1.2/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv4=10.2.1.2/30')
            self.len(3, nodes)

            # 10.2.1.1/29 is 10.2.1.0 -> 10.2.1.7 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv4=10.2.1.1/29')
            self.len(7, nodes)

            # 10.2.1.8/29 is 10.2.1.8 -> 10.2.1.15
            nodes = await core.nodes('inet:ipv4=10.2.1.8/29')
            self.len(8, nodes)

            # 10.2.1.1/28 is 10.2.1.0 -> 10.2.1.15 but we don't have 10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv4=10.2.1.1/28')
            self.len(15, nodes)

    async def test_addr(self):
        formname = 'inet:addr'
        async with self.getTestCore() as core:
            t = core.model.type(formname)

            # Proto defaults to tcp
            self.eq(t.norm('1.2.3.4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.eq(t.norm('1.2.3.4:80'),
                          ('tcp://1.2.3.4:80', {'subs': {'port': 80, 'ipv4': 16909060, 'proto': 'tcp'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'https://192.168.1.1:80')  # bad proto

            # IPv4
            self.eq(t.norm('tcp://1.2.3.4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.eq(t.norm('udp://1.2.3.4:80'),
                    ('udp://1.2.3.4:80', {'subs': {'port': 80, 'ipv4': 16909060, 'proto': 'udp'}}))
            self.eq(t.norm('tcp://1[.]2.3[.]4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://1.2.3.4:-1')
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://1.2.3.4:66000')

            # IPv6
            self.eq(t.norm('icmp://::1'), ('icmp://::1', {'subs': {'ipv6': '::1', 'proto': 'icmp'}}))
            self.eq(t.norm('tcp://[::1]:2'), ('tcp://[::1]:2', {'subs': {'ipv6': '::1', 'port': 2, 'proto': 'tcp'}}))
            self.eq(t.norm('tcp://[::1]'), ('tcp://[::1]', {'subs': {'ipv6': '::1', 'proto': 'tcp'}}))
            self.eq(t.norm('tcp://[::fFfF:0102:0304]:2'),
                    ('tcp://[::ffff:1.2.3.4]:2', {'subs': {'ipv6': '::ffff:1.2.3.4',
                                                           'ipv4': 0x01020304,
                                                           'port': 2,
                                                           'proto': 'tcp',
                                                           }}))
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://[::1')  # bad ipv6 w/ port

            # Host
            hstr = 'ffa3e574aa219e553e1b2fc1ccd0180f'
            self.eq(t.norm('host://vertex.link'), (f'host://{hstr}', {'subs': {'host': hstr, 'proto': 'host'}}))
            self.eq(t.norm('host://vertex.link:1337'),
                    (f'host://{hstr}:1337', {'subs': {'host': hstr, 'port': 1337, 'proto': 'host'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'vertex.link')  # must use host proto

    async def test_asn_collection(self):
        async with self.getTestCore() as core:
            owner = s_common.guid()
            nodes = await core.nodes('[(inet:asn=123 :name=COOL :owner=$owner)]', opts={'vars': {'owner': owner}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asn', 123))
            self.eq(node.get('name'), 'cool')
            self.eq(node.get('owner'), owner)

            nodes = await core.nodes('[(inet:asn=456)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asn', 456))
            self.none(node.get('name'))
            self.none(node.get('owner'))

            nodes = await core.nodes('[inet:asnet4=(54959, (1.2.3.4, 5.6.7.8))]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet4', (54959, (0x01020304, 0x05060708))))
            self.eq(node.get('asn'), 54959)
            self.eq(node.get('net4'), (0x01020304, 0x05060708))
            self.eq(node.get('net4:min'), 0x01020304)
            self.eq(node.get('net4:max'), 0x05060708)
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))
            self.len(1, await core.nodes('inet:ipv4=5.6.7.8'))

            nodes = await core.nodes('[ inet:asnet6=(99, (ff::00, ff::0100)) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:asnet6', (99, ('ff::', 'ff::100'))))
            self.eq(node.get('asn'), 99)
            self.eq(node.get('net6'), ('ff::', 'ff::100'))
            self.eq(node.get('net6:min'), 'ff::')
            self.eq(node.get('net6:max'), 'ff::100')
            self.len(1, await core.nodes('inet:ipv6="ff::"'))
            self.len(1, await core.nodes('inet:ipv6="ff::100"'))

    async def test_cidr4(self):
        formname = 'inet:cidr4'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            valu = '0/24'
            expected = ('0.0.0.0/24', {'subs': {
                'broadcast': 255,
                'network': 0,
                'mask': 24,
            }})
            self.eq(t.norm(valu), expected)

            valu = '192.168.1.101/24'
            expected = ('192.168.1.0/24', {'subs': {
                'broadcast': 3232236031,  # 192.168.1.255
                'network': 3232235776,    # 192.168.1.0
                'mask': 24,
            }})
            self.eq(t.norm(valu), expected)

            valu = '123.123.0.5/30'
            expected = ('123.123.0.4/30', {'subs': {
                'broadcast': 2071658503,  # 123.123.0.7
                'network': 2071658500,    # 123.123.0.4
                'mask': 30,
            }})
            self.eq(t.norm(valu), expected)

            self.raises(s_exc.BadTypeValu, t.norm, '10.0.0.1/-1')
            self.raises(s_exc.BadTypeValu, t.norm, '10.0.0.1/33')
            self.raises(s_exc.BadTypeValu, t.norm, '10.0.0.1/foo')
            self.raises(s_exc.BadTypeValu, t.norm, '10.0.0.1')

            # Form Tests ======================================================
            valu = '192[.]168.1.123/24'
            expected_ndef = (formname, '192.168.1.0/24')  # ndef is network/mask, not ip/mask

            nodes = await core.nodes('[inet:cidr4=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, expected_ndef)
            self.eq(node.get('network'), 3232235776)  # 192.168.1.0
            self.eq(node.get('broadcast'), 3232236031)  # 192.168.1.255
            self.eq(node.get('mask'), 24)

    async def test_cidr6(self):
        formname = 'inet:cidr6'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            valu = '::/0'
            expected = ('::/0', {'subs': {
                'broadcast': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
                'network': '::',
                'mask': 0,
            }})
            self.eq(t.norm(valu), expected)

            valu = '2001:db8::/59'
            expected = ('2001:db8::/59', {'subs': {
                'broadcast': '2001:db8:0:1f:ffff:ffff:ffff:ffff',
                'network': '2001:db8::',
                'mask': 59,
            }})
            self.eq(t.norm(valu), expected)

            self.raises(s_exc.BadTypeValu, t.norm, '10.0.0.1/-1')

    async def test_client(self):
        data = (
            ('tcp://127.0.0.1:12345', 'tcp://127.0.0.1:12345', {
                'ipv4': 2130706433,
                'port': 12345,
                'proto': 'tcp',
            }),
            ('tcp://127.0.0.1', 'tcp://127.0.0.1', {
                'ipv4': 2130706433,
                'proto': 'tcp',
            }),
            ('tcp://[::1]:12345', 'tcp://[::1]:12345', {
                'ipv6': '::1',
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
            props = {
                'time': 0,
                'file': 64 * 'b',
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
            self.eq(node.get('file'), 'sha256:' + 64 * 'b')
            self.eq(node.get('fqdn'), 'vertex.link')
            self.eq(node.get('client'), 'tcp://127.0.0.1:45654')
            self.eq(node.get('client:ipv4'), 2130706433)
            self.eq(node.get('client:port'), 45654)
            self.eq(node.get('client:proto'), 'tcp')
            self.eq(node.get('server'), 'tcp://1.2.3.4:80')
            self.eq(node.get('server:ipv4'), 0x01020304)
            self.eq(node.get('server:port'), 80)
            self.eq(node.get('server:proto'), 'tcp')

    async def test_email(self):
        formname = 'inet:email'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {'fqdn': 'vertex.link', 'user': 'unittest'}})
            self.eq(t.norm(email), expected)

            valu = t.norm('bob\udcfesmith@woot.com')[0]

            with self.raises(s_exc.BadTypeValu) as cm:
                t.norm('hehe')
            self.isin('Email address expected in <user>@<fqdn> format', cm.exception.get('mesg'))

            with self.raises(s_exc.BadTypeValu) as cm:
                t.norm('hehe@1.2.3.4')
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
            valu = s_common.guid()
            srccert = s_common.guid()
            dstcert = s_common.guid()
            shost = s_common.guid()
            sproc = s_common.guid()
            sexe = 'sha256:' + 'b' * 64
            dhost = s_common.guid()
            dproc = s_common.guid()
            dexe = 'sha256:' + 'c' * 64
            pfrom = s_common.guid()
            sfile = 'sha256:' + 'd' * 64
            props = {
                'from': pfrom,
                'shost': shost,
                'sproc': sproc,
                'sexe': sexe,
                'dhost': dhost,
                'dproc': dproc,
                'dexe': dexe,
                'sfile': sfile,
                'skey': srccert,
                'dkey': dstcert,
                'scrt': srccert,
                'dcrt': dstcert,
            }
            q = '''[(inet:flow=$valu
                :time=(0)
                :duration=(1)
                :from=$p.from
                :src="tcp://127.0.0.1:45654"
                :src:host=$p.shost
                :src:proc=$p.sproc
                :src:exe=$p.sexe
                :src:txcount=30
                :src:txbytes=1
                :src:handshake="Hello There"
                :dst="tcp://1.2.3.4:80"
                :dst:host=$p.dhost
                :dst:proc=$p.dproc
                :dst:exe=$p.dexe
                :dst:txcount=33
                :dst:txbytes=2
                :tot:txcount=63
                :tot:txbytes=3
                :dst:handshake="OHai!"
                :src:softnames=(HeHe, haha)
                :dst:softnames=(FooBar, bazfaz)
                :src:cpes=("cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*", "cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*")
                :dst:cpes=("cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*", "cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*")
                :ip:proto=6
                :ip:tcp:flags=(0x20)
                :sandbox:file=$p.sfile
                :src:ssh:key=$p.skey
                :dst:ssh:key=$p.dkey
                :src:ssl:cert=$p.scrt
                :dst:ssl:cert=$p.dcrt
                :src:rdp:hostname=SYNCODER
                :src:rdp:keyboard:layout=AZERTY
                :raw=((10), (20))
                :src:txfiles={[ file:attachment=* :name=foo.exe ]}
                :dst:txfiles={[ file:attachment=* :name=bar.exe ]}
                :capture:host=*
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:flow', valu))
            self.eq(node.get('time'), 0)
            self.eq(node.get('duration'), 1)
            self.eq(node.get('from'), pfrom)
            self.eq(node.get('src'), 'tcp://127.0.0.1:45654')
            self.eq(node.get('src:port'), 45654)
            self.eq(node.get('src:proto'), 'tcp')
            self.eq(node.get('src:host'), shost)
            self.eq(node.get('src:proc'), sproc)
            self.eq(node.get('src:exe'), sexe)
            self.eq(node.get('src:txcount'), 30)
            self.eq(node.get('src:txbytes'), 1)
            self.eq(node.get('src:handshake'), 'Hello There')
            self.eq(node.get('dst'), 'tcp://1.2.3.4:80')
            self.eq(node.get('dst:port'), 80)
            self.eq(node.get('dst:proto'), 'tcp')
            self.eq(node.get('dst:ipv4'), 0x01020304)
            self.eq(node.get('dst:host'), dhost)
            self.eq(node.get('dst:proc'), dproc)
            self.eq(node.get('dst:exe'), dexe)
            self.eq(node.get('dst:txcount'), 33)
            self.eq(node.get('dst:txbytes'), 2)
            self.eq(node.get('dst:handshake'), 'OHai!')
            self.eq(node.get('tot:txcount'), 63)
            self.eq(node.get('tot:txbytes'), 3)
            self.eq(node.get('src:softnames'), ('haha', 'hehe'))
            self.eq(node.get('dst:softnames'), ('bazfaz', 'foobar'))
            self.eq(node.get('src:cpes'), ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)
            self.eq(node.get('dst:cpes'), ('cpe:2.3:a:aaa:bbb:*:*:*:*:*:*:*:*', 'cpe:2.3:a:zzz:yyy:*:*:*:*:*:*:*:*'),)
            self.eq(node.get('ip:proto'), 6)
            self.eq(node.get('ip:tcp:flags'), 0x20)
            self.eq(node.get('sandbox:file'), sfile)
            self.eq(node.get('src:ssh:key'), srccert)
            self.eq(node.get('dst:ssh:key'), dstcert)
            self.eq(node.get('src:ssl:cert'), srccert)
            self.eq(node.get('dst:ssl:cert'), dstcert)
            self.eq(node.get('src:rdp:hostname'), 'syncoder')
            self.eq(node.get('src:rdp:keyboard:layout'), 'azerty')
            self.eq(node.get('raw'), (10, 20))
            self.nn(node.get('capture:host'))
            self.len(2, await core.nodes('inet:flow -> crypto:x509:cert'))
            self.len(1, await core.nodes('inet:flow :src:ssh:key -> crypto:key'))
            self.len(1, await core.nodes('inet:flow :dst:ssh:key -> crypto:key'))
            self.len(1, await core.nodes('inet:flow :src:txfiles -> file:attachment +:name=foo.exe'))
            self.len(1, await core.nodes('inet:flow :dst:txfiles -> file:attachment +:name=bar.exe'))
            self.len(1, await core.nodes('inet:flow :capture:host -> it:host'))

    async def test_fqdn(self):
        formname = 'inet:fqdn'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            fqdn = 'example.Vertex.link'
            expected = ('example.vertex.link', {'subs': {'host': 'example', 'domain': 'vertex.link'}})
            self.eq(t.norm(fqdn), expected)
            self.raises(s_exc.BadTypeValu, t.norm, '!@#$%')

            # defanging works
            self.eq(t.norm('example[.]vertex(.)link'), expected)

            # Demonstrate Valid IDNA
            fqdn = 'tèst.èxamplè.link'
            ex_fqdn = 'xn--tst-6la.xn--xampl-3raf.link'
            expected = (ex_fqdn, {'subs': {'domain': 'xn--xampl-3raf.link', 'host': 'xn--tst-6la'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)  # Calling repr on IDNA encoded domain should result in the unicode

            # Use IDNA2008 if possible
            fqdn = "faß.de"
            ex_fqdn = 'xn--fa-hia.de'
            expected = (ex_fqdn, {'subs': {'domain': 'de', 'host': 'xn--fa-hia'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Emojis are valid IDNA2003
            fqdn = '👁👄👁.fm'
            ex_fqdn = 'xn--mp8hai.fm'
            expected = (ex_fqdn, {'subs': {'domain': 'fm', 'host': 'xn--mp8hai'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)

            # Variant forms get normalized
            varfqdn = '👁️👄👁️.fm'
            self.eq(t.norm(varfqdn), expected)
            self.ne(varfqdn, fqdn)

            # Unicode full stops are okay but get normalized
            fqdn = 'foo(．)bar[。]baz｡lol'
            ex_fqdn = 'foo.bar.baz.lol'
            expected = (ex_fqdn, {'subs': {'domain': 'bar.baz.lol', 'host': 'foo'}})
            self.eq(t.norm(fqdn), expected)

            # Ellipsis shouldn't make it through
            self.raises(s_exc.BadTypeValu, t.norm, 'vertex…link')

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'link'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))  # UnicodeError raised and caught and fallback to norm

            fqdn = 'xn--cc.bartmp.l.google.com'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'bartmp.l.google.com'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com')

            # IP addresses are NOT valid FQDNs
            self.raises(s_exc.BadTypeValu, t.norm, '1.2.3.4')

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

            props = {
                'body': 64 * 'b',
                'flow': flow,
                'sess': sess,
                'client:host': client,
                'server:host': server,
                'sandbox:file': 64 * 'c'
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
            self.eq(node.get('time'), 1420070400000)
            self.eq(node.get('flow'), flow)
            self.eq(node.get('method'), 'gEt')
            self.eq(node.get('query'), 'hoho=1&qaz=bar')
            self.eq(node.get('path'), '/woot/hehe/')
            self.eq(node.get('body'), 'sha256:' + 64 * 'b')
            self.eq(node.get('response:code'), 200)
            self.eq(node.get('response:reason'), 'OK')
            self.eq(node.get('response:headers'), (('baz', 'faz'),))
            self.eq(node.get('response:body'), 'sha256:' + 64 * 'b')
            self.eq(node.get('session'), sess)
            self.eq(node.get('sandbox:file'), 'sha256:' + 64 * 'c')
            self.eq(node.get('client'), 'tcp://1.2.3.4')
            self.eq(node.get('client:ipv4'), 0x01020304)
            self.eq(node.get('client:host'), client)
            self.eq(node.get('server'), 'tcp://5.5.5.5:443')
            self.eq(node.get('server:host'), server)
            self.eq(node.get('server:ipv4'), 0x05050505)
            self.eq(node.get('server:port'), 443)

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
                :ipv4=1.2.3.4
                :ipv6="ff::00"
                :phone=12345678910
                :wifi:ssid="hehe haha"
                :wifi:bssid="00:ff:00:ff:00:ff"
                :mob:imei=123456789012347
                :mob:imsi=12345678901234
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:iface', valu))
            self.eq(node.get('host'), host)
            self.eq(node.get('network'), netw)
            self.eq(node.get('type'), 'cool')
            self.eq(node.get('mac'), 'ff:00:ff:00:ff:00')
            self.eq(node.get('ipv4'), 0x01020304)
            self.eq(node.get('ipv6'), 'ff::')
            self.eq(node.get('phone'), '12345678910')
            self.eq(node.get('wifi:ssid'), 'hehe haha')
            self.eq(node.get('wifi:bssid'), '00:ff:00:ff:00:ff')
            self.eq(node.get('mob:imei'), 123456789012347)
            self.eq(node.get('mob:imsi'), 12345678901234)

    async def test_ipv4(self):
        formname = 'inet:ipv4'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)
            ip_int = 16909060
            ip_str = '1.2.3.4'
            ip_str_enfanged = '1[.]2[.]3[.]4'
            ip_str_enfanged2 = '1(.)2(.)3(.)4'
            ip_str_unicode = '1\u200b.\u200b2\u200b.\u200b3\u200b.\u200b4'

            info = {'subs': {'type': 'unicast'}}
            self.eq(t.norm(ip_int), (ip_int, info))
            self.eq(t.norm(ip_str), (ip_int, info))
            self.eq(t.norm(ip_str_enfanged), (ip_int, info))
            self.eq(t.norm(ip_str_enfanged2), (ip_int, info))
            self.eq(t.norm(ip_str_unicode), (ip_int, info))
            self.eq(t.repr(ip_int), ip_str)

            # Link local test
            ip_str = '169.254.1.1'
            norm, info = t.norm(ip_str)
            self.eq(2851995905, norm)
            self.eq(info.get('subs').get('type'), 'linklocal')

            norm, info = t.norm('100.63.255.255')
            self.eq(info.get('subs').get('type'), 'unicast')

            norm, info = t.norm('100.64.0.0')
            self.eq(info.get('subs').get('type'), 'shared')

            norm, info = t.norm('100.127.255.255')
            self.eq(info.get('subs').get('type'), 'shared')

            norm, info = t.norm('100.128.0.0')
            self.eq(info.get('subs').get('type'), 'unicast')

            # Don't allow invalid values
            with self.raises(s_exc.BadTypeValu):
                t.norm(0x00000000 - 1)

            with self.raises(s_exc.BadTypeValu):
                t.norm(0xFFFFFFFF + 1)

            with self.raises(s_exc.BadTypeValu):
                t.norm('foo-bar.com')
            with self.raises(s_exc.BadTypeValu):
                t.norm('bar.com')

            # Form Tests ======================================================
            place = s_common.guid()
            props = {
                'asn': 3,
                'loc': 'uS',
                'dns:rev': 'vertex.link',
                'latlong': '-50.12345, 150.56789',
                'place': place,
            }
            q = '[(inet:ipv4=$valu :asn=$p.asn :loc=$p.loc :dns:rev=$p."dns:rev" :latlong=$p.latlong :place=$p.place)]'
            opts = {'vars': {'valu': '1.2.3.4', 'p': props}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:ipv4', 0x01020304))
            self.eq(node.get('asn'), 3)
            self.eq(node.get('loc'), 'us')
            self.eq(node.get('type'), 'unicast')
            self.eq(node.get('dns:rev'), 'vertex.link')
            self.eq(node.get('latlong'), (-50.12345, 150.56789))
            self.eq(node.get('place'), place)

            # > / < lifts and filters
            self.len(4, await core.nodes('[inet:ipv4=0 inet:ipv4=1 inet:ipv4=2 inet:ipv4=3]'))
            # Lifts
            self.len(0, await core.nodes('inet:ipv4<0'))
            self.len(1, await core.nodes('inet:ipv4<=0'))
            self.len(1, await core.nodes('inet:ipv4<1'))
            self.len(3, await core.nodes('inet:ipv4<=2'))
            self.len(2, await core.nodes('inet:ipv4>2'))
            self.len(3, await core.nodes('inet:ipv4>=2'))
            self.len(0, await core.nodes('inet:ipv4>=255.0.0.1'))
            with self.raises(s_exc.BadTypeValu):
                self.len(5, await core.nodes('inet:ipv4>=$foo', {'vars': {'foo': 0xFFFFFFFF + 1}}))
            # Filters
            self.len(0, await core.nodes('.created +inet:ipv4<0'))
            self.len(1, await core.nodes('.created +inet:ipv4<1'))
            self.len(3, await core.nodes('.created +inet:ipv4<=2'))
            self.len(2, await core.nodes('.created +inet:ipv4>2'))
            self.len(3, await core.nodes('.created +inet:ipv4>=2'))
            self.len(0, await core.nodes('.created +inet:ipv4>=255.0.0.1'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv4=foo]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv4=foo-bar.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv4=foo-bar-duck.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv4=3.87/nice/index.php]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv4=3.87/33]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo"] [inet:ipv4=$node.value()]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo-bar.com"] [inet:ipv4=$node.value()]')

            self.len(0, await core.nodes('[inet:ipv4?=foo]'))
            self.len(0, await core.nodes('[inet:ipv4?=foo-bar.com]'))

            self.len(0, await core.nodes('[test:str="foo"] [inet:ipv4?=$node.value()] -test:str'))
            self.len(0, await core.nodes('[test:str="foo-bar.com"] [inet:ipv4?=$node.value()] -test:str'))

            q = '''init { $l = () }
            [inet:ipv4=192.0.0.9 inet:ipv4=192.0.0.0 inet:ipv4=192.0.0.255] $l.append(:type)
            fini { return ( $l ) }'''
            resp = await core.callStorm(q)
            self.eq(resp, ['unicast', 'private', 'private'])

    async def test_ipv6(self):
        formname = 'inet:ipv6'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            info = {'subs': {'type': 'loopback', 'scope': 'link-local'}}
            self.eq(t.norm('::1'), ('::1', info))
            self.eq(t.norm('0:0:0:0:0:0:0:1'), ('::1', info))

            self.eq(t.norm('ff01::1'), ('ff01::1', {'subs': {'type': 'multicast', 'scope': 'interface-local'}}))

            info = {'subs': {'type': 'private', 'scope': 'global'}}
            self.eq(t.norm('2001:0db8:0000:0000:0000:ff00:0042:8329'), ('2001:db8::ff00:42:8329', info))
            self.eq(t.norm('2001:0db8:0000:0000:0000:ff00:0042\u200b:8329'), ('2001:db8::ff00:42:8329', info))
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')

            # Specific examples given in RFC5952
            self.eq(t.norm('2001:db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:0db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:db8::1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:db8::0:1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:0db8::1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:db8:0:0:1::1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:DB8:0:0:1::1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('2001:DB8:0:0:1:0000:0000:1')[0], '2001:db8::1:0:0:1')
            self.raises(s_exc.BadTypeValu, t.norm, '::1::')
            self.eq(t.norm('2001:0db8::0001')[0], '2001:db8::1')
            self.eq(t.norm('2001:db8:0:0:0:0:2:1')[0], '2001:db8::2:1')
            self.eq(t.norm('2001:db8:0:1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')
            self.eq(t.norm('2001:0:0:1:0:0:0:1')[0], '2001:0:0:1::1')
            self.eq(t.norm('2001:db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')
            self.eq(t.norm('::ffff:1.2.3.4')[0], '::ffff:1.2.3.4')
            self.eq(t.norm('2001:db8::0:1')[0], '2001:db8::1')
            self.eq(t.norm('2001:db8:0:0:0:0:2:1')[0], '2001:db8::2:1')
            self.eq(t.norm('2001:db8::')[0], '2001:db8::')

            self.eq(t.norm(0)[0], '::')
            self.eq(t.norm(1)[0], '::1')
            self.eq(t.norm(2**128 - 1)[0], 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

            # Link local test
            ip_str = 'fe80::1'
            norm, info = t.norm(ip_str)
            self.eq('fe80::1', norm)
            self.eq(info.get('subs').get('type'), 'linklocal')

            # Form Tests ======================================================
            place = s_common.guid()
            valu = '::fFfF:1.2.3.4'
            props = {
                'loc': 'cool',
                'latlong': '0,2',
                'dns:rev': 'vertex.link',
                'place': place,
            }
            opts = {'vars': {'valu': valu, 'p': props}}
            q = '[(inet:ipv6=$valu :loc=$p.loc :latlong=$p.latlong :dns:rev=$p."dns:rev" :place=$p.place)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:ipv6', valu.lower()))
            self.eq(node.get('dns:rev'), 'vertex.link')
            self.eq(node.get('ipv4'), 0x01020304)
            self.eq(node.get('latlong'), (0.0, 2.0))
            self.eq(node.get('loc'), 'cool')
            self.eq(node.get('place'), place)

            nodes = await core.nodes('[inet:ipv6="::1"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:ipv6', '::1'))
            self.none(node.get('ipv4'))

            self.len(1, await core.nodes('inet:ipv6=0::1'))
            self.len(1, await core.nodes('inet:ipv6*range=(0::1, 0::1)'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv6=foo]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv6=foo-bar.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[inet:ipv6=foo-bar-duck.com]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo"] [inet:ipv6=$node.value()]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:str="foo-bar.com"] [inet:ipv6=$node.value()]')

            self.len(0, await core.nodes('[inet:ipv6?=foo]'))
            self.len(0, await core.nodes('[inet:ipv6?=foo-bar.com]'))

            self.len(0, await core.nodes('[test:str="foo"] [inet:ipv6?=$node.value()] -test:str'))
            self.len(0, await core.nodes('[test:str="foo-bar.com"] [inet:ipv6?=$node.value()] -test:str'))

            await core.nodes('[ inet:ipv6=2a00:: inet:ipv6=2a00::1 ]')

            self.len(1, await core.nodes('inet:ipv6>2a00::'))
            self.len(2, await core.nodes('inet:ipv6>=2a00::'))
            self.len(2, await core.nodes('inet:ipv6<2a00::'))
            self.len(3, await core.nodes('inet:ipv6<=2a00::'))

            self.len(1, await core.nodes('inet:ipv6 +inet:ipv6>2a00::'))
            self.len(2, await core.nodes('inet:ipv6 +inet:ipv6>=2a00::'))
            self.len(2, await core.nodes('inet:ipv6 +inet:ipv6<2a00::'))
            self.len(3, await core.nodes('inet:ipv6 +inet:ipv6<=2a00::'))

    async def test_ipv6_lift_range(self):

        async with self.getTestCore() as core:

            for i in range(5):
                valu = f'0::f00{i}'
                nodes = await core.nodes('[inet:ipv6=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)

            self.len(3, await core.nodes('inet:ipv6=0::f001-0::f003'))
            self.len(3, await core.nodes('[inet:ipv6=0::f001-0::f003]'))
            self.len(3, await core.nodes('inet:ipv6 +inet:ipv6=0::f001-0::f003'))
            self.len(3, await core.nodes('inet:ipv6*range=(0::f001, 0::f003)'))

    async def test_ipv6_filt_cidr(self):

        async with self.getTestCore() as core:

            self.len(5, await core.nodes('[ inet:ipv6=0::f000/126 inet:ipv6=0::ffff:a2c4 ]'))
            self.len(4, await core.nodes('inet:ipv6 +inet:ipv6=0::f000/126'))
            self.len(1, await core.nodes('inet:ipv6 -inet:ipv6=0::f000/126'))

            self.len(256, await core.nodes('[ inet:ipv6=0::ffff:192.168.1.0/120]'))
            self.len(256, await core.nodes('[ inet:ipv6=0::ffff:192.168.2.0/120]'))
            self.len(256, await core.nodes('inet:ipv6=0::ffff:192.168.1.0/120'))

            # Seed some nodes for bounds checking
            vals = list(range(1, 33))
            q = 'for $v in $vals { [inet:ipv6=`0::10.2.1.{$v}` ] }'
            self.len(len(vals), await core.nodes(q, opts={'vars': {'vals': vals}}))

            nodes = await core.nodes('inet:ipv6=0::10.2.1.4/128')
            self.len(1, nodes)
            self.len(1, await core.nodes('inet:ipv6 +inet:ipv6=0::10.2.1.4/128'))
            self.len(1, await core.nodes('inet:ipv6 +inet:ipv6=0::10.2.1.4'))

            nodes = await core.nodes('inet:ipv6=0::10.2.1.4/127')
            self.len(2, nodes)
            self.len(2, await core.nodes('inet:ipv6 +inet:ipv6=0::10.2.1.4/127'))

            # 0::10.2.1.0 -> 0::10.2.1.3 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv6=0::10.2.1.1/126')
            self.len(3, nodes)

            nodes = await core.nodes('inet:ipv6=0::10.2.1.2/126')
            self.len(3, nodes)

            # 0::10.2.1.0 -> 0::10.2.1.7 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv6=0::10.2.1.0/125')
            self.len(7, nodes)

            # 0::10.2.1.8 -> 0::10.2.1.15
            nodes = await core.nodes('inet:ipv6=0::10.2.1.8/125')
            self.len(8, nodes)

            # 0::10.2.1.0 -> 0::10.2.1.15 but we don't have 0::10.2.1.0 in the core
            nodes = await core.nodes('inet:ipv6=0::10.2.1.1/124')
            self.len(15, nodes)

    async def test_mac(self):
        formname = 'inet:mac'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.eq(t.norm('00:00:00:00:00:00'), ('00:00:00:00:00:00', {}))
            self.eq(t.norm('FF:ff:FF:ff:FF:ff'), ('ff:ff:ff:ff:ff:ff', {}))
            self.raises(s_exc.BadTypeValu, t.norm, ' FF:ff:FF:ff:FF:ff ')
            self.raises(s_exc.BadTypeValu, t.norm, 'GG:ff:FF:ff:FF:ff')

            # Form Tests ======================================================
            nodes = await core.nodes('[inet:mac="00:00:00:00:00:00"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:mac', '00:00:00:00:00:00'))
            self.none(node.get('vendor'))

            nodes = await core.nodes('[inet:mac="00:00:00:00:00:00" :vendor=Cool]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:mac', '00:00:00:00:00:00'))
            self.eq(node.get('vendor'), 'Cool')

    async def test_net4(self):
        tname = 'inet:net4'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('1.2.3.4', '5.6.7.8')
            expected = ((16909060, 84281096), {'subs': {'min': 16909060, 'max': 84281096}})
            self.eq(t.norm(valu), expected)

            valu = '1.2.3.4-5.6.7.8'
            self.eq(t.norm(valu), expected)

            valu = '1.2.3.0/24'
            expected = ((0x01020300, 0x010203ff), {'subs': {'min': 0x01020300, 'max': 0x010203ff}})
            self.eq(t.norm(valu), expected)

            valu = '5.6.7.8-1.2.3.4'
            self.raises(s_exc.BadTypeValu, t.norm, valu)

            valu = ('1.2.3.4', '5.6.7.8', '7.8.9.10')
            self.raises(s_exc.BadTypeValu, t.norm, valu)

    async def test_net6(self):
        tname = 'inet:net6'
        async with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('0:0:0:0:0:0:0:0', '::Ff')
            expected = (('::', '::ff'), {'subs': {'min': '::', 'max': '::ff'}})
            self.eq(t.norm(valu), expected)

            valu = '0:0:0:0:0:0:0:0-::Ff'
            self.eq(t.norm(valu), expected)

            # Test case in which ipaddress ordering is not alphabetical
            valu = ('3300:100::', '3300:100:1::ffff')
            expected = (('3300:100::', '3300:100:1::ffff'), {'subs': {'min': '3300:100::', 'max': '3300:100:1::ffff'}})
            self.eq(t.norm(valu), expected)

            valu = '2001:db8::/101'

            expected = (('2001:db8::', '2001:db8::7ff:ffff'),
                        {'subs': {'min': '2001:db8::', 'max': '2001:db8::7ff:ffff'}})
            self.eq(t.norm(valu), expected)

            valu = ('fe00::', 'fd00::')
            self.raises(s_exc.BadTypeValu, t.norm, valu)

            valu = ('fd00::', 'fe00::', 'ff00::')
            self.raises(s_exc.BadTypeValu, t.norm, valu)

    async def test_passwd(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:passwd=2Cool4u]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:passwd', '2Cool4u'))
            self.eq(node.get('md5'), '91112d75297841c12ca655baafc05104')
            self.eq(node.get('sha1'), '2984ab44774294be9f7a369bbd73b52021bf0bb4')
            self.eq(node.get('sha256'), '62c7174a99ff0afd4c828fc779d2572abc2438415e3ca9769033d4a36479b14f')

    async def test_port(self):
        tname = 'inet:port'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(tname)
            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.eq(t.norm(0), (0, {}))
            self.eq(t.norm(1), (1, {}))
            self.eq(t.norm('2'), (2, {}))
            self.eq(t.norm('0xF'), (15, {}))
            self.eq(t.norm(65535), (65535, {}))
            self.raises(s_exc.BadTypeValu, t.norm, 65536)

    async def test_rfc2822_addr(self):
        formname = 'inet:rfc2822:addr'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.eq(t.norm('FooBar'), ('foobar', {'subs': {}}))
            self.eq(t.norm('visi@vertex.link'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))
            self.eq(t.norm('foo bar<visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('foo bar <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('"foo bar "   <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('<visi@vertex.link>'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))

            valu = t.norm('bob\udcfesmith@woot.com')[0]
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
                'ipv4': 2130706433,
                'port': 12345,
                'proto': 'tcp',
            }),
            ('tcp://127.0.0.1', 'tcp://127.0.0.1', {
                'ipv4': 2130706433,
                'proto': 'tcp',
            }),
            ('tcp://[::1]:12345', 'tcp://[::1]:12345', {
                'ipv6': '::1',
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
            for valu, expected_valu, props in data:
                nodes = await core.nodes('[inet:server=$valu]', opts={'vars': {'valu': valu}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, ('inet:server', expected_valu))
                for p, v in props.items():
                    self.eq(node.get(p), v)

    async def test_servfile(self):
        async with self.getTestCore() as core:
            valu = ('tcp://127.0.0.1:4040', 64 * 'f')
            nodes = await core.nodes('[(inet:servfile=$valu :server:host=$host)]',
                                     opts={'vars': {'valu': valu, 'host': 32 * 'a'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:servfile', ('tcp://127.0.0.1:4040', 'sha256:' + 64 * 'f')))
            self.eq(node.get('server'), 'tcp://127.0.0.1:4040')
            self.eq(node.get('server:host'), 32 * 'a')
            self.eq(node.get('server:port'), 4040)
            self.eq(node.get('server:proto'), 'tcp')
            self.eq(node.get('server:ipv4'), 2130706433)
            self.eq(node.get('file'), 'sha256:' + 64 * 'f')

    async def test_ssl_cert(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:ssl:cert=("tcp://1.2.3.4:443", "guid:abcdabcdabcdabcdabcdabcdabcdabcd")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('file'), 'guid:abcdabcdabcdabcdabcdabcdabcdabcd')
            self.eq(node.get('server'), 'tcp://1.2.3.4:443')

            self.eq(node.get('server:port'), 443)
            self.eq(node.get('server:ipv4'), 0x01020304)

    async def test_url(self):
        formname = 'inet:url'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)
            self.raises(s_exc.BadTypeValu, t.norm, 'http:///wat')
            self.raises(s_exc.BadTypeValu, t.norm, 'wat')  # No Protocol
            self.raises(s_exc.BadTypeValu, t.norm, "file://''")  # Missing address/url
            self.raises(s_exc.BadTypeValu, t.norm, "file://#")  # Missing address/url
            self.raises(s_exc.BadTypeValu, t.norm, "file://$")  # Missing address/url
            self.raises(s_exc.BadTypeValu, t.norm, "file://%")  # Missing address/url

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com/hehe.asp')
            valu = t.norm('http://www.googlesites.com/hehe\udcfestuff.asp')
            url = 'http://www.googlesites.com/hehe\udcfestuff.asp'
            expected = (url, {'subs': {
                'proto': 'http',
                'path': '/hehe\udcfestuff.asp',
                'port': 80,
                'params': '',
                'fqdn': 'www.googlesites.com',
                'base': url
            }})
            self.eq(valu, expected)

            url = 'https://dummyimage.com/600x400/000/fff.png&text=cat@bam.com'
            valu = t.norm(url)
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
            valu = t.norm(url)
            expected = (url, {'subs': {
                'proto': 'http',
                'path': '/index.html',
                'params': '?foo=bar',
                'ipv4': 0,
                'port': 80,
                'base': 'http://0.0.0.0/index.html'
            }})
            self.eq(valu, expected)

            unc = '\\\\0--1.ipv6-literal.net\\share\\path\\to\\filename.txt'
            url = 'smb://::1/share/path/to/filename.txt'
            valu = t.norm(unc)
            expected = (url, {'subs': {
                'base': url,
                'proto': 'smb',
                'params': '',
                'path': '/share/path/to/filename.txt',
                'ipv6': '::1',
            }})
            self.eq(valu, expected)

            unc = '\\\\0--1.ipv6-literal.net@1234\\share\\filename.txt'
            url = 'smb://[::1]:1234/share/filename.txt'
            valu = t.norm(unc)
            expected = (url, {'subs': {
                'base': url,
                'proto': 'smb',
                'path': '/share/filename.txt',
                'params': '',
                'port': 1234,
                'ipv6': '::1',
            }})
            self.eq(valu, expected)

            unc = '\\\\server@SSL@1234\\share\\path\\to\\filename.txt'
            url = 'https://server:1234/share/path/to/filename.txt'
            valu = t.norm(unc)
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

            self.none(nodes[0].get('ipv4'))
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
            self.eq(nodes[0].get('ipv6'), 'fedc:ba98:7654:3210:fedc:ba98:7654:3210')
            self.eq(nodes[0].get('port'), 80)

            self.eq(nodes[1].get('base'), 'http://[1080::8:800:200c:417a]/index.html')
            self.eq(nodes[1].get('proto'), 'http')
            self.eq(nodes[1].get('path'), '/index.html')
            self.eq(nodes[1].get('params'), '?foo=bar')
            self.eq(nodes[1].get('ipv6'), '1080::8:800:200c:417a')
            self.eq(nodes[1].get('port'), 80)

            self.eq(nodes[2].get('base'), 'http://[3ffe:2a00:100:7031::1]')
            self.eq(nodes[2].get('proto'), 'http')
            self.eq(nodes[2].get('path'), '')
            self.eq(nodes[2].get('params'), '')
            self.eq(nodes[2].get('ipv6'), '3ffe:2a00:100:7031::1')
            self.eq(nodes[2].get('port'), 80)

            self.eq(nodes[3].get('base'), 'http://[1080::8:800:200c:417a]/foo')
            self.eq(nodes[3].get('proto'), 'http')
            self.eq(nodes[3].get('path'), '/foo')
            self.eq(nodes[3].get('params'), '')
            self.eq(nodes[3].get('ipv6'), '1080::8:800:200c:417a')
            self.eq(nodes[3].get('port'), 80)

            self.eq(nodes[4].get('base'), 'http://[::c009:505]/ipng')
            self.eq(nodes[4].get('proto'), 'http')
            self.eq(nodes[4].get('path'), '/ipng')
            self.eq(nodes[4].get('params'), '')
            self.eq(nodes[4].get('ipv6'), '::c009:505')
            self.eq(nodes[4].get('port'), 80)

            self.eq(nodes[5].get('base'), 'http://[::ffff:129.144.52.38]:80/index.html')
            self.eq(nodes[5].get('proto'), 'http')
            self.eq(nodes[5].get('path'), '/index.html')
            self.eq(nodes[5].get('params'), '')
            self.eq(nodes[5].get('ipv6'), '::ffff:129.144.52.38')
            self.eq(nodes[5].get('port'), 80)

            self.eq(nodes[6].get('base'), 'https://[2010:836b:4179::836b:4179]')
            self.eq(nodes[6].get('proto'), 'https')
            self.eq(nodes[6].get('path'), '')
            self.eq(nodes[6].get('params'), '')
            self.eq(nodes[6].get('ipv6'), '2010:836b:4179::836b:4179')
            self.eq(nodes[6].get('port'), 443)

    async def test_url_file(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            self.raises(s_exc.BadTypeValu, t.norm, 'file:////')
            self.raises(s_exc.BadTypeValu, t.norm, 'file://///')
            self.raises(s_exc.BadTypeValu, t.norm, 'file://')
            self.raises(s_exc.BadTypeValu, t.norm, 'file:')

            url = 'file:///'
            expected = (url, {'subs': {
                'base': url,
                'path': '/',
                'proto': 'file',
                'params': '',
            }})
            self.eq(t.norm(url), expected)

            url = 'file:///home/foo/Documents/html/index.html'
            expected = (url, {'subs': {
                'base': url,
                'path': '/home/foo/Documents/html/index.html',
                'proto': 'file',
                'params': '',
            }})
            self.eq(t.norm(url), expected)

            url = 'file:///c:/path/to/my/file.jpg'
            expected = (url, {'subs': {
                'base': url,
                'path': 'c:/path/to/my/file.jpg',
                'params': '',
                'proto': 'file'
            }})
            self.eq(t.norm(url), expected)

            url = 'file://localhost/c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': 'c:/Users/BarUser/stuff/moar/stuff.txt',
                'params': '',
                'fqdn': 'localhost',
                'base': url,
            }})
            self.eq(t.norm(url), expected)

            url = 'file:///c:/Users/BarUser/stuff/moar/stuff.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': 'c:/Users/BarUser/stuff/moar/stuff.txt',
                'params': '',
                'base': url,
            }})
            self.eq(t.norm(url), expected)

            url = 'file://localhost/home/visi/synapse/README.rst'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': '/home/visi/synapse/README.rst',
                'params': '',
                'fqdn': 'localhost',
                'base': url,
            }})
            self.eq(t.norm(url), expected)

            url = 'file:/C:/invisig0th/code/synapse/README.rst'
            expected = ('file:///C:/invisig0th/code/synapse/README.rst', {'subs': {
                'proto': 'file',
                'path': 'C:/invisig0th/code/synapse/README.rst',
                'params': '',
                'base': 'file:///C:/invisig0th/code/synapse/README.rst'
            }})
            self.eq(t.norm(url), expected)

            url = 'file://somehost/path/to/foo.txt'
            expected = (url, {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/path/to/foo.txt',
                'fqdn': 'somehost',
                'base': url
            }})
            self.eq(t.norm(url), expected)

            url = 'file:/c:/foo/bar/baz/single/slash.txt'
            expected = ('file:///c:/foo/bar/baz/single/slash.txt', {'subs': {
                'proto': 'file',
                'params': '',
                'path': 'c:/foo/bar/baz/single/slash.txt',
                'base': 'file:///c:/foo/bar/baz/single/slash.txt',
            }})
            self.eq(t.norm(url), expected)

            url = 'file:c:/foo/bar/baz/txt'
            expected = ('file:///c:/foo/bar/baz/txt', {'subs': {
                'proto': 'file',
                'params': '',
                'path': 'c:/foo/bar/baz/txt',
                'base': 'file:///c:/foo/bar/baz/txt',
            }})
            self.eq(t.norm(url), expected)

            url = 'file:/home/visi/synapse/synapse/lib/'
            expected = ('file:///home/visi/synapse/synapse/lib/', {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/home/visi/synapse/synapse/lib/',
                'base': 'file:///home/visi/synapse/synapse/lib/',
            }})
            self.eq(t.norm(url), expected)

            url = 'file://foo.vertex.link/home/bar/baz/biz.html'
            expected = (url, {'subs': {
                'proto': 'file',
                'path': '/home/bar/baz/biz.html',
                'params': '',
                'fqdn': 'foo.vertex.link',
                'base': 'file://foo.vertex.link/home/bar/baz/biz.html',
            }})
            self.eq(t.norm(url), expected)

            url = 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': 'file',
                'fqdn': 'somehost.vertex.link',
                'base': 'file://visi@vertex.link@somehost.vertex.link/c:/invisig0th/code/synapse/',
                'path': 'c:/invisig0th/code/synapse/',
                'user': 'visi@vertex.link',
                'params': '',
            }})
            self.eq(t.norm(url), expected)

            url = 'file://foo@bar.com:neato@password@7.7.7.7/c:/invisig0th/code/synapse/'
            expected = (url, {'subs': {
                'proto': 'file',
                'ipv4': 117901063,
                'base': 'file://foo@bar.com:neato@password@7.7.7.7/c:/invisig0th/code/synapse/',
                'path': 'c:/invisig0th/code/synapse/',
                'user': 'foo@bar.com',
                'passwd': 'neato@password',
                'params': '',
            }})
            self.eq(t.norm(url), expected)

            # not allowed by the rfc
            self.raises(s_exc.BadTypeValu, t.norm, 'file:foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/')

            # Also an invalid URL, but doesn't cleanly fall out, because well, it could be a valid filename
            url = 'file:/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/'
            expected = ('file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/', {'subs': {
                'proto': 'file',
                'path': '/foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/',
                'params': '',
                'base': 'file:///foo@bar.com:password@1.162.27.3:12345/c:/invisig0th/code/synapse/',
            }})
            self.eq(t.norm(url), expected)

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
            self.eq(t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.2.2
            url = 'FILE:c|/synapse/synapse/lib/stormtypes.py'
            expected = ('file:///c|/synapse/synapse/lib/stormtypes.py', {'subs': {
                'path': 'c|/synapse/synapse/lib/stormtypes.py',
                'proto': 'file',
                'params': '',
                'base': 'file:///c|/synapse/synapse/lib/stormtypes.py',
            }})
            self.eq(t.norm(url), expected)

            # https://datatracker.ietf.org/doc/html/rfc8089#appendix-E.3.2
            url = 'file:////host.vertex.link/SharedDir/Unc/FilePath'
            expected = ('file:////host.vertex.link/SharedDir/Unc/FilePath', {'subs': {
                'proto': 'file',
                'params': '',
                'path': '/SharedDir/Unc/FilePath',
                'fqdn': 'host.vertex.link',
                'base': 'file:////host.vertex.link/SharedDir/Unc/FilePath',
            }})
            self.eq(t.norm(url), expected)

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
            self.eq(t.norm(url), expected)

    async def test_url_fqdn(self):

        async with self.getTestCore() as core:

            t = core.model.type('inet:url')

            host = 'Vertex.Link'
            norm_host = core.model.type('inet:fqdn').norm(host)[0]
            repr_host = core.model.type('inet:fqdn').repr(norm_host)

            self.eq(norm_host, 'vertex.link')
            self.eq(repr_host, 'vertex.link')

            await self._test_types_url_behavior(t, 'fqdn', host, norm_host, repr_host)

    async def test_url_ipv4(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '192[.]168.1[.]1'
            norm_host = core.model.type('inet:ipv4').norm(host)[0]
            repr_host = core.model.type('inet:ipv4').repr(norm_host)
            self.eq(norm_host, 3232235777)
            self.eq(repr_host, '192.168.1.1')

            await self._test_types_url_behavior(t, 'ipv4', host, norm_host, repr_host)

    async def test_url_ipv6(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '::1'
            norm_host = core.model.type('inet:ipv6').norm(host)[0]
            repr_host = core.model.type('inet:ipv6').repr(norm_host)
            self.eq(norm_host, '::1')
            self.eq(repr_host, '::1')

            await self._test_types_url_behavior(t, 'ipv6', host, norm_host, repr_host)

            # IPv6 Port Special Cases
            weird = t.norm('http://::1:81/hehe')
            self.eq(weird[1]['subs']['ipv6'], '::1:81')
            self.eq(weird[1]['subs']['port'], 80)

            self.raises(s_exc.BadTypeValu, t.norm, 'http://0:0:0:0:0:0:0:0:81/')

    async def _test_types_url_behavior(self, t, htype, host, norm_host, repr_host):

        # Handle IPv6 Port Brackets
        host_port = host
        repr_host_port = repr_host

        if htype == 'ipv6':
            host_port = f'[{host}]'
            repr_host_port = f'[{repr_host}]'

        # URL with auth and port.
        url = f'https://user:password@{host_port}:1234/a/b/c/'
        expected = (f'https://user:password@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 1234,
            'base': f'https://user:password@{repr_host_port}:1234/a/b/c/',
            'params': ''
        }})
        self.eq(t.norm(url), expected)

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
        self.eq(t.norm(url), expected)

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
        self.eq(t.norm(url), expected)

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
        self.eq(t.norm(url), expected)

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
        self.eq(t.norm(url), expected)

        # URL with no port, but default port valu.
        # Port should be in subs, but not normed URL.
        url = f'https://user:password@{host}/a/b/c/?foo=bar&baz=faz'
        expected = (f'https://user:password@{repr_host}/a/b/c/?foo=bar&baz=faz', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 443,
            'base': f'https://user:password@{repr_host}/a/b/c/',
            'params': '?foo=bar&baz=faz',
        }})
        self.eq(t.norm(url), expected)

        # URL with no port and no default port valu.
        # Port should not be in subs or normed URL.
        url = f'arbitrary://user:password@{host}/a/b/c/'
        expected = (f'arbitrary://user:password@{repr_host}/a/b/c/', {'subs': {
            'proto': 'arbitrary', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host,
            'base': f'arbitrary://user:password@{repr_host}/a/b/c/',
            'params': '',
        }})
        self.eq(t.norm(url), expected)

        # URL with user but no password.
        # User should still be in URL and subs.
        url = f'https://user@{host_port}:1234/a/b/c/'
        expected = (f'https://user@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', htype: norm_host, 'port': 1234,
            'base': f'https://user@{repr_host_port}:1234/a/b/c/',
            'params': '',
        }})
        self.eq(t.norm(url), expected)

        # URL with no user/password.
        # User/Password should not be in URL or subs.
        url = f'https://{host_port}:1234/a/b/c/'
        expected = (f'https://{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', htype: norm_host, 'port': 1234,
            'base': f'https://{repr_host_port}:1234/a/b/c/',
            'params': '',
        }})
        self.eq(t.norm(url), expected)

        # URL with no path.
        url = f'https://{host_port}:1234'
        expected = (f'https://{repr_host_port}:1234', {'subs': {
            'proto': 'https', 'path': '', htype: norm_host, 'port': 1234,
            'base': f'https://{repr_host_port}:1234',
            'params': '',
        }})
        self.eq(t.norm(url), expected)

        # URL with no path or port or default port.
        url = f'a://{host}'
        expected = (f'a://{repr_host}', {'subs': {
            'proto': 'a', 'path': '', htype: norm_host,
            'base': f'a://{repr_host}',
            'params': '',
        }})
        self.eq(t.norm(url), expected)

    async def test_urlfile(self):
        async with self.getTestCore() as core:
            valu = ('https://vertex.link/a_cool_program.exe', 64 * 'f')
            nodes = await core.nodes('[inet:urlfile=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:urlfile', (valu[0], 'sha256:' + valu[1])))
            self.eq(node.get('url'), 'https://vertex.link/a_cool_program.exe')
            self.eq(node.get('file'), 'sha256:' + 64 * 'f')

            url = await core.nodes('inet:url')
            self.len(1, url)
            url = url[0]
            self.eq(443, url.props['port'])
            self.eq('', url.props['params'])
            self.eq('vertex.link', url.props['fqdn'])
            self.eq('https', url.props['proto'])
            self.eq('https://vertex.link/a_cool_program.exe', url.props['base'])

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
            nodes = await core.nodes('[inet:urlredir=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:urlredir', valu))
            self.eq(node.get('src'), 'https://vertex.link/idk')
            self.eq(node.get('src:fqdn'), 'vertex.link')
            self.eq(node.get('dst'), 'https://cool.vertex.newp:443/something_else')
            self.eq(node.get('dst:fqdn'), 'cool.vertex.newp')
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))
            self.len(1, await core.nodes('inet:fqdn=cool.vertex.newp'))

    async def test_user(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:user="cool User "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:user', 'cool user '))

    async def test_web_acct(self):
        async with self.getTestCore() as core:
            formname = 'inet:web:acct'

            # Type Tests
            t = core.model.type(formname)

            with self.raises(s_exc.BadTypeValu):
                t.norm('vertex.link,person1')
            enorm = ('vertex.link', 'person1')
            edata = {'subs': {'user': 'person1',
                              'site': 'vertex.link',
                              'site:host': 'vertex',
                              'site:domain': 'link', },
                     'adds': (
                        ('inet:fqdn', 'vertex.link', {'subs': {'domain': 'link', 'host': 'vertex'}}),
                        ('inet:user', 'person1', {}),
                    )}
            self.eq(t.norm(('VerTex.linK', 'PerSon1')), (enorm, edata))

            # Form Tests
            valu = ('blogs.Vertex.link', 'Brutus')
            place = s_common.guid()
            props = {
                'avatar': 'sha256:' + 64 * 'a',
                'banner': 'sha256:' + 64 * 'b',
                'dob': -64836547200000,
                'email': 'brutus@vertex.link',
                'linked:accts': (('twitter.com', 'brutus'),
                                 ('linkedin.com', 'brutester'),
                                 ('linkedin.com', 'brutester')),
                'latlong': '0,0',
                'place': place,
                'loc': 'sol',
                'name': 'ካሳር',
                'aliases': ('foo', 'bar', 'bar'),
                'name:en': 'brutus',
                'occupation': 'jurist',
                'passwd': 'hunter2',
                'phone': '555-555-5555',
                'realname': 'Брут',
                'realname:en': 'brutus',
                'signup': 3,
                'signup:client': '0.0.0.4',
                'signup:client:ipv6': '::1',
                'tagline': 'Taglines are not tags',
                'url': 'https://blogs.vertex.link/',
                'webpage': 'https://blogs.vertex.link/brutus',
                'recovery:email': 'recovery@vertex.link',
            }
            q = '''[(inet:web:acct=$valu :avatar=$p.avatar :banner=$p.banner :dob=$p.dob :email=$p.email
                :linked:accts=$p."linked:accts" :latlong=$p.latlong :loc=$p.loc :place=$p.place
                :name=$p.name :aliases=$p.aliases :name:en=$p."name:en"
                :realname=$p.realname :realname:en=$p."realname:en"
                :occupation=$p.occupation :passwd=$p.passwd :phone=$p.phone
                :signup=$p.signup :signup:client=$p."signup:client" :signup:client:ipv6=$p."signup:client:ipv6"
                :tagline=$p.tagline :url=$p.url :webpage=$p.webpage :recovery:email=$p."recovery:email")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:acct', ('blogs.vertex.link', 'brutus')))
            self.eq(node.get('site'), 'blogs.vertex.link')
            self.eq(node.get('user'), 'brutus')
            self.eq(node.get('avatar'), 'sha256:' + 64 * 'a')
            self.eq(node.get('banner'), 'sha256:' + 64 * 'b')
            self.eq(node.get('dob'), -64836547200000)
            self.eq(node.get('email'), 'brutus@vertex.link')
            self.eq(node.get('linked:accts'), (('linkedin.com', 'brutester'), ('twitter.com', 'brutus')))
            self.eq(node.get('latlong'), (0.0, 0.0))
            self.eq(node.get('place'), place)
            self.eq(node.get('loc'), 'sol')
            self.eq(node.get('name'), 'ካሳር')
            self.eq(node.get('aliases'), ('bar', 'foo'))
            self.eq(node.get('name:en'), 'brutus')
            self.eq(node.get('realname'), 'брут')
            self.eq(node.get('passwd'), 'hunter2')
            self.eq(node.get('phone'), '5555555555')
            self.eq(node.get('signup'), 3)
            self.eq(node.get('signup:client'), 'tcp://0.0.0.4')
            self.eq(node.get('signup:client:ipv4'), 4)
            self.eq(node.get('signup:client:ipv6'), '::1')
            self.eq(node.get('tagline'), 'Taglines are not tags')
            self.eq(node.get('recovery:email'), 'recovery@vertex.link')
            self.eq(node.get('url'), 'https://blogs.vertex.link/')
            self.eq(node.get('webpage'), 'https://blogs.vertex.link/brutus')
            self.len(2, await core.nodes('inet:web:acct=(blogs.vertex.link, brutus) :linked:accts -> inet:web:acct'))

    async def test_web_action(self):
        async with self.getTestCore() as core:
            valu = 32 * 'a'
            place = s_common.guid()
            q = '''[(inet:web:action=$valu :act="Did a Thing" :acct=(vertex.link, vertexmc) :time=(0) :client=0.0.0.0
                :loc=ru :latlong="30,30" :place=$place)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'place': place}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:action', valu))
            self.eq(node.get('act'), 'did a thing')
            self.eq(node.get('acct'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('acct:site'), 'vertex.link')
            self.eq(node.get('acct:user'), 'vertexmc')
            self.eq(node.get('time'), 0)
            self.eq(node.get('client'), 'tcp://0.0.0.0')
            self.eq(node.get('client:ipv4'), 0)
            self.eq(node.get('loc'), 'ru')
            self.eq(node.get('latlong'), (30.0, 30.0))
            self.eq(node.get('place'), place)
            self.len(2, await core.nodes('inet:fqdn'))

            q = '[inet:web:action=(test,) :acct:user=hehe :acct:site=newp.com :client="tcp://::ffff:8.7.6.5"]'
            self.len(1, await core.nodes(q))
            self.len(1, await core.nodes('inet:ipv4=8.7.6.5'))
            self.len(1, await core.nodes('inet:ipv6="::ffff:8.7.6.5"'))
            self.len(1, await core.nodes('inet:fqdn=newp.com'))
            self.len(1, await core.nodes('inet:user=hehe'))

    async def test_web_chprofile(self):
        async with self.getTestCore() as core:
            valu = s_common.guid()
            props = {
                'acct': ('vertex.link', 'vertexmc'),
                'client': '0.0.0.3',
                'time': 0,
                'pv': ('inet:web:acct:site', 'Example.com')
            }
            q = '[(inet:web:chprofile=$valu :acct=$p.acct :client=$p.client :time=$p.time :pv=$p.pv)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:chprofile', valu))
            self.eq(node.get('acct'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('acct:site'), 'vertex.link')
            self.eq(node.get('acct:user'), 'vertexmc')
            self.eq(node.get('client'), 'tcp://0.0.0.3')
            self.eq(node.get('client:ipv4'), 3)
            self.eq(node.get('time'), 0)
            self.eq(node.get('pv'), ('inet:web:acct:site', 'example.com'))
            self.eq(node.get('pv:prop'), 'inet:web:acct:site')
            q = '[inet:web:chprofile=(test,) :acct:user=hehe :acct:site=newp.com :client="tcp://::ffff:8.7.6.5"]'
            self.len(1, await core.nodes(q))
            self.len(1, await core.nodes('inet:ipv4=8.7.6.5'))
            self.len(1, await core.nodes('inet:ipv6="::ffff:8.7.6.5"'))
            self.len(1, await core.nodes('inet:user=hehe'))

    async def test_web_file(self):
        async with self.getTestCore() as core:
            valu = (('vertex.link', 'vertexmc'), 64 * 'f')
            nodes = await core.nodes('[(inet:web:file=$valu :name=Cool :posted=(0) :client="::1")]',
                                     opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:file', (valu[0], 'sha256:' + valu[1])))
            self.eq(node.get('acct'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('acct:site'), 'vertex.link')
            self.eq(node.get('acct:user'), 'vertexmc')
            self.eq(node.get('file'), 'sha256:' + 64 * 'f')
            self.eq(node.get('name'), 'cool')
            self.eq(node.get('posted'), 0)
            self.eq(node.get('client'), 'tcp://::1')
            self.eq(node.get('client:ipv6'), '::1')

    async def test_web_follows(self):
        async with self.getTestCore() as core:
            valu = (('vertex.link', 'vertexmc'), ('example.com', 'aUser'))
            nodes = await core.nodes('[inet:web:follows=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:follows', (('vertex.link', 'vertexmc'), ('example.com', 'auser'))))
            self.eq(node.get('follower'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('followee'), ('example.com', 'auser'))

    async def test_web_group(self):
        async with self.getTestCore() as core:
            place = s_common.guid()
            props = {
                'avatar': 64 * 'a',
                'place': place
            }
            q = '''[(inet:web:group=(vertex.link, CoolGroup)
                :name='The coolest group'
                :aliases=(foo, bar, bar)
                :name:en='The coolest group (in english)'
                :url='https://vertex.link/CoolGroup'
                :avatar=$p.avatar
                :desc='A really cool group'
                :webpage='https://vertex.link/CoolGroup/page'
                :loc='the internet'
                :latlong='0,0'
                :place=$p.place
                :signup=(0)
                :signup:client=0.0.0.0
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:group', ('vertex.link', 'CoolGroup')))
            self.eq(node.get('site'), 'vertex.link')
            self.eq(node.get('id'), 'CoolGroup')
            self.eq(node.get('name'), 'The coolest group')
            self.eq(node.get('aliases'), ('bar', 'foo'))
            self.eq(node.get('name:en'), 'The coolest group (in english)')
            self.eq(node.get('url'), 'https://vertex.link/CoolGroup')
            self.eq(node.get('avatar'), 'sha256:' + 64 * 'a')
            self.eq(node.get('desc'), 'A really cool group')
            self.eq(node.get('webpage'), 'https://vertex.link/CoolGroup/page')
            self.eq(node.get('loc'), 'the internet')
            self.eq(node.get('latlong'), (0.0, 0.0))
            self.eq(node.get('place'), place)
            self.eq(node.get('signup'), 0)
            self.eq(node.get('signup:client'), 'tcp://0.0.0.0')

    async def test_web_logon(self):
        async with self.getTestCore() as core:
            valu = s_common.guid()
            place = s_common.guid()
            props = {
                'place': place
            }
            q = '''[(inet:web:logon=$valu
                :acct=(vertex.link, vertexmc)
                :time=(0)
                :client='::'
                :logout=(1)
                :loc=ru
                :latlong="30,30"
                :place=$p.place
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:logon', valu))
            self.eq(node.get('acct'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('time'), 0)
            self.eq(node.get('client'), 'tcp://::')
            self.eq(node.get('client:ipv6'), '::')
            self.eq(node.get('logout'), 1)
            self.eq(node.get('loc'), 'ru')
            self.eq(node.get('latlong'), (30.0, 30.0))
            self.eq(node.get('place'), place)

    async def test_web_memb(self):
        async with self.getTestCore() as core:
            q = '''[(inet:web:memb=((vertex.link, visi), (vertex.link, kenshoto)) :title=cool :joined=2015)]'''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:memb', (('vertex.link', 'visi'), ('vertex.link', 'kenshoto'))))
            self.eq(node.get('joined'), 1420070400000)
            self.eq(node.get('title'), 'cool')
            self.eq(node.get('acct'), ('vertex.link', 'visi'))
            self.eq(node.get('group'), ('vertex.link', 'kenshoto'))

    async def test_web_member(self):

        async with self.getTestCore() as core:
            msgs = await core.stormlist('''
                [ inet:web:member=*
                    :acct=twitter.com/invisig0th
                    :channel=*
                    :group=twitter.com/nerds
                    :added=2022
                    :removed=2023
                ]
            ''')
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node[1]['props']['channel'])
            self.eq(1640995200000, node[1]['props']['added'])
            self.eq(1672531200000, node[1]['props']['removed'])
            self.eq(('twitter.com', 'nerds'), node[1]['props']['group'])
            self.eq(('twitter.com', 'invisig0th'), node[1]['props']['acct'])

    async def test_web_mesg(self):
        async with self.getTestCore() as core:
            file0 = 'sha256:' + 64 * 'f'
            props = {
                'url': 'https://vertex.link/messages/0',
                'client': 'tcp://1.2.3.4',
                'text': 'a cool Message',
                'deleted': True,
                'file': file0
            }
            q = '''[(inet:web:mesg=(VERTEX.link/visi, vertex.link/vertexMC, (0))
                :url=$p.url :client=$p.client :text=$p.text :deleted=$p.deleted :file=$p.file
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:mesg', (('vertex.link', 'visi'), ('vertex.link', 'vertexmc'), 0)))
            self.eq(node.get('to'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('from'), ('vertex.link', 'visi'))
            self.eq(node.get('time'), 0)
            self.eq(node.get('url'), 'https://vertex.link/messages/0')
            self.eq(node.get('client'), 'tcp://1.2.3.4')
            self.eq(node.get('client:ipv4'), 0x01020304)
            self.eq(node.get('deleted'), True)
            self.eq(node.get('text'), 'a cool Message')
            self.eq(node.get('file'), file0)

            q = '[inet:web:mesg=(vertex.link/visi, vertex.link/epiphyte, (0)) :client="tcp://::1"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:mesg', (('vertex.link', 'visi'), ('vertex.link', 'epiphyte'), 0)))
            self.eq(node.get('client'), 'tcp://::1')
            self.eq(node.get('client:ipv6'), '::1')

    async def test_web_post(self):
        async with self.getTestCore() as core:
            valu = 32 * 'a'
            place = s_common.guid()
            props = {
                'acct': ('vertex.link', 'vertexmc'),
                'text': 'my cooL POST',
                'time': 0,
                'deleted': True,
                'url': 'https://vertex.link/mypost',
                'client': 'tcp://1.2.3.4',
                'file': 64 * 'f',
                'replyto': 32 * 'b',
                'repost': 32 * 'c',

                'hashtags': '#foo,#bar,#foo',
                'mentions:users': 'vertex.link/visi,vertex.link/whippit',
                'mentions:groups': 'vertex.link/ninjas',

                'loc': 'ru',
                'place': place,
                'latlong': (20, 30),
            }
            q = '''[(inet:web:post=$valu :acct=$p.acct :text=$p.text :time=$p.time :deleted=$p.deleted :url=$p.url
                :client=$p.client :file=$p.file :replyto=$p.replyto :repost=$p.repost :hashtags=$p.hashtags
                :mentions:users=$p."mentions:users" :mentions:groups=$p."mentions:groups"
                :loc=$p.loc :place=$p.place :latlong=$p.latlong)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:post', valu))
            self.eq(node.get('acct'), ('vertex.link', 'vertexmc'))
            self.eq(node.get('acct:site'), 'vertex.link')
            self.eq(node.get('acct:user'), 'vertexmc')
            self.eq(node.get('client'), 'tcp://1.2.3.4')
            self.eq(node.get('client:ipv4'), 0x01020304)
            self.eq(node.get('text'), 'my cooL POST')
            self.eq(node.get('time'), 0)
            self.eq(node.get('deleted'), True)
            self.eq(node.get('url'), 'https://vertex.link/mypost')
            self.eq(node.get('file'), 'sha256:' + 64 * 'f')
            self.eq(node.get('replyto'), 32 * 'b')
            self.eq(node.get('repost'), 32 * 'c')
            self.eq(node.get('hashtags'), ('#bar', '#foo'))
            self.eq(node.get('mentions:users'), (('vertex.link', 'visi'), ('vertex.link', 'whippit')))
            self.eq(node.get('mentions:groups'), (('vertex.link', 'ninjas'),))
            self.eq(node.get('loc'), 'ru')
            self.eq(node.get('latlong'), (20.0, 30.0))

            valu = s_common.guid()
            nodes = await core.nodes('[(inet:web:post=$valu :client="::1")]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:web:post', valu))
            self.eq(node.get('client'), 'tcp://::1')
            self.eq(node.get('client:ipv6'), '::1')
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))
            self.len(1, await core.nodes('inet:group=ninjas'))

            nodes = await core.nodes('[ inet:web:post:link=* :post={inet:web:post | limit 1} :url=https://vtx.lk :text=Vertex ]')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('post'))
            self.eq(node.get('url'), 'https://vtx.lk')
            self.eq(node.get('text'), 'Vertex')

    async def test_whois_contact(self):
        async with self.getTestCore() as core:
            valu = (('vertex.link', '@2015'), 'regiStrar')
            props = {
                'id': 'ID',
                'name': 'NAME',
                'email': 'unittest@vertex.link',
                'orgname': 'unittest org',
                'address': '1234 Not Real Road',
                'city': 'Faketown',
                'state': 'Stateland',
                'country': 'US',
                'phone': '555-555-5555',
                'fax': '555-555-5556',
                'url': 'https://vertex.link/contact',
                'whois:fqdn': 'vertex.link'
            }
            q = '''[(inet:whois:contact=$valu :id=$p.id :name=$p.name :email=$p.email :orgname=$p.orgname
                            :address=$p.address :city=$p.city :state=$p.state :country=$p.country :phone=$p.phone :fax=$p.fax
                            :url=$p.url :whois:fqdn=$p."whois:fqdn")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:contact', (('vertex.link', 1420070400000), 'registrar')))
            self.eq(node.get('rec'), ('vertex.link', 1420070400000))
            self.eq(node.get('rec:asof'), 1420070400000)
            self.eq(node.get('rec:fqdn'), 'vertex.link')
            self.eq(node.get('type'), 'registrar')
            self.eq(node.get('id'), 'id')
            self.eq(node.get('name'), 'name')
            self.eq(node.get('email'), 'unittest@vertex.link')
            self.eq(node.get('orgname'), 'unittest org')
            self.eq(node.get('address'), '1234 not real road')
            self.eq(node.get('city'), 'faketown')
            self.eq(node.get('state'), 'stateland')
            self.eq(node.get('country'), 'us')
            self.eq(node.get('phone'), '5555555555')
            self.eq(node.get('fax'), '5555555556')
            self.eq(node.get('url'), 'https://vertex.link/contact')
            self.eq(node.get('whois:fqdn'), 'vertex.link')
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))

    async def test_whois_collection(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:whois:rar="cool Registrar "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:rar', 'cool registrar '))

            nodes = await core.nodes('[inet:whois:reg="cool Registrant "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:reg', 'cool registrant '))

            nodes = await core.nodes('[inet:whois:recns=(ns1.woot.com, (woot.com, "@20501217"))]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:recns', ('ns1.woot.com', ('woot.com', 2554848000000))))
            self.eq(node.get('ns'), 'ns1.woot.com')
            self.eq(node.get('rec'), ('woot.com', 2554848000000))
            self.eq(node.get('rec:fqdn'), 'woot.com')
            self.eq(node.get('rec:asof'), 2554848000000)

            valu = s_common.guid()
            rec = s_common.guid()
            props = {
                'time': 2554869000000,
                'fqdn': 'arin.whois.net',
                'ipv4': 167772160,
                'success': True,
                'rec': rec,
            }
            q = '[(inet:whois:ipquery=$valu :time=$p.time :fqdn=$p.fqdn :success=$p.success :rec=$p.rec :ipv4=$p.ipv4)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:ipquery', valu))
            self.eq(node.get('time'), 2554869000000)
            self.eq(node.get('fqdn'), 'arin.whois.net')
            self.eq(node.get('success'), True)
            self.eq(node.get('rec'), rec)
            self.eq(node.get('ipv4'), 167772160)

            valu = s_common.guid()
            props = {
                'time': 2554869000000,
                'url': 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff',
                'ipv6': '3300:100:1::ffff',
                'success': False,
            }
            q = '[(inet:whois:ipquery=$valu :time=$p.time :url=$p.url :success=$p.success :ipv6=$p.ipv6)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:ipquery', valu))
            self.eq(node.get('time'), 2554869000000)
            self.eq(node.get('url'), 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff')
            self.eq(node.get('success'), False)
            self.none(node.get('rec'))
            self.eq(node.get('ipv6'), '3300:100:1::ffff')

            contact = s_common.guid()
            pscontact = s_common.guid()
            subcontact = s_common.guid()
            props = {
                'contact': pscontact,
                'asof': 2554869000000,
                'created': 2554858000000,
                'updated': 2554858000000,
                'role': 'registrant',
                'roles': ('abuse', 'administrative', 'technical'),
                'asn': 123456,
                'id': 'SPM-3',
                'links': ('http://myrdap.com/SPM3',),
                'status': 'active',
                'contacts': (subcontact,),
            }
            q = '''[(inet:whois:ipcontact=$valu :contact=$p.contact
            :asof=$p.asof :created=$p.created :updated=$p.updated :role=$p.role :roles=$p.roles
            :asn=$p.asn :id=$p.id :links=$p.links :status=$p.status :contacts=$p.contacts)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': contact, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:ipcontact', contact))
            self.eq(node.get('contact'), pscontact)
            self.eq(node.get('contacts'), (subcontact,))
            self.eq(node.get('asof'), 2554869000000)
            self.eq(node.get('created'), 2554858000000)
            self.eq(node.get('updated'), 2554858000000)
            self.eq(node.get('role'), 'registrant')
            self.eq(node.get('roles'), ('abuse', 'administrative', 'technical'))
            self.eq(node.get('asn'), 123456)
            self.eq(node.get('id'), 'SPM-3')
            self.eq(node.get('links'), ('http://myrdap.com/SPM3',))
            self.eq(node.get('status'), 'active')
            #  check regid pivot
            valu = s_common.guid()
            nodes = await core.nodes('[inet:whois:iprec=$valu :id=$id]',
                                     opts={'vars': {'valu': valu, 'id': props.get('id')}})
            self.len(1, nodes)
            nodes = await core.nodes('inet:whois:ipcontact=$valu :id -> inet:whois:iprec:id',
                                     opts={'vars': {'valu': contact}})
            self.len(1, nodes)

    async def test_whois_rec(self):

        async with self.getTestCore() as core:
            valu = ('woot.com', '@20501217')
            props = {
                'text': 'YELLING AT pennywise@vertex.link LOUDLY',
                'registrar': ' cool REGISTRAR ',
                'registrant': ' cool REGISTRANT ',
            }
            q = '[(inet:whois:rec=$valu :text=$p.text :registrar=$p.registrar :registrant=$p.registrant)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:rec', ('woot.com', 2554848000000)))
            self.eq(node.get('fqdn'), 'woot.com')
            self.eq(node.get('asof'), 2554848000000)
            self.eq(node.get('text'), 'yelling at pennywise@vertex.link loudly')
            self.eq(node.get('registrar'), ' cool registrar ')
            self.eq(node.get('registrant'), ' cool registrant ')

            nodes = await core.nodes('inet:whois:email')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:whois:email', ('woot.com', 'pennywise@vertex.link')))

            q = '''
            [inet:whois:rec=(wellsfargo.com, 2019/11/24 03:30:07.000)
                :created="1993/02/19 05:00:00.000"]
            +inet:whois:rec:created < 2017/01/01
            '''
            self.len(1, await core.nodes(q))

    async def test_whois_iprec(self):
        async with self.getTestCore() as core:
            contact = s_common.guid()
            addlcontact = s_common.guid()
            rec_ipv4 = s_common.guid()
            props = {
                'net4': '10.0.0.0/28',
                'asof': 2554869000000,
                'created': 2554858000000,
                'updated': 2554858000000,
                'text': 'this is  a bunch of \nrecord text 123123',
                'desc': 'these are some notes\n about record 123123',
                'asn': 12345,
                'id': 'NET-10-0-0-0-1',
                'name': 'vtx',
                'parentid': 'NET-10-0-0-0-0',
                'registrant': contact,
                'contacts': (addlcontact, ),
                'country': 'US',
                'status': 'validated',
                'type': 'direct allocation',
                'links': ('http://rdap.com/foo', 'http://rdap.net/bar'),
            }
            q = '''[(inet:whois:iprec=$valu :net4=$p.net4 :asof=$p.asof :created=$p.created :updated=$p.updated
                :text=$p.text :desc=$p.desc :asn=$p.asn :id=$p.id :name=$p.name :parentid=$p.parentid
                :registrant=$p.registrant :contacts=$p.contacts :country=$p.country :status=$p.status :type=$p.type
                :links=$p.links)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': rec_ipv4, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:iprec', rec_ipv4))
            self.eq(node.get('net4'), (167772160, 167772175))
            self.eq(node.get('net4:min'), 167772160)
            self.eq(node.get('net4:max'), 167772175)
            self.eq(node.get('asof'), 2554869000000)
            self.eq(node.get('created'), 2554858000000)
            self.eq(node.get('updated'), 2554858000000)
            self.eq(node.get('text'), 'this is  a bunch of \nrecord text 123123')
            self.eq(node.get('desc'), 'these are some notes\n about record 123123')
            self.eq(node.get('asn'), 12345)
            self.eq(node.get('id'), 'NET-10-0-0-0-1')
            self.eq(node.get('name'), 'vtx')
            self.eq(node.get('parentid'), 'NET-10-0-0-0-0')
            self.eq(node.get('registrant'), contact)
            self.eq(node.get('contacts'), (addlcontact,))
            self.eq(node.get('country'), 'us')
            self.eq(node.get('status'), 'validated')
            self.eq(node.get('type'), 'direct allocation')
            self.eq(node.get('links'), ('http://rdap.com/foo', 'http://rdap.net/bar'))

            rec_ipv6 = s_common.guid()
            props = {
                'net6': '2001:db8::/101',
                'asof': 2554869000000,
                'created': 2554858000000,
                'updated': 2554858000000,
                'text': 'this is  a bunch of \nrecord text 123123',
                'asn': 12345,
                'id': 'NET-10-0-0-0-0',
                'name': 'EU-VTX-1',
                'registrant': contact,
                'country': 'tp',
                'status': 'renew prohibited',
                'type': 'allocated-BY-rir',
            }

            q = '''[(inet:whois:iprec=$valu :net6=$p.net6 :asof=$p.asof :created=$p.created :updated=$p.updated
                :text=$p.text :asn=$p.asn :id=$p.id :name=$p.name
                :registrant=$p.registrant :country=$p.country :status=$p.status :type=$p.type)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': rec_ipv6, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:whois:iprec', rec_ipv6))
            self.eq(node.get('net6'), ('2001:db8::', '2001:db8::7ff:ffff'))
            self.eq(node.get('net6:min'), '2001:db8::')
            self.eq(node.get('net6:max'), '2001:db8::7ff:ffff')
            self.eq(node.get('asof'), 2554869000000)
            self.eq(node.get('created'), 2554858000000)
            self.eq(node.get('updated'), 2554858000000)
            self.eq(node.get('text'), 'this is  a bunch of \nrecord text 123123')
            self.eq(node.get('asn'), 12345)
            self.eq(node.get('id'), 'NET-10-0-0-0-0')
            self.eq(node.get('name'), 'EU-VTX-1')
            self.eq(node.get('registrant'), contact)
            self.eq(node.get('country'), 'tp')
            self.eq(node.get('status'), 'renew prohibited')
            self.eq(node.get('type'), 'allocated-by-rir')

            # check regid pivot
            scmd = f'inet:whois:iprec={rec_ipv4} :parentid -> inet:whois:iprec:id'
            nodes = await core.nodes(scmd)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:whois:iprec', rec_ipv6))

            # bad country code
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[(inet:whois:iprec=* :country=u9)]')

    async def test_wifi_collection(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:wifi:ssid="The Best SSID"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:wifi:ssid', "The Best SSID"))

            valu = ('The Best SSID2 ', '00:11:22:33:44:55')
            place = s_common.guid()
            props = {
                'accuracy': '10km',
                'latlong': (20, 30),
                'place': place,
                'channel': 99,
                'encryption': 'wpa2',
            }
            q = '''[(inet:wifi:ap=$valu :place=$p.place :channel=$p.channel :latlong=$p.latlong :accuracy=$p.accuracy
                    :encryption=$p.encryption)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('inet:wifi:ap', valu))
            self.eq(node.get('ssid'), valu[0])
            self.eq(node.get('bssid'), valu[1])
            self.eq(node.get('latlong'), (20.0, 30.0))
            self.eq(node.get('accuracy'), 10000000)
            self.eq(node.get('place'), place)
            self.eq(node.get('channel'), 99)
            self.eq(node.get('encryption'), 'wpa2')

    async def test_banner(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[inet:banner=("tcp://1.2.3.4:443", "Hi There")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('text'), 'Hi There')
            self.eq(node.get('server:port'), 443)
            self.eq(node.get('server:ipv4'), 0x01020304)

            self.len(1, await core.nodes('it:dev:str="Hi There"'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

            nodes = await core.nodes('[inet:banner=("tcp://::ffff:8.7.6.5", sup)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('text'), 'sup')
            self.none(node.get('server:port'))
            self.eq(node.get('server:ipv6'), '::ffff:8.7.6.5')

    async def test_search_query(self):
        async with self.getTestCore() as core:
            iden = s_common.guid()
            host = s_common.guid()
            props = {
                'time': 200,
                'text': 'hi there',
                'engine': 'roofroof',
                'host': host,
                'acct': 'vertex.link/visi',
            }

            q = '''[
                inet:search:query=$valu
                    :time=$p.time
                    :text=$p.text
                    :engine=$p.engine
                    :acct=$p.acct
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
            self.eq(node.get('acct'), ('vertex.link', 'visi'))
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
                :received:from:ipv4=1.2.3.4
                :received:from:ipv6="::1"
                :received:from:fqdn=smtp.vertex.link
                :flow=$flow
            ]

            {[( inet:email:message:link=($node, https://www.vertex.link) :text=Vertex )]}
            {[( inet:email:message:attachment=($node, "*") :name=sploit.exe )]}
            '''
            nodes = await core.nodes(q, opts={'vars': {'flow': flow}})
            self.len(1, nodes)

            self.eq(nodes[0].get('id'), 'Woot-12345')
            self.eq(nodes[0].get('cc'), ('baz@faz.org', 'foo@bar.com'))
            self.eq(nodes[0].get('received:from:ipv6'), '::1')
            self.eq(nodes[0].get('received:from:ipv4'), 0x01020304)
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

    async def test_model_inet_tunnel(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
            [ inet:tunnel=*
                :ingress=1.2.3.4:443
                :egress=5.5.5.5
                :type=vpn
                :anon=$lib.true
                :operator = {[ ps:contact=* :email=visi@vertex.link ]}
            ]''')
            self.len(1, nodes)

            self.eq(True, nodes[0].get('anon'))
            self.eq('vpn.', nodes[0].get('type'))
            self.eq('tcp://5.5.5.5', nodes[0].get('egress'))
            self.eq('tcp://1.2.3.4:443', nodes[0].get('ingress'))

            self.len(1, await core.nodes('inet:tunnel -> ps:contact +:email=visi@vertex.link'))

    async def test_model_inet_proto(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:proto=https :port=443 ]')
            self.len(1, nodes)
            self.eq(('inet:proto', 'https'), nodes[0].ndef)
            self.eq(443, nodes[0].get('port'))

    async def test_model_inet_web_attachment(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
            [ inet:web:attachment=*
                :acct=twitter.com/invisig0th
                :client=tcp://1.2.3.4
                :file=*
                :name=beacon.exe
                :time=20230202
                :post=*
                :mesg=(twitter.com/invisig0th, twitter.com/vtxproject, 20230202)
            ]''')
            self.len(1, nodes)
            self.eq(1675296000000, nodes[0].get('time'))
            self.eq('beacon.exe', nodes[0].get('name'))
            self.eq('tcp://1.2.3.4', nodes[0].get('client'))
            self.eq(0x01020304, nodes[0].get('client:ipv4'))

            self.nn(nodes[0].get('post'))
            self.nn(nodes[0].get('mesg'))
            self.nn(nodes[0].get('file'))

            self.len(1, await core.nodes('inet:web:attachment :file -> file:bytes'))
            self.len(1, await core.nodes('inet:web:attachment :post -> inet:web:post'))
            self.len(1, await core.nodes('inet:web:attachment :mesg -> inet:web:mesg'))

    async def test_model_inet_egress(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
            [ inet:egress=*
                :host = *
                :host:iface = *
                :client=1.2.3.4
                :client:ipv6="::1"
            ]
            ''')

            self.len(1, nodes)
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('host:iface'))
            self.eq(nodes[0].get('client'), 'tcp://1.2.3.4')
            self.eq(nodes[0].get('client:ipv4'), 0x01020304)
            self.eq(nodes[0].get('client:ipv6'), '::1')

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
                        :server:fingerprint:ja3=$ja3s
                        :client=$client
                        :client:cert=*
                        :client:fingerprint:ja3=$ja3
                ]
            ''', opts={'vars': props})
            self.len(1, nodes)
            self.nn(nodes[0].get('time'))
            self.nn(nodes[0].get('flow'))
            self.nn(nodes[0].get('server:cert'))
            self.nn(nodes[0].get('client:cert'))

            self.eq(props['ja3'], nodes[0].get('client:fingerprint:ja3'))
            self.eq(props['ja3s'], nodes[0].get('server:fingerprint:ja3'))

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
                :name=Slack
                :provider={ ou:org:name=$provname }
                :provider:name=$provname
            ]
            '''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:service:platform', s_common.guid(('slack',))))
            self.eq(nodes[0].get('url'), 'https://slack.com')
            self.eq(nodes[0].get('name'), 'slack')
            self.eq(nodes[0].get('provider'), provider.ndef[1])
            self.eq(nodes[0].get('provider:name'), provname.lower())
            platform = nodes[0]

            q = '''
            [ inet:service:instance=(vertex, slack)
                :id='T2XK1223Y'
                :platform={ inet:service:platform=(slack,) }
                :url="https://v.vtx.lk/slack"
                :name="Synapse users slack"
                :tenant={[ inet:service:tenant=({"id": "VS-31337"}) ]}
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].get('tenant'))
            self.eq(nodes[0].ndef, ('inet:service:instance', s_common.guid(('vertex', 'slack'))))
            self.eq(nodes[0].get('id'), 'T2XK1223Y')
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('url'), 'https://v.vtx.lk/slack')
            self.eq(nodes[0].get('name'), 'synapse users slack')
            platinst = nodes[0]

            q = '''
            [
                (inet:service:account=(blackout, account, vertex, slack)
                    :id=U7RN51U1J
                    :user=blackout
                    :url=https://vertex.link/users/blackout
                    :email=blackout@vertex.link
                    :profile={ gen.ps.contact.email vertex.employee blackout@vertex.link }
                    :tenant={[ inet:service:tenant=({"id": "VS-31337"}) ]}
                )

                (inet:service:account=(visi, account, vertex, slack)
                    :id=U2XK7PUVB
                    :user=visi
                    :email=visi@vertex.link
                    :profile={ gen.ps.contact.email vertex.employee visi@vertex.link }
                )
            ]
            '''
            accounts = await core.nodes(q)
            self.len(2, accounts)

            self.nn(accounts[0].get('tenant'))

            profiles = await core.nodes('ps:contact')
            self.len(2, profiles)
            self.eq(profiles[0].get('email'), 'blackout@vertex.link')
            self.eq(profiles[1].get('email'), 'visi@vertex.link')
            blckprof, visiprof = profiles

            self.eq(accounts[0].ndef, ('inet:service:account', s_common.guid(('blackout', 'account', 'vertex', 'slack'))))
            self.eq(accounts[0].get('id'), 'U7RN51U1J')
            self.eq(accounts[0].get('user'), 'blackout')
            self.eq(accounts[0].get('url'), 'https://vertex.link/users/blackout')
            self.eq(accounts[0].get('email'), 'blackout@vertex.link')
            self.eq(accounts[0].get('profile'), blckprof.ndef[1])

            self.eq(accounts[1].ndef, ('inet:service:account', s_common.guid(('visi', 'account', 'vertex', 'slack'))))
            self.eq(accounts[1].get('id'), 'U2XK7PUVB')
            self.eq(accounts[1].get('user'), 'visi')
            self.eq(accounts[1].get('email'), 'visi@vertex.link')
            self.eq(accounts[1].get('profile'), visiprof.ndef[1])
            blckacct, visiacct = accounts

            q = '''
            [ inet:service:group=(developers, group, vertex, slack)
                :id=X1234
                :name="developers, developers, developers"
                :profile={ gen.ps.contact.email vertex.slack.group developers@vertex.slack.com }
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            profiles = await core.nodes('ps:contact:email=developers@vertex.slack.com')
            self.len(1, profiles)
            devsprof = profiles[0]

            self.eq(nodes[0].get('id'), 'X1234')
            self.eq(nodes[0].get('name'), 'developers, developers, developers')
            self.eq(nodes[0].get('profile'), devsprof.ndef[1])
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
            self.eq(nodes[0].get('period'), (1685577600000, 9223372036854775807))
            self.eq(nodes[0].get('creator'), visiacct.ndef[1])
            self.eq(nodes[0].get('remover'), visiacct.ndef[1])

            self.eq(nodes[1].get('account'), visiacct.ndef[1])
            self.eq(nodes[1].get('group'), devsgrp.ndef[1])
            self.eq(nodes[1].get('period'), (1420070400000, 9223372036854775807))
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
            self.eq(nodes[0].get('period'), (1715850000000, 1715856900000))
            blcksess = nodes[0]
            self.len(1, await core.nodes('inet:service:session -> inet:http:session'))

            q = '''
            [ inet:service:login=*
                :method=password
                :session=$blcksess
                :server=tcp://10.10.10.4:443
                :client=tcp://192.168.0.10:12345
            ]
            '''
            opts = {'vars': {'blcksess': blcksess.ndef[1]}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('method'), 'password.')

            server = await core.nodes('inet:server=tcp://10.10.10.4:443')
            self.len(1, server)
            server = server[0]

            client = await core.nodes('inet:client=tcp://192.168.0.10:12345')
            self.len(1, client)
            client = client[0]

            self.eq(nodes[0].get('server'), server.ndef[1])
            self.eq(nodes[0].get('client'), client.ndef[1])

            q = '''
            [ inet:service:message:link=(blackout, developers, 1715856900000, https://www.youtube.com/watch?v=dQw4w9WgXcQ, vertex, slack)
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
            self.eq(nodes[0].get('name'), 'general')
            self.eq(nodes[0].get('period'), (1420070400000, 9223372036854775807))
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
            self.eq(nodes[0].get('period'), (1420070400000, 9223372036854775807))
            self.eq(nodes[0].get('channel'), gnrlchan.ndef[1])

            self.eq(nodes[1].ndef, ('inet:service:channel:member', s_common.guid(('blackout', 'general', 'channel', 'vertex', 'slack'))))
            self.eq(nodes[1].get('account'), blckacct.ndef[1])
            self.eq(nodes[1].get('period'), (1685577600000, 9223372036854775807))
            self.eq(nodes[1].get('channel'), gnrlchan.ndef[1])

            for node in nodes:
                self.eq(node.get('platform'), platform.ndef[1])
                self.eq(node.get('instance'), platinst.ndef[1])
                self.eq(node.get('channel'), gnrlchan.ndef[1])

            q = '''
            [ inet:service:message:attachment=(pbjtime.gif, blackout, developers, 1715856900000, vertex, slack)
                :file={[ file:bytes=sha256:028241d9116a02059e99cb239c66d966e1b550926575ad7dcf0a8f076a352bcd ]}
                :name=pbjtime.gif
                :text="peanut butter jelly time"
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].get('file'), 'sha256:028241d9116a02059e99cb239c66d966e1b550926575ad7dcf0a8f076a352bcd')
            self.eq(nodes[0].get('name'), 'pbjtime.gif')
            self.eq(nodes[0].get('text'), 'peanut butter jelly time')
            attachment = nodes[0]

            q = '''
            [
                (inet:service:message=(blackout, developers, 1715856900000, vertex, slack)
                    :type=chat.group
                    :group=$devsiden
                    :public=$lib.false
                    :repost=*
                )

                (inet:service:message=(blackout, visi, 1715856900000, vertex, slack)
                    :type=chat.direct
                    :to=$visiiden
                    :public=$lib.false
                )

                (inet:service:message=(blackout, general, 1715856900000, vertex, slack)
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

                :client:software = {[ it:prod:softver=* :name=woot ]}
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

            self.eq(nodes[1].get('to'), visiacct.ndef[1])
            self.false(nodes[1].get('public'))
            self.eq(nodes[1].get('type'), 'chat.direct.')

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
            self.eq(nodes[0].ndef, ('inet:service:message', 'c0d64c559e2f42d57b37b558458c068b'))
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
            [ inet:service:access=(api, blackout, 1715856900000, vertex, slack)
                :account=$blckiden
                :instance=$instiden
                :platform=$platiden
                :resource=$rsrciden
                :success=$lib.true
                :time=(1715856900000)
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
            self.eq(nodes[0].get('account'), blckacct.ndef[1])
            self.eq(nodes[0].get('instance'), platinst.ndef[1])
            self.eq(nodes[0].get('platform'), platform.ndef[1])
            self.eq(nodes[0].get('resource'), resource.ndef[1])
            self.true(nodes[0].get('success'))
            self.eq(nodes[0].get('time'), 1715856900000)

            q = '''
            [ inet:service:message=(visi, says, relax)
                :title="Hehe Haha"
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
                    :pay:instrument={[ econ:bank:account=* :contact={[ ps:contact=* :name=visi]} ]}
                    :subscriber={[ inet:service:tenant=({"id": "VS-31337"}) ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq('vertex.synapse.enterprise.', nodes[0].get('level'))
            self.eq('econ:bank:account', nodes[0].get('pay:instrument')[0])
            self.eq('inet:service:tenant', nodes[0].get('subscriber')[0])
            self.len(1, await core.nodes('inet:service:subscription -> inet:service:subscription:level:taxonomy'))
            self.len(1, await core.nodes('inet:service:subscription :pay:instrument -> econ:bank:account'))
            self.len(1, await core.nodes('inet:service:subscription :subscriber -> inet:service:tenant'))
