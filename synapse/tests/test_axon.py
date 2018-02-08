import struct

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
asdfsha512 = hashlib.sha512(b'asdfasdf').hexdigest()

logger = logging.getLogger(__name__)

def u64(x):
    return struct.pack('>Q', x)

class AxonTest(SynTest):

    def test_axon_blob(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0) as bst0:

                buid = b'\x56' * 32
                blobs = (
                    (buid + u64(0), b'asdf'),
                    (buid + u64(1), b'qwer'),
                    (buid + u64(2), b'hehe'),
                    (buid + u64(3), b'haha'),
                )

                bst0.save(blobs)

                retn = b''.join(bst0.load(buid))
                self.eq(retn, b'asdfqwerhehehaha')

                path1 = os.path.join(dirn, 'blob1')

                with s_axon.BlobStor(path1) as bst1:

                    bst1._saveCloneRows(bst0.clone(0))

                    retn = b''.join(bst1.load(buid))
                    self.eq(retn, b'asdfqwerhehehaha')

    def test_axon_base(self):

        with self.getTestDir() as dirn:

            with s_axon.Axon(dirn) as axon:

                self.false(axon.has('md5', asdfmd5))

                axon.eat((b'asdfasdf',))

                self.true(axon.has('md5', asdfmd5))
                self.true(axon.has('sha1', asdfsha1))
                self.true(axon.has('sha256', asdfsha256))
                self.true(axon.has('sha512', asdfsha512))

                answ = list(axon.find('sha256', asdfsha256))
                self.len(1, answ)

                byts = b''.join(axon.bytes('sha256', asdfsha256))
                self.eq(b'asdfasdf', byts)

                # test upload by hacking blocksize...
                axon.blocksize = 2
                axon.upload((b'qw', b'er', b'q', b'wer'))

                qwersha256 = hashlib.sha256(b'qwerqwer').hexdigest()

                self.true(axon.has('sha256', qwersha256))

                byts = b''.join(axon.bytes('sha256', qwersha256))
                self.eq(b'qwerqwer', byts)

    def newp_axon_cell(self):

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
