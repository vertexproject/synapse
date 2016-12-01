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
