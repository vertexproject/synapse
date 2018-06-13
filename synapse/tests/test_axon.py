import os
import time
import struct
import hashlib
import logging

import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron
import synapse.lib.msgpack as s_msgpack

import synapse.lib.cell as s_cell
import synapse.tests.common as s_test

import unittest

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4585

nullhash = hashlib.sha256(b'').digest()
bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(b'asdfasdf').digest()
hehahash = hashlib.sha256(b'hehehaha').digest()
ohmyhash = hashlib.sha256(b'ohmyohmy').digest()
qwerhash = hashlib.sha256(b'qwerqwer').digest()

def u64(x):
    return struct.pack('>Q', x)

class AxonTest(s_test.SynTest):

    def test_axon_blob(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                tbuid = b'\x56' * 32
                blobs = (
                    (tbuid + u64(0), b'asdf'),
                    (tbuid + u64(1), b'qwer'),
                    (tbuid + u64(2), b'hehe'),
                    (tbuid + u64(3), b'haha'),
                )

                bst0.save(blobs)

                retn = b''.join(bst0.load(tbuid))
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

                with s_axon.BlobStor(path1, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst1:

                    bst1.addCloneRows(bst0.clone(0))

                    retn = b''.join(bst1.load(tbuid))
                    self.eq(retn, b'asdfqwerhehehaha')
                    retn = b''.join(bst1.load(buid2))
                    self.eq(retn, b'deadb33ff0resale')
                    retn = b''.join(bst0.load(buid3))
                    self.eq(retn, b'')

                    bst1.addCloneRows([])  # Empty addCloneRows call for coverage

    def test_axon_blob_stat(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                tbuid = b'\x56' * 32
                blobs = (
                    (tbuid + u64(0), os.urandom(1000)),
                    (tbuid + u64(1), b'qwer'),
                    (tbuid + u64(2), b'hehe'),
                    (tbuid + u64(3), b'haha'),
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
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                tbuid = b'\x56' * 32
                blobs = (
                    (tbuid + u64(0), os.urandom(1000)),
                    (tbuid + u64(1), b'qwer'),
                    (tbuid + u64(2), b'hehe'),
                    (tbuid + u64(3), b'haha'),
                )  # 4 blocks, size 1000 + 4 + 4 + 4 = 1012 bytes

                metrics = sorted(list(bst0.metrics()))
                self.eq(metrics, [])

                bst0.save(blobs[0:1])
                metrics = []
                for item in bst0.metrics():
                    item[1].pop('time')
                    metrics.append(item[1])
                tooks = [m.pop('took') for m in metrics]  # remove took since it may vary
                self.eq(metrics, [{'size': 1000, 'blocks': 1}])
                self.len(1, tooks)
                # These are time based and cannot be promised to be a particular value
                for took in tooks:
                    self.lt(took, 10000)

                bst0.save(blobs[1:])
                metrics = []
                for item in bst0.metrics():
                    item[1].pop('time')
                    metrics.append(item[1])
                tooks = [m.pop('took') for m in metrics]  # remove took since it may vary
                self.eq(metrics, [{'size': 1000, 'blocks': 1}, {'blocks': 3, 'size': 12}])
                self.len(2, tooks)
                # These are time based and cannot be promised to be a particular value
                for took in tooks:
                    self.lt(took, 10000)

    def test_axon_cell(self):
        raise unittest.SkipTest()

        # implement as many tests as possible in this one
        # since it *has* to use a neuron to work correctly

        # put all the things that need fini() into a BusRef...
        with self.getTestDir() as dirn:

            with s_eventbus.BusRef() as bref:

                # neur00 ############################################
                # Set port to zero to allow a port to be automatically assigned during testing
                conf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0}
                path = s_common.gendir(dirn, 'neuron')
                logger.debug('Bringing Neuron online')
                neur = s_neuron.Neuron(path, conf)
                bref.put('neur00', neur)

                root = neur.getCellAuth()
                addr = neur.getCellAddr()
                nport = addr[1]  # Save the port for later use

                # blob00 ############################################
                path = s_common.gendir(dirn, 'blob00')
                authblob00 = neur.genCellAuth('blob00')
                s_msgpack.dumpfile(authblob00, os.path.join(path, 'cell.auth'))
                logger.debug('Bringing blob00 online')
                conf = {'host': 'localhost', 'bind': '127.0.0.1', 'blob:mapsize': s_test.TEST_MAP_SIZE}
                blob00 = s_axon.BlobCell(path, conf)
                bref.put('blob00', blob00)
                self.true(blob00.cellpool.neurwait(timeout=3))

                user = s_cell.CellUser(root)
                blob00sess = user.open(blob00.getCellAddr(), timeout=3)
                bref.put('blob00sess', blob00sess)

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
                logger.debug('Bringing blob01 online')
                blob01 = s_axon.BlobCell(path, blob01conf)
                bref.put('blob01', blob01)
                self.true(blob01.cellpool.neurwait(timeout=3))
                blob01sess = user.open(blob01.getCellAddr(), timeout=3)
                bref.put('blob01sess', blob01sess)
                blob01wait = blob01.waiter(1, 'blob:clone:rows')

                # axon00 ############################################
                path = s_common.gendir(dirn, 'axon00')
                authaxon00 = neur.genCellAuth('axon00')
                s_msgpack.dumpfile(authaxon00, os.path.join(path, 'cell.auth'))
                axonconf = {
                    'host': 'localhost',
                    'bind': '127.0.0.1',
                    'axon:blobs': ('blob00@localhost',),
                    'axon:mapsize': s_test.TEST_MAP_SIZE,
                }
                logger.debug('Bringing axon00 online')
                axon00 = s_axon.AxonCell(path, axonconf)
                bref.put('axon00', axon00)
                self.true(axon00.cellpool.neurwait(timeout=3))
                #####################################################

                sess = user.open(axon00.getCellAddr(), timeout=3)
                bref.put('sess', sess)

                # wait for the axon to have blob00
                ready = False

                for i in range(30):

                    if axon00.blobs.items():
                        ready = True
                        break

                    time.sleep(0.1)

                self.true(ready)

                axon = s_axon.AxonClient(sess)
                blob = s_axon.BlobClient(blob00sess)
                blob01c = s_axon.BlobClient(blob01sess)

                self.eq((), tuple(axon.metrics()))
                self.eq((), tuple(blob.metrics()))

                self.len(1, axon.wants([asdfhash]))

                # Asking for bytes prior to the bytes being present raises
                self.genraises(RetnErr, axon.bytes, asdfhash, timeout=3)

                self.eq(1, axon.save([b'asdfasdf'], timeout=3))

                self.eq((), tuple(axon.metrics(offs=999999999)))
                self.eq((), tuple(blob.metrics(offs=99999999, timeout=3)))

                metrics = list(blob.metrics(timeout=3))
                self.len(1, metrics)
                self.eq(8, metrics[0][1].get('size'))
                self.eq(1, metrics[0][1].get('blocks'))

                self.len(0, axon.wants([asdfhash], timeout=3))

                self.eq(b'asdfasdf', b''.join(axon.bytes(asdfhash, timeout=3)))

                stat = axon.stat(timeout=3)
                self.eq(1, stat.get('files'))
                self.eq(8, stat.get('bytes'))

                # Save it again - we should have no change in metrics/storage
                self.eq(0, axon.save([b'asdfasdf'], timeout=3))
                metrics = list(blob.metrics(timeout=3))
                self.len(1, metrics)
                self.eq(8, metrics[0][1].get('size'))
                self.eq(1, metrics[0][1].get('blocks'))
                stat = axon.stat(timeout=3)
                self.eq(1, stat.get('files'))
                self.eq(8, stat.get('bytes'))

                # FIXME - What is the behavior we want here?
                # Currently, we duplicate the uploaded bytes with a new buid.
                # self.eq(asdfhash, axon.upload([b'asdf', b'asdf'], timeout=3))
                # metrics = list(blob.metrics(timeout=3))
                # self.len(1, metrics)
                # self.eq(8, metrics[0][1].get('size'))
                # self.eq(1, metrics[0][1].get('blocks'))
                # stat = axon.stat(timeout=3)
                # self.eq(1, stat.get('files'))
                # self.eq(8, stat.get('bytes'))

                # lets see if the bytes made it to the blob clone...
                self.nn(blob01wait.wait(timeout=10))

                newp = os.urandom(32)
                def loop():
                    s_common.spin(axon.bytes(newp))

                self.raises(s_exc.RetnErr, loop)

                blob01wait = blob01.waiter(1, 'blob:clone:rows')
                self.eq(qwerhash, axon.upload([b'qwer', b'qwer'], timeout=3))

                self.len(0, axon.wants([qwerhash]))
                self.eq(b'qwerqwer', b''.join(axon.bytes(qwerhash, timeout=3)))
                self.nn(blob01wait.wait(3))

                retn = list(axon.metrics(0, timeout=3))
                self.eq(retn[0][1].get('size'), 8)
                self.eq(retn[0][1].get('cell'), 'blob00@localhost')

                # Try uploading a large file
                logger.debug('Large file test')
                # Monkeypatch axon to a smaller blocksize
                s_axon.blocksize = s_const.kibibyte
                self.raises(RetnErr, axon.locs, bbufhash, timeout=3)
                genr = s_common.chunks(bbuf, s_axon.blocksize)
                # It is possible that we may need multiple events captured
                # to avoid a timing issue
                blob01wait = blob01.waiter(2, 'blob:clone:rows')
                self.eq(bbufhash, axon.upload(genr, timeout=3))
                self.eq((), axon.wants([bbufhash], timeout=3))

                # Then retrieve it
                size = 0
                gots = []
                testhash = hashlib.sha256()
                for byts in axon.bytes(bbufhash, timeout=3):
                    size += len(byts)
                    gots.append(byts)
                    testhash.update(byts)
                self.eq(bbufhash, testhash.digest())

                try:
                    self.eq(size, len(bbuf))
                    self.eq(bbufhash, testhash.digest())

                except Exception as e:

                    for byts in gots:
                        print(repr(byts))

                    print('SIZE: %d/%d' % (size, len(bbuf)))
                    raise

                blob01wait.wait(3)
                self.ne(blob01wait.events, [])
                locs = axon.locs(bbufhash, timeout=3)
                self.len(1, locs)
                self.isin('blob00', locs[0][0])
                # Use the buid to retrieve the large file from blob01
                tbuid = locs[0][1]
                testhash = hashlib.sha256()
                for byts in blob01c.bytes(tbuid, timeout=3):
                    testhash.update(byts)
                self.eq(bbufhash, testhash.digest())

                # Try storing a empty file
                logger.debug('Nullfile test')
                axon.save([b''])
                self.eq((), tuple(axon.wants([nullhash])))
                # Then retrieve it
                parts = []
                for part in axon.bytes(nullhash):
                    parts.append(part)
                self.eq([b''], parts)

                logger.debug('Shutdown / restart blob01 test')
                bref.pop('blob01')
                blob01.fini()
                self.true(blob01.isfini)
                axon.save([b'hehehaha'], timeout=3)
                self.eq((), axon.wants([hehahash], timeout=3))
                # Now bring blob01 back online
                logger.debug('Bringing blob01 back online')
                blob01 = s_axon.BlobCell(path, blob01conf)
                bref.put('blob01', blob01)
                self.true(blob01.cellpool.neurwait(timeout=3))
                blob01wait = blob01.waiter(1, 'blob:clone:rows')
                # Cloning should start up shortly
                self.nn(blob01wait.wait(10))

                # Ask a blobclient for data for a random buid
                newp = buid()
                parts = []
                for part in blob.bytes(newp):
                    parts.append(part)
                self.eq(parts, [])

            # Let everything get shut down by the busref fini
            logger.debug('Bringing everything back up')
            with s_eventbus.BusRef() as bref:
                # neur00 ############################################
                conf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': nport}
                path = s_common.gendir(dirn, 'neuron')
                logger.debug('Bringing Neuron Back online')
                neur = s_neuron.Neuron(path, conf)
                bref.put('neur00', neur)
                root = neur.getCellAuth()
                # blob00 ############################################
                path = s_common.gendir(dirn, 'blob00')
                logger.debug('Bringing blob00 back online')
                conf = {'host': 'localhost', 'bind': '127.0.0.1', 'blob:mapsize': s_test.TEST_MAP_SIZE}
                blob00 = s_axon.BlobCell(path, conf)
                bref.put('blob00', blob00)
                self.true(blob00.cellpool.neurwait(timeout=3))
                user = s_cell.CellUser(root)
                blob00sess = user.open(blob00.getCellAddr(), timeout=3)
                bref.put('blob00sess', blob00sess)
                # blob01 ############################################
                path = s_common.gendir(dirn, 'blob01')
                blob01conf = dict(conf)
                blob01conf['blob:cloneof'] = 'blob00@localhost'
                logger.debug('Bringing blob01 back online')
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
                    'axon:mapsize': s_test.TEST_MAP_SIZE
                }
                logger.debug('Bringing axon00 online')
                axon00 = s_axon.AxonCell(path, axonconf)
                bref.put('axon00', axon00)
                self.true(axon00.cellpool.neurwait(timeout=3))
                #####################################################
                sess = user.open(axon00.getCellAddr(), timeout=3)
                bref.put('sess', sess)
                # wait for the axon to have blob00
                ready = False
                for i in range(30):
                    if axon00.blobs.items():
                        ready = True
                        break
                    time.sleep(0.1)
                self.true(ready)
                axon = s_axon.AxonClient(sess)

                # Try retrieving a large file
                testhash = hashlib.sha256()
                for byts in axon.bytes(bbufhash, timeout=3):
                    testhash.update(byts)
                self.eq(bbufhash, testhash.digest())

                # Try saving a new file and a existing file to the cluster and ensure it is replicated
                self.eq((ohmyhash,), axon.wants((ohmyhash, hehahash, nullhash), 3))
                self.eq(1, axon.save([b'ohmyohmyy', b'']))
                self.nn(blob01wait.wait(10))
