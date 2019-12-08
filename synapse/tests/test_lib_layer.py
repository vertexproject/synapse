import contextlib
from unittest.mock import patch

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist


async def iterPropForm(self, form=None, prop=None):
    bad_valu = [(b'foo', "bar"), (b'bar', ('bar',)), (b'biz', 4965), (b'baz', (0, 56))]
    bad_valu += [(b'boz', 'boz')] * 10
    for buid, valu in bad_valu:
        yield buid, valu


@contextlib.contextmanager
def patch_snap(snap):
    old_layr = []
    for layr in snap.layers:
        old_layr.append((layr.iterPropRows, layr.iterUnivRows, layr.iterFormRows))
        layr.iterPropRows, layr.iterUnivRows, layr.iterFormRows = (iterPropForm,) * 3

    yield

    for layr_idx, layr in enumerate(snap.layers):
        layr.iterPropRows, layr.iterUnivRows, layr.iterFormRows = old_layr[layr_idx]


class LayerTest(s_t_utils.SynTest):

    async def test_ival_failure(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('test:str', 'a', {'tick': '1970'})
                await snap.addNode('test:str', 'b', {'tick': '19700101'})
                await snap.addNode('test:str', 'c', {'tick': '1972'})
                oper = ('test:str', 'tick', (0, 24 * 60 * 60 * 366))

                async def liftByHandler(lopf, expt):
                    count = 0
                    lops = ((lopf, oper),)
                    async for node in snap.getLiftRows(lops):
                        count += 1
                    self.assertTrue(count == expt)

                with patch_snap(snap):
                    await liftByHandler('prop:ival', 1)
                    await liftByHandler('univ:ival', 1)
                    await liftByHandler('form:ival', 1)

    async def test_layer_buidcache(self):
        '''
        Make sure the layer buidcache isn't caching incorrectly
        '''

        async with self.getTestCore() as core:
            buidcache = core.view.layers[0].buidcache

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'tick': '2001'})
                await node.addTag('foo')
                testbuid = node.buid

            self.isin(testbuid, buidcache)
            propbag = buidcache.get(testbuid)
            self.eq(propbag.get('*test:str'), 'a')
            self.eq(propbag.get('tick'), 978307200000)
            self.eq(propbag.get('#foo'), (None, None))
            self.isin('.created', propbag)

            async with await core.snap() as snap:
                nodes = await alist(snap.getNodesBy('test:str'))
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.props['tick'], 978307200000)
                await node.set('tick', '2002')

            self.eq(buidcache.get(testbuid).get('tick'), 1009843200000)

            # new snap -> no cached buids in snap
            async with await core.snap() as snap:
                nodes = await alist(snap.getNodesBy('test:str'))
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.props['tick'], 1009843200000,)
                self.eq(node.tags, {'foo': (None, None)})
                await node.delete()

            self.notin(testbuid, buidcache)

            async with await core.snap() as snap:
                nodes = await alist(snap.getNodesBy('test:str'))
                self.len(0, nodes)

            self.notin(testbuid, buidcache)

    async def test_splicemigration_pre010(self):
        async with self.getRegrCore('pre-010') as core:
            splices1 = await s_t_utils.alist(core.view.layers[0].splices(0, 1000))
            self.gt(len(splices1), 100)
            self.false(core.view.layers[0].layrslab.dbexists('splices'))

        def baddrop(self, name):
            raise s_exc.DbOutOfSpace()

        with self.getRegrDir('cortexes', 'pre-010') as dirn:
            # Simulate a crash during recovery
            with self.raises(s_exc.DbOutOfSpace):
                with patch('synapse.lib.lmdbslab.Slab.dropdb', baddrop):
                    async with await s_cortex.Cortex.anit(dirn) as core:
                        pass

            # Make sure when it comes back we're not stuck
            with patch('synapse.lib.lmdbslab.PROGRESS_PERIOD', 50), patch('synapse.lib.lmdbslab.COPY_CHUNKSIZE', 50):
                with self.getLoggerStream('synapse.lib.lmdblayer') as stream:
                    async with await s_cortex.Cortex.anit(dirn) as core:
                        splices2 = await s_t_utils.alist(core.view.layers[0].splices(0, 1000))
                        self.false(core.view.layers[0].layrslab.dbexists('splices'))

                    self.eq(splices1, splices2)

                    stream.seek(0)
                    mesgs = stream.read()
                    self.isin('Incomplete migration', mesgs)

            with self.getLoggerStream('synapse.lib.lmdblayer') as stream:
                # Make sure the third time around we didn't migrate and we still have our splices
                async with await s_cortex.Cortex.anit(dirn) as core:
                    splices3 = await s_t_utils.alist(core.view.layers[0].splices(0, 1000))

                self.eq(splices1, splices3)

                # Test for no hint of migration happening
                stream.seek(0)
                mesgs = stream.read()
                self.notin('migration', mesgs)
