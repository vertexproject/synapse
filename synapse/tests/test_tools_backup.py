import os

import synapse.common as s_common
import synapse.lib.spooled as s_spooled

import synapse.tests.utils as s_t_utils

import synapse.tools.backup as s_backup

class BackupTest(s_t_utils.SynTest):

    def dirset(self, sdir, skipfns, skipdirs):
        ret = set()
        for fdir, dns, fns in os.walk(sdir):

            for dn in list(dns):
                if dn in skipdirs:
                    dns.remove(dn)

            for fn in fns:

                if fn in skipfns:
                    continue

                fp = os.path.join(fdir, fn)
                if not os.path.isfile(fp) and not os.path.isdir(fp):
                    continue

                fp = fp[len(sdir):]
                ret.add(fp)

        return ret

    def compare_dirs(self, dir1, dir2, skipfns=None, skipdirs=None):
        if skipfns is None:
            skipfns = set()

        if skipdirs is None:
            skipdirs = set()

        set1 = self.dirset(dir1, skipfns, skipdirs)
        set2 = self.dirset(dir2, skipfns, set())
        self.gt(len(set1), 1)
        self.gt(len(set2), 1)
        self.eq(set1, set2)
        return set1

    async def test_backup(self):

        async with self.getTestCore() as core:
            layriden = core.getLayer().iden

            # For additional complication, open a spooled set that shouldn't be backed up
            async with await s_spooled.Set.anit(dirn=core.dirn, size=2) as sset:
                await sset.add(10)
                await sset.add(20)
                await sset.add(30)

                await core.fini()  # Avoid having the same DB open twice

                with self.getTestDir() as dirn2:

                    argv = (core.dirn, dirn2)

                    self.eq(0, s_backup.main(argv))

                    fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs={'tmp'})
                    self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))

                    # We expect the data.mdb file to be in the fpset
                    self.isin(f'/layers/{layriden}/layer_v2.lmdb/data.mdb', fpset)
