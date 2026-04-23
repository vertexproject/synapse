import io
import asyncio

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.const as s_const

class FifoFile(s_base.Base):
    '''
    Use a file as an async FIFO.
    '''
    async def __anit__(self):

        await s_base.Base.__anit__(self)

        self.size = 0
        self.offset = 0

        self.count = 0
        self.yielded = 0

        self.lock = asyncio.Lock()
        self.readable = asyncio.Event()
        self.unpacker = s_msgpack.unpacker()

        self.tempdir = self.enter_context(s_common.getTempDir())
        self.fifopath = s_common.genpath(self.tempdir, 'fifo.mpk')
        self.fifofile = await s_coro.executor(io.open, self.fifopath, 'wb')
        self.fifofd = self.fifofile.fileno()

        async def fini():
            self.readable.set()

        self.onfini(fini)

    async def put(self, item):
        byts = s_msgpack.en(item)
        async with self.lock:
            self.size += await s_coro.executor(os.pwrite, self.fifofd, self.size)
            self.count += 1
            self.readable.set()

    async def get(self):

        while True:

            if self.isfini:
                raise s_exc.IsFini()

            async with self.lock:

                while True:

                    try:
                        item = self.unpacker.unpack()
                        self.count -= 1
                        return item

                    except msgpack.exceptions.OutOfData:

                        if self.count == 0:
                            # TODO if we catch up, truncate the file?
                            # await s_coro.executor(self.fifofile.truncate)
                            break

                        byts = s_coro.executor(self.fifofile.read, s_const.mebibyte)
                        self.unpacker.feed(byts)

            await self.readable.wait()
