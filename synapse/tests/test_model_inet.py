# -*- coding: UTF-8 -*-
from __future__ import absolute_import,unicode_literals

import synapse.cortex as s_cortex

from synapse.tests.common import *

class InetModelTest(SynTest):

    def test_model_inet_email(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:email','visi@vertex.link')
            self.eq( t0[1].get('inet:email:user'), 'visi' )
            self.eq( t0[1].get('inet:email:fqdn'), 'vertex.link' )

    def test_model_inet_passwd(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:passwd','secret')
            self.eq( t0[1].get('inet:passwd:md5'), '5ebe2294ecd0e0f08eab7690d2a6ee69' )
            self.eq( t0[1].get('inet:passwd:sha1'), 'e5e9fa1ba31ecd1ae84f75caaa474f3a663f05f4' )
            self.eq( t0[1].get('inet:passwd:sha256'), '2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b' )

    def test_model_inet_mac(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:mac','00:01:02:03:04:05')
            self.eq( t0[1].get('inet:mac:vendor'), '??')

            t1 = core.formTufoByProp('inet:mac','FF:ee:dd:cc:bb:aa', vendor='woot')
            self.eq( t1[1].get('inet:mac'), 'ff:ee:dd:cc:bb:aa' )
            self.eq( t1[1].get('inet:mac:vendor'), 'woot' )

    def test_model_inet_passwd(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:passwd','secret')
            self.eq( t0[1].get('inet:passwd:md5'), '5ebe2294ecd0e0f08eab7690d2a6ee69' )
            self.eq( t0[1].get('inet:passwd:sha1'), 'e5e9fa1ba31ecd1ae84f75caaa474f3a663f05f4' )
            self.eq( t0[1].get('inet:passwd:sha256'), '2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b' )

    def test_model_inet_ipv4(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByFrob('inet:ipv4','16909060')
            self.eq( t0[1].get('inet:ipv4'), 0x01020304 )

    def test_model_inet_cidr4(self):

        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:cidr4','1.2.3.4/24')

            self.eq( t0[1].get('inet:cidr4'), '1.2.3.0/24')
            self.eq( t0[1].get('inet:cidr4:mask'), 24 )
            self.eq( t0[1].get('inet:cidr4:ipv4'), 0x01020300 )

    def test_model_inet_asnet4(self):

        with s_cortex.openurl('ram:///') as core:

            t0 = core.formTufoByProp('inet:asnet4','54959/1.2.3.4-5.6.7.8')

            self.eq( t0[1].get('inet:asnet4:asn'), 54959 )
            self.eq( t0[1].get('inet:asnet4:net4'), '1.2.3.4-5.6.7.8' )
            self.eq( t0[1].get('inet:asnet4:net4:min'), 0x01020304 )
            self.eq( t0[1].get('inet:asnet4:net4:max'), 0x05060708 )

            self.assertIsNotNone( core.getTufoByProp('inet:asn', 54959) )
            self.assertIsNotNone( core.getTufoByProp('inet:ipv4', 0x01020304) )
            self.assertIsNotNone( core.getTufoByProp('inet:ipv4', 0x05060708) )

    def test_model_inet_fqdn(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:fqdn','com', sfx=1)
            t1 = core.formTufoByProp('inet:fqdn','woot.com')

            self.eq( t0[1].get('inet:fqdn:host'), 'com' )
            self.eq( t0[1].get('inet:fqdn:domain'), None )
            self.eq( t0[1].get('inet:fqdn:sfx'), 1 )
            self.eq( t0[1].get('inet:fqdn:zone'), 0 )

            self.eq( t1[1].get('inet:fqdn:host'), 'woot' )
            self.eq( t1[1].get('inet:fqdn:domain'), 'com' )
            self.eq( t1[1].get('inet:fqdn:sfx'), 0 )
            self.eq( t1[1].get('inet:fqdn:zone'), 1 )

    def test_model_inet_fqdn_unicode(self):

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:fqdn'
            idna_valu = 'xn--tst.xampl.link-vjbdf'
            unicode_valu = 'tèst.èxamplè.link'
            parents = (
                    ('èxamplè.link', {'inet:fqdn:host': 'èxamplè', 'inet:fqdn:domain': 'link', 'inet:fqdn:zone': 1, 'inet:fqdn:sfx': 0}),
                    ('link', {'inet:fqdn:host': 'link', 'inet:fqdn:domain': None, 'inet:fqdn:zone': 0, 'inet:fqdn:sfx': 1}),
            )
            idna_tufo = core.formTufoByFrob(prop, idna_valu)
            self.eq(idna_tufo[1].get('inet:fqdn:host'), 'tèst')
            self.eq(idna_tufo[1].get('inet:fqdn:domain'), 'èxamplè.link')
            self.eq(idna_tufo[1].get('inet:fqdn:zone'), 0)
            self.eq(idna_tufo[1].get('inet:fqdn:sfx'), 0)

            for parent_fqdn, parent_props in parents:
                parent_tufo = core.getTufoByProp(prop, parent_fqdn)
                for key in parent_props:
                    self.eq(parent_tufo[1].get(key), parent_props[key])

            idna_tufo = core.formTufoByFrob(prop, idna_valu)
            unicode_tufo = core.formTufoByFrob(prop, unicode_valu)
            self.eq(unicode_tufo, idna_tufo)

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:netuser'
            valu = '%s/%s' % ('xn--tst.xampl.link-vjbdf', 'user')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:netuser:site'), 'tèst.èxamplè.link')
            self.eq(tufo[1].get('inet:netuser'), 'tèst.èxamplè.link/user')

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:email'
            valu = '%s@%s' % ('user', 'xn--tst.xampl.link-vjbdf')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:email:fqdn'), 'tèst.èxamplè.link')
            self.eq(tufo[1].get('inet:email'), 'user@tèst.èxamplè.link')

        with s_cortex.openurl('ram:///') as core:
            prop = 'inet:url'
            valu = '%s://%s/%s' % ('https', 'xn--tst.xampl.link-vjbdf', 'things')
            tufo = core.formTufoByProp(prop, valu)
            self.eq(tufo[1].get('inet:url'), 'https://xn--tst.xampl.link-vjbdf/things') # hostpart is not normed in inet:url

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
