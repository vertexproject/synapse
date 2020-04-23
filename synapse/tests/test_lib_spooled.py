import os

import synapse.tests.utils as s_test

import synapse.lib.spooled as s_spooled

class SpooledTest(s_test.SynTest):

    async def test_spooled_set(self):
        async with await s_spooled.Set.anit(size=2) as sset:
            self.len(0, sset)

            await sset.add(10)
            self.true(10 in sset)
            self.len(1, sset)
            sset.discard(10)
            self.false(10 in sset)

            self.len(0, sset)
            self.false(sset.fallback)

            await sset.add(10)

            # Trigger fallback
            await sset.add(20)
            await sset.add(30)
            await sset.add(None)

            self.len(4, sset)

            self.nn(sset.slab)
            self.nn(sset.slabpath)
            self.true(sset.fallback)

            self.true(10 in sset)
            sset.discard(10)
            self.false(10 in sset)
            self.len(3, sset)

            sset.discard(10)
            self.len(3, sset)

            self.true(None in sset)

            self.true(os.path.isdir(sset.slabpath))

        self.false(os.path.isdir(sset.slabpath))

    async def test_spooled_set_dir(self):
        with self.getTestDir() as dirn:
            async with await s_spooled.Set.anit(dirn=dirn, size=2) as sset:
                await sset.add(10)
                await sset.add(20)
                await sset.add(30)
                self.true(os.path.isdir(sset.slabpath))
                self.true(os.path.abspath(sset.slabpath).startswith(dirn))
