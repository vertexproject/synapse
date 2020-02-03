import asyncio

import synapse.tests.utils as s_test

class LmdbLayerTest(s_test.SynTest):

    async def test_lib_lmdblayer_abrv(self):
        async with self.getTestCore() as core:
            layr = core.view.layers[0]
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.getNameAbrv('visi'))
            # another to check the cache...
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.getNameAbrv('visi'))
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x01', layr.getNameAbrv('whip'))
            self.eq('visi', layr.getAbrvName(b'\x00\x00\x00\x00\x00\x00\x00\x00'))
            self.eq('whip', layr.getAbrvName(b'\x00\x00\x00\x00\x00\x00\x00\x01'))

    async def test_lib_lmdblayer_stat(self):
        self.thisHostMust(hasmemlocking=True)

        conf = {'dedicated': True}
        async with self.getTestCore(conf=conf) as core:
            slab = core.getLayer().layrslab
            self.true(await asyncio.wait_for(slab.lockdoneevent.wait(), 8))

            nstat = await core.stat()
            layr = nstat.get('layer')

            self.true(layr.get('locking_memory'))
            self.eq(layr.get('lock_goal'), layr.get('lock_progress'))
            self.gt(layr.get('lock_goal'), 0)
