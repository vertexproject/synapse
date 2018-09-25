from unittest.mock import patch

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cryotank as s_cryotank

import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

logger = s_cryotank.logger

cryodata = (('foo', {'bar': 10}), ('baz', {'faz': 20}))

class CryoTest(s_t_utils.SynTest):

    async def test_cryo_cell_async(self):
        async with self.getTestDmon(mirror='cryodmon') as dmon, \
                await self.agetTestProxy(dmon, 'cryo00') as prox:
            self.true(await prox.init('foo'))
            self.eq([], [x async for x in await prox.rows('foo', 0, 1)])

    @s_glob.synchelp
    @patch('synapse.lib.lmdb.DEFAULT_MAP_SIZE', s_t_utils.TEST_MAP_SIZE)
    async def test_cryo_cell(self):

        async with self.getTestDmon(mirror='cryodmon') as dmon:

            async with await self.agetTestProxy(dmon, 'cryo00') as prox:

                self.eq((), await prox.list())

                self.true(await prox.init('foo'))

                self.eq('foo', (await prox.list())[0][0])

                self.none(await prox.last('foo'))

                self.eq([], await alist(await prox.rows('foo', 0, 1)))

                self.true(await prox.puts('foo', cryodata))

                info = await prox.list()
                self.eq('foo', info[0][0])
                self.eq(2, info[0][1].get('stat').get('entries'))

                self.true(await prox.puts('foo', cryodata))

                items = await alist(await prox.slice('foo', 1, 3))
                self.eq(items[0][1][0], 'baz')

                metrics = await alist(await prox.metrics('foo', 0, 9999))
                self.len(2, metrics)
                self.eq(2, metrics[0][1]['count'])

                self.eq(3, (await prox.last('foo'))[0])
                self.eq('baz', (await prox.last('foo'))[1][0])

                iden = s_common.guid()
                self.eq(0, await prox.offset('foo', iden))

                items = await alist(await prox.slice('foo', 0, 1000, iden=iden))
                self.eq(0, await prox.offset('foo', iden))

                items = await alist(await prox.slice('foo', 4, 1000, iden=iden))
                self.eq(4, await prox.offset('foo', iden))

            # test the direct tank share....
            async with await self.agetTestProxy(dmon, 'cryo00/foo') as prox:

                items = await alist(await prox.slice(1, 3))

                self.eq(items[0][1][0], 'baz')

                self.len(4, await alist(await prox.slice(0, 9999)))

                await prox.puts(cryodata)

                self.len(6, await alist(await prox.slice(0, 9999)))

                # test offset storage and updating
                iden = s_common.guid()
                self.eq(0, await prox.offset(iden))
                self.eq(2, await prox.puts(cryodata, seqn=(iden, 0)))
                self.eq(2, await prox.offset(iden))

            # test the new open share
            async with await self.agetTestProxy(dmon, 'cryo00/lulz') as prox:

                self.len(0, await alist(await prox.slice(0, 9999)))

                await prox.puts(cryodata)

                self.len(2, await alist(await prox.slice(0, 9999)))

                self.len(1, await alist(await prox.metrics(0)))

    async def test_cryo_cell_indexing(self):

        # conf = {'defvals': {'mapsize': s_t_utils.TEST_MAP_SIZE}}
        async with self.getTestDmon(mirror='cryodmon') as dmon, \
                await self.agetTestProxy(dmon, 'cryo00') as ccell, \
                await self.agetTestProxy(dmon, 'cryo00/woot:woot') as tank:
            # Setting the _chunksize to 1 forces iteration on the client
            # side of puts, as well as the server-side.
            tank._chunksize = 1
            await tank.puts(cryodata)

            # Test index operations
            self.eq((), await tank.getIndices())
            await self.asyncraises(s_exc.BadOperArg, tank.addIndex('prop1', 'str', []))
            await tank.addIndex('prop1', 'str', ['0'])
            await tank.delIndex('prop1')
            await self.asyncraises(s_exc.NoSuchIndx, tank.delIndex('noexist'))
            await tank.addIndex('prop1', 'str', ['0'])
            await tank.pauseIndex('prop1')
            await tank.pauseIndex()
            await tank.resumeIndex()
            self.eq([(1, 'baz'), (0, 'foo')], await alist(await tank.queryNormValu('prop1')))
            self.eq([(1, 'baz')], await alist(await tank.queryNormValu('prop1', valu='b')))
            self.eq([], await alist(await tank.queryNormValu('prop1', valu='bz')))
            self.eq([(1, {'prop1': 'baz'})], (await alist(await tank.queryNormRecords('prop1', valu='b'))))
            self.eq([(1, s_msgpack.en(('baz', {'faz': 20})))],
                    await alist(await tank.queryRows('prop1', valu='b')))

            ccell.init('woot:boring', {'noindex': True})
            async with await self.agetTestProxy(dmon, 'cryo00/woot:boring') as tank2:
                self.eq([], await tank2.getIndices())

