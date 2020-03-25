import copy
import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

logger = logging.getLogger(__name__)

class InetModelTest(s_t_utils.SynTest):

    async def test_ipv4_lift_range(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('inet:ipv4', '1.2.3.0')
                await snap.addNode('inet:ipv4', '1.2.3.1')
                await snap.addNode('inet:ipv4', '1.2.3.2')
                await snap.addNode('inet:ipv4', '1.2.3.3')
                await snap.addNode('inet:ipv4', '1.2.3.4')

            await self.agenlen(3, core.eval('inet:ipv4=1.2.3.1-1.2.3.3'))
            await self.agenlen(3, core.eval('[inet:ipv4=1.2.3.1-1.2.3.3]'))
            await self.agenlen(3, core.eval('inet:ipv4 +inet:ipv4=1.2.3.1-1.2.3.3'))
            await self.agenlen(3, core.eval('inet:ipv4*range=(1.2.3.1, 1.2.3.3)'))

    async def test_ipv4_filt_cidr(self):

        async with self.getTestCore() as core:

            await self.agenlen(5, core.eval('[ inet:ipv4=1.2.3.0/30 inet:ipv4=5.5.5.5 ]'))
            await self.agenlen(4, core.eval('inet:ipv4 +inet:ipv4=1.2.3.0/30'))
            await self.agenlen(1, core.eval('inet:ipv4 -inet:ipv4=1.2.3.0/30'))

            await self.agenlen(256, core.eval('[ inet:ipv4=192.168.1.0/24]'))
            await self.agenlen(256, core.eval('[ inet:ipv4=192.168.2.0/24]'))
            await self.agenlen(256, core.eval('inet:ipv4=192.168.1.0/24'))

            # Seed some nodes for bounds checking
            pnodes = [(('inet:ipv4', f'10.2.1.{d}'), {}) for d in range(1, 33)]
            nodes = await alist(core.addNodes(pnodes))

            nodes = await alist(core.eval('inet:ipv4=10.2.1.4/32'))
            self.len(1, nodes)
            await self.agenlen(1, core.eval('inet:ipv4 +inet:ipv4=10.2.1.4/32'))

            nodes = await alist(core.eval('inet:ipv4=10.2.1.4/31'))
            self.len(2, nodes)
            await self.agenlen(2, core.eval('inet:ipv4 +inet:ipv4=10.2.1.4/31'))

            # 10.2.1.1/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await alist(core.eval('inet:ipv4=10.2.1.1/30'))
            self.len(3, nodes)

            # 10.2.1.2/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = await alist(core.eval('inet:ipv4=10.2.1.2/30'))
            self.len(3, nodes)

            # 10.2.1.1/29 is 10.2.1.0 -> 10.2.1.7 but we don't have 10.2.1.0 in the core
            nodes = await alist(core.eval('inet:ipv4=10.2.1.1/29'))
            self.len(7, nodes)

            # 10.2.1.8/29 is 10.2.1.8 -> 10.2.1.15
            nodes = await alist(core.eval('inet:ipv4=10.2.1.8/29'))
            self.len(8, nodes)

            # 10.2.1.1/28 is 10.2.1.0 -> 10.2.1.15 but we don't have 10.2.1.0 in the core
            nodes = await alist(core.eval('inet:ipv4=10.2.1.1/28'))
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

    async def test_asn(self):
        formname = 'inet:asn'
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                valu = '123'
                expected_ndef = (formname, 123)
                input_props = {
                    'name': 'COOL',
                    'owner': 32 * 'a'
                }
                expected_props = {
                    'name': 'cool',
                    'owner': 32 * 'a',
                }
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                valu = '456'
                expected_ndef = (formname, 456)
                expected_props = {}
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_asnet4(self):
        formname = 'inet:asnet4'
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                valu = ('54959', ('1.2.3.4', '5.6.7.8'))
                expected_ndef = (formname, (54959, (16909060, 84281096)))
                expected_props = {
                    'net4:min': 16909060,
                    'net4': (16909060, 84281096),
                    'net4:max': 84281096,
                    'asn': 54959,
                }
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

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

            # Form Tests ======================================================
            valu = '192[.]168.1.123/24'
            expected_ndef = (formname, '192.168.1.0/24')  # ndef is network/mask, not ip/mask

            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
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
        formname = 'inet:client'
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
            async with await core.snap() as snap:
                for valu, expected_valu, expected_props in data:
                    node = await snap.addNode(formname, valu)
                    self.checkNode(node, ((formname, expected_valu), expected_props))

    async def test_download(self):
        formname = 'inet:download'
        input_props = {
            'time': 0,
            'file': 64 * 'b',
            'fqdn': 'vertex.link',
            'client': 'tcp://127.0.0.1:45654',
            'server': 'tcp://1.2.3.4:80'
        }
        expected_props = {
            'time': 0,
            'file': 'sha256:' + 64 * 'b',
            'fqdn': 'vertex.link',
            'client': 'tcp://127.0.0.1:45654',
            'client:ipv4': 2130706433,
            'client:port': 45654,
            'client:proto': 'tcp',
            'server': 'tcp://1.2.3.4:80',
            'server:ipv4': 16909060,
            'server:port': 80,
            'server:proto': 'tcp',
        }
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, ((formname, 32 * 'a'), expected_props))

    async def test_email(self):
        formname = 'inet:email'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {'fqdn': 'vertex.link', 'user': 'unittest'}})
            self.eq(t.norm(email), expected)

            valu = t.norm('bob\udcfesmith@woot.com')[0]

            # Form Tests ======================================================
            valu = 'UnitTest@Vertex.link'
            expected_ndef = (formname, valu.lower())
            expected_props = {
                'fqdn': 'vertex.link',
                'user': 'unittest',
            }
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_flow(self):
        formname = 'inet:flow'
        input_props = {
            'time': 0,
            'duration': 1,
            'from': 32 * 'b',
            'src': 'tcp://127.0.0.1:45654',
            'src:host': 32 * 'b',
            'src:proc': 32 * 'c',
            'src:exe': 64 * 'd',
            'src:txbytes': 1,
            'dst': 'tcp://1.2.3.4:80',
            'dst:host': 32 * 'e',
            'dst:proc': 32 * 'f',
            'dst:exe': 64 * '0',
            'dst:txbytes': 2
        }
        expected_props = {
            'time': 0,
            'duration': 1,
            'from': 32 * 'b',
            'src': 'tcp://127.0.0.1:45654',
            'src:port': 45654,
            'src:proto': 'tcp',
            'src:ipv4': 2130706433,
            'src:host': 32 * 'b',
            'src:proc': 32 * 'c',
            'src:exe': 'sha256:' + 64 * 'd',
            'src:txbytes': 1,
            'dst': 'tcp://1.2.3.4:80',
            'dst:port': 80,
            'dst:proto': 'tcp',
            'dst:ipv4': 16909060,
            'dst:host': 32 * 'e',
            'dst:proc': 32 * 'f',
            'dst:exe': 'sha256:' + 64 * '0',
            'dst:txbytes': 2
        }
        expected_ndef = (formname, 32 * 'a')
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

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

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'link'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(fqdn, t.repr(fqdn))  # UnicodeError raised and caught and fallback to norm

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com')

            # IP addresses are NOT valid FQDNs
            self.raises(s_exc.BadTypeValu, t.norm, '1.2.3.4')

            # Form Tests ======================================================
            valu = 'api.vertex.link'
            expected_ndef = (formname, valu)

            # Demonstrate cascading formation
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'vertex.link')
                self.eq(node.get('host'), 'api')
                #self.eq(node.get('issuffix'), 0)
                #self.eq(node.get('iszone'), 0)
                self.eq(node.get('zone'), 'vertex.link')

            async with await core.snap() as snap:
                nvalu = 'vertex.link'
                expected_ndef = (formname, nvalu)
                node = await snap.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'link')
                self.eq(node.get('host'), 'vertex')
                self.eq(node.get('issuffix'), 0)
                self.eq(node.get('iszone'), 1)
                self.eq(node.get('zone'), 'vertex.link')

            async with await core.snap() as snap:
                nvalu = 'link'
                expected_ndef = (formname, nvalu)
                node = await snap.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('host'), 'link')
                self.eq(node.get('issuffix'), 1)
                self.eq(node.get('iszone'), 0)

            # Demonstrate wildcard
            async with await core.snap() as snap:
                self.len(3, await snap.nodes('inet:fqdn="*"'))
                self.len(3, await snap.nodes('inet:fqdn="*link"'))
                self.len(2, await snap.nodes('inet:fqdn="*.link"'))
                self.len(1, await snap.nodes('inet:fqdn="*.vertex.link"'))
                with self.raises(s_exc.BadLiftValu):
                    await snap.nodes('inet:fqdn=api.*.link')

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
            async with await core.snap() as snap:

                # Create some nodes and demonstrate zone/suffix behavior
                # Only FQDNs of the lowest level should be suffix
                # Only FQDNs whose domains are suffixes should be zones
                n0 = await snap.addNode(formname, 'abc.vertex.link')
                n1 = await snap.addNode(formname, 'def.vertex.link')
                n2 = await snap.addNode(formname, 'g.def.vertex.link')
                # form again to show g. should not make this a zone
                n1 = await snap.addNode(formname, 'def.vertex.link')
                n3 = await snap.getNodeByNdef((formname, 'vertex.link'))
                n4 = await snap.getNodeByNdef((formname, 'link'))
                isneither(n0)
                isneither(n1)
                isneither(n2)
                iszone(n3)     # vertex.link should be a zone
                issuffix(n4)   # link should be a suffix

                # Make one of the FQDNs a suffix and make sure its children become zones
                n3 = await snap.addNode(formname, 'vertex.link', props={'issuffix': True})
                isboth(n3)     # vertex.link should now be both because we made it a suffix
                n0 = await snap.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = await snap.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = await snap.getNodeByNdef((formname, 'g.def.vertex.link'))
                iszone(n0)     # now a zone because vertex.link is a suffix
                iszone(n1)     # now a zone because vertex.link is a suffix
                isneither(n2)  # still neither as parent is not a suffix

                # Remove the FQDN's suffix status and make sure its children lose zone status
                n3 = await snap.addNode(formname, 'vertex.link', props={'issuffix': False})
                iszone(n3)     # vertex.link should now be a zone because we removed its suffix status
                n0 = await snap.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = await snap.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = await snap.getNodeByNdef((formname, 'g.def.vertex.link'))
                n4 = await snap.getNodeByNdef((formname, 'link'))
                isneither(n0)  # loses zone status
                isneither(n1)  # loses zone status
                isneither(n2)  # stays the same
                issuffix(n4)   # stays the same

    async def test_group(self):
        formname = 'inet:group'
        valu = 'cool Group '
        expected_props = {}
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_http_cookie(self):

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('inet:http:cookie', 'HeHe=HaHa')
                self.eq(node.ndef[1], 'HeHe=HaHa')

    def test_http_header(self):
        pass # this is tested below...

    def test_http_header_name(self):
        pass # this is tested below...

    async def test_http_request_header(self):
        formname = 'inet:http:request:header'
        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('cool', 'Cooler'))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_http_response_header(self):

        formname = 'inet:http:response:header'

        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('cool', 'Cooler'))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_http_param(self):
        formname = 'inet:http:param'
        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('Cool', 'Cooler'))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_http_request(self):
        formname = 'inet:http:request'
        input_props = {
            'time': '2015',
            'flow': 32 * 'f',
            'method': 'gEt',
            'path': '/woot/hehe/',
            'query': 'hoho=1&qaz=bar',
            'client': '1.2.3.4',
            'server': '5.5.5.5:443',
            'body': 64 * 'b',
            'response:code': 200,
            'response:reason': 'OK',
            'response:body': 64 * 'b'
        }
        expected_props = {
            'time': 1420070400000,
            'flow': 32 * 'f',
            'method': 'gEt',
            'path': '/woot/hehe/',
            'query': 'hoho=1&qaz=bar',
            'body': 'sha256:' + 64 * 'b',

            'client:ipv4': 0x01020304,

            'server:port': 443,
            'server:ipv4': 0x05050505,

            'response:code': 200,
            'response:reason': 'OK',
            'response:body': 'sha256:' + 64 * 'b',
        }
        expected_ndef = (formname, 32 * 'a')
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_iface(self):
        formname = 'inet:iface'
        valu = 32 * 'a'
        input_props = {
            'host': 32 * 'c',
            'type': 'Cool',
            'mac': 'ff:00:ff:00:ff:00',
            'ipv4': '1.2.3.4',
            'ipv6': 'ff::00',
            'phone': 12345678910,
            'wifi:ssid': 'hehe haha',
            'wifi:bssid': '00:ff:00:ff:00:ff',
            'mob:imei': 123456789012347,
            'mob:imsi': 12345678901234,
        }
        expected_props = {
            'host': 32 * 'c',
            'type': 'cool',
            'mac': 'ff:00:ff:00:ff:00',
            'ipv4': 16909060,
            'ipv6': 'ff::',
            'phone': '12345678910',
            'wifi:ssid': 'hehe haha',
            'wifi:bssid': '00:ff:00:ff:00:ff',
            'mob:imei': 123456789012347,
            'mob:imsi': 12345678901234,
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

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

            # Demonstrate wrap-around
            info = {'subs': {'type': 'private'}}
            self.eq(t.norm(0x00000000 - 1), (2**32 - 1, info))
            self.eq(t.norm(0xFFFFFFFF + 1), (0, info))

            # Form Tests ======================================================
            place = s_common.guid()
            input_props = {
                'asn': 3,
                'loc': 'uS',
                'dns:rev': 'vertex.link',
                'latlong': '-50.12345, 150.56789',
                'place': place,
            }
            expected_props = {
                'asn': 3,
                'loc': 'us',
                'type': 'unicast',
                'dns:rev': 'vertex.link',
                'latlong': (-50.12345, 150.56789),
                'place': place,
            }
            valu_str = '1.2.3.4'
            valu_int = 16909060
            expected_ndef = (formname, valu_int)

            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu_str, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_ipv6(self):
        formname = 'inet:ipv6'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            info = {'subs': {'type': 'loopback'}}
            self.eq(t.norm('::1'), ('::1', info))
            self.eq(t.norm('0:0:0:0:0:0:0:1'), ('::1', info))

            info = {'subs': {'type': 'private'}}
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
            async with await core.snap() as snap:

                place = s_common.guid()

                valu_str = '::fFfF:1.2.3.4'
                input_props = {
                    'loc': 'cool',
                    'latlong': '0,2',
                    'dns:rev': 'vertex.link',
                    'place': place,
                }
                expected_props = {
                    'ipv4': 16909060,
                    'loc': 'cool',
                    'latlong': (0.0, 2.0),
                    'dns:rev': 'vertex.link',
                    'place': place,
                }
                expected_ndef = (formname, valu_str.lower())
                node = await snap.addNode(formname, valu_str, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                valu_str = '::1'
                expected_props = {
                }
                expected_ndef = (formname, valu_str)
                node = await snap.addNode(formname, valu_str)
                self.checkNode(node, (expected_ndef, expected_props))

            await self.agenlen(1, core.eval('inet:ipv6*range=(0::1, 0::1)'))

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
            async with await core.snap() as snap:
                valu = '00:00:00:00:00:00'
                expected_ndef = (formname, valu)

                node = await snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.none(node.get('vendor'))

                node = await snap.addNode(formname, valu, props={'vendor': 'Cool'})
                self.eq(node.ndef, expected_ndef)
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
            async with await core.snap() as snap:

                node = await snap.addNode('inet:passwd', '2Cool4u')
                self.eq(node.ndef[1], '2Cool4u')
                self.eq('91112d75297841c12ca655baafc05104', node.get('md5'))
                self.eq('2984ab44774294be9f7a369bbd73b52021bf0bb4', node.get('sha1'))
                self.eq('62c7174a99ff0afd4c828fc779d2572abc2438415e3ca9769033d4a36479b14f', node.get('sha256'))

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

            # Form Tests ======================================================
            valu = '"UnitTest"    <UnitTest@Vertex.link>'
            expected_ndef = (formname, 'unittest <unittest@vertex.link>')
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('email'), 'unittest@vertex.link')
                self.eq(node.get('name'), 'unittest')

                await snap.addNode(formname, '"UnitTest1')
                await snap.addNode(formname, '"UnitTest12')

                self.len(3, await snap.nodes('inet:rfc2822:addr^=unittest'))
                self.len(2, await snap.nodes('inet:rfc2822:addr^=unittest1'))
                self.len(1, await snap.nodes('inet:rfc2822:addr^=unittest12'))

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
            async with await core.snap() as snap:
                for valu, expected_valu, expected_props in data:
                    node = await snap.addNode(formname, valu)
                    self.checkNode(node, ((formname, expected_valu), expected_props))

    async def test_servfile(self):
        formname = 'inet:servfile'
        valu = ('tcp://127.0.0.1:4040', 'sha256:' + 64 * 'f')
        input_props = {
            'server:host': 32 * 'a'
        }
        expected_props = {
            'server': 'tcp://127.0.0.1:4040',
            'server:host': 32 * 'a',
            'server:port': 4040,
            'server:proto': 'tcp',
            'server:ipv4': 2130706433,
            'file': 'sha256:' + 64 * 'f'
        }
        expected_ndef = (formname, tuple(item.lower() for item in valu))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_ssl_cert(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('inet:ssl:cert', ('tcp://1.2.3.4:443', 'guid:abcdabcdabcdabcdabcdabcdabcdabcd'))

                self.eq(node.get('file'), 'guid:abcdabcdabcdabcdabcdabcdabcdabcd')
                self.eq(node.get('server'), 'tcp://1.2.3.4:443')

                self.eq(node.get('server:port'), 443)
                self.eq(node.get('server:ipv4'), 0x01020304)

    async def test_url(self):
        formname = 'inet:url'
        async with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.raises(s_exc.BadTypeValu, t.norm, 'http:///wat')  # No Host
            self.raises(s_exc.BadTypeValu, t.norm, 'wat')  # No Protocol

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com/hehe.asp')
            valu = t.norm('http://www.googlesites.com/hehe\udcfestuff.asp')[0]

            # Form Tests ======================================================
            async with await core.snap() as snap:
                valu = 'https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1'
                expected_ndef = (formname, valu)
                node = await snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('passwd'), 'hunter2')
                self.eq(node.get('path'), '/coolthings')
                self.eq(node.get('port'), 1337)
                self.eq(node.get('proto'), 'https')
                self.eq(node.get('user'), 'vertexmc')
                self.eq(node.get('base'), 'https://vertexmc:hunter2@vertex.link:1337/coolthings')
                self.eq(node.get('params'), '?a=1')

                valu = 'https://vertex.link?a=1'
                expected_ndef = (formname, valu)
                node = await snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
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
        formname = 'inet:urlfile'
        valu = ('https://vertex.link/a_cool_program.exe', 64 * 'f')
        expected_props = {
            'url': 'https://vertex.link/a_cool_program.exe',
            'file': 'sha256:' + 64 * 'f',
        }
        expected_ndef = (formname, (valu[0], 'sha256:' + valu[1]))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

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
        formname = 'inet:urlredir'
        valu = ('https://vertex.link/idk', 'https://cool.vertex.link:443/something_else')
        expected_props = {
            'src': 'https://vertex.link/idk',
            'src:fqdn': 'vertex.link',
            'dst': 'https://cool.vertex.link:443/something_else',
            'dst:fqdn': 'cool.vertex.link',
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_user(self):
        formname = 'inet:user'
        valu = 'cool User '
        expected_props = {}
        expected_ndef = (formname, 'cool user ')
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_acct(self):
        async with self.getTestCore() as core:
            formname = 'inet:web:acct'

            # Type Tests
            t = core.model.type(formname)

            self.raises(s_exc.BadTypeValu, t.norm, 'vertex.link/person1')
            enorm = ('vertex.link', 'person1')
            edata = {'subs': {'user': 'person1',
                              'site': 'vertex.link',
                              'site:host': 'vertex',
                              'site:domain': 'link', },
                     'adds': []}
            self.eq(t.norm(('VerTex.linK', 'PerSon1')), (enorm, edata))

            # Form Tests
            place = s_common.guid()
            valu = ('blogs.Vertex.link', 'Brutus')
            input_props = {
                'avatar': 'sha256:' + 64 * 'a',
                'dob': -64836547200000,
                'email': 'brutus@vertex.link',
                'latlong': '0,0',
                'place': place,
                'loc': 'sol',
                'name': 'ካሳር',
                'name:en': 'brutus',
                'occupation': 'jurist',
                'passwd': 'hunter2',
                'phone': '555-555-5555',
                'realname': 'Брут',
                'realname:en': 'brutus',
                'signup': 3,
                'signup:client': '0.0.0.4',
                'tagline': 'Taglines are not tags',
                'url': 'https://blogs.vertex.link/',
                'webpage': 'https://blogs.vertex.link/brutus',
            }

            expected_ndef = (formname, ('blogs.vertex.link', 'brutus'))
            expected_props = copy.copy(input_props)
            expected_props.update({
                'site': valu[0].lower(),
                'user': valu[1].lower(),
                'latlong': (0.0, 0.0),
                'place': place,
                'phone': '5555555555',
                'realname': 'брут',
                'signup:client': 'tcp://0.0.0.4',
                'signup:client:ipv4': 4,
            })

            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.eq(node.ndef, expected_ndef)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_action(self):
        formname = 'inet:web:action'
        valu = 32 * 'a'
        input_props = {
            'act': 'Did a Thing',
            'acct': ('vertex.link', 'vertexmc'),
            'time': 0,
            'client': '0.0.0.0'
        }
        expected_props = {
            'act': 'did a thing',
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'time': 0,
            'client': 'tcp://0.0.0.0',
            'client:ipv4': 0
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_chprofile(self):
        formname = 'inet:web:chprofile'
        valu = 32 * 'a'
        input_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'client': '0.0.0.3',
            'time': 0,
            'pv': ('inet:web:acct:site', 'Example.com')
        }
        expected_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'client': 'tcp://0.0.0.3',
            'client:ipv4': 3,
            'time': 0,
            'pv': ('inet:web:acct:site', 'example.com'),
            'pv:prop': 'inet:web:acct:site',
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_file(self):
        formname = 'inet:web:file'
        valu = (('vertex.link', 'vertexmc'), 64 * 'f')
        input_props = {
            'name': 'Cool',
            'posted': 0,
            'client': '::1'
        }
        expected_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'file': 'sha256:' + 64 * 'f',
            'name': 'cool',
            'posted': 0,
            'client': 'tcp://::1',
            'client:ipv6': '::1'
        }
        expected_ndef = (formname, (valu[0], 'sha256:' + valu[1]))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_follows(self):
        formname = 'inet:web:follows'
        valu = (('vertex.link', 'vertexmc'), ('example.com', 'aUser'))
        input_props = {}
        expected_props = {
            'follower': ('vertex.link', 'vertexmc'),
            'followee': ('example.com', 'auser'),
        }
        expected_ndef = (formname, (('vertex.link', 'vertexmc'), ('example.com', 'auser')))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_group(self):
        formname = 'inet:web:group'
        valu = ('vertex.link', 'CoolGroup')
        place = s_common.guid()
        input_props = {
            'name': 'The coolest group',
            'name:en': 'The coolest group (in english)',
            'url': 'https://vertex.link/CoolGroup',
            'avatar': 64 * 'f',
            'desc': 'a Really cool group',
            'webpage': 'https://vertex.link/CoolGroup/page',
            'loc': 'the internet',
            'latlong': '0,0',
            'place': place,
            'signup': 0,
            'signup:client': '0.0.0.0',
        }
        expected_props = {
            'site': valu[0],
            'id': valu[1],
            'name': 'The coolest group',
            'name:en': 'The coolest group (in english)',
            'url': 'https://vertex.link/CoolGroup',
            'avatar': 'sha256:' + 64 * 'f',
            'desc': 'a Really cool group',
            'webpage': 'https://vertex.link/CoolGroup/page',
            'loc': 'the internet',
            'latlong': (0.0, 0.0),
            'place': place,
            'signup': 0,
            'signup:client': 'tcp://0.0.0.0',
            'signup:client:ipv4': 0
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_logon(self):
        formname = 'inet:web:logon'
        valu = 32 * 'a'
        input_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'time': 0,
            'client': '::',
            'logout': 1,
        }
        expected_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'time': 0,
            'client': 'tcp://::',
            'client:ipv6': '::',
            'logout': 1,
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_memb(self):
        formname = 'inet:web:memb'
        valu = (('VERTEX.link', 'visi'), ('vertex.LINK', 'kenshoto'))
        input_props = {'joined': 2554848000000, 'title': 'Cool'}
        expected_props = {
            'joined': 2554848000000,
            'title': 'cool',
            'acct': ('vertex.link', 'visi'),
            'group': ('vertex.link', 'kenshoto'),
        }
        expected_ndef = (formname, (('vertex.link', 'visi'), ('vertex.link', 'kenshoto')))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_web_mesg(self):
        formname = 'inet:web:mesg'
        valu = (('VERTEX.link', 'visi'), ('vertex.LINK', 'vertexmc'), 0)
        input_props = {
            'url': 'https://vertex.link/messages/0',
            'client': 'tcp://1.2.3.4',
            'text': 'a cool Message',
            'file': 'sha256:' + 64 * 'F'
        }
        expected_props = {
            'to': ('vertex.link', 'vertexmc'),
            'from': ('vertex.link', 'visi'),
            'time': 0,
            'url': 'https://vertex.link/messages/0',
            'client': 'tcp://1.2.3.4',
            'client:ipv4': 0x01020304,
            'text': 'a cool Message',
            'file': 'sha256:' + 64 * 'f'
        }
        expected_ndef = (formname, (('vertex.link', 'visi'), ('vertex.link', 'vertexmc'), 0))

        valu2 = (('vertex.link', 'visi'), ('vertex.link', 'epiphyte'), 0)
        inputs2 = {'client': '::1'}
        expected2 = {
            'client': 'tcp://::1',
            'client:ipv6': '::1',
        }

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                node = await snap.addNode('inet:web:mesg', valu2, props=inputs2)
                self.checkNode(node, (('inet:web:mesg', valu2), expected2))

    async def test_web_post(self):
        formname = 'inet:web:post'
        valu = 32 * 'a'
        input_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'text': 'my cooL POST',
            'time': 0,
            'url': 'https://vertex.link/mypost',
            'client': 'tcp://1.2.3.4',
            'file': 64 * 'f',
            'replyto': 32 * 'b',
            'repost': 32 * 'c',
        }
        expected_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'client': 'tcp://1.2.3.4',
            'client:ipv4': 0x01020304,
            'text': 'my cooL POST',
            'time': 0,
            'url': 'https://vertex.link/mypost',
            'file': 'sha256:' + 64 * 'f',
            'replyto': 32 * 'b',
            'repost': 32 * 'c',
        }

        node2 = s_common.guid()
        inputs2 = {'client': '::1'}
        expected2 = {
            'client': 'tcp://::1',
            'client:ipv6': '::1',
        }

        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                node = await snap.addNode('inet:web:post', node2, props=inputs2)
                self.checkNode(node, (('inet:web:post', node2), expected2))

    async def test_whois_contact(self):
        formname = 'inet:whois:contact'
        valu = (('vertex.link', '@2015'), 'regiStrar')
        input_props = {
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
        expected_props = {
            'rec': ('vertex.link', 1420070400000),
            'rec:asof': 1420070400000,
            'rec:fqdn': 'vertex.link',
            'type': 'registrar',
            'id': 'id',
            'name': 'name',
            'email': 'unittest@vertex.link',
            'orgname': 'unittest org',
            'address': '1234 not real road',
            'city': 'faketown',
            'state': 'stateland',
            'country': 'us',
            'phone': '5555555555',
            'fax': '5555555556',
            'url': 'https://vertex.link/contact',
            'whois:fqdn': 'vertex.link'
        }
        expected_ndef = (formname, (('vertex.link', 1420070400000), 'registrar'))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_whois_rar(self):
        formname = 'inet:whois:rar'
        valu = 'cool Registrar '
        expected_props = {}
        expected_ndef = (formname, 'cool registrar ')
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_whois_rec(self):
        formname = 'inet:whois:rec'
        valu = ('woot.com', '@20501217')
        input_props = {
            'text': 'YELLING AT pennywise@vertex.link LOUDLY',
            'registrar': ' cool REGISTRAR ',
            'registrant': ' cool REGISTRANT ',
        }
        expected_props = {
            'fqdn': 'woot.com',
            'asof': 2554848000000,
            'text': 'yelling at pennywise@vertex.link loudly',
            'registrar': ' cool registrar ',
            'registrant': ' cool registrant ',
        }
        expected_ndef = (formname, ('woot.com', 2554848000000))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))
            nodes = await core.nodes('inet:whois:email')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:whois:email', ('woot.com', 'pennywise@vertex.link')))

    async def test_whois_recns(self):
        formname = 'inet:whois:recns'
        valu = ('ns1.woot.com', ('woot.com', '@20501217'))
        expected_props = {
            'ns': 'ns1.woot.com',
            'rec': ('woot.com', 2554848000000),
            'rec:fqdn': 'woot.com',
            'rec:asof': 2554848000000,
        }
        expected_ndef = (formname, ('ns1.woot.com', ('woot.com', 2554848000000)))
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_whois_reg(self):
        formname = 'inet:whois:reg'
        valu = 'cool Registrant '
        expected_props = {}
        expected_ndef = (formname, 'cool registrant ')
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_whois_ipquery(self):
        rec = s_common.guid()
        query_ipv4 = s_common.guid()
        props_ipv4 = {
            'time': 2554869000000,
            'fqdn': 'arin.whois.net',
            'ipv4': 167772160,
            'success': True,
            'rec': rec,
        }
        query_ipv6 = s_common.guid()
        props_ipv6 = {
            'time': 2554869000000,
            'url': 'http://myrdap/rdap/?query=3300%3A100%3A1%3A%3Affff',
            'ipv6': '3300:100:1::ffff',
            'success': False,
        }

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('inet:whois:ipquery', query_ipv4, props=props_ipv4)
                self.checkNode(node, (('inet:whois:ipquery', query_ipv4), props_ipv4))

                node = await snap.addNode('inet:whois:ipquery', query_ipv6, props=props_ipv6)
                self.checkNode(node, (('inet:whois:ipquery', query_ipv6), props_ipv6))

    async def test_whois_iprec(self):
        contact = s_common.guid()
        addlcontact = s_common.guid()

        rec_ipv4 = s_common.guid()
        props_ipv4 = {
            'net4': '10.0.0.0/28',
            'asof': 2554869000000,
            'created': 2554858000000,
            'updated': 2554858000000,
            'text': 'this is  a bunch of \nrecord text 123123',
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
        expected_ipv4 = copy.deepcopy(props_ipv4)
        expected_ipv4.update({
            'net4': (167772160, 167772175),
            'net4:min': 167772160,
            'net4:max': 167772175,
            'country': 'us',
        })

        rec_ipv6 = s_common.guid()
        props_ipv6 = {
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
        expected_ipv6 = copy.deepcopy(props_ipv6)
        expected_ipv6.update({
            'net6': ('2001:db8::', '2001:db8::7ff:ffff'),
            'net6:min': '2001:db8::',
            'net6:max': '2001:db8::7ff:ffff',
            'type': 'allocated-by-rir',
        })

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('inet:whois:iprec', rec_ipv4, props=props_ipv4)
                self.checkNode(node, (('inet:whois:iprec', rec_ipv4), expected_ipv4))

                node = await snap.addNode('inet:whois:iprec', rec_ipv6, props=props_ipv6)
                self.checkNode(node, (('inet:whois:iprec', rec_ipv6), expected_ipv6))

                # check regid pivot
                scmd = f'inet:whois:iprec={rec_ipv4} :parentid -> inet:whois:iprec:id'
                nodes = await core.nodes(scmd)
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('inet:whois:iprec', rec_ipv6))

                # bad country code
                guid = s_common.guid()
                props = {'country': 'u9'}
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('inet:whois:iprec', guid, props=props))

    async def test_whois_ipcontact(self):
        pscontact = s_common.guid()
        contact = s_common.guid()
        subcontact = s_common.guid()
        props = {
            'contact': pscontact,
            'asof': 2554869000000,
            'created': 2554858000000,
            'updated': 2554858000000,
            'role': 'registrant',
            'roles': ('abuse', 'technical', 'administrative'),
            'asn': 123456,
            'id': 'SPM-3',
            'links': ('http://myrdap.com/SPM3',),
            'status': 'active',
            'contacts': (subcontact,),
        }

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('inet:whois:ipcontact', contact, props=props)
                self.checkNode(node, (('inet:whois:ipcontact', contact), props))

                # check regid pivot
                iprec_guid = s_common.guid()
                await snap.addNode(f'inet:whois:iprec', iprec_guid, props={'id': props['id']})
                scmd = f'inet:whois:ipcontact={contact} :id -> inet:whois:iprec:id'
                nodes = await core.nodes(scmd)
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('inet:whois:iprec', iprec_guid))

    async def test_wifi_ap(self):

        place = s_common.guid()

        formname = 'inet:wifi:ap'
        valu = ('The Best SSID2 ', '00:11:22:33:44:55')
        props = {
            'accuracy': '10km',
            'latlong': (20, 30),
            'place': place,
        }
        expected_props = {
            'ssid': valu[0],
            'bssid': valu[1],
            'latlong': (20.0, 30.0),
            'accuracy': 10000000,
            'place': place,
        }
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=props)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_wifi_ssid(self):
        formname = 'inet:wifi:ssid'
        valu = 'The Best SSID '
        expected_props = {}
        expected_ndef = (formname, valu)
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    async def test_banner(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('inet:banner', ('tcp://1.2.3.4:443', 'Hi There'))

                self.eq('Hi There', node.get('text'))

                self.eq(443, node.get('server:port'))
                self.eq(0x01020304, node.get('server:ipv4'))

                strn = await snap.getNodeByNdef(('it:dev:str', 'Hi There'))
                self.nn(strn)

    async def test_search_query(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                props = {
                    'time': 200,
                    'text': 'hi there',
                    'engine': 'roofroof',
                }
                iden = s_common.guid()
                node = await snap.addNode('inet:search:query', iden, props=props)
                self.eq(node.get('time'), 200)
                self.eq(node.get('text'), 'hi there')
                self.eq(node.get('engine'), 'roofroof')
                props = {
                    'query': iden,
                    'url': 'http://hehehaha.com/',
                    'rank': 0,
                    'text': 'woot woot woot',
                    'title': 'this is a title',
                }
                residen = s_common.guid()
                node = await snap.addNode('inet:search:result', residen, props=props)
                self.eq(node.get('url'), 'http://hehehaha.com/')
                self.eq(node.get('rank'), 0)
                self.eq(node.get('text'), 'woot woot woot')
                self.eq(node.get('title'), 'this is a title')
                self.eq(node.get('query'), iden)

    async def test_model_inet_email_message(self):

        async with self.getTestCore() as core:
            q = '''
            [
            inet:email:message="*"
                :to=woot@woot.com
                :from=visi@vertex.link
                :replyto=root@root.com
                :subject="hi there"
                :date=2015
                :body="there are mad sploitz here!"
                :bytes="*"
            ]

            {[ inet:email:message:link=($node, https://www.vertex.link) ]}

            {[ inet:email:message:attachment=($node, "*") ] -inet:email:message [ :name=sploit.exe ]}

            {[ edge:has=($node, ('inet:email:header', ('to', 'Visi Kensho <visi@vertex.link>'))) ]}
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            self.len(1, await core.nodes('inet:email:message:to=woot@woot.com'))
            self.len(1, await core.nodes('inet:email:message:date=2015'))
            self.len(1, await core.nodes('inet:email:message:body="there are mad sploitz here!"'))
            self.len(1, await core.nodes('inet:email:message:subject="hi there"'))
            self.len(1, await core.nodes('inet:email:message:replyto=root@root.com'))

            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> edge:has -> inet:email:header +:name=to +:value="Visi Kensho <visi@vertex.link>"'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:message:link -> inet:url +inet:url=https://www.vertex.link'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> inet:email:message:attachment +:name=sploit.exe -> file:bytes'))
            self.len(1, await core.nodes('inet:email:message:from=visi@vertex.link -> file:bytes'))
