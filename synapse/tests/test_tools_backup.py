import os
import synapse.lib.scope as s_scope

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

    def test_backup(self):
        async with self.getTestCore() as core:
            src_dirn = s_scope.get('dirn')
            # This technically mangles the value in scope but that value
            # is not used for doing directory removal.
            with self.getTestDir() as dirn2:
                argv = [src_dirn, dirn2]
                args = s_backup.parse_args(argv)
                ret = s_backup.main(args)
                self.eq(ret, 0)
                cmpr_path = os.path.join(args.outpath,
                                         os.path.basename(src_dirn))
                fpset = self.compare_dirs(src_dirn,
                                         cmpr_path,
                                         skipfns=['lock.mdb'])
                # We expect the data.mdb file to be in the fpset
                self.isin('/layers/000-default/layer.lmdb/data.mdb', fpset)
