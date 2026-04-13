import asyncio
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.httpapi as s_httpapi
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version

import synapse.tests.utils as s_test

class StormLibPkgTest(s_test.SynTest):

    async def test_stormlib_pkg_basic(self):

        async with self.getTestCore() as core:

            pkg0 = {'name': 'hehe', 'version': '1.2.3'}
            await core.addStormPkg(pkg0)
            self.eq('1.2.3', await core.callStorm('return($lib.pkg.get(hehe).version)'))

            self.eq(None, await core.callStorm('return($lib.pkg.get(nopkg))'))

            pkg1 = {'name': 'haha', 'version': '1.2.3'}
            await core.addStormPkg(pkg1)
            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('haha', msgs)
            self.stormIsInPrint('hehe', msgs)

            self.true(await core.callStorm('return($lib.pkg.has(haha))'))

            await core.delStormPkg('haha')
            self.none(await core.callStorm('return($lib.pkg.get(haha))'))
            self.false(await core.callStorm('return($lib.pkg.has(haha))'))

            msgs = await core.stormlist('pkg.list --verbose')
            self.stormIsInPrint('not available', msgs)

            pkg2 = {'name': 'hoho', 'version': '4.5.6', 'build': {'time': 1732017600000000}}
            await core.addStormPkg(pkg2)
            self.eq('4.5.6', await core.callStorm('return($lib.pkg.get(hoho).version)'))
            msgs = await core.stormlist('pkg.list --verbose')
            self.stormIsInPrint('2024-11-19 12:00:00', msgs)

            pkgdef = {
                'name': 'foobar',
                'version': '1.2.3',
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (),
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'conflicts': (
                        {'name': 'foobar'},
                    ),
                }
            }

            with self.raises(s_exc.StormPkgConflicts):
                await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (
                    {'name': 'foobar', 'version': None, 'desc': None, 'ok': False, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'conflicts': (
                        {'name': 'foobar', 'version': '>=1.0.0', 'desc': 'foo'},
                    ),
                }
            }

            with self.raises(s_exc.StormPkgConflicts):
                await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (
                    {'name': 'foobar', 'version': '>=1.0.0', 'desc': 'foo', 'ok': False, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'foobar', 'version': '>=2.0.0,<3.0.0'},
                    ),
                }
            }

            with self.getAsyncLoggerStream('synapse.cortex', 'bazfaz requirement') as stream:
                await core.addStormPkg(pkgdef)
                self.true(await stream.wait(timeout=1))

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'optional': True},
                    ),
                }
            }

            with self.getAsyncLoggerStream('synapse.cortex', 'bazfaz optional requirement') as stream:
                await core.addStormPkg(pkgdef)
                self.true(await stream.wait(timeout=1))

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'desc': None,
                     'ok': False, 'actual': '1.2.3', 'optional': True},
                ),
                'conflicts': ()
            }, deps)

            pkgdef = {
                'name': 'lolzlolz',
                'version': '1.2.3',
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (),
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'lolzlolz', 'version': '>=1.0.0,<2.0.0', 'desc': 'lol'},
                    ),
                    'conflicts': (
                        {'name': 'foobar', 'version': '>=3.0.0'},
                    ),
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'lolzlolz', 'version': '>=1.0.0,<2.0.0', 'desc': 'lol', 'ok': True, 'actual': '1.2.3'},
                ),
                'conflicts': (
                    {'name': 'foobar', 'version': '>=3.0.0', 'desc': None, 'ok': True, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'zoinkszoinks',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'newpnewp', 'version': '1.2.3'},
                    ),
                    'conflicts': (
                        {'name': 'newpnewp'},
                    ),
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'newpnewp', 'version': '1.2.3', 'desc': None, 'ok': False, 'actual': None},
                ),
                'conflicts': (
                    {'name': 'newpnewp', 'version': None, 'desc': None, 'ok': True, 'actual': None},
                )
            }, deps)

    async def test_stormlib_pkg_load(self):
        cont = s_common.guid()
        pkg = {
            'name': 'testload',
            'version': '0.3.0',
            'modules': (
                {
                    'name': 'testload',
                    'storm': 'function x() { return((0)) }',
                },
            ),
            'onload': f'[ entity:contact={cont} ] $lib.print(teststring) $lib.warn(testwarn, key=valu) return($path.vars.newp)'
        }
        class PkgHandler(s_httpapi.Handler):

            async def get(self, name):
                assert self.request.headers.get('X-Synapse-Version') == s_version.verstring

                if name == 'notok':
                    self.sendRestErr('FooBar', 'baz faz')
                    return

                self.sendRestRetn(pkg)

        class PkgHandlerRaw(s_httpapi.Handler):
            async def get(self, name):
                assert self.request.headers.get('X-Synapse-Version') == s_version.verstring

                self.set_header('Content-Type', 'application/json')
                return self.write(pkg)

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/pkgtest/(.*)', PkgHandler, {'cell': core})
            core.addHttpApi('/api/v1/pkgtestraw/(.*)', PkgHandlerRaw, {'cell': core})
            port = (await core.addHttpsPort(0, host='127.0.0.1'))[1]

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/newp/newp')
            self.stormIsInWarn('pkg.load got HTTP code: 404', msgs)

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/notok')
            self.stormIsInWarn('pkg.load got JSON error: FooBar', msgs)

            # onload will on fire once. all other pkg.load events will effectively bounce
            # because the pkg hasn't changed so no loading occurs
            waiter = core.waiter(1, 'core:pkg:onload:complete')

            with self.getAsyncLoggerStream('synapse.cortex') as stream:
                msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

                msgs = await core.stormlist(f'pkg.load --ssl-noverify --raw https://127.0.0.1:{port}/api/v1/pkgtestraw/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

            stream.seek(0)
            buf = stream.read()
            self.isin("testload onload output: teststring", buf)
            self.isin("testload onload output: testwarn", buf)
            self.isin("No var with name: newp", buf)
            self.len(1, await core.nodes(f'entity:contact={cont}'))

            evnts = await waiter.wait(timeout=4)
            exp = [
                ('core:pkg:onload:complete', {'pkg': 'testload', 'storvers': -1})
            ]
            self.eq(exp, evnts)

    async def test_stormlib_pkg_vars(self):
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                lowuser = await core.addUser('lowuser')
                aslow = {'user': lowuser.get('iden')}
                await core.callStorm('auth.user.addrule lowuser node')

                # basic crud

                self.none(await core.callStorm('return($lib.pkg.vars(pkg0).bar)'))
                self.none(await core.callStorm('$varz=$lib.pkg.vars(pkg0) $varz.baz=$lib.undef return($varz.baz)'))
                self.eq([], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    return($kvs)
                '''))

                await core.callStorm('$lib.pkg.vars(pkg0).bar = cat')
                await core.callStorm('$lib.pkg.vars(pkg0).baz = dog')

                await core.callStorm('$lib.pkg.vars(pkg1).bar = emu')
                await core.callStorm('$lib.pkg.vars(pkg1).baz = groot')

                self.eq('cat', await core.callStorm('return($lib.pkg.vars(pkg0).bar)'))
                self.eq('dog', await core.callStorm('return($lib.pkg.vars(pkg0).baz)'))
                self.eq('emu', await core.callStorm('return($lib.pkg.vars(pkg1).bar)'))
                self.eq('groot', await core.callStorm('return($lib.pkg.vars(pkg1).baz)'))

                self.sorteq([('bar', 'cat'), ('baz', 'dog')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    return($kvs)
                '''))
                self.sorteq([('bar', 'emu'), ('baz', 'groot')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg1) { $kvs.append($kv) }
                    return($kvs)
                '''))

                await core.callStorm('$lib.pkg.vars(pkg0).baz = $lib.undef')
                self.none(await core.callStorm('return($lib.pkg.vars(pkg0).baz)'))

                # perms

                await self.asyncraises(s_exc.AuthDeny, core.callStorm('$lib.print($lib.pkg.vars(pkg0))', opts=aslow))
                await self.asyncraises(s_exc.AuthDeny, core.callStorm('return($lib.pkg.vars(pkg0).baz)', opts=aslow))
                await self.asyncraises(s_exc.AuthDeny, core.callStorm('$lib.pkg.vars(pkg0).baz = cool', opts=aslow))
                await self.asyncraises(s_exc.AuthDeny, core.callStorm('$lib.pkg.vars(pkg0).baz = $lib.undef', opts=aslow))
                await self.asyncraises(s_exc.AuthDeny, core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    return($kvs)
                ''', opts=aslow))
                await self.asyncraises(s_exc.AuthDeny, core.callStorm('''
                    [ test:str=foo ]
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    fini { return($kvs) }
                ''', opts=aslow))

                await core.callStorm('auth.user.addrule lowuser "power-ups.pkg0.admin"')

                self.stormHasNoWarnErr(await core.nodes('$lib.print($lib.pkg.vars(pkg0))', opts=aslow))
                await core.callStorm('$lib.pkg.vars(pkg0).baz = cool', opts=aslow)
                self.eq('cool', await core.callStorm('return($lib.pkg.vars(pkg0).baz)', opts=aslow))
                await core.callStorm('$lib.pkg.vars(pkg0).baz = $lib.undef', opts=aslow)
                self.eq([('bar', 'cat')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    return($kvs)
                ''', opts=aslow))
                self.eq([('bar', 'cat')], await core.callStorm('''
                    [ test:str=foo ]
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    fini { return($kvs) }
                ''', opts=aslow))

            async with self.getTestCore(dirn=dirn) as core:

                # data persists

                self.eq('cat', await core.callStorm('return($lib.pkg.vars(pkg0).bar)'))
                self.none(await core.callStorm('return($lib.pkg.vars(pkg0).baz)'))
                self.eq('emu', await core.callStorm('return($lib.pkg.vars(pkg1).bar)'))
                self.eq('groot', await core.callStorm('return($lib.pkg.vars(pkg1).baz)'))

                self.sorteq([('bar', 'cat')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg0) { $kvs.append($kv) }
                    return($kvs)
                '''))
                self.sorteq([('bar', 'emu'), ('baz', 'groot')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.vars(pkg1) { $kvs.append($kv) }
                    return($kvs)
                '''))

    async def test_stormlib_pkg_queues(self):
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                self.eq(1, await core.callStorm('$q = $lib.pkg.queues(pkg0).add(stuff) $q.put(5) return($q.size())'))
                self.eq(2, await core.callStorm('$q = $lib.pkg.queues(pkg0).get(stuff) $q.put(6) return($q.size())'))
                self.eq(3, await core.callStorm('$q = $lib.pkg.queues(pkg0).gen(stuff) $q.put(7) return($q.size())'))
                self.eq(1, await core.callStorm('$q = $lib.pkg.queues(pkg0).gen(other) $q.put(8) return($q.size())'))
                self.eq(1, await core.callStorm('$q = $lib.pkg.queues(pkg1).gen(stuff) $q.put(9) return($q.size())'))

                # Replay coverage
                await core._addStormPkgQueue('pkg1', 'stuff', {})
                await core._delStormPkgQueue('pkg1', 'newp')

                q = '$qs = () for $q in $lib.pkg.queues(pkg0).list() { $qs.append($q) } return($qs)'
                self.len(2, await core.callStorm(q))

                q = '$qs = () for $q in $lib.pkg.queues(pkg1).list() { $qs.append($q) } return($qs)'
                self.len(1, await core.callStorm(q))

                await core.callStorm('$q = $lib.pkg.queues(pkg0).del(other)')

                q = '$qs = () for $q in $lib.pkg.queues(pkg0).list() { $qs.append($q) } return($qs)'
                self.len(1, await core.callStorm(q))

                await core.callStorm('$lib.pkg.queues(pkg0).get(stuff).puts((10, 11))')

                self.eq((0, '5'), await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).get())'))

                q = '''
                $retn = ()
                for ($_, $v) in $lib.pkg.queues(pkg0).get(stuff).gets(1, wait=(false)) { $retn.append($v) }
                return($retn)
                '''
                self.eq(('6', '7', '10', '11'), await core.callStorm(q))

                q = '''
                $retn = ()
                for ($_, $v) in $lib.pkg.queues(pkg0).get(stuff).gets(1, size=(2)) { $retn.append($v) }
                return($retn)
                '''
                self.eq(('6', '7'), await core.callStorm(q))

                self.eq((1, '6'), await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).get(1))'))

                q = '''
                $retn = ()
                for ($_, $v) in $lib.pkg.queues(pkg0).get(stuff).gets(2, wait=(false)) { $retn.append($v) }
                return($retn)
                '''
                self.eq(('7', '10', '11'), await core.callStorm(q))

                await core.callStorm('$lib.pkg.queues(pkg0).get(stuff).cull(2)')
                self.eq((3, '10'), await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).pop())'))

                q = 'return(`{$lib.pkg.queues(pkg0).get(stuff)}`)'
                self.eq('pkg:queue: pkg0 - stuff', await core.callStorm(q))

                q = 'return(($lib.pkg.queues(pkg0).get(stuff) = $lib.pkg.queues(pkg0).get(stuff)))'
                self.true(await core.callStorm(q))

                q = 'return(($lib.pkg.queues(pkg0).get(stuff) = $lib.pkg.queues(pkg1).get(stuff)))'
                self.false(await core.callStorm(q))

                q = 'return(($lib.pkg.queues(pkg0).get(stuff) = "newp"))'
                self.false(await core.callStorm(q))

                q = '$set = $lib.set() $p = $lib.pkg.queues(pkg0).get(stuff) $set.add($p) $set.add($p) return($set)'
                self.len(1, await core.callStorm(q))

                with self.raises(s_exc.DupName):
                    await core.callStorm('$lib.pkg.queues(pkg1).add(stuff)')

                with self.raises(s_exc.NoSuchName):
                    await core.callStorm('$lib.pkg.queues(pkg1).del(newp)')

                lowuser = await core.addUser('lowuser')
                aslow = {'user': lowuser.get('iden')}
                await core.callStorm('auth.user.addrule lowuser "power-ups.pkg0.admin"')

                self.eq(1, await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).size())', opts=aslow))

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm('$lib.print($lib.pkg.queues(pkg1))', opts=aslow)

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm('$lib.pkg.queues(pkg1).get(stuff)', opts=aslow)

            async with self.getTestCore(dirn=dirn) as core:
                self.eq(1, await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).size())', opts=aslow))

                self.eq((4, '11'), await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).pop(4))'))
                self.none(await core.callStorm('return($lib.pkg.queues(pkg0).get(stuff).pop())'))

    async def test_stormlib_pkg_uninstall(self):

        # Basic uninstall with onuninstall handler, pkg vars cleaned, queues cleaned, beholder events
        async with self.getTestCore() as core:

            onuninstall = {'query': '$lib.print(`onuninstall called keep={$keep}`)'}
            pkg = {
                'name': 'test.uninstall',
                'version': '1.0.0',
                'onuninstall': onuninstall,
            }

            await core.addStormPkg(pkg)

            # Set up some pkg vars and queues
            await core.callStorm('$lib.pkg.vars(test.uninstall).myvar = hello')
            self.eq('hello', await core.callStorm('return($lib.pkg.vars(test.uninstall).myvar)'))

            await core.callStorm('$lib.pkg.queues(test.uninstall).add(myqueue).put(42)')
            self.eq(1, await core.callStorm('return($lib.pkg.queues(test.uninstall).get(myqueue).size())'))

            # Use beholder to watch for events
            beholds = []

            async def _onBeholder(evnt):
                beholds.append(evnt)

            core.on('cell:beholder', _onBeholder)

            onuninstallwaiter = core.waiter(1, 'core:pkg:onuninstall:complete')
            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'onuninstall called keep=') as stream:
                msgs = await core.stormlist('pkg.del test.uninstall --uninstall')
                self.stormIsInPrint('Uninstalling package: test.uninstall', msgs)
                self.true(await stream.wait(timeout=30))

            evnts = await onuninstallwaiter.wait(timeout=30)
            self.ge(len(evnts), 1)
            self.eq(evnts[0][0], 'core:pkg:onuninstall:complete')

            evnts = await donewaiter.wait(timeout=30)
            self.ge(len(evnts), 1)
            self.eq(evnts[0][0], 'core:pkg:uninstall:complete')

            # Pkg should be gone
            self.none(await core.callStorm('return($lib.pkg.get(test.uninstall))'))

            # Pkg vars should be gone
            self.none(await core.callStorm('return($lib.pkg.vars(test.uninstall).myvar)'))

            # Queues should be gone
            q = '$qs = () for $q in $lib.pkg.queues(test.uninstall).list() { $qs.append($q) } return($qs)'
            self.len(0, await core.callStorm(q))

            # Verify beholder events
            bnames = [e[1].get('event') for e in beholds]
            self.isin('pkg:uninstall:start', bnames)
            self.isin('pkg:del', bnames)

        # onuninstall receives keep set via $lib.pkg.del with uninstall
        async with self.getTestCore() as core:

            onuninstall = {'query': 'if (not $keep) { $lib.print(keep_empty) } else { $lib.print(`keep={$keep}`) }'}
            pkg = {
                'name': 'test.keepset',
                'version': '1.0.0',
                'onuninstall': onuninstall,
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.keepset).myvar = hello')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'keep=') as stream:
                await core.callStorm('$lib.pkg.del(test.keepset, uninstall=$lib.true, keep=(variables,))')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            # Pkg should be gone
            self.none(await core.callStorm('return($lib.pkg.get(test.keepset))'))

            # Pkg vars should still be present because we kept them
            self.eq('hello', await core.callStorm('return($lib.pkg.vars(test.keepset).myvar)'))

        # --uninstall-keep queues via Storm command
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepqueues',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.queues(test.keepqueues).add(q1).put(99)')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            msgs = await core.stormlist('pkg.del test.keepqueues --uninstall --uninstall-keep (queues,)')
            self.stormIsInPrint('Uninstalling package: test.keepqueues', msgs)

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.keepqueues))'))

            # Queue should still exist
            self.eq(1, await core.callStorm('return($lib.pkg.queues(test.keepqueues).get(q1).size())'))

        # --uninstall-keep pkg-vars via core API
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keeppkgvars',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.keeppkgvars).myvar = hello')
            await core.callStorm('$lib.pkg.queues(test.keeppkgvars).add(q1).put(42)')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.keeppkgvars', uninstall=True, keep=('variables',))
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.keeppkgvars))'))

            # Pkg vars should still be present
            self.eq('hello', await core.callStorm('return($lib.pkg.vars(test.keeppkgvars).myvar)'))

            # Queues should be cleaned
            q = '$qs = () for $q in $lib.pkg.queues(test.keeppkgvars).list() { $qs.append($q) } return($qs)'
            self.len(0, await core.callStorm(q))

        # Vault cleanup during uninstall
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.vaultclean',
                'version': '1.0.0',
                'vaults': {
                    'test:vaultclean': {
                        'schemas': {},
                    },
                },
            }

            await core.addStormPkg(pkg)

            # Create a vault with the package's vault type
            vdef = {
                'name': 'my test vault',
                'type': 'test:vaultclean',
                'scope': 'global',
                'owner': None,
                'secrets': {},
                'configs': {},
            }
            viden = await core.addVault(vdef)

            self.nn(core.getVault(viden))

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.vaultclean', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.vaultclean))'))
            self.none(core.getVault(viden))

        # Vault kept with --uninstall-keep vaults
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.vaultkeep',
                'version': '1.0.0',
                'vaults': {
                    'test:vaultkeep': {
                        'schemas': {},
                    },
                },
            }

            await core.addStormPkg(pkg)

            vdef = {
                'name': 'my kept vault',
                'type': 'test:vaultkeep',
                'scope': 'global',
                'owner': None,
                'secrets': {},
                'configs': {},
            }
            viden = await core.addVault(vdef)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.vaultkeep', uninstall=True, keep=('vaults',))
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.vaultkeep))'))
            self.nn(core.getVault(viden))

        # Dmon created on package load and cleaned up during uninstall
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            pkg = {
                'name': 'test.dmonclean',
                'version': '1.0.0',
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            # Dmon should have been created automatically
            self.nn(await core.getStormDmon(dmoniden))

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.dmonclean', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.dmonclean))'))
            self.none(await core.getStormDmon(dmoniden))

        # Dmon bumped when package is re-added
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            pkg = {
                'name': 'test.dmonbump',
                'version': '1.0.0',
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon bump'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            self.nn(await core.getStormDmon(dmoniden))

            # Re-add the package; dmon should be bumped not duplicated
            pkg['version'] = '1.0.1'
            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            self.nn(await core.getStormDmon(dmoniden))

        # Dmon kept with --uninstall-keep dmons
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            pkg = {
                'name': 'test.dmonkeep',
                'version': '1.0.0',
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon keep'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            self.nn(await core.getStormDmon(dmoniden))

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.dmonkeep', uninstall=True, keep=('dmons',))
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.dmonkeep))'))
            self.nn(await core.getStormDmon(dmoniden))

        # Dmon already deleted before uninstall
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            pkg = {
                'name': 'test.dmonmissing',
                'version': '1.0.0',
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon missing'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            # Manually delete the dmon before uninstall
            await core.delStormDmon(dmoniden)
            self.none(await core.getStormDmon(dmoniden))

            # Uninstall should not error on missing dmon
            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.dmonmissing', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.dmonmissing))'))

        # onuninstall storm error ($lib.raise) - storm err messages are logged but
        # the handler completes normally (storm errors don't abort the uninstall)
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.ondelfail',
                'version': '1.0.0',
                'onuninstall': {'query': '$lib.raise(FatalError, boom)'},
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'onuninstall output') as stream:
                await core.callStorm('$lib.pkg.del(test.ondelfail, uninstall=$lib.true)')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            # Package should be deleted (storm errors don't abort uninstall)
            self.none(await core.callStorm('return($lib.pkg.get(test.ondelfail))'))

        # Package without onuninstall: auto-cleanup still runs
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.noondel',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.noondel).foo = bar')
            await core.callStorm('$lib.pkg.queues(test.noondel).add(q1).put(1)')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.callStorm('$lib.pkg.del(test.noondel, uninstall=$lib.true)')
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.noondel))'))
            self.none(await core.callStorm('return($lib.pkg.vars(test.noondel).foo)'))

            q = '$qs = () for $q in $lib.pkg.queues(test.noondel).list() { $qs.append($q) } return($qs)'
            self.len(0, await core.callStorm(q))

        # Bad onuninstall syntax rejected at add time
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.badsyntax',
                'version': '1.0.0',
                'onuninstall': {'query': '} invalid storm {'},
            }

            with self.raises(s_exc.BadSyntax):
                await core.addStormPkg(pkg)

        # Bad dmon storm syntax rejected at add time
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.baddmon',
                'version': '1.0.0',
                'dmons': [
                    {'iden': s_common.guid(), 'storm': '} invalid storm {', 'name': 'bad dmon'},
                ],
            }

            with self.raises(s_exc.BadSyntax):
                await core.addStormPkg(pkg)

        # Reboot survival: uninstall resumes after cortex restart
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                # Create a pkg with an onuninstall to simulate reboot during uninstall
                onuninstall = {'query': '$lib.print(onuninstall_resumed)'}
                pkg = {
                    'name': 'test.reboot',
                    'version': '1.0.0',
                    'onuninstall': onuninstall,
                }

                await core.addStormPkg(pkg)
                await core.callStorm('$lib.pkg.vars(test.reboot).foo = bar')

                # Manually persist the uninstalling state (simulating mid-uninstall restart)
                pkgvars = core._getStormPkgVarKV('test.reboot')
                pkgvars.set('uninstalling', {'keep': [], 'time': s_common.now()})

            # Reopen the cortex - it should resume the uninstall
            async with self.getTestCore(dirn=dirn) as core:

                donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
                await donewaiter.wait(timeout=30)

                # Pkg should have been removed during startup
                self.none(await core.callStorm('return($lib.pkg.get(test.reboot))'))
                self.none(await core.callStorm('return($lib.pkg.vars(test.reboot).foo)'))

        # Running onload is cancelled before onuninstall runs
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.cancelonload',
                'version': '1.0.0',
                'onload': '$lib.time.sleep(60)',
                'onuninstall': {'query': '$lib.print(onuninstall_after_cancel)'},
            }

            await core.addStormPkg(pkg)

            # The onload should be running now (sleeping for 60s)
            self.isin('test.cancelonload', core._pkgOnloadTasks)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'onuninstall_after_cancel') as stream:
                await core.delStormPkg('test.cancelonload', uninstall=True)
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            # Onload task should be gone
            self.notin('test.cancelonload', core._pkgOnloadTasks)

            # Package should be deleted
            self.none(await core.callStorm('return($lib.pkg.get(test.cancelonload))'))

        # Plain pkg.del (no --uninstall) works as before, no onuninstall
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            onuninstall = {'query': '$lib.print(should_not_run)'}
            pkg = {
                'name': 'test.plaindelete',
                'version': '1.0.0',
                'onuninstall': onuninstall,
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon plaindel'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            await core.callStorm('$lib.pkg.vars(test.plaindelete).v = 1')

            self.nn(await core.getStormDmon(dmoniden))

            msgs = await core.stormlist('pkg.del test.plaindelete')
            self.stormIsInPrint('Removing package: test.plaindelete', msgs)
            self.stormNotInPrint('should_not_run', msgs)

            self.none(await core.callStorm('return($lib.pkg.get(test.plaindelete))'))

            # Dmons are disabled (not deleted) on plain delete
            ddef = await core.getStormDmon(dmoniden)
            self.nn(ddef)
            self.true(ddef.get('enabled') is False)

            # Pkg vars are NOT cleaned (plain delete does not auto-cleanup)
            self.eq('1', await core.callStorm('return($lib.pkg.vars(test.plaindelete).v)'))

        # Plain pkg.del cancels running onload/init tasks
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.delcancelonload',
                'version': '1.0.0',
                'onload': '$lib.time.sleep(60)',
            }

            await core.addStormPkg(pkg)

            # The onload should be running now (sleeping for 60s)
            self.isin('test.delcancelonload', core._pkgOnloadTasks)

            await core.delStormPkg('test.delcancelonload')

            # Onload task should be cancelled and gone
            self.notin('test.delcancelonload', core._pkgOnloadTasks)

            # Package should be deleted
            self.none(await core.callStorm('return($lib.pkg.get(test.delcancelonload))'))

        # Safe mode: entire uninstall skipped, package stays
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.safemode',
                'version': '1.0.0',
                'onuninstall': {'query': '$lib.print(should_not_run_in_safemode)'},
            }

            await core.addStormPkg(pkg)

            core.safemode = True

            with self.getAsyncLoggerStream('synapse.cortex', 'safemode is active') as stream:
                await core.callStorm('$lib.pkg.del(test.safemode, uninstall=$lib.true)')
                self.true(await stream.wait(timeout=30))

            # Package should still exist (safemode skips entire uninstall)
            self.nn(await core.callStorm('return($lib.pkg.get(test.safemode))'))

            # Package should still be in uninstalling state
            pkgvars = core._getStormPkgVarKV('test.safemode')
            self.nn(pkgvars.get('uninstalling'))

            core.safemode = False

        # Double uninstall: error if already uninstalling
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.doubleuninst',
                'version': '1.0.0',
                'onuninstall': {'query': '$lib.time.sleep(3)'},
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            await core.callStorm('$lib.pkg.del(test.doubleuninst, uninstall=$lib.true)')

            # The _uninstalling state is set synchronously via nexus, so it is
            # immediately visible for the duplicate check.
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('test.doubleuninst', uninstall=True)

            await donewaiter.wait(timeout=30)

        # $lib.pkg.del() with uninstall path works
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.libuninstall',
                'version': '1.0.0',
                'onuninstall': {'query': '$lib.print(lib_uninstall_onuninstall)'},
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'lib_uninstall_onuninstall') as stream:
                await core.callStorm('$lib.pkg.del(test.libuninstall, uninstall=$lib.true)')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.libuninstall))'))

        # CoreApi delStormPkg with uninstall=True works
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.coreapi',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.coreapi).x = 1')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.coreapi', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.coreapi))'))
            self.none(await core.callStorm('return($lib.pkg.vars(test.coreapi).x)'))

    async def test_stormlib_pkg_list_status(self):

        # pkg.list shows uninstalling status
        async with self.getTestCore() as core:

            pkg_normal = {
                'name': 'test.normal',
                'version': '1.0.0',
            }
            await core.addStormPkg(pkg_normal)

            pkg_uninst = {
                'name': 'test.uninst',
                'version': '2.0.0',
            }
            await core.addStormPkg(pkg_uninst)

            # Manually set the uninstalling state via pkgvars (no keep)
            pkgvars = core._getStormPkgVarKV('test.uninst')
            pkgvars.set('uninstalling', {'keep': [], 'time': s_common.now()})

            pkg_keep = {
                'name': 'test.keepitems',
                'version': '3.0.0',
            }
            await core.addStormPkg(pkg_keep)

            # Manually set the uninstalling state with keep items
            pkgvars = core._getStormPkgVarKV('test.keepitems')
            pkgvars.set('uninstalling', {'keep': ['variables', 'queues'], 'time': s_common.now()})

            msgs = await core.stormlist('pkg.list')

            # Normal package should not show "uninstalling"
            self.stormIsInPrint('test.normal 1.0.0', msgs, whitespace=False)
            self.stormNotInPrint('test.normal 1.0.0 uninstalling', msgs, whitespace=False)

            # Package with uninstalling and no keep should show "uninstalling"
            self.stormIsInPrint('test.uninst 2.0.0 uninstalling', msgs, whitespace=False)
            self.stormNotInPrint('test.uninst 2.0.0 uninstalling (keep', msgs, whitespace=False)

            # Package with uninstalling and keep items should show "uninstalling (keeping ...)"
            self.stormIsInPrint('test.keepitems 3.0.0 uninstalling (keeping variables, queues)', msgs, whitespace=False)

    async def test_stormlib_pkg_install_blocked_during_uninstall(self):

        # Block install during uninstall
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.blockinstall',
                'version': '1.0.0',
                'onuninstall': {'query': '$lib.time.sleep(5)'},
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            await core.callStorm('$lib.pkg.del(test.blockinstall, uninstall=$lib.true)')

            # Attempt to install same package while uninstall is in progress
            with self.raises(s_exc.BadArg) as cm:
                await core.addStormPkg(pkg)

            self.isin('currently being uninstalled', cm.exception.get('mesg'))

            await donewaiter.wait(timeout=30)

            # After uninstall completes, install should succeed
            await core.addStormPkg(pkg)
            self.nn(await core.callStorm('return($lib.pkg.get(test.blockinstall))'))

    async def test_stormlib_pkg_uninstall_coreapi(self):

        # CoreApi.delStormPkg with uninstall=True via telepath proxy
        async with self.getTestCoreAndProxy() as (core, prox):

            pkg = {
                'name': 'test.proxuninst',
                'version': '1.0.0',
            }

            await prox.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.proxuninst).v = 1')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await prox.delStormPkg('test.proxuninst', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.proxuninst))'))
            self.none(await core.callStorm('return($lib.pkg.vars(test.proxuninst).v)'))

    async def test_stormlib_pkg_uninstall_nosuchpkg(self):

        # delStormPkg with uninstall=True on nonexistent package raises NoSuchPkg
        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchPkg):
                await core.delStormPkg('test.doesnotexist', uninstall=True)

    async def test_stormlib_pkg_uninstall_nexus_replay(self):

        # _uninstallStormPkg early return when pkgdef is None (nexus replay edge case)
        async with self.getTestCore() as core:

            # Directly call the nexus handler with a nonexistent package name
            await core._uninstallStormPkg('test.nonexistent', ())

    async def test_stormlib_pkg_onuninstall_warn(self):

        # onuninstall handler that emits a warn message
        async with self.getTestCore() as core:

            onuninstall = {'query': '$lib.warn(warnmsg)'}
            pkg = {
                'name': 'test.ondelwarn',
                'version': '1.0.0',
                'onuninstall': onuninstall,
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'onuninstall output: warnmsg') as stream:
                await core.delStormPkg('test.ondelwarn', uninstall=True)
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.ondelwarn))'))

    async def test_stormlib_pkg_onuninstall_exception(self):

        # onuninstall where self.storm() raises a Python exception - aborts uninstall
        async with self.getTestCore() as core:

            onuninstall = {'query': '$lib.print(hello)'}
            pkg = {
                'name': 'test.ondelexc',
                'version': '1.0.0',
                'onuninstall': onuninstall,
            }

            await core.addStormPkg(pkg)

            real_storm = core.storm

            async def mock_storm(text, *args, **kwargs):
                if 'hello' in text:
                    raise RuntimeError('mock storm failure')
                async for mesg in real_storm(text, *args, **kwargs):
                    yield mesg

            with mock.patch.object(core, 'storm', mock_storm):
                with self.getAsyncLoggerStream('synapse.cortex', 'onuninstall failed for package') as stream:
                    await core.delStormPkg('test.ondelexc', uninstall=True)
                    self.true(await stream.wait(timeout=30))

            # Package should still exist (uninstall aborted on exception)
            self.nn(await core.callStorm('return($lib.pkg.get(test.ondelexc))'))

            # Package should still be in uninstalling state
            pkgvars = core._getStormPkgVarKV('test.ondelexc')
            self.nn(pkgvars.get('uninstalling'))

    async def test_stormlib_pkg_onuninstall_cancelled(self):

        # onuninstall where the task is cancelled during execution
        async with self.getTestCore() as core:

            onuninstall = {'query': '$lib.time.sleep(60)'}
            pkg = {
                'name': 'test.ondelcancel',
                'version': '1.0.0',
                'onuninstall': onuninstall,
            }

            await core.addStormPkg(pkg)

            real_storm = core.storm

            async def mock_storm(text, *args, **kwargs):
                if '$lib.time.sleep' in text:
                    raise asyncio.CancelledError()
                async for mesg in real_storm(text, *args, **kwargs):
                    yield mesg

            with mock.patch.object(core, 'storm', mock_storm):
                with self.raises(asyncio.CancelledError):
                    await core._runStormPkgOnuninstall(pkg, ())

    async def test_stormlib_pkg_uninstall_keep_validation(self):

        # $lib.pkg.del with keep as non-list raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.pkg.del(test.keepvalid, uninstall=$lib.true, keep=notalist)')

            self.isin('must be a list', cm.exception.get('mesg'))

        # $lib.pkg.del with keep containing non-string raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid2',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.pkg.del(test.keepvalid2, uninstall=$lib.true, keep=((1),))')

        # $lib.pkg.del with unknown keep value raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid3',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.pkg.del(test.keepvalid3, uninstall=$lib.true, keep=(newp,))')

            self.isin('Invalid keep item', cm.exception.get('mesg'))

        # --uninstall-keep with unknown value via Storm command raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid4',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            msgs = await core.stormlist('pkg.del test.keepvalid4 --uninstall --uninstall-keep (newp,)')
            self.stormIsInErr('Invalid keep item', msgs)

        # core API with unknown keep value raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid5',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.delStormPkg('test.keepvalid5', uninstall=True, keep=['newp'])

            self.isin('Invalid keep item', cm.exception.get('mesg'))

    async def test_stormlib_pkg_model(self):

        async with self.getTestCore() as core:

            # Valid model with all four sub-keys
            pkg = {
                'name': 'test.model',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:mytype': {
                            'type': 'str',
                            'typeopts': {'lower': True},
                            'typeinfo': {'doc': 'A test type.'},
                        },
                    },
                    'forms': {
                        '_test:myform': {
                            'type': 'str',
                            'typeopts': {'lower': True},
                            'typeinfo': {'doc': 'A test form.'},
                        },
                    },
                    'props': {
                        '_test:myprop': {
                            'forms': ['_test:myform'],
                            'typedef': ['str', {'lower': True}],
                            'propinfo': {'doc': 'A test prop.'},
                        },
                    },
                    'tagprops': {
                        '_test:mytagprop': {
                            'typedef': ['int', {'min': 0}],
                            'propinfo': {'doc': 'A test tag prop.'},
                        },
                    },
                },
            }

            await core.addStormPkg(pkg)

            pkgdef = await core.callStorm('return($lib.pkg.get(test.model))')
            self.nn(pkgdef)
            self.nn(pkgdef.get('extmodel'))
            self.eq(pkgdef['extmodel']['types']['_test:mytype']['type'], 'str')
            self.eq(pkgdef['extmodel']['forms']['_test:myform']['type'], 'str')
            self.eq(pkgdef['extmodel']['props']['_test:myprop']['forms'], ['_test:myform'])
            self.eq(pkgdef['extmodel']['props']['_test:myprop']['typedef'], ['str', {'lower': True}])
            self.eq(pkgdef['extmodel']['tagprops']['_test:mytagprop']['typedef'], ['int', {'min': 0}])

            # Valid model with only some sub-keys
            pkg2 = {
                'name': 'test.model2',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:mytype2': {
                            'type': 'int',
                        },
                    },
                },
            }

            await core.addStormPkg(pkg2)

            pkgdef2 = await core.callStorm('return($lib.pkg.get(test.model2))')
            self.nn(pkgdef2)
            self.eq(pkgdef2['extmodel']['types']['_test:mytype2']['type'], 'int')

            # Empty model is valid
            pkg3 = {
                'name': 'test.model3',
                'version': '1.0.0',
                'extmodel': {},
            }

            await core.addStormPkg(pkg3)

            # Invalid: type entry missing required 'type' field
            pkg4 = {
                'name': 'test.model4',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:bad': {
                            'typeopts': {'lower': True},
                        },
                    },
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg4)

            # Invalid: form entry missing required 'type' field
            pkg5 = {
                'name': 'test.model5',
                'version': '1.0.0',
                'extmodel': {
                    'forms': {
                        '_test:bad': {
                            'typeinfo': {'doc': 'Missing type field.'},
                        },
                    },
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg5)

            # Invalid: prop entry missing required 'forms' and 'typedef'
            pkg6 = {
                'name': 'test.model6',
                'version': '1.0.0',
                'extmodel': {
                    'props': {
                        '_test:bad': {
                            'propinfo': {'doc': 'Missing required fields.'},
                        },
                    },
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg6)

            # Invalid: tagprop entry missing required 'typedef'
            pkg7 = {
                'name': 'test.model7',
                'version': '1.0.0',
                'extmodel': {
                    'tagprops': {
                        '_test:bad': {
                            'propinfo': {'doc': 'Missing typedef.'},
                        },
                    },
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg7)

            # Invalid: extra property in type entry
            pkg8 = {
                'name': 'test.model8',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:bad': {
                            'type': 'str',
                            'newp': 'invalid',
                        },
                    },
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg8)

            # Invalid: extra property in model
            pkg9 = {
                'name': 'test.model9',
                'version': '1.0.0',
                'extmodel': {
                    'newp': {},
                },
            }

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(pkg9)

            # Also test direct schema validation
            s_schemas.reqValidPkgdef({
                'name': 'test.direct',
                'version': '0.0.1',
                'extmodel': {
                    'types': {
                        '_test:dtype': {'type': 'str'},
                    },
                },
            })

    async def test_stormlib_pkg_del_dmon_already_deleted(self):

        # Plain pkg.del when the dmon was already manually deleted
        async with self.getTestCore() as core:

            dmoniden = s_common.guid()
            pkg = {
                'name': 'test.deldmonmissing',
                'version': '1.0.0',
                'dmons': [
                    {'iden': dmoniden, 'storm': '$lib.time.sleep(1000)', 'name': 'test dmon delmissing'},
                ],
            }

            loadwaiter = core.waiter(1, 'core:pkg:onload:complete')
            await core.addStormPkg(pkg)
            await loadwaiter.wait(timeout=30)

            # Manually delete the dmon before plain pkg.del
            await core.delStormDmon(dmoniden)
            self.none(await core.getStormDmon(dmoniden))

            # Plain delete should not error on missing dmon
            await core.delStormPkg('test.deldmonmissing')
            self.none(await core.callStorm('return($lib.pkg.get(test.deldmonmissing))'))

    async def test_stormlib_pkg_uninstall_model_cleanup(self):

        # Uninstall a package with model definitions triggers model and data cleanup
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.modelclean',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:cleantype': {'type': 'str'},
                    },
                    'forms': {
                        '_test:cleanform': {'type': 'str'},
                    },
                    'props': {
                        '_test:cleanprop': {
                            'forms': ['_test:cleanform'],
                            'typedef': ['str', {}],
                        },
                    },
                    'tagprops': {
                        '_test:cleantagprop': {
                            'typedef': ['int', {}],
                        },
                    },
                },
            }

            await core.addStormPkg(pkg)

            # Register the ext model elements and create data
            await core.addType('_test:cleantype', 'str', {}, {})
            await core.addForm('_test:cleanform', 'str', {}, {})
            await core.addFormProp('_test:cleanform', '_test:cleanprop', ('str', {}), {})
            await core.addTagProp('_test:cleantagprop', ('int', {}), {})

            # Create nodes with the ext model
            await core.nodes('[_test:cleanform=foo :_test:cleanprop=bar +#test:_test:cleantagprop=42]')
            self.len(1, await core.nodes('_test:cleanform'))

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.modelclean', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.modelclean))'))

            # Verify all data and model elements were cleaned up
            self.none(core.model.form('_test:cleanform'))
            self.none(core.model.type('_test:cleantype'))
            self.none(core.model.type('_test:cleanform'))

        # Uninstall with keep=model skips model cleanup
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.modelkeep',
                'version': '1.0.0',
                'extmodel': {
                    'types': {
                        '_test:keeptype': {'type': 'str'},
                    },
                },
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.modelkeep', uninstall=True, keep=('extmodel',))
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.modelkeep))'))

        # Uninstall a package with no model key at all
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.nomodel',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('test.nomodel', uninstall=True)
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.nomodel))'))
