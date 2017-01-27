import synapse.cortex as s_cortex

from synapse.tests.common import *

class InetModelTest(SynTest):

    def test_model_inet_fqdn(self):
        with s_cortex.openurl('ram:///') as core:
            t0 = core.formTufoByProp('inet:fqdn','com', sfx=1)
            t1 = core.formTufoByProp('inet:fqdn','woot.com')

            self.eq( t0[1].get('inet:fqdn:sfx'), 1 )
            self.eq( t1[1].get('inet:fqdn:zone'), 1 )
            self.eq( t1[1].get('inet:fqdn:parent'), 'com' )

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
