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
