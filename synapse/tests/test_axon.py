import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron
#import synapse.daemon as s_daemon
#import synapse.telepath as s_telepath

#import synapse.lib.tufo as s_tufo
#import synapse.lib.service as s_service
import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

asdfmd5 = hashlib.md5(b'asdfasdf').hexdigest()
asdfsha1 = hashlib.sha1(b'asdfasdf').hexdigest()
asdfsha256 = hashlib.sha256(b'asdfasdf').hexdigest()

logger = logging.getLogger(__name__)

class AxonTest(SynTest):

    def test_axon_base(self):

        with self.getTestDir() as dirn:

            with s_axon.Axon(dirn) as axon:

                self.false(axon.has('md5', asdfmd5))

                iden = axon.alloc(8, sha256=asdfsha256)

                self.nn(iden)
                self.true(axon.chunk(iden, b'asdfasdf'))

                self.len(1, list(axon.files(0, 100)))

                self.none(axon.alloc(8, sha256=asdfsha256))

                self.false(axon.eat(b'asdfasdf'))

                self.true(axon.has('md5', asdfmd5))
                self.true(axon.has('sha256', asdfsha256))

                answ = list(axon.find('sha256', asdfsha256))
                self.len(1, answ)

                byts = b''.join(axon.bytes('sha256', asdfsha256))
                self.eq(b'asdfasdf', byts)

    def test_axon_cell(self):

        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}
            with s_axon.AxonCell(dirn, conf=conf) as cell:

                port = cell.getCellPort()
                auth = cell.genUserAuth('visi@vertex.link')

                addr = ('127.0.0.1', port)

                axon = s_axon.AxonUser(auth, addr, timeout=4)

                self.true(axon.eat(b'asdfasdf'))
                self.false(axon.eat(b'asdfasdf'))

                self.true(axon.has('md5', asdfmd5))

                byts = b''.join(axon.bytes('md5', asdfmd5))
                self.eq(byts, b'asdfasdf')
