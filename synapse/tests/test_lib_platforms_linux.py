import mmap
import pathlib
import synapse.tests.utils as s_t_utils
import synapse.lib.thisplat as s_thisplat

class LinuxTest(s_t_utils.SynTest):
    def test_getMappedAddress(self):
        self.thisHostMust(platform='linux')
        with self.getTestDir() as dirn:
            fsize = 32 * 1024
            fn = pathlib.Path(dirn) / 'mapfile'
            with open(fn, 'wb') as f:
                f.write(b'x' * fsize)
                f.flush()
            with open(fn, 'r+b') as f:
                with mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ):
                    addr, size = s_thisplat.getMappedAddress(fn)
                    self.ne(addr, 0)
                    self.eq(size, fsize)
