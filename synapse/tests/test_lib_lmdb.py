import lmdb

import synapse.lib.lmdb as s_lmdb

from synapse.tests.common import *

class LmdbTest(SynTest):

    def test_lmdb_seqn(self):

        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            seqn = s_lmdb.Seqn(lenv, b'seqn:test')

            items = ('foo', 10, 20)

            with lenv.begin(write=True) as xact:
                self.eq(seqn.nextindx(xact), 0)
                seqn.save(xact, items)
                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

                self.raises(TypeError, seqn.save, xact, ({'set'},))
                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

                self.eq(seqn.nextindx(xact), 3)

            lenv.close()

            # Reopen the seqn and continue where we left off
            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)
            seqn = s_lmdb.Seqn(lenv, b'seqn:test')
            self.eq(seqn.index(), 3)

            with lenv.begin(write=True) as xact:
                self.eq(seqn.nextindx(xact), 3)
                seqn.save(xact, items)

                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20),
                               (3, 'foo'), (4, 10), (5, 20)))
                self.eq(seqn.nextindx(xact), 6)

            with lenv.begin() as xact:
                # We can also start in the middle of the sequence
                retn = tuple(seqn.iter(xact, 4))
                self.eq(retn, ((4, 10), (5, 20)))

            with lenv.begin() as xact:
                # iterating past the end yields nothing
                retn = tuple(seqn.iter(xact, 100))
                self.eq(retn, ())

            # A xact which is not a writer fails
            with lenv.begin() as xact:
                self.raises(lmdb.ReadonlyError, seqn.save, xact, items)

            # A subseqeunt write works.
            with lenv.begin(write=True) as xact:
                seqn.save(xact, items)
                retn = tuple(seqn.iter(xact, 0))
                self.len(9, retn)

            lenv.close()

    def test_lmdb_seqn_raceattempt(self):
        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)
            seqn = s_lmdb.Seqn(lenv, b'seqn:test')

            evt = threading.Event()
            evt1 = threading.Event()
            evt2 = threading.Event()
            evt3 = threading.Event()
            evt4 = threading.Event()

            @firethread
            def race(n, m, e):
                valus = [i for i in range(n, m)]
                e.set()
                evt.wait()
                with lenv.begin(write=True) as xact:
                    seqn.save(xact, valus)

            thr1 = race(10000, 20000, evt1)
            thr2 = race(20000, 30000, evt2)
            thr3 = race(30000, 40000, evt3)
            thr4 = race(40000, 50000, evt4)
            evt1.wait()
            evt2.wait()
            evt3.wait()
            evt4.wait()
            evt.set()

            thr1.join()
            thr2.join()
            thr3.join()
            thr4.join()

            with lenv.begin(write=False) as xact:
                retn = tuple(seqn.iter(xact, 0))
                offsets = [off for off, valu in retn]
                valus = [valu for off, valu in retn]
                self.len(40000, offsets)
                self.eq(offsets, [i for i in range(40000)])
                # Everything makes it in but order isn't guaranteed
                self.eq(sorted(valus), [i for i in range(10000, 50000)])

    def test_lmdb_metrics(self):

        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)
            metr = s_lmdb.Metrics(lenv)
            self.eq(metr.stat(), {})

            self.eq(0, metr.indx)

            with lenv.begin(write=True) as xact:
                metr.inc(xact, 'woot', 20)
                metr.inc(xact, 'woot', 20)
                metr.record(xact, {'hehe': 10, 'haha': 20})
                metr.record(xact, {'hehe': 20, 'haha': 30})

            self.eq(2, metr.indx)

            lenv.sync()
            lenv.close()

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            metr = s_lmdb.Metrics(lenv)
            with lenv.begin(write=True) as xact:

                self.eq(metr.info.get('woot'), 40)

                retn = list(metr.iter(xact, 1))
                self.len(1, retn)
                self.eq(retn[0][0], 1)
                self.eq(retn[0][1].get('hehe'), 20)

                self.len(0, list(metr.iter(xact, 1234567890)))

            self.eq(2, metr.indx)
            with lenv.begin(write=True) as xact:
                metr.record(xact, {'hehe': 30, 'haha': 20})
                metr.record(xact, {'hehe': 40, 'haha': 30})
            self.eq(4, metr.indx)

            with lenv.begin(write=False) as xact:
                retn = list(metr.iter(xact, 0))
                self.eq([off for off, item in retn], [0, 1, 2, 3])

            self.eq(metr.stat(), {'woot': 40})

    def test_lmdb_propstor(self):

        with self.getTestDir() as dirn:

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            # this allows result sorting...
            buid0 = b'\x00' * 32
            buid1 = b'\x01' * 32

            psto = s_lmdb.PropStor(lenv)

            recs = (
                (buid0, (
                    (b'foo:bar', b'asdfqwer', 0),
                    (b'foo:baz', b'asdfasdf', 0),
                    (b'foo:intish', b'\x00\x80', 0),
                )),
                (buid1, (
                    (b'foo:bar', b'asdfzxcv', 0),
                    (b'foo:baz', b'qwer', 0),
                    (b'foo:intish', b'\x00\x01', 0),
                )),
            )

            with lenv.begin(write=True) as xact:
                setr = psto.getPropSetr(xact)
                retn = list(setr.put(recs))
                self.len(2, retn)
                self.eq(retn[0][0], 0)
                self.eq(retn[0][1][0], buid0)
                self.isinstance(retn[0][1][1], list)
                edit = retn[0][1][1][0]
                self.len(3, edit)
                self.isinstance(edit[0], bytes)
                self.isinstance(edit[1], bytes)
                self.isinstance(edit[2], int)

            with lenv.begin(write=True) as xact:

                setr = psto.getPropSetr(xact=xact)
                self.true(setr.has(b'foo:baz', b'qwer'))
                self.false(setr.has(b'foo:lol', b'rofl'))
                self.true(setr.has(b'foo:baz', b'qwer'))

                self.true(setr.set(buid0, b'foo:lol', b'rofl'))
                self.true(setr.has(b'foo:lol', b'rofl'))
                self.true(setr.has(b'foo:baz', b'qwer'))

                self.false(setr.set(buid0, b'foo:lol', b'rofl'))
                self.false(setr.set(buid0, b'foo:lol', b'defv', flags=s_lmdb.STOR_FLAG_DEFVAL))
                self.false(setr.has(b'foo:lol', b'defv'))
                self.true(setr.has(b'foo:lol', b'rofl'))
                self.true(psto.has(xact, b'foo:lol', b'rofl'))

                self.true(setr.set(buid0, b'foo:lol', b'woo'))
                self.true(setr.has(b'foo:lol', b'woo'))
                self.true(psto.has(xact, b'foo:lol', b'woo'))
                self.false(setr.has(b'foo:lol', b'defv'))
                self.false(setr.has(b'foo:lol', b'rofl'))
                self.false(psto.has(xact, b'foo:lol', b'defv'))
                self.false(psto.has(xact, b'foo:lol', b'rofl'))

                self.true(setr.set(buid1, b'foo:multi', b'root', flags=s_lmdb.STOR_FLAG_MULTIVAL))
                self.true(setr.set(buid1, b'foo:multi', b'user', flags=s_lmdb.STOR_FLAG_MULTIVAL))
                self.true(setr.has(b'foo:multi', b'root'))
                self.true(setr.has(b'foo:multi', b'user'))
                self.false(setr.set(buid1, b'foo:multi', b'user', flags=s_lmdb.STOR_FLAG_MULTIVAL))

                retn = tuple(sorted(psto.pref(xact, b'e', b'gg')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.pref(xact, b'f', b'gg')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.pref(xact, b'foo:ba', b'asdf')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.pref(xact, b'foo:baa', b'asdf')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.pref(xact, b'foo:bar', b'asdf')))
                self.eq(retn, ((buid0, b'foo:bar', b'asdfqwer'), (buid1, b'foo:bar', b'asdfzxcv')))
                retn = tuple(sorted(psto.pref(xact, b'g', b'gg')))
                self.eq(retn, ())

                retn = tuple(sorted(psto.range(xact, b'e', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.range(xact, b'foo:intaaa', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.range(xact, b'foo:intish', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ((buid1, b'foo:intish', b'\x00\x01'),))
                retn = tuple(sorted(psto.range(xact, b'foo:nothere', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ())
                retn = tuple(sorted(psto.range(xact, b'g', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ())

                retn = tuple(sorted(psto.eq(xact, b'foo:intish', b'\x00\x01')))
                self.eq(retn, ((buid1, b'foo:intish', b'\x00\x01'), ))
                retn = tuple(sorted(psto.eq(xact, b'foo:nothere', b'\x00\x01')))
                self.eq(retn, ())

            buid2 = b'\x02' * 32
            buid3 = b'\x03' * 32
            rows = (
                (buid2, b'hehe:a', b'haha'),
                (buid2, b'hehe:b', b'haha'),
                (buid3, b'hehe:c', b'haha'),
            )
            with lenv.begin(write=True) as xact:
                setr = psto.getPropSetr(xact=xact)
                setr.set(*rows[0])
                setr.set(*rows[1])
                # don't add the last row

                retn = tuple(sorted(psto.recs(xact, rows)))
                self.len(3, retn)
                self.eq(retn[0], (buid2, [(rows[0][1], rows[0][2]), (rows[1][1], rows[1][2]), ]))
                self.eq(retn[1], (buid2, [(rows[0][1], rows[0][2]), (rows[1][1], rows[1][2]), ]))  # FIXME do we really need this twice?
                self.eq(retn[2], (buid3, ()))

    def test_lmdb_encode(self):
        pos_enc = s_lmdb.encodeValAsKey(42)
        very_pos = s_lmdb.encodeValAsKey(42 * 1000000000)
        neg_enc = s_lmdb.encodeValAsKey(-42)
        zero_enc = s_lmdb.encodeValAsKey(0)
        very_neg = s_lmdb.encodeValAsKey(-42 * 1000000000)
        self.true(very_neg < neg_enc < zero_enc < pos_enc < very_pos)

        sm_str = 'leet0'
        med_str = 'leet0' * 10
        long_str = 'leet0' * 200
        very_long_str = 'leet0' * 300
        sm_enc, med_enc, long_enc, very_long_enc = \
            (s_lmdb.encodeValAsKey(x, isprefix=True) for x in (sm_str, med_str, long_str, very_long_str))
        sm_enc2, med_enc2, long_enc2, very_long_enc2 = \
            (s_lmdb.encodeValAsKey(x) for x in (sm_str, med_str, long_str, very_long_str))
        self.true(very_long_enc2.startswith(long_enc))
        self.true(long_enc2.startswith(med_enc))
        self.true(med_enc2.startswith(sm_enc))
        self.false(very_long_enc2.startswith(long_enc2))
        self.false(long_enc2.startswith(med_enc2))
        self.false(med_enc2.startswith(sm_enc2))
        self.false(very_long_enc.startswith(long_enc2))
        self.false(long_enc.startswith(med_enc2))
        self.false(med_enc.startswith(sm_enc2))
