import os
import asyncio
import pathlib
import multiprocessing
import synapse.exc as s_exc
import synapse.common as s_common

from unittest.mock import patch

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class LmdbSlabTest(s_t_utils.SynTest):

    async def test_lmdbslab_base(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            await self.asyncraises(s_exc.BadArg, s_lmdbslab.Slab.anit(path, map_size=None))

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

            # Copy a database inside the same slab
            self.raises(s_exc.DataAlreadyExists, slab.copydb, foo, slab, 'bar')
            self.eq(3, slab.copydb(foo, slab, 'foo2'))

            # Increase the size of the new source DB to trigger a resize on the next copydb
            foo2 = slab.initdb('foo2')
            slab.put(b'bigkey', b'x' * 1024 * 1024, dupdata=True, db=foo2)

            vardict = {}

            def progfunc(count):
                vardict['prog'] = count

            # Copy a database to a different slab
            path2 = os.path.join(dirn, 'test2.lmdb')
            async with await s_lmdbslab.Slab.anit(path2, map_size=512 * 1024) as slab2:
                with patch('synapse.lib.lmdbslab.PROGRESS_PERIOD', 2):

                    self.eq(4, slab.copydb(foo2, slab2, destdbname='foo2', progresscb=progfunc))
                    self.gt(vardict.get('prog', 0), 0)

            # Test slab.drop and slab.dbexists
            self.true(slab.dbexists('foo2'))
            slab.dropdb('foo2')
            self.false(slab.dbexists('foo2'))

            self.none(slab.dropdb('notadb'))

            # start a scan and then fini the whole db...
            scan = slab.scanByPref(b'\x00', db=foo)
            self.eq((b'\x00\x01', b'hehe'), next(scan))

            await slab.fini()

            self.raises(s_exc.IsFini, next, scan)

    async def test_lmdbslab_maxsize(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.lmdb')

            my_maxsize = 400000
            async with await s_lmdbslab.Slab.anit(path, map_size=100000, maxsize=my_maxsize) as slab:
                foo = slab.initdb('foo', dupsort=True)
                byts = b'\x00' * 256

                # Trigger an out-of-space
                with self.raises(s_exc.DbOutOfSpace):

                    for i in range(400):
                        slab.put(b'\xff\xff\xff\xff' + s_common.guid(i).encode('utf8'), byts, db=foo)

            # lets ensure our maxsize persisted and it caps the mapsize
            async with await s_lmdbslab.Slab.anit(path, map_size=100000, readonly=True) as newdb:
                self.eq(my_maxsize, newdb.mapsize)
                self.eq(my_maxsize, newdb.maxsize)

    async def test_lmdbslab_grow(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, growsize=10000) as slab:

                foo = slab.initdb('foo', dupsort=True)
                foo2 = slab.initdb('foo2', dupsort=False)

                byts = b'\x00' * 256
                for i in range(100):
                    slab.put(s_common.guid(i).encode('utf8'), byts, db=foo)
                    slab.put(s_common.guid(1000 + i).encode('utf8'), byts, db=foo2)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 100)

                # Trigger a grow/bump in the middle of a scan; make sure new nodes come after current scan position
                iter = slab.scanByRange(b'', db=foo)
                for i in range(50):
                    next(iter)

                multikey = b'\xff\xff\xff\xfe' + s_common.guid(2000).encode('utf8')
                mapsize = slab.mapsize
                count = 0

                # Write until we grow
                while mapsize == slab.mapsize:
                    count += 1
                    rv = slab.put(multikey, s_common.guid(count + 100000).encode('utf8') + byts, dupdata=True, db=foo)
                    self.true(rv)

                self.eq(50 + count, sum(1 for _ in iter))

                self.true(os.path.isfile(slab.optspath))

                # Trigger a grow/bump in the middle of a dup scan
                iter = slab.scanByDups(multikey, db=foo)
                next(iter)

                iter2 = slab.scanByFull(db=foo2)
                next(iter2)

                multikey = b'\xff\xff\xff\xff' + s_common.guid(i + 150000).encode('utf8')
                for i in range(200):
                    slab.put(multikey, s_common.guid(i + 200000).encode('utf8') + byts, dupdata=True, db=foo)

                self.eq(count - 1, sum(1 for _ in iter))
                self.eq(99, sum(1 for _ in iter2))

            # lets ensure our mapsize / growsize persisted, and make sure readonly works
            async with await s_lmdbslab.Slab.anit(path, map_size=100000, readonly=True) as newdb:

                self.eq(10000, newdb.growsize)
                foo = newdb.initdb('foo', dupsort=True)
                for _, _ in newdb.scanByRange(b'', db=foo):
                    count += 1
                self.gt(count, 200)

                # Make sure readonly is really readonly
                self.raises(s_exc.IsReadOnly, newdb.dropdb, 'foo')
                self.raises(s_exc.IsReadOnly, newdb.put, b'1234', b'3456')
                self.raises(s_exc.IsReadOnly, newdb.replace, b'1234', b'3456')
                self.raises(s_exc.IsReadOnly, newdb.pop, b'1234')
                self.raises(s_exc.IsReadOnly, newdb.delete, b'1234')
                self.raises(s_exc.IsReadOnly, newdb.putmulti, ((b'1234', b'3456'),))

                # While we have the DB open in readonly, have another process write a bunch of data to cause the
                # map size to be increased

                def anotherproc(path):
                    async def lotsofwrites(path):
                        os.remove(pathlib.Path(path).with_suffix('.opts.yaml'))
                        async with await s_lmdbslab.Slab.anit(path, map_size=100000) as slab:
                            foo = slab.initdb('foo', dupsort=True)
                            mapsize = slab.mapsize
                            count = 0
                            while mapsize == slab.mapsize:
                                count += 1
                                slab.put(b'abcd', s_common.guid(count).encode('utf8') + byts, dupdata=True, db=foo)
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
                    slab.put(key, s_common.guid(i).encode('utf8'), db=foo)

                count = 0
                for _, _ in slab.scanByRange(b'', db=foo):
                    count += 1
                self.eq(count, 100)

                # Partially read through scan
                iter = slab.scanByRange(lmin=key, lmax=key, db=foo)
                for i in range(60):
                    next(iter)

                # Trigger a bump by writing a bunch; make sure we're not writing into the middle of the scan
                multikey = b'\xff\xff\xff\xff' + s_common.guid(200).encode('utf8')
                mapsize = slab.mapsize
                count = 0
                while mapsize == slab.mapsize:
                    count += 1
                    slab.put(multikey, s_common.guid(count).encode('utf8') + b'0' * 256, dupdata=True, db=foo)

                # we wrote 100, read 60.  We should read only another 40
                self.len(40, list(iter))

    async def test_slab_guid_stor(self):

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'slab.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                guidstor = s_lmdbslab.GuidStor(slab, 'guids')

                info0 = guidstor.gen('aaaa')
                info0.set('hehe', 20)
                self.eq(20, info0.get('hehe'))
                self.none(info0.get('haha'))

                info0.set('woot', {'woot': 1})
                self.eq((('hehe', 20), ('woot', {'woot': 1})), info0.items())

                self.eq({'woot': 1}, info0.get('woot'))
                self.eq({'woot': 1}, info0.pop('woot'))
                self.none(info0.get('woot'))
                self.none(info0.pop('woot'))
                self.true(info0.pop('woot', s_common.novalu) is s_common.novalu)

                # Sad path case
                self.raises(TypeError, info0.set, 'newp', {1, 2, 3})

            async with await s_lmdbslab.Slab.anit(path) as slab:
                guidstor = s_lmdbslab.GuidStor(slab, 'guids')
                info1 = guidstor.gen('aaaa')
                self.eq(20, info1.get('hehe'))
                self.none(info1.pop('woot'))
                self.len(1, info1.items())
                self.eq((('hehe', 20), ), info1.items())

    async def test_slab_initdb_grow(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'slab.lmdb')
            async with await s_lmdbslab.Slab.anit(path, map_size=1024) as slab:
                [slab.initdb(str(i)) for i in range(10)]

    def test_slab_math(self):
        self.eq(s_lmdbslab._mapsizeround(100), 128)
        self.eq(s_lmdbslab._mapsizeround(s_const.mebibyte), s_const.mebibyte)
        self.eq(s_lmdbslab._mapsizeround(s_const.mebibyte + 1), 2 * s_const.mebibyte)
        self.eq(s_lmdbslab._mapsizeround(65 * s_const.gibibyte), 100 * s_const.gibibyte)
        self.eq(s_lmdbslab._mapsizeround(472 * s_const.gibibyte), 500 * s_const.gibibyte)
        self.eq(s_lmdbslab._mapsizeround(1000 * s_const.gibibyte), 1000 * s_const.gibibyte)

    async def test_slab_infinite_loop(self):
        '''
        Trigger a map full when replaying the log from a prior map full.
        '''
        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            byts = b'\x00' * 256

            count = 0
            async with await s_lmdbslab.Slab.anit(path, map_size=32000, growsize=5000) as slab:
                foo = slab.initdb('foo')
                slab.put(b'abcd', s_common.guid(count).encode('utf8') + byts, db=foo)
                await asyncio.sleep(1.1)
                count += 1
                slab.put(b'abcd', s_common.guid(count).encode('utf8') + byts, db=foo)

            # If we got here we're good
            self.true(True)

    async def test_slab_mapfull_runsyncloop(self):
        '''
        forcecommit in runSyncLoop can very occasionally trigger a mapfull
        '''
        fake_confdefs = (
            ('lmdb:mapsize', {'type': 'int', 'defval': s_const.mebibyte}),
            ('lmdb:maxsize', {'type': 'int', 'defval': None}),
            ('lmdb:growsize', {'type': 'int', 'defval': 128 * s_const.kibibyte}),
            ('lmdb:readahead', {'type': 'bool', 'defval': True}),
        )
        with patch('synapse.lib.lmdblayer.LmdbLayer.confdefs', fake_confdefs):
            batchsize = 4000
            numbatches = 2
            async with self.getTestCore() as core:
                before_mapsize = core.view.layers[0].layrslab.mapsize
                for i in range(numbatches):
                    async with await core.snap() as snap:
                        ips = ((('test:int', i * 1000000 + x), {'props': {'loc': 'us'}}) for x in range(batchsize))
                        await alist(snap.addNodes(ips))
                        # Wait for the syncloop to run
                        await asyncio.sleep(1.1)

                # Verify that it hit
                self.gt(core.view.layers[0].layrslab.mapsize, before_mapsize)

    async def test_slab_mapfull_drop(self):
        '''
        Test a mapfull in the middle of a dropdb
        '''
        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            data = [i.to_bytes(4, 'little') for i in range(400)]

            async with await s_lmdbslab.Slab.anit(path, map_size=32000, growsize=5000) as slab:
                slab.initdb('foo')
                kvpairs = [(x, x) for x in data]
                slab.putmulti(kvpairs)
                slab.forcecommit()
                before_mapsize = slab.mapsize
                slab.dropdb('foo')
                self.false(slab.dbexists('foo'))
                self.gt(slab.mapsize, before_mapsize)
