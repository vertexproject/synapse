# -*- coding: UTF-8 -*-
import synapse.lib.tufo as s_tufo

from synapse.tests.common import *

class InetModelTest(SynTest):

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
            self.eq(unicode_tufo, idna_tufo)

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

    def test_model_inet_netpost(self):

        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:netpost', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            iden = node0[1].get('inet:netpost')

            node1 = core.formTufoByProp('inet:netpost', ('vertex.link/visi', 'whos there'), time='20141217010102', replyto=iden)

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))

            self.eq(node0[1].get('inet:netpost:netuser:user'), 'visi')
            self.eq(node1[1].get('inet:netpost:netuser:user'), 'visi')

            self.eq(node0[1].get('inet:netpost:netuser:site'), 'vertex.link')
            self.eq(node1[1].get('inet:netpost:netuser:site'), 'vertex.link')

            self.eq(node0[1].get('inet:netpost'), node1[1].get('inet:netpost:replyto'))

    def test_model_inet_netmesg(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:netmesg', ('VERTEX.link/visi', 'vertex.LINK/hehe', '20501217'), text='hehe haha')
            self.nn(node)
            self.eq(node[1].get('inet:netmesg:from'), 'vertex.link/visi')
            self.eq(node[1].get('inet:netmesg:to'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:netmesg:time'), 2554848000000)
            self.eq(node[1].get('inet:netmesg:text'), 'hehe haha')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/hehe'))

    def test_model_inet_netmemb(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:netmemb', ('VERTEX.link/visi', 'vertex.LINK/kenshoto'), joined='20501217')

            self.nn(node)

            self.eq(node[1].get('inet:netmemb:joined'), 2554848000000)
            self.eq(node[1].get('inet:netmemb:user'), 'vertex.link/visi')
            self.eq(node[1].get('inet:netmemb:group'), 'vertex.link/kenshoto')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:group', 'vertex.link/kenshoto'))

    def test_model_inet_follows(self):

        with self.getRamCore() as core:

            props = {'seen:min': '20501217', 'seen:max': '20501217'}
            node = core.formTufoByProp('inet:follows', ('VERTEX.link/visi', 'vertex.LINK/hehe'), **props)

            self.nn(node)
            self.eq(node[1].get('inet:follows:follower'), 'vertex.link/visi')
            self.eq(node[1].get('inet:follows:followee'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:follows:seen:min'), 2554848000000)
            self.eq(node[1].get('inet:follows:seen:max'), 2554848000000)

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

    def test_model_inet_weblogon(self):

        with self.getRamCore() as core:
            tick = now()

            t0 = core.formTufoByProp('inet:web:logon', '*',
                                     netuser='vertex.link/pennywise',
                                     time=tick)

            self.nn(t0)

            self.eq(t0[1].get('inet:web:logon:time'), tick)
            self.eq(t0[1].get('inet:web:logon:netuser'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:logon:netuser:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:logon:netuser:site'), 'vertex.link')

            # Pivot from a netuser to the netlogon forms via storm
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise'))
            nodes = core.eval('inet:web:acct=vertex.link/pennywise inet:web:acct -> inet:web:logon:netuser')
            self.eq(len(nodes), 1)

            t0 = core.setTufoProps(t0, ipv4=0x01020304, logout=tick + 1, ipv6='0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:web:logon:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:web:logon:logout'), tick + 1)
            self.eq(t0[1].get('inet:web:logon:logout') - t0[1].get('inet:web:logon:time'), 1)
            self.eq(t0[1].get('inet:web:logon:ipv6'), '::1')

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

        N = 2
        adds = []

        tag1_iden = guid()
        tag2_iden = guid()
        tag1_tick = now()
        tag2_tick = now()

        adds.extend([
            (tag1_iden, 'syn:tagform:title', '??', tag1_tick),
            (tag1_iden, 'syn:tagform', guid(), tag1_tick),
            (tag1_iden, 'tufo:form', 'syn:tagform', tag1_tick),
            (tag1_iden, 'syn:tagform:tag', 'hehe.hoho', tag1_tick),
            (tag1_iden, 'syn:tagform:form', 'inet:netuser', tag1_tick),
            (tag1_iden, 'syn:tagform:doc', '??', tag1_tick),

            (tag2_iden, 'syn:tagform:title', '??', tag2_tick),
            (tag2_iden, 'syn:tagform', guid(), tag2_tick),
            (tag2_iden, 'tufo:form', 'syn:tagform', tag2_tick),
            (tag2_iden, 'syn:tagform:tag', 'hehe', tag2_tick),
            (tag2_iden, 'syn:tagform:form', 'inet:netuser', tag2_tick),
            (tag2_iden, 'syn:tagform:doc', '??', tag2_tick),
        ])

        for i in range(N):
            user = 'pennywise%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'inet:web:acct', tick),
                (iden, 'inet:netuser', 'vertex.link/' + user, tick),
                (iden, 'inet:netuser:site', 'vertex.link', tick),
                (iden, 'inet:netuser:user', user, tick),
                (iden, 'inet:netuser:dob', 1337, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*inet:netuser#hehe.hoho', tick, tick),
                (dark_iden, '_:*inet:netuser#hehe', tick, tick),
            ])

        for i in range(N):
            group = 'group%d' % i
            iden = guid()
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'inet:netgroup', tick),
                (iden, 'inet:netgroup', 'vertex.link/' + group, tick),
                (iden, 'inet:netgroup:site', 'vertex.link', tick),
                (iden, 'inet:netgroup:name', group, tick),
                (iden, 'inet:netgroup:desc', 'hehe', tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
            ])

        with s_cortex.openstore('ram:///') as stor:

            # force model migration callbacks
            stor.setModlVers('inet', 0)

            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='inet', vers=201709271521)

            with s_cortex.fromstore(stor) as core:

                # assert that the correct number of users and groups were migrated
                tufos = core.getTufosByProp('inet:web:acct')
                self.len(N, tufos)
                tufos = core.getTufosByProp('inet:web:group')
                self.len(N, tufos)

                # check that properties were correctly migrated and tags were not damaged
                tufo = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise0')
                self.eq(tufo[1]['inet:web:acct'], 'vertex.link/pennywise0')
                self.eq(tufo[1]['inet:web:acct:user'], 'pennywise0')
                self.eq(tufo[1]['inet:web:acct:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:acct:dob'], 1337)
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('_:*inet:netuser#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netuser#hehe'))
                self.len(2, core.getRowsByProp('_:*inet:web:acct#hehe.hoho'))
                self.len(2, core.getRowsByProp('_:*inet:web:acct#hehe'))

                tufo = core.getTufoByProp('inet:web:group', 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:group'], 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:group:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:group:name'], 'group0')
                self.eq(tufo[1]['inet:web:group:desc'], 'hehe')
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))

                # assert that no inet:web:acct remains
                tufos = core.getTufosByProp('inet:netuser')
                self.len(0, tufos)
                rows = core.getJoinByProp('inet:netuser')
                self.len(0, rows)
