import synapse.axon as s_axon
import synapse.cortex as s_cortex

from synapse.tests.common import *

class DnsModelTest(SynTest):

    def test_model_file_bytes(self):

        with s_cortex.openurl('ram:///') as core:

            hset = s_axon.HashSet()
            hset.update(b'visi')

            valu,props = hset.guid()
            t0 = core.formTufoByProp('file:bytes',valu,**props)

            self.eq( t0[1].get('file:bytes:size'), 4)

            self.eq( t0[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27' )
            self.eq( t0[1].get('file:bytes:md5'), '1b2e93225959e3722efed95e1731b764')
            self.eq( t0[1].get('file:bytes:sha1'), '93de0c7d579384feb3561aa504acd8f23f388040')
            self.eq( t0[1].get('file:bytes:sha256'), 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')
            self.eq( t0[1].get('file:bytes:sha512'), '8238be12bcc3c10da7e07dbea528e9970dc809c07c5aef545a14e5e8d2038563b29c2e818d167b06e6a33412e6beb8347fcc44520691347aea9ee21fcf804e39')

