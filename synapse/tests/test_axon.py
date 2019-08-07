import hashlib
import logging

import synapse.axon as s_axon
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4793491
abuf = b'asdfasdf'
pbuf = b'pennywise'

bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(abuf).digest()
emptyhash = hashlib.sha256(b'').digest()
pennhash = hashlib.sha256(pbuf).digest()

asdfretn = (8, asdfhash)
emptyretn = (0, emptyhash)
pennretn = (9, pennhash)

class AxonTest(s_t_utils.SynTest):

    async def runAxonTestBase(self, axon):

        tick = s_common.now()

        logger.info('asdfhash test')

        self.false(await axon.has(asdfhash))

        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        # do it again to test the short circuit
        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        bytz = []
        async for byts in axon.get(asdfhash):
            bytz.append(byts)

        self.eq(b'asdfasdf', b''.join(bytz))

        self.true(await axon.has(asdfhash))

        logger.info('bbufhash test')

        self.false(await axon.has(bbufhash))

        self.eq((bbufhash,), await axon.wants((bbufhash, asdfhash)))

        async with await axon.upload() as fd:
            await fd.write(bbuf)
            await fd.save()

        self.true(await axon.has(asdfhash))
        self.true(await axon.has(bbufhash))

        self.eq((), await axon.wants((bbufhash, asdfhash)))

        logger.info('History and metrics')

        items = [x async for x in axon.hashes(0)]
        self.eq(((0, (asdfhash, 8)), (1, (bbufhash, 33554437))), items)

        items = [x[1] async for x in axon.history(tick)]
        self.eq(((asdfhash, 8), (bbufhash, 33554437)), items)

        items = [x[1] async for x in axon.history(0, tock=1)]
        self.eq((), items)

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(2, info.get('file:count'))

        logger.info('Empty file test')

        async with await axon.upload() as fd:
            await fd.write(b'')
            self.eq(emptyretn, await fd.save())

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(3, info.get('file:count'))

        bytz = []
        async for byts in axon.get(emptyhash):
            bytz.append(byts)

        self.eq(b'', b''.join(bytz))

        logger.info('Upload context reuse')
        async with await axon.upload() as fd:
            # We can reuse the FD _after_ we have called save() on it.
            await fd.write(abuf)
            retn = await fd.save()
            self.eq(retn, asdfretn)
            # Now write a new file
            await fd.write(pbuf)
            retn = await fd.save()
            self.eq(retn, pennretn)
            logger.info('Reuse test with large file causing a rollover')
            # Write a large file that will cause a rollover
            very_bigbuf = (s_axon.MAX_SPOOL_SIZE + 2) * b'V'
            vbhash = hashlib.sha256(very_bigbuf).digest()
            for chunk in s_common.chunks(very_bigbuf, s_axon.CHUNK_SIZE):
                await fd.write(chunk)
            retn = await fd.save()
            self.eq(retn, (len(very_bigbuf), vbhash))

        info = await axon.metrics()
        self.eq(570425393, info.get('size:bytes'))
        self.eq(5, info.get('file:count'))

        # When testing a local axon, we want to ensure that the FD was in fact fini'd
        if isinstance(fd, s_axon.UpLoad):
            self.true(fd.fd.closed)

    async def test_axon_base(self):
        async with self.getTestAxon() as axon:
            self.isin('axon', axon.dmon.shared)
            await self.runAxonTestBase(axon)

    async def test_axon_proxy(self):
        async with self.getTestAxon() as axon:
            async with axon.getLocalProxy() as prox:
                await self.runAxonTestBase(prox)
