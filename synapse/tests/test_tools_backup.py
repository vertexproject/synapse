import os

import synapse.common as s_common
import synapse.lib.lmdbslab as s_lmdbslab

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

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                layriden = core.getLayer().iden

                # For additional complication, open a Slab that shouldn't be backed up
                slabpath = s_common.gendir(dirn, 'tmp', 'test.lmdb')
                async with await s_lmdbslab.Slab.anit(slabpath) as slab:
                    foo = slab.initdb('foo')
                    slab.put(b'\x00\x01', b'hehe', db=foo)

            with self.getTestDir() as dirn2:

                argv = (core.dirn, dirn2)

                self.eq(0, s_backup.main(argv))

                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs={'tmp'})
                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))

                # We expect the data.mdb file to be in the fpset
                self.isin(f'/layers/{layriden}/layer_v2.lmdb/data.mdb', fpset)

            # Test corner case no-lmdbinfo
            with self.getTestDir() as dirn2:
                with self.getLoggerStream('synapse.tools.backup') as stream:
                    s_backup.txnbackup({}, core.dirn, dirn2)
                    stream.seek(0)
                    self.isin('not copied', stream.read())

    async def test_backup_exclude(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                layriden = core.getLayer().iden

            with self.getTestDir() as dirn2:

                argv = (
                    core.dirn,
                    dirn2,
                    '--skipdirs', '**/nodeedits.lmdb', './axon',
                )

                self.eq(0, s_backup.main(argv))

                skipdirs = {'tmp', 'nodeedits.lmdb', 'axon'}
                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs=skipdirs)

                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'axon')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'layers', layriden, 'nodeedits.lmdb')))

                self.true(os.path.exists(s_common.genpath(dirn2, 'layers', layriden, 'layer_v2.lmdb')))
                self.isin(f'/layers/{layriden}/layer_v2.lmdb/data.mdb', fpset)

            with self.getTestDir() as dirn2:

                argv = (
                    core.dirn,
                    dirn2,
                    '--skipdirs', 'layers/*',
                )

                self.eq(0, s_backup.main(argv))

                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs={'tmp', layriden})

                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))
                self.true(os.path.exists(s_common.genpath(dirn2, 'layers')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'layers', layriden)))

                self.true(os.path.exists(s_common.genpath(dirn2, 'slabs', 'cell.lmdb')))
                self.isin(f'/slabs/cell.lmdb/data.mdb', fpset)
