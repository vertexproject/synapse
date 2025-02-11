import shutil
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class MultiSlabSeqn(s_t_utils.SynTest):

    async def test_multislabseqn_base(self):

        with self.getTestDir() as dirn:

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                s_multislabseqn.logger.debug(f'Repr test {msqn}')

                self.eq(0, msqn.index())

                retn = await alist(msqn.iter(0))
                self.eq([], retn)

                retn = await msqn.last()
                self.eq(None, retn)

                retn = await msqn.rotate()
                self.eq(0, retn)

                self.false(await msqn.cull(0))

                retn = await msqn.add('foo')
                self.eq(0, retn)

                retn = await msqn.add('foo2')
                self.eq(1, retn)

                retn = await alist(msqn.iter(0))
                self.eq([(0, 'foo'), (1, 'foo2')], retn)

                retn = await alist(msqn.iter(1))
                self.eq([(1, 'foo2')], retn)

                retn = await msqn.add('foo9', indx=9)
                self.eq(9, retn)

                retn = await alist(msqn.iter(0))
                self.eq([(0, 'foo'), (1, 'foo2'), (9, 'foo9')], retn)

                evnt1 = msqn.getOffsetEvent(9)
                self.true(evnt1.is_set())
                self.true(await msqn.waitForOffset(9, timeout=0.5))

                evnt1 = msqn.getOffsetEvent(10)
                self.false(await msqn.waitForOffset(10, timeout=0.1))

                retn = await msqn.add('foo10')
                self.eq(10, retn)

                retn = await alist(msqn.iter(0))
                self.eq([(0, 'foo'), (1, 'foo2'), (9, 'foo9'), (10, 'foo10')], retn)

                retn = await msqn.last()
                self.eq((10, 'foo10'), retn)

                retn = msqn.index()
                self.eq(11, retn)

                self.eq(4, msqn.tailseqn.size)
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(1, fns)

                # cause a rotation
                self.eq(11, await msqn.rotate())
                self.eq(11, msqn.index())
                self.eq((10, 'foo10'), await msqn.last())

                retn = await alist(msqn.iter(0))
                self.eq([(0, 'foo'), (1, 'foo2'), (9, 'foo9'), (10, 'foo10')], retn)

                self.len(0, [x for x in msqn.tailseqn.iter(0)])

                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(2, fns)

                # Need one entry so can't cull at >= 10
                self.false(await msqn.cull(10))
                self.false(await msqn.cull(11))

                self.true(await msqn.cull(9))
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(2, fns)

                retn = await alist(msqn.iter(0))
                self.eq([(10, 'foo10')], retn)

                # Once we write into tailseqn we can actually remove the rotated seqn
                await msqn.add('foo11')
                retn = await alist(msqn.iter(0))
                self.eq([(10, 'foo10'), (11, 'foo11')], retn)

                self.true(await msqn.cull(10))
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(1, fns)

                retn = await alist(msqn.iter(0))
                self.eq([(11, 'foo11')], retn)
                self.eq((11, 'foo11'), await msqn.last())

                # Add some values and rotate for persistence check
                await msqn.add('foo12')
                await msqn.rotate()
                await msqn.add('foo13')
                await msqn.add('foo14')

                exp = [(11, 'foo11'), (12, 'foo12'), (13, 'foo13'), (14, 'foo14')]
                self.eq(exp, await alist(msqn.iter(0)))

            # Persistence check

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                self.eq(exp, await alist(msqn.iter(0)))

                self.eq((14, 'foo14'), await msqn.last())

                self.eq('foo11', await msqn.get(11))
                self.eq('foo12', await msqn.get(12))
                self.eq('foo13', await msqn.get(13))
                self.eq('foo14', await msqn.get(14))

                retn = await alist(msqn.gets(9, wait=False))
                self.eq(exp, retn)

                evnt = asyncio.Event()

                async def getter():
                    retn = []
                    async for item in msqn.gets(9):
                        evnt.set()
                        if item[1] == 'done':
                            return retn
                        retn.append(item)
                    return retn

                task = msqn.schedCoro(getter())
                await s_coro.event_wait(evnt, timeout=1)
                await msqn.add('done')

                retn = await asyncio.wait_for(task, timeout=1)
                self.eq(exp, retn)

                # Add entries not on the tail
                retn = await msqn.add('foo11b', indx=11)
                self.eq(11, retn)

                retn = await msqn.add('foo13b', indx=13)
                self.eq(13, retn)

                await self.asyncraises(s_exc.BadIndxValu, msqn.add('foo7', indx=7))

                retn = await alist(msqn.iter(1))
                exp = [(11, 'foo11b'), (12, 'foo12'), (13, 'foo13b'), (14, 'foo14'), (15, 'done')]
                self.eq(exp, retn)

                # Make sure we're not holding onto more than 2 slabs

                # rotate
                await msqn.add('foo16')
                await msqn.rotate()
                await msqn.add('foo17')
                await msqn.add('foo18')

                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(3, fns)

                # Slab @ 13 will get fini out
                _slab = msqn._openslabs[13][0]
                self.true(await _slab.waitfini(6))

                self.len(2, msqn._openslabs)

                retn = await msqn.get(11)  # first
                self.eq('foo11b', retn)

                self.len(2, msqn._openslabs)

                retn = await msqn.get(14)  # middle
                self.eq('foo14', retn)

                self.len(2, msqn._openslabs)

                retn = await msqn.get(17)  # tail
                self.eq('foo17', retn)

                self.len(2, msqn._openslabs)

                # Make sure we don't open the same slab twice

                # Keep a ref to the first slab
                it = msqn.iter(0)
                retn = await it.__anext__()
                self.eq(retn, (11, 'foo11b'))

                self.len(2, msqn._openslabs)

                # (Need to evict first slab ref from the cacheslab)
                self.true(msqn._cacheslab.path.endswith('b.lmdb'))
                retn = await msqn.get(14)
                self.eq(retn, 'foo14')
                self.true(msqn._cacheslab.path.endswith('d.lmdb'))

                # Should have the tail slab, the cache slab, and the open iterator slabs
                self.len(3, msqn._openslabs)

                retn = await msqn.get(12)
                self.eq(retn, 'foo12')

                retn = await alist(it)
                self.len(7, retn)

                # Iterator exhausted: should have just the cache slab (10) and the tail slab (20)
                self.len(2, msqn._openslabs)

    async def test_multislabseqn_cull(self):

        with self.getTestDir() as dirn:

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:

                for i in range(10):
                    await msqn.add(f'foo{i}')

                # cull with only one seqn
                self.true(await msqn.cull(2))
                await self.asyncraises(s_exc.BadIndxValu, msqn.get(2))

                await msqn.rotate()

                for i in range(10, 15):
                    await msqn.add(f'foo{i}')

                # A no-op
                self.false(await msqn.cull(99))

                # Ensure there's a cached slab
                retn = await msqn.get(4)
                self.eq('foo4', retn)

                self.true(await msqn.cull(4))
                await self.asyncraises(s_exc.BadIndxValu, msqn.get(4))
                await self.asyncraises(s_exc.BadIndxValu, msqn.add('foo12', indx=4))

                retn = await msqn.get(5)
                self.eq('foo5', retn)

                it = msqn.iter(0)
                retn = await it.__anext__()
                await self.asyncraises(s_exc.SlabInUse, msqn.cull(6))
                await it.aclose()

                # culling on the tail just moves firstindx forward
                it = msqn.iter(10)
                retn = await it.__anext__()
                await msqn.cull(11)
                self.eq(12, msqn.firstindx)
                await it.aclose()

                retn = await alist(msqn.iter(1))
                self.eq([(12, 'foo12'), (13, 'foo13'), (14, 'foo14')], retn)

                await self.asyncraises(s_exc.BadIndxValu, msqn.get(11))
                await self.asyncraises(s_exc.BadIndxValu, msqn.add('foo', indx=11))

                # Make sure it deleted a slab
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(1, fns)

                # Make sure ranges are updated
                self.eq([10], msqn._ranges)

                # Can't cull before firstidx
                self.false(await msqn.cull(10))

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                await msqn.cull(13)
                retn = await alist(msqn.iter(1))
                self.eq([(14, 'foo14')], retn)

    async def test_multislabseqn_discover(self):
        '''
        Test all the horrible things that admins can do by deleting/moving slabs
        '''

        # Speed up copying dirs
        slabopts = {'map_size': 100000}

        with self.getTestDir() as dirn:

            origdirn = s_common.gendir(dirn, 'orig')

            async with await s_multislabseqn.MultiSlabSeqn.anit(origdirn, slabopts=slabopts) as msqn:
                for i in range(25):
                    if i > 0 and i % 10 == 0:
                        await msqn.rotate()
                    await msqn.add(f'foo{i}')

            baddirn = s_common.genpath(dirn, 'bad1')
            shutil.copytree(origdirn, baddirn)

            # Make a slab a non-dir
            slab0dirn = s_common.genpath(baddirn, f'seqn{"0" * 16}.lmdb')
            shutil.rmtree(slab0dirn)
            s_json.jssave('{}', slab0dirn)

            with self.getAsyncLoggerStream('synapse.lib.multislabseqn', 'non-directory') as stream:
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    await self.agenlen(15, msqn.iter(0))
                await stream.wait(timeout=1)

            # Switcheroo

            baddirn = s_common.genpath(dirn, 'bad2')
            shutil.copytree(origdirn, baddirn)

            slab0dirn = s_common.genpath(baddirn, f'seqn{"0" * 16}.lmdb')
            slab10dirn = s_common.genpath(baddirn, f'seqn{"0" * 14}0a.lmdb')
            tmpdirn = s_common.genpath(baddirn, 'tmp')
            shutil.move(slab10dirn, tmpdirn)
            shutil.move(slab0dirn, slab10dirn)
            shutil.move(tmpdirn, slab0dirn)

            with self.raises(s_exc.BadCoreStore):
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    pass

            # Delete out from the middle
            baddirn = s_common.genpath(dirn, 'bad3')
            shutil.copytree(origdirn, baddirn)

            slab10dirn = s_common.genpath(baddirn, f'seqn{"0" * 14}0a.lmdb')
            shutil.rmtree(slab10dirn)

            with self.getAsyncLoggerStream('synapse.lib.multislabseqn', 'gap in indices') as stream:
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    await self.agenlen(15, msqn.iter(0))
                await stream.wait(timeout=1)

            # Wipe a seqn clean
            baddirn = s_common.genpath(dirn, 'bad4')
            shutil.copytree(origdirn, baddirn)

            slab20dirn = s_common.genpath(baddirn, f'seqn{"0" * 14}14.lmdb')
            async with await s_lmdbslab.Slab.anit(slab20dirn) as slab:
                seqn = slab.getSeqn('nexuslog')
                await seqn.cull(25)

            async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                await self.agenlen(20, msqn.iter(0))

            # Overlapping seqns
            baddirn = s_common.genpath(dirn, 'bad5')
            shutil.copytree(origdirn, baddirn)

            slab10dirn = s_common.genpath(baddirn, f'seqn{"0" * 14}0a.lmdb')
            async with await s_lmdbslab.Slab.anit(slab10dirn) as slab:
                seqn = slab.getSeqn('nexuslog')
                seqn.add('foo', indx=22)

            with self.raises(s_exc.BadCoreStore):
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    pass

            # Somebody really messing with us
            baddirn = s_common.genpath(dirn, 'bad6')
            shutil.copytree(origdirn, baddirn)

            slab20dirn = s_common.genpath(baddirn, f'seqn{"0" * 14}14.lmdb')
            async with await s_lmdbslab.Slab.anit(slab20dirn) as slab:
                db = slab.initdb('info')
                slab.put(b'firstindx', s_common.int64en(99), db=db)

            with self.raises(s_exc.BadCoreStore):
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    pass

    async def test_multislabseqn_iterrotate(self):

        with self.getTestDir() as dirn:

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:

                for i in range(9):
                    await msqn.add(f'foo{i}')

                it = msqn.iter(0)
                retn = await it.__anext__()
                self.eq((0, 'foo0'), retn)

                # rotate
                await msqn.add('foo9')
                await msqn.rotate()
                await msqn.add('foo10')
                await msqn.add('foo11')

                self.len(2, msqn._openslabs)

                # can still iterate on the seqn
                retn = await it.__anext__()
                self.eq((1, 'foo1'), retn)

                # iterator will pick up the new seqn
                retn = await alist(it)
                self.len(10, retn)
                self.eq([(2, 'foo2'), (11, 'foo11')], [retn[0], retn[-1]])
                await it.aclose()

                # and we can cull once done
                await msqn.cull(10)
                self.len(1, msqn._openslabs)

                self.eq(12, msqn.tailseqn.indx)

    async def test_multislabseqn_multicache(self):
        '''
        A new consumer can iterate over an older non-cacheslab while the cacheslab is in use
        '''

        with self.getTestDir() as dirn:

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:

                for i in range(15):
                    if i > 0 and i % 4 == 0:
                        await msqn.rotate()
                    await msqn.add(f'foo{i}')

                self.len(4, msqn._ranges)
                self.none(msqn._cacheslab)
                self.len(1, msqn._openslabs)

                it00 = msqn.iter(5)
                retn = await it00.__anext__()
                self.eq((5, 'foo5'), retn)

                self.nn(msqn._cacheslab)
                self.true(msqn._cacheslab.path.endswith('4.lmdb'))
                self.len(2, msqn._openslabs)

                it01 = msqn.iter(0)
                retn = await it01.__anext__()
                self.eq((0, 'foo0'), retn)

                self.true(msqn._cacheslab.path.endswith('0.lmdb'))
                self.len(3, msqn._openslabs)

                retn = await it00.__anext__()
                self.eq((6, 'foo6'), retn)

                retn = await it01.__anext__()
                self.eq((1, 'foo1'), retn)

                await it00.aclose()
                await it01.aclose()

                self.true(msqn._cacheslab.path.endswith('0.lmdb'))
                self.len(2, msqn._openslabs)

                # cache slab remains open, but can be culled
                await msqn.cull(13)
                self.none(msqn._cacheslab)
                self.len(1, msqn._openslabs)

    async def test_multislabseqn_last(self):

        with self.getTestDir() as dirn:

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:

                self.none(await msqn.last())

                for i in range(5):
                    await msqn.add(f'foo{i}')

                self.eq((4, 'foo4'), await msqn.last())

                # rotate so we have an empty tail slab
                await msqn.rotate()
                self.eq(0, msqn.tailseqn.size)

                self.eq((4, 'foo4'), await msqn.last())

                # create a hole in the index
                await msqn.add('foo6', indx=6)
                self.eq((6, 'foo6'), await msqn.last())
