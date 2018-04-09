# -*- coding: UTF-8 -*-
import synapse.common as s_common
import synapse.lib.time as s_time
import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types


from synapse.tests.common import *

class InetModelTest(SynTest):

    def test_model_type_inet_url(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:url', 'newp')
        self.eq(tlib.getTypeNorm('inet:url', 'http://WoOt.com/HeHe')[0], 'http://woot.com/HeHe')
        self.eq(tlib.getTypeNorm('inet:url', 'HTTP://WoOt.com/HeHe')[0], 'http://woot.com/HeHe')
        self.eq(tlib.getTypeNorm('inet:url', 'HttP://Visi:Secret@WoOt.com/HeHe&foo=10')[0],
                'http://Visi:Secret@woot.com/HeHe&foo=10')

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:url', 'newp')
        self.eq(tlib.getTypeParse('inet:url', 'http://WoOt.com/HeHe')[0], 'http://woot.com/HeHe')
        self.eq(tlib.getTypeParse('inet:url', 'HTTP://WoOt.com/HeHe')[0], 'http://woot.com/HeHe')
        self.eq(tlib.getTypeParse('inet:url', 'HttP://Visi:Secret@WoOt.com/HeHe&foo=10')[0],
                'http://Visi:Secret@woot.com/HeHe&foo=10')

        self.eq(tlib.getTypeRepr('inet:url', 'http://woot.com/HeHe'), 'http://woot.com/HeHe')

    def test_model_typeinet_ipv4(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeNorm('inet:ipv4', 0x01020304)[0], 0x01020304)
        self.eq(tlib.getTypeNorm('inet:ipv4', '0x01020304')[0], 0x01020304)
        self.eq(tlib.getTypeParse('inet:ipv4', '1.2.3.4')[0], 0x01020304)
        self.eq(tlib.getTypeRepr('inet:ipv4', 0x01020304), '1.2.3.4')

    def tes_model_type_inet_tcp4(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeNorm('inet:tcp4', '1.2.3.4:2')[0], 0x010203040002)
        self.eq(tlib.getTypeNorm('inet:tcp4', 0x010203040002)[0], 0x010203040002)

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:tcp4', 'newp')
        self.eq(tlib.getTypeParse('inet:tcp4', '1.2.3.4:2')[0], 0x010203040002)

        self.eq(tlib.getTypeRepr('inet:tcp4', 0x010203040002), '1.2.3.4:2')

    def test_model_type_inet_udp4(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeNorm('inet:udp4', '1.2.3.4:2')[0], 0x010203040002)
        self.eq(tlib.getTypeNorm('inet:udp4', 0x010203040002)[0], 0x010203040002)

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:udp4', 'newp')
        self.eq(tlib.getTypeParse('inet:udp4', '1.2.3.4:2')[0], 0x010203040002)

        self.eq(tlib.getTypeRepr('inet:udp4', 0x010203040002), '1.2.3.4:2')

    def test_model_type_inet_port(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:port', '70000')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:port', 0xffffffff)

        self.eq(tlib.getTypeNorm('inet:port', 20)[0], 20)

    def test_model_type_inet_mac(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:mac', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:mac', 'newp')

        self.eq(tlib.getTypeNorm('inet:mac', 'FF:FF:FF:FF:FF:FF')[0], 'ff:ff:ff:ff:ff:ff')
        self.eq(tlib.getTypeParse('inet:mac', 'FF:FF:FF:FF:FF:FF')[0], 'ff:ff:ff:ff:ff:ff')
        self.eq(tlib.getTypeRepr('inet:mac', 'ff:ff:ff:ff:ff:ff'), 'ff:ff:ff:ff:ff:ff')

    def test_model_type_inet_email(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:email', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:email', 'newp')

        self.eq(tlib.getTypeParse('inet:email', 'ViSi@Woot.Com')[0], 'visi@woot.com')

        self.eq(tlib.getTypeNorm('inet:email', 'ViSi@Woot.Com')[0], 'visi@woot.com')

        self.eq(tlib.getTypeRepr('inet:email', 'visi@woot.com'), 'visi@woot.com')

    def test_model_type_inet_ipv6(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'inet:ipv6', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[fffffffffffffffffffffffff::2]:80')

        self.eq(tlib.getTypeParse('inet:ipv6', 'AF:00::02')[0], 'af::2')
        self.eq(tlib.getTypeNorm('inet:ipv6', 'AF:00::02')[0], 'af::2')
        self.eq(tlib.getTypeRepr('inet:ipv6', 'af::2'), 'af::2')

        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8::1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')

        # Specific examples given in RFC5952
        # Section 1
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:0db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8::1:0:0:1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8::0:1:0:0:1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:0db8::1:0:0:1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:1::1')[0], '2001:db8::1:0:0:1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:DB8:0:0:1::1')[0], '2001:db8::1:0:0:1')

        # Section 2.1
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:DB8:0:0:1:0000:0000:1')[0], '2001:db8::1:0:0:1')

        # Section 2.2
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:ipv6', '::1::')

        # Section 4.1
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:0db8::0001')[0], '2001:db8::1')

        # Section 4.2.1
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:0:0:2:1')[0], '2001:db8::2:1')

        # Section 4.2.2
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')

        # Section 4.2.3
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:0:0:1:0:0:0:1')[0], '2001:0:0:1::1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:1:0:0:1')[0], '2001:db8::1:0:0:1')

        self.eq(tlib.getTypeNorm('inet:ipv6', '::ffff:1.2.3.4')[0], '::ffff:1.2.3.4')

        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8::0:1')[0], '2001:db8::1')
        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:0:0:2:1')[0], '2001:db8::2:1')

        self.eq(tlib.getTypeNorm('inet:ipv6', '2001:db8::')[0], '2001:db8::')

        self.eq(tlib.getTypeRepr('inet:srv6', '[af::2]:80'), '[af::2]:80')
        self.eq(tlib.getTypeParse('inet:srv6', '[AF:00::02]:80')[0], '[af::2]:80')
        self.eq(tlib.getTypeNorm('inet:srv6', '[AF:00::02]:80')[0], '[af::2]:80')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[AF:00::02]:999999')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[AF:00::02]:-1')

    def test_model_type_inet_cidr(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:cidr4', '1.2.3.0/33')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'inet:cidr4', '1.2.3.0/-1')

        self.eq(tlib.getTypeNorm('inet:cidr4', '1.2.3.0/24'), ('1.2.3.0/24', {'ipv4': 16909056, 'mask': 24}))
        self.eq(tlib.getTypeRepr('inet:cidr4', '1.2.3.0/24'), '1.2.3.0/24')

    def test_model_inet_email(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:email', 'visi@vertex.link')
            self.eq(t0[1].get('inet:email:user'), 'visi')
            self.eq(t0[1].get('inet:email:fqdn'), 'vertex.link')

    def test_model_inet_passwd(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:passwd', 'secret')
            self.eq(t0[1].get('inet:passwd:md5'), '5ebe2294ecd0e0f08eab7690d2a6ee69')
            self.eq(t0[1].get('inet:passwd:sha1'), 'e5e9fa1ba31ecd1ae84f75caaa474f3a663f05f4')
            self.eq(t0[1].get('inet:passwd:sha256'), '2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b')

    def test_model_inet_mac(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:mac', '00:01:02:03:04:05')
            self.eq(t0[1].get('inet:mac:vendor'), '??')

            t1 = core.formTufoByProp('inet:mac', 'FF:ee:dd:cc:bb:aa', vendor='woot')
            self.eq(t1[1].get('inet:mac'), 'ff:ee:dd:cc:bb:aa')
            self.eq(t1[1].get('inet:mac:vendor'), 'woot')

    def test_model_inet_ipv4(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:ipv4', '16909060')
            self.eq(t0[1].get('inet:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:ipv4:asn'), -1)

            self.raises(BadTypeValu, core.formTufoByProp, 'inet:ipv4', [])

    def test_model_inet_ipv6(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:ipv6', '0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:ipv6'), '::1')
            self.eq(t0[1].get('inet:ipv6:asn'), -1)

            self.eq(core.getTypeRepr('inet:ipv6', '0:0:0:0:0:0:0:1'), '::1')
            self.eq(core.getTypeRepr('inet:ipv6', '::1'), '::1')

    def test_model_inet_cidr4(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:cidr4', '1.2.3.4/24')

            self.eq(t0[1].get('inet:cidr4'), '1.2.3.0/24')
            self.eq(t0[1].get('inet:cidr4:mask'), 24)
            self.eq(t0[1].get('inet:cidr4:ipv4'), 0x01020300)

    def test_model_inet_asnet4(self):

        with self.getRamCore() as core:

            t0 = core.formTufoByProp('inet:asnet4', '54959/1.2.3.4-5.6.7.8')

            self.eq(t0[1].get('inet:asnet4:asn'), 54959)
            self.eq(t0[1].get('inet:asnet4:net4'), '1.2.3.4-5.6.7.8')
            self.eq(t0[1].get('inet:asnet4:net4:min'), 0x01020304)
            self.eq(t0[1].get('inet:asnet4:net4:max'), 0x05060708)

            self.nn(core.getTufoByProp('inet:asn', 54959))
            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            self.nn(core.getTufoByProp('inet:ipv4', 0x05060708))

            o1 = core.formTufoByProp('ou:org', '*', alias='vertex')
            _, o1pprop = s_tufo.ndef(o1)
            t1 = core.formTufoByProp('inet:asn', 12345)
            self.none(t1[1].get('inet:asn:owner'))
            t1 = core.setTufoProps(t1, owner='$vertex')
            self.eq(t1[1].get('inet:asn:owner'), o1pprop)
            # TODO: Uncomment when we have a global alias resolver in place.
            # self.nn(core.getTufoByProp('ou:alias', 'vertex'))
            t2 = core.formTufoByProp('inet:asn', 12346, owner='$vertex')
            self.eq(t2[1].get('inet:asn:owner'), o1pprop)
            # Lift asn's by owner with guid resolver syntax
            nodes = core.eval('inet:asn:owner=$vertex')
            self.eq(len(nodes), 2)

    def test_model_inet_fqdn(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:fqdn', 'com', sfx=1)
            t1 = core.formTufoByProp('inet:fqdn', 'woot.com')

            self.eq(t0[1].get('inet:fqdn:host'), 'com')
            self.eq(t0[1].get('inet:fqdn:domain'), None)
            self.eq(t0[1].get('inet:fqdn:sfx'), 1)
            self.eq(t0[1].get('inet:fqdn:zone'), 0)

            self.eq(t1[1].get('inet:fqdn:host'), 'woot')
            self.eq(t1[1].get('inet:fqdn:domain'), 'com')
            self.eq(t1[1].get('inet:fqdn:sfx'), 0)
            self.eq(t1[1].get('inet:fqdn:zone'), 1)

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
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '281474976710656')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', 281474976710656)
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:65536')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:-1')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', -1)
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '-1')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', 'ruh roh')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '1.2.3.4:8080:9090')

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

    def test_model_inet_fqdn_unicode(self):

        with self.getRamCore() as core:
            prop = 'inet:fqdn'
            idna_valu = 'xn--tst-6la.xn--xampl-3raf.link'
            unicode_valu = 'tèst.èxamplè.link'
            unicode_cap_valu = 'tèst.èxaMplè.link'
            parents = (
                    ('xn--xampl-3raf.link', {'inet:fqdn:host': 'xn--xampl-3raf', 'inet:fqdn:domain': 'link', 'inet:fqdn:zone': 1, 'inet:fqdn:sfx': 0}),
                    ('link', {'inet:fqdn:host': 'link', 'inet:fqdn:domain': None, 'inet:fqdn:zone': 0, 'inet:fqdn:sfx': 1}),
            )
            idna_tufo = core.formTufoByProp(prop, idna_valu)
            self.eq(idna_tufo[1].get('inet:fqdn:host'), 'xn--tst-6la')
            self.eq(idna_tufo[1].get('inet:fqdn:domain'), 'xn--xampl-3raf.link')
            self.eq(idna_tufo[1].get('inet:fqdn:zone'), 0)
            self.eq(idna_tufo[1].get('inet:fqdn:sfx'), 0)

            for parent_fqdn, parent_props in parents:
                parent_tufo = core.getTufoByProp(prop, parent_fqdn)
                for key in parent_props:
                    self.eq(parent_tufo[1].get(key), parent_props[key])

            idna_tufo = core.formTufoByProp(prop, idna_valu)
            unicode_tufo = core.formTufoByProp(prop, unicode_valu)
            unicode_cap_tufo = core.formTufoByProp(prop, unicode_cap_valu)
            self.eq(unicode_tufo, idna_tufo)
            self.eq(unicode_tufo, unicode_cap_tufo)

        with self.getRamCore() as core:
            prop = 'inet:web:acct'
            valu = '%s/%s' % ('xn--tst-6la.xn--xampl-3raf.link', 'user')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:web:acct:site'), 'xn--tst-6la.xn--xampl-3raf.link')
            self.eq(tufo[1].get('inet:web:acct'), 'tèst.èxamplè.link/user')
            idna_valu = 'xn--tst-6la.xn--xampl-3raf.link'

        with self.getRamCore() as core:
            prop = 'inet:email'
            valu = '%s@%s' % ('user', 'tèst.èxamplè.link')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:email:fqdn'), 'xn--tst-6la.xn--xampl-3raf.link')
            self.eq(tufo[1].get('inet:email'), 'user@xn--tst-6la.xn--xampl-3raf.link')

        with self.getRamCore() as core:
            prop = 'inet:url'
            valu = '%s://%s/%s' % ('https', 'xn--tst-6la.xn--xampl-3raf.link', 'things')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:url'), 'https://xn--tst-6la.xn--xampl-3raf.link/things') # hostpart is not normed in inet:url

    def test_model_inet_fqdn_idna(self):

        with self.getRamCore() as core:
            prop = 'inet:fqdn'
            valu = 'xn--lskfjaslkdfjaslfj.link'

            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1][prop], valu)

            tufo = core.getTufoByProp(prop, valu)
            self.eq(tufo[1][prop], valu)

            # Catch invalid IDNA error and just return the raw data
            self.eq(core.getTypeRepr(prop, tufo[1][prop]), valu)
            self.eq(core.getPropRepr(prop, tufo[1][prop]), valu)

    def test_model_inet_fqdn_set_sfx(self):
        with self.getRamCore() as core:
            tufo = core.formTufoByProp('inet:fqdn', 'abc.dyndns.com') # abc.dyndns.com - zone=0 sfx=0, dyndns.com - zone=1 sfx=0, com - zone=0 sfx=1
            self.eq(tufo[1].get('inet:fqdn:host'), 'abc')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0)
            tufo = core.formTufoByProp('inet:fqdn', 'def.dyndns.com') # def.dyndns.com - zone=0 sfx=0
            self.eq(tufo[1].get('inet:fqdn:host'), 'def')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0)
            tufo = core.formTufoByProp('inet:fqdn', 'g.def.dyndns.com') # g.def.dyndns.com - zone=0 sfx=0, def.dyndns.com - zone=0 sfx=0
            self.eq(tufo[1].get('inet:fqdn:host'), 'g')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0)
            tufo = core.getTufoByProp('inet:fqdn', 'def.dyndns.com') # def.dyndns.com - zone=0 sfx=0 - adding g.def does not make def a zone
            self.eq(tufo[1].get('inet:fqdn:host'), 'def')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0)
            tufo = core.getTufoByProp('inet:fqdn', 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'dyndns')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 1)
            tufo = core.getTufoByProp('inet:fqdn', 'com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'com')
            self.eq(tufo[1].get('inet:fqdn:domain'), None)
            self.eq(tufo[1].get('inet:fqdn:sfx'), 1)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0)

            # make dyndns.com a suffix
            tufo = core.getTufoByProp('inet:fqdn', 'dyndns.com')
            tufo = core.setTufoProp(tufo, 'sfx', 1)
            self.eq(tufo[1].get('inet:fqdn:host'), 'dyndns')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 1)
            self.eq(tufo[1].get('inet:fqdn:zone'), 1) # should still be a zone after sfx set to 1

            # assert that child fqdns are properly updated
            tufo = core.getTufoByProp('inet:fqdn', 'abc.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'abc')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 1) # now a zone because dyndns.com is a suffix
            tufo = core.getTufoByProp('inet:fqdn', 'def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'def')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 1) # now a zone because dyndns.com is a suffix
            tufo = core.getTufoByProp('inet:fqdn', 'g.def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'g')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0) # should remain zone=0 sfx=0 because its parent is not a sfx

            # make dyndns.com not a suffix
            tufo = core.getTufoByProp('inet:fqdn', 'dyndns.com')
            tufo = core.setTufoProp(tufo, 'sfx', 0)
            self.eq(tufo[1].get('inet:fqdn:host'), 'dyndns')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 1) # should still be a zone after sfx set to 0

            # assert that child fqdns are properly updated
            tufo = core.getTufoByProp('inet:fqdn', 'abc.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'abc')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0) # no longer a zone because dyndns.com is not a sfx
            tufo = core.getTufoByProp('inet:fqdn', 'def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'def')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0) # no longer a zone because dyndns.com is not a sfx
            tufo = core.getTufoByProp('inet:fqdn', 'g.def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:host'), 'g')
            self.eq(tufo[1].get('inet:fqdn:domain'), 'def.dyndns.com')
            self.eq(tufo[1].get('inet:fqdn:sfx'), 0)
            self.eq(tufo[1].get('inet:fqdn:zone'), 0) # should remain zone=0 sfx=0 because its parent is not a sfx

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

    def test_model_inet_url_fields(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:url', 'HTTP://visi:hehe@www.vertex.link:9999/')
            self.eq(node[1].get('inet:url:port'), 9999)
            self.eq(node[1].get('inet:url:user'), 'visi')
            self.eq(node[1].get('inet:url:passwd'), 'hehe')
            self.eq(node[1].get('inet:url:fqdn'), 'www.vertex.link')

            node = core.formTufoByProp('inet:url', 'HTTP://www.vertex.link/')
            self.eq(node[1].get('inet:url:port'), 80)

            node = core.formTufoByProp('inet:url', 'HTTP://1.2.3.4/')
            self.eq(node[1].get('inet:url:ipv4'), 0x01020304)

    def test_model_inet_web_acct(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:web:acct', 'vertex.link/person1',
                                     **{'name': 'ካሳር',
                                        'name:en': 'caesar',
                                        'realname': 'Брут',    # uppercased Cyrllic
                                        'realname:en': 'brutus',
                                        })
            self.eq(t0[1].get('inet:web:acct'), 'vertex.link/person1')
            self.eq(t0[1].get('inet:web:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:acct:user'), 'person1')
            t0 = core.setTufoProp(t0, 'loc', 'HAHA')
            self.eq(t0[1].get('inet:web:acct:loc'), 'haha')
            self.eq(t0[1].get('inet:web:acct:name'), 'ካሳር')
            self.eq(t0[1].get('inet:web:acct:name:en'), 'caesar')
            self.eq(t0[1].get('inet:web:acct:realname'), 'брут')  # lowercased Cyrllic
            self.eq(t0[1].get('inet:web:acct:realname:en'), 'brutus')

    def test_model_inet_web_post(self):

        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            iden = node0[1].get('inet:web:post')

            node1 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'whos there'),
                                        time='20141217010102', replyto=iden)

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))

            self.eq(node0[1].get('inet:web:post:acct:user'), 'visi')
            self.eq(node1[1].get('inet:web:post:acct:user'), 'visi')

            self.eq(node0[1].get('inet:web:post:acct:site'), 'vertex.link')
            self.eq(node1[1].get('inet:web:post:acct:site'), 'vertex.link')

            self.eq(node0[1].get('inet:web:post'), node1[1].get('inet:web:post:replyto'))
            self.none(node0[1].get('inet:web:post:repost'))
            self.none(node1[1].get('inet:web:post:repost'))

            repost = node1[1].get('inet:web:post')
            node2 = core.formTufoByProp('inet:web:post', ('vertex.link/pennywise', 'whos there'),
                                        time='201710091541', repost=repost)
            self.eq(node2[1].get('inet:web:post:acct'), 'vertex.link/pennywise')
            self.eq(node2[1].get('inet:web:post:text'), 'whos there')
            self.eq(node2[1].get('inet:web:post:repost'), repost)
            self.none(node2[1].get('inet:web:replyto'))

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

    def test_model_inet_web_group(self):
        with self.getRamCore() as core:
            from pprint import pprint
            iden = guid()
            node = core.formTufoByProp('inet:web:group',
                                       ('vertex.link', '1234'),
                                       **{'name': 'brjálaður muffins',
                                          'name:en': 'crazy cupcakes',
                                          'url': 'http://vertex.link/g/1234',
                                          'desc': 'Crazy cupcakes players union',
                                          'avatar': iden,
                                          'webpage': 'http://muffinman.com/hehe',
                                          'loc': 'Reykjavík',
                                          'latlong': '64.0788707,-21.8369301',
                                          'signup': '2016',
                                          'signup:ipv4': '1.2.3.4',
                                          'signup:ipv6': '0:0:0:0:0:0:0:1',
                                          'seen:min': '2016',
                                          'seen:max': '2018'
                                          })
            self.nn(node)
            _, pprop = s_tufo.ndef(node)
            self.eq(pprop, 'vertex.link/1234')
            props = s_tufo.props(node)
            self.eq(props.get('avatar'), iden)
            self.eq(props.get('desc'), 'Crazy cupcakes players union')
            self.eq(props.get('id'), '1234')
            self.eq(props.get('latlong'), '64.0788707,-21.8369301')
            self.eq(props.get('loc'), 'reykjavík')
            self.eq(props.get('name'), 'brjálaður muffins')
            self.eq(props.get('name:en'), 'crazy cupcakes')
            self.eq(props.get('seen:max'), 1514764800000,)
            self.eq(props.get('seen:min'), 1451606400000,)
            self.eq(props.get('signup'), 1451606400000,)
            self.eq(props.get('signup:ipv4'), 16909060)
            self.eq(props.get('signup:ipv6'), '::1')
            self.eq(props.get('site'), 'vertex.link')
            self.eq(props.get('url'), 'http://vertex.link/g/1234')
            self.eq(props.get('webpage'), 'http://muffinman.com/hehe')
            # Validate autoadds
            self.nn(core.getTufoByProp('inet:group', '1234'))
            self.nn(core.getTufoByProp('inet:group', 'crazy cupcakes'))
            self.nn(core.getTufoByProp('inet:group', 'brjálaður muffins'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:fqdn', 'muffinman.com'))
            self.nn(core.getTufoByProp('file:bytes', iden))
            self.nn(core.getTufoByProp('inet:ipv4', '1.2.3.4'))
            self.nn(core.getTufoByProp('inet:ipv6', '::1'))

    def test_model_inet_web_follows(self):

        with self.getRamCore() as core:

            props = {'seen:min': '20501217', 'seen:max': '20501217'}
            node = core.formTufoByProp('inet:web:follows', ('VERTEX.link/visi', 'vertex.LINK/hehe'), **props)

            self.nn(node)
            self.eq(node[1].get('inet:web:follows:follower'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:follows:followee'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:web:follows:seen:min'), 2554848000000)
            self.eq(node[1].get('inet:web:follows:seen:max'), 2554848000000)

    def test_model_inet_ipv4_raise(self):
        with self.getRamCore() as core:
            self.raises(BadTypeValu, core.formTufoByProp, 'inet:ipv4', 'lolololololol')

    def test_model_inet_urlfile(self):
        with self.getRamCore() as core:

            url = 'HTTP://visi:hehe@www.vertex.link:9999/'
            fguid = 32 * 'a'
            node = core.formTufoByProp('inet:urlfile', (url, fguid), **{'seen:min': 0, 'seen:max': 1})

            self.eq(node[1].get('inet:urlfile:file'), 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
            self.eq(node[1].get('inet:urlfile:url'), 'http://visi:hehe@www.vertex.link:9999/')
            self.eq(node[1].get('inet:urlfile:seen:min'), 0)
            self.eq(node[1].get('inet:urlfile:seen:max'), 1)

            self.none(node[1].get('inet:urlfile:url:port'))
            self.none(node[1].get('inet:urlfile:url:proto'))
            self.none(node[1].get('inet:urlfile:url:user'))
            self.none(node[1].get('inet:urlfile:url:passwd'))

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

    def test_model_fqdn_punycode(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:fqdn', 'www.xn--heilpdagogik-wiki-uqb.de')

            fqdn = node[1].get('inet:fqdn')

            self.eq(fqdn, 'www.xn--heilpdagogik-wiki-uqb.de')
            self.eq(core.getTypeRepr('inet:fqdn', fqdn), 'www.heilpädagogik-wiki.de')

            self.raises(BadTypeValu, core.getTypeNorm, 'inet:fqdn', '!@#$%')

    def test_model_inet_web_logon(self):

        with self.getRamCore() as core:
            tick = now()

            t0 = core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise', time=tick)
            self.nn(t0)

            self.eq(t0[1].get('inet:web:logon:time'), tick)
            self.eq(t0[1].get('inet:web:logon:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:logon:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:logon:acct:site'), 'vertex.link')

            # Pivot from an inet:web:acct to the inet:web:logon forms via storm
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise'))
            nodes = core.eval('inet:web:acct=vertex.link/pennywise inet:web:acct -> inet:web:logon:acct')
            self.eq(len(nodes), 1)

            t0 = core.setTufoProps(t0, ipv4=0x01020304, logout=tick + 1, ipv6='0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:web:logon:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:web:logon:logout'), tick + 1)
            self.eq(t0[1].get('inet:web:logon:logout') - t0[1].get('inet:web:logon:time'), 1)
            self.eq(t0[1].get('inet:web:logon:ipv6'), '::1')

    def test_model_inet_web_action(self):

        with self.getRamCore() as core:
            tick = now()

            t0 = core.formTufoByProp('inet:web:action', '*', act='didathing', acct='vertex.link/pennywise', time=tick)
            self.nn(t0)

            self.eq(t0[1].get('inet:web:action:time'), tick)
            self.eq(t0[1].get('inet:web:action:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:action:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:action:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:action:act'), 'didathing')

            # Pivot from an inet:web:acct to the inet:web:action forms via storm
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise'))
            nodes = core.eval('inet:web:acct=vertex.link/pennywise inet:web:acct -> inet:web:action:acct')
            self.eq(len(nodes), 1)

            t0 = core.setTufoProps(t0, ipv4=0x01020304, ipv6='0:0:0:0:0:0:0:1', acct='vertex.link/user2')
            self.eq(t0[1].get('inet:web:action:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:web:action:ipv6'), '::1')
            self.eq(t0[1].get('inet:web:action:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:action:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:action:acct:site'), 'vertex.link')

            d = {'key': 1, 'valu': ['oh', 'my']}
            t0 = core.setTufoProps(t0, info=d)
            self.eq(json.loads(t0[1].get('inet:web:action:info')), d)

            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:action', '*', acct='vertex.link/pennywise', time=tick)
            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:action', '*', act='didathing', time=tick)

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

    def test_model_inet_201706121318(self):

        iden0 = guid()
        iden1 = guid()
        tick = now()
        rows = (
            (iden0, 'tufo:form', 'inet:url', tick),
            (iden0, 'inet:url', 'http://www.woot.com/', tick),
            (iden1, 'tufo:form', 'inet:url', tick),
            (iden1, 'inet:url', 'http://1.2.3.4/', tick),
        )

        data = {}
        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('inet', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True
            stor.on('modl:vers:rev', addrows, name='inet', vers=201706121318)

            with s_cortex.fromstore(stor) as core:
                self.true(data.get('added'))

                t0 = core.getTufoByIden(iden0)
                self.eq(t0[1].get('inet:url:fqdn'), 'www.woot.com')

                t1 = core.getTufoByIden(iden1)
                self.eq(t1[1].get('inet:url:ipv4'), 0x01020304)

    def test_model_inet_201706201837(self):

        data = {}
        iden0 = guid()
        iden1 = guid()
        tick = now()
        rows = [
            (iden0, 'tufo:form', 'inet:tcp4', tick),
            (iden0, 'inet:tcp4', '1.2.3.4:80', tick),
            (iden1, 'tufo:form', 'inet:udp4', tick),
            (iden1, 'inet:udp4', '1.2.3.4:443', tick),
        ]

        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('inet', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True
            stor.on('modl:vers:rev', addrows, name='inet', vers=201706201837)

            with s_cortex.fromstore(stor) as core:

                t1 = core.getTufoByIden(iden0)
                self.eq(t1[1].get('inet:tcp4:port'), 80)
                self.eq(t1[1].get('inet:tcp4:ipv4'), 0x01020304)

                t2 = core.getTufoByIden(iden1)
                self.eq(t2[1].get('inet:udp4:port'), 443)
                self.eq(t2[1].get('inet:udp4:ipv4'), 0x01020304)

    def test_model_inet_201709181501(self):
        data = {}
        iden0 = guid()
        tick = now()
        rows = [
            (iden0, 'tufo:form', 'inet:whois:rec', tick),
            (iden0, 'inet:whois:rec', 'vertex.link@2017/09/18 15:01:00.000', tick),  # 1505746860000,
            (iden0, 'inet:whois:rec:fqdn', 'vertex.link', tick),
            (iden0, 'inet:whois:rec:asof', 1505746860000, tick),
            (iden0, 'inet:whois:rec:ns1', 'ns1.vertex.link', tick),
            (iden0, 'inet:whois:rec:ns2', 'ns2.vertex.link', tick),
            (iden0, 'inet:whois:rec:ns3', 'ns3.vertex.link', tick),
            (iden0, 'inet:whois:rec:ns4', 'ns4.vertex.link', tick),
        ]

        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('inet', 0)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True
            stor.on('modl:vers:rev', addrows, name='inet', vers=201709181501)

            with s_cortex.fromstore(stor) as core:

                t_guid, _ = core.getTypeNorm('inet:whois:recns', ['ns1.vertex.link',
                                                                  'vertex.link@2017/09/18 15:01:00.000'])

                node = core.eval('inet:whois:rec')[0]
                self.notin('inet:whois:rec:ns1', node[1])
                self.notin('inet:whois:rec:ns2', node[1])
                self.notin('inet:whois:rec:ns3', node[1])
                self.notin('inet:whois:rec:ns4', node[1])

                nodes = core.eval('inet:whois:recns')
                self.eq(len(nodes), 4)

                nodes = core.eval('inet:whois:recns={}'.format(t_guid))
                self.eq(len(nodes), 1)
                node = nodes[0]
                self.eq(node[1].get('inet:whois:recns:ns'), 'ns1.vertex.link')
                self.eq(node[1].get('inet:whois:recns:rec:fqdn'), 'vertex.link')
                self.eq(node[1].get('inet:whois:recns:rec:asof'), 1505746860000)

    def test_model_inet_201709271521(self):
        # There is a lot to look at here.
        # Note that `inet:follows` is completely missing tagforms, these should be created.
        # Note that `inet:netmemb` is missing one tagform, these should be created.

        N = 2
        adds = []

        def _addTag(tag, form):
            tick = now()
            iden = guid()
            tlib = s_types.TypeLib()
            form_valu, _ = tlib.getTypeNorm('syn:tagform', (tag, form))
            return [
                (iden, 'syn:tagform:title', '??', tick),
                (iden, 'syn:tagform', form_valu, tick),
                (iden, 'tufo:form', 'syn:tagform', tick),
                (iden, 'syn:tagform:tag', tag, tick),
                (iden, 'syn:tagform:form', form, tick),
                (iden, 'syn:tagform:doc', '??', tick),
            ]

        for i in range(N):
            user = 'pennywise%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'inet:netuser', tick),
                (iden, 'inet:netuser', 'vertex.link/' + user, tick),
                (iden, 'inet:netuser:site', 'vertex.link', tick),
                (iden, 'inet:netuser:user', user, tick),
                (iden, 'inet:netuser:dob', 1337, tick),
                (iden, 'inet:netuser:url', 'https://vertex.link/url', tick),
                (iden, 'inet:netuser:webpage', 'https://vertex.link/webpage', tick),
                (iden, 'inet:netuser:avatar', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden, 'inet:netuser:tagline', 'a tagline', tick),
                (iden, 'inet:netuser:occupation', 'entertainer', tick),
                (iden, 'inet:netuser:name', 'my name', tick),
                (iden, 'inet:netuser:realname', 'my real name', tick),
                (iden, 'inet:netuser:email', 'email@vertex.link', tick),
                (iden, 'inet:netuser:phone', '17035551212', tick),
                (iden, 'inet:netuser:signup', 7331, tick),
                (iden, 'inet:netuser:signup:ipv4', 0x01020304, tick),
                (iden, 'inet:netuser:passwd', 'hunter2', tick),
                (iden, 'inet:netuser:seen:min', 0, tick),
                (iden, 'inet:netuser:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*inet:netuser#hehe.hoho', tick, tick),
                (dark_iden, '_:*inet:netuser#hehe', tick, tick),
            ])
        adds.extend(_addTag('hehe.hoho', 'inet:netuser'))
        adds.extend(_addTag('hehe', 'inet:netuser'))

        for i in range(N):
            group = 'group%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'inet:netgroup', tick),
                (iden, 'inet:netgroup', 'vertex.link/' + group, tick),
                (iden, 'inet:netgroup:site', 'vertex.link', tick),
                (iden, 'inet:netgroup:name', group, tick),
                (iden, 'inet:netgroup:desc', 'hehe', tick),
                (iden, 'inet:netgroup:url', 'https://vertex.link/url', tick),
                (iden, 'inet:netgroup:webpage', 'https://vertex.link/webpage', tick),
                (iden, 'inet:netgroup:avatar', 'd41d8cd98f00b204e9800998ecf8427e', tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*inet:netgroup#hehe.hoho', tick, tick),
                (dark_iden, '_:*inet:netgroup#hehe', tick, tick),
            ])
        adds.extend(_addTag('hehe.hoho', 'inet:netgroup'))
        adds.extend(_addTag('hehe', 'inet:netgroup'))

        iden = guid()
        acct1 = 'vertex.link/person1'
        acct2 = 'vertex.link/person2'
        follow_valu = '4ebc93255f8582a9d6c38dbba952dc9b'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'inet:follows', tick),
            (iden, 'inet:follows', follow_valu, tick),
            (iden, 'inet:follows:follower', acct1, tick),
            (iden, 'inet:follows:followee', acct2, tick),
            (iden, 'inet:follows:seen:min', 0, tick),
            (iden, 'inet:follows:seen:max', 1, tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:follows#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:follows#hehe', tick, tick),
        ])
        # NOTE: we do not add the tagform here on purpose to make sure the dark rows migrate

        iden = guid()
        webmemb_valu = '7d8675f29b54cf71e3c36d4448aaa842'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'inet:netmemb', tick),
            (iden, 'inet:netmemb', webmemb_valu, tick),
            (iden, 'inet:netmemb:user', 'vertex.link/person1', tick),
            (iden, 'inet:netmemb:group', 'vertex.link/group0', tick),
            (iden, 'inet:netmemb:title', 'a title', tick),
            (iden, 'inet:netmemb:joined', 123, tick),
            (iden, 'inet:netmemb:seen:min', 0, tick),
            (iden, 'inet:netmemb:seen:max', 1, tick),
            (iden, '#hehe.hoho.haha', tick, tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:netmemb#hehe.hoho.haha', tick, tick),
            (dark_iden, '_:*inet:netmemb#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:netmemb#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho.haha', 'inet:netmemb'))
        # hehe.hoho is missing for some unknown reason
        adds.extend(_addTag('hehe', 'inet:netmemb'))

        iden = guid()
        webpost_valu = '19abe9969d6712318370f7c4d943f8ea'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'inet:netpost', tick),
            (iden, 'inet:netpost', webpost_valu, tick),
            (iden, 'inet:netpost:netuser', 'vertex.link/person1', tick),
            (iden, 'inet:netpost:netuser:site', 'vertex.link', tick),
            (iden, 'inet:netpost:netuser:user', 'person1', tick),
            (iden, 'inet:netpost:text', 'my cool post', tick),
            (iden, 'inet:netpost:replyto', '0' * 32, tick),
            (iden, 'inet:netpost:url', 'https://vertex.link/blog/1', tick),
            (iden, 'inet:netpost:file', 'd41d8cd98f00b204e9800998ecf8427e', tick),
            (iden, 'inet:netpost:time', 12345, tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:netpost#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:netpost#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'inet:netpost'))
        adds.extend(_addTag('hehe', 'inet:netpost'))

        iden = guid()
        webfile_valu = '1f91e1492718d2cbccae1f27c54409ed'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'inet:netfile', tick),
            (iden, 'inet:netfile', webfile_valu, tick),
            (iden, 'inet:netfile:file', '0' * 32, tick),
            (iden, 'inet:netfile:netuser', 'vertex.link/person1', tick),
            (iden, 'inet:netfile:netuser:site', 'vertex.link', tick),
            (iden, 'inet:netfile:netuser:user', 'person1', tick),
            (iden, 'inet:netfile:name', 'my cool file', tick),
            (iden, 'inet:netfile:posted', 123456, tick),
            (iden, 'inet:netfile:ipv4', 0, tick),
            (iden, 'inet:netfile:ipv6', '::1', tick),
            (iden, 'inet:netfile:seen:min', 0, tick),
            (iden, 'inet:netfile:seen:max', 1, tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:netfile#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:netfile#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'inet:netfile'))
        adds.extend(_addTag('hehe', 'inet:netfile'))

        iden = guid()
        imgof_valu = 'b873597b32ce4adb836d8d4aae1831f6'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'file:imgof', tick),
            (iden, 'file:imgof', imgof_valu, tick),
            (iden, 'file:imgof:file', '0' * 32, tick),
            (iden, 'file:imgof:xref', 'inet:netuser=vertex.link/person1', tick),
            (iden, 'file:imgof:xref:prop', 'inet:netuser', tick),
            (iden, 'file:imgof:xref:strval', 'vertex.link/person1', tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*file:imgof#hehe.hoho', tick, tick),
            (dark_iden, '_:*file:imgof#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'file:imgof'))
        adds.extend(_addTag('hehe', 'file:imgof'))

        iden = guid()
        txtref_valu = 'c10d26ad2467bb72320ad1fc501ec40b'
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'tufo:form', 'file:txtref', tick),
            (iden, 'file:txtref', txtref_valu, tick),
            (iden, 'file:txtref:file', '0' * 32, tick),
            (iden, 'file:txtref:xref', 'inet:netgroup=vertex.link/group0', tick),
            (iden, 'file:txtref:xref:prop', 'inet:netgroup', tick),
            (iden, 'file:txtref:xref:strval', 'vertex.link/group0', tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*file:txtref#hehe.hoho', tick, tick),
            (dark_iden, '_:*file:txtref#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'file:txtref'))
        adds.extend(_addTag('hehe', 'file:txtref'))

        iden = guid()
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'ps:hasnetuser:netuser', 'vertex.link/heheman', tick),
            (iden, 'ps:hasnetuser:person', '00000000000000000000000000000000', tick),
            (iden, 'tufo:form', 'ps:hasnetuser', tick),
            (iden, 'ps:hasnetuser', '00000000000000000000000000000000/vertex.link/heheman', tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*ps:hasnetuser#hehe.hoho', tick, tick),
            (dark_iden, '_:*ps:hasnetuser#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'ps:hasnetuser'))
        adds.extend(_addTag('hehe', 'ps:hasnetuser'))

        iden = guid()
        dark_iden = iden[::-1]
        tick = now()
        adds.extend([
            (iden, 'ou:hasnetuser:netuser', 'vertex.link/heheman', tick),
            (iden, 'ou:hasnetuser:org', '00000000000000000000000000000000', tick),
            (iden, 'tufo:form', 'ou:hasnetuser', tick),
            (iden, 'ou:hasnetuser', '4016087db1b71ecc56db535a5ee9e86e', tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*ou:hasnetuser#hehe.hoho', tick, tick),
            (dark_iden, '_:*ou:hasnetuser#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'ou:hasnetuser'))
        adds.extend(_addTag('hehe', 'ou:hasnetuser'))

        # inet:web:logon is already in the inet:web:logon space but needs to account for the netuser move
        iden = guid()
        tick = now()
        adds.extend([
            (iden, 'inet:web:logon', 'cf672b42e342f49d6afee00341de1ebd', tick),
            (iden, 'inet:web:logon:netuser', 'vertex.link/pennywise', tick),
            (iden, 'inet:web:logon:netuser:site', 'vertex.link', tick),
            (iden, 'inet:web:logon:netuser:user', 'pennywise', tick),
            (iden, 'inet:web:logon:ipv4', 16909060, tick),
            (iden, 'inet:web:logon:time', 1505001600000, tick),
            (iden, 'tufo:form', 'inet:web:logon', tick),
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:web:logon#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:web:logon#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'inet:web:logon'))
        adds.extend(_addTag('hehe', 'inet:web:logon'))

        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('inet', 0)

            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='inet', vers=201709271521)

            with s_cortex.fromstore(stor) as core:

                # inet:netuser -> inet:web:acct
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:acct')
                self.len(N, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise0')
                self.eq(tufo[1]['tufo:form'], 'inet:web:acct')
                self.eq(tufo[1]['inet:web:acct'], 'vertex.link/pennywise0')
                self.eq(tufo[1]['inet:web:acct:user'], 'pennywise0')
                self.eq(tufo[1]['inet:web:acct:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:acct:url'], 'https://vertex.link/url')
                self.eq(tufo[1]['inet:web:acct:webpage'], 'https://vertex.link/webpage')
                self.eq(tufo[1]['inet:web:acct:avatar'], 'd41d8cd98f00b204e9800998ecf8427e')
                self.eq(tufo[1]['inet:web:acct:tagline'], 'a tagline')
                self.eq(tufo[1]['inet:web:acct:occupation'], 'entertainer')
                self.eq(tufo[1]['inet:web:acct:name'], 'my name')
                self.eq(tufo[1]['inet:web:acct:realname'], 'my real name')
                self.eq(tufo[1]['inet:web:acct:email'], 'email@vertex.link')
                self.eq(tufo[1]['inet:web:acct:phone'], '17035551212')
                self.eq(tufo[1]['inet:web:acct:signup'], 7331)
                self.eq(tufo[1]['inet:web:acct:signup:ipv4'], 16909060)
                self.eq(tufo[1]['inet:web:acct:passwd'], 'hunter2')
                self.eq(tufo[1]['inet:web:acct:seen:min'], 0)
                self.eq(tufo[1]['inet:web:acct:seen:max'], 1)

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:netuser'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:acct'))
                self.len(0, core.getRowsByProp('_:*inet:netuser#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netuser#hehe'))
                self.len(2, core.getRowsByProp('_:*inet:web:acct#hehe.hoho'))
                self.len(2, core.getRowsByProp('_:*inet:web:acct#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:netuser')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netuser')
                self.len(0, rows)

                # inet:netgroup -> inet:web:group
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:group')
                self.len(N, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:group', 'vertex.link/group0')
                self.eq(tufo[1]['tufo:form'], 'inet:web:group')
                self.eq(tufo[1]['inet:web:group'], 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:group:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:group:id'], 'group0')
                self.eq(tufo[1]['inet:web:group:desc'], 'hehe')
                self.eq(tufo[1]['inet:web:group:url'], 'https://vertex.link/url')
                self.eq(tufo[1]['inet:web:group:webpage'], 'https://vertex.link/webpage')
                self.eq(tufo[1]['inet:web:group:avatar'], 'd41d8cd98f00b204e9800998ecf8427e')

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:netgroup'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:group'))
                self.len(0, core.getRowsByProp('_:*inet:netgroup#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netgroup#hehe'))
                self.len(2, core.getRowsByProp('_:*inet:web:group#hehe.hoho'))
                self.len(2, core.getRowsByProp('_:*inet:web:group#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:netgroup')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netgroup')
                self.len(0, rows)

                # inet:netmemb -> inet:web:memb
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:memb')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:memb', webmemb_valu)
                self.eq(tufo[1]['tufo:form'], 'inet:web:memb')
                self.eq(tufo[1]['inet:web:memb'], webmemb_valu)
                self.eq(tufo[1]['inet:web:memb:acct'], 'vertex.link/person1')
                self.eq(tufo[1]['inet:web:memb:group'], 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:memb:title'], 'a title')
                self.eq(tufo[1]['inet:web:memb:joined'], 123)
                self.eq(tufo[1]['inet:web:memb:seen:min'], 0)
                self.eq(tufo[1]['inet:web:memb:seen:max'], 1)

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho', 'hehe.hoho.haha'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:netmemb'))
                self.len(3, core.getRowsByProp('syn:tagform:form', 'inet:web:memb'))  # NOTE: the middle tagform was created
                self.len(0, core.getRowsByProp('_:*inet:netmemb#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netmemb#hehe'))
                self.len(1, core.getRowsByProp('_:*inet:web:memb#hehe.hoho.haha'))
                self.len(1, core.getRowsByProp('_:*inet:web:memb#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*inet:web:memb#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:netmemb')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netmemb')
                self.len(0, rows)

                # inet:follows -> inet:web:follows
                # assert that the correct number of follow relationships were migrated
                tufos = core.getTufosByProp('inet:web:follows')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:follows', follow_valu)
                self.eq(tufo[1]['tufo:form'], 'inet:web:follows')
                self.eq(tufo[1]['inet:web:follows'], follow_valu)
                self.eq(tufo[1]['inet:web:follows:follower'], acct1)
                self.eq(tufo[1]['inet:web:follows:followee'], acct2)
                self.eq(tufo[1]['inet:web:follows:seen:min'], 0)
                self.eq(tufo[1]['inet:web:follows:seen:max'], 1)

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                # NOTE: we try to create missing tagforms
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:follows'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:follows'))
                self.len(0, core.getRowsByProp('_:*inet:follows#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:follows#hehe'))
                self.len(1, core.getRowsByProp('_:*inet:web:follows#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*inet:web:follows#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:follows')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:follows')
                self.len(0, rows)

                # inet:netpost -> inet:web:post
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:post')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:post', webpost_valu)
                self.eq(tufo[1]['tufo:form'], 'inet:web:post')
                self.eq(tufo[1]['inet:web:post'], webpost_valu)
                self.eq(tufo[1]['inet:web:post:acct'], 'vertex.link/person1')
                self.eq(tufo[1]['inet:web:post:acct:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:post:acct:user'], 'person1')
                self.eq(tufo[1]['inet:web:post:text'], 'my cool post')
                self.eq(tufo[1]['inet:web:post:replyto'], '0' * 32)
                self.eq(tufo[1]['inet:web:post:url'], 'https://vertex.link/blog/1')
                self.eq(tufo[1]['inet:web:post:file'], 'd41d8cd98f00b204e9800998ecf8427e')
                self.eq(tufo[1]['inet:web:post:time'], 12345)

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:netpost'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:post'))
                self.len(0, core.getRowsByProp('_:*inet:netpost#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netpost#hehe'))
                self.len(1, core.getRowsByProp('_:*inet:web:post#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*inet:web:post#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:netpost')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netpost')
                self.len(0, rows)

                # inet:netfile -> inet:web:file
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:file')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:file', webfile_valu)
                self.eq(tufo[1]['tufo:form'], 'inet:web:file')
                self.eq(tufo[1]['inet:web:file'], webfile_valu)
                self.eq(tufo[1]['inet:web:file:acct'], 'vertex.link/person1')
                self.eq(tufo[1]['inet:web:file:acct:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:file:acct:user'], 'person1')
                self.eq(tufo[1]['inet:web:file:file'], '0' * 32)
                self.eq(tufo[1]['inet:web:file:name'], 'my cool file')
                self.eq(tufo[1]['inet:web:file:posted'], 123456)
                self.eq(tufo[1]['inet:web:file:ipv4'], 0)
                self.eq(tufo[1]['inet:web:file:ipv6'], '::1')
                self.eq(tufo[1]['inet:web:file:seen:min'], 0)
                self.eq(tufo[1]['inet:web:file:seen:max'], 1)

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'inet:netfile'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:file'))
                self.len(0, core.getRowsByProp('_:*inet:netfile#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netfile#hehe'))
                self.len(1, core.getRowsByProp('_:*inet:web:file#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*inet:web:file#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('inet:netfile')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netfile')
                self.len(0, rows)

                # file:imgof
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('file:imgof')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                new_imgof_valu = 'fd415d0895e9ce466d8292c3d55c6bf5'  # NOTE: valu changes because we change the prop name
                tufo = core.getTufoByProp('file:imgof', new_imgof_valu)
                self.eq(tufo[1]['tufo:form'], 'file:imgof')
                self.eq(tufo[1]['file:imgof'], new_imgof_valu)
                self.eq(tufo[1]['file:imgof:file'], '0' * 32)
                self.eq(tufo[1]['file:imgof:xref'], 'inet:web:acct=vertex.link/person1')
                self.eq(tufo[1]['file:imgof:xref:prop'], 'inet:web:acct')
                self.eq(tufo[1]['file:imgof:xref:strval'], 'vertex.link/person1')

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'file:imgof'))
                self.len(1, core.getRowsByProp('_:*file:imgof#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*file:imgof#hehe'))  # NOTE: dark rows should stay the same

                # assert that no old data remains
                tufos = core.getTufosByProp('file:imgof', imgof_valu)
                self.len(0, tufos)

                # file:txtref
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('file:txtref')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                new_txtref_valu = 'd4f8fbb792d127422a0dc788588f8f7a'  # NOTE: valu changes because we change the prop name
                tufo = core.getTufoByProp('file:txtref', new_txtref_valu)
                self.eq(tufo[1]['tufo:form'], 'file:txtref')
                self.eq(tufo[1]['file:txtref'], new_txtref_valu)
                self.eq(tufo[1]['file:txtref:file'], '0' * 32)
                self.eq(tufo[1]['file:txtref:xref'], 'inet:web:group=vertex.link/group0')
                self.eq(tufo[1]['file:txtref:xref:prop'], 'inet:web:group')
                self.eq(tufo[1]['file:txtref:xref:strval'], 'vertex.link/group0')

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'file:txtref'))
                self.len(1, core.getRowsByProp('_:*file:txtref#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*file:txtref#hehe'))  # NOTE: dark rows should stay the same

                # assert that no old data remains
                tufos = core.getTufosByProp('file:txtref', txtref_valu)
                self.len(0, tufos)

                # ps:hasnetuser -> ps:haswebacct
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('ps:haswebacct')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('ps:haswebacct', '00000000000000000000000000000000/vertex.link/heheman')
                self.eq(tufo[1]['tufo:form'], 'ps:haswebacct')
                self.eq(tufo[1]['ps:haswebacct'], '00000000000000000000000000000000/vertex.link/heheman')
                self.eq(tufo[1]['ps:haswebacct:acct'], 'vertex.link/heheman')
                self.eq(tufo[1]['ps:haswebacct:person'], '00000000000000000000000000000000')

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'ps:hasnetuser'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'ps:haswebacct'))
                self.len(0, core.getRowsByProp('_:*ps:hasnetuser#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*ps:hasnetuser#hehe'))
                self.len(1, core.getRowsByProp('_:*ps:haswebacct#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*ps:haswebacct#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('ps:hasnetuser')
                self.len(0, tufos)
                rows = core.getJoinByProp('ps:hasnetuser')
                self.len(0, rows)

                # ou:hasnetuser -> ou:haswebacct
                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('ou:haswebacct')
                self.len(1, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('ou:haswebacct', '4016087db1b71ecc56db535a5ee9e86e')
                self.eq(tufo[1]['tufo:form'], 'ou:haswebacct')
                self.eq(tufo[1]['ou:haswebacct'], '4016087db1b71ecc56db535a5ee9e86e')
                self.eq(tufo[1]['ou:haswebacct:acct'], 'vertex.link/heheman')
                self.eq(tufo[1]['ou:haswebacct:org'], '00000000000000000000000000000000')

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('syn:tagform:form', 'ou:hasnetuser'))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'ou:haswebacct'))
                self.len(0, core.getRowsByProp('_:*ou:hasnetuser#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*ou:hasnetuser#hehe'))
                self.len(1, core.getRowsByProp('_:*ou:haswebacct#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*ou:haswebacct#hehe'))

                # assert that no old data remains
                tufos = core.getTufosByProp('ou:hasnetuser')
                self.len(0, tufos)
                rows = core.getJoinByProp('ou:hasnetuser')
                self.len(0, rows)

                # ensure inet:web:logon:netuser was moved over
                tufo = core.getTufoByProp('inet:web:logon')
                self.eq(tufo[1].get('tufo:form'), 'inet:web:logon')
                self.eq(tufo[1].get('inet:web:logon:acct'), 'vertex.link/pennywise')
                self.eq(tufo[1].get('inet:web:logon:acct:site'), 'vertex.link')
                self.eq(tufo[1].get('inet:web:logon:acct:user'), 'pennywise')
                self.notin('inet:web:logon:netuser', tufo[1])
                self.notin('inet:web:logon:netuser:site', tufo[1])
                self.notin('inet:web:logon:netuser:user', tufo[1])

                # check that tags were correctly migrated
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(2, core.getRowsByProp('syn:tagform:form', 'inet:web:logon'))
                self.len(1, core.getRowsByProp('_:*inet:web:logon#hehe.hoho'))
                self.len(1, core.getRowsByProp('_:*inet:web:logon#hehe'))

    def test_model_inet_201710111553(self):

        adds = []

        iden, tick = guid(), now()
        adds.extend([
            (iden, 'tufo:form', 'inet:web:acct', tick),
            (iden, 'inet:web:acct', 'vertex.link/pennywise1', tick),
            (iden, 'inet:web:acct:site', 'vertex.link', tick),
            (iden, 'inet:web:acct:user', 'pennywise', tick),
            (iden, 'inet:web:acct:occupation', 'EnterTainEr', tick),
        ])

        iden, tick = guid(), now()
        adds.extend([
            (iden, 'tufo:form', 'inet:web:acct', tick),
            (iden, 'inet:web:acct', 'vertex.link/pennywise2', tick),
            (iden, 'inet:web:acct:site', 'vertex.link', tick),
            (iden, 'inet:web:acct:user', 'pennywise', tick),
            (iden, 'inet:web:acct:occupation', 'entertainer', tick),
        ])

        with s_cortex.openstore('ram:///') as stor:

            stor.setModlVers('inet', 0)
            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='inet', vers=201710111553)

            with s_cortex.fromstore(stor) as core:

                tufo = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise1')
                self.eq(tufo[1]['tufo:form'], 'inet:web:acct')
                self.eq(tufo[1]['inet:web:acct'], 'vertex.link/pennywise1')
                self.eq(tufo[1]['inet:web:acct:occupation'], 'entertainer')

                tufo = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise2')
                self.eq(tufo[1]['tufo:form'], 'inet:web:acct')
                self.eq(tufo[1]['inet:web:acct'], 'vertex.link/pennywise2')
                self.eq(tufo[1]['inet:web:acct:occupation'], 'entertainer')

    def test_model_inet_201802131725(self):

        data = {}
        iden0 = guid()
        tick = now()
        rows = [
            (iden0, 'tufo:form', 'inet:web:group', tick),
            (iden0, 'inet:web:group', 'vertex.link/1234', tick),
            (iden0, 'inet:web:group:site', 'vertex.link', tick),
            (iden0, 'inet:web:group:name', '1234', tick),
        ]

        with s_cortex.openstore('ram:///') as stor:
            # force model migration callbacks
            stor.setModlVers('inet', 201802131724)

            def addrows(mesg):
                stor.addRows(rows)
                data['added'] = True
            stor.on('modl:vers:rev', addrows, name='inet', vers=201802131725)

            with s_cortex.fromstore(stor) as core:
                t1 = core.getTufoByIden(iden0)
                self.none(t1[1].get('inet:web:group:name'))
                self.eq(t1[1].get('inet:web:group:id'), '1234')
                self.nn(core.getTufoByProp('inet:group', '1234'))
                vals = [v for v, t in core.getTufoDarkValus(t1, 'syn:modl:rev')]
                self.isin('inet:201802131725', vals)

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

            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://[FF::56]:99')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://8.6.7.5:309')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'tcp://8.6.7.256:309')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'giggles://float.down.here/')

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

    def test_model_inet_wifi(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:wifi:ssid', 'hehe haha')
            self.eq(node[1].get('inet:wifi:ssid'), 'hehe haha')

            node = core.formTufoByProp('inet:wifi:ap', ('lololol', '01:02:03:04:05:06'))
            self.eq(node[1].get('inet:wifi:ap:ssid'), 'lololol')
            self.eq(node[1].get('inet:wifi:ap:bssid'), '01:02:03:04:05:06')

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

    def test_model_inet_urlredir(self):

        with self.getRamCore() as core:

            tick = s_time.parse('20161217')
            tock = s_time.parse('20170216')

            props = {'seen:min': tick, 'seen:max': tock}
            node = core.formTufoByProp('inet:urlredir', ('http://foo.com/', 'http://bar.com/'), **props)

            self.nn(core.getTufoByProp('inet:url', 'http://foo.com/'))
            self.nn(core.getTufoByProp('inet:url', 'http://bar.com/'))

            self.eq(node[1].get('inet:urlredir:src'), 'http://foo.com/')
            self.eq(node[1].get('inet:urlredir:src:fqdn'), 'foo.com')

            self.eq(node[1].get('inet:urlredir:dst'), 'http://bar.com/')
            self.eq(node[1].get('inet:urlredir:dst:fqdn'), 'bar.com')

            self.eq(node[1].get('inet:urlredir:seen:min'), tick)
            self.eq(node[1].get('inet:urlredir:seen:max'), tock)

    def test_model_inet_rfc2822_addr(self):

        with self.getRamCore() as core:

            self.raises(BadTypeValu, core.formTufoByProp, 'inet:rfc2822:addr', 20)

            n0 = core.formTufoByProp('inet:rfc2822:addr', 'FooBar')
            n1 = core.formTufoByProp('inet:rfc2822:addr', 'visi@vertex.link')
            n2 = core.formTufoByProp('inet:rfc2822:addr', 'foo bar<visi@vertex.link>')
            n3 = core.formTufoByProp('inet:rfc2822:addr', 'foo bar <visi@vertex.link>')
            n4 = core.formTufoByProp('inet:rfc2822:addr', '"foo bar "   <visi@vertex.link>')
            n5 = core.formTufoByProp('inet:rfc2822:addr', '<visi@vertex.link>')

            self.eq(n0[1].get('inet:rfc2822:addr'), 'foobar')
            self.none(n0[1].get('inet:rfc2822:addr:name'))
            self.none(n0[1].get('inet:rfc2822:addr:addr'))

            self.eq(n1[1].get('inet:rfc2822:addr'), 'visi@vertex.link')
            self.eq(n1[1].get('inet:rfc2822:addr:email'), 'visi@vertex.link')
            self.none(n1[1].get('inet:rfc2822:addr:name'))

            self.eq(n2[1].get('inet:rfc2822:addr'), 'foo bar <visi@vertex.link>')
            self.eq(n2[1].get('inet:rfc2822:addr:name'), 'foo bar')
            self.eq(n2[1].get('inet:rfc2822:addr:email'), 'visi@vertex.link')

            self.eq(n2[0], n3[0])
            self.eq(n2[0], n4[0])
            self.eq(n1[0], n5[0])

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

            node = core.formTufoByProp('inet:http:resphead', (ridn, ('server', 'my web server')))
            self.eq(node[1].get('inet:http:resphead:response'), ridn)
            self.eq(node[1].get('inet:http:resphead:header:name'), 'server')
            self.eq(node[1].get('inet:http:resphead:header:value'), 'my web server')
