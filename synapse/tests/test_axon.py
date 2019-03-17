import hashlib
import logging

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4793491

bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(b'asdfasdf').digest()
emptyhash = hashlib.sha256(b'').digest()

asdfretn = (8, asdfhash)
emptyretn = (0, emptyhash)

class AxonTest(s_t_utils.SynTest):

    async def runAxonTestBase(self, axon):

        tick = s_common.now()

        self.false(await axon.has(asdfhash))

        async with await axon.upload() as fd:
            await fd.write(b'asdfasdf')
            self.eq(asdfretn, await fd.save())

        # do it again to test the short circuit
        async with await axon.upload() as fd:
            await fd.write(b'asdfasdf')
            self.eq(asdfretn, await fd.save())

        bytz = []
        async for byts in axon.get(asdfhash):
            bytz.append(byts)

        self.eq(b'asdfasdf', b''.join(bytz))

        self.true(await axon.has(asdfhash))
        self.false(await axon.has(bbufhash))

        self.eq((bbufhash,), await axon.wants((bbufhash, asdfhash)))

        async with await axon.upload() as fd:
            await fd.write(bbuf)
            await fd.save()

        self.true(await axon.has(asdfhash))
        self.true(await axon.has(bbufhash))

        self.eq((), await axon.wants((bbufhash, asdfhash)))

        items = [x async for x in axon.hashes(0)]
        self.eq(((0, (asdfhash, 8)), (1, (bbufhash, 33554437))), items)

        items = [x[1] async for x in axon.history(tick)]
        self.eq(((asdfhash, 8), (bbufhash, 33554437)), items)

        items = [x[1] async for x in axon.history(0, tock=1)]
        self.eq((), items)

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(2, info.get('file:count'))

        async with await axon.upload() as fd:
            await fd.write(b'')
            self.eq(emptyretn, await fd.save())

        bytz = []
        async for byts in axon.get(emptyhash):
            bytz.append(byts)

        self.eq(b'', b''.join(bytz))

    async def test_axon_base(self):
        async with self.getTestAxon() as axon:
            await self.runAxonTestBase(axon)

    async def test_axon_proxy(self):
        async with self.getTestAxon() as axon:
            async with axon.getLocalProxy() as prox:
                await self.runAxonTestBase(prox)
