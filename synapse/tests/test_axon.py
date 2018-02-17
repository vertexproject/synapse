import os
import struct

import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron

import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

asdfhex = hashlib.sha256(b'asdfasdf').hexdigest()
asdfsha256 = hashlib.sha256(b'asdfasdf').digest()

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

                # Order doesn't matter since we're indexed chunks
                buid2 = b'\x01' * 32
                blobs = (
                    (buid2 + u64(3), b'sale'),
                    (buid2 + u64(1), b'b33f'),
                    (buid2 + u64(0), b'dead'),
                    (buid2 + u64(2), b'f0re'),
                )
                bst0.save(blobs)
                retn = b''.join(bst0.load(buid2))
                self.eq(retn, b'deadb33ff0resale')

                path1 = os.path.join(dirn, 'blob1')

                with s_axon.BlobStor(path1) as bst1:

                    bst1.addCloneRows(bst0.clone(0))

                    retn = b''.join(bst1.load(buid))
                    self.eq(retn, b'asdfqwerhehehaha')
                    retn = b''.join(bst1.load(buid2))
                    self.eq(retn, b'deadb33ff0resale')

    def test_axon_blob_stat(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0) as bst0:

                buid = b'\x56' * 32
                blobs = (
                    (buid + u64(0), os.urandom(1000)),
                    (buid + u64(1), b'qwer'),
                    (buid + u64(2), b'hehe'),
                    (buid + u64(3), b'haha'),
                )  # 4 blocks, size 1000 + 4 + 4 + 4 = 1012 bytes

                stats = bst0.stat()
                self.eq(stats, {})

                bst0.save(blobs[0:1])
                stats = bst0.stat()
                self.eq(stats, {'bytes': 1000, 'blocks': 1})

                bst0.save(blobs[1:])
                stats = bst0.stat()
                self.eq(stats, {'bytes': 1012, 'blocks': 4})

    def test_axon_blob_metrics(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0) as bst0:

                buid = b'\x56' * 32
                blobs = (
                    (buid + u64(0), os.urandom(1000)),
                    (buid + u64(1), b'qwer'),
                    (buid + u64(2), b'hehe'),
                    (buid + u64(3), b'haha'),
                )  # 4 blocks, size 1000 + 4 + 4 + 4 = 1012 bytes

                metrics = sorted(list(bst0.metrics()))
                self.eq(metrics, [])

                bst0.save(blobs[0:1])
                metrics = []
                for item in bst0.metrics():
                    item[1].pop('time')
                    metrics.append(item[1])
                self.eq(metrics, [{'size': 1000, 'blocks': 1}])

                bst0.save(blobs[1:])
                metrics = []
                for item in bst0.metrics():
                    item[1].pop('time')
                    metrics.append(item[1])
                self.eq(metrics, [{'size': 1000, 'blocks': 1}, {'blocks': 3, 'size': 12}])

    def test_axon_cell(self):

        # implement as many tests as possible in this one
        # since it *has* to use a neuron to work correctly

        # put all the things that need fini() into a BusRef...
        with self.getTestDir() as dirn:

            with s_eventbus.BusRef() as bref:

                # neur00 ############################################
                conf = {'host': 'localhost', 'bind': '127.0.0.1'}
                path = s_common.gendir(dirn, 'neuron')

                neur = s_neuron.Neuron(path, conf)
                bref.put('neur00', neur)

                root = neur.getCellAuth()
                addr = neur.getCellAddr()

                # blob00 ############################################
                path = s_common.gendir(dirn, 'blob00')
                authblob00 = neur.genCellAuth('blob00')
                s_msgpack.dumpfile(authblob00, os.path.join(path, 'cell.auth'))

                blob00 = s_axon.BlobCell(path, conf)
                bref.put('blob00', blob00)
                self.true(blob00.cellpool.neurwait(timeout=3))

                user = s_neuron.CellUser(root)
                blob00sess = user.open(blob00.getCellAddr(), timeout=3)

                mesg = ('blob:stat', {})
                ok, retn = blob00sess.call(mesg, timeout=3)
                self.true(ok)
                self.eq(retn, {})  # Nothing there yet

                # blob01 ############################################
                path = s_common.gendir(dirn, 'blob01')
                authblob01 = neur.genCellAuth('blob01')
                s_msgpack.dumpfile(authblob01, os.path.join(path, 'cell.auth'))

                blob01conf = dict(conf)
                blob01conf['blob:cloneof'] = 'blob00@localhost'

                blob01 = s_axon.BlobCell(path, blob01conf)
                bref.put('blob01', blob01)
                self.true(blob01.cellpool.neurwait(timeout=3))
                blob01wait = blob01.waiter(1, 'blob:clone:rows')

                # axon00 ############################################
                path = s_common.gendir(dirn, 'axon00')
                authaxon00 = neur.genCellAuth('axon00')
                s_msgpack.dumpfile(authaxon00, os.path.join(path, 'cell.auth'))
                axonconf = {
                    'host': 'localhost',
                    'bind': '127.0.0.1',
                    'axon:blobs': ('blob00@localhost',),
                }

                axon00 = s_axon.AxonCell(path, axonconf)
                self.true(axon00.cellpool.neurwait(timeout=3))
                #####################################################

                sess = user.open(axon00.getCellAddr(), timeout=3)

                # wait for the axon to have blob00
                ready = False

                for i in range(30):

                    if axon00.blobs.items():
                        ready = True
                        break

                    time.sleep(0.1)

                self.true(ready)

                axon = s_axon.Axon(sess)

                self.len(1, axon.wants([asdfhex]))

                self.eq(1, axon.save([b'asdfasdf'], timeout=3))

                self.len(0, axon.wants([asdfhex], timeout=3))

                self.eq(b'asdfasdf', b''.join(axon.bytes(asdfhex, timeout=3)))

                stat = axon.stat(timeout=3)
                self.eq(1, stat.get('files'))
                self.eq(8, stat.get('bytes'))

                newp = s_common.ehex(os.urandom(32))
                def loop():
                    s_common.spin(axon.bytes(newp))

                self.raises(s_exc.RetnErr, loop)

                qwerhash = hashlib.sha256(b'qwerqwer').hexdigest()

                self.eq(qwerhash, axon.upload([b'qwer', b'qwer'], timeout=3))

                self.len(0, axon.wants([qwerhash]))
                self.eq(b'qwerqwer', b''.join(axon.bytes(qwerhash, timeout=3)))
