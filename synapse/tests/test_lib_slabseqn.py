import os

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

            seqn.save(items)
            retn = tuple(seqn.iter(0))
            self.len(9, retn)

            await slab.fini()
