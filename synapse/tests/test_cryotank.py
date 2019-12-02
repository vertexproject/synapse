import synapse.common as s_common
import synapse.cryotank as s_cryotank

import synapse.lib.const as s_const

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

logger = s_cryotank.logger

cryodata = (('foo', {'bar': 10}), ('baz', {'faz': 20}))

class CryoTest(s_t_utils.SynTest):

    async def test_cryo_cell_async(self):
        async with self.getTestCryo() as cryo:
            async with cryo.getLocalProxy() as prox:
                self.true(await prox.init('foo'))
                self.eq([], await alist(prox.rows('foo', 0, 1)))

    async def test_cryo_cell(self):
        with self.getTestDir() as dirn:
            async with self.getTestCryoAndProxy(dirn=dirn) as (cryo, prox):

                self.eq((), await prox.list())

                self.true(await prox.init('foo'))

                self.eq('foo', (await prox.list())[0][0])

                self.none(await prox.last('foo'))

                self.eq([], await alist(prox.rows('foo', 0, 1)))

                self.true(await prox.puts('foo', cryodata))

                info = await prox.list()
                self.eq('foo', info[0][0])
                self.eq(2, info[0][1].get('stat').get('entries'))

                self.true(await prox.puts('foo', cryodata))

                items = await alist(prox.slice('foo', 1, 3))
                self.eq(items[0][1][0], 'baz')

                metrics = await alist(prox.metrics('foo', 0, 9999))
                self.len(2, metrics)
                self.eq(2, metrics[0][1]['count'])

                self.eq(3, (await prox.last('foo'))[0])
                self.eq('baz', (await prox.last('foo'))[1][0])

                iden = s_common.guid()
                self.eq(0, await prox.offset('foo', iden))

                items = await alist(prox.slice('foo', 0, 1000, iden=iden))
                self.eq(0, await prox.offset('foo', iden))

                items = await alist(prox.slice('foo', 4, 1000, iden=iden))
                self.eq(4, await prox.offset('foo', iden))

                # test the direct tank share....
                async with cryo.getLocalProxy(share='cryotank/foo') as lprox:

                    items = await alist(lprox.slice(1, 3))

                    self.eq(items[0][1][0], 'baz')

                    self.len(4, await alist(lprox.slice(0, 9999)))

                    await lprox.puts(cryodata)

                    self.len(6, await alist(lprox.slice(0, 9999)))

                    # test offset storage and updating
                    iden = s_common.guid()
                    self.eq(0, await lprox.offset(iden))
                    self.eq(2, await lprox.puts(cryodata, seqn=(iden, 0)))
                    self.eq(2, await lprox.offset(iden))

                # test the new open share
                async with cryo.getLocalProxy(share='cryotank/lulz') as lprox:

                    self.len(0, await alist(lprox.slice(0, 9999)))

                    await lprox.puts(cryodata)

                    self.len(2, await alist(lprox.slice(0, 9999)))

                    self.len(1, await alist(lprox.metrics(0)))

                # Delete apis
                self.false(await prox.delete('newp'))
                self.true(await prox.delete('lulz'))

            # Re-open the tank and ensure that the deleted tank is not present.
            async with self.getTestCryoAndProxy(dirn=dirn) as (cryo, prox):
                tanks = await prox.list()
                self.len(1, tanks)
                self.eq('foo', tanks[0][0])

    async def test_cryo_init(self):
        with self.getTestDir() as dirn:
            async with self.getTestCryo(dirn) as cryo:
                # test passing conf data in through init directly
                tank = await cryo.init('conftest', conf={'map_size': s_const.mebibyte * 64})
                self.eq(tank.slab.mapsize, s_const.mebibyte * 64)
                _, conf = await cryo.hive.get(('cryo', 'names', 'conftest'))
                self.eq(conf, {'map_size': s_const.mebibyte * 64})

            # And the data was persisted
            async with self.getTestCryo(dirn) as cryo:
                tank = cryo.tanks.get('conftest')
                self.eq(tank.slab.mapsize, s_const.mebibyte * 64)
                _, conf = await cryo.hive.get(('cryo', 'names', 'conftest'))
                self.eq(conf, {'map_size': s_const.mebibyte * 64})
