import os
import time
import struct
import hashlib
import asyncio
import logging
import contextlib

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack

import synapse.tests.common as s_test

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

    @s_glob.synchelp
    async def test_blobstor(self):
        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                data1 = b'asdfqwerhehehaha'

                hash1 = hashlib.sha256(data1).digest()
                blobs = (
                    (hash1, 0, data1[0:4]),
                    (None, 1, data1[4:8]),
                    (None, 2, data1[8:12]),
                    (None, 3, data1[12:16]),
                )
                print('Got here 0')
                await bst0.bulkput(blobs)
                print('Got here 1')

                retn = b''.join([x async for x in bst0.get(hash1)])
                self.eq(retn, data1)

                # We can store and retrieve an empty string
                data = b''
                hash2 = hashlib.sha256(data).digest()
                blobs = (
                    (hash2, 0, data),
                )
                await bst0.bulkput(blobs)

                bl = []
                async for byts in bst0.get(hash2):
                    bl.append(byts.tobytes())
                self.eq(bl, [b''])
                retn = b''.join(bl)
                self.eq(retn, b'')

                path1 = os.path.join(dirn, 'blob1')

                with s_axon.BlobStor(path1, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst1:

                    clone_data = [x async for x in bst0.clone(0)]
                    await bst1._consume_clone_data(clone_data)

                    retn = b''.join([x async for x in bst1.get(hash1)])
                    self.eq(retn, data1)
                    retn = b''.join([x async for x in bst1.get(hash2)])
                    self.eq(retn, b'')

                    await bst1._consume_clone_data([])

    @s_glob.synchelp
    async def test_blobstor_stat(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                blobs = (
                    (None, 0, os.urandom(1000)),
                    (None, 1, b'qwer'),
                    (None, 2, b'hehe'),
                    (None, 3, b'haha'),
                )  # 4 blocks, size 1000 + 4 + 4 + 4 = 1012 bytes

                stats = await bst0.stat()
                self.eq(stats, {})

                await bst0.bulkput(blobs[0:1])
                stats = await bst0.stat()
                self.eq(stats, {'bytes': 1000, 'blobs': 1})

                await bst0.bulkput(blobs)
                stats = await bst0.stat()
                self.eq(stats, {'bytes': 2012, 'blobs': 2})

    @s_glob.synchelp
    async def test_blobstor_metrics(self):

        with self.getTestDir() as dirn:

            path0 = os.path.join(dirn, 'blob0')
            with s_axon.BlobStor(path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                blobs = (
                    (None, 0, os.urandom(1000)),
                    (None, 1, b'qwer'),
                    (None, 2, b'hehe'),
                    (None, 3, b'haha'),
                )
                metrics = sorted([x async for x in bst0.metrics()])
                self.eq(metrics, [])

                await bst0.bulkput(blobs[0:1])

                metrics = [x async for x in bst0.metrics()]
                [m[1].pop('time') for m in metrics]
                tooks = [m[1].pop('took') for m in metrics]  # remove took since it may vary
                self.eq(metrics[0][1], {'size': 1000})
                self.len(1, tooks)
                # These are time based and cannot be promised to be a particular value
                for took in tooks:
                    self.lt(took, 10000)

                await bst0.bulkput(blobs[0:2])
                metrics = []
                async for item in bst0.metrics():
                    item[1].pop('time')
                    metrics.append(item[1])
                tooks = [m.pop('took') for m in metrics]  # remove took since it may vary
                self.eq(metrics, [{'size': 1000}, {'size': 1004}])
                self.len(2, tooks)
                # These are time based and cannot be promised to be a particular value
                for took in tooks:
                    self.lt(took, 10000)

    def test_axon(self):

        with contextlib.ExitStack() as ctxs:

            dmon = ctxs.enter_context(self.getTestDmon(mirror='axondmon00'))
            axon = ctxs.enter_context(dmon._getTestProxy('axon00'))
            blobstor0 = ctxs.enter_context(dmon._getTestProxy('blobstor00'))

            retn = blobstor0.stat()
            self.eq({}, blobstor0.stat())  # Nothing there yet

            self.eq((), list(axon.metrics()))
            self.eq((), list(blobstor0.metrics()))

            self.len(1, axon.wants([asdfhash]))

            # Asking for bytes prior to the bytes being present raises
            self.genraises(s_exc.NoSuchFile, axon.get, asdfhash)

            # FIXME: tmp
            return

            self.eq(1, axon.put([b'asdfasdf'], timeout=3))

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

            # Try retrieving a large file
            testhash = hashlib.sha256()
            for byts in axon.bytes(bbufhash, timeout=3):
                testhash.update(byts)
            self.eq(bbufhash, testhash.digest())

            # Try saving a new file and a existing file to the cluster and ensure it is replicated
            self.eq((ohmyhash,), axon.wants((ohmyhash, hehahash, nullhash), 3))
            self.eq(1, axon.save([b'ohmyohmyy', b'']))
            self.nn(blob01wait.wait(10))