class CryoIndexTest(s_t_utils.SynTest):

    def initWaiter(self, tank, operation):
        return tank.waiter(1, 'cryotank:indexer:noworkleft:' + operation)

    async def wait(self, waiter):
        rv = await waiter.wait(s_cryotank.CryoTankIndexer.MAX_WAIT_S)
        self.nn(rv)

    async def test_cryotank_index(self):
        conf = {'mapsize': s_t_utils.TEST_MAP_SIZE}
        async with s_t_utils.SyncToAsyncCMgr(self.getTestConfDir, name='CryoTank', conf=conf) as dirn, \
                await s_cryotank.CryoTank.anit(dirn) as tank:

            idxr = tank.indexer

            data1 = {'foo': 1234, 'bar': 'stringval'}
            data2 = {'foo': 2345, 'baz': 4567, 'bar': 'strinstrin'}
            data3 = {'foo': 388383, 'bar': ('strinstrin' * 20)}
            data4 = {'foo2': 9999, 'baz': 4567}
            baddata = {'foo': 'bad'}

            # Simple index add/remove
            self.eq([], idxr.getIndices())
            idxr.addIndex('first', 'int', ['foo'])
            self.raises(s_exc.DupIndx, idxr.addIndex, 'first', 'int', ['foo'])
            idxs = idxr.getIndices()
            self.eq(idxs[0]['propname'], 'first')
            idxr.delIndex('first')
            self.raises(s_exc.NoSuchIndx, idxr.delIndex, 'first')
            self.eq([], idxr.getIndices())

            self.genraises(s_exc.NoSuchIndx, idxr.queryNormValu, 'notanindex')

            # Check simple 1 record, 1 index index and retrieval
            waiter = self.initWaiter(tank, 'addIndex')
            tank.puts([data1])
            idxr.addIndex('first', 'int', ['foo'])
            await self.wait(waiter)
            waiter = self.initWaiter(tank, 'getIndices')
            idxs = idxr.getIndices()
            await self.wait(waiter)
            self.eq(1, idxs[0]['nextoffset'])
            self.eq(1, idxs[0]['ngood'])
            retn = list(idxr.queryNormRecords('first'))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 0)
            self.eq(t[1], {'first': 1234})

            waiter = self.initWaiter(tank, 'None')
            tank.puts([data2])
            await self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(2, idxs[0]['nextoffset'])
            self.eq(2, idxs[0]['ngood'])

            # exact query
            retn = list(idxr.queryRows('first', valu=2345, exact=True))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 1)
            self.eq(s_msgpack.un(t[1]), data2)

            # second index
            waiter = self.initWaiter(tank, 'addIndex')
            idxr.addIndex('second', 'str', ['bar'])
            await self.wait(waiter)

            # prefix search
            retn = list(idxr.queryNormValu('second', valu='strin'))
            self.eq(retn, [(0, 'stringval'), (1, 'strinstrin')])

            # long value, exact
            waiter = self.initWaiter(tank, 'None')
            tank.puts([data3])
            await self.wait(waiter)
            retn = list(idxr.queryRows('second', valu='strinstrin' * 20, exact=True))
            self.eq(1, len(retn))
            self.eq(s_msgpack.un(retn[0][1]), data3)

            # long value with prefix
            retn = list(idxr.queryRows('second', valu='str'))
            self.eq(3, len(retn))

            # long value with long prefix
            self.genraises(s_exc.BadOperArg, idxr.queryNormRecords, 'second', valu='strinstrin' * 15)

            # Bad data
            waiter = self.initWaiter(tank, 'None')
            tank.puts([baddata])
            await self.wait(waiter)
            idxs = idxr.getIndices()
            idx = next(i for i in idxs if i['propname'] == 'first')
            self.eq(4, idx['nextoffset'])
            self.eq(3, idx['ngood'])
            self.eq(1, idx['nnormfail'])

            waiter = self.initWaiter(tank, 'delIndex')
            idxr.delIndex('second')
            await self.wait(waiter)

            # Multiple datapaths
            waiter = self.initWaiter(tank, 'delIndex')
            idxr.delIndex('first')
            await self.wait(waiter)
            waiter = self.initWaiter(tank, 'addIndex')
            idxr.addIndex('first', 'int', ('foo', 'foo2'))
            await self.wait(waiter)

            waiter = self.initWaiter(tank, 'None')
            tank.puts([data4])
            await self.wait(waiter)
            retn = list(idxr.queryNormValu('first'))
            self.eq(retn, [(0, 1234), (1, 2345), (4, 9999), (2, 388383)])

            waiter = self.initWaiter(tank, 'pauseIndex')
            idxr.pauseIndex('first')
            await self.wait(waiter)

            waiter = self.initWaiter(tank, 'resumeIndex')
            idxr.resumeIndex('first')
            await self.wait(waiter)

            waiter = self.initWaiter(tank, 'getIndices')
            before_idxs = idxr.getIndices()
            before_idx = next(i for i in before_idxs if i['propname'] == 'first')
            await self.wait(waiter)
            waiter = self.initWaiter(tank, 'None')
            tank.puts([data1, data2, data3, data4] * 1000)
            await self.wait(waiter)
            after_idxs = idxr.getIndices()
            after_idx = next(i for i in after_idxs if i['propname'] == 'first')
            self.lt(before_idx['ngood'], after_idx['ngood'])

    async def test_cryotank_index_nest(self):
        conf = {'mapsize': s_t_utils.TEST_MAP_SIZE}
        with self.getTestConfDir(name='CryoTank', conf=conf) as dirn:
            async with await s_cryotank.CryoTank.anit(dirn) as tank:
                idxr = tank.indexer
                item = {
                    'hehe': {
                        'haha': {
                            'key': 'valu'
                        }
                    }
                }
                waiter = self.initWaiter(tank, 'addIndex')
                idxr.addIndex('key', 'str', ['hehe/haha/key'])
                await self.wait(waiter)
                waiter = self.initWaiter(tank, 'None')
                tank.puts([item])
                await self.wait(waiter)
                idxs = idxr.getIndices()
                self.eq(idxs[0]['ngood'], 1)
