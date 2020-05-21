import os
import asyncio
import pathlib
import multiprocessing
import synapse.exc as s_exc
import synapse.common as s_common

from unittest.mock import patch

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.thisplat as s_thisplat

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

def getFileMapCount(filename):
    filename = str(filename)
    count = 0
    with open(f'/proc/{os.getpid()}/maps') as maps:
        for line in maps:
            if len(line) < 50:
                continue
            if line.rstrip().endswith(filename):
                count += 1
    return count

class LmdbSlabTest(s_t_utils.SynTest):

    async def test_lmdbslab_scankeys(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path) as slab:

                testdb = slab.initdb('test')
                dupsdb = slab.initdb('dups', dupsort=True)
                editdb = slab.initdb('edit')

                self.eq((), list(slab.scanKeys(db=testdb)))

                slab.put(b'hehe', b'haha', db=dupsdb)
                slab.put(b'hehe', b'lolz', db=dupsdb)
                slab.put(b'hoho', b'asdf', db=dupsdb)

                slab.put(b'hehe', b'haha', db=testdb)
                slab.put(b'hoho', b'haha', db=testdb)

                testgenr = slab.scanKeys(db=testdb)
                dupsgenr = slab.scanKeys(db=testdb)

                testlist = [next(testgenr)]
                dupslist = [next(dupsgenr)]

                slab.put(b'derp', b'derp', db=editdb)

                # bump them both...
                await s_lmdbslab.Slab.syncLoopOnce()

                testlist.extend(testgenr)
                dupslist.extend(dupsgenr)

                self.eq(testlist, (b'hehe', b'hoho'))
                self.eq(dupslist, (b'hehe', b'hoho'))

                # now lets delete the key we're on
                testgenr = slab.scanKeys(db=testdb)
                dupsgenr = slab.scanKeys(db=testdb)

                testlist = [next(testgenr)]
                dupslist = [next(dupsgenr)]

                slab.delete(b'hehe', db=testdb)
                for lkey, lval in slab.scanByDups(b'hehe', db=dupsdb):
                    slab.delete(lkey, lval, db=dupsdb)

                await s_lmdbslab.Slab.syncLoopOnce()

                testlist.extend(testgenr)
                dupslist.extend(dupsgenr)

                self.eq(testlist, (b'hehe', b'hoho'))
                self.eq(dupslist, (b'hehe', b'hoho'))

    async def test_lmdbslab_base(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            await self.asyncraises(s_exc.BadArg, s_lmdbslab.Slab.anit(path, map_size=None))

            slab = await s_lmdbslab.Slab.anit(path, map_size=1000000, lockmemory=True)

            foo = slab.initdb('foo')
            baz = slab.initdb('baz')
            bar = slab.initdb('bar', dupsort=True)

            slab.put(b'\x00\x01', b'hehe', db=foo)
            slab.put(b'\x00\x02', b'haha', db=foo)
            slab.put(b'\x01\x03', b'hoho', db=foo)

            slab.put(b'\x00\x01', b'hehe', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'haha', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'visi', dupdata=True, db=bar)
            slab.put(b'\x00\x02', b'zomg', dupdata=True, db=bar)
            slab.put(b'\x00\x03', b'hoho', dupdata=True, db=bar)

            slab.put(b'\x00\x01', b'hehe', db=baz)
            slab.put(b'\xff', b'haha', db=baz)
            slab.put(b'\xff\xff', b'hoho', db=baz)

            self.true(slab.dirty)

            self.true(slab.forcecommit())
            self.false(slab.dirty)

            self.eq(b'hehe', slab.get(b'\x00\x01', db=foo))

            items = list(slab.scanByPref(b'\x00', db=foo))
            self.eq(items, ((b'\x00\x01', b'hehe'), (b'\x00\x02', b'haha')))

            items = list(slab.scanByRange(b'\x00\x02', b'\x01\x03', db=foo))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x01\x03', b'hoho')))

            items = list(slab.scanByDups(b'\x00\x02', db=bar))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x02', b'visi'), (b'\x00\x02', b'zomg')))

            items = list(slab.scanByDups(b'\x00\x04', db=bar))
            self.eq(items, ())

            self.true(slab.prefexists(b'\x00', db=baz))
            self.true(slab.prefexists(b'\x00\x01', db=baz))
            self.false(slab.prefexists(b'\x00\x03', db=baz))
            self.false(slab.prefexists(b'\x02', db=baz))
            self.true(slab.prefexists(b'\xff\xff', db=baz))
            self.false(slab.prefexists(b'\xff\xff', db=foo))

            self.true(slab.rangeexists(b'\x00', b'\x01', db=baz))
            self.true(slab.rangeexists(b'\x00\x00', b'\x00\x04', db=baz))
            self.false(slab.rangeexists(b'\x00\x04', b'\x01', db=baz))
            self.true(slab.rangeexists(b'\x05', None, db=baz))
            self.false(slab.rangeexists(b'\xfa', b'\xfc', db=baz))
            self.false(slab.rangeexists(b'\x00\x00', b'\x00\x00', db=foo))
            self.false(slab.rangeexists(b'\x01\x04', b'\x01\x05', db=foo))

            # backwards scan tests

            items = list(slab.scanByPrefBack(b'\x00', db=foo))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x01', b'hehe')))

            items = list(slab.scanByPrefBack(b'\x01', db=foo))
            self.eq(items, ((b'\x01\x03', b'hoho'),))

            items = list(slab.scanByPrefBack(b'\xff', db=baz))
            self.eq(items, ((b'\xff\xff', b'hoho'), (b'\xff', b'haha')))

            items = list(slab.scanByRangeBack(b'\x00\x03', db=foo))
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x01', b'hehe')))

            items = list(slab.scanByRangeBack(b'\x00\x03', b'\x00\x02', db=foo))
            self.eq(items, ((b'\x00\x02', b'haha'), ))

            items = list(slab.scanByRangeBack(b'\x01\x03', b'\x00\x02', db=foo))
            self.eq(items, ((b'\x01\x03', b'hoho'), (b'\x00\x02', b'haha')))

            items = list(slab.scanByRangeBack(b'\x01\x05', b'\x00\x02', db=foo))
            self.eq(items, ((b'\x01\x03', b'hoho'), (b'\x00\x02', b'haha')))

            items = list(slab.scanByDupsBack(b'\x00\x02', db=bar))
            self.eq(items, ((b'\x00\x02', b'zomg'), (b'\x00\x02', b'visi'), (b'\x00\x02', b'haha')))

            items = list(slab.scanByDupsBack(b'\x00\x04', db=bar))
            self.eq(items, ())

            items = list(slab.scanByFullBack(db=foo))
            self.eq(items, ((b'\x01\x03', b'hoho'), (b'\x00\x02', b'haha'), (b'\x00\x01', b'hehe')))

            with s_lmdbslab.ScanBack(slab, db=bar) as scan:
                scan.first()
                self.eq(scan.atitem, (b'\x00\x03', b'hoho'))

            with s_lmdbslab.ScanBack(slab, db=foo) as scan:
                scan.set_key(b'\x00\x02')
                self.eq(scan.atitem, (b'\x00\x02', b'haha'))

            # test scans on emptydb

            emptydb = slab.initdb('empty')

            items = list(slab.scanByPrefBack(b'\x00\x01', db=emptydb))
            self.eq(items, ())

            items = list(slab.scanByPrefBack(b'\xff\xff', db=emptydb))
            self.eq(items, ())

            items = list(slab.scanByRangeBack(b'\x00\x01', db=emptydb))
            self.eq(items, ())

            items = list(slab.scanByFullBack(db=emptydb))
            self.eq(items, ())

            # ok... lets start a scan and then rip out the xact...
            scan = slab.scanByPref(b'\x00', db=foo)
            self.eq((b'\x00\x01', b'hehe'), next(scan))

            slab.forcecommit()

            items = list(scan)
            self.eq(items, ((b'\x00\x02', b'haha'),))

            # to test iternext_dup, lets do the same with a dup scan
            scan = slab.scanByDups(b'\x00\x02', db=bar)
            self.eq((b'\x00\x02', b'haha'), next(scan))

            slab.forcecommit()

            items = list(scan)
            self.eq(items, ((b'\x00\x02', b'visi'), (b'\x00\x02', b'zomg')))

            # do the same with backwards scanning
            scan = slab.scanByRangeBack(b'\x01\x03', db=foo)
            self.eq((b'\x01\x03', b'hoho'), next(scan))

            slab.forcecommit()

            items = list(scan)
            self.eq(items, ((b'\x00\x02', b'haha'), (b'\x00\x01', b'hehe')))

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

            scanback = slab.scanByPrefBack(b'\x00', db=foo)
            self.eq((b'\x00\x02', b'haha'), next(scanback))

            await slab.fini()

            self.raises(s_exc.IsFini, next, scan)
            self.raises(s_exc.IsFini, next, scanback)

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

    async def test_lmdbslab_scanbump(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, growsize=10000) as slab:

                foo = slab.initdb('foo', dupsort=True)
                foo2 = slab.initdb('foo2', dupsort=False)

                multikey = b'\xff\xff\xff\xfe' + s_common.guid(2000).encode('utf8')

                byts = b'\x00' * 256
                for i in range(10):
                    slab.put(multikey, s_common.int64en(i), dupdata=True, db=foo)
                    slab.put(s_common.int64en(i), byts, db=foo2)

                iter = slab.scanByDups(multikey, db=foo)
                iter2 = slab.scanByFull(db=foo2)

                for _ in range(6):
                    next(iter)
                    next(iter2)

                iterback = slab.scanByDupsBack(multikey, db=foo)
                next(iterback)

                iterback2 = slab.scanByFullBack(db=foo2)
                next(iterback2)

                iterback3 = slab.scanByDupsBack(multikey, db=foo)
                iterback4 = slab.scanByFullBack(db=foo2)

                for _ in range(8):
                    next(iterback3)
                    next(iterback4)

                iterback5 = slab.scanByDupsBack(multikey, db=foo)
                next(iterback5)

                iterback6 = slab.scanByFullBack(db=foo2)
                next(iterback6)

                # Delete keys to cause set_range in iternext to fail
                for i in range(5):
                    slab.delete(multikey, s_common.int64en(i + 5), db=foo)
                    slab.delete(s_common.int64en(i + 5), db=foo2)

                slab.forcecommit()

                self.raises(StopIteration, next, iter)
                self.raises(StopIteration, next, iter2)
                self.eq(5, sum(1 for _ in iterback))
                self.eq(5, sum(1 for _ in iterback2))

                # Delete all the keys in front of a backwards scan
                for i in range(4):
                    slab.delete(multikey, s_common.int64en(i), db=foo)
                    slab.delete(s_common.int64en(i), db=foo2)

                self.raises(StopIteration, next, iterback3)
                self.raises(StopIteration, next, iterback4)

                # Delete remaining keys so curs.last fails
                slab.delete(multikey, s_common.int64en(4), db=foo)
                slab.delete(s_common.int64en(4), db=foo2)

                self.raises(StopIteration, next, iterback5)
                self.raises(StopIteration, next, iterback6)

    async def test_lmdbslab_scanbump2(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path, map_size=100000, growsize=10000) as slab:

                dupydb = slab.initdb('dup', dupsort=True)
                dupndb = slab.initdb('ndup', dupsort=False)

                for db in (dupndb, dupydb):
                    slab.put(b'1', b'', db=db)
                    slab.put(b'2', b'', db=db)
                    slab.put(b'3', b'', db=db)

                    # forwards, bump after 2nd entry
                    it = slab.scanByFull(db=db)
                    self.eq((b'1', b''), next(it))
                    self.eq((b'2', b''), next(it))
                    slab.forcecommit()
                    self.eq((b'3', b''), next(it))
                    self.raises(StopIteration, next, it)

                    # backwards, bump after 2nd entry
                    it = slab.scanByFullBack(db=db)
                    self.eq((b'3', b''), next(it))
                    self.eq((b'2', b''), next(it))
                    slab.forcecommit()
                    self.eq((b'1', b''), next(it))
                    self.raises(StopIteration, next, it)

                    # forwards, bump/delete after 2nd entry
                    it = slab.scanByFull(db=db)
                    self.eq((b'1', b''), next(it))
                    self.eq((b'2', b''), next(it))
                    slab.forcecommit()
                    slab.delete(b'2', db=db)
                    self.eq((b'3', b''), next(it))
                    self.raises(StopIteration, next, it)

                    it = slab.scanByFull(db=db)
                    self.eq((b'1', b''), next(it))
                    slab.forcecommit()
                    slab.delete(b'3', db=db)
                    self.raises(StopIteration, next, it)

                    slab.put(b'2', b'', db=db)
                    slab.put(b'3', b'', db=db)

                    # backwards, bump/delete after 2nd entry
                    it = slab.scanByFullBack(db=db)
                    self.eq((b'3', b''), next(it))
                    self.eq((b'2', b''), next(it))
                    slab.forcecommit()
                    slab.delete(b'2', db=db)
                    self.eq((b'1', b''), next(it))
                    self.raises(StopIteration, next, it)

                    it = slab.scanByFullBack(db=db)
                    slab.forcecommit()
                    slab.delete(b'3', db=db)
                    self.eq((b'1', b''), next(it))
                    self.raises(StopIteration, next, it)

                slab.delete(b'1', db=dupydb)
                slab.delete(b'2', db=dupydb)
                slab.delete(b'3', db=dupydb)
                slab.put(b'0', b'', db=dupydb)
                slab.put(b'1', b'1', db=dupydb)
                slab.put(b'1', b'2', db=dupydb)
                slab.put(b'1', b'3', db=dupydb)
                slab.put(b'2', b'', db=dupydb)

                # dupsort=yes, forwards, same keys, bump after 2nd entry
                it = slab.scanByFull(db=dupydb)
                self.eq((b'0', b''), next(it))
                self.eq((b'1', b'1'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                self.eq((b'1', b'3'), next(it))
                self.eq((b'2', b''), next(it))
                self.raises(StopIteration, next, it)

                # forwards, bump/delete after 2nd entry
                it = slab.scanByFull(db=dupydb)
                self.eq((b'0', b''), next(it))
                self.eq((b'1', b'1'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'2', db=dupydb)
                self.eq((b'1', b'3'), next(it))
                self.eq((b'2', b''), next(it))
                self.raises(StopIteration, next, it)

                it = slab.scanByFull(db=dupydb)
                self.eq((b'0', b''), next(it))
                self.eq((b'1', b'1'), next(it))
                self.eq((b'1', b'3'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'3', db=dupydb)
                self.eq((b'2', b''), next(it))
                self.raises(StopIteration, next, it)

                slab.put(b'1', b'2', db=dupydb)
                slab.put(b'1', b'3', db=dupydb)

                # dupsort=yes, backwards, same keys, bump after 2nd entry
                it = slab.scanByFullBack(db=dupydb)
                self.eq((b'2', b''), next(it))
                self.eq((b'1', b'3'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                self.eq((b'1', b'1'), next(it))
                self.eq((b'0', b''), next(it))
                self.raises(StopIteration, next, it)

                # dupsort=yes, backwards, same keys, bump/delete after 2nd entry
                it = slab.scanByFullBack(db=dupydb)
                self.eq((b'2', b''), next(it))
                self.eq((b'1', b'3'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'2', db=dupndb)
                self.eq((b'1', b'1'), next(it))
                self.eq((b'0', b''), next(it))
                self.raises(StopIteration, next, it)

                slab.put(b'1', b'2', db=dupydb)
                slab.put(b'1', b'3', db=dupydb)

                # single key, forwards, bump after 2nd entry
                it = slab.scanByDups(db=dupydb, lkey=b'1')
                self.eq((b'1', b'1'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                self.eq((b'1', b'3'), next(it))
                self.raises(StopIteration, next, it)

                # single key, forwards, bump/delete after 2nd entry
                it = slab.scanByDups(db=dupydb, lkey=b'1')
                self.eq((b'1', b'1'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'2', db=dupydb)
                self.eq((b'1', b'3'), next(it))
                self.raises(StopIteration, next, it)

                it = slab.scanByDups(db=dupydb, lkey=b'1')
                self.eq((b'1', b'1'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'3', db=dupydb)
                self.raises(StopIteration, next, it)

                slab.put(b'1', b'2', db=dupydb)
                slab.put(b'1', b'3', db=dupydb)

                # dupsort=yes, backwards, same keys, bump after 2nd entry
                it = slab.scanByDupsBack(db=dupydb, lkey=b'1')
                self.eq((b'1', b'3'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                self.eq((b'1', b'1'), next(it))
                self.raises(StopIteration, next, it)

                # dupsort=yes, backwards, same keys, bump/delete after 2nd entry
                it = slab.scanByDupsBack(db=dupydb, lkey=b'1')
                self.eq((b'1', b'3'), next(it))
                self.eq((b'1', b'2'), next(it))
                slab.forcecommit()
                slab.delete(b'1', val=b'2', db=dupndb)
                self.eq((b'1', b'1'), next(it))
                self.raises(StopIteration, next, it)

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

                count = 0
                for _, _ in slab.scanByRangeBack(b'ffffffffffffffffffffffffffffffff', db=foo):
                    count += 1
                self.eq(count, 100)

                # Trigger a grow/bump in the middle of a scan; make sure new nodes come after current scan position
                iter = slab.scanByRange(b'', db=foo)
                for _ in range(50):
                    next(iter)

                iterback = slab.scanByRangeBack(b'ffffffffffffffffffffffffffffffff', db=foo)
                for _ in range(50):
                    next(iterback)

                multikey = b'\xff\xff\xff\xfe' + s_common.guid(2000).encode('utf8')
                mapsize = slab.mapsize
                count = 0

                # Write until we grow
                while mapsize == slab.mapsize:
                    count += 1
                    rv = slab.put(multikey, s_common.guid(count + 100000).encode('utf8') + byts, dupdata=True, db=foo)
                    self.true(rv)

                self.eq(50 + count, sum(1 for _ in iter))
                self.eq(50, sum(1 for _ in iterback))

                self.true(os.path.isfile(slab.optspath))

                # Trigger a grow/bump in the middle of a dup scan
                iter = slab.scanByDups(multikey, db=foo)
                next(iter)

                iter2 = slab.scanByFull(db=foo2)
                next(iter2)

                iterback = slab.scanByDupsBack(multikey, db=foo)
                next(iterback)

                iterback2 = slab.scanByFullBack(db=foo2)
                next(iterback2)

                multikey = b'\xff\xff\xff\xff' + s_common.guid(i + 150000).encode('utf8')
                for i in range(200):
                    slab.put(multikey, s_common.guid(i + 200000).encode('utf8') + byts, dupdata=True, db=foo)

                self.eq(count - 1, sum(1 for _ in iter))
                self.eq(99, sum(1 for _ in iter2))

                self.eq(count - 1, sum(1 for _ in iterback))
                self.eq(99, sum(1 for _ in iterback2))

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

                ctx = multiprocessing.get_context('spawn')
                proc = ctx.Process(target=_writeproc, args=(path, ))
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
                for _ in range(60):
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
        self.thisHostMust(platform='linux')

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'slab.lmdb')
            async with await s_lmdbslab.Slab.anit(path, map_size=1024, lockmemory=True) as slab:
                self.true(await asyncio.wait_for(slab.lockdoneevent.wait(), 8))
                mapcount = getFileMapCount('slab.lmdb/data.mdb')
                self.eq(1, mapcount)

                mapsize = slab.mapsize
                [slab.initdb(str(i)) for i in range(10)]
                self.gt(slab.mapsize, mapsize)

                # Make sure there is still only one map
                self.true(await asyncio.wait_for(slab.lockdoneevent.wait(), 8))

                mapcount = getFileMapCount('slab.lmdb/data.mdb')
                self.eq(1, mapcount)

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
            async with await s_lmdbslab.Slab.anit(path, map_size=32000, growsize=5000, lockmemory=True) as slab:
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
        with patch('synapse.lib.lmdbslab.Slab.DEFAULT_MAPSIZE', s_const.mebibyte), \
                patch('synapse.lib.lmdbslab.Slab.DEFAULT_GROWSIZE', 128 * s_const.kibibyte):
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

    async def test_lmdb_multiqueue(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path) as slab:

                mque = await slab.getMultiQueue('test')

                self.false(mque.exists('woot'))

                with self.raises(s_exc.NoSuchName):
                    await mque.rem('woot')

                with self.raises(s_exc.NoSuchName):
                    await mque.get('woot', 0)

                with self.raises(s_exc.NoSuchName):
                    await mque.put('woot', 'lulz')

                with self.raises(s_exc.NoSuchName):
                    mque.status('woot')

                with self.raises(s_exc.NoSuchName):
                    await mque.cull('woot', -1)

                await mque.add('woot', {'some': 'info'})
                await self.asyncraises(s_exc.DupName, mque.add('woot', {}))

                self.true(mque.exists('woot'))

                self.eq(0, await mque.put('woot', 'hehe'))
                self.eq(1, await mque.put('woot', 'haha'))
                self.eq(2, await mque.put('woot', 'hoho'))

                self.eq(3, mque.size('woot'))

                self.eq(3, await mque.put('woot', 'lol', reqid='foo'))
                self.eq(4, await mque.put('woot', 'lol', reqid='foo'))
                self.eq(4, await mque.put('woot', 'lol', reqid='foo'))

                self.eq(4, await mque.puts('woot', ('lol2', 'lol3'), reqid='foo2'))
                self.eq(6, await mque.puts('woot', ('lol2', 'lol3'), reqid='foo2'))
                self.eq(6, await mque.puts('woot', ('lol2', 'lol3'), reqid='foo2'))

                self.eq((0, 'hehe'), await mque.get('woot', 0))
                self.eq((1, 'haha'), await mque.get('woot', 1))
                self.eq((1, 'haha'), await mque.get('woot', 0))

                self.eq((-1, None), await mque.get('woot', 1000, cull=False))

                self.eq(5, mque.size('woot'))

                status = mque.list()
                self.len(1, status)
                self.eq(status[0], {'name': 'woot',
                                    'meta': {'some': 'info'},
                                    'size': 5,
                                    'offs': 6,
                                    })

                await mque.cull('woot', -1)
                self.eq(mque.status('woot'), status[0])

            async with await s_lmdbslab.Slab.anit(path) as slab:

                mque = await slab.getMultiQueue('test')

                self.eq(5, mque.size('woot'))
                self.eq(6, mque.offset('woot'))

                self.eq(((1, 'haha'), ), [x async for x in mque.gets('woot', 0, size=1)])

                correct = ((1, 'haha'), (2, 'hoho'), (3, 'lol'), (4, 'lol2'), (5, 'lol3'))
                self.eq(correct, [x async for x in mque.gets('woot', 0)])

                data = []
                evnt = asyncio.Event()

                async def getswait():
                    async for item in mque.gets('woot', 0, wait=True):

                        if item[1] is None:
                            break

                        data.append(item)

                        if item[1] == 'hoho':
                            evnt.set()

                task = slab.schedCoro(getswait())

                await asyncio.wait_for(evnt.wait(), 5)

                self.eq(data, correct)

                await mque.put('woot', 'lulz')
                await mque.put('woot', None)

                await asyncio.wait_for(task, 2)

                self.eq(data, (*correct, (6, 'lulz')))

                self.true(mque.exists('woot'))

                self.eq((2, 'hoho'), await mque.get('woot', 2))

                await mque.put('woot', 'huhu')

                await mque.rem('woot')

                self.false(mque.exists('woot'))

    async def test_slababrv(self):
        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path) as slab:
                abrv = s_lmdbslab.SlabAbrv(slab, 'test')

                valu = abrv.setBytsToAbrv('hehe'.encode())
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x00')
                valu = abrv.setBytsToAbrv('haha'.encode())
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x01')

                name = abrv.abrvToByts(b'\x00\x00\x00\x00\x00\x00\x00\x01')
                self.eq(name, b'haha')

                self.raises(s_exc.NoSuchAbrv, abrv.abrvToByts, b'\x00\x00\x00\x00\x00\x00\x00\x02')

            # And persistence
            async with await s_lmdbslab.Slab.anit(path) as slab:
                abrv = s_lmdbslab.SlabAbrv(slab, 'test')
                # recall first
                name = abrv.abrvToByts(b'\x00\x00\x00\x00\x00\x00\x00\x00')
                self.eq(name, b'hehe')

                name = abrv.abrvToByts(b'\x00\x00\x00\x00\x00\x00\x00\x01')
                self.eq(name, b'haha')
                # Remaking them makes the values we already had
                valu = abrv.nameToAbrv('hehe')
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x00')

                valu = abrv.nameToAbrv('haha')
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x01')

                self.eq('haha', abrv.abrvToName(b'\x00\x00\x00\x00\x00\x00\x00\x01'))

                # And we still have no valu for 02
                self.raises(s_exc.NoSuchAbrv, abrv.abrvToByts, b'\x00\x00\x00\x00\x00\x00\x00\x02')

                # And we don't overwrite existing values on restart
                valu = abrv.setBytsToAbrv('hoho'.encode())
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x02')

                valu = abrv.nameToAbrv('haha')
                self.eq(valu, b'\x00\x00\x00\x00\x00\x00\x00\x01')

    async def test_lmdbslab_hotkeyval(self):
        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path, map_size=1000000) as slab, \
                    await s_lmdbslab.HotKeyVal.anit(slab, 'counts') as ctr:
                self.eq(None, ctr.get('foo'))
                self.eq({}, ctr.pack())
                ctr.set('foo', 1)
                ctr.set('bar', {'val': 42})
                self.eq({'foo': 1, 'bar': {'val': 42}}, ctr.pack())

            async with await s_lmdbslab.Slab.anit(path, map_size=1000000) as slab, \
                    await s_lmdbslab.HotKeyVal.anit(slab, 'counts') as ctr:
                self.eq({'foo': 1, 'bar': {'val': 42}}, ctr.pack())
                self.eq({'val': 42}, ctr.get('bar'))

    async def test_lmdbslab_hotcount(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            async with await s_lmdbslab.Slab.anit(path, map_size=1000000, lockmemory=True) as slab, \
                    await s_lmdbslab.HotCount.anit(slab, 'counts') as ctr:
                self.eq(0, ctr.get('foo'))
                self.eq({}, ctr.pack())
                ctr.inc('foo')
                self.eq({'foo': 1}, ctr.pack())
                self.eq(1, ctr.get('foo'))
                ctr.set('bar', 42)
                self.eq({'foo': 1, 'bar': 42}, ctr.pack())
                ctr.sync()
                self.eq({'foo': 1, 'bar': 42}, ctr.pack())

                ctr.inc('foo')
                ctr.inc('foo')
                ctr.set('bar', 37)
                ctr.sync()

                cache = []
                for lkey, lval in slab.scanByFull(db='counts'):
                    cache.append((lkey, s_common.int64un(lval)))

                self.len(1, [k for k, v in cache if k == b'foo'])
                self.len(1, [k for k, v in cache if k == b'bar'])

    async def test_lmdbslab_doubleopen(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                foo = slab.initdb('foo')
                slab.put(b'\x00\x01', b'hehe', db=foo)

            # Can close and re-open fine
            async with await s_lmdbslab.Slab.anit(path) as slab:
                foo = slab.initdb('foo')
                self.eq(b'hehe', slab.get(b'\x00\x01', db=foo))

                # Can't re-open while already open
                await self.asyncraises(s_exc.SlabAlreadyOpen, s_lmdbslab.Slab.anit(path))

class LmdbSlabMemLockTest(s_t_utils.SynTest):

    async def test_lmdbslabmemlock(self):
        self.thisHostMust(hasmemlocking=True)

        beforelockmem = s_thisplat.getCurrentLockedMemory()

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            async with await s_lmdbslab.Slab.anit(path, map_size=1000000, lockmemory=True) as lmdbslab:

                self.true(await asyncio.wait_for(lmdbslab.lockdoneevent.wait(), 8))
                lockmem = s_thisplat.getCurrentLockedMemory()
                self.ge(lockmem - beforelockmem, 4000)

    async def test_multiple_grow(self):
        '''
        Trigger multiple grow events rapidly and ensure memlock thread survives.
        '''
        self.thisHostMust(hasmemlocking=True)

        with self.getTestDir() as dirn:

            count = 0
            byts = b'\x00' * 1024
            path = os.path.join(dirn, 'test.lmdb')
            mapsize = 10 * 1024 * 1024
            async with await s_lmdbslab.Slab.anit(path, map_size=mapsize, growsize=5000, lockmemory=True) as slab:
                foo = slab.initdb('foo')
                while count < 8000:
                    count += 1
                    slab.put(s_common.guid(count).encode('utf8'), s_common.guid(count).encode('utf8') + byts, db=foo)

                self.true(await asyncio.wait_for(slab.lockdoneevent.wait(), 8))

                lockmem = s_thisplat.getCurrentLockedMemory()

                # TODO: make this test reliable
                self.ge(lockmem, 0)

def _writeproc(path):

    async def lotsofwrites(path):
        byts = b'\x00' * 256
        os.remove(pathlib.Path(path).with_suffix('.opts.yaml'))
        async with await s_lmdbslab.Slab.anit(path, map_size=100000) as slab:
            foo = slab.initdb('foo', dupsort=True)
            mapsize = slab.mapsize
            count = 0
            while mapsize == slab.mapsize:
                count += 1
                slab.put(b'abcd', s_common.guid(count).encode('utf8') + byts, dupdata=True, db=foo)
    asyncio.run(lotsofwrites(path))
