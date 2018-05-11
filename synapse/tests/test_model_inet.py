import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.common as s_t_common


class InetModelTest(s_t_common.SynTest):

    def test__unextended(self):
        with self.getTestCore() as core:

            # The following types are subtypes that do not extend their base type
            self.nn(core.model.type('inet:asn'))  # int
            self.nn(core.model.type('inet:asnet4'))  # comp
            self.nn(core.model.type('inet:net4'))  # range
            self.nn(core.model.type('inet:passwd'))  # str
            self.nn(core.model.type('inet:port'))  # int w/ min/max
            self.nn(core.model.type('inet:user'))  # str w/ lower
            self.nn(core.model.type('inet:urlfile'))  # comp
            self.nn(core.model.type('inet:urlredir'))  # comp
            self.nn(core.model.type('inet:web:acct'))  # comp
            self.nn(core.model.type('inet:web:action'))  # guid
            self.nn(core.model.type('inet:web:file'))  # comp
            self.nn(core.model.type('inet:web:follows'))  # comp
            self.nn(core.model.type('inet:web:group'))  # comp
            self.nn(core.model.type('inet:web:logon'))  # guid
            self.nn(core.model.type('inet:web:post'))  # comp
            self.nn(core.model.type('inet:wifi:ap'))  # comp
            self.nn(core.model.type('inet:wifi:ssid'))  # str
            self.nn(core.model.type('inet:whois:rar'))  # str w/ lower
            self.nn(core.model.type('inet:whois:rec'))  # comp
            self.nn(core.model.type('inet:whois:reg'))  # str w/ lower

            # The following forms do not extend their base type
            self.nn(core.model.form('inet:asnet4'))  # comp
            self.nn(core.model.form('inet:group'))  # str w/ lower
            self.nn(core.model.form('inet:user'))  # str w/ lower
            self.nn(core.model.form('inet:urlfile'))  # comp
            self.nn(core.model.form('inet:urlredir'))  # comp
            self.nn(core.model.form('inet:web:acct'))  # comp
            self.nn(core.model.form('inet:web:action'))  # guid
            self.nn(core.model.form('inet:web:file'))  # comp
            self.nn(core.model.form('inet:web:follows'))  # comp
            self.nn(core.model.form('inet:web:group'))  # comp
            self.nn(core.model.form('inet:web:logon'))  # guid
            self.nn(core.model.form('inet:web:post'))  # comp
            self.nn(core.model.form('inet:wifi:ap'))  # comp
            self.nn(core.model.form('inet:wifi:ssid'))  # str
            self.nn(core.model.form('inet:whois:rar'))  # str w/ lower
            self.nn(core.model.form('inet:whois:rec'))  # comp
            self.nn(core.model.form('inet:whois:reg'))  # str w/ lower

    def test_asn(self):
        formname = 'inet:asn'
        with self.getTestCore() as core:

            with core.xact(write=True) as xact:

                valu = '123'
                input_props = {
                    'name': 'COOL',
                    'owner': 32 * 'a'
                }
                expected_ndef = (formname, 123)
                node = xact.addNode(formname, valu, props=input_props)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('name'), 'cool')
                self.eq(node.get('owner'), 32 * 'a')

                valu = '456'
                expected_ndef = (formname, 456)
                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('name'), '??')

    def test_cidr4(self):
        formname = 'inet:cidr4'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:cidr4')

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

            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('network'), 3232235776)  # 192.168.1.0
                self.eq(node.get('broadcast'), 3232236031)  # 192.168.1.255
                self.eq(node.get('mask'), 24)

    def test_email(self):
        formname = 'inet:email'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:email')

            email = 'UnitTest@Vertex.link'
            expected = ('unittest@vertex.link', {'subs': {'fqdn': 'vertex.link', 'user': 'unittest'}})
            self.eq(t.norm(email), expected)

            # Form Tests ======================================================
            valu = 'UnitTest@Vertex.link'
            expected_ndef = (formname, valu.lower())

            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('user'), 'unittest')

    def test_fqdn(self):
        formname = 'inet:fqdn'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:fqdn')

            fqdn = 'example.Vertex.link'
            expected = ('example.vertex.link', {'subs': {'host': 'example', 'domain': 'vertex.link'}})
            self.eq(t.norm(fqdn), expected)
            self.raises(s_exc.BadTypeValu, t.norm, '!@#$%')

            # Demonstrate Valid IDNA
            fqdn = 'tèst.èxamplè.link'
            ex_fqdn = 'xn--tst-6la.xn--xampl-3raf.link'
            expected = (ex_fqdn, {'subs': {'domain': 'xn--xampl-3raf.link', 'host': 'xn--tst-6la'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)  # Calling repr on IDNA encoded domain should result in the unicode
            self.raises(UnicodeDecodeError, t.repr, fqdn)  # Can't repr unicode domain

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'link'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(fqdn), fqdn)  # UnicodeError raised and caught

            # Form Tests ======================================================
            valu = 'api.vertex.link'
            expected_ndef = (formname, valu)

            # Demonstrate cascading formation
            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu, props={'created': 0, 'expires': 1, 'updated': 2})
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'vertex.link')
                self.eq(node.get('expires'), 1)
                self.eq(node.get('host'), 'api')
                self.eq(node.get('issuffix'), 0)
                self.eq(node.get('iszone'), 0)
                self.eq(node.get('updated'), 2)
                self.eq(node.get('zone'), 'vertex.link')

            with core.xact() as xact:
                nvalu = 'vertex.link'
                expected_ndef = (formname, nvalu)
                node = xact.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('domain'), 'link')
                self.eq(node.get('host'), 'vertex')
                self.eq(node.get('issuffix'), 0)
                self.eq(node.get('iszone'), 1)
                self.eq(node.get('zone'), 'vertex.link')

            with core.xact() as xact:
                nvalu = 'link'
                expected_ndef = (formname, nvalu)
                node = xact.getNodeByNdef((formname, nvalu))
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('host'), 'link')
                self.eq(node.get('issuffix'), 1)
                self.eq(node.get('iszone'), 0)

            # Demonstrate wildcard
            with core.xact() as xact:
                self.len(3, list(xact.getNodesBy(formname, '*')))
                self.len(2, list(xact.getNodesBy(formname, '*.link')))
                self.len(1, list(xact.getNodesBy(formname, '*.vertex.link')))
                badgen = xact.getNodesBy(formname, 'api.*.link')
                self.raises(s_exc.BadLiftValu, list, badgen)

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
            with core.xact(write=True) as xact:

                # Create some nodes and demonstrate zone/suffix behavior
                # Only FQDNs of the lowest level should be suffix
                # Only FQDNs whose domains are suffixes should be zones
                n0 = xact.addNode(formname, 'abc.vertex.link')
                n1 = xact.addNode(formname, 'def.vertex.link')
                n2 = xact.addNode(formname, 'g.def.vertex.link')
                n1 = xact.addNode(formname, 'def.vertex.link')  # form again to show g. should not make this a zone
                n3 = xact.getNodeByNdef((formname, 'vertex.link'))
                n4 = xact.getNodeByNdef((formname, 'link'))
                isneither(n0)
                isneither(n1)
                isneither(n2)
                iszone(n3)     # vertex.link should be a zone
                issuffix(n4)   # link should be a suffix

                # Make one of the FQDNs a suffix and make sure its children become zones
                n3 = xact.addNode(formname, 'vertex.link', props={'issuffix': True})
                isboth(n3)     # vertex.link should now be both because we made it a suffix
                n0 = xact.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = xact.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = xact.getNodeByNdef((formname, 'g.def.vertex.link'))
                iszone(n0)     # now a zone because vertex.link is a suffix
                iszone(n1)     # now a zone because vertex.link is a suffix
                isneither(n2)  # still neither as parent is not a suffix

                # Remove the FQDN's suffix status and make sure its children lose zone status
                n3 = xact.addNode(formname, 'vertex.link', props={'issuffix': False})
                iszone(n3)     # vertex.link should now be a zone becuase we removed its suffix status
                n0 = xact.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = xact.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = xact.getNodeByNdef((formname, 'g.def.vertex.link'))
                n4 = xact.getNodeByNdef((formname, 'link'))
                isneither(n0)  # loses zone status
                isneither(n1)  # loses zone status
                isneither(n2)  # stays the same
                issuffix(n4)   # stays the same

    def test_ipv4(self):
        formname = 'inet:ipv4'

        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:ipv4')
            ip_int = 16909060
            ip_str = '1.2.3.4'
            ip_str_enfanged = '1[.]2[.]3[.]4'

            self.eq(t.norm(ip_int), (ip_int, {}))
            self.eq(t.norm(ip_str), (ip_int, {}))
            self.eq(t.norm(ip_str_enfanged), (ip_int, {}))
            self.eq(t.repr(ip_int), ip_str)

            # Demonstrate wrap-around
            self.eq(t.norm(0x00000000 - 1), (2**32 - 1, {}))
            self.eq(t.norm(0xFFFFFFFF + 1), (0, {}))

            # Form Tests ======================================================
            with core.xact(write=True) as xact:
                valu_str = '1.2.3.4'
                valu_int = 16909060
                input_props = {'asn': 3, 'loc': 'us', 'type': 'cool', 'latlong': '-50.12345, 150.56789'}
                expected_ndef = (formname, valu_int)

                node = xact.addNode(formname, valu_str, props=input_props)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('asn'), 3)
                self.eq(node.get('loc'), 'us')
                self.eq(node.get('type'), 'cool')
                self.eq(node.get('latlong'), (-50.12345, 150.56789))

    def test_ipv6(self):
        formname = 'inet:ipv6'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:ipv6')

            self.eq(t.norm('::1'), ('::1', {}))
            self.eq(t.norm('0:0:0:0:0:0:0:1'), ('::1', {}))
            self.eq(t.norm('2001:0db8:0000:0000:0000:ff00:0042:8329'), ('2001:db8::ff00:42:8329', {}))
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

            # Form Tests ======================================================
            with core.xact(write=True) as xact:

                valu_str = '::fFfF:1.2.3.4'
                expected_ndef = (formname, valu_str.lower())
                node = xact.addNode(formname, valu_str, props={'latlong': '0,2'})
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('asn'), 0)
                self.eq(node.get('ipv4'), 16909060)
                self.eq(node.get('loc'), '??')
                self.eq(node.get('latlong'), (0.0, 2.0))

                valu_str = '::1'
                expected_ndef = (formname, valu_str)
                node = xact.addNode(formname, valu_str)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('asn'), 0)
                self.eq(node.get('loc'), '??')

    def test_mac(self):
        formname = 'inet:mac'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:mac')

            self.eq(t.norm('00:00:00:00:00:00'), ('00:00:00:00:00:00', {}))
            self.eq(t.norm('FF:ff:FF:ff:FF:ff'), ('ff:ff:ff:ff:ff:ff', {}))
            self.raises(s_exc.BadTypeValu, t.norm, ' FF:ff:FF:ff:FF:ff ')
            self.raises(s_exc.BadTypeValu, t.norm, 'GG:ff:FF:ff:FF:ff')

            # Form Tests ======================================================
            with core.xact(write=True) as xact:
                valu = '00:00:00:00:00:00'
                expected_ndef = (formname, valu)

                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('vendor'), '??')

                node = xact.addNode(formname, valu, props={'vendor': 'Cool'})
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('vendor'), 'Cool')

    def test_url(self):
        formname = 'inet:url'
        with self.getTestCore() as core:

            # Type Tests ======================================================
            t = core.model.type('inet:url')

            self.raises(s_exc.BadTypeValu, t.norm, 'http:///wat')  # No Host
            self.raises(s_exc.BadTypeValu, t.norm, 'wat')  # No Protocol

            # Form Tests ======================================================
            with core.xact(write=True) as xact:
                valu = 'https://vertexmc:hunter2@vertex.link:1337/coolthings?a=1'
                expected_ndef = (formname, valu)
                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('fqdn'), 'vertex.link')
                self.eq(node.get('passwd'), 'hunter2')
                self.eq(node.get('path'), '/coolthings?a=1')
                self.eq(node.get('port'), 1337)
                self.eq(node.get('proto'), 'https')
                self.eq(node.get('user'), 'vertexmc')

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

            self.raises(s_exc.NoSuchFunc, t.norm, 20)

            # Form Tests ======================================================
            valu = '"UnitTest"    <UnitTest@Vertex.link>'
            expected_ndef = (formname, 'unittest <unittest@vertex.link>')
            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu)
                self.eq(node.ndef, expected_ndef)
                self.eq(node.get('email'), 'unittest@vertex.link')
                #FIXME add ps:name

                xact.addNode(formname, '"UnitTest1')
                xact.addNode(formname, '"UnitTest12')

                self.len(3, list(xact.getNodesBy(formname, 'unittest', cmpr='^=')))
                self.len(2, list(xact.getNodesBy(formname, 'unittest1', cmpr='^=')))
                self.len(1, list(xact.getNodesBy(formname, 'unittest12', cmpr='^=')))

    def test_url_fqdn(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = 'Vertex.Link'
            norm_host = core.model.type('inet:fqdn').norm(host)[0]
            repr_host = core.model.type('inet:fqdn').repr(norm_host)
            self.eq(norm_host, 'vertex.link')
            self.eq(repr_host, 'vertex.link')

            self._test_types_url_behavior(t, 'fqdn', host, norm_host, repr_host)

    def test_url_ipv4(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '192[.]168.1[.]1'
            norm_host = core.model.type('inet:ipv4').norm(host)[0]
            repr_host = core.model.type('inet:ipv4').repr(norm_host)
            self.eq(norm_host, 3232235777)
            self.eq(repr_host, '192.168.1.1')

            self._test_types_url_behavior(t, 'ipv4', host, norm_host, repr_host)

    def test_url_ipv6(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:url')

            host = '::1'
            norm_host = core.model.type('inet:ipv6').norm(host)[0]
            repr_host = core.model.type('inet:ipv6').repr(norm_host)
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

class FIXME:

    def test_model_inet_srv4_types(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:tcp4', '8.8.8.8:80')
            form, pprop = s_tufo.ndef(t0)
            self.eq(pprop, 8830587502672)
            self.eq(t0[1].get('inet:tcp4:port'), 80)
            self.eq(t0[1].get('inet:tcp4:ipv4'), core.getTypeNorm('inet:ipv4', '8.8.8.8')[0])

            # 1.2.3.4:8443
            t1 = core.formTufoByProp('inet:tcp4', 1108152164603)
            self.eq(t1[1].get('inet:tcp4:port'), 8443)
            self.eq(t1[1].get('inet:tcp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            t2 = core.formTufoByProp('inet:udp4', '8.8.8.8:80')
            form, pprop = s_tufo.ndef(t2)
            self.eq(pprop, 8830587502672)
            self.eq(t2[1].get('inet:udp4:port'), 80)
            self.eq(t2[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '8.8.8.8')[0])

            # 1.2.3.4:8443
            t3 = core.formTufoByProp('inet:udp4', 1108152164603)
            self.eq(t3[1].get('inet:udp4:port'), 8443)
            self.eq(t3[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            # 1.2.3.4:8443
            t4 = core.formTufoByProp('inet:udp4', '1108152164603')
            self.eq(t4[1].get('inet:udp4:port'), 8443)
            self.eq(t4[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            # Ensure boundaries are observed
            for i in ['0', 0, '0.0.0.0:0']:
                valu, subs = core.getTypeNorm('inet:srv4', i)
                self.eq(valu, 0)
                self.eq(subs.get('port'), 0)
                self.eq(subs.get('ipv4'), 0)

            for i in ['281474976710655', 281474976710655, '255.255.255.255:65535']:
                valu, subs = core.getTypeNorm('inet:srv4', i)
                self.eq(valu, 281474976710655)
                self.eq(subs.get('port'), 0xFFFF)
                self.eq(subs.get('ipv4'), 0xFFFFFFFF)

            # Repr works as expected
            self.eq(core.getTypeRepr('inet:srv4', 0), '0.0.0.0:0')
            self.eq(core.getTypeRepr('inet:srv4', 1108152164603), '1.2.3.4:8443')
            self.eq(core.getTypeRepr('inet:srv4', 281474976710655), '255.255.255.255:65535')

            # Ensure bad input fails
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', '281474976710656')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', 281474976710656)
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:65536')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:-1')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', -1)
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', '-1')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', 'ruh roh')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:srv4', '1.2.3.4:8080:9090')

    def test_model_inet_srv6_types(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:tcp6', '[0:0:0:0:0:0:0:1]:80')
            form, pprop = s_tufo.ndef(t0)
            self.eq(pprop, '[::1]:80')
            self.eq(t0[1].get('inet:tcp6:port'), 80)
            self.eq(t0[1].get('inet:tcp6:ipv6'), '::1')

            t1 = core.formTufoByProp('inet:tcp6', '[0:0:0:0:0:3:2:1]:443')
            form, pprop = s_tufo.ndef(t1)
            self.eq(pprop, '[::3:2:1]:443')
            self.eq(t1[1].get('inet:tcp6:port'), 443)
            self.eq(t1[1].get('inet:tcp6:ipv6'), '::3:2:1')

            t2 = core.formTufoByProp('inet:udp6', '[0:0:0:0:0:3:2:1]:5000')
            form, pprop = s_tufo.ndef(t2)
            self.eq(pprop, '[::3:2:1]:5000')
            self.eq(t2[1].get('inet:udp6:port'), 5000)
            self.eq(t2[1].get('inet:udp6:ipv6'), '::3:2:1')

            self.eq(core.getTypeRepr('inet:tcp6', '[0:0:0:0:0:0:0:1]:80'), '[::1]:80')
            self.eq(core.getTypeRepr('inet:tcp6', '[::1]:80'), '[::1]:80')
            self.eq(core.getTypeRepr('inet:tcp6', '[0:0:0:0:0:3:2:1]:5000'), '[::3:2:1]:5000')

    def test_model_inet_cast_defang(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeCast('inet:defang', '1[.]2[.]3[.]4'), '1.2.3.4')

    def test_model_inet_whoisemail(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:whois:regmail', ('WOOT.COM', 'visi@vertex.LINK'))
            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))
            self.eq(node[1].get('inet:whois:regmail:email'), 'visi@vertex.link')
            self.eq(node[1].get('inet:whois:regmail:fqdn'), 'woot.com')

    def test_model_inet_postref(self):
        with self.getRamCore() as core:

            fnod = core.formTufoByProp('file:bytes', 'd41d8cd98f00b204e9800998ecf8427e')
            pnod = core.formTufoByProp('inet:web:post', ('vertex.link/user1', 'txt about a file'))

            fiden = fnod[1].get('file:bytes')
            piden = pnod[1].get('inet:web:post')

            pr0 = core.formTufoByProp('inet:web:postref', (piden, ('file:bytes', fiden)))
            pr1 = core.formTufoByProp('inet:web:postref', '(%s,file:bytes=%s)' % (piden, fiden))

            self.eq(pr0[0], pr1[0])
            self.eq(pr0[1].get('inet:web:postref:post'), piden)
            self.eq(pr0[1].get('inet:web:postref:xref'), 'file:bytes=' + fiden)
            self.eq(pr0[1].get('inet:web:postref:xref:prop'), 'file:bytes')
            self.eq(pr0[1].get('inet:web:postref:xref:strval'), fiden)
            self.eq(pr0[1].get('inet:web:postref:xref:intval'), None)

    def test_model_inet_web_mesg(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:web:mesg', ('VERTEX.link/visi', 'vertex.LINK/hehe', '20501217'), text='hehe haha')
            self.nn(node)
            self.eq(node[1].get('inet:web:mesg:from'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:mesg:to'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:web:mesg:time'), 2554848000000)
            self.eq(node[1].get('inet:web:mesg:text'), 'hehe haha')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/hehe'))

    def test_model_inet_web_memb(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:web:memb', ('VERTEX.link/visi', 'vertex.LINK/kenshoto'), joined='20501217')

            self.nn(node)

            self.eq(node[1].get('inet:web:memb:joined'), 2554848000000)
            self.eq(node[1].get('inet:web:memb:acct'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:memb:group'), 'vertex.link/kenshoto')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:group', 'vertex.link/kenshoto'))

    def test_model_whois_contact(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:whois:contact', '(woot.com@20501217,admin)')

            self.eq(len(core.eval('inet:fqdn="woot.com"')), 1)
            self.eq(len(core.eval('inet:whois:rec="woot.com@20501217"')), 1)
            self.eq(len(core.eval('inet:whois:contact:rec="woot.com@20501217"')), 1)

            props = {'url': 'http://woot.com/hehe', 'whois:fqdn': 'blah.com'}
            node = core.formTufoByProp('inet:whois:contact', ('woot.com@2015', 'registrar'), **props)
            self.eq(node[1].get('inet:whois:contact:url'), 'http://woot.com/hehe')
            self.eq(node[1].get('inet:whois:contact:whois:fqdn'), 'blah.com')

            self.nn(core.getTufoByProp('inet:fqdn', 'blah.com'))
            self.nn(core.getTufoByProp('inet:url', 'http://woot.com/hehe'))

    def test_model_inet_whois_recns(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:whois:rec', 'woot.com@20501217')
            form, pprop = s_tufo.ndef(node)
            node = core.formTufoByProp('inet:whois:recns', ['ns1.woot.com', pprop])
            self.eq(node[1].get('inet:whois:recns:ns'), 'ns1.woot.com')
            self.eq(node[1].get('inet:whois:recns:rec'), pprop)
            self.eq(node[1].get('inet:whois:recns:rec:fqdn'), 'woot.com')
            self.eq(node[1].get('inet:whois:recns:rec:asof'), 2554848000000)
            nodes = core.eval('inet:whois:recns:rec:fqdn=woot.com')
            self.eq(node[0], nodes[0][0])
            nodes = core.eval('inet:whois:rec:fqdn=woot.com inet:whois:rec->inet:whois:recns:rec')
            self.eq(len(nodes), 1)
            self.eq(node[0], nodes[0][0])

    def test_model_inet_web_actref(self):
        with self.getRamCore() as core:

            fnod = core.formTufoByProp('file:bytes', 'd41d8cd98f00b204e9800998ecf8427e')
            anod = core.formTufoByProp('inet:web:action', '*', act='laughed', acct='vertex.link/user1')

            fiden = fnod[1].get('file:bytes')
            aiden = anod[1].get('inet:web:action')

            ar0 = core.formTufoByProp('inet:web:actref', (aiden, ('file:bytes', fiden)))
            ar1 = core.formTufoByProp('inet:web:actref', '(%s,file:bytes=%s)' % (aiden, fiden))

            self.eq(ar0[0], ar1[0])
            self.eq(ar0[1].get('inet:web:actref:act'), aiden)
            self.eq(ar0[1].get('inet:web:actref:xref'), 'file:bytes=' + fiden)
            self.eq(ar0[1].get('inet:web:actref:xref:prop'), 'file:bytes')
            self.eq(ar0[1].get('inet:web:actref:xref:strval'), fiden)
            self.eq(ar0[1].get('inet:web:actref:xref:intval'), None)

    def test_model_inet_chprofile(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:web:chprofile', '*', acct='vertex.link/pennywise', ipv4='1.2.3.4',
                                     pv='inet:web:acct:name=bob gray', time='201710020800')
            self.eq(t0[1].get('inet:web:chprofile:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:chprofile:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:chprofile:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:chprofile:ipv4'), 0x01020304)
            self.none(t0[1].get('inet:web:chprofile:acct:ipv6'))
            self.eq(t0[1].get('inet:web:chprofile:time'), 1506931200000)
            self.eq(t0[1].get('inet:web:chprofile:pv'), 'inet:web:acct:name=bob gray')
            self.eq(t0[1].get('inet:web:chprofile:pv:prop'), 'inet:web:acct:name')
            self.eq(t0[1].get('inet:web:chprofile:pv:strval'), 'bob gray')
            self.none(t0[1].get('inet:web:chprofile:pv:intval'))

            t1 = core.formTufoByProp('inet:web:chprofile', '*', acct='vertex.link/pennywise', ipv4='1.2.3.4',
                                     pv='inet:web:acct:seen:min=2014', time='201710020800')
            self.eq(t1[1].get('inet:web:chprofile:pv'), 'inet:web:acct:seen:min=2014/01/01 00:00:00.000')
            self.eq(t1[1].get('inet:web:chprofile:pv:prop'), 'inet:web:acct:seen:min')
            self.eq(t1[1].get('inet:web:chprofile:pv:intval'), 1388534400000)
            self.none(t1[1].get('inet:web:chprofile:pv:strval'))

            # We require the account to be present
            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:chprofile', '*')

    def test_model_inet_postref_postmissingprops(self):
        with self.getRamCore() as core:

            postref_tufo = core.formTufoByProp('inet:web:postref', (('vertex.link/user', 'mypost 0.0.0.0'), ('inet:ipv4', 0)))
            self.nn(core.getTufoByProp('inet:web:post', ('vertex.link/user', 'mypost 0.0.0.0')))

            self.eq(postref_tufo[1]['tufo:form'], 'inet:web:postref')
            self.eq(postref_tufo[1]['inet:web:postref'], '804ec63392f4ea031bb3fd004dee209d')
            self.eq(postref_tufo[1]['inet:web:postref:post'], '68bc4607f0518963165536921d6e86fa')
            self.eq(postref_tufo[1]['inet:web:postref:xref'], 'inet:ipv4=0.0.0.0')
            self.eq(postref_tufo[1]['inet:web:postref:xref:prop'], 'inet:ipv4')
            self.eq(postref_tufo[1]['inet:web:postref:xref:intval'], 0)

            post_tufo = core.formTufoByProp('inet:web:post', ('vertex.link/user', 'mypost 0.0.0.0'))
            # Ensure we got the deconflicted node that was already made, not a new node
            self.notin('.new', post_tufo[1])
            self.eq(post_tufo[1]['inet:web:post'], postref_tufo[1]['inet:web:postref:post'])
            # Ensure that subs on the autoadd node are formed properly
            self.eq(post_tufo[1].get('inet:web:post:acct'), 'vertex.link/user')
            self.eq(post_tufo[1].get('inet:web:post:text'), 'mypost 0.0.0.0')
            # Ensure multiple subs were made into nodes
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/user'))
            self.nn(core.getTufoByProp('inet:user', 'user'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:fqdn', 'link'))

    def test_model_inet_addr(self):
        with self.getRamCore() as core:

            # ipv4
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4')
            self.eq(valu, 'tcp://1.2.3.4')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            # ipv4:port
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4:80')
            self.eq(valu, 'tcp://1.2.3.4:80')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['port'], 80)
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('host'))

            # DWIM IPv6...
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4:80')
            self.eq(valu, 'tcp://1.2.3.4:80')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['port'], 80)
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('host'))

            # ipv6 port
            valu, subs = core.getTypeNorm('inet:addr', '[FF::56]:99')
            self.eq(valu, 'tcp://[ff::56]:99')
            self.eq(subs['port'], 99)
            self.eq(subs['ipv6'], 'ff::56')
            self.eq(subs['proto'], 'tcp')
            self.none(subs.get('ipv4'))
            self.none(subs.get('host'))

            # unadorned syntax...
            valu, subs = core.getTypeNorm('inet:addr', 'FF::56')
            self.eq(valu, 'tcp://[ff::56]')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], 'ff::56')
            self.none(subs.get('ipv4'))
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            valu, subs = core.getTypeNorm('inet:addr', '[::ffff:1.2.3.4]:8080')
            self.eq(valu, 'tcp://1.2.3.4:8080')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.eq(subs['ipv4'], 16909060,)
            self.eq(subs['port'], 8080)
            self.none(subs.get('host'))
            # Renorm the primary property (which no longer uses the ipv6 syntax
            nvalu, nsubs = core.getTypeNorm('inet:addr', valu)
            self.eq(nvalu, valu)
            self.eq(nsubs, subs)

            valu, subs = core.getTypeNorm('inet:addr', '::ffff:1.2.3.4')
            self.eq(valu, 'tcp://1.2.3.4')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.eq(subs['ipv4'], 16909060,)
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            host = s_common.guid('thx')
            valu, subs = core.getTypeNorm('inet:addr', 'HosT://%s:1138/' % host)
            self.eq(valu, 'host://%s:1138' % host)
            self.eq(subs['proto'], 'host')
            self.eq(subs['host'], host)
            self.eq(subs['port'], 1138)
            self.none(subs.get('ipv4'))
            self.none(subs.get('ipv6'))

            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://[FF::56]:99')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://8.6.7.5:309')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:addr', 'tcp://8.6.7.256:309')
            self.raises(s_exc.BadTypeValu, core.getTypeNorm, 'inet:addr', 'giggles://float.down.here/')

            host = s_common.guid()
            node = core.formTufoByProp('inet:client', 'host://%s' % (host,))
            self.eq(node[1]['inet:client:host'], host)
            self.eq(node[1]['inet:client:proto'], 'host')
            self.nn(core.getTufoByProp('it:host', host))

    def test_model_inet_server(self):

        with self.getRamCore() as core:

            valu, subs = core.getTypeNorm('inet:server', 'udp://1.2.3.4:80')
            self.eq(valu, 'udp://1.2.3.4:80')
            self.eq(subs['port'], 80)
            self.eq(subs['proto'], 'udp')
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')

    def test_model_inet_servfile(self):

        with self.getRamCore() as core:

            iden = s_common.guid()
            props = {'seen:min': 10, 'seen:max': 20}
            node = core.formTufoByProp('inet:servfile', ('tcp://1.2.3.4:443', iden), **props)
            self.eq(node[1]['inet:servfile:file'], iden)
            self.eq(node[1]['inet:servfile:server'], 'tcp://1.2.3.4:443')
            self.eq(node[1]['inet:servfile:server:port'], 443)
            self.eq(node[1]['inet:servfile:server:proto'], 'tcp')
            self.eq(node[1]['inet:servfile:server:ipv4'], 0x01020304)
            self.eq(node[1]['inet:servfile:server:ipv6'], '::ffff:1.2.3.4')
            self.eq(node[1]['inet:servfile:seen:min'], 10)
            self.eq(node[1]['inet:servfile:seen:max'], 20)

    def test_model_inet_download(self):

        with self.getRamCore() as core:

            iden = s_common.guid()
            props = {'time': 10, 'file': iden, 'server': 'tcp://1.2.3.4:80', 'client': 'tcp://5.6.7.8'}
            node = core.formTufoByProp('inet:download', '*', **props)
            self.eq(node[1].get('inet:download:time'), 10)
            self.eq(node[1].get('inet:download:file'), iden)
            self.eq(node[1].get('inet:download:server:proto'), 'tcp')
            self.eq(node[1].get('inet:download:server:port'), 80)
            self.eq(node[1].get('inet:download:server:ipv4'), 0x01020304)
            self.eq(node[1].get('inet:download:client:proto'), 'tcp')
            self.eq(node[1].get('inet:download:client:ipv4'), 0x05060708)

    def test_model_inet_iface(self):

        with self.getRamCore() as core:

            info = {
                'host': '*',
                'ipv6': 'ff::00',
                'ipv4': '1.2.3.4',
                'phone': 12345678910,
                'mac': 'ff:00:ff:00:ff:00',
                'wifi:ssid': 'hehe haha',
                'wifi:bssid': '00:ff:00:ff:00:ff',
                'mob:imei': 12345678901234,
                'mob:imsi': 12345678901234,
            }

            node = core.formTufoByProp('inet:iface', info)

            self.nn(core.getTufoByProp('it:host', node[1].get('inet:iface:host')))
            self.nn(core.getTufoByProp('inet:mac', node[1].get('inet:iface:mac')))
            self.nn(core.getTufoByProp('inet:ipv4', node[1].get('inet:iface:ipv4')))
            self.nn(core.getTufoByProp('inet:ipv6', node[1].get('inet:iface:ipv6')))
            self.nn(core.getTufoByProp('tel:phone', node[1].get('inet:iface:phone')))
            self.nn(core.getTufoByProp('inet:mac', node[1].get('inet:iface:wifi:bssid')))
            self.nn(core.getTufoByProp('inet:wifi:ssid', node[1].get('inet:iface:wifi:ssid')))
            self.nn(core.getTufoByProp('tel:mob:imei', node[1].get('inet:iface:mob:imei')))
            self.nn(core.getTufoByProp('tel:mob:imsi', node[1].get('inet:iface:mob:imsi')))

    def test_model_inet_http(self):

        with self.getRamCore() as core:

            tick = 0x01010101
            flow = s_common.guid()
            host = s_common.guid()
            body = s_common.guid()

            props = {
                'flow': flow,
                'time': tick,
                'host': host,
                'method': 'HeHe',
                'path': '/foo/bar',
                'query': 'baz=faz&woot=haha',
                'body': body,
            }

            requ = core.formTufoByProp('inet:http:request', '*', **props)

            iden = requ[1].get('inet:http:request')

            self.eq(requ[1]['inet:http:request:flow'], flow)
            self.eq(requ[1]['inet:http:request:time'], tick)
            self.eq(requ[1]['inet:http:request:host'], host)
            self.eq(requ[1]['inet:http:request:method'], 'HeHe')
            self.eq(requ[1]['inet:http:request:path'], '/foo/bar')
            self.eq(requ[1]['inet:http:request:query'], 'baz=faz&woot=haha')

            node = core.formTufoByProp('inet:http:reqhead', (iden, ('User-Agent', 'BillyBob')))

            self.eq(node[1].get('inet:http:reqhead:request'), iden)
            self.eq(node[1].get('inet:http:reqhead:header:name'), 'user-agent')
            self.eq(node[1].get('inet:http:reqhead:header:value'), 'BillyBob')

            node = core.getTufoByProp('inet:http:header', ('User-Agent', 'BillyBob'))
            self.eq(node[1].get('inet:http:header:name'), 'user-agent')
            self.eq(node[1].get('inet:http:header:value'), 'BillyBob')

            node = core.formTufoByProp('inet:http:reqhead', (iden, ('Host', 'vertex.ninja')))
            self.eq(node[1].get('inet:http:reqhead:request'), iden)
            self.eq(node[1].get('inet:http:reqhead:header:name'), 'host')
            self.eq(node[1].get('inet:http:reqhead:header:value'), 'vertex.ninja')

            node = core.getTufoByProp('inet:http:header', ('Host', 'vertex.ninja'))
            self.eq(node[1].get('inet:http:header:name'), 'host')
            self.eq(node[1].get('inet:http:header:value'), 'vertex.ninja')

            node = core.formTufoByProp('inet:http:reqparam', (iden, ('baz', 'faz')))
            self.eq(node[1].get('inet:http:reqparam:request'), iden)
            self.eq(node[1].get('inet:http:reqparam:param:name'), 'baz')
            self.eq(node[1].get('inet:http:reqparam:param:value'), 'faz')

            props = {
                'time': tick,
                'host': host,
                'request': iden,
                'code': 31337,
                'reason': 'too leet',
                'flow': flow,
                'body': body,
            }

            resp = core.formTufoByProp('inet:http:response', '*', **props)
            self.eq(resp[1]['inet:http:response:request'], iden)
            self.eq(resp[1]['inet:http:response:flow'], flow)
            self.eq(resp[1]['inet:http:response:time'], tick)
            self.eq(resp[1]['inet:http:response:host'], host)
            self.eq(resp[1]['inet:http:response:code'], 31337)
            self.eq(resp[1]['inet:http:response:reason'], 'too leet')
            self.eq(resp[1]['inet:http:response:body'], body)

            ridn = resp[1].get('inet:http:response')
