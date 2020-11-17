import synapse.exc as s_exc
import synapse.lib.jsonstor as s_jsonstor

import synapse.tests.utils as s_test

class SynTest(s_test.SynTest):

    async def test_lib_jsonstor_basics(self):
        with self.getTestDir() as dirn:
            async with await s_jsonstor.JsonStorCell.anit(dirn) as jsonstor:
                async with jsonstor.getLocalProxy() as prox:

                    await prox.setPathObj('foo/bar', {'hehe': 'haha'})
                    self.eq({'hehe': 'haha'}, await prox.getPathObj('foo/bar'))

                    self.true(await prox.setPathObjProp('foo/bar', 'zip', {'zop': True}))
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/bar'))
                    self.true(await prox.getPathObjProp('foo/bar', 'zip/zop'))

                    await prox.setPathLink('foo/baz', 'foo/bar')
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/baz'))

                    with self.raises(s_exc.PathExists):
                        await prox.setPathLink('foo/baz', 'foo/bar')

                    with self.raises(s_exc.NoSuchPath):
                        await prox.setPathLink('lol/lol', 'hehe/haha')

                    self.true(await prox.addQueue('hehe', {}))
                    self.false(await prox.addQueue('hehe', {}))

                    self.eq(0, await prox.putsQueue('hehe', ('haha', 'hoho')))

                    retn = []
                    async for item in prox.getsQueue('hehe', 0, wait=False):
                        retn.append(item)
                    self.eq(retn, ((0, 'haha'), (1, 'hoho')))

                    await prox.cullQueue('hehe', 0)

                    retn = []
                    async for item in prox.getsQueue('hehe', 1, cull=True, wait=False):
                        retn.append(item)
                    self.eq(retn, ((1, 'hoho'),))

                    retn = []
                    async for item in prox.getsQueue('hehe', 2, cull=True, wait=False):
                        retn.append(item)
                    self.eq(retn, ())

            async with await s_jsonstor.JsonStorCell.anit(dirn) as jsonstor:
                async with jsonstor.getLocalProxy() as prox:
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/bar'))
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/baz'))

                self.eq(('bar', 'baz'), [x async for x in prox.getPathList('foo')])
