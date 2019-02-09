import os

import synapse.tests.utils as s_t_utils

import synapse.tools.backup as s_backup

class BackupTest(s_t_utils.SynTest):

    def dirset(self, sdir, skipfns):
        ret = set()
        for fdir, _, fns in os.walk(sdir):

            for fn in fns:

                if fn in skipfns:
                    continue

                fp = os.path.join(fdir, fn)
                if not os.path.isfile(fp) and not os.path.isdir(fp):
                    continue

                fp = fp[len(sdir):]
                ret.add(fp)

        return ret

    def compare_dirs(self, dir1, dir2, skipfns=None):
        if not skipfns:
            skipfns = []
        set1 = self.dirset(dir1, skipfns)
        set2 = self.dirset(dir2, skipfns)
        self.gt(len(set1), 1)
        self.gt(len(set2), 1)
        self.eq(set1, set2)
        return set1

    async def test_backup(self):

        async with self.getTestCore() as core:

            await core.fini()  # Avoid having the same DB open twice

            with self.getTestDir() as dirn2:

                argv = (core.dirn, dirn2)

                self.eq(0, s_backup.main(argv))

                fpset = self.compare_dirs(core.dirn, dirn2, skipfns=['lock.mdb'])

                # We expect the data.mdb file to be in the fpset
                self.isin(f'/layers/{core.iden}/layer.lmdb/data.mdb', fpset)
