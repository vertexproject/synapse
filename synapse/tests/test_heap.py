import os
import tempfile

import synapse.axon as s_axon
import synapse.compat as s_compat
import synapse.lib.heap as s_heap

from synapse.tests.common import *

class HeapTest(SynTest):

    def test_heap_base(self):

        # FIXME test these on windows...
        #self.thisHostMust(platform='linux')

        fd = tempfile.TemporaryFile()
        heap = s_heap.Heap(fd)

        self.eq(heap.size(), heap.pagesize)

        off0 = heap.alloc(8)
        off1 = heap.alloc(8)

        # do interlaced writes
        heap.writeoff(off0, b'asdf')
        heap.writeoff(off1, b'hehe')

        heap.writeoff(off0 + 4, b'qwer')
        heap.writeoff(off1 + 4, b'haha')

        self.eq(heap.readoff(off0, 8), b'asdfqwer')
        self.eq(heap.readoff(off1, 8), b'hehehaha')

        heap.fini()

    def test_heap_resize(self):

        fd = tempfile.TemporaryFile()

        with s_heap.Heap(fd) as heap:

            pagesize = heap.pagesize
            self.eq(heap.size(), heap.pagesize)

            blocks = []
            while heap.size() == heap.pagesize:
                # NOTE test assumes pages are at least 1k
                blocks.append(heap.alloc(1024))

            self.eq(heap.size(), heap.pagesize * 2)

    def test_heap_save(self):

        #self.thisHostMust(platform='linux')

        msgs = []

        fd0 = tempfile.TemporaryFile()
        heap0 = s_heap.Heap(fd0)

        heap0.on('heap:sync', msgs.append)

        off0 = heap0.alloc(8)
        off1 = heap0.alloc(8)

        # do interlaced writes
        heap0.writeoff(off0, b'asdf')
        heap0.writeoff(off1, b'hehe')

        heap0.writeoff(off0 + 4, b'qwer')
        heap0.writeoff(off1 + 4, b'haha')

        fd1 = tempfile.TemporaryFile()
        heap1 = s_heap.Heap(fd1)

        heap1.syncs(msgs)

        self.eq(heap0.readoff(off0, 8), heap1.readoff(off0, 8))
        self.eq(heap0.readoff(off1, 8), heap1.readoff(off1, 8))

        heap0.fini()
        heap1.fini()

    def test_heap_readiter(self):
        #self.thisHostMust(platform='linux')

        fd = tempfile.TemporaryFile()

        with s_heap.Heap(fd) as heap:

            rand = os.urandom(2048)
            off = heap.alloc(2048)
            heap.writeoff(off, rand)

            blocks = [b for b in heap.readiter(off, 2048, itersize=9)]
            byts = b''.join(blocks)

            self.eq(rand, byts)
