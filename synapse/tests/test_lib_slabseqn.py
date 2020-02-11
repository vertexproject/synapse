import os
import asyncio

import synapse.lib.coro as s_coro
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

import synapse.tests.utils as s_t_utils

class SlabSeqn(s_t_utils.SynTest):

    async def test_slab_seqn(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            slab = await s_lmdbslab.Slab.anit(path, map_size=1000000)

            seqn = s_slabseqn.SlabSeqn(slab, 'seqn:test')

            self.eq(seqn.nextindx(), 0)
            items = ('foo', 10, 20)
            seqn.save(items)
            retn = tuple(seqn.iter(0))
            self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

            self.raises(TypeError, seqn.save, ({'set'},))
            retn = tuple(seqn.iter(0))
            self.eq(retn, ((0, 'foo'), (1, 10), (2, 20)))

            self.eq(seqn.nextindx(), 3)

            await slab.fini()

            # Reopen the seqn and continue where we left off
            slab = await s_lmdbslab.Slab.anit(path, map_size=1000000)

            seqn = s_slabseqn.SlabSeqn(slab, 'seqn:test')
            self.eq(seqn.index(), 3)

            self.eq(seqn.nextindx(), 3)
            seqn.save(items)

            retn = tuple(seqn.iter(0))
            self.eq(retn, ((0, 'foo'), (1, 10), (2, 20),
                           (3, 'foo'), (4, 10), (5, 20)))
            self.eq(seqn.nextindx(), 6)

            # We can also start in the middle of the sequence
            retn = tuple(seqn.iter(4))
            self.eq(retn, ((4, 10), (5, 20)))

            # iterating past the end yields nothing
            retn = tuple(seqn.iter(100))
            self.eq(retn, ())

            evnt = seqn.getOffsetEvent(4)
            self.true(evnt.is_set())

            evnt1 = seqn.getOffsetEvent(8)
            evnt2 = seqn.getOffsetEvent(9)
            evnt3 = seqn.getOffsetEvent(8)

            seqn.save(items)
            retn = tuple(seqn.iter(0))
            self.len(9, retn)

            self.eq('foo', seqn.getByIndxByts(b'\x00' * 8))

            self.true(evnt1.is_set())
            self.true(await seqn.waitForOffset(8, timeout=0.5))
            self.false(evnt2.is_set())
            self.false(await seqn.waitForOffset(9, timeout=0.1))
            self.true(evnt3.is_set())

            state = None

            started = asyncio.Event()

            async def taskloop():
                nonlocal state
                state = 'started'
                started.set()
                state = await seqn.waitForOffset(9, timeout=5)

            task = asyncio.get_running_loop().create_task(taskloop())
            self.true(await s_coro.event_wait(started, 2))
            self.eq(state, 'started')

            seqn.add('bar')
            self.true(evnt2.is_set())

            self.true(state)
            await task

            await slab.fini()
