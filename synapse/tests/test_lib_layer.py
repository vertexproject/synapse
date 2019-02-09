import contextlib
import synapse.tests.utils as s_t_utils


async def iterPropForm(self, form=None, prop=None):
    bad_valu = [('foo', "bar"), ('bar', ('bar',)), ('biz', 4965), ('baz', (0, 56))]
    bad_valu += [('boz', 'boz')] * 10
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

                node = await snap.addNode('teststr', 'a', {'tick': '1970'})
                node = await snap.addNode('teststr', 'b', {'tick': '19700101'})
                node = await snap.addNode('teststr', 'c', {'tick': '1972'})
                oper = ('teststr', 'tick', (0, 24 * 60 * 60 * 366))

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
