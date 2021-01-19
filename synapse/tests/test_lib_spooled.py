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

            await sset.add(10)
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

            await sset.add(20)
            self.len(4, sset)

            self.nn(sset.slab)
            self.true(sset.fallback)

            self.true(10 in sset)
            sset.discard(10)
            self.false(10 in sset)
            self.len(3, sset)

            sset.discard(10)
            self.len(3, sset)

            self.true(None in sset)

            self.true(os.path.isdir(sset.slab.path))

        self.false(os.path.isdir(sset.slab.path))
        self.false(os.path.isfile(sset.slab.optspath))

    async def test_spooled_set_dir(self):
        with self.getTestDir() as dirn:
            async with await s_spooled.Set.anit(dirn=dirn, size=2) as sset:
                await sset.add(10)
                await sset.add(20)
                await sset.add(30)
                self.true(os.path.isdir(sset.slab.path))
                self.true(os.path.abspath(sset.slab.path).startswith(dirn))

    async def test_spooled_dict(self):

        async def runtest(x):
            await x.set(10, 'hehe')
            self.eq(x.get(10), 'hehe')
            self.eq(x.get(20, 'newp'), 'newp')
            await x.set(20, 'haha')
            await x.set(30, 'hoho')
            self.eq(x.get(20), 'haha')
            self.eq(x.get(40, 'newp'), 'newp')
            self.len(3, x)
            self.eq('hehe', x.get(10))
            self.eq(list(x.items()), ((10, 'hehe'), (20, 'haha'), (30, 'hoho')))
            self.eq(list(x.keys()), (10, 20, 30))
            self.true(x.has(20))
            self.false(x.has(99))

        async with await s_spooled.Dict.anit(size=2) as sd0:
            await runtest(sd0)

        async with await s_spooled.Dict.anit(size=1000) as sd1:
            await runtest(sd1)
