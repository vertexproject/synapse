import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.daemon as s_daemon

import synapse.tests.utils as s_test

import synapse.lib.hive as s_hive
import synapse.lib.lmdbslab as s_slab

class HiveTest(s_test.SynTest):

    @contextlib.asynccontextmanager
    async def getTestHive(self):
        with self.getTestDir() as dirn:
            async with self.getTestHiveFromDirn(dirn) as hive:
                yield hive

    @contextlib.asynccontextmanager
    async def getTestHiveFromDirn(self, dirn):

        import synapse.lib.const as s_const
        map_size = s_const.gibibyte

        async with await s_slab.Slab.anit(dirn, map_size=map_size) as slab:

            async with await s_hive.SlabHive.anit(slab) as hive:

                yield hive

    @contextlib.asynccontextmanager
    async def getTestHiveDmon(self):

        with self.getTestDir() as dirn:

            async with self.getTestHiveFromDirn(dirn) as hive:

                async with await s_daemon.Daemon.anit(dirn) as dmon:

                    await dmon.listen('tcp://127.0.0.1:0/')
                    dmon.share('hive', hive)

                    yield dmon

    @contextlib.asynccontextmanager
    async def getTestTeleHive(self):

        async with self.getTestHiveDmon() as dmon:

            turl = self.getTestUrl(dmon, 'hive')

            async with await s_hive.openurl(turl) as hive:

                yield hive

    async def test_hive_slab(self):

        with self.getTestDir() as dirn:

            async with self.getTestHiveFromDirn(dirn) as hive:

                path = ('foo', 'bar')

                #node = await hive.open(path)
                async with await hive.dict(path) as hivedict:

                    self.none(await hivedict.set('hehe', 200))
                    self.none(await hivedict.set('haha', 'hoho'))

                    data = {}

                    async def onSetHehe(valu):
                        data['hehe'] = valu

                    self.eq(200, hivedict.get('hehe', onedit=onSetHehe))

                    self.eq(200, await hivedict.set('hehe', 300))

                    self.eq(300, hivedict.get('hehe'))

                    self.eq(300, await hive.get(('foo', 'bar', 'hehe')))
                    self.eq(300, await hive.set(('foo', 'bar', 'hehe'), 400))

                    hivedict.setdefault('lulz', 31337)

                    self.eq(31337, hivedict.get('lulz'))

            async with self.getTestHiveFromDirn(dirn) as hive:

                self.eq(400, await hive.get(('foo', 'bar', 'hehe')))
                self.eq('hoho', await hive.get(('foo', 'bar', 'haha')))

                self.none(await hive.get(('foo', 'bar', 'lulz')))

                path = ('foo', 'bar')

    async def test_hive_telepath(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestHiveDmon() as dmon:

            turl = self.getTestUrl(dmon, 'hive')

            async with await s_hive.openurl(turl) as hive0:

                path = ('foo', 'bar')

                evnt = asyncio.Event()
                def onedit(mesg):
                    evnt.set()

                node0 = await hive0.open(path)
                node0.on('hive:set', onedit)

                async with await s_hive.openurl(turl) as hive1:

                    node1 = await hive1.open(path)
                    await node1.set(200)

                    await evnt.wait()

                    self.eq(200, node0.valu)

                    self.eq(201, await node0.add(1))
                    self.eq(202, await node1.add(1))
                    self.eq(203, await node0.add(1))

    async def test_hive_auth(self):

        async with self.getTestTeleHive() as hive:

            node = await hive.open(('hive', 'auth'))

            async with await s_hive.HiveAuth.anit(node) as auth:

                user = await auth.addUser('visi@vertex.link')
                role = await auth.addRole('ninjas')

                with self.raises(s_exc.DupUserName):
                    await auth.addUser('visi@vertex.link')

                with self.raises(s_exc.DupRoleName):
                    await auth.addRole('ninjas')

                self.nn(user)

                self.false(user.admin)
                self.len(0, user.rules)
                self.len(0, user.roles)

                await user.info.set('admin', True)

                self.true(user.admin)

                self.true(user.allowed(('foo', 'bar')))
                self.false(user.allowed(('foo', 'bar'), elev=False))

                await user.addRule((True, ('foo',)))

                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.len(1, user.permcache)

                await user.grant('ninjas')

                self.len(0, user.permcache)

                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.true(user.allowed(('baz', 'faz')))
                self.false(user.allowed(('baz', 'faz'), elev=False))

                self.len(2, user.permcache)

                await role.addRule((True, ('baz', 'faz')))

                self.len(0, user.permcache)

                self.true(user.allowed(('baz', 'faz'), elev=False))
                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.len(2, user.permcache)

                await user.setLocked(True)

                self.false(user.allowed(('baz', 'faz'), elev=True))
                self.false(user.allowed(('baz', 'faz'), elev=False))

                await user.setLocked(False)

                self.true(user.allowed(('baz', 'faz'), elev=False))
                self.true(user.allowed(('foo', 'bar'), elev=False))
