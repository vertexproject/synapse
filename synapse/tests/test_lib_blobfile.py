import unittest.mock as mock

import synapse.lib.atomfile as s_atomfile
import synapse.lib.blobfile as s_blobfile

from synapse.tests.common import *

class BlobFileTest(SynTest):

    def blobfile_basic_assumptions(self, blob):
        '''
        Basic assumptions for a Blobfile

        Args:
            blob (s_blobfile.BlobFile): BlobFile under test.
        '''
        self.false(blob.isclone)
        self.eq(blob.size(), 0)

        off0 = blob.alloc(8)

        self.eq(blob.size(), 8 + s_blobfile.headsize)
        # The blob and atomfile grow in lockstep
        self.eq(blob.atom._size, blob.size())

        off1 = blob.alloc(8)

        # do interlaced writes
        blob.writeoff(off0, b'asdf')
        blob.writeoff(off1, b'hehe')

        blob.writeoff(off0 + 4, b'qwer')
        blob.writeoff(off1 + 4, b'haha')

        self.eq(blob.readoff(off0, 8), b'asdfqwer')
        self.eq(blob.readoff(off1, 8), b'hehehaha')

        # Do a third allocation and write
        off2 = blob.alloc(8)
        # Ensure our alloc did not smash old data
        self.eq(blob.readoff(off1, 8), b'hehehaha')
        byts = 4 * b':)'
        blob.writeoff(off2, byts)

        self.eq(blob.readoff(off0, 8), b'asdfqwer')
        self.eq(blob.readoff(off1, 8), b'hehehaha')
        self.eq(blob.readoff(off2, 8), byts)

        # The blob and atomfile continue too grow in lockstep
        self.eq(blob.atom._size, blob.size())
        esisze = (3 * (s_blobfile.headsize + 8))
        self.eq(blob.size(), esisze)

        # Ensure bad reads are caught
        self.raises(BadBlobFile, blob.readoff, blob.size() - 4, 8)

    def test_blob_base(self):

        # FIXME test these on windows...
        #self.thisHostMust(platform='linux')
        with self.getTestDir() as dir:
            fp = os.path.join(dir, 'test.blob')
            blob = s_blobfile.BlobFile(fp)
            self.blobfile_basic_assumptions(blob)
            blob.fini()

            # fini the blob closes the underlying fd
            self.true(blob.atom.isfini)
            self.true(blob.fd.closed)

    def test_blob_simple_atom(self):

        def getSimpleAtom(fd, memok=True):
            return s_atomfile.AtomFile(fd)

        with mock.patch('synapse.lib.atomfile.getAtomFile', getSimpleAtom) as p:
            with self.getTestDir() as dir:
                fp = os.path.join(dir, 'test.blob')
                blob = s_blobfile.BlobFile(fp)
                self.isinstance(blob.atom, s_atomfile.AtomFile)
                self.false(isinstance(blob.atom, s_atomfile.FastAtom))
                self.blobfile_basic_assumptions(blob)
                blob.fini()
                # fini the blob closes the underlying fd
                self.true(blob.atom.isfini)
                self.true(blob.fd.closed)

    def test_blob_resize(self):

        with self.getTestDir() as dir:
            fp = os.path.join(dir, 'test.blob')
            with s_blobfile.BlobFile(fp) as blob:  # type: s_blobfile.BlobFile

                blocks = []
                w = blob.waiter(5, 'blob:alloc')
                esize = (s_blobfile.headsize + 8) * 5
                while blob.size() < esize:
                    blocks.append(blob.alloc(8))

                self.eq(w.count, 5)
                w.fini()
                self.eq(blob.size(), esize)

                # Firing a single event will work properly.
                # This is for test coverage - normal use case would
                # not use syncing except in the file-duplication case

                mesg0 = ('blob:alloc', {'size': 32})
                mesg = ('blob:sync', {'mesg': mesg0})
                blob.sync(mesg)
                # Ensure the blob was not changed since isclone is false
                self.eq(blob.size(), esize)

    def test_blob_save(self):

        #self.thisHostMust(platform='linux')

        msgs = []

        with self.getTestDir() as dir:
            fp0 = os.path.join(dir, 'test0.blob')
            blob0 = s_blobfile.BlobFile(fp0)

            blob0.on('blob:sync', msgs.append)

            off0 = blob0.alloc(8)
            off1 = blob0.alloc(8)

            # do interlaced writes
            blob0.writeoff(off0, b'asdf')
            blob0.writeoff(off1, b'hehe')

            blob0.writeoff(off0 + 4, b'qwer')
            blob0.writeoff(off1 + 4, b'haha')

            fp1 = os.path.join(dir, 'test1.blob')

            blob1 = s_blobfile.BlobFile(fp1, isclone=True)
            self.true(blob1.isclone)
            blob1.syncs(msgs)

            self.eq(blob0.readoff(off0, 8), blob1.readoff(off0, 8))
            self.eq(blob0.readoff(off1, 8), blob1.readoff(off1, 8))

            self.eq(blob0.size(), blob1.size())

            # Replaying messages to blob0 doesn't do anything to is since
            # the reactor is not wired up
            blob0.syncs(msgs)
            self.eq(blob0.size(), blob1.size())

            # Calling alloc / writeoff apis to the clone fails
            self.raises(BlobFileIsClone, blob1.alloc, 1)
            self.raises(BlobFileIsClone, blob1.writeoff, 1, b'1')

            blob0.fini()
            blob1.fini()

    def test_blob_readiter(self):
        #self.thisHostMust(platform='linux')

        with self.getTestDir() as dir:
            fp = os.path.join(dir, 'test.blob')
            with s_blobfile.BlobFile(fp) as blob:

                rand = os.urandom(2048)
                off = blob.alloc(2048)
                blob.writeoff(off, rand)

                blocks = [b for b in blob.readiter(off, 2048, itersize=9)]
                byts = b''.join(blocks)

                self.eq(rand, byts)

    def test_blob_walk(self):
        edata = {}
        with self.getTestDir() as fdir:
            fp = os.path.join(fdir, 'test.blob')
            bkup_fp = fp + '.bak'

            with s_blobfile.BlobFile(fp) as blob:  # type: s_blobfile.BlobFile

                off0 = blob.alloc(8)
                off1 = blob.alloc(8)

                edata[off0] = b'asdfqwer'
                edata[off1] = b'hehehaha'

                # do interlaced writes
                blob.writeoff(off0, b'asdf')
                blob.writeoff(off1, b'hehe')

                blob.writeoff(off0 + 4, b'qwer')
                blob.writeoff(off1 + 4, b'haha')
                # self.eq(blob.readoff(off1, 8), edata[off1])
                # Do a large write
                off2 = blob.alloc(1024)
                byts = 512 * b':)'
                blob.writeoff(off2, byts)
                edata[off2] = byts

            # Backup the file
            shutil.copy(fp, bkup_fp)

            with s_blobfile.BlobFile(fp) as blob:  # type: s_blobfile.BlobFile
                dcheck = {}

                def data_check(fd, baseoff, off, size):
                    fd.seek(off)
                    byts = fd.read(size)
                    dcheck[off] = byts == edata.get(off)

                for offset, size in blob.walk():
                    dcheck[offset] = blob.readoff(offset, size) == edata.get(offset)

                self.eq({True}, set(dcheck.values()))

            # Restore backup file
            shutil.copy(bkup_fp, fp)
            fd = genfile(fp)

            # Truncate the file short
            fd.seek(-2, os.SEEK_END)
            fd.truncate()
            fd.close()

            with s_blobfile.BlobFile(fp) as blob:  # type: s_blobfile.BlobFile
                with self.assertRaises(BadBlobFile) as cm:
                    for offset, size in blob.walk():
                        pass
            self.isin('BlobFile truncated', str(cm.exception))

            # Restore backup file
            shutil.copy(bkup_fp, fp)
            fd = genfile(fp)

            # Add bytes
            fd.seek(0, os.SEEK_END)
            fd.write(b':(')
            fd.close()

            with s_blobfile.BlobFile(fp) as blob:  # type: s_blobfile.BlobFile
                with self.assertRaises(BadBlobFile) as cm:
                    for offset, size in blob.walk():
                        pass
                self.isin('failed to read/unpack header', str(cm.exception))
