import struct

import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron

import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

logger = logging.getLogger(__name__)

bbuf = s_const.mebibyte * 130 * b'\00'
nullhash = hashlib.sha256(b'').digest()
bbufhash = hashlib.sha256(bbuf).digest()
asdfsha256 = hashlib.sha256(b'asdfasdf').digest()

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

                # We do not have bytes for buid2 yet
                bl = []
                for byts in bst0.load(buid2):
                    bl.append(byts)
                self.eq(bl, [])

                bst0.save(blobs)
                retn = b''.join(bst0.load(buid2))
                self.eq(retn, b'deadb33ff0resale')

                # We can store and retrieve an empty string
                buid3 = b'\x02' * 32
                blobs = (
                    (buid3 + u64(0), b''),
                )
                bst0.save(blobs)
                bl = []
                for byts in bst0.load(buid3):
                    bl.append(byts)
                self.eq(bl, [b''])
                retn = b''.join(bl)
                self.eq(retn, b'')

                path1 = os.path.join(dirn, 'blob1')

                with s_axon.BlobStor(path1) as bst1:

                    bst1.addCloneRows(bst0.clone(0))

                    retn = b''.join(bst1.load(buid))
                    self.eq(retn, b'asdfqwerhehehaha')
                    retn = b''.join(bst1.load(buid2))
                    self.eq(retn, b'deadb33ff0resale')
                    retn = b''.join(bst0.load(buid3))
                    self.eq(retn, b'')

                    bst1.addCloneRows([])  # Empty addCloneRows call for coverage

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

                metrics = []
                mesg = ('blob:metrics', {})
                with blob00sess.chan() as bchan:
                    bchan.setq()
                    bchan.tx(mesg)
                    for ok, retn in bchan.rxwind(timeout=30):
                        self.true(ok)
                        retn[1].pop('time')
                        metrics.append(retn[1])
                self.eq(metrics, [])  # No data yet

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

                newp = os.urandom(32)
                ok, retn = sess.call(('axon:wants', {'hashes': [newp]}))
                self.true(ok)
                self.eq(retn, (newp,))

                # wait for the axon to have blob00
                ready = False

                for i in range(30):

                    if axon00.blobs.items():
                        ready = True
                        break

                    time.sleep(0.1)

                self.true(ready)

                mesg = ('axon:save', {'files': [b'asdfasdf']})
                ok, retn = sess.call(mesg, timeout=3)
                self.true(ok)
                self.eq(retn, True)

                mesg = ('blob:stat', {})
                ok, retn = blob00sess.call(mesg, timeout=3)
                self.true(ok)
                self.eq(retn, {'blocks': 1, 'bytes': 8})  # Now it should have data

                metrics = []
                mesg = ('blob:metrics', {'offs': 99999999})
                with blob00sess.chan() as bchan:
                    bchan.setq()
                    bchan.tx(mesg)
                    for ok, retn in bchan.rxwind(timeout=30):
                        self.true(ok)
                        retn[1].pop('time')
                        metrics.append(retn[1])
                self.eq(metrics, [])  # No data because of higher offset

                metrics = []
                mesg = ('blob:metrics', {})
                with blob00sess.chan() as bchan:
                    bchan.setq()
                    bchan.tx(mesg)
                    for ok, retn in bchan.rxwind(timeout=30):
                        self.true(ok)
                        retn[1].pop('time')
                        metrics.append(retn[1])
                self.eq(metrics, [{'blocks': 1, 'size': 8}])  # Same data as above in stat

                mesg = ('axon:save', {'files': [b'asdfasdf']})
                ok, retn = sess.call(mesg, timeout=3)
                self.true(ok)
                self.eq(retn, False)

                mesg = ('axon:save', {})
                ok, retn = sess.call(mesg, timeout=3)
                self.true(ok)
                self.eq(retn, False)

                ok, retn = sess.call(('axon:wants', {'hashes': [asdfsha256]}))
                self.true(ok)
                self.eq(retn, ())

                # lets see if the bytes make it to the blob clone...
                self.nn(blob01wait.wait(timeout=10))
                valu = b''.join(blob01.blobs.load(asdfsha256))
                self.eq(valu, b'asdfasdf')

                # no such hash file...
                mesg = ('axon:bytes', {'sha256': newp})
                with sess.task(mesg) as chan:
                    ok, retn = chan.next(timeout=3)
                    self.false(ok)
                    self.eq(retn[0], 'FileNotFound')

                mesg = ('axon:bytes', {'sha256': asdfsha256})
                with sess.task(mesg) as chan:
                    ok, retn = chan.next(timeout=3)
                    self.eq((ok, retn), (True, 'blob00@localhost'))

                    full = b''
                    for ok, byts in chan.rxwind(timeout=3):
                        self.true(ok)
                        full += byts

                    self.eq(full, b'asdfasdf')

                ok, retn = sess.call(('axon:stat', {}), timeout=3)
                self.true(ok)

                self.eq(retn.get('files'), 1)
                self.eq(retn.get('bytes'), 8)

                ok, retn = sess.call(('axon:metrics', {'offs': 0}), timeout=3)
                self.true(ok)
                self.eq(retn[0][1].get('size'), 8)
                self.eq(retn[0][1].get('cell'), 'blob00@localhost')
