import pathlib

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
import synapse.lib.thisplat as s_thisplat

class LinuxTest(s_t_utils.SynTest):
    def test_mlocking(self):
        self.thisHostMust(hasmemlocking=True)
        with self.getTestDir() as dirn:
            fsize = 8 * 1024
            fn = pathlib.Path(dirn) / 'mapfile'
            with open(fn, 'wb') as f:
                f.write(b'x' * fsize)
                f.flush()
            with open(fn, 'r+b') as f:
                with s_thisplat.mmap(0, fsize, 0x1, 0x8001, f.fileno(), 0):
                    addr, size = s_thisplat.getFileMappedRegion(fn)
                    self.ne(addr, 0)
                    self.eq(size, fsize)
                    beforelock = s_thisplat.getCurrentLockedMemory()
                    maxlocked = s_thisplat.getMaxLockedMemory()
                    self.ge(maxlocked, beforelock)
                    self.ge(s_thisplat.getTotalMemory(), beforelock)
                    self.ge(s_thisplat.getAvailableMemory(), beforelock)
                    s_thisplat.mlock(addr, size)
                    locktotal = s_thisplat.getCurrentLockedMemory()
                    self.ge(locktotal, size)
                    self.ge(locktotal, beforelock)
                    maxlocked = s_thisplat.getMaxLockedMemory()
                    self.ge(maxlocked, locktotal)
                    s_thisplat.munlock(addr, size)
                    locktotal = s_thisplat.getCurrentLockedMemory()
                    self.eq(locktotal, beforelock)

                    # Make sure we get the largest mapped region
                    with s_thisplat.mmap(0, int(fsize / 2), 0x1, 0x8001, f.fileno(), 0):
                        addr, size = s_thisplat.getFileMappedRegion(fn)
                        self.eq(size, fsize)

            # Sad tests
            bfn = pathlib.Path(dirn) / 'mapfile.newp'
            self.raises(s_exc.NoSuchFile, s_thisplat.getFileMappedRegion, bfn)

        # Sad tests
        with self.raises(OSError) as cm:
            s_thisplat.mlock(0x01, 16)
        # Cannot allocate memory to lock
        self.eq(cm.exception.errno, 12)

        with self.raises(OSError) as cm:
            s_thisplat.munlock(0xFF, 16)
        # Cannot allocate memory to unlock
        self.eq(cm.exception.errno, 12)
