import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

import synapse.lib.hive as s_hive
import synapse.lib.lmdbslab as s_slab

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

                self.eq(user, auth.user(user.iden))
                self.eq(user, auth.getUserByName('visi@vertex.link'))

                self.eq(role, auth.role(role.iden))
                self.eq(role, auth.getRoleByName('ninjas'))

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

                await user.delRule((True, ('foo',)))

                self.len(0, user.permcache)
                self.false(user.allowed(('foo', 'bar'), elev=False))

                await user.addRule((True, ('foo',)))

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

                await self.asyncraises(s_exc.NoSuchRole, user.revoke('accountants'))

                await user.revoke('ninjas')
                self.false(user.allowed(('baz', 'faz'), elev=False))

                await user.grant('ninjas')
                self.true(user.allowed(('baz', 'faz'), elev=False))

                await self.asyncraises(s_exc.NoSuchRole, auth.delRole('accountants'))

                await auth.delRole('ninjas')
                self.false(user.allowed(('baz', 'faz'), elev=False))

                await self.asyncraises(s_exc.NoSuchUser, auth.delUser('fred@accountancy.com'))

                await auth.delUser('visi@vertex.link')
                self.false(user.allowed(('baz', 'faz'), elev=False))

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

            self.eq(None, await hive.pop(('foo', )))
            self.none(await hive.get(('foo', 'bar')))

    async def test_hive_tele_auth(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestHiveDmon() as dmon:

            hive = dmon.shared.get('hive')

            hive.conf['auth:en'] = True

            auth = await hive.getHiveAuth()

            user = auth.getUserByName('root')
            await user.setPasswd('secret')

            # hive passwords must be non-zero length strings
            with self.raises(s_exc.BadArg):
                await user.setPasswd('')
            with self.raises(s_exc.BadArg):
                await user.setPasswd({'key': 'vau'})

            turl = self.getTestUrl(dmon, 'hive')

            await user.setLocked(True)

            with self.raises(s_exc.AuthDeny):
                await s_hive.openurl(turl, user='root', passwd='secret')

            await user.setLocked(False)

            with self.raises(s_exc.AuthDeny):
                await s_hive.openurl(turl, user='root', passwd='newpnewp')

            async with await s_hive.openurl(turl, user='root', passwd='secret') as hive0:
                await hive.open(('foo', 'bar'))

    async def test_hive_saveload(self):

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
