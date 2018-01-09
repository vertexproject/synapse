import struct

import synapse.lib.heap as s_heap

from synapse.tests.common import *

class HeapTest(SynTest):

    def test_heap_base(self):

        # FIXME test these on windows...
        #self.thisHostMust(platform='linux')

        fd = tempfile.TemporaryFile()
        heap = s_heap.Heap(fd)

        self.eq(heap.atomSize(), heap.pagesize)
        self.eq(heap.heapSize(), 64)

        off0 = heap.alloc(8)
        off1 = heap.alloc(8)

        # do interlaced writes
        heap.writeoff(off0, b'asdf')
        heap.writeoff(off1, b'hehe')

        heap.writeoff(off0 + 4, b'qwer')
        heap.writeoff(off1 + 4, b'haha')

        self.eq(heap.readoff(off0, 8), b'asdfqwer')
        self.eq(heap.readoff(off1, 8), b'hehehaha')

        self.eq(heap.atomSize(), heap.pagesize)
        self.eq(heap.heapSize(), 160)

        heap.fini()

    def test_heap_resize(self):

        fd = tempfile.TemporaryFile()

        with s_heap.Heap(fd) as heap:  # type: s_heap.Heap

            blocks = []
            w = heap.waiter(1, 'heap:resize')
            while heap.atomSize() == heap.pagesize:
                # NOTE test assumes pages are at least 1k
                blocks.append(heap.alloc(1024))

            self.eq(w.count, 1)
            w.fini()

            self.eq(heap.atomSize(), heap.pagesize * 2)

            # Ensure that resize events are dropped if they would resize downwards
            mesg0 = ('heap:resize', {'size': 137})
            mesg = ('heap:sync', {'mesg': mesg0})
            with self.getLoggerStream('synapse.lib.heap') as stream:
                heap.sync(mesg)
            # Ensure our bad sync event was logged
            stream.seek(0)
            mesgs = stream.read()
            self.isin('Attempted to resize the heap downwards', mesgs)
            # Ensure the heapsize was unchanged
            self.eq(heap.atomSize(), heap.pagesize * 2)

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

    def test_heap_allocation_death(self):
        self.skipTest('Known bad behavior')
        fd = tempfile.TemporaryFile()

        with s_heap.Heap(fd) as heap:
            sz = heap.pagesize - s_heap.headsize - heap.used
            off = heap.alloc(sz)
            heap.writeoff(off, sz * b'!')

    def test_heap_integrity(self):
        with self.getTestDir() as fdir:
            fp = os.path.join(fdir, 'test.heap')
            fd = open(fp, 'w+b')
            # Setup a good heapfile
            with s_heap.Heap(fd) as heap:
                rand = os.urandom(2048)
                off = heap.alloc(2048)
                heap.writeoff(off, rand)

                blocks = [b for b in heap.readiter(off, 2048, itersize=9)]
                byts = b''.join(blocks)

                self.eq(rand, byts)

            # Backup our heapfile for reuse
            shutil.copy(fp, fp + '.bak')

            # Truncate the file so that the atomfile size vs used check fails
            with open(fp, 'r+b') as fd:
                fd.seek(1024)
                fd.truncate()
                fd.seek(0)

                self.raises(BadHeapFile, s_heap.Heap, fd)

            # Restore the heapfile
            shutil.copy(fp + '.bak', fp)
            with open(fp, 'r+b') as fd:
                # Pack a bad head value which will have a invalid magic number
                byts = struct.pack(s_heap.headfmt, b'0123' * 8, 32, 1)
                fd.seek(0)
                # Overwrite the header at 0
                fd.write(byts)
                # ensure the s_heap fails to validate the magic number for heap header at 0x0
                self.raises(BadHeapFile, s_heap.Heap, fd)

            # Restore the heapfile
            shutil.copy(fp + '.bak', fp)
            with open(fp, 'r+b') as fd:
                # Pack a bad head value which will have a invalid size
                byts = s_heap.packHeapHead(1024)
                fd.seek(0)
                # Overwrite the header at 0
                fd.write(byts)
                # ensure the s_heap fails to validate the size for heap header at 0x0
                self.raises(BadHeapFile, s_heap.Heap, fd)
