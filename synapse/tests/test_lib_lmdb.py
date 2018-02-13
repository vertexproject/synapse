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
                seqn.save(xact, items)
                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

                self.raises(TypeError, seqn.save, xact, ({'set'},))
                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

            lenv.close()

            # Reopen the seqn and continue where we left off
            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)
            seqn = s_lmdb.Seqn(lenv, b'seqn:test')

            with lenv.begin(write=True) as xact:
                seqn.save(xact, items)

                retn = tuple(seqn.iter(xact, 0))
                self.eq(retn, ((0, 'foo'), (1, 10), (2, 20),
                               (3, 'foo'), (4, 10), (5, 20)))

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

            with lenv.begin(write=True) as xact:

                metr.inc(xact, 'woot', 20)
                metr.inc(xact, 'woot', 20)
                metr.record(xact, {'hehe': 10, 'haha': 20})
                metr.record(xact, {'hehe': 20, 'haha': 30})

            lenv.sync()
            lenv.close()

            lenv = lmdb.open(dirn, writemap=True, max_dbs=128)

            metr = s_lmdb.Metrics(lenv)
            with lenv.begin(write=True) as xact:

                self.eq(metr.info.get('woot'), 40)

                retn = list(metr.iter(xact, 1))
                self.len(1, retn)
                self.eq(retn[0][1].get('hehe'), 20)

                self.len(0, list(metr.iter(xact, 1234567890)))

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

                retn = tuple(sorted(psto.range(xact, b'foo:intish', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ((buid1, b'foo:intish', b'\x00\x01'),))
                retn = tuple(sorted(psto.range(xact, b'foo:nothere', b'\x00\x00', b'\x00\x80')))
                self.eq(retn, ())

                retn = tuple(sorted(psto.eq(xact, b'foo:intish', b'\x00\x01')))
                self.eq(retn, ((buid1, b'foo:intish', b'\x00\x01'), ))
                retn = tuple(sorted(psto.eq(xact, b'foo:nothere', b'\x00\x01')))
                self.eq(retn, ())
