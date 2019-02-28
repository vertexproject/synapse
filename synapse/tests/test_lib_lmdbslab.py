import os
import asyncio
import multiprocessing
import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

class LmdbSlabTest(s_t_utils.SynTest):

    async def test_lmdbslab_base(self):

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
                foo2 = slab.initdb('foo2', dupsort=False)

                byts = b'\x00' * 256
                for i in range(100):
                    slab.put(s_common.guid().encode('utf8'), byts, db=foo)
                    slab.put(s_common.guid().encode('utf8'), byts, db=foo2)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 100)

                # Trigger a grow/bump in the middle of a scan; make sure new nodes come after current scan position
                iter = slab.scanByRange(b'', db=foo)
                for i in range(50):
                    next(iter)

                multikey = b'\xff\xff\xff\xfe' + s_common.guid().encode('utf8')
                mapsize = slab.mapsize
                count = 0

                # Write until we grow
                while mapsize == slab.mapsize:
                    count += 1
                    rv = slab.put(multikey, s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)
                    self.true(rv)

                self.eq(50 + count, sum(1 for _ in iter))

                self.true(os.path.isfile(slab.optspath))

                # Trigger a grow/bump in the middle of a dup scan
                iter = slab.scanByDups(multikey, db=foo)
                next(iter)

                iter2 = slab.scanByFull(db=foo2)
                next(iter2)

                multikey = b'\xff\xff\xff\xff' + s_common.guid().encode('utf8')
                for i in range(200):
                    slab.put(multikey, s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)

                self.eq(count - 1, sum(1 for _ in iter))
                self.eq(99, sum(1 for _ in iter2))

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
                self.raises(s_exc.IsReadOnly, newdb.put, b'1234', b'3456')
                self.raises(s_exc.IsReadOnly, newdb.replace, b'1234', b'3456')
                self.raises(s_exc.IsReadOnly, newdb.pop, b'1234')
                self.raises(s_exc.IsReadOnly, newdb.delete, b'1234')
                self.raises(s_exc.IsReadOnly, newdb.putmulti, ((b'1234', b'3456'),))

                # While we have the DB open in readonly, have another process write a bunch of data to cause the
                # map size to be increased

                def anotherproc(path):
                    async def lotsofwrites(path):
                        async with await s_lmdbslab.Slab.anit(path) as slab:
                            foo = slab.initdb('foo', dupsort=True)
                            mapsize = slab.mapsize
                            while mapsize == slab.mapsize:
                                slab.put(b'abcd', s_common.guid().encode('utf8') + byts, dupdata=True, db=foo)
                    asyncio.run(lotsofwrites(path))

                proc = multiprocessing.Process(target=anotherproc, args=(path, ))
                proc.start()
                proc.join()

                # Now trigger a remap for me
                newdb.get(multikey, db=foo)

    async def test_lmdbslab_grow_putmulti(self):
        '''
        Test for a regression where putmulti's across a grow could corrupt the database

        Test for a regression where a generator being passed into a putmulti would result in a partial write
        '''
        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            data = [i.to_bytes(4, 'little') for i in range(1000)]

            async with await s_lmdbslab.Slab.anit(path, map_size=10000) as slab:
                # A putmulti across a grow
                before_mapsize = slab.mapsize
                kvpairs = [(x, x) for x in data]
                retn = slab.putmulti(kvpairs)
                self.eq(retn, (1000, 1000))

                after_mapsize1 = slab.mapsize
                self.gt(after_mapsize1, before_mapsize)

                # A putmulti across a grow with a generator passed in
                kvpairs = ((b' ' + x, x) for x in data)
                retn = slab.putmulti(kvpairs)
                self.eq(retn, (1000, 1000))
                after_mapsize2 = slab.mapsize
                self.gt(after_mapsize2, after_mapsize1)

    async def test_lmdbslab_iternext_repeat_regression(self):
        '''
        Test for a scan being bumped in an iternext where the cursor is in the middle of a list of values with the same
        key
        '''

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            my_maxsize = 500000

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, growsize=50000, maxsize=my_maxsize) as slab:
                foo = slab.initdb('foo', dupsort=True)

                key = b'foo'
                for i in range(100):
                    slab.put(key, s_common.guid().encode('utf8'), db=foo)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 100)

                # Partially read through scan
                iter = slab.scanByRange(lmin=key, lmax=key, db=foo)
                for i in range(60):
                    next(iter)

                # Trigger a bump by writing a bunch; make sure we're not writing into the middle of the scan
                multikey = b'\xff\xff\xff\xff' + s_common.guid().encode('utf8')
                mapsize = slab.mapsize
                while mapsize == slab.mapsize:
                    slab.put(multikey, s_common.guid().encode('utf8') + b'0' * 256, dupdata=True, db=foo)

                # we wrote 100, read 60.  We should read only another 40
                self.len(40, list(iter))

    async def test_slab_guid_stor(self):

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'slab.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                guidstor = s_lmdbslab.GuidStor(slab, 'guids')

                info0 = guidstor.gen('aaaa')
                info0.set('hehe', 20)

            async with await s_lmdbslab.Slab.anit(path) as slab:
                guidstor = s_lmdbslab.GuidStor(slab, 'guids')
                info1 = guidstor.gen('aaaa')
                self.eq(20, info1.get('hehe'))
