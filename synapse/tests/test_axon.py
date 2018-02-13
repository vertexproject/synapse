import struct

import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron

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
