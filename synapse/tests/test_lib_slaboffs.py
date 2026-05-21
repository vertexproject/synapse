import os
import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slaboffs as s_slaboffs

import synapse.tests.utils as s_t_utils

class SlabOffsTest(s_t_utils.SynTest):

    async def test_lmdbslab_base(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:

                offsdb = slab.initdb('offsets')
                offs = s_slaboffs.SlabOffs(slab, offsdb)

                guid = s_common.guid()
                self.eq(0, offs.get(guid))

                offs.set(guid, 42)
                self.eq(42, offs.get(guid))

                offs.delete(guid)
                self.eq(0, offs.get(guid))
