import asyncio

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
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
            self.true(await core.hasStormPkg('haha'))
            self.false(await core.hasStormPkg('newp'))

            await core.delStormPkg('haha')
            self.none(await core.callStorm('return($lib.pkg.get(haha))'))
            self.false(await core.callStorm('return($lib.pkg.has(haha))'))
            self.false(await core.hasStormPkg('haha'))

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
                'conflicts': {
                    'foobar': {},
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
                'conflicts': {
                    'foobar': {'version': '>=1.0.0', 'desc': 'foo'},
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
                'dependencies': {
                    'foobar': {'version': '>=2.0.0,<3.0.0'},
                }
            }

            with self.raises(s_exc.StormPkgRequires) as cm:
                await core.addStormPkg(pkgdef)
            self.isin('bazfaz requirement foobar>=2.0.0,<3.0.0 is currently unmet', str(cm.exception))

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'desc': None,
                     'ok': False, 'actual': '1.2.3', 'optional': False},
                ),
                'conflicts': ()
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'dependencies': {
                    'foobar': {'version': '>=2.0.0,<3.0.0', 'optional': True},
                }
            }

            with self.getLoggerStream('synapse.cortex') as stream:
                await core.addStormPkg(pkgdef)
                await stream.expect('bazfaz optional requirement', timeout=1)

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
                'dependencies': {
                    'lolzlolz': {'version': '>=1.0.0,<2.0.0', 'desc': 'lol'},
                },
                'conflicts': {
                    'foobar': {'version': '>=3.0.0'},
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'lolzlolz', 'version': '>=1.0.0,<2.0.0', 'desc': 'lol', 'ok': True, 'actual': '1.2.3',
                     'optional': False},
                ),
                'conflicts': (
                    {'name': 'foobar', 'version': '>=3.0.0', 'desc': None, 'ok': True, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'zoinkszoinks',
                'version': '2.2.2',
                'dependencies': {
                    'newpnewp': {'version': '1.2.3', 'optional': True},
                },
                'conflicts': {
                    'newpnewp': {},
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'newpnewp', 'version': '1.2.3', 'desc': None, 'ok': False, 'actual': None,
                     'optional': True},
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
            'onload': f'[ entity:contact={cont} ] $lib.print(teststring) $lib.warn(testwarn) return($path.vars.newp)'
        }
        class PkgHandler(s_httpapi.Handler):

            async def get(self, name):
                assert self.request.headers.get('X-Synapse-Version') == s_version.version

                if name == 'notok':
                    self.sendRestErr('FooBar', 'baz faz')
                    return

                self.sendRestRetn(pkg)

        class PkgHandlerRaw(s_httpapi.Handler):
            async def get(self, name):
                assert self.request.headers.get('X-Synapse-Version') == s_version.version

                self.set_header('Content-Type', 'application/json')
                return self.write(pkg)

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v3/pkgtest/(.*)', PkgHandler, {'cell': core})
            core.addHttpApi('/api/v3/pkgtestraw/(.*)', PkgHandlerRaw, {'cell': core})
            port = (await core.addHttpsPort(0, host='127.0.0.1'))[1]

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v3/newp/newp')
            self.stormIsInWarn('pkg.load got HTTP code: 404', msgs)

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v3/pkgtest/notok')
            self.stormIsInWarn('pkg.load got JSON error: FooBar', msgs)

            # onload will on fire once. all other pkg.load events will effectively bounce
            # because the pkg hasn't changed so no loading occurs
            waiter = core.waiter(1, 'core:pkg:onload:complete')

            with self.getLoggerStream('synapse.cortex') as stream:
                msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v3/pkgtest/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

                msgs = await core.stormlist(f'pkg.load --ssl-noverify --raw https://127.0.0.1:{port}/api/v3/pkgtestraw/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

            buf = stream.getvalue()
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

                # nexus no-op: set/pop must not emit entries when value is unchanged or key is absent

                ind = core.nexsroot.nexslog.index()

                await core.setStormPkgVar('pkg0', 'nxtest', 1)
                self.eq(ind + 1, core.nexsroot.nexslog.index())

                await core.setStormPkgVar('pkg0', 'nxtest', 1)
                self.eq(ind + 1, core.nexsroot.nexslog.index())

                await core.setStormPkgVar('pkg0', 'nxtest', 2)
                self.eq(ind + 2, core.nexsroot.nexslog.index())

                await core.popStormPkgVar('pkg0', 'missing')
                self.eq(ind + 2, core.nexsroot.nexslog.index())

                await core.popStormPkgVar('pkg0', 'nxtest')
                self.eq(ind + 3, core.nexsroot.nexslog.index())

                retn = await core.popStormPkgVar('pkg0', 'missing', default='fallback')
                self.eq('fallback', retn)
                self.eq(ind + 3, core.nexsroot.nexslog.index())

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

    async def test_stormlib_pkg_state(self):
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                lowuser = await core.addUser('lowuser')
                aslow = {'user': lowuser.get('iden')}
                await core.callStorm('auth.user.addrule lowuser node')

                # basic read

                self.none(await core.callStorm('return($lib.pkg.state(pkg0).bar)'))
                self.eq([], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.state(pkg0) { $kvs.append($kv) }
                    return($kvs)
                '''))

                # set state internally (not via Storm)
                await core.setStormPkgState('pkg0', 'bar', 'cat')
                await core.setStormPkgState('pkg0', 'baz', 'dog')
                await core.setStormPkgState('pkg1', 'bar', 'emu')
                await core.setStormPkgState('pkg1', 'baz', 'groot')

                self.eq('cat', await core.callStorm('return($lib.pkg.state(pkg0).bar)'))
                self.eq('dog', await core.callStorm('return($lib.pkg.state(pkg0).baz)'))
                self.eq('emu', await core.callStorm('return($lib.pkg.state(pkg1).bar)'))
                self.eq('groot', await core.callStorm('return($lib.pkg.state(pkg1).baz)'))

                self.sorteq([('bar', 'cat'), ('baz', 'dog')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.state(pkg0) { $kvs.append($kv) }
                    return($kvs)
                '''))

                # state is read-only from Storm: assignment must raise an error
                await self.asyncraises(s_exc.StormRuntimeError, core.callStorm('$lib.pkg.state(pkg0).bar = newval'))

                # perms: any user can get the state object, deref, and iter
                self.stormHasNoWarnErr(await core.nodes('$lib.print($lib.pkg.state(pkg0))', opts=aslow))
                self.eq('cat', await core.callStorm('return($lib.pkg.state(pkg0).bar)', opts=aslow))
                self.sorteq([('bar', 'cat'), ('baz', 'dog')], await core.callStorm('''
                    $kvs = ([])
                    for $kv in $lib.pkg.state(pkg0) { $kvs.append($kv) }
                    return($kvs)
                ''', opts=aslow))

                # state write is still denied from Storm
                await self.asyncraises(s_exc.StormRuntimeError, core.callStorm('$lib.pkg.state(pkg0).bar = newval', opts=aslow))

                # nexus no-op: set/pop must not emit entries when value is unchanged or key is absent

                ind = core.nexsroot.nexslog.index()

                await core.setStormPkgState('pkg0', 'nxtest', 1)
                self.eq(ind + 1, core.nexsroot.nexslog.index())

                await core.setStormPkgState('pkg0', 'nxtest', 1)
                self.eq(ind + 1, core.nexsroot.nexslog.index())

                await core.setStormPkgState('pkg0', 'nxtest', 2)
                self.eq(ind + 2, core.nexsroot.nexslog.index())

                await core.popStormPkgState('pkg0', 'missing')
                self.eq(ind + 2, core.nexsroot.nexslog.index())

                await core.popStormPkgState('pkg0', 'nxtest')
                self.eq(ind + 3, core.nexsroot.nexslog.index())

                retn = await core.popStormPkgState('pkg0', 'missing', default='fallback')
                self.eq('fallback', retn)
                self.eq(ind + 3, core.nexsroot.nexslog.index())

            async with self.getTestCore(dirn=dirn) as core:

                # data persists
                self.eq('cat', await core.callStorm('return($lib.pkg.state(pkg0).bar)'))
                self.eq('dog', await core.callStorm('return($lib.pkg.state(pkg0).baz)'))
                self.eq('emu', await core.callStorm('return($lib.pkg.state(pkg1).bar)'))
                self.eq('groot', await core.callStorm('return($lib.pkg.state(pkg1).baz)'))

    async def test_stormlib_pkg_uninstall(self):

        vtype = 'synapse-test:uninst'
        otype = 'synapse-test:other'

        pkgdef = {
            'name': 'unipkg',
            'version': '0.0.1',
            'vaults': {vtype: {'version': 1}},
            'perms': (
                {'perm': ('power-ups', 'unipkg', 'admin'), 'gate': 'cortex', 'desc': 'Admin unipkg.'},
            ),
            'uninstall': {
                'query': '''
                    $lib.print(`uninstalling`)
                    $lib.warn(`uninstalling loudly`)
                    $lib.globals.unikeep = $keep
                    if $lib.globals.unifail { $lib.raise(StormRuntimeError, 'uninstall newp') }
                    if $lib.globals.unislow { $lib.time.sleep(60) }
                ''',
                'keep': (
                    {'name': 'dmons', 'desc': 'Keep the dmons.'},
                ),
            },
        }

        async def waitgone(core, name):
            for _ in range(200):
                if not await core.hasStormPkg(name):
                    return True
                await asyncio.sleep(0.05)
            return False  # pragma: no cover

        async with self.getTestCoreAndProxy() as (core, prox):

            events = []

            async def onbehold(mesg):
                if mesg[1].get('event').startswith('pkg:'):
                    events.append(mesg[1].get('event'))

            core.on('cell:beholder', onbehold)

            # schema and keep name validation
            newp = {'name': 'newp', 'version': '0.0.1'}
            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg({**newp, 'uninstall': {'keep': ()}})
            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg({**newp, 'uninstall': {'query': '', 'x': 1}})
            with self.raises(s_exc.BadSyntax):
                await core.addStormPkg({**newp, 'uninstall': {'query': '$lib.('}})

            keep = ({'name': 'vaults', 'desc': 'reserved'},)
            with self.raises(s_exc.BadPkgDef):
                await core.addStormPkg({**newp, 'uninstall': {'query': '', 'keep': keep}})

            keep = ({'name': 'dup', 'desc': 'one'}, {'name': 'dup', 'desc': 'two'})
            with self.raises(s_exc.BadPkgDef):
                await core.addStormPkg({**newp, 'uninstall': {'query': '', 'keep': keep}})

            keep = ({'name': 'Bad Name', 'desc': 'x'},)
            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg({**newp, 'uninstall': {'query': '', 'keep': keep}})

            # an empty uninstall query is allowed and the keep list is optional
            await core.addStormPkg({**newp, 'uninstall': {'query': ''}})
            await core.callStorm('$lib.pkg.del(newp)')

            self.eq(['pkg:add', 'pkg:del'], events)
            events.clear()

            # state the cortex owns which an uninstall removes
            await core.addStormPkg(pkgdef)
            self.none(core.getStormPkgStatus('unipkg'))
            self.none(await core.callStorm('return($lib.pkg.status(unipkg))'))

            await core.setStormPkgVar('unipkg', 'foo', 'bar')
            await core.setStormPkgState('unipkg', 'baz', 'faz')
            await core.addStormPkgQueue('unipkg', 'uniq')
            await core.addStormPkgQueue('otherpkg', 'otherq')

            await core.addVaultType({'name': otype, 'version': 1})
            viden = await core.addVault({'name': 'univault', 'type': vtype, 'scope': None,
                                         'owner': core.auth.rootuser.iden, 'configs': {}, 'secrets': {}})
            oiden = await core.addVault({'name': 'othervault', 'type': otype, 'scope': None,
                                         'owner': core.auth.rootuser.iden, 'configs': {}, 'secrets': {}})

            # argument validation
            with self.raises(s_exc.NoSuchPkg):
                await core.delStormPkg('newp', uninstall=True)
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', keep=['dmons'])
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', uninstall=True, keep=['newp'])
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', uninstall=True, keep=[1])
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', uninstall=True, keep='dmons')
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', uninstall=True, keep=3)

            # a package which declares no vault types cannot keep vaults
            await core.addStormPkg({**newp, 'uninstall': {'query': ''}})
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('newp', uninstall=True, keep=['vaults'])
            await core.delStormPkg('newp')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.pkg.del(unipkg, uninstall=(true), keep=newp)')

            events.clear()
            self.nn(await core.callStorm('return($lib.pkg.get(unipkg))'))

            # a failed uninstall leaves the package installed and reports why
            await core.setStormVar('unifail', True)

            waiter = core.waiter(1, 'core:pkg:uninstall:failed')
            await core.delStormPkg('unipkg', uninstall=True, keep=['dmons'])
            self.nn(await waiter.wait(timeout=10))

            status = core.getStormPkgStatus('unipkg')
            self.eq('failed', status['status'])
            self.eq(['dmons'], status['keep'])
            self.isin('uninstall newp', status['mesg'])
            self.true(await core.hasStormPkg('unipkg'))
            self.eq('failed', await core.callStorm('return($lib.pkg.status(unipkg).status)'))
            self.eq(status, await prox.getStormPkgStatus('unipkg'))
            self.eq('bar', await core.getStormPkgVar('unipkg', 'foo'))

            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('uninstall failed', msgs)

            # a retry is allowed after a failure, and a replacement add or a plain delete abandons it
            await core.addStormPkg(pkgdef)
            self.none(core.getStormPkgStatus('unipkg'))
            self.true(await core.hasStormPkg('unipkg'))

            waiter = core.waiter(1, 'core:pkg:uninstall:failed')
            await core.delStormPkg('unipkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))
            self.eq('failed', core.getStormPkgStatus('unipkg')['status'])

            await core.delStormPkg('unipkg')
            self.none(core.getStormPkgStatus('unipkg'))
            self.false(await core.hasStormPkg('unipkg'))

            await core.addStormPkg(pkgdef)

            waiter = core.waiter(1, 'core:pkg:uninstall:failed')
            await core.delStormPkg('unipkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))

            # the retry succeeds and keeps what it was asked to keep
            await core.setStormVar('unifail', False)

            waiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('unipkg', uninstall=True, keep=['dmons', 'vaults', 'dmons'])
            self.nn(await waiter.wait(timeout=10))

            self.eq(['dmons', 'vaults'], await core.getStormVar('unikeep'))

            self.false(await core.hasStormPkg('unipkg'))
            self.none(core.getStormPkgStatus('unipkg'))
            self.none(await core.callStorm('return($lib.pkg.status(unipkg))'))
            self.eq([], [item async for item in core.iterStormPkgVars('unipkg')])
            self.eq([], [item async for item in core.iterStormPkgState('unipkg')])
            self.eq([], [item async for item in core.listStormPkgQueues('unipkg')])
            self.len(1, [item async for item in core.listStormPkgQueues('otherpkg')])
            self.nn(core.getVault(viden))
            self.nn(core.getVaultType(vtype))

            # without a keep list the vaults of the package vault types and the types are removed
            await core.addStormPkg(pkgdef)
            await core.setStormPkgVar('unipkg', 'foo', 'bar')

            waiter = core.waiter(1, 'core:pkg:uninstall:complete')
            msgs = await core.stormlist('pkg.del unipkg --uninstall')
            self.stormIsInWarn('UNINSTALLING unipkg', msgs)
            self.stormIsInPrint('Uninstall of unipkg started', msgs)
            self.nn(await waiter.wait(timeout=10))

            self.eq([], await core.getStormVar('unikeep'))
            self.none(core.getVault(viden))
            self.none(core.getVaultType(vtype))
            self.nn(core.getVault(oiden))
            self.nn(core.getVaultType(otype))
            self.eq([], [item async for item in core.iterStormPkgVars('unipkg')])

            msgs = await core.stormlist('pkg.del unipkg')
            self.stormIsInPrint('No package names match', msgs)

            self.eq([
                'pkg:uninstall:init', 'pkg:uninstall:fail',
                'pkg:add', 'pkg:uninstall:init', 'pkg:uninstall:fail', 'pkg:del',
                'pkg:add', 'pkg:uninstall:init', 'pkg:uninstall:fail',
                'pkg:uninstall:init', 'pkg:del', 'pkg:uninstall:fini',
                'pkg:add', 'pkg:uninstall:init', 'pkg:del', 'pkg:uninstall:fini',
            ], events)

            # the cortex refuses to add or uninstall a package which is being uninstalled
            await core.setStormVar('unislow', True)
            await core.addStormPkg(pkgdef)

            waiter = core.waiter(1, 'core:pkg:uninstall:start')
            await core.delStormPkg('unipkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))

            self.eq('uninstalling', core.getStormPkgStatus('unipkg')['status'])
            self.true(any(t.name == 'storm:pkg:uninstall:unipkg' for t in core.boss.tasks.values()))
            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('uninstalling', msgs)

            with self.raises(s_exc.BadArg):
                await core.addStormPkg(pkgdef)
            with self.raises(s_exc.BadArg):
                await core.delStormPkg('unipkg', uninstall=True)

            # the add handler also refuses, for an add which raced the check
            await core._addStormPkg({**pkgdef, 'version': '0.0.2'})
            self.eq('0.0.1', core.stormpkgs['unipkg']['version'])

            # and a plain delete is how an uninstall is abandoned
            task = core.stormpkguninsttask['unipkg']
            await core.delStormPkg('unipkg')
            await asyncio.wait([task], timeout=10)
            self.true(task.cancelled())
            self.none(core.getStormPkgStatus('unipkg'))
            self.false(await core.hasStormPkg('unipkg'))
            self.eq({}, core.stormpkguninsttask)

            await core.setStormVar('unislow', False)

            # a running onload is cancelled by a re-add, a delete and an uninstall
            onpkg = {'name': 'onpkg', 'version': '0.0.1', 'onload': '$lib.time.sleep(60)'}

            await core.addStormPkg(onpkg)
            first = core.stormpkgonload['onpkg']

            await core.addStormPkg({**onpkg, 'version': '0.0.2'})
            await asyncio.wait([first], timeout=10)
            self.true(first.cancelled())
            second = core.stormpkgonload['onpkg']
            self.ne(first, second)

            await core.delStormPkg('onpkg')
            await asyncio.wait([second], timeout=10)
            self.true(second.cancelled())
            self.notin('onpkg', core.stormpkgonload)

            await core.addStormPkg(onpkg)
            third = core.stormpkgonload['onpkg']

            waiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await core.delStormPkg('onpkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))
            self.true(third.cancelled())
            self.false(await core.hasStormPkg('onpkg'))

            # a finished onload is reaped
            await core.addStormPkg({'name': 'onpkg', 'version': '0.0.3', 'onload': '$lib.print(hi)'})
            for _ in range(100):
                if 'onpkg' not in core.stormpkgonload:
                    break
                await asyncio.sleep(0.05)
            self.notin('onpkg', core.stormpkgonload)

            # telepath and permissions
            await core.addStormPkg(pkgdef)

            lowuser = await core.addUser('lowuser')
            aslow = {'user': lowuser.get('iden')}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.pkg.del(unipkg, uninstall=(true))', opts=aslow)

            async with core.getLocalProxy(user='lowuser') as lowprox:
                with self.raises(s_exc.AuthDeny):
                    await lowprox.getStormPkgStatus('unipkg')

            waiter = core.waiter(1, 'core:pkg:uninstall:complete')
            await prox.delStormPkg('unipkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))
            self.false(await core.hasStormPkg('unipkg'))

            # an uninstall which raises is a failure too
            with mock.patch.object(core, 'storm', side_effect=Exception('boom')):
                await core.addStormPkg(pkgdef)

                waiter = core.waiter(1, 'core:pkg:uninstall:failed')
                await core.delStormPkg('unipkg', uninstall=True)
                self.nn(await waiter.wait(timeout=10))
                self.isin('boom', core.getStormPkgStatus('unipkg')['mesg'])

            # bad query options are a recorded failure rather than a stuck uninstall
            await core.delStormPkg('unipkg')
            badopts = {**pkgdef, 'uninstall': {**pkgdef['uninstall'], 'queryopts': {'vars': None}}}
            await core.addStormPkg(badopts)

            waiter = core.waiter(1, 'core:pkg:uninstall:failed')
            await core.delStormPkg('unipkg', uninstall=True)
            self.nn(await waiter.wait(timeout=10))
            status = core.getStormPkgStatus('unipkg')
            self.eq('failed', status['status'])
            self.isin('TypeError', status['mesg'])

            # uninstall and failure for a package which was removed meanwhile are ignored
            await core.delStormPkg('unipkg')
            self.none(await core._uninstStormPkg('unipkg', [], s_common.now()))
            self.none(await core._failStormPkgUninstall('unipkg', 'newp', s_common.now()))
            self.none(await core._finiStormPkgUninstall('unipkg', []))

            # stale failure and completion events do not act on a package which is not uninstalling
            await core.addStormPkg(pkgdef)
            self.none(await core._failStormPkgUninstall('unipkg', 'newp', s_common.now()))
            self.none(core.getStormPkgStatus('unipkg'))
            self.none(await core._finiStormPkgUninstall('unipkg', []))
            self.true(await core.hasStormPkg('unipkg'))

            # an uninstall task for a package which is no longer being uninstalled does nothing
            core._initStormPkgUninstall('ghostpkg')
            await asyncio.wait([core.stormpkguninsttask['ghostpkg']], timeout=10)

            # an uninstall which is already running is not started again
            core.stormpkguninsttask['unipkg'] = asyncio.get_running_loop().create_future()
            self.none(core._initStormPkgUninstall('unipkg'))
            core.stormpkguninsttask.pop('unipkg')

        # resuming after a restart, including one in safemode
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn, conf={'safemode': True}) as core:

                await core.addStormPkg(pkgdef)
                await core.addStormPkg({'name': 'failpkg', 'version': '0.0.1',
                                        'onload': '$lib.globals.failonload = (true)'})
                await core.setStormPkgVar('unipkg', 'foo', 'bar')

                core.pkguninst.set('failpkg', {'status': 'failed', 'keep': [], 'time': 1, 'mesg': 'x'})

                waiter = core.waiter(1, 'core:pkg:uninstall:skipped')
                await core.delStormPkg('unipkg', uninstall=True)
                events = await waiter.wait(timeout=10)
                self.eq(events, (('core:pkg:uninstall:skipped', {'pkg': 'unipkg', 'reason': 'safemode'}),))

                self.eq('uninstalling', core.getStormPkgStatus('unipkg')['status'])
                self.true(await core.hasStormPkg('unipkg'))

            async with self.getTestCore(dirn=dirn, conf={'safemode': False}) as core:

                self.true(await waitgone(core, 'unipkg'))
                self.none(core.getStormPkgStatus('unipkg'))
                self.eq([], [item async for item in core.iterStormPkgVars('unipkg')])

                # a failed uninstall stays put until it is retried or deleted
                self.eq('failed', core.getStormPkgStatus('failpkg')['status'])
                self.true(await core.hasStormPkg('failpkg'))
                self.none(await core.getStormVar('failonload'))

    async def test_stormlib_pkg_docs(self):

        # a doc page's content lives in the Axon, so this needs a real
        # cluster (getTestCore() boots a bare Cortex with no Axon peer).
        async with self.getTestCluster() as clus:

            core = clus.cortex
            axon = await core.getAxon()

            async def putfile(text):
                (size, sha256) = await axon.put(text.encode())
                return {'sha256': sha256.hex()}

            # a package with no files at all
            await core.addStormPkg({'name': 'nofiles', 'version': '0.0.1'})

            # a package with files but none under docs/
            await core.addStormPkg({
                'name': 'nodocs',
                'version': '0.0.1',
                'files': {
                    'foo.txt': await putfile('not a doc'),
                },
            })

            # a package with docs/ but no docs/metadata.json (hand rolled, no doc build)
            await core.addStormPkg({
                'name': 'nometa',
                'version': '0.0.1',
                'files': {
                    'docs/index.md': await putfile('# Index\n'),
                },
            })

            # a fully built package: an index page outside the nav, a nested toc
            # entry (setup.md -> reference.md), and two docs sharing one title
            # to exercise the ambiguous-match branch.
            toc = {'toc': [
                {'href': 'guide/setup.md', 'title': 'Setup Guide', 'children': [
                    {'href': 'reference.md', 'title': 'Reference'},
                ]},
                {'href': 'dup1.md', 'title': 'Same'},
                {'href': 'dup2.md', 'title': 'Same'},
            ]}

            pkgdef = {
                'name': 'testpkg',
                'version': '1.2.3',
                'files': {
                    'docs/index.md': await putfile('# Index\n'),
                    'docs/guide/setup.md': await putfile('# Setup\n\nSetup content.\n'),
                    'docs/reference.md': await putfile('# Reference\n\nReference content.\n'),
                    'docs/dup1.md': await putfile('# Dup One\n\nDup one content.\n'),
                    'docs/dup2.md': await putfile('# Dup Two\n\nDup two content.\n'),
                    'docs/metadata.json': {'sha256': (await axon.put(s_json.dumps(toc)))[1].hex()},
                },
            }
            await core.addStormPkg(pkgdef)

            # package not found
            msgs = await core.stormlist('pkg.docs nosuchpkg')
            self.stormIsInWarn('Package (nosuchpkg) not found!', msgs)

            # no doc files at all
            msgs = await core.stormlist('pkg.docs nofiles')
            self.stormIsInPrint('Package (nofiles) contains no documentation.', msgs)

            msgs = await core.stormlist('pkg.docs nodocs')
            self.stormIsInPrint('Package (nodocs) contains no documentation.', msgs)

            # docs with no metadata.json: listing falls back to bare paths
            msgs = await core.stormlist('pkg.docs nometa')
            self.stormIsInPrint('Documentation for package (nometa):', msgs)
            self.stormIsInPrint('index.md', msgs)

            msgs = await core.stormlist('pkg.docs nometa index.md')
            self.stormIsInPrint('Index', msgs)

            # listing: all docs present, index.md has no title (not in the toc),
            # nested children flattened into the title map
            msgs = await core.stormlist('pkg.docs testpkg')
            self.stormIsInPrint('Documentation for package (testpkg):', msgs)
            self.stormIsInPrint('index.md', msgs)
            self.stormIsInPrint('guide/setup.md', msgs)
            self.stormIsInPrint('Setup Guide', msgs)
            self.stormIsInPrint('reference.md', msgs)
            self.stormIsInPrint('Reference', msgs)
            self.stormIsInPrint('dup1.md', msgs)
            self.stormIsInPrint('dup2.md', msgs)
            self.stormIsInPrint('Use: pkg.docs testpkg <doc>', msgs)

            # select by relative path
            msgs = await core.stormlist('pkg.docs testpkg guide/setup.md')
            self.stormIsInPrint('Setup content.', msgs)

            # select by stem (no .md suffix)
            msgs = await core.stormlist('pkg.docs testpkg guide/setup')
            self.stormIsInPrint('Setup content.', msgs)

            # select by full path
            msgs = await core.stormlist('pkg.docs testpkg docs/guide/setup.md')
            self.stormIsInPrint('Setup content.', msgs)

            # select by title, case-insensitively -- also proves the nested
            # toc child (reference.md) was flattened into the title map
            msgs = await core.stormlist('pkg.docs testpkg "SETUP GUIDE"')
            self.stormIsInPrint('Setup content.', msgs)

            msgs = await core.stormlist('pkg.docs testpkg reference')
            self.stormIsInPrint('Reference content.', msgs)

            # the package name must match exactly -- unlike pkg.list/pkg.del,
            # pkg.docs looks it up with $lib.pkg.get(), which does not do
            # prefix matching
            msgs = await core.stormlist('pkg.docs test')
            self.stormIsInWarn('Package (test) not found!', msgs)

            # no selector match
            msgs = await core.stormlist('pkg.docs testpkg nope')
            self.stormIsInWarn('No document matches "nope" in package (testpkg).', msgs)
            self.stormIsInPrint('index.md', msgs)

            # ambiguous selector match
            msgs = await core.stormlist('pkg.docs testpkg same')
            self.stormIsInWarn('Multiple documents match "same" in package (testpkg):', msgs)
            self.stormIsInPrint('dup1.md', msgs)
            self.stormIsInPrint('dup2.md', msgs)

            # a sha256 the pkgdef declares but the Axon never actually got --
            # exercises the axon.has() guard in the pkg.docs storm helper for
            # both metadata.json and a doc page.
            ghost = 'ab' * 32

            await core.addStormPkg({
                'name': 'ghostmeta',
                'version': '0.0.1',
                'files': {
                    'docs/index.md': await putfile('# Index\n'),
                    'docs/metadata.json': {'sha256': ghost},
                },
            })
            msgs = await core.stormlist('pkg.docs ghostmeta')
            self.stormIsInPrint('Documentation for package (ghostmeta):', msgs)
            self.stormIsInPrint('index.md', msgs)

            await core.addStormPkg({
                'name': 'ghostdoc',
                'version': '0.0.1',
                'files': {
                    'docs/index.md': {'sha256': ghost},
                },
            })
            msgs = await core.stormlist('pkg.docs ghostdoc index.md')
            self.stormIsInWarn('Document (index.md) is missing from the Axon.', msgs)

            # pkg.docs and $lib.pkg.docs.* require no permissions -- a low
            # privilege user can list and read package documentation without
            # the axon.get/axon.has perms that $lib.axon.* would otherwise need.
            lowuser = await core.addUser('lowuser')
            aslow = {'user': lowuser.get('iden')}

            msgs = await core.stormlist('pkg.docs testpkg', opts=aslow)
            self.stormIsInPrint('Documentation for package (testpkg):', msgs)

            msgs = await core.stormlist('pkg.docs testpkg guide/setup.md', opts=aslow)
            self.stormIsInPrint('Setup content.', msgs)

            docs = await core.callStorm('return($lib.pkg.docs.list(testpkg))', opts=aslow)
            self.eq(sorted(d['path'] for d in docs), ['dup1.md', 'dup2.md', 'guide/setup.md',
                                                        'index.md', 'reference.md'])

            titles = {d['path']: d['title'] for d in docs}
            self.none(titles['index.md'])
            self.eq(titles['guide/setup.md'], 'Setup Guide')
            self.eq(titles['reference.md'], 'Reference')

            onedoc = await core.callStorm('return($lib.pkg.docs.get(testpkg, doc="guide/setup.md"))', opts=aslow)
            self.eq(['guide/setup.md'], list(onedoc.keys()))
            self.isin('Setup content.', onedoc['guide/setup.md'])

            alldocs = await core.callStorm('return($lib.pkg.docs.get(testpkg))', opts=aslow)
            self.eq(sorted(alldocs.keys()), ['dup1.md', 'dup2.md', 'guide/setup.md', 'index.md', 'reference.md'])
            self.isin('Setup content.', alldocs['guide/setup.md'])

            # a missing package returns null from both functions
            self.none(await core.callStorm('return($lib.pkg.docs.list(nosuchpkg))'))
            self.none(await core.callStorm('return($lib.pkg.docs.get(nosuchpkg))'))

            # a package with no doc files returns an empty list, and get()
            # with no selector returns an empty dict
            self.eq([], await core.callStorm('return($lib.pkg.docs.list(nofiles))'))
            self.eq([], await core.callStorm('return($lib.pkg.docs.list(nodocs))'))
            self.eq({}, await core.callStorm('return($lib.pkg.docs.get(nofiles))'))

            # a doc selector that does not exist on the package returns null
            self.none(await core.callStorm('return($lib.pkg.docs.get(testpkg, doc=nope))'))

            # get() only matches an exact path relative to docs/ -- the full
            # path (with the docs/ prefix) does not match
            self.none(await core.callStorm('return($lib.pkg.docs.get(testpkg, doc="docs/guide/setup.md"))'))

            # a hand rolled package with no metadata.json has null titles for every doc
            nometadocs = await core.callStorm('return($lib.pkg.docs.list(nometa))')
            self.eq([{'path': 'index.md', 'title': None}], nometadocs)

            # a pkgdef that declares a metadata.json sha256 the Axon never
            # actually got falls back to null titles rather than raising
            ghostmetadocs = await core.callStorm('return($lib.pkg.docs.list(ghostmeta))')
            self.eq([{'path': 'index.md', 'title': None}], ghostmetadocs)

            # a pkgdef that declares a doc sha256 the Axon never got raises
            # NoSuchFile out of get(), both for a single doc and for the full dict
            await self.asyncraises(s_exc.NoSuchFile,
                core.callStorm('return($lib.pkg.docs.get(ghostdoc, doc="index.md"))'))
            await self.asyncraises(s_exc.NoSuchFile,
                core.callStorm('return($lib.pkg.docs.get(ghostdoc))'))

            # metadata.json that is not valid JSON also falls back to null titles
            await core.addStormPkg({
                'name': 'badmeta',
                'version': '0.0.1',
                'files': {
                    'docs/index.md': await putfile('# Index\n'),
                    'docs/metadata.json': await putfile('not json'),
                },
            })
            badmetadocs = await core.callStorm('return($lib.pkg.docs.list(badmeta))')
            self.eq([{'path': 'index.md', 'title': None}], badmetadocs)

            # a toc entry with no href is skipped when building the title map
            notoc = {'toc': [{'title': 'No Href'}]}
            await core.addStormPkg({
                'name': 'nohreftoc',
                'version': '0.0.1',
                'files': {
                    'docs/index.md': await putfile('# Index\n'),
                    'docs/metadata.json': {'sha256': (await axon.put(s_json.dumps(notoc)))[1].hex()},
                },
            })
            nohrefdocs = await core.callStorm('return($lib.pkg.docs.list(nohreftoc))')
            self.eq([{'path': 'index.md', 'title': None}], nohrefdocs)

            # a document over the size limit raises StormRuntimeError out of
            # get() -- list() still succeeds, but metadata.json is also over
            # the limit now, so every title falls back to null
            with mock.patch('synapse.lib.stormlib.pkg.MAX_DOC_SIZE', 4):
                await self.asyncraises(s_exc.StormRuntimeError,
                    core.callStorm('return($lib.pkg.docs.get(testpkg, doc="guide/setup.md"))'))
                oksizedocs = await core.callStorm('return($lib.pkg.docs.list(testpkg))')
                self.len(5, oksizedocs)
                self.true(all(d['title'] is None for d in oksizedocs))
