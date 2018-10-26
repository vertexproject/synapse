import os
import asyncio
import multiprocessing
import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

class LmdbSlabTest(s_t_utils.SynTest):
    async def test_lmdbslab_base(self):

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

    async def test_lmdbslab_grow(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            my_maxsize = 500000

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, growsize=50000, maxsize=my_maxsize) as slab:

                foo = slab.initdb('foo', dupsort=True)

                byts = b'\x00' * 256
                for i in range(200):
                    slab.put(s_common.guid().encode('utf8'), byts, db=foo)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 200)

                # Trigger a grow/bump in the middle of a scan; make sure new nodes come after current scan position
                iter = slab.scanByRange(b'', db=foo)
                for i in range(50):
                    next(iter)

                multikey = b'\xff\xff\xff\xfe' + s_common.guid().encode('utf8')
                for i in range(100):
                    rv = slab.put(multikey, s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)
                    self.true(rv)

                self.eq(250, sum(1 for _ in iter))

                self.true(os.path.isfile(slab.optspath))

                # Trigger a grow/bump in the middle of a dup scan
                iter = slab.scanByDups(multikey, db=foo)
                for i in range(25):
                    next(iter)

                multikey = b'\xff\xff\xff\xff' + s_common.guid().encode('utf8')
                for i in range(200):
                    slab.put(multikey, s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)

                self.eq(75, sum(1 for _ in iter))

                # Trigger an out-of-space
                try:
                    for i in range(400):
                        slab.put(b'\xff\xff\xff\xff' + s_common.guid().encode('utf8'), byts, db=foo)

                    # Should have hit a DbOutOfSpace exception
                    self.true(0)

                except s_exc.DbOutOfSpace:
                    pass

            # lets ensure our mapsize / growsize persisted, and make sure readonly works
            async with await s_lmdbslab.Slab.anit(path, map_size=100000, readonly=True) as newdb:

                self.eq(my_maxsize, newdb.mapsize)

                self.eq(50000, newdb.growsize)
                foo = newdb.initdb('foo', dupsort=True)
                for _, _ in newdb.scanByRange(b'', db=foo):
                    count += 1
                self.gt(count, 300)

                # Make sure readonly is really readonly
                self.raises(s_exc.DbIsReadOnly, newdb.put, b'1234', b'3456')
                self.raises(s_exc.DbIsReadOnly, newdb.replace, b'1234', b'3456')
                self.raises(s_exc.DbIsReadOnly, newdb.pop, b'1234')
                self.raises(s_exc.DbIsReadOnly, newdb.delete, b'1234')
                self.raises(s_exc.DbIsReadOnly, newdb.putmulti, ((b'1234', b'3456'),))

                # While we have the DB open in readonly, have another process write a bunch of data to cause the
                # map size to be increased

                def anotherproc(path):
                    async def lotsofwrites(path):
                        async with await s_lmdbslab.Slab.anit(path) as slab:
                            foo = slab.initdb('foo', dupsort=True)
                            multikey = b'\xff\xff\xff\xff' + s_common.guid().encode('utf8')
                            for i in range(400):
                                slab.put(multikey, s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)
                    asyncio.run(lotsofwrites(path))

                proc = multiprocessing.Process(target=anotherproc, args=(path, ))
                proc.start()
                proc.join()

                # Now trigger a remap for me
                newdb.get(multikey, db=foo)
