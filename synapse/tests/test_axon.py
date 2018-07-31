import os
import time
import hashlib
import asyncio
import logging

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.threads as s_threads

import synapse.tests.common as s_test

from synapse.tests.utils import SyncToAsyncCMgr

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4793491

bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(b'asdfasdf').digest()

async def alist(coro):
    return [x async for x in coro]

class AxonTest(s_test.SynTest):

    async def _wait_for_axon_files(self, axon, nfiles):
        for i in range(20):
            stats = await axon.stat()
            if stats.get('files', 0) >= nfiles:
                break
            await asyncio.sleep(0.2, loop=s_glob.plex.loop)
        self.eq(nfiles, (await axon.stat()).get('files'))

    @s_glob.synchelp
    async def test_blobstor(self):
        with self.getTestDir() as dirn:
            path0 = os.path.join(dirn, 'blob0')
            async with SyncToAsyncCMgr(s_axon.BlobStor, path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

                data1 = b'asdfqwerhehehaha'

                hash1 = hashlib.sha256(data1).digest()
                blobs = (
                    (hash1, 0, data1[0:4]),
                    (None, 1, data1[4:8]),
                    (None, 2, data1[8:12]),
                    (None, 3, data1[12:16]),
                )
                self.eq(1, await bst0.bulkput(blobs))

                retn = b''.join([x async for x in bst0.get(hash1)])
                self.eq(retn, data1)

                # We can store and retrieve an empty string
                data = b''
                hash2 = hashlib.sha256(data).digest()
                blobs = (
                    (hash2, 0, data),
                )
                self.eq(1, await bst0.bulkput(blobs))

                bl = []
                async for byts in bst0.get(hash2):
                    bl.append(byts.tobytes())
                self.eq(bl, [b''])
                retn = b''.join(bl)
                self.eq(retn, b'')

                path1 = os.path.join(dirn, 'blob1')
                blobstorconf = {'mapsize': s_test.TEST_MAP_SIZE}
                async with SyncToAsyncCMgr(s_axon.BlobStor, path1, conf=blobstorconf) as bst1:

                    clone_data = [x async for x in bst0.clone(0)]
                    await bst1._consume_clone_data(clone_data)

                    retn = b''.join([x async for x in bst1.get(hash1)])
                    self.eq(retn, data1)
                    retn = b''.join([x async for x in bst1.get(hash2)])
                    self.eq(retn, b'')

                    await bst1._consume_clone_data([])

                # Test the convenience functions
                xxxxhash = hashlib.sha256(b'xxxx').digest()
                yyyyhash = hashlib.sha256(b'yyyy').digest()
                self.eq((1, xxxxhash), await bst0.putone(b'xxxx'))
                self.eq((2, yyyyhash), await bst0.putmany((b'xxxy', b'yyyy')))

    @s_glob.synchelp
    async def test_blobstor_stat(self):
        with self.getTestDir() as dirn:
            path0 = os.path.join(dirn, 'blob0')
            async with SyncToAsyncCMgr(s_axon.BlobStor, path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

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
            async with SyncToAsyncCMgr(s_axon.BlobStor, path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as bst0:

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

    @s_glob.synchelp
    async def test_blobstor_remote(self):
        with self.getTestDir():
            async with SyncToAsyncCMgr(self.getTestDmon, mirror='axondmon') as dmon, \
                    await dmon._getTestProxy('blobstor00') as bst0:
                stats = await bst0.stat()
                self.eq(stats, {})
                upld = await bst0.startput()
                await upld.write(b'abcd')
                await upld.finish()

    @s_glob.synchelp
    async def test_axon(self):
        with self.getTestDir() as dirn:
            path0 = os.path.join(dirn, 'axon0')
            async with SyncToAsyncCMgr(self.getTestDmon, mirror='axondmon') as dmon, \
                    await dmon._getTestProxy('blobstor00') as blobstor0, \
                    SyncToAsyncCMgr(s_axon.Axon, path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as axon:

                self.eq((), [x async for x in axon.metrics()])
                self.eq((), [x async for x in await blobstor0.metrics()])

                self.len(1, await axon.wants([asdfhash]))

                # Asking for bytes prior to the bytes being present raises
                await self.asyncraises(s_exc.NoSuchFile, alist(axon.get(asdfhash)))

                # Try to put before we have any blobstors
                await self.asyncraises(s_exc.AxonNoBlobStors, axon.bulkput([b'asdfasdf']))

                blobstorurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor00'
                await axon.addBlobStor(blobstorurl)

                # self.eq((), [x async for x in axon.metrics()])
                self.eq((), [x async for x in await blobstor0.metrics()])

                self.eq(1, await axon.bulkput([b'asdfasdf']))

                metrics = [x async for x in axon.metrics()]

                self.len(1, metrics)

                self.eq((), await axon.wants([asdfhash]))

                self.eq(b'asdfasdf', b''.join([x async for x in axon.get(asdfhash)]))

                stat = await axon.stat()
                self.eq(1, stat.get('files'))

                # Save it again - we should have no change in metrics/storage
                self.eq(0, await axon.bulkput([b'asdfasdf']))
                metrics = [x async for x in axon.metrics()]
                self.len(1, metrics)
                stat = await axon.stat()
                self.eq(1, stat.get('files'))

                # Empty file test
                self.eq(1, await axon.bulkput([b'']))

    @s_glob.synchelp
    async def test_axon_remote(self):
        with self.getTestDir():
            async with SyncToAsyncCMgr(self.getTestDmon, mirror='axondmon') as dmon, \
                    await dmon._getTestProxy('axon00') as axon:
                blobstorurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor00'
                await axon.addBlobStor(blobstorurl)

                async with await axon.startput() as uploader:
                    await uploader.write(b'a')
                    count, hashval = await uploader.finish()

                await self._wait_for_axon_files(axon, 1)

                await axon.unwatchBlobStor(blobstorurl)

                # Check that invalid paths don't kill things
                blobstorurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/notablobstor'
                await self.asyncraises(s_exc.NoSuchName, axon.addBlobStor(blobstorurl))
                blobstorurl = f'tcp://{dmon.addr[0]}:32323/notablobstor'
                await self.asyncraises(s_exc.SynErr, axon.addBlobStor(blobstorurl))
                bslist = await axon.getBlobStors()
                self.notin(blobstorurl, bslist)

    @s_glob.synchelp
    async def test_axon_uploader(self):
        with self.getTestDir() as dirn:
            async with SyncToAsyncCMgr(self.getTestDmon, mirror='axondmon') as dmon, \
                    await dmon._getTestProxy('axon00') as axon:
                abhash = hashlib.sha256(b'ab').digest()
                cdhash = hashlib.sha256(b'cd').digest()

                blobstorurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor00'
                await axon.addBlobStor(blobstorurl)

                # Test uploader interface
                async with await axon.startput() as uploader:
                    await uploader.write(b'a')
                    await uploader.write(b'b')
                    await uploader.finishFile()
                    await uploader.write(b'cd')
                    count, hashval = await uploader.finish()
                    self.eq(2, count)
                    self.eq(cdhash, hashval)

                # Give the clone subscription a chance to catch up
                self.eq([], await axon.wants([abhash, cdhash]))
                foo = await axon.get(cdhash)
                bar = [x async for x in foo]
                self.eq(b'cd', b''.join([x async for x in await axon.get(cdhash)]))
                self.eq(b'ab', b''.join([x async for x in await axon.get(abhash)]))

                # Test deconfliction, Upload a big boy
                async with await axon.startput() as uploader:
                    await uploader.write(b'cd')
                    await uploader.finishFile()
                    await uploader.write(b'c')
                    await uploader.write(b'd')
                    await uploader.finishFile()
                    for chunk in s_common.chunks(bbuf, s_axon.CHUNK_SIZE + 13):
                        await uploader.write(chunk)
                    count, hashval = await uploader.finish()
                    self.eq(1, count)
                    self.eq(bbufhash, hashval)

                await self._wait_for_axon_files(axon, 3)
                self.eq((), await axon.wants([bbufhash]))
                self.eq(bbuf, b''.join([x async for x in await axon.get(bbufhash)]))

    @s_glob.synchelp
    async def test_axon_cloning(self):
        ''' Bring up an axon and a blobstor, then bring up a second blobstor that's cloning the first '''
        with self.getTestDir() as dirn:
            path0 = os.path.join(dirn, 'axon0')
            async with SyncToAsyncCMgr(self.getTestDmon, mirror='axondmon') as dmon, \
                    await dmon._getTestProxy('blobstor00') as blobstor0, \
                    SyncToAsyncCMgr(s_axon.Axon, path0, conf={'mapsize': s_test.TEST_MAP_SIZE}) as axon:

                blobstorurl0 = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor00'
                blobstorurl1 = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor01'
                await axon.addBlobStor(blobstorurl0)
                self.eq(1, await axon.bulkput([b'asdfasdf']))
                self.eq(1, await axon.bulkput([b'foo']))
                blobstor1conf = {'mapsize': s_test.TEST_MAP_SIZE, 'cloneof': blobstorurl0}

                # Make a second blobstor that clones the first
                async with SyncToAsyncCMgr(s_axon.BlobStor, path0, conf=blobstor1conf) as blobstor1:
                    # Make sure the cloning works
                    for i in range(10):
                        if blobstor1.getCloneProgress() >= 2:
                            break
                        await asyncio.sleep(0.2, loop=s_glob.plex.loop)
                    self.eq(2, blobstor1.getCloneProgress())

                    # Add the second blobstor to the axon
                    dmon.share('blobstor01', blobstor1)
                    await axon.addBlobStor(blobstorurl1)

                    bss = await axon.getBlobStors()
                    self.sorteq((blobstorurl0, blobstorurl1), bss)

                    # Make sure the axon gets the updates from the second blobstor
                    await self._wait_for_axon_files(axon, 4)

                    self.eq(b'asdfasdf', b''.join([x async for x in axon.get(asdfhash)]))

                    boohash = hashlib.sha256(b'boo').digest()
                    self.eq((1, boohash), await blobstor0.putone(b'boo'))
                    await self._wait_for_axon_files(axon, 6)

                    # Make sure a regular write to the axon still works
                    self.eq(1, await axon.bulkput([b'bar']))

                    # Now turn off the second blobstor and see what happens
                    await s_glob.plex.executor(blobstor1.fini)

                    # Not sure this is entirely fair
                    # self.eq(1, await axon.bulkput([b'bar']))

    @s_glob.synchelp
    async def test_axon_blobstors_dropping(self):
        # FIXME
        pass

class _AsyncQueueTest(s_test.SynTest):
    @s_glob.synchelp
    async def test_asyncqueue(self):

        # The axon tests test most of the asyncqueue functionality.  We just need to test the
        # draining part

        q = s_axon._AsyncQueue(5, drain_level=3)
        [await q.put(i) for i in range(5)]
        got_to_end = False
        last_msg = 0

        def sync_worker():
            nonlocal got_to_end
            nonlocal last_msg
            time.sleep(0.1)

            last_msg = q.get()
            last_msg = q.get()
            time.sleep(0.1)
            last_msg = q.get()

            got_to_end = True
        t = s_threads.worker(sync_worker)
        before = time.time()
        await q.put(6)
        self.lt(0.1, time.time() - before)
        self.eq(last_msg, 2)
        await asyncio.sleep(0.1)

        self.true(got_to_end)

        t.join()
