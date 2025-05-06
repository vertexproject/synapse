import os
import asyncio

import synapse.lib.lmdbslab as s_lmdbslab
import synapse.tools.axon2to3 as s_t_axon

import synapse.tests.utils as s_test

class Axon2to3Test(s_test.SynTest):

    async def test_axon_migration_ms_to_us(self):

        ticks = [1710000000000, 1710000001000, 1710000002000]
        items = ['foo', 'bar', 'baz']

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'axon.lmdb')
            async with await s_lmdbslab.Slab.anit(path) as slab:
                hist = s_lmdbslab.Hist(slab, 'history')

                for tick, item in zip(ticks, items):
                    hist.add(item, tick=tick)

            await s_t_axon.migrate_history(dirn)

            async with await s_lmdbslab.Slab.anit(path) as slab:
                hist = s_lmdbslab.Hist(slab, 'history')
                rows = list(hist.carve(0))
                self.len(3, rows)
                for (tick, item), orig_tick, orig_item in zip(rows, ticks, items):
                    self.eq(item, orig_item)
                    self.true(tick % 1000 == 0)
                    self.eq(tick, orig_tick * 1000)

    async def test_axon_migrate_args(self):
        outp = self.getTestOutp()
        ret = await s_t_axon.main([], outp=outp)
        self.eq(ret, 0)
        outp.expect('arguments are required:')

        outp = self.getTestOutp()
        ret = await s_t_axon.main(['--help'], outp=outp)
        self.eq(ret, 0)
        outp.expect('usage: synapse.tools.axon2to3')

    async def test_axon_migrate_tool(self):

        with self.getTestDir() as dirn:
            async with self.getTestAxon(dirn) as axon:
                await axon.put(b'visi')
                await axon.put(b'vertex')

            outp = self.getTestOutp()
            await s_t_axon.main([dirn], outp=outp)
            outp.expect('Migrated 2 history rows in total.')

    async def test_axon_migrate_tool_already_migrated(self):

        with self.getTestDir() as dirn:
            async with self.getTestAxon(dirn) as axon:
                await axon.put(b'visi')
                await axon.put(b'vertex')

            outp = self.getTestOutp()
            await s_t_axon.main([dirn], outp=outp)
            outp.expect('Migrated 2 history rows in total.')

            outp = self.getTestOutp()
            await s_t_axon.main([dirn], outp=outp)
            outp.expect('Migration already done.')

    async def test_axon_migrate_tool_open_axon(self):

        async with self.getTestAxon() as axon:
            await axon.put(b'visi')
            await axon.put(b'vertex')

            outp = self.getTestOutp()
            await s_t_axon.main([axon.dirn], outp=outp)
            outp.expect('ERROR: The Axon appears to be running.')
