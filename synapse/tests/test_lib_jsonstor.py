import synapse.exc as s_exc
import synapse.lib.jsonstor as s_jsonstor

import synapse.tests.utils as s_test

class JsonStorTest(s_test.SynTest):

    async def test_lib_jsonstor_popprop(self):

        async with self.getTestJsonStor() as jsonstor:
            async with jsonstor.getLocalProxy() as prox:
                await prox.setPathObj('foo/bar', {'foo': 'bar', 'baz': 'faz'})
                self.eq('faz', await prox.popPathObjProp('foo/bar', 'baz'))
                self.none(await prox.getPathObjProp('foo/bar', 'baz'))

                self.none(await prox.popPathObjProp('foo/bar', 'baz'))
                self.none(await prox.popPathObjProp('newp/newp', 'baz'))

                # coverage for the loop'd get
                await prox.setPathObj('hehe', {'foo': {'bar': 'baz'}})
                self.eq('baz', await prox.popPathObjProp('hehe', 'foo/bar'))
                self.none(await prox.popPathObjProp('hehe', 'foo/newp'))

    async def test_lib_jsonstor_has(self):

        async with self.getTestJsonStor() as jsonstor:
            async with jsonstor.getLocalProxy() as prox:
                await prox.setPathObj('foo/bar', 'asdf')
                self.true(await prox.hasPathObj('foo/bar'))

    async def test_lib_jsonstor_copy(self):

        async with self.getTestJsonStor() as jsonstor:
            async with jsonstor.getLocalProxy() as prox:
                await prox.setPathObj('foo/bar', 'asdf')
                await prox.copyPathObj('foo/bar', 'foo/baz')
                self.eq('asdf', await prox.getPathObj('foo/baz'))

                await prox.copyPathObjs((('foo/bar', 'foo/faz'),))
                self.eq('asdf', await prox.getPathObj('foo/faz'))

    async def test_lib_jsonstor_basics(self):

        with self.getTestDir() as dirn:
            async with self.getTestJsonStor(dirn=dirn) as jsonstor:
                async with jsonstor.getLocalProxy() as prox:

                    await prox.setPathObj('foo/bar', {'hehe': 'haha', 'mooz': 'zoom'})
                    self.eq({'hehe': 'haha', 'mooz': 'zoom'}, await prox.getPathObj('foo/bar'))

                    self.false(await prox.cmpDelPathObjProp('foo/bar', 'mooz', 'hehe'))
                    self.true(await prox.cmpDelPathObjProp('foo/bar', 'mooz', 'zoom'))

                    self.eq({'hehe': 'haha'}, await prox.getPathObj('foo/bar'))

                    self.true(await prox.setPathObjProp('foo/bar', 'zip', {'zop': True}))
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/bar'))
                    self.true(await prox.getPathObjProp('foo/bar', 'zip/zop'))

                    await prox.setPathObjProp('foo/bar', 'nested/nested2', 'a bird')
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}, 'nested': {'nested2': 'a bird'}}, await prox.getPathObj('foo/bar'))
                    await prox.delPathObjProp('foo/bar', 'nested')

                    await prox.setPathLink('foo/baz', 'foo/bar')
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/baz'))

                    items = list([x async for x in prox.getPathObjs('foo')])

                    self.len(2, items)
                    self.eq(items[0][0][0], 'bar')
                    self.eq(items[1][0][0], 'baz')
                    self.eq(items[0][1]['hehe'], 'haha')
                    self.eq(items[1][1]['hehe'], 'haha')

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

                    self.none(await prox.getPathObjProp('newp/newp', 'newp'))
                    self.false(await prox.setPathObjProp('newp/newp', 'newp', 'newp'))

            async with self.getTestJsonStor(dirn=dirn) as jsonstor:
                async with jsonstor.getLocalProxy() as prox:
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/bar'))
                    self.eq({'hehe': 'haha', 'zip': {'zop': True}}, await prox.getPathObj('foo/baz'))

                    await prox.setPathObjProp('foo/baz', 'zip/zop', False)
                    self.eq({'hehe': 'haha', 'zip': {'zop': False}}, await prox.getPathObj('foo/baz'))

                    self.eq(('bar', 'baz'), [x async for x in prox.getPathList('foo')])

                    self.true(await prox.delPathObjProp('foo/bar', 'zip/zop'))
                    self.eq({'hehe': 'haha', 'zip': {}}, await prox.getPathObj('foo/bar'))

                    self.false(await prox.delPathObjProp('newp/newp', 'newp'))

                    await prox.delPathObj('foo/bar')
                    self.none(await prox.getPathObj('foo/bar'))
                    await prox.delPathObj('foo/baz')
                    self.none(await prox.getPathObj('foo/bar'))

                    self.true(await prox.delQueue('hehe'))
                    self.false(await prox.delQueue('hehe'))
