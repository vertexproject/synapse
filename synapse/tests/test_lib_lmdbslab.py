import os
import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

class LmdbSlabTest(s_t_utils.SynTest):
    async def test_lmdb_slab_base(self):

        self.true(s_glob.plex.iAmLoop())

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            slab = await s_lmdbslab.Slab.anit(path, map_size=1000000)

            foo = slab.initdb('foo')
            bar = slab.initdb('bar', dupsort=True)

            slab.put(b'\x00\x01', b'hehe', db=foo)
            slab.put(b'\x00\x02', b'haha', db=foo)
            slab.put(b'\x00\x03', b'hoho', db=foo)

            slab.put(b'\x00\x01', b'hehe', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'haha', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'visi', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'zomg', dupdata=True, db=bar)
            slab.put(b'\x00\x03', b'hoho', dupdata=True, db=bar)

            self.true(slab.dirty)

            self.true(slab.forcecommit())
            self.false(slab.dirty)

            self.eq(b'hehe', slab.get(b'\x00\x01', db=foo))

            items = list(slab.scanByPref(b'\x00', db=foo))
            self.eq(items, ((b'\x00\x01', b'hehe'), (b'\x00\x02', b'haha'), (b'\x00\x03', b'hoho')))

            items = list(slab.scanByRange(b'\x00\x02', b'\x00\x03', db=foo))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x03', b'hoho')))

            items = list(slab.scanByDups(b'\x00\x02', db=bar))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x02', b'visi'), (b'\x00\x02', b'zomg')))

            # ok... lets start a scan and then rip out the xact...
            scan = slab.scanByPref(b'\x00', db=foo)
            self.eq((b'\x00\x01', b'hehe'), next(scan))

            slab.forcecommit()

            items = list(scan)
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x03', b'hoho')))

            # to test iternext_dup, lets do the same with a dup scan
            scan = slab.scanByDups(b'\x00\x02', db=bar)
            self.eq((b'\x00\x02', b'haha'), next(scan))

            slab.forcecommit()

            items = list(scan)
            self.eq(items, ((b'\x00\x02', b'visi'), (b'\x00\x02', b'zomg')))

            # start a scan and then fini the whole db...
            scan = slab.scanByPref(b'\x00', db=foo)
            self.eq((b'\x00\x01', b'hehe'), next(scan))

            await slab.fini()

            self.raises(s_exc.IsFini, next, scan)

    async def test_lmdb_slab_grow(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            my_maxsize = 350000

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, maxsize=my_maxsize) as slab:

                foo = slab.initdb('foo')

                byts = b'\x00' * 1024
                for i in range(50):
                    slab.put(s_common.guid().encode('utf8'), byts, db=foo)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 50)

                iter = slab.scanByRange(b'', db=foo)
                for i in range(25):
                    next(iter)

                # Trigger a grow/bump in the middle of a scan; make sure new nodes come after current scan position
                for i in range(50):
                    slab.put(b'\xff\xff\xff\xff' + s_common.guid().encode('utf8'), byts, db=foo)

                self.eq(75, sum(1 for _ in iter))

                self.true(os.path.isfile(slab.optspath))

                # Trigger an out-of-space
                try:
                    for i in range(50):
                        slab.put(b'\xff\xff\xff\xff' + s_common.guid().encode('utf8'), byts, db=foo)

                    # Should have hit a DbOutOfSpace exception
                    self.true(0)

                except s_exc.DbOutOfSpace:
                    pass

            # lets ensure our mapsize / growsize persisted

            async with await s_lmdbslab.Slab.anit(path, map_size=100000) as newdb:

                self.eq(my_maxsize, newdb.mapsize)

                self.none(newdb.growsize)
