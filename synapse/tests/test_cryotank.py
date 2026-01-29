import os
import asyncio

import synapse.exc as s_exc
import synapse.cryotank as s_cryotank

import synapse.lib.const as s_const
import synapse.lib.slaboffs as s_slaboffs

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

                footankiden = await prox.init('foo')
                self.nn(footankiden)

                self.eq([('foo', footankiden)], [(info[0], info[1]['iden']) for info in await prox.list()])

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
                _, conf = cryo.names.get('conftest')
                self.eq(conf, {'map_size': s_const.mebibyte * 64})

            # And the data was persisted
            async with self.getTestCryo(dirn) as cryo:
                tank = cryo.tanks.get('conftest')
                self.eq(tank.slab.mapsize, s_const.mebibyte * 64)
                _, conf = cryo.names.get('conftest')
                self.eq(conf, {'map_size': s_const.mebibyte * 64})

    async def test_cryo_perms(self):

        async with self.getTestCryo() as cryo:

            uadmin = (await cryo.addUser('admin'))['iden']
            await cryo.setUserAdmin(uadmin, True)

            ulower = (await cryo.addUser('lower'))['iden']

            utank0 = (await cryo.addUser('tank0'))['iden']
            await cryo.addUserRule(utank0, (True, ('cryo', 'tank', 'add')), gateiden='cryo')

            await cryo.init('tank1')

            async with cryo.getLocalProxy(user='tank0') as prox:

                # check perm defs

                perms = await prox.getPermDefs()
                self.eq([
                    ('cryo', 'tank', 'add'),
                    ('cryo', 'tank', 'put'),
                    ('cryo', 'tank', 'read'),
                ], [p['perm'] for p in perms])

                perm = await prox.getPermDef(('cryo', 'tank', 'add'))
                self.eq(('cryo', 'tank', 'add'), perm['perm'])

                # creator is admin

                tankiden0 = await prox.init('tank0')

                self.eq(1, await prox.puts('tank0', ('foo',)))
                self.nn(await prox.last('tank0'))
                self.len(1, await alist(prox.slice('tank0', 0, wait=False)))
                self.len(1, await alist(prox.rows('tank0', 0, 10)))
                self.len(1, await alist(prox.metrics('tank0', 0)))

                async with cryo.getLocalProxy(user='tank0', share='cryotank/tank0b') as share:
                    tankiden0b = await share.iden()
                    self.eq(1, await share.puts(('foo',)))
                    self.len(1, await alist(share.slice(0, wait=False)))
                    self.len(1, await alist(share.metrics(0)))

                # ..but only admin on that tank

                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank1', ('bar',)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.rows('tank1', 0, 10)))

                async with cryo.getLocalProxy(user='tank0', share='cryotank/tank1') as share:
                    await self.asyncraises(s_exc.AuthDeny, share.puts(('bar',)))
                    await self.asyncraises(s_exc.AuthDeny, alist(share.slice(0, wait=False)))

                # only sees tanks in list() they have read access to

                self.len(2, await prox.list())
                self.len(3, await cryo.list())

                # only global admin can delete

                await self.asyncraises(s_exc.AuthDeny, prox.delete('tank0'))

            async with cryo.getLocalProxy(user='lower') as prox:

                # default user has no access

                self.len(0, await prox.list())

                await self.asyncraises(s_exc.AuthDeny, prox.init('tank2'))
                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank0', ('bar',)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.slice('tank0', 0, wait=False)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.rows('tank0', 0, 10)))
                await self.asyncraises(s_exc.AuthDeny, alist(prox.metrics('tank0', 0)))

                with self.raises(s_exc.AuthDeny):
                    async with cryo.getLocalProxy(user='lower', share='cryotank/tank2'):
                        pass

                async with cryo.getLocalProxy(user='lower', share='cryotank/tank0b') as share:
                    self.eq(tankiden0b, await share.iden())
                    await self.asyncraises(s_exc.AuthDeny, share.puts(('bar',)))
                    await self.asyncraises(s_exc.AuthDeny, alist(share.slice(0, wait=False)))
                    await self.asyncraises(s_exc.AuthDeny, alist(share.metrics(0)))

                # add read access

                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'read')), gateiden=tankiden0)
                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'read')), gateiden=tankiden0b)

                self.len(2, await prox.list())

                await self.asyncraises(s_exc.AuthDeny, prox.puts('tank0', ('bar',)))
                self.len(1, await alist(prox.slice('tank0', 0, wait=False)))
                self.len(1, await alist(prox.rows('tank0', 0, 10)))
                self.len(1, await alist(prox.metrics('tank0', 0)))

                async with cryo.getLocalProxy(user='lower', share='cryotank/tank0b') as share:
                    await self.asyncraises(s_exc.AuthDeny, share.puts(('bar',)))
                    self.len(1, await alist(share.slice(0, wait=False)))
                    self.len(1, await alist(share.metrics(0)))

                # add write access

                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'put')), gateiden=tankiden0)
                await cryo.addUserRule(ulower, (True, ('cryo', 'tank', 'put')), gateiden=tankiden0b)

                self.eq(1, await prox.puts('tank0', ('bar',)))

                async with cryo.getLocalProxy(user='lower', share='cryotank/tank0b') as share:
                    self.eq(1, await share.puts(('bar',)))

    async def test_cryo_migrate_v2(self):

        with self.withNexusReplay():

            with self.getRegrDir('cells', 'cryotank-2.147.0') as dirn:

                async with self.getTestCryoAndProxy(dirn=dirn) as (cryo, prox):

                    tank00iden = 'a4f502db5ebb7740eb8423639144ecf4'
                    tank01iden = '1cfca0e6d5c4b9daff65f75e29db25dd'

                    seqniden = 'acf2a29b8f2a88c29e6d6ff359c86667'

                    self.eq(
                        [(0, 'foo'), (1, 'bar')],
                        await alist(prox.slice('tank00', 0, wait=False))
                    )

                    self.eq(
                        [(0, 'cat'), (1, 'dog'), (2, 'emu')],
                        await alist(prox.slice('tank01', 0, wait=False))
                    )

                    tank00 = await cryo.init('tank00')
                    self.true(tank00iden == cryo.names.get('tank00')[0] == tank00.iden())
                    self.false(os.path.exists(os.path.join(tank00.dirn, 'guid')))
                    self.false(os.path.exists(os.path.join(tank00.dirn, 'cell.guid')))
                    self.false(os.path.exists(os.path.join(tank00.dirn, 'slabs', 'cell.lmdb')))
                    self.eq(0, s_slaboffs.SlabOffs(tank00.slab, 'offsets').get(seqniden))

                    tank01 = await cryo.init('tank01')
                    self.true(tank01iden == cryo.names.get('tank01')[0] == tank01.iden())
                    self.false(os.path.exists(os.path.join(tank01.dirn, 'guid')))
                    self.false(os.path.exists(os.path.join(tank01.dirn, 'cell.guid')))
                    self.false(os.path.exists(os.path.join(tank01.dirn, 'slabs', 'cell.lmdb')))
                    self.eq(0, s_slaboffs.SlabOffs(tank01.slab, 'offsets').get(seqniden))

                    await prox.puts('tank00', ('bam',))
                    self.eq(
                        [(1, 'bar'), (2, 'bam')],
                        await alist(prox.slice('tank00', 1, wait=False))
                    )

                    await prox.puts('tank01', ('eek',))
                    self.eq(
                        [(2, 'emu'), (3, 'eek')],
                        await alist(prox.slice('tank01', 2, wait=False))
                    )
