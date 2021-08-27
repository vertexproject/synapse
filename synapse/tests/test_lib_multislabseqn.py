import asyncio
import shutil

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class MultiSlabSeqn(s_t_utils.SynTest):

    async def test_multislabseqn(self):

        with self.getTestDir() as dirn, self.setTstEnvars(SYN_MULTISLAB_MAX_INDEX='10'):

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                self.eq(0, msqn.index())

                retn = await alist(msqn.iter(0))
                self.eq([], retn)

                retn = msqn.last()
                self.eq(None, retn)

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

                retn = msqn.last()
                self.eq((10, 'foo10'), retn)

                retn = msqn.index()
                self.eq(11, retn)

                # Make sure it added a new slab
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(2, fns)

            # Persistence check

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                retn = await alist(msqn.iter(0))
                self.eq([(0, 'foo'), (1, 'foo2'), (9, 'foo9'), (10, 'foo10')], retn)

                retn = await alist(msqn.iter(0))

                retn = await msqn.get(9)
                self.eq('foo9', retn)

                retn = await alist(msqn.gets(9, wait=False))
                self.eq([(9, 'foo9'), (10, 'foo10')], retn)

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
                self.eq([(9, 'foo9'), (10, 'foo10')], retn)

                # Add entries not on the tail
                retn = await msqn.add('foo10b', indx=10)
                self.eq(10, retn)

                retn = await msqn.add('foo7', indx=7)
                self.eq(7, retn)

                retn = await alist(msqn.iter(1))
                self.eq([(1, 'foo2'), (7, 'foo7'), (9, 'foo9'), (10, 'foo10b'), (11, 'done')], retn)

                # Give a chance for the non-iterated async generators to get cleaned up
                await asyncio.sleep(0)
                await asyncio.sleep(0)

                # Make sure we're not holding onto more than 2 slabs

                await msqn.add('foo20', indx=20)

                self.len(2, msqn._openslabs)

                retn = await msqn.get(0)
                self.eq('foo', retn)

                self.len(2, msqn._openslabs)

                retn = await msqn.get(10)
                self.eq('foo10b', retn)

                self.len(2, msqn._openslabs)

                # Make sure we don't open the same slab twice

                # Keep a ref to the 0 slab
                it = msqn.iter(0)
                retn = await it.__anext__()
                self.eq(retn, (0, 'foo'))

                self.len(2, msqn._openslabs)

                # (Need to evict 0 slab ref from the cacheslab)
                retn = await msqn.get(10)
                self.eq(retn, 'foo10b')

                # Should have the tail slab (20), the cache slab (10), and the open iterator (0) slabs
                self.len(3, msqn._openslabs)

                retn = await msqn.get(1)
                self.eq(retn, 'foo2')

                retn = await alist(it)
                self.len(6, retn)

                # Iterator exhausted: should have just the cache slab (10) and the tail slab (20)
                self.len(2, msqn._openslabs)

    async def test_multislabseqn_cull(self):

        with self.getTestDir() as dirn, self.setTstEnvars(SYN_MULTISLAB_MAX_INDEX='10'):

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                for i in range(18):
                    await msqn.add(f'foo{i}')

                # A no-op
                await msqn.cull(99)

                # Ensure there's a cached slab
                retn = await msqn.get(4)
                self.eq('foo4', retn)

                await msqn.cull(4)
                await self.asyncraises(s_exc.BadLiftValu, msqn.get(4))

                retn = await msqn.get(5)
                self.eq('foo5', retn)

                it = msqn.iter(0)
                retn = await it.__anext__()
                await self.asyncraises(s_exc.SlabInUse, msqn.cull(14))
                await it.aclose()

                await msqn.cull(14)

                retn = await alist(msqn.iter(1))
                self.eq([(15, 'foo15'), (16, 'foo16'), (17, 'foo17')], retn)

                await self.asyncraises(s_exc.BadLiftValu, msqn.get(10))
                await self.asyncraises(s_exc.BadLiftValu, msqn.add('foo', indx=10))

                # Make sure it deleted a slab
                fns = sorted(s_common.listdir(dirn, glob='*.lmdb'))
                self.len(1, fns)

            async with await s_multislabseqn.MultiSlabSeqn.anit(dirn) as msqn:
                await msqn.cull(10)
                retn = await alist(msqn.iter(1))
                self.eq([(15, 'foo15'), (16, 'foo16'), (17, 'foo17')], retn)

    async def test_multislabseqn_discover(self):
        '''
        Test all the horrible things that admins can do by deleting/moving slabs
        '''

        # Speed up copying dirs
        slabopts = {'map_size': 100000}

        with self.getTestDir() as dirn, self.setTstEnvars(SYN_MULTISLAB_MAX_INDEX='10'):

            origdirn = s_common.gendir(dirn, 'orig')

            async with await s_multislabseqn.MultiSlabSeqn.anit(origdirn, slabopts=slabopts) as msqn:
                for i in range(25):
                    await msqn.add(f'foo{i}')

            baddirn = s_common.genpath(dirn, 'bad1')
            shutil.copytree(origdirn, baddirn)

            # Make a slab a non-dir
            slab0dirn = s_common.genpath(baddirn, f'seqn{"0" * 16}.lmdb')
            shutil.rmtree(slab0dirn)
            s_common.jssave('{}', slab0dirn)

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

            with self.getAsyncLoggerStream('synapse.lib.multislabseqn', 'found empty seqn') as stream:
                async with await s_multislabseqn.MultiSlabSeqn.anit(baddirn) as msqn:
                    await self.agenlen(20, msqn.iter(0))
                await stream.wait(timeout=1)

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
