import lmdb
import synapse.common as s_common
import synapse.lib.lmdb as s_lmdb

from synapse.tests.common import *

class LmdbTest(SynTest):

    def test_lmdb_seqn(self):

        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            seqn = s_lmdb.Seqn(lenv, b'seqn:test')

            items = ('foo', 10, 20)

            with lenv.begin(write=True) as xact:
                seqn.save(xact, items)

            retn = tuple(seqn.iter(0))
            self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

            lenv.close()

    def test_lmdb_propstor(self):

        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            buid0 = s_common.buid()
            buid1 = s_common.buid()

            psto = s_lmdb.PropStor(lenv)

            props = (
                (buid0, (
                    ('foo:bar', s_lmdb.STOR_TYPE_UINT64, 0, 99),
                    ('foo:baz', s_lmdb.STOR_TYPE_UTF8, 0, 'asdf'),
                )),
                (buid1, (
                    ('foo:bar', s_lmdb.STOR_TYPE_UINT64, 0, 99),
                    ('foo:baz', s_lmdb.STOR_TYPE_UTF8, 0, 'qwer'),
                )),
            )

            with lenv.begin(write=True) as xact:
                retn = list(psto.addPropRows(xact, props))

            with lenv.begin() as xact:
                retn = list(psto.getRecsByBuids(xact, (buid0,)))

            self.len(1, retn)

            self.eq(retn[0][0], buid0)
            self.eq(tuple(sorted(retn[0][1])), (('foo:bar', 99), ('foo:baz', 'asdf')))

            with lenv.begin() as xact:
                props = (('foo:bar', s_lmdb.STOR_TYPE_UINT64, 0, 99), )
                retn = list(psto.getRowsByPropEq(xact, props))

            self.isin((buid0, 'foo:bar', 99), retn)
            self.isin((buid1, 'foo:bar', 99), retn)

            nidx = (
                (buid0, (
                    ('foo:noidx', s_lmdb.STOR_TYPE_UINT64, s_lmdb.STOR_FLAG_NOINDEX, 100),
                )),
                (buid1, (
                    ('foo:mult', s_lmdb.STOR_TYPE_UTF8, s_lmdb.STOR_FLAG_MULTIVAL, 'hehe'),
                    ('foo:mult', s_lmdb.STOR_TYPE_UTF8, s_lmdb.STOR_FLAG_MULTIVAL, 'haha'),
                )),
            )

            with lenv.begin(write=True) as xact:
                retn = list(psto.addPropRows(xact, nidx))

            with lenv.begin() as xact:

                props = (('foo:noidx', s_lmdb.STOR_TYPE_UINT64, 0, 100), )

                retn = list(psto.getRowsByPropEq(xact, props))
                self.len(0, retn)

                retn = list(psto.getRecsByBuids(xact, (buid0,)))
                self.isin(('foo:noidx', 100), retn[0][1])

                retn = list(psto.getRecsByBuids(xact, (buid1,)))

                self.isin(('foo:mult', 'hehe'), retn[0][1])
                self.isin(('foo:mult', 'haha'), retn[0][1])

            stor = ('newp', [], {})
            def store():
                return list(psto.store((stor,)))

            self.raises(s_exc.NoSuchFunc, store)

            stor = ('prop:set', (
                (buid0, (
                    ('foo:zzz', s_lmdb.STOR_TYPE_UINT64, 0, 22),
                )),
            ))

            edits = list(psto.store((stor,)))

            with lenv.begin() as xact:
                retn = list(psto.getRecsByBuids(xact, (buid0,)))
                self.isin(('foo:zzz', 22), retn[0][1])
