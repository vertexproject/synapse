# -*- coding: UTF-8 -*-
from __future__ import absolute_import, unicode_literals

import synapse.lib.tufo as s_tufo

from synapse.tests.common import *

class InetModelTest(SynTest):

    def test_model_inet_email(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:email', 'visi@vertex.link')
            self.eq(t0[1].get('inet:email:user'), 'visi')
            self.eq(t0[1].get('inet:email:fqdn'), 'vertex.link')

    def test_model_inet_passwd(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:passwd', 'secret')
            self.eq(t0[1].get('inet:passwd:md5'), '5ebe2294ecd0e0f08eab7690d2a6ee69')
            self.eq(t0[1].get('inet:passwd:sha1'), 'e5e9fa1ba31ecd1ae84f75caaa474f3a663f05f4')
            self.eq(t0[1].get('inet:passwd:sha256'), '2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b')

    def test_model_inet_mac(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:mac', '00:01:02:03:04:05')
            self.eq(t0[1].get('inet:mac:vendor'), '??')

            t1 = core.formTufoByProp('inet:mac', 'FF:ee:dd:cc:bb:aa', vendor='woot')
            self.eq(t1[1].get('inet:mac'), 'ff:ee:dd:cc:bb:aa')
            self.eq(t1[1].get('inet:mac:vendor'), 'woot')

    def test_model_inet_ipv4(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:ipv4', '16909060')
            self.eq(t0[1].get('inet:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:ipv4:asn'), -1)

    def test_model_inet_ipv6(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:ipv6', '0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:ipv6'), '::1')
            self.eq(t0[1].get('inet:ipv6:asn'), -1)

            self.eq(core.getTypeRepr('inet:ipv6', '0:0:0:0:0:0:0:1'), '::1')
            self.eq(core.getTypeRepr('inet:ipv6', '::1'), '::1')

    def test_model_inet_cidr4(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:cidr4', '1.2.3.4/24')

            self.eq(t0[1].get('inet:cidr4'), '1.2.3.0/24')
            self.eq(t0[1].get('inet:cidr4:mask'), 24)
            self.eq(t0[1].get('inet:cidr4:ipv4'), 0x01020300)

    def test_model_inet_asnet4(self):

        with s_cortex.openurl('ram:///') as core:

            t0 = core.formTufoByProp('inet:asnet4', '54959/1.2.3.4-5.6.7.8')

            self.eq(t0[1].get('inet:asnet4:asn'), 54959)
            self.eq(t0[1].get('inet:asnet4:net4'), '1.2.3.4-5.6.7.8')
            self.eq(t0[1].get('inet:asnet4:net4:min'), 0x01020304)
            self.eq(t0[1].get('inet:asnet4:net4:max'), 0x05060708)

            self.nn(core.getTufoByProp('inet:asn', 54959))
            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            self.nn(core.getTufoByProp('inet:ipv4', 0x05060708))

    def test_model_inet_fqdn(self):
        with s_cortex.openurl('ram:///') as core:
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
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
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

    def test_model_inet_srv6_types(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
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

        with s_cortex.openurl('ram:///') as core:
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

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:netuser'
            valu = '%s/%s' % ('xn--tst-6la.xn--xampl-3raf.link', 'user')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:netuser:site'), 'xn--tst-6la.xn--xampl-3raf.link')
            self.eq(tufo[1].get('inet:netuser'), 'tèst.èxamplè.link/user')
            idna_valu = 'xn--tst-6la.xn--xampl-3raf.link'

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:email'
            valu = '%s@%s' % ('user', 'tèst.èxamplè.link')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:email:fqdn'), 'xn--tst-6la.xn--xampl-3raf.link')
            self.eq(tufo[1].get('inet:email'), 'user@xn--tst-6la.xn--xampl-3raf.link')

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:url'
            valu = '%s://%s/%s' % ('https', 'xn--tst-6la.xn--xampl-3raf.link', 'things')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:url'), 'https://xn--tst-6la.xn--xampl-3raf.link/things') # hostpart is not normed in inet:url

    def test_model_inet_fqdn_set_sfx(self):
        with s_cortex.openurl('ram:///') as core:
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
        with s_cortex.openurl('ram:///') as core:
            self.eq(core.getTypeCast('inet:defang', '1[.]2[.]3[.]4'), '1.2.3.4')

    def test_model_inet_whoisemail(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('inet:whois:regmail', ('WOOT.COM', 'visi@vertex.LINK'))
            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))
            self.eq(node[1].get('inet:whois:regmail:email'), 'visi@vertex.link')
            self.eq(node[1].get('inet:whois:regmail:fqdn'), 'woot.com')

    def test_model_inet_url_fields(self):
        with s_cortex.openurl('ram:///') as core:
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

        with s_cortex.openurl('sqlite:///:memory:') as core:

            core.setConfOpt('enforce', 1)

            node0 = core.formTufoByProp('inet:netpost', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            iden = node0[1].get('inet:netpost')

            node1 = core.formTufoByProp('inet:netpost', ('vertex.link/visi', 'whos there'), time='20141217010102', replyto=iden)

            self.nn(core.getTufoByProp('inet:netuser', 'vertex.link/visi'))

            self.eq(node0[1].get('inet:netpost:netuser:user'), 'visi')
            self.eq(node1[1].get('inet:netpost:netuser:user'), 'visi')

            self.eq(node0[1].get('inet:netpost:netuser:site'), 'vertex.link')
            self.eq(node1[1].get('inet:netpost:netuser:site'), 'vertex.link')

            self.eq(node0[1].get('inet:netpost'), node1[1].get('inet:netpost:replyto'))

    def test_model_inet_netmesg(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:netmesg', ('VERTEX.link/visi', 'vertex.LINK/hehe', '20501217'), text='hehe haha')
            self.nn(node)
            self.eq(node[1].get('inet:netmesg:from'), 'vertex.link/visi')
            self.eq(node[1].get('inet:netmesg:to'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:netmesg:time'), 2554848000000)
            self.eq(node[1].get('inet:netmesg:text'), 'hehe haha')

            self.nn(core.getTufoByProp('inet:netuser', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:netuser', 'vertex.link/hehe'))

    def test_model_inet_netmemb(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:netmemb', ('VERTEX.link/visi', 'vertex.LINK/kenshoto'), joined='20501217')

            self.nn(node)

            self.eq(node[1].get('inet:netmemb:joined'), 2554848000000)
            self.eq(node[1].get('inet:netmemb:user'), 'vertex.link/visi')
            self.eq(node[1].get('inet:netmemb:group'), 'vertex.link/kenshoto')

            self.nn(core.getTufoByProp('inet:netuser', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:netgroup', 'vertex.link/kenshoto'))

    def test_model_inet_follows(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            props = {'seen:min': '20501217', 'seen:max': '20501217'}
            node = core.formTufoByProp('inet:follows', ('VERTEX.link/visi', 'vertex.LINK/hehe'), **props)

            self.nn(node)
            self.eq(node[1].get('inet:follows:follower'), 'vertex.link/visi')
            self.eq(node[1].get('inet:follows:followee'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:follows:seen:min'), 2554848000000)
            self.eq(node[1].get('inet:follows:seen:max'), 2554848000000)

    def test_model_inet_ipv4_raise(self):
        with s_cortex.openurl('ram:///') as core:
            self.raises(BadTypeValu, core.formTufoByProp, 'inet:ipv4', 'lolololololol')

    def test_model_inet_urlfile(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

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
        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:whois:contact', '(woot.com@20501217,admin)')

            self.eq(len(core.eval('inet:fqdn="woot.com"')), 1)
            self.eq(len(core.eval('inet:whois:rec="woot.com@20501217"')), 1)
            self.eq(len(core.eval('inet:whois:contact:rec="woot.com@20501217"')), 1)

    def test_model_fqdn_punycode(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:fqdn', 'www.xn--heilpdagogik-wiki-uqb.de')

            fqdn = node[1].get('inet:fqdn')

            self.eq(fqdn, 'www.xn--heilpdagogik-wiki-uqb.de')
            self.eq(core.getTypeRepr('inet:fqdn', fqdn), 'www.heilpädagogik-wiki.de')

            self.raises(BadTypeValu, core.getTypeNorm, 'inet:fqdn', '!@#$%')

    def test_model_inet_netlogon(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            tick = now()
            # Form via list
            t0 = core.formTufoByProp('inet:netlogon', ['vertex.link/pennywise',
                                                       tick,
                                                       False])
            t1 = core.formTufoByProp('inet:netlogon', ['vertex.link/pennywise',
                                                       tick,
                                                       True])
            # form via string
            tick = tick + 1
            t2 = core.formTufoByProp('inet:netlogon', '(vertex.link/pennywise,{},0)'.format(tick))
            t3 = core.formTufoByProp('inet:netlogon', '(vertex.link/pennywise,{},1)'.format(tick))

            self.nn(t0)
            self.nn(t1)
            self.nn(t2)
            self.nn(t3)

            self.eq(t0[1].get('inet:netlogon:user'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:netlogon:time'), tick - 1)
            self.eq(t0[1].get('inet:netlogon:status'), 0)

            self.eq(t1[1].get('inet:netlogon:status'), 1)

            # Pivot from a netuser to the netlogon forms via storm
            self.nn(core.getTufoByProp('inet:netuser', 'vertex.link/pennywise'))
            nodes = core.eval('inet:netuser=vertex.link/pennywise inet:netuser -> inet:netlogon:user')
            self.eq(len(nodes), 4)
            self.eq(list({s_tufo.ndef(node)[0] for node in nodes}), ['inet:netlogon'])

            # Cannot set ro props
            _t0 = core.setTufoProps(t0, user='vertex.link/invisig0th', time=0, status=1)
            self.eq(_t0[1].get('inet:netlogon:user'), 'vertex.link/pennywise')
            self.eq(_t0[1].get('inet:netlogon:time'), tick - 1)
            self.eq(_t0[1].get('inet:netlogon:status'), 0)

            # Can set mutable props
            t0 = core.setTufoProps(t0, ipv4=0x01020304, logout=tick + 1, ipv6='0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:netlogon:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:netlogon:logout'), tick + 1)
            self.eq(t0[1].get('inet:netlogon:logout') - t0[1].get('inet:netlogon:time'), 2)
            self.eq(t0[1].get('inet:netlogon:ipv6'), '::1')

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
