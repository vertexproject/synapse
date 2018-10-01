import copy
import logging

import synapse.exc as s_exc
import synapse.models.inet as s_m_inet
import synapse.tests.common as s_t_common

ENFORCE_MODEL_COVERAGE = True  # TODO: replace with envvar when we decide upon a convention
logger = logging.getLogger(__name__)


class InetModelTest(s_t_common.SynTest):

    def test__untested_model_elements(self):
        untested_types = []
        for name in [typ[0] for typ in s_m_inet.InetModule.getModelDefs(None)[0][1]['types']]:

            tname = 'test_' + name.split('inet:', 1)[1].replace(':', '_')
            if not hasattr(self, tname):
                untested_types.append(name)

        untested_forms = []
        for name in [form[0] for form in s_m_inet.InetModule.getModelDefs(None)[0][1]['forms']]:

            tname = 'test_' + name.split('inet:', 1)[1].replace(':', '_')
            if not hasattr(self, tname):
                untested_forms.append(name)

        if (len(untested_types) + len(untested_forms)) > 0:
            msg = f'Untested model elements: types({untested_types}), forms({untested_forms})'
            if ENFORCE_MODEL_COVERAGE is True:
                raise AssertionError(msg)
            logger.warning(msg)

    def test_ipv4_lift_range(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                snap.addNode('inet:ipv4', '1.2.3.0')
                snap.addNode('inet:ipv4', '1.2.3.1')
                snap.addNode('inet:ipv4', '1.2.3.2')
                snap.addNode('inet:ipv4', '1.2.3.3')
                snap.addNode('inet:ipv4', '1.2.3.4')

            self.len(3, core.eval('inet:ipv4=1.2.3.1-1.2.3.3'))
            self.len(3, core.eval('[inet:ipv4=1.2.3.1-1.2.3.3]'))
            self.len(3, core.eval('inet:ipv4 +inet:ipv4=1.2.3.1-1.2.3.3'))

    def test_ipv4_filt_cidr(self):

        with self.getTestCore() as core:

            self.len(5, core.eval('[ inet:ipv4=1.2.3.0/30 inet:ipv4=5.5.5.5 ]'))
            self.len(4, core.eval('inet:ipv4 +inet:ipv4=1.2.3.0/30'))
            self.len(1, core.eval('inet:ipv4 -inet:ipv4=1.2.3.0/30'))

            self.len(256, core.eval('[ inet:ipv4=192.168.1.0/24]'))
            self.len(256, core.eval('[ inet:ipv4=192.168.2.0/24]'))
            self.len(256, core.eval('inet:ipv4=192.168.1.0/24'))

            # Seed some nodes for bounds checking
            pnodes = [(('inet:ipv4', f'10.2.1.{d}'), {}) for d in range(1, 33)]
            nodes = list(core.addNodes(pnodes))

            nodes = list(core.eval('inet:ipv4=10.2.1.4/32'))
            self.len(1, nodes)
            self.len(1, core.eval('inet:ipv4 +inet:ipv4=10.2.1.4/32'))

            nodes = list(core.eval('inet:ipv4=10.2.1.4/31'))
            self.len(2, nodes)
            self.len(2, core.eval('inet:ipv4 +inet:ipv4=10.2.1.4/31'))

            # 10.2.1.1/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = list(core.eval('inet:ipv4=10.2.1.1/30'))
            self.len(3, nodes)

            # 10.2.1.2/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
            nodes = list(core.eval('inet:ipv4=10.2.1.2/30'))
            self.len(3, nodes)

            # 10.2.1.1/29 is 10.2.1.0 -> 10.2.1.7 but we don't have 10.2.1.0 in the core
            nodes = list(core.eval('inet:ipv4=10.2.1.1/29'))
            self.len(7, nodes)

            # 10.2.1.8/29 is 10.2.1.8 -> 10.2.1.15
            nodes = list(core.eval('inet:ipv4=10.2.1.8/29'))
            self.len(8, nodes)

            # 10.2.1.1/28 is 10.2.1.0 -> 10.2.1.15 but we don't have 10.2.1.0 in the core
            nodes = list(core.eval('inet:ipv4=10.2.1.1/28'))
            self.len(15, nodes)

    def test_addr(self):
        formname = 'inet:addr'
        with self.getTestCore() as core:
            t = core.model.type(formname)

            # Proto defaults to tcp
            self.eq(t.norm('1.2.3.4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.eq(t.norm('1.2.3.4:80'), ('tcp://1.2.3.4:80', {'subs': {'port': 80, 'ipv4': 16909060, 'proto': 'tcp'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'https://192.168.1.1:80')  # bad proto

            # IPv4
            self.eq(t.norm('tcp://1.2.3.4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.eq(t.norm('udp://1.2.3.4:80'), ('udp://1.2.3.4:80', {'subs': {'port': 80, 'ipv4': 16909060, 'proto': 'udp'}}))
            self.eq(t.norm('tcp://1[.]2.3[.]4'), ('tcp://1.2.3.4', {'subs': {'ipv4': 16909060, 'proto': 'tcp'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://1.2.3.4:-1')
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://1.2.3.4:66000')

            # IPv6
            self.eq(t.norm('icmp://::1'), ('icmp://::1', {'subs': {'ipv6': '::1', 'proto': 'icmp'}}))
            self.eq(t.norm('tcp://[::1]:2'), ('tcp://[::1]:2', {'subs': {'ipv6': '::1', 'port': 2, 'proto': 'tcp'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'tcp://[::1')  # bad ipv6 w/ port

            # Host
            hstr = 'ffa3e574aa219e553e1b2fc1ccd0180f'
            self.eq(t.norm('host://vertex.link'), (f'host://{hstr}', {'subs': {'host': hstr, 'proto': 'host'}}))
            self.eq(t.norm('host://vertex.link:1337'), (f'host://{hstr}:1337', {'subs': {'host': hstr, 'port': 1337, 'proto': 'host'}}))
            self.raises(s_exc.BadTypeValu, t.norm, 'vertex.link')  # must use host proto

    def test_asn(self):
        formname = 'inet:asn'
        with self.getTestCore() as core:
            with core.snap() as snap:

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
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                valu = '456'
                expected_ndef = (formname, 456)
                expected_props = {'name': '??'}
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_asnet4(self):
        formname = 'inet:asnet4'
        with self.getTestCore() as core:
            with core.snap() as snap:

                valu = ('54959', ('1.2.3.4', '5.6.7.8'))
                expected_ndef = (formname, (54959, (16909060, 84281096)))
                expected_props = {
                    'net4:min': 16909060,
                    'net4': (16909060, 84281096),
                    'net4:max': 84281096,
                    'asn': 54959,
                }
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_cidr4(self):
        formname = 'inet:cidr4'
        with self.getTestCore() as core:

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

            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('network'), 3232235776)  # 192.168.1.0
                self.eq(node.get('broadcast'), 3232236031)  # 192.168.1.255
                self.eq(node.get('mask'), 24)

    def test_client(self):
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

        with self.getTestCore() as core:
            with core.snap() as snap:
                for valu, expected_valu, expected_props in data:
                    node = snap.addNode(formname, valu)
                    self.checkNode(node, ((formname, expected_valu), expected_props))

    def test_download(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, ((formname, 32 * 'a'), expected_props))

    def test_email(self):
        formname = 'inet:email'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {'fqdn': 'vertex.link', 'user': 'unittest'}})
            self.eq(t.norm(email), expected)

            valu = t.norm('bob\udcfesmith@woot.com')[0]
            self.eq(b'bob\xed\xb3\xbesmith@woot.com', t.indx(valu))

            # Form Tests ======================================================
            valu = 'UnitTest@Vertex.link'
            expected_ndef = (formname, valu.lower())
            expected_props = {
                'fqdn': 'vertex.link',
                'user': 'unittest',
            }
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_flow(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_fqdn(self):
        formname = 'inet:fqdn'
        with self.getTestCore() as core:

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
            self.none(t.repr(fqdn))  # UnicodeError raised and caught and fallback to norm

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com')

            # Form Tests ======================================================
            valu = 'api.vertex.link'
            expected_ndef = (formname, valu)

            # Demonstrate cascading formation
            # FIXME use checkNode
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props={'created': 0, 'expires': 1, 'updated': 2})
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'vertex.link')
                self.eq(node.get('expires'), 1)
                self.eq(node.get('host'), 'api')
                self.eq(node.get('issuffix'), 0)
                self.eq(node.get('iszone'), 0)
                self.eq(node.get('updated'), 2)
                self.eq(node.get('zone'), 'vertex.link')

            with core.snap() as snap:
                nvalu = 'vertex.link'
                expected_ndef = (formname, nvalu)
                node = snap.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'link')
                self.eq(node.get('host'), 'vertex')
                self.eq(node.get('issuffix'), 0)
                self.eq(node.get('iszone'), 1)
                self.eq(node.get('zone'), 'vertex.link')

            with core.snap() as snap:
                nvalu = 'link'
                expected_ndef = (formname, nvalu)
                node = snap.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('host'), 'link')
                self.eq(node.get('issuffix'), 1)
                self.eq(node.get('iszone'), 0)

            # Demonstrate wildcard
            with core.snap() as snap:
                self.len(3, list(snap.getNodesBy(formname, '*')))
                self.len(2, list(snap.getNodesBy(formname, '*.link')))
                self.len(1, list(snap.getNodesBy(formname, '*.vertex.link')))
                self.genraises(s_exc.BadLiftValu, snap.getNodesBy, formname, 'api.*.link')

    def test_fqdn_suffix(self):
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

        with self.getTestCore() as core:
            with core.snap() as snap:

                # Create some nodes and demonstrate zone/suffix behavior
                # Only FQDNs of the lowest level should be suffix
                # Only FQDNs whose domains are suffixes should be zones
                n0 = snap.addNode(formname, 'abc.vertex.link')
                n1 = snap.addNode(formname, 'def.vertex.link')
                n2 = snap.addNode(formname, 'g.def.vertex.link')
                n1 = snap.addNode(formname, 'def.vertex.link')  # form again to show g. should not make this a zone
                n3 = snap.getNodeByNdef((formname, 'vertex.link'))
                n4 = snap.getNodeByNdef((formname, 'link'))
                isneither(n0)
                isneither(n1)
                isneither(n2)
                iszone(n3)     # vertex.link should be a zone
                issuffix(n4)   # link should be a suffix

                # Make one of the FQDNs a suffix and make sure its children become zones
                n3 = snap.addNode(formname, 'vertex.link', props={'issuffix': True})
                isboth(n3)     # vertex.link should now be both because we made it a suffix
                n0 = snap.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = snap.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = snap.getNodeByNdef((formname, 'g.def.vertex.link'))
                iszone(n0)     # now a zone because vertex.link is a suffix
                iszone(n1)     # now a zone because vertex.link is a suffix
                isneither(n2)  # still neither as parent is not a suffix

                # Remove the FQDN's suffix status and make sure its children lose zone status
                n3 = snap.addNode(formname, 'vertex.link', props={'issuffix': False})
                iszone(n3)     # vertex.link should now be a zone becuase we removed its suffix status
                n0 = snap.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = snap.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = snap.getNodeByNdef((formname, 'g.def.vertex.link'))
                n4 = snap.getNodeByNdef((formname, 'link'))
                isneither(n0)  # loses zone status
                isneither(n1)  # loses zone status
                isneither(n2)  # stays the same
                issuffix(n4)   # stays the same

    def test_group(self):
        formname = 'inet:group'
        valu = 'cool Group '
        expected_props = {}
        expected_ndef = (formname, valu)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_http_cookie(self):

        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode('inet:http:cookie', 'HeHe=HaHa')
                self.eq(node.ndef[1], 'HeHe=HaHa')

    def test_http_header(self):
        pass # this is tested below...

    def test_http_header_name(self):
        pass # this is tested below...

    def test_http_request_header(self):
        formname = 'inet:http:request:header'
        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('cool', 'Cooler'))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_http_response_header(self):

        formname = 'inet:http:response:header'

        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('cool', 'Cooler'))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_http_param(self):
        formname = 'inet:http:param'
        valu = ('Cool', 'Cooler')
        expected_props = {
            'name': 'cool',
            'value': 'Cooler'
        }
        expected_ndef = (formname, ('Cool', 'Cooler'))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_http_request(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, 32 * 'a', props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_iface(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_ipv4(self):
        formname = 'inet:ipv4'
        with self.getTestCore() as core:

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

            # Demonstrate wrap-around
            info = {'subs': {'type': 'private'}}
            self.eq(t.norm(0x00000000 - 1), (2**32 - 1, info))
            self.eq(t.norm(0xFFFFFFFF + 1), (0, info))

            # Form Tests ======================================================
            input_props = {
                'asn': 3,
                'loc': 'uS',
                'latlong': '-50.12345, 150.56789'
            }
            expected_props = {
                'asn': 3,
                'loc': 'us',
                'type': 'unicast',
                'latlong': (-50.12345, 150.56789),
            }
            valu_str = '1.2.3.4'
            valu_int = 16909060
            expected_ndef = (formname, valu_int)
            with core.snap() as snap:
                node = snap.addNode(formname, valu_str, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_ipv6(self):
        formname = 'inet:ipv6'
        with self.getTestCore() as core:

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

            # Form Tests ======================================================
            with core.snap() as snap:

                valu_str = '::fFfF:1.2.3.4'
                input_props = {'latlong': '0,2', 'loc': 'cool'}
                expected_props = {
                    'asn': 0,
                    'ipv4': 16909060,
                    'loc': 'cool',
                    'latlong': (0.0, 2.0),
                }
                expected_ndef = (formname, valu_str.lower())
                node = snap.addNode(formname, valu_str, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                valu_str = '::1'
                expected_props = {
                    'asn': 0,
                    'loc': '??',
                }
                expected_ndef = (formname, valu_str)
                node = snap.addNode(formname, valu_str)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_mac(self):
        formname = 'inet:mac'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.eq(t.norm('00:00:00:00:00:00'), ('00:00:00:00:00:00', {}))
            self.eq(t.norm('FF:ff:FF:ff:FF:ff'), ('ff:ff:ff:ff:ff:ff', {}))
            self.raises(s_exc.BadTypeValu, t.norm, ' FF:ff:FF:ff:FF:ff ')
            self.raises(s_exc.BadTypeValu, t.norm, 'GG:ff:FF:ff:FF:ff')

            # Form Tests ======================================================
            with core.snap() as snap:
                valu = '00:00:00:00:00:00'
                expected_ndef = (formname, valu)

                node = snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('vendor'), '??')

                node = snap.addNode(formname, valu, props={'vendor': 'Cool'})
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('vendor'), 'Cool')

    def test_net4(self):
        tname = 'inet:net4'
        with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('1.2.3.4', '5.6.7.8')
            expected = ((16909060, 84281096), {'subs': {'min': 16909060, 'max': 84281096}})
            self.eq(t.norm(valu), expected)

            valu = '1.2.3.4-5.6.7.8'
            self.eq(t.norm(valu), expected)

            self.raises(s_exc.BadTypeValu, t.norm, (valu[1], valu[0]))

    def test_net6(self):
        tname = 'inet:net6'
        with self.getTestCore() as core:
            # Type Tests ======================================================
            t = core.model.type(tname)

            valu = ('0:0:0:0:0:0:0:0', '::Ff')
            expected = (('::', '::ff'), {'subs': {'min': '::', 'max': '::ff'}})
            self.eq(t.norm(valu), expected)

            valu = '0:0:0:0:0:0:0:0-::Ff'
            self.eq(t.norm(valu), expected)

            self.raises(s_exc.BadTypeValu, t.norm, (valu[1], valu[0]))

    def test_passwd(self):
        with self.getTestCore() as core:
            with core.snap() as snap:

                node = snap.addNode('inet:passwd', '2Cool4u')
                self.eq(node.ndef[1], '2Cool4u')
                self.eq('91112d75297841c12ca655baafc05104', node.get('md5'))
                self.eq('2984ab44774294be9f7a369bbd73b52021bf0bb4', node.get('sha1'))
                self.eq('62c7174a99ff0afd4c828fc779d2572abc2438415e3ca9769033d4a36479b14f', node.get('sha256'))

    def test_port(self):
        tname = 'inet:port'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(tname)
            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.eq(t.norm(0), (0, {}))
            self.eq(t.norm(1), (1, {}))
            self.eq(t.norm('2'), (2, {}))
            self.eq(t.norm('0xF'), (15, {}))
            self.eq(t.norm(65535), (65535, {}))
            self.raises(s_exc.BadTypeValu, t.norm, 65536)

    def test_rfc2822_addr(self):
        formname = 'inet:rfc2822:addr'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.eq(t.norm('FooBar'), ('foobar', {'subs': {}}))
            self.eq(t.norm('visi@vertex.link'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))
            self.eq(t.norm('foo bar<visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('foo bar <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('"foo bar "   <visi@vertex.link>'), ('foo bar <visi@vertex.link>', {'subs': {'email': 'visi@vertex.link', 'name': 'foo bar'}}))
            self.eq(t.norm('<visi@vertex.link>'), ('visi@vertex.link', {'subs': {'email': 'visi@vertex.link'}}))

            valu = t.norm('bob\udcfesmith@woot.com')[0]
            self.eq(b'bob\xed\xb3\xbesmith@woot.com', t.indx(valu))
            self.eq(b'bob\xed\xb3\xbesmith', t.indxByPref('bob\udcfesmith')[0][1])

            self.raises(s_exc.NoSuchFunc, t.norm, 20)

            # Form Tests ======================================================
            valu = '"UnitTest"    <UnitTest@Vertex.link>'
            expected_ndef = (formname, 'unittest <unittest@vertex.link>')
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('email'), 'unittest@vertex.link')
                self.eq(node.get('name'), 'unittest')

                snap.addNode(formname, '"UnitTest1')
                snap.addNode(formname, '"UnitTest12')

                self.len(3, list(snap.getNodesBy(formname, 'unittest', cmpr='^=')))
                self.len(2, list(snap.getNodesBy(formname, 'unittest1', cmpr='^=')))
                self.len(1, list(snap.getNodesBy(formname, 'unittest12', cmpr='^=')))

    def test_server(self):
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

        with self.getTestCore() as core:
            with core.snap() as snap:
                for valu, expected_valu, expected_props in data:
                    node = snap.addNode(formname, valu)
                    self.checkNode(node, ((formname, expected_valu), expected_props))

    def test_servfile(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_ssl_cert(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('inet:ssl:cert', ('tcp://1.2.3.4:443', 'guid:abcdabcdabcdabcdabcdabcdabcdabcd'))

                self.eq(node.get('file'), 'guid:abcdabcdabcdabcdabcdabcdabcdabcd')
                self.eq(node.get('server'), 'tcp://1.2.3.4:443')

                self.eq(node.get('server:port'), 443)
                self.eq(node.get('server:ipv4'), 0x01020304)

    def test_url(self):
        formname = 'inet:url'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type(formname)

            self.raises(s_exc.BadTypeValu, t.norm, 'http:///wat')  # No Host
            self.raises(s_exc.BadTypeValu, t.norm, 'wat')  # No Protocol

            self.raises(s_exc.BadTypeValu, t.norm, 'www.google\udcfesites.com/hehe.asp')
            valu = t.norm('http://www.googlesites.com/hehe\udcfestuff.asp')[0]
            self.eq(b'http://www.googlesites.com/hehe\xed\xb3\xbestuff.asp',
                    t.indx(valu))

            # Form Tests ======================================================
            with core.snap() as snap:

                valu = 'https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1'
                expected_ndef = (formname, valu)
                node = snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('passwd'), 'hunter2')
                self.eq(node.get('path'), '/coolthings?a=1')
                self.eq(node.get('port'), 1337)
                self.eq(node.get('proto'), 'https')
                self.eq(node.get('user'), 'vertexmc')

                valu = 'https://vertex.link?a=1'
                expected_ndef = (formname, valu)
                node = snap.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('path'), '?a=1')

                self.len(2, snap.storm('inet:url^=https'))

    def test_url_fqdn(self):

        with self.getTestCore() as core:

            t = core.model.type('inet:url')

            host = 'Vertex.Link'
            norm_host = core.model.type('inet:fqdn').norm(host)[0]
            repr_host = core.model.type('inet:fqdn').repr(norm_host, defval=norm_host)

            self.eq(norm_host, 'vertex.link')
            self.eq(repr_host, 'vertex.link')

            self._test_types_url_behavior(t, 'fqdn', host, norm_host, repr_host)

    def test_url_ipv4(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '192[.]168.1[.]1'
            norm_host = core.model.type('inet:ipv4').norm(host)[0]
            repr_host = core.model.type('inet:ipv4').repr(norm_host, defval=norm_host)
            self.eq(norm_host, 3232235777)
            self.eq(repr_host, '192.168.1.1')

            self._test_types_url_behavior(t, 'ipv4', host, norm_host, repr_host)

    def test_url_ipv6(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '::1'
            norm_host = core.model.type('inet:ipv6').norm(host)[0]
            repr_host = core.model.type('inet:ipv6').repr(norm_host, defval=norm_host)
            self.eq(norm_host, '::1')
            self.eq(repr_host, '::1')

            self._test_types_url_behavior(t, 'ipv6', host, norm_host, repr_host)

            # IPv6 Port Special Cases
            weird = t.norm('http://::1:81/hehe')
            self.eq(weird[1]['subs']['ipv6'], '::1:81')
            self.eq(weird[1]['subs']['port'], 80)

            self.raises(s_exc.BadTypeValu, t.norm, 'http://0:0:0:0:0:0:0:0:81/')

    def _test_types_url_behavior(self, t, htype, host, norm_host, repr_host):

        # Handle IPv6 Port Brackets
        host_port = host
        repr_host_port = repr_host

        if htype == 'ipv6':
            host_port = f'[{host}]'
            repr_host_port = f'[{repr_host}]'

        # URL with auth and port.
        url = f'https://user:password@{host_port}:1234/a/b/c/'
        expected = (f'https://user:password@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 1234
        }})
        self.eq(t.norm(url), expected)

        # URL with no port, but default port valu.
        # Port should be in subs, but not normed URL.
        url = f'https://user:password@{host}/a/b/c/'
        expected = (f'https://user:password@{repr_host}/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host, 'port': 443
        }})
        self.eq(t.norm(url), expected)

        # URL with no port and no default port valu.
        # Port should not be in subs or normed URL.
        url = f'arbitrary://user:password@{host}/a/b/c/'
        expected = (f'arbitrary://user:password@{repr_host}/a/b/c/', {'subs': {
            'proto': 'arbitrary', 'path': '/a/b/c/', 'user': 'user', 'passwd': 'password', htype: norm_host
        }})
        self.eq(t.norm(url), expected)

        # URL with user but no password.
        # User should still be in URL and subs.
        url = f'https://user@{host_port}:1234/a/b/c/'
        expected = (f'https://user@{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', 'user': 'user', htype: norm_host, 'port': 1234
        }})
        self.eq(t.norm(url), expected)

        # URL with no user/password.
        # User/Password should not be in URL or subs.
        url = f'https://{host_port}:1234/a/b/c/'
        expected = (f'https://{repr_host_port}:1234/a/b/c/', {'subs': {
            'proto': 'https', 'path': '/a/b/c/', htype: norm_host, 'port': 1234
        }})
        self.eq(t.norm(url), expected)

        # URL with no path.
        url = f'https://{host_port}:1234'
        expected = (f'https://{repr_host_port}:1234', {'subs': {
            'proto': 'https', 'path': '', htype: norm_host, 'port': 1234
        }})
        self.eq(t.norm(url), expected)

        # URL with no path or port or default port.
        url = f'a://{host}'
        expected = (f'a://{repr_host}', {'subs': {
            'proto': 'a', 'path': '', htype: norm_host
        }})
        self.eq(t.norm(url), expected)

    def test_urlfile(self):
        formname = 'inet:urlfile'
        valu = ('https://vertex.link/a_cool_program.exe', 64 * 'f')
        expected_props = {
            'url': 'https://vertex.link/a_cool_program.exe',
            'file': 'sha256:' + 64 * 'f',
        }
        expected_ndef = (formname, (valu[0], 'sha256:' + valu[1]))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_urlredir(self):
        formname = 'inet:urlredir'
        valu = ('https://vertex.link/idk', 'https://cool.vertex.link:443/something_else')
        expected_props = {
            'src': 'https://vertex.link/idk',
            'src:fqdn': 'vertex.link',
            'dst': 'https://cool.vertex.link:443/something_else',
            'dst:fqdn': 'cool.vertex.link',
        }
        expected_ndef = (formname, valu)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_user(self):
        formname = 'inet:user'
        valu = 'cool User '
        expected_props = {}
        expected_ndef = (formname, 'cool user ')
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_acct(self):
        with self.getTestCore() as core:
            formname = 'inet:web:acct'

            # Type Tests
            t = core.model.type(formname)

            self.raises(s_exc.NoSuchFunc, t.norm, 'vertex.link/person1')  # No longer a sepr
            enorm = ('vertex.link', 'person1')
            edata = {'subs': {'user': 'person1',
                              'site': 'vertex.link',
                              'site:host': 'vertex',
                              'site:domain': 'link', },
                     'adds': []}
            self.eq(t.norm(('VerTex.linK', 'PerSon1')), (enorm, edata))

            # Form Tests
            valu = ('blogs.Vertex.link', 'Brutus')
            input_props = {
                'avatar': 'sha256:' + 64 * 'a',
                'dob': -64836547200000,
                'email': 'brutus@vertex.link',
                'latlong': '0,0',
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
                'phone': '5555555555',
                'realname': 'брут',
                'signup:client': 'tcp://0.0.0.4',
                'signup:client:ipv4': 4,
            })

            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.eq(node.ndef, expected_ndef)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_action(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_actref(self):
        formname = 'inet:web:actref'
        valu = (32 * 'a', ('inet:ipv4', '0.0.0.1'))
        input_props = {}
        expected_props = {
            'act': 32 * 'a',
            'node': ('inet:ipv4', 1),
            'node:form': 'inet:ipv4',
        }
        expected_ndef = (formname, (32 * 'a', ('inet:ipv4', 1)))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_chprofile(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_file(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_follows(self):
        formname = 'inet:web:follows'
        valu = (('vertex.link', 'vertexmc'), ('example.com', 'aUser'))
        input_props = {}
        expected_props = {
            'follower': ('vertex.link', 'vertexmc'),
            'followee': ('example.com', 'auser'),
        }
        expected_ndef = (formname, (('vertex.link', 'vertexmc'), ('example.com', 'auser')))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_group(self):
        formname = 'inet:web:group'
        valu = ('vertex.link', 'CoolGroup')
        input_props = {
            'name': 'The coolest group',
            'name:en': 'The coolest group (in english)',
            'url': 'https://vertex.link/CoolGroup',
            'avatar': 64 * 'f',
            'desc': 'a Really cool group',
            'webpage': 'https://vertex.link/CoolGroup/page',
            'loc': 'the internet',
            'latlong': '0,0',
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
            'signup': 0,
            'signup:client': 'tcp://0.0.0.0',
            'signup:client:ipv4': 0
        }
        expected_ndef = (formname, valu)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_logon(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_memb(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_mesg(self):
        formname = 'inet:web:mesg'
        valu = (('VERTEX.link', 'visi'), ('vertex.LINK', 'vertexmc'), 0)
        input_props = {
            'url': 'https://vertex.link/messages/0',
            'text': 'a cool Message',
            'file': 'sha256:' + 64 * 'F'
        }
        expected_props = {
            'to': ('vertex.link', 'vertexmc'),
            'from': ('vertex.link', 'visi'),
            'time': 0,
            'url': 'https://vertex.link/messages/0',
            'text': 'a cool Message',
            'file': 'sha256:' + 64 * 'f'
        }
        expected_ndef = (formname, (('vertex.link', 'visi'), ('vertex.link', 'vertexmc'), 0))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_post(self):
        formname = 'inet:web:post'
        valu = 32 * 'a'
        input_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'text': 'my cooL POST',
            'time': 0,
            'url': 'https://vertex.link/mypost',
            'file': 64 * 'f',
            'replyto': 32 * 'b',
            'repost': 32 * 'c',
        }
        expected_props = {
            'acct': ('vertex.link', 'vertexmc'),
            'acct:site': 'vertex.link',
            'acct:user': 'vertexmc',
            'text': 'my cooL POST',
            'time': 0,
            'url': 'https://vertex.link/mypost',
            'file': 'sha256:' + 64 * 'f',
            'replyto': 32 * 'b',
            'repost': 32 * 'c',
        }
        expected_ndef = (formname, valu)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_web_postref(self):
        formname = 'inet:web:postref'
        valu = (32 * 'a', ('inet:ipv4', '0.0.0.1'))
        input_props = {}
        expected_props = {
            'post': 32 * 'a',
            'node': ('inet:ipv4', 1),
            'node:form': 'inet:ipv4',
        }
        expected_ndef = (formname, (32 * 'a', ('inet:ipv4', 1)))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_whois_contact(self):
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
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_whois_rar(self):
        formname = 'inet:whois:rar'
        valu = 'cool Registrar '
        expected_props = {}
        expected_ndef = (formname, 'cool registrar ')
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_whois_rec(self):
        formname = 'inet:whois:rec'
        valu = ('woot.com', '@20501217')
        input_props = {
            'text': 'YELLING TO VISI@VERTEX.LINK AND SUCH',
            'created': 0,
            'updated': 1,
            'expires': 2,
            'registrar': ' cool REGISTRAR ',
            'registrant': ' cool REGISTRANT ',
        }
        expected_props = {
            'fqdn': 'woot.com',
            'asof': 2554848000000,
            'text': 'yelling to visi@vertex.link and such',
            'created': 0,
            'updated': 1,
            'expires': 2,
            'registrar': ' cool registrar ',
            'registrant': ' cool registrant ',
        }

        expected_ndef = (formname, ('woot.com', 2554848000000))
        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))

                whomail = snap.getNodeByNdef(('inet:whois:email', ('woot.com', 'visi@vertex.link')))
                self.nn(whomail)
                self.eq(whomail.get('fqdn'), 'woot.com')
                self.eq(whomail.get('email'), 'visi@vertex.link')
                self.eq(whomail.get('.seen'), (2554848000000, 2554848000001))

    def test_whois_recns(self):
        formname = 'inet:whois:recns'
        valu = ('ns1.woot.com', ('woot.com', '@20501217'))
        expected_props = {
            'ns': 'ns1.woot.com',
            'rec': ('woot.com', 2554848000000),
            'rec:fqdn': 'woot.com',
            'rec:asof': 2554848000000,
        }
        expected_ndef = (formname, ('ns1.woot.com', ('woot.com', 2554848000000)))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_whois_reg(self):
        formname = 'inet:whois:reg'
        valu = 'cool Registrant '
        expected_props = {}
        expected_ndef = (formname, 'cool registrant ')
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_whois_regmail(self):
        formname = 'inet:whois:regmail'
        valu = ('wOOt.Com', 'visi@vertex.LINK')
        expected_props = {
            'fqdn': 'woot.com',
            'email': 'visi@vertex.link',
        }
        expected_ndef = (formname, tuple(item.lower() for item in valu))
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_wifi_ap(self):
        valu = ('The Best SSID2 ', '00:11:22:33:44:55')
        ndef = ('inet:wifi:ap', valu)
        props = {'loc': 'ru', 'latlong': (-50.12345, 150.56789)}
        expected = {
            'ssid': valu[0],
            'bssid': valu[1],
        }
        expected.update(props)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode('inet:wifi:ap', valu, props=props)
                self.checkNode(node, (ndef, expected))

    def test_wifi_ssid(self):
        formname = 'inet:wifi:ssid'
        valu = 'The Best SSID '
        expected_props = {}
        expected_ndef = (formname, valu)
        with self.getTestCore() as core:
            with core.snap() as snap:
                node = snap.addNode(formname, valu)
                self.checkNode(node, (expected_ndef, expected_props))

    def test_banner(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('inet:banner', ('tcp://1.2.3.4:443', 'Hi There'))

                self.eq('Hi There', node.get('text'))

                self.eq(443, node.get('server:port'))
                self.eq(0x01020304, node.get('server:ipv4'))

                strn = snap.getNodeByNdef(('it:dev:str', 'Hi There'))
                self.nn(strn)
