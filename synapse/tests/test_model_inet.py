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

    def test_model_inet_web_acct(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:web:acct', 'vertex.link/person1')
            self.eq(t0[1].get('inet:web:acct'), 'vertex.link/person1')
            self.eq(t0[1].get('inet:web:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:acct:user'), 'person1')
            t0 = core.setTufoProp(t0, 'loc', 'HAHA')
            self.eq(t0[1].get('inet:web:acct:loc'), 'haha')

    def test_model_inet_web_post(self):

        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            iden = node0[1].get('inet:web:post')

            node1 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'whos there'), time='20141217010102', replyto=iden)

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))

            self.eq(node0[1].get('inet:web:post:acct:user'), 'visi')
            self.eq(node1[1].get('inet:web:post:acct:user'), 'visi')

            self.eq(node0[1].get('inet:web:post:acct:site'), 'vertex.link')
            self.eq(node1[1].get('inet:web:post:acct:site'), 'vertex.link')

            self.eq(node0[1].get('inet:web:post'), node1[1].get('inet:web:post:replyto'))

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

        def _addTag(tag, form):
            iden = guid()
            tick = now()
            return [
                (iden, 'syn:tagform:title', '??', tick),
                (iden, 'syn:tagform', guid(), tick),
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
                (iden, 'tufo:form', 'inet:web:acct', tick),
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
        adds.extend(_addTag('hehe.hoho', 'inet:follows'))
        adds.extend(_addTag('hehe', 'inet:follows'))

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
            (iden, '#hehe.hoho', tick, tick),
            (iden, '#hehe', tick, tick),
            (dark_iden, '_:*inet:netmemb#hehe.hoho', tick, tick),
            (dark_iden, '_:*inet:netmemb#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'inet:netmemb'))
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
        adds.extend(_addTag('hehe.hoho', 'inet:netpost'))
        adds.extend(_addTag('hehe', 'inet:netpost'))

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
            (dark_iden, '_:*file:imgof#hehe.hoho', tick, tick),
            (dark_iden, '_:*file:imgof#hehe', tick, tick),
        ])
        adds.extend(_addTag('hehe.hoho', 'file:txtref'))
        adds.extend(_addTag('hehe', 'file:txtref'))

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
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
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
                self.eq(tufo[1]['inet:web:group'], 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:group:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:group:name'], 'group0')
                self.eq(tufo[1]['inet:web:group:desc'], 'hehe')
                self.eq(tufo[1]['inet:web:group:url'], 'https://vertex.link/url')
                self.eq(tufo[1]['inet:web:group:webpage'], 'https://vertex.link/webpage')
                self.eq(tufo[1]['inet:web:group:avatar'], 'd41d8cd98f00b204e9800998ecf8427e')
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
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
                self.eq(tufo[1]['inet:web:memb'], webmemb_valu)
                self.eq(tufo[1]['inet:web:memb:acct'], 'vertex.link/person1')
                self.eq(tufo[1]['inet:web:memb:group'], 'vertex.link/group0')
                self.eq(tufo[1]['inet:web:memb:title'], 'a title')
                self.eq(tufo[1]['inet:web:memb:joined'], 123)
                self.eq(tufo[1]['inet:web:memb:seen:min'], 0)
                self.eq(tufo[1]['inet:web:memb:seen:max'], 1)
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
                self.len(0, core.getRowsByProp('_:*inet:netmemb#hehe.hoho'))
                self.len(0, core.getRowsByProp('_:*inet:netmemb#hehe'))
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
                self.eq(tufo[1]['inet:web:follows'], follow_valu)
                self.eq(tufo[1]['inet:web:follows:follower'], acct1)
                self.eq(tufo[1]['inet:web:follows:followee'], acct2)
                self.eq(tufo[1]['inet:web:follows:seen:min'], 0)
                self.eq(tufo[1]['inet:web:follows:seen:max'], 1)
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))
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
                self.eq(tufo[1]['inet:web:post'], webpost_valu)
                self.eq(tufo[1]['inet:web:post:acct'], 'vertex.link/person1')
                self.eq(tufo[1]['inet:web:post:acct:site'], 'vertex.link')
                self.eq(tufo[1]['inet:web:post:acct:user'], 'person1')
                self.eq(tufo[1]['inet:web:post:text'], 'my cool post')
                self.eq(tufo[1]['inet:web:post:replyto'], '0' * 32)
                self.eq(tufo[1]['inet:web:post:url'], 'https://vertex.link/blog/1')
                self.eq(tufo[1]['inet:web:post:file'], 'd41d8cd98f00b204e9800998ecf8427e')
                self.eq(tufo[1]['inet:web:post:time'], 12345)
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))

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
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))

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
                self.eq(tufo[1]['file:imgof'], new_imgof_valu)
                self.eq(tufo[1]['file:imgof:file'], '0' * 32)
                self.eq(tufo[1]['file:imgof:xref'], 'inet:web:acct=vertex.link/person1')
                self.eq(tufo[1]['file:imgof:xref:prop'], 'inet:web:acct')
                self.eq(tufo[1]['file:imgof:xref:strval'], 'vertex.link/person1')
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))

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
                self.eq(tufo[1]['file:txtref'], new_txtref_valu)
                self.eq(tufo[1]['file:txtref:file'], '0' * 32)
                self.eq(tufo[1]['file:txtref:xref'], 'inet:web:group=vertex.link/group0')
                self.eq(tufo[1]['file:txtref:xref:prop'], 'inet:web:group')
                self.eq(tufo[1]['file:txtref:xref:strval'], 'vertex.link/group0')
                self.eq(['hehe', 'hehe.hoho'], sorted(s_tufo.tags(tufo)))

                # assert that no old data remains
                tufos = core.getTufosByProp('file:txtref', txtref_valu)
                self.len(0, tufos)
