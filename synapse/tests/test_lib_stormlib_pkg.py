import asyncio
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.httpapi as s_httpapi
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

        # Basic uninstall with ondel handler, pkg vars cleaned, queues cleaned, beholder events
        async with self.getTestCore() as core:

            ondel = '$lib.print(`ondel called keep={$keep}`)'
            pkg = {
                'name': 'test.uninstall',
                'version': '1.0.0',
                'ondel': ondel,
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

            ondelwaiter = core.waiter(1, 'core:pkg:ondel:complete')
            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'ondel called keep=') as stream:
                msgs = await core.stormlist('pkg.del test.uninstall --uninstall')
                self.stormIsInPrint('Uninstalling package: test.uninstall', msgs)
                self.true(await stream.wait(timeout=30))

            evnts = await ondelwaiter.wait(timeout=30)
            self.ge(len(evnts), 1)
            self.eq(evnts[0][0], 'core:pkg:ondel:complete')

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

        # ondel receives keep set via $lib.pkg.uninstall
        async with self.getTestCore() as core:

            ondel = 'if (not $keep) { $lib.print(keep_empty) } else { $lib.print(`keep={$keep}`) }'
            pkg = {
                'name': 'test.keepset',
                'version': '1.0.0',
                'ondel': ondel,
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.keepset).myvar = hello')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'keep=') as stream:
                await core.callStorm('$lib.pkg.uninstall(test.keepset, keep=(pkg-vars,))')
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

            msgs = await core.stormlist('pkg.del test.keepqueues --uninstall --uninstall-keep queues')
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
            await core.uninstallStormPkg('test.keeppkgvars', keep=('pkg-vars',))
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
            await core.uninstallStormPkg('test.vaultclean')
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
            await core.uninstallStormPkg('test.vaultkeep', keep=('vaults',))
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.vaultkeep))'))
            self.nn(core.getVault(viden))

        # ondel failure does NOT prevent deletion
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.ondelfail',
                'version': '1.0.0',
                'ondel': '$lib.raise(FatalError, boom)',
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'ondel output') as stream:
                await core.callStorm('$lib.pkg.uninstall(test.ondelfail)')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            # Package should still be deleted despite ondel failure
            self.none(await core.callStorm('return($lib.pkg.get(test.ondelfail))'))

        # Package without ondel: auto-cleanup still runs
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.noondel',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.noondel).foo = bar')
            await core.callStorm('$lib.pkg.queues(test.noondel).add(q1).put(1)')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.callStorm('$lib.pkg.uninstall(test.noondel)')
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.noondel))'))
            self.none(await core.callStorm('return($lib.pkg.vars(test.noondel).foo)'))

            q = '$qs = () for $q in $lib.pkg.queues(test.noondel).list() { $qs.append($q) } return($qs)'
            self.len(0, await core.callStorm(q))

        # Bad ondel syntax rejected at add time
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.badsyntax',
                'version': '1.0.0',
                'ondel': '} invalid storm {',
            }

            with self.raises(s_exc.BadSyntax):
                await core.addStormPkg(pkg)

        # Reboot survival: uninstall resumes after cortex restart
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                # Create a pkg with a slow ondel to simulate reboot during uninstall
                ondel = '$lib.print(ondel_resumed)'
                pkg = {
                    'name': 'test.reboot',
                    'version': '1.0.0',
                    'ondel': ondel,
                }

                await core.addStormPkg(pkg)
                await core.callStorm('$lib.pkg.vars(test.reboot).foo = bar')

                # Manually persist the uninstalling state (simulating mid-uninstall restart)
                pkgdef = core.pkgdefs.get('test.reboot')
                pkgdef['_uninstalling'] = {'keep': [], 'time': s_common.now()}
                core.pkgdefs.set('test.reboot', pkgdef)
                core.stormpkgs['test.reboot'] = pkgdef

            # Reopen the cortex - it should resume the uninstall
            async with self.getTestCore(dirn=dirn) as core:

                donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
                await donewaiter.wait(timeout=30)

                # Pkg should have been removed during startup
                self.none(await core.callStorm('return($lib.pkg.get(test.reboot))'))
                self.none(await core.callStorm('return($lib.pkg.vars(test.reboot).foo)'))

        # Running onload is cancelled before ondel runs
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.cancelonload',
                'version': '1.0.0',
                'onload': '$lib.time.sleep(60)',
                'ondel': '$lib.print(ondel_after_cancel)',
            }

            await core.addStormPkg(pkg)

            # The onload should be running now (sleeping for 60s)
            self.isin('test.cancelonload', core._pkgOnloadTasks)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'ondel_after_cancel') as stream:
                await core.uninstallStormPkg('test.cancelonload')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            # Onload task should be gone
            self.notin('test.cancelonload', core._pkgOnloadTasks)

            # Package should be deleted
            self.none(await core.callStorm('return($lib.pkg.get(test.cancelonload))'))

        # Plain pkg.del (no --uninstall) works as before, no ondel
        async with self.getTestCore() as core:

            ondel = '$lib.print(should_not_run)'
            pkg = {
                'name': 'test.plaindelete',
                'version': '1.0.0',
                'ondel': ondel,
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.plaindelete).v = 1')

            msgs = await core.stormlist('pkg.del test.plaindelete')
            self.stormIsInPrint('Removing package: test.plaindelete', msgs)
            self.stormNotInPrint('should_not_run', msgs)

            self.none(await core.callStorm('return($lib.pkg.get(test.plaindelete))'))

            # Pkg vars are NOT cleaned (plain delete does not auto-cleanup)
            self.eq('1', await core.callStorm('return($lib.pkg.vars(test.plaindelete).v)'))

        # Safe mode: ondel skipped
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.safemode',
                'version': '1.0.0',
                'ondel': '$lib.print(should_not_run_in_safemode)',
            }

            await core.addStormPkg(pkg)

            core.safemode = True

            skipwaiter = core.waiter(1, 'core:pkg:ondel:skipped')
            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.callStorm('$lib.pkg.uninstall(test.safemode)')
            evnts = await skipwaiter.wait(timeout=30)
            self.ge(len(evnts), 1)

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.safemode))'))

            core.safemode = False

        # Double uninstall: error if already uninstalling
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.doubleuninst',
                'version': '1.0.0',
                'ondel': '$lib.time.sleep(3)',
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            await core.callStorm('$lib.pkg.uninstall(test.doubleuninst)')

            # The _uninstalling state is set synchronously via nexus, so it is
            # immediately visible for the duplicate check.
            with self.raises(s_exc.BadArg):
                await core.uninstallStormPkg('test.doubleuninst')

            await donewaiter.wait(timeout=30)

        # $lib.pkg.uninstall() path works
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.libuninstall',
                'version': '1.0.0',
                'ondel': '$lib.print(lib_uninstall_ondel)',
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'lib_uninstall_ondel') as stream:
                await core.callStorm('$lib.pkg.uninstall(test.libuninstall)')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.libuninstall))'))

        # CoreApi uninstallStormPkg works
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.coreapi',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.coreapi).x = 1')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.uninstallStormPkg('test.coreapi')
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

            # Manually set the _uninstalling state (no keep)
            pkgdef = core.pkgdefs.get('test.uninst')
            pkgdef['_uninstalling'] = {'keep': None, 'time': s_common.now()}
            core.pkgdefs.set('test.uninst', pkgdef)
            core.stormpkgs['test.uninst'] = pkgdef

            pkg_keep = {
                'name': 'test.keepitems',
                'version': '3.0.0',
            }
            await core.addStormPkg(pkg_keep)

            # Manually set the _uninstalling state with keep items
            pkgdef = core.pkgdefs.get('test.keepitems')
            pkgdef['_uninstalling'] = {'keep': ['pkg-vars', 'queues'], 'time': s_common.now()}
            core.pkgdefs.set('test.keepitems', pkgdef)
            core.stormpkgs['test.keepitems'] = pkgdef

            msgs = await core.stormlist('pkg.list')

            # Normal package should not show "uninstalling"
            for msg in msgs:
                if msg[0] == 'print' and 'test.normal' in msg[1].get('mesg', ''):
                    self.notin('uninstalling', msg[1]['mesg'])
                    break

            # Package with _uninstalling and no keep should show "uninstalling"
            found_uninst = False
            for msg in msgs:
                if msg[0] == 'print' and 'test.uninst' in msg[1].get('mesg', ''):
                    mesg = msg[1]['mesg']
                    self.isin('uninstalling', mesg)
                    self.notin('keeping', mesg)
                    found_uninst = True
                    break

            self.true(found_uninst)

            # Package with _uninstalling and keep items should show "uninstalling (keeping ...)"
            found_keep = False
            for msg in msgs:
                if msg[0] == 'print' and 'test.keepitems' in msg[1].get('mesg', ''):
                    mesg = msg[1]['mesg']
                    self.isin('uninstalling (keeping pkg-vars, queues)', mesg)
                    found_keep = True
                    break

            self.true(found_keep)

    async def test_stormlib_pkg_install_blocked_during_uninstall(self):

        # Block install during uninstall
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.blockinstall',
                'version': '1.0.0',
                'ondel': '$lib.time.sleep(5)',
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            await core.callStorm('$lib.pkg.uninstall(test.blockinstall)')

            # Attempt to install same package while uninstall is in progress
            with self.raises(s_exc.BadArg) as cm:
                await core.addStormPkg(pkg)

            self.isin('currently being uninstalled', cm.exception.get('mesg'))

            await donewaiter.wait(timeout=30)

            # After uninstall completes, install should succeed
            await core.addStormPkg(pkg)
            self.nn(await core.callStorm('return($lib.pkg.get(test.blockinstall))'))

    async def test_stormlib_pkg_uninstall_coreapi(self):

        # CoreApi.uninstallStormPkg via telepath proxy
        async with self.getTestCoreAndProxy() as (core, prox):

            pkg = {
                'name': 'test.proxuninst',
                'version': '1.0.0',
            }

            await prox.addStormPkg(pkg)
            await core.callStorm('$lib.pkg.vars(test.proxuninst).v = 1')

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await prox.uninstallStormPkg('test.proxuninst')
            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.proxuninst))'))
            self.none(await core.callStorm('return($lib.pkg.vars(test.proxuninst).v)'))

    async def test_stormlib_pkg_uninstall_nosuchpkg(self):

        # uninstallStormPkg on nonexistent package raises NoSuchPkg
        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchPkg):
                await core.uninstallStormPkg('test.doesnotexist')

    async def test_stormlib_pkg_uninstall_nexus_replay(self):

        # _uninstallStormPkg early return when pkgdef is None (nexus replay edge case)
        async with self.getTestCore() as core:

            # Directly call the nexus handler with a nonexistent package name
            await core._uninstallStormPkg('test.nonexistent', None)

    async def test_stormlib_pkg_ondel_warn(self):

        # ondel handler that emits a warn message
        async with self.getTestCore() as core:

            ondel = '$lib.warn(warnmsg)'
            pkg = {
                'name': 'test.ondelwarn',
                'version': '1.0.0',
                'ondel': ondel,
            }

            await core.addStormPkg(pkg)

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with self.getAsyncLoggerStream('synapse.cortex', 'ondel output: warnmsg') as stream:
                await core.uninstallStormPkg('test.ondelwarn')
                self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.ondelwarn))'))

    async def test_stormlib_pkg_ondel_exception(self):

        # ondel where self.storm() raises a Python exception (not a storm error message)
        async with self.getTestCore() as core:

            ondel = '$lib.print(hello)'
            pkg = {
                'name': 'test.ondelexc',
                'version': '1.0.0',
                'ondel': ondel,
            }

            await core.addStormPkg(pkg)

            real_storm = core.storm

            async def mock_storm(text, *args, **kwargs):
                if 'hello' in text:
                    raise RuntimeError('mock storm failure')
                async for mesg in real_storm(text, *args, **kwargs):
                    yield mesg

            donewaiter = core.waiter(1, 'core:pkg:uninstall:complete')

            with mock.patch.object(core, 'storm', mock_storm):
                with self.getAsyncLoggerStream('synapse.cortex', 'ondel failed for package') as stream:
                    await core.uninstallStormPkg('test.ondelexc')
                    self.true(await stream.wait(timeout=30))

            await donewaiter.wait(timeout=30)

            self.none(await core.callStorm('return($lib.pkg.get(test.ondelexc))'))

    async def test_stormlib_pkg_ondel_cancelled(self):

        # ondel where the task is cancelled during execution
        async with self.getTestCore() as core:

            ondel = '$lib.time.sleep(60)'
            pkg = {
                'name': 'test.ondelcancel',
                'version': '1.0.0',
                'ondel': ondel,
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
                    await core._runStormPkgOndel(pkg, None)

    async def test_stormlib_pkg_uninstall_keep_validation(self):

        # $lib.pkg.uninstall with keep as non-list raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.pkg.uninstall(test.keepvalid, keep=notalist)')

            self.isin('must be a list', cm.exception.get('mesg'))

        # $lib.pkg.uninstall with keep containing non-string raises BadArg
        async with self.getTestCore() as core:

            pkg = {
                'name': 'test.keepvalid2',
                'version': '1.0.0',
            }

            await core.addStormPkg(pkg)

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.pkg.uninstall(test.keepvalid2, keep=((1),))')
