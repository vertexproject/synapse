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

            pkg2 = {'name': 'hoho', 'version': '4.5.6', 'build': {'time': 1732017600000}}
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
            'onload': f'[ ps:contact={cont} ] $lib.print(teststring) $lib.warn(testwarn, key=valu) return($path.vars.newp)'
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
            self.len(1, await core.nodes(f'ps:contact={cont}'))

            evnts = await waiter.wait(timeout=4)
            exp = [
                ('core:pkg:onload:complete', {'pkg': 'testload'})
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
