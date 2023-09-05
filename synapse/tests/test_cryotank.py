import asyncio

import synapse.exc as s_exc
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

                # waiters

                self.true(await prox.init('dowait'))

                self.true(await prox.puts('dowait', cryodata))
                await self.agenlen(2, prox.slice('dowait', 0, size=1000))

                genr = prox.slice('dowait', 1, size=1000, wait=True).__aiter__()

                res = await asyncio.wait_for(genr.__anext__(), timeout=2)
                self.eq(1, res[0])

                await prox.puts('dowait', cryodata[:1])
                res = await asyncio.wait_for(genr.__anext__(), timeout=2)
                self.eq(2, res[0])

                await self.asyncraises(TimeoutError, asyncio.wait_for(genr.__anext__(), timeout=1))

                genr = prox.slice('dowait', 4, size=1000, wait=True, timeout=1)
                res = await asyncio.wait_for(alist(genr), timeout=2)
                self.eq([], res)

                self.true(await prox.delete('dowait'))

                # test the direct tank share....
                async with cryo.getLocalProxy(share='cryotank/foo') as lprox:

                    items = await alist(lprox.slice(1, 3))

                    self.eq(items[0][1][0], 'baz')

                    self.len(4, await alist(lprox.slice(0, 9999)))

                    await lprox.puts(cryodata)

                    self.len(6, await alist(lprox.slice(0, 9999)))

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

    async def test_cryo_perms(self):

        async with self.getTestCryo() as cryo:

            uadmin = (await cryo.addUser('admin'))['iden']
            await cryo.setUserAdmin(uadmin, True)

            ulower = (await cryo.addUser('lower'))['iden']

            utank0 = (await cryo.addUser('tank0'))['iden']
            await cryo.addUserRule(utank0, (True, ('cryo', 'tank', 'add')))

            await cryo.init('tank1')
            tankiden1 = cryo.getTankIdenByName('tank1')

            async with cryo.getLocalProxy(user='tank0') as prox:

                # creator is admin

                self.true(await prox.init('tank0'))
                tankiden0 = cryo.getTankIdenByName('tank0')

                self.eq(1, await prox.puts('tank0', ('foo',)))
                self.nn(await prox.last('tank0'))
                self.len(1, await alist(prox.slice('tank0', 0, wait=False)))
                self.len(1, await alist(prox.rows('tank0', 0, 10)))
                self.len(1, await alist(prox.metrics('tank0', 0)))

                # ..but only admin on that tank

                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank1', ('bar',)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.rows('tank1', 0, 10)))

                # only sees tanks in list() they have read access to

                self.len(1, await prox.list())
                self.len(2, await cryo.list())

                # only admin can delete

                await self.asyncraises(s_exc.AuthDeny, prox.delete('tank0'))

            async with cryo.getLocalProxy(user='lower') as prox:

                # default user has no access

                self.len(0, await prox.list())

                await self.asyncraises(s_exc.AuthDeny, prox.init('tank2'))
                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank0', ('bar',)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.slice('tank0', 0, wait=False)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.rows('tank0', 0, 10)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.metrics('tank0', 0)))

                # add read access

                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'read')), gateiden=tankiden0)

                self.len(1, await prox.list())

                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank0', ('bar',)))
                self.len(1, await alist(prox.slice('tank0', 0, wait=False)))
                self.len(1, await alist(prox.rows('tank0', 0, 10)))
                self.len(1, await alist(prox.metrics('tank0', 0)))

                # add write access

                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'put')), gateiden=tankiden0)

                self.eq(1, await prox.puts('tank0', ('bar',)))

            # todo: migration for idens
            # todo: remove offset tracking / drop during migration
