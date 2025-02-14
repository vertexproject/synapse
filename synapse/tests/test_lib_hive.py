import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

tree0 = {
    'kids': {
        'hehe': {'value': 'haha'},
        'hoho': {'value': 'huhu', 'kids': {
            'foo': {'value': 99},
        }},
    }
}

tree1 = {
    'kids': {
        'hoho': {'value': 'huhu', 'kids': {
            'foo': {'value': 99},
        }}
    }
}

class HiveTest(s_test.SynTest):

    async def test_hive_slab(self):

        with self.getTestDir() as dirn:

            async with self.getTestHiveFromDirn(dirn) as hive:

                path = ('foo', 'bar')

                async with await hive.dict(path) as hivedict:

                    self.none(await hivedict.set('hehe', 200))
                    self.none(await hivedict.set('haha', 'hoho'))

                    valus = list(hivedict.values())
                    self.len(2, valus)
                    self.eq(set(valus), {200, 'hoho'})

                    self.eq(200, hivedict.get('hehe'))

                    self.eq(200, await hivedict.set('hehe', 300))

                    self.eq(300, hivedict.get('hehe'))

                    self.eq(300, await hive.get(('foo', 'bar', 'hehe')))
                    self.eq(300, await hive.set(('foo', 'bar', 'hehe'), 400))

                    hivedict.setdefault('lulz', 31337)

                    self.eq(31337, hivedict.get('lulz'))
                    await hivedict.set('lulz', 'boo')
                    items = list(hivedict.items())
                    self.eq([('hehe', 400), ('haha', 'hoho'), ('lulz', 'boo')], items)
                    self.eq('boo', await hivedict.pop('lulz'))
                    self.eq(31337, await hivedict.pop('lulz'))

                    self.eq(None, hivedict.get('nope'))

                    self.eq(s_common.novalu, hivedict.get('nope', default=s_common.novalu))
                    self.eq(s_common.novalu, await hivedict.pop('nope', default=s_common.novalu))

            async with self.getTestHiveFromDirn(dirn) as hive:

                self.eq(400, await hive.get(('foo', 'bar', 'hehe')))
                self.eq('hoho', await hive.get(('foo', 'bar', 'haha')))

                self.none(await hive.get(('foo', 'bar', 'lulz')))

    async def test_hive_dir(self):

        async with self.getTestHive() as hive:

            await hive.open(('foo', 'bar'))
            await hive.open(('foo', 'baz'))
            await hive.open(('foo', 'faz'))

            self.none(hive.dir(('nosuchdir',)))

            self.eq([('foo', None, 3)], list(hive.dir(())))

            await hive.open(('foo',))

            kids = list(hive.dir(('foo',)))

            self.len(3, kids)

            names = list(sorted([name for (name, node, size) in kids]))

            self.eq(names, ('bar', 'baz', 'faz'))

    async def test_hive_pop(self):

        async with self.getTestHive() as hive:

            node = await hive.open(('foo', 'bar'))

            await node.set(20)

            self.none(await hive.pop(('newp',)))

            self.eq(20, await hive.pop(('foo', 'bar')))

            self.none(await hive.get(('foo', 'bar')))

            # Test recursive delete
            node = await hive.open(('foo', 'bar'))
            await node.set(20)

            self.eq(None, await hive.pop(('foo',)))
            self.none(await hive.get(('foo', 'bar')))

    async def test_hive_saveload(self):

        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            self.eq('haha', await hive.get(('hehe',)))
            self.eq('huhu', await hive.get(('hoho',)))
            self.eq(99, await hive.get(('hoho', 'foo')))

            await hive.loadHiveTree(tree1, trim=True)
            self.none(await hive.get(('hehe',)))
            self.eq('huhu', await hive.get(('hoho',)))
            self.eq(99, await hive.get(('hoho', 'foo')))

        async with self.getTestHive() as hive:

            node = await hive.open(('hehe', 'haha'))
            await node.set(99)

            tree = await hive.saveHiveTree()

            self.nn(tree['kids']['hehe'])
            self.nn(tree['kids']['hehe']['kids']['haha'])

            self.eq(99, tree['kids']['hehe']['kids']['haha']['value'])

    async def test_hive_exists(self):
        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            self.true(await hive.exists(('hoho', 'foo')))
            self.false(await hive.exists(('hoho', 'food')))
            self.false(await hive.exists(('newp',)))

    async def test_hive_rename(self):
        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('hehe',), ('hoho',)))
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('newp',), ('newp2',)))
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('hehe',), ('hehe', 'foo')))

            await hive.rename(('hehe',), ('lolo',))
            self.eq('haha', await hive.get(('lolo',)))
            self.false(await hive.exists(('hehe',)))

            await hive.rename(('hoho',), ('jojo',))
            self.false(await hive.exists(('hoho',)))
            jojo = await hive.open(('jojo',))
            self.len(1, jojo.kids)
            self.eq('huhu', jojo.valu)
            self.eq(99, await hive.get(('jojo', 'foo')))
