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

            self.eq((10,), [x async for x in sset])

            await sset.add(10)
            self.len(1, sset)
            self.true(sset.has(10))

            sset.discard(10)
            self.false(10 in sset)

            self.len(0, sset)
            self.false(sset.fallback)

            await sset.add(10)

            newset = await sset.copy()
            self.len(1, newset)
            self.true(10 in newset)
            self.false(newset.fallback)

            # Trigger fallback
            await sset.add(20)
            await sset.add(30)
            await sset.add(None)

            newset = await sset.copy()
            self.true(10 in newset)
            self.true(20 in newset)
            self.true(30 in newset)
            self.true(None in newset)
            self.len(4, newset)

            await newset.clear()
            self.false(10 in newset)
            self.false(20 in newset)
            self.false(30 in newset)
            self.false(None in newset)
            self.len(0, newset)

            self.true(os.path.isdir(newset.slab.path))
            await newset.fini()
            self.false(os.path.isdir(newset.slab.path))

            self.len(4, sset)

            await sset.add(20)
            self.len(4, sset)

            self.nn(sset.slab)
            self.true(sset.fallback)

            self.true(sset.has(10))
            self.eq((10, 20, 30, None), [x async for x in sset])

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

                newset = await sset.copy()
                self.true(os.path.isdir(newset.slab.path))
                self.true(os.path.abspath(newset.slab.path).startswith(dirn))

            # Slabs should get removed on fini
            self.false(os.path.isdir(sset.slab.path))

            self.true(os.path.isdir(newset.slab.path))
            await newset.fini()
            self.false(os.path.isdir(newset.slab.path))

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
            self.eq('haha', x.pop(20))
            self.len(2, x)
            self.eq(None, x.pop(20))
            self.len(2, x)

        async with await s_spooled.Dict.anit(size=2) as sd0:
            await runtest(sd0)
            self.true(sd0.fallback)

        async with await s_spooled.Dict.anit(size=1000) as sd1:
            await runtest(sd1)
            self.false(sd1.fallback)
