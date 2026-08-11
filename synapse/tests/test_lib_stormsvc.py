import asyncio
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

import synapse.lib.cell as s_cell
import synapse.lib.share as s_share
import synapse.lib.stormsvc as s_stormsvc

import synapse.tools.service.backup as s_tools_backup

old_pkg = {
    'name': 'old',
    'version': '0.0.1',
    'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
    'modules': (
        {'name': 'old.bar', 'storm': 'function bar(x, y) { return ($($x + $y)) }'},
        {'name': 'old.baz', 'storm': 'function baz(x, y) { return ($($x + $y)) }'},
    ),
    'commands': (
        {
            'name': 'old.bar',
            'storm': '$bar = $lib.import(old.bar) [:asn = $bar.bar(:asn, $(20))]',
        },
        {
            'name': 'old.baz',
            'storm': '$baz = $lib.import(old.baz) [:asn = $baz.baz(:asn, $(20))]',
        },
        {
            'name': 'oldcmd',
            'storm': '[ inet:ip=1.2.3.4 ]',
        },
    )
}

new_old_pkg = {
    'name': 'old',
    'version': '0.1.0',
    'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
    'modules': (
        {'name': 'old.bar', 'storm': 'function bar(x, y) { return ($($x + $y)) }'},
        {'name': 'new.baz', 'storm': 'function baz(x) { return ($($x + 20)) }'},
    ),
    'commands': (
        {
            'name': 'old.bar',
            'storm': '$bar = $lib.import(old.bar) [:asn = $bar.bar(:asn, $(20))]',
        },
        {
            'name': 'new.baz',
            'storm': '$baz = $lib.import(new.baz) [:asn = $baz.baz(:asn)]',
        },
        {
            'name': 'newcmd',
            'storm': '[ inet:ip=5.6.7.8 ]',
        },
    )
}

new_pkg = {
    'name': 'new',
    'version': '0.0.1',
    'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
    'modules': (
        {'name': 'echo', 'storm': '''function echo(arg1, arg2) {
                                        $lib.print(`{$arg1}={$arg2}`)
                                        return ()
                                    }
                                  '''
         },
    ),
    'commands': (
        {
            'name': 'runtecho',
            'storm': '''$echo = $lib.import(echo)
                        for ($key, $valu) in $lib.runt.vars() {
                                $echo.echo($key, $valu)
                        }
                    ''',
        },
    )
}

class OldServiceAPI(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = old_pkg  # type: ignore

class NewServiceAPI(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = new_old_pkg  # type: ignore

class RenamedServiceAPI(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = new_pkg  # type: ignore

class ChangingService(s_cell.Cell):

    celltype = 'chng'

    confdefs = {
        'updated': {
            'type': 'string',
            'default': 'old',
            'description': 'Which cell api to serve: old, new, or renamed.',
        }
    }

    async def getTeleApi(self, link, mesg, path):

        user = await self._getCellUser(link, mesg)

        updated = self.conf.get('updated')
        if updated == 'new':
            return await NewServiceAPI.anit(self, link, user)

        if updated == 'renamed':
            return await RenamedServiceAPI.anit(self, link, user)

        return await OldServiceAPI.anit(self, link, user)

class OldService(s_cell.Cell):

    celltype = 'chng'
    cellapi = OldServiceAPI

    async def getCellInfo(self):
        realinfo = await s_cell.Cell.getCellInfo(self)
        realinfo['synapse']['version'] = '2.0.0'
        return realinfo

class RealService(s_test.StubStormSvc):
    celltype = 'real'
    _storm_svc_pkg = {  # type: ignore
        'name': 'foo',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'modules': (
            {'name': 'foo.bar',
             'storm': '''
             function asdf(x, y) { return ($($x + $y)) }
             function printmodconf() {
                 for ($k, $v) in $modconf { $lib.print(`{$k}={$v}`) }
                 return ( true )
             }
             ''',
             'modconf': {'key': 'valu'},
             },
            {'name': 'foo.baz',
             'storm': '''
              function getMetaVars(){
                 return ($modconf.pkgmeta)
              }
             '''
            },
        ),
        'commands': (
            {
                'name': 'foobar',
                'storm': '''
                // Import the foo.bar module
                $bar = $lib.import(foo.bar)
                // Set :asn to the output of the asdf function defined
                // in foo.bar module.
                [:asn = $bar.asdf(:asn, $(20))]
                ''',
            },
            {
                'name': 'ohhai',
                'cmdargs': (
                    ('--verbose', {'default': False, 'action': 'store_true'}),
                ),
                'storm': '[ inet:ip=1.2.3.4 :asn=$lib.service.get(real).asn() ] '
                         'fini { if $cmdopts.verbose { $lib.print("ohhai verbose") } }',
            },
            {
                'name': 'yoyo',
                'storm': 'for $ipv4 in $lib.service.get(real).ipv4s() { [inet:ip=$ipv4] }',
            },
        )
    }

    async def asn(self):
        return 20

    async def ipv4s(self):
        yield '1.2.3.4'
        yield '5.5.5.5'
        yield '123.123.123.123'

class NodeCreateService(s_test.StubStormSvc):
    celltype = 'ncreate'
    _storm_svc_pkg = {
        'name': 'ncreate',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'commands': (
            {
                'name': 'baz',
                'storm': '''
                [inet:ip=8.8.8.8]
                ''',
            },
        )
    }

class BoomService(s_test.StubStormSvc):
    celltype = 'boom'
    _storm_svc_pkg = {  # type: ignore
        'name': 'boom',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'modules': (
            {'name': 'blah', 'storm': '+}'},
        ),
        'commands': (
            {
                'name': 'badcmd',
                'storm': ' --++{',
            },
            {
                'name': 'goboom',
                'storm': ']',
            },
        ),
    }

class DeadService(s_test.StubStormSvc):
    celltype = 'dead'
    _storm_svc_pkg = {  # type: ignore
        'name': 'dead',
        'version': '0.0.1',
        'commands': (
            {
                'name': 'dead',
                'storm': '$#$#$#$#',
            },
        ),
    }

class NoService:
    def lower(self):
        return 'asdf'

class NoPkgService(s_test.StubStormSvc):
    # a storm service which declares no package at all
    celltype = 'nopkg'

class LifterService(s_test.StubStormSvc):
    celltype = 'lifter'
    _storm_svc_pkg = {  # type: ignore
        'name': 'lifter',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'commands': (
            {
                'name': 'lifter',
                'desc': 'Lift inet:ip=1.2.3.4',
                'storm': 'inet:ip=1.2.3.4',
            },
        ),
    }

filesbyts = b'wootwoot' * 1024
filessha256 = s_common.ehex(hashlib.sha256(filesbyts).digest())

class FilesService(s_test.StubStormSvc):
    '''
    A service whose package declares a file the cortex must retrieve into its
    axon, since a service delivered package has no publisher to upload it.
    '''
    celltype = 'files'
    _storm_svc_pkg = {  # type: ignore
        'name': 'files',
        'version': '0.0.1',
        'files': {
            'sub/data.dat': {'sha256': filessha256},
        },
        # the file must be in the axon by the time onload runs
        'onload': f'$lib.globals.filesonload = $lib.axon.size({filessha256})',
    }

    def __init__(self, path):
        self._storm_svc_pkgfiles = {'sub/data.dat': path}

docsbyts = b'# Docs\n'
docssha256 = s_common.ehex(hashlib.sha256(docsbyts).digest())

class DocsFilesService(s_test.StubStormSvc):
    '''
    A service whose package declares both an ordinary file and a docs/
    file, to prove Cortex._setStormSvcPkgFiles skips the docs/ one while
    running under a test (see synapse.common.isTestRun).
    '''
    celltype = 'docsfiles'
    _storm_svc_pkg = {  # type: ignore
        'name': 'docsfiles',
        'version': '0.0.1',
        'files': {
            'sub/data.dat': {'sha256': filessha256},
            'docs/foo.md': {'sha256': docssha256},
        },
    }

    def __init__(self, datapath, docspath):
        self._storm_svc_pkgfiles = {'sub/data.dat': datapath, 'docs/foo.md': docspath}

class StormvarService(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = {  # type: ignore
        'name': 'stormvar',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'commands': (
            {
                'name': 'magic',
                'desc': 'Test stormvar support.',
                'cmdargs': (
                    ('name', {}),
                    ('--debug', {'default': False, 'action': 'store_true'})
                ),
                'cmdinputs': [
                    {'form': 'test:str'},
                    {'form': 'test:int'},
                ],
                'storm': '''
                $fooz = $cmdopts.name
                if $cmdopts.debug {
                    $lib.print(`DEBUG: fooz={$fooz}`)
                }
                $lib.print(`my foo var is {$fooz}`)
                ''',
            },
        ),
        'modules': (
            {
                'name': 'testmod',
                'storm': '',
            },
            {
                'name': 'apimod',
                'storm': 'function status() { return((true)) }',
                'apidefs': (
                    {
                        'name': 'status',
                        'desc': 'Status of the foo.',
                        'type': {
                            'type': 'function',
                            'returns': {
                                'type': 'boolean',
                                'desc': 'Where foo is ok',
                            },
                        },
                    },
                ),
            },
        ),
    }

class StormvarServiceCell(s_cell.Cell):

    celltype = 'stormvar'
    confdefs = {
        'some:obj': {
            'description': 'Some object',
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'string',
                },
                'bar': {
                    'type': 'string',
                },
                'name': {
                    'type': 'string',
                },
            },
            'required': ['name', ],
            'additionalProperties': False,
        },
    }
    cellapi = StormvarService

class SvcShare(s_share.Share):

    async def __anit__(self, link, cell):
        await s_share.Share.__anit__(self, link, None)
        cell.onfini(self)
        self.cell = cell

    async def foo(self):
        return await self.cell.foo()

class ShareService(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = {  # type: ignore
        'name': 'sharer',
        'version': '0.0.1',
        'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
        'modules': (
            {
                'name': 'sharer',
                'storm': '''
                    function get() {
                        return($lib.service.get(sharer).getShare())
                    }
                ''',
            },
        ),
    }

    async def getShare(self):
        return await SvcShare.anit(self.link, self.cell)

class ShareServiceCell(s_cell.Cell):

    celltype = 'sharer'

    cellapi = ShareService

    async def foo(self):
        return 'bar'

class StormSvcTest(s_test.SynTest):

    async def test_storm_svc_cmds(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('service.add --help')
            self.stormIsInPrint('Add a storm service to the cortex.', msgs)

            msgs = await core.stormlist('service.del --help')
            self.stormIsInPrint('Remove a storm service from the cortex.', msgs)

            msgs = await core.stormlist('service.list --help')
            self.stormIsInPrint('List the storm services configured in the cortex.', msgs)

            msgs = await core.stormlist('service.add fake tcp://localhost:3333/foo')
            ssvc = core.getStormSvcs()[0]
            self.eq('fake', ssvc.name)
            self.stormIsInPrint('added fake: tcp://localhost:3333/foo', msgs)

            msgs = await core.stormlist('service.list')
            self.stormIsInPrint('Storm service list (ready, name, service version, url):', msgs)
            self.stormIsInPrint('    false (fake @ Unknown): tcp://localhost:3333/foo', msgs)

            # a service def is keyed by name, so re-adding is a no-op
            self.eq(ssvc.sdef, await core._addStormSvc({'name': 'fake'}))

            msgs = await core.stormlist('service.del newp')
            self.stormIsInPrint('No service found by name: newp', msgs)

            msgs = await core.stormlist('service.del fake')
            self.stormIsInPrint('removed fake: tcp://localhost:3333/foo', msgs)
            self.len(0, core.getStormSvcs())

    async def test_storm_svcs_bads(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadArg):
                await core.addStormSvc({'url': 'tcp://127.0.0.1:1/'})

            sdef = {'name': 'dups', 'url': 'tcp://127.0.0.1:1/'}
            await core.addStormSvc(sdef)
            with self.raises(s_exc.DupStormSvc):
                await core.addStormSvc(sdef)

            with self.raises(s_exc.NoSuchStormSvc):
                await core.delStormSvc('newp')

            # a service is identified by name, so a non-string is rejected rather
            # than reaching the slab
            with self.raises(s_exc.BadArg):
                await core.delStormSvc(None)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.service.get(newp)')

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.service.wait(newp)')

            async with self.getTestDmon() as dmon:
                dmon.share('real', RealService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/real'

                # a service must be added under its cell type name
                await core.nodes(f'service.add fake {lurl}')
                self.false(await core.callStorm('return($lib.service.wait(fake, timeout=(1)))'))
                await core.nodes('service.del fake')

                await core.nodes(f'service.add real {lurl}')
                await core.nodes('$lib.service.wait(real)')

                self.true(await core.callStorm('return($lib.service.wait(real, timeout=(0)))'))
                self.true(await core.callStorm('return($lib.service.wait(real, timeout=(1)))'))

                core.svcs['real'].readytimeout = 0.1
                proxy = await core.svcs['real'].proxy()

            self.true(await proxy.waitfini(6))

            self.false(await core.callStorm('return($lib.service.wait(real, timeout=(1)))'))
            # This blocks indefinitely without a timeout value provided.
            fut = core.callStorm('return($lib.service.wait(real))')
            with self.raises(asyncio.TimeoutError):
                await asyncio.wait_for(fut, timeout=0.3)

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ inet:ip=6.6.6.6 ] | ohhai')

    async def test_storm_pkg_persist(self):

        pkg = {
            'name': 'foobar',
            'version': '0.0.1',
            'dependencies': {'synapse': {'version': '>=3.0.0b6,<4.0.0'}},
            'modules': (
                {'name': 'hehe.haha', 'storm': 'function add(x, y) { return ($($x + $y)) }'},
            ),
            'commands': (
                {'name': 'foobar', 'storm': '$haha = $lib.import(hehe.haha) [ inet:asn=$haha.add($(10), $(20)) ]'},
            ),
        }
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                await core.addStormPkg(pkg)

            async with self.getTestCore(dirn=dirn) as core:
                nodes = await core.nodes('foobar')
                self.eq(nodes[0].ndef, ('inet:asn', 30))

    async def test_storm_svc_nodecreate(self):
        '''
        Regression test for var leakage
        '''
        with self.getTestDir() as dirn:

            async with self.getTestDmon() as dmon:

                dmon.share('real', RealService())
                dmon.share('ncreate', NodeCreateService())

                host, port = dmon.addr

                lurl = f'tcp://127.0.0.1:{port}/real'
                murl = f'tcp://127.0.0.1:{port}/ncreate'

                async with self.getTestCore(dirn=dirn) as core:

                    await core.nodes(f'service.add real {lurl}')
                    await core.nodes(f'service.add ncreate {murl}')

                    await core.nodes('$lib.service.wait(real)')
                    await core.nodes('$lib.service.wait(ncreate)')

                    await core.nodes('[inet:ip=1.2.3.3]')

                    # baz yields inbound *and* a new node
                    # yoyo calls back into its own service from an iterator
                    nodes = await core.nodes('inet:ip=1.2.3.3 | baz | yoyo')
                    self.len(5, {n.ndef for n in nodes})

    async def test_storm_svcs_base(self):

        with self.getTestDir() as dirn:

            async with self.getTestDmon() as dmon:

                dmon.share('prim', NoService())
                dmon.share('real', RealService())
                dmon.share('boom', BoomService())
                dmon.share('dead', DeadService())
                dmon.share('lift', LifterService())

                host, port = dmon.addr

                lurl = f'tcp://127.0.0.1:{port}/real'
                purl = f'tcp://127.0.0.1:{port}/prim'
                burl = f'tcp://127.0.0.1:{port}/boom'
                curl = f'tcp://127.0.0.1:{port}/lift'

                async with self.getTestCore(dirn=dirn) as core:

                    await core.nodes(f'service.add real {lurl}')
                    await core.nodes(f'service.add prim {purl}')
                    await core.nodes(f'service.add boom {burl}')
                    await core.nodes(f'service.add lifter {curl}')

                    # force a wait for command loads
                    await core.nodes('$lib.service.wait(real)')
                    await core.nodes('$lib.service.wait(prim)')
                    await core.nodes('$lib.service.wait(boom)')
                    await core.nodes('$lib.service.wait(lifter)')

                    # check that new commands are displayed properly in help
                    msgs = await core.stormlist('help')
                    self.stormIsInPrint('service: real', msgs)
                    self.stormIsInPrint('package: foo', msgs)
                    self.stormIsInPrint('foobar', msgs)

                    self.nn(core.getStormCmd('ohhai'))
                    self.none(core.getStormCmd('goboom'))

                    msgs = await core.stormlist('ohhai')
                    self.stormNotInPrint('ohhai verbose', msgs)
                    msgs = await core.stormlist('ohhai --verbose')
                    self.stormIsInPrint('ohhai verbose', msgs)

                    prim = core.getStormSvc('prim')
                    refs = prim._syn_refs
                    await core.nodes('function subr(svc) { return() } $subr($lib.service.get(prim))')
                    await core.nodes('function subr(svc) { $other=$svc return() } $subr($lib.service.get(prim))')
                    await core.nodes('function subr(svc) { $other=$svc return() } $t=$subr($lib.service.get(prim))')
                    self.eq(refs, prim._syn_refs)

                    nodes = await core.nodes('[ entity:name=$lib.service.get(prim).lower() ]')
                    self.len(1, nodes)
                    self.eq(nodes[0].ndef[1], 'asdf')

                    nodes = await core.nodes('[ inet:ip=5.5.5.5 ] | ohhai')

                    self.len(2, nodes)
                    self.propeq(nodes[0], 'asn', 20)
                    self.eq(nodes[0].ndef, ('inet:ip', (4, 0x05050505)))

                    self.propeq(nodes[1], 'asn', 20)
                    self.eq(nodes[1].ndef, ('inet:ip', (4, 0x01020304)))

                    nodes = await core.nodes('for $ipv4 in $lib.service.get(real).ipv4s() { [inet:ip=$ipv4] }')
                    self.len(3, nodes)

                    nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 ] | foobar | +:asn=40')
                    self.len(1, nodes)

                    self.none(await core.getStormPkg('boom'))
                    self.none(core.getStormCmd('badcmd'))

                    scmd = '''
                        $svc = $lib.service.get(prim)
                        if ($svc = null) { return((false)) }
                        else { return((true)) }
                    '''
                    self.true(await core.callStorm(scmd))

                    # a pure storm service command works without inbound nodes
                    nodes = await core.nodes('lifter')
                    self.len(1, nodes)

                    # modconf data is available to commands, with no service iden
                    msgs = await core.stormlist('$real_lib = $lib.import("foo.bar") $real_lib.printmodconf()')
                    self.stormIsInPrint('key=valu', msgs)
                    self.stormIsInPrint("pkgmeta={'modname': 'foo.bar', 'pkgname': 'foo'}", msgs)

                    # metavars are available
                    q = '$mod = $lib.import(foo.baz) return ( $mod.getMetaVars() )'
                    ret = await core.callStorm(q)
                    self.eq(ret, {'modname': 'foo.baz', 'pkgname': 'foo'})

                    # the cortex tracks which service delivered a package
                    self.eq('real', core.getStormPkgSvc('foo'))
                    self.none(core.getStormPkgSvc('newp'))

                    # ... and derives it onto the defs it hands out rather than
                    # storing it, so a signed package is never modified
                    pkgdef = await core.getStormPkg('foo')
                    self.eq('real', pkgdef.get('svcname'))
                    self.none(core.pkgdefs.get('foo').get('svcname'))

                    pkgdefs = {p.get('name'): p for p in await core.getStormPkgs()}
                    self.eq('real', pkgdefs['foo'].get('svcname'))

                    # a def which was read may be pushed back, and the derived
                    # svcname is authoritative rather than whatever it carried
                    pkgdef['svcname'] = 'newp'
                    await core.addStormPkg(pkgdef)
                    self.eq('real', (await core.getStormPkg('foo')).get('svcname'))

                    # a package no service delivered never reports one
                    await core.addStormPkg({'name': 'nosvc', 'version': '0.0.1', 'svcname': 'newp'})
                    self.none((await core.getStormPkg('nosvc')).get('svcname'))
                    await core.delStormPkg('nosvc')

                    # Check some service related permissions
                    user = await core.auth.addUser('user')

                    # No permissions is a failure too!
                    msgs = await core.stormlist('$svc=$lib.service.get(real)', {'user': user.iden})
                    self.stormIsInErr('must have permission service.get', msgs)

                    await user.addRule((True, ('service', 'get')))
                    msgs = await core.stormlist('$svc=$lib.service.get(real) $lib.print($svc)', {'user': user.iden})
                    self.stormIsInPrint('telepath:proxy', msgs)
                    self.len(0, [m for m in msgs if m[0] == 'warn'])

                    q = '$hasfoo=$lib.service.has($svc) if $hasfoo {$lib.print(yes)} else {$lib.print(no)}'
                    msgs = await core.stormlist(q, {'vars': {'svc': 'foo'}})
                    self.stormIsInPrint('no', msgs)
                    msgs = await core.stormlist(q, {'vars': {'svc': 'real'}})
                    self.stormIsInPrint('yes', msgs)

                    # anyone that can get a service can also wait for it
                    msgs = await core.stormlist('$svc=$lib.service.wait(real) $lib.print(yup)', {'user': user.iden})
                    self.len(0, [m for m in msgs if m[0] == 'err'])
                    self.stormIsInPrint('yup', msgs)

                async with self.getTestCore(dirn=dirn) as core:

                    # a service delivered package survives a restart, with its
                    # provenance, before the service reconnects
                    self.eq('real', core.getStormPkgSvc('foo'))

                    await core.nodes('$lib.service.wait(real)')
                    nodes = await core.nodes('[ inet:ip=6.6.6.6 ] | ohhai')

                    self.len(2, nodes)
                    self.propeq(nodes[0], 'asn', 20)
                    self.eq(nodes[0].ndef, ('inet:ip', (4, 0x06060606)))

                    self.propeq(nodes[1], 'asn', 20)
                    self.eq(nodes[1].ndef, ('inet:ip', (4, 0x01020304)))

                    # reach in and close the proxies
                    for ssvc in core.getStormSvcs():
                        await (await ssvc.proxy()).fini()

                    nodes = await core.nodes('[ inet:ip=6.6.6.6 ] | ohhai')
                    self.len(2, nodes)

                    await core.delStormSvc('real')

                    # make sure stormcmd and the package provenance got deleted
                    self.none(core.getStormCmd('ohhai'))
                    self.none(core.getStormPkgSvc('foo'))

                    # specifically call teardown
                    for svc in core.getStormSvcs():
                        mesgs = await core.stormlist(f'service.del {svc.name}')
                        mesgs = [m[1].get('mesg') for m in mesgs if m[0] == 'print']
                        self.len(1, mesgs)
                        self.isin(f'removed {svc.name}', mesgs[0])

                    self.len(0, core.getStormSvcs())

                    nodes = await core.nodes('inet:ip')
                    ans = {'1.2.3.4', '5.5.5.5', '6.6.6.6', '123.123.123.123'}
                    reprs = set(map(lambda k: k.repr(), nodes))
                    self.eq(ans, reprs)

                    # timeout=0 on a name never registered returns False immediately
                    # rather than waiting on the 'core:stormsvc:add' event.
                    self.false(await core.waitStormSvc('newp', timeout=0))

                    # a bounded wait on a name that never registers times out to False.
                    self.false(await core.waitStormSvc('newp', timeout=0.01))

    async def test_storm_svc_pkgsync(self):
        '''
        A cortex reconciles service packages when it becomes the leader.
        '''
        async with self.getTestCore() as core:

            async with self.getTestDmon() as dmon:

                dmon.share('real', RealService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/real'

                await core.nodes(f'service.add real {lurl}')
                self.true(await core.callStorm('return($lib.service.wait(real, timeout=(12)))'))

                # the package is unchanged, so a re-sync is a no-op
                await core._syncStormSvcPkgs()
                self.eq('real', core.getStormPkgSvc('foo'))

                # a service which is not ready is skipped
                core.svcs['real'].svcready.clear()
                await core._syncStormSvcPkgs()
                core.svcs['real'].svcready.set()

            # the service is gone, so the proxy fails and the failure is logged.
            # force the ready state so the sync attempts the dead proxy.
            core.svcs['real'].svcready.set()
            core.svcs['real'].readytimeout = 0.1

            with self.getLoggerStream('synapse.cortex') as stream:
                await core._syncStormSvcPkgs()
                await stream.expect('storm package sync failed for storm service real', timeout=12)

    async def test_storm_svc_pkgfiles(self):
        '''
        The cortex retrieves the files declared by a service delivered package
        into its axon, since such a package has no publisher to upload them.
        '''
        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'data.dat')
            with open(path, 'wb') as fd:
                fd.write(filesbyts)

            # a package with files needs a cortex with an axon
            async with self.getTestCoreProv() as (core, axon, jsonstor):

                self.false(await axon.has(s_common.uhex(filessha256)))

                async with self.getTestDmon() as dmon:

                    dmon.share('files', FilesService(path))
                    host, port = dmon.addr
                    lurl = f'tcp://127.0.0.1:{port}/files'

                    waiter = core.waiter(1, 'core:pkg:onload:complete')

                    await core.nodes(f'service.add files {lurl}')
                    self.true(await core.callStorm('return($lib.service.wait(files, timeout=(12)))'))

                    self.true(await axon.has(s_common.uhex(filessha256)))

                    # the file was in the axon before the package onload ran
                    self.nn(await waiter.wait(timeout=12))
                    self.eq(len(filesbyts), await core.callStorm('return($lib.globals.filesonload)'))

                    # a re-register of the same package skips the retrieval since
                    # the axon already has the content addressed file
                    with self.getLoggerStream('synapse.cortex') as stream:
                        await core.delStormSvc('files')
                        await core.nodes(f'service.add files {lurl}')
                        self.true(await core.callStorm('return($lib.service.wait(files, timeout=(12)))'))

                    stream.seek(0)
                    self.notin('Retrieved storm package file', stream.read())

                    # a path the package does not declare is refused
                    ssvc = core.getStormSvc('files')
                    proxy = await ssvc.proxy()
                    with self.raises(s_exc.NoSuchFile):
                        async for _ in proxy.getStormSvcPkgFile('newp.dat'):
                            pass

    async def test_storm_svc_pkgfiles_skips_docs_under_test(self):
        '''
        Cortex._setStormSvcPkgFiles skips a package's docs/-prefixed
        declared files while running under pytest (synapse.common.isTestRun),
        since no test exercises their content (synapse.lib.mddocs.validate
        and docs/test_doctests.py already cover doc correctness) and
        fetching potentially hundreds of them (e.g. Optic's userguide
        images, SYN-11304) into a cold per-test axon adds real overhead. A
        package's other declared files are unaffected.
        '''
        with self.getTestDir() as dirn:

            datapath = s_common.genpath(dirn, 'data.dat')
            with open(datapath, 'wb') as fd:
                fd.write(filesbyts)

            docspath = s_common.genpath(dirn, 'foo.md')
            with open(docspath, 'wb') as fd:
                fd.write(docsbyts)

            async with self.getTestCoreProv() as (core, axon, jsonstor):

                async with self.getTestDmon() as dmon:

                    dmon.share('docsfiles', DocsFilesService(datapath, docspath))
                    host, port = dmon.addr
                    lurl = f'tcp://127.0.0.1:{port}/docsfiles'

                    await core.nodes(f'service.add docsfiles {lurl}')
                    self.true(await core.callStorm('return($lib.service.wait(docsfiles, timeout=(12)))'))

                    # the ordinary file was fetched; the docs/ file was skipped
                    self.true(await axon.has(s_common.uhex(filessha256)))
                    self.false(await axon.has(s_common.uhex(docssha256)))

            # outside a test run, the docs/ file is fetched too
            with self.setTstEnvars(PYTEST_CURRENT_TEST=None):

                async with self.getTestCoreProv() as (core, axon, jsonstor):

                    async with self.getTestDmon() as dmon:

                        dmon.share('docsfiles', DocsFilesService(datapath, docspath))
                        host, port = dmon.addr
                        lurl = f'tcp://127.0.0.1:{port}/docsfiles'

                        await core.nodes(f'service.add docsfiles {lurl}')
                        self.true(await core.callStorm('return($lib.service.wait(docsfiles, timeout=(12)))'))

                        self.true(await axon.has(s_common.uhex(filessha256)))
                        self.true(await axon.has(s_common.uhex(docssha256)))

    async def test_storm_svc_pkgfiles_mismatch(self):
        '''
        A package file whose contents changed on the service is refused.
        '''
        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'data.dat')
            with open(path, 'wb') as fd:
                fd.write(b'newp' * 1024)

            async with self.getTestCoreProv() as (core, axon, jsonstor):

                async with self.getTestDmon() as dmon:

                    dmon.share('files', FilesService(path))
                    host, port = dmon.addr
                    lurl = f'tcp://127.0.0.1:{port}/files'

                    with self.getLoggerStream('synapse.cortex') as stream:
                        await core.nodes(f'service.add files {lurl}')
                        await stream.expect('storm package file retrieval failed', timeout=12)

                    # the package is not registered when its files are not
                    self.none(await core.getStormPkg('files'))

    async def test_storm_svc_nopkg(self):
        '''
        A storm service which delivers no package is registered but loads nothing.
        '''
        async with self.getTestCore() as core:

            async with self.getTestDmon() as dmon:

                dmon.share('nopkg', NoPkgService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/nopkg'

                with self.getLoggerStream('synapse.cortex') as stream:
                    await core.nodes(f'service.add nopkg {lurl}')
                    self.true(await core.callStorm('return($lib.service.wait(nopkg, timeout=(12)))'))
                    await stream.expect('Storm service nopkg delivered no storm package', timeout=12)

                self.none(core.getStormSvcPkg('nopkg'))
                self.notin('pkgname', core.svcdefs.get('nopkg'))

    async def test_storm_svc_celltype(self):
        '''
        A storm service must be added under the cell type name it reports.
        '''
        async with self.getTestCore() as core:

            async with self.getTestDmon() as dmon:

                dmon.share('real', RealService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/real'

                with self.getLoggerStream('synapse.cortex') as stream:
                    await core.nodes(f'service.add newp {lurl}')
                    await stream.expect('Storm service newp is actually a real service', timeout=12)

                # the mismatch leaves the service unready and no package loaded
                self.false(await core.callStorm('return($lib.service.wait(newp, timeout=(1)))'))
                self.none(core.getStormCmd('ohhai'))
                self.none(await core.getStormPkg('foo'))

                await core.nodes('service.del newp')

    async def test_storm_svc_oldvers(self):

        async with self.getTestCore() as core:
            with self.getTestDir() as svcd:
                async with await OldService.anit(svcd) as olds:
                    olds.dmon.share('olds', olds)

                    root = await olds.auth.getUserByName('root')
                    await root.setPasswd('root')

                    info = await olds.dmon.listen('tcp://127.0.0.1:0/')
                    host, port = info

                    curl = f'tcp://root:root@127.0.0.1:{port}/olds'

                    with self.getLoggerStream('synapse.cortex') as stream:
                        await core.nodes(f'service.add chng {curl}')
                        await stream.expect('running Synapse 2.0.0', timeout=12)

    async def test_storm_svc_restarts(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                async with core.beholder() as wind:
                    with self.getTestDir() as svcd:
                        async with await ChangingService.anit(svcd) as chng:
                            chng.dmon.share('chng', chng)

                            root = await chng.auth.getUserByName('root')
                            await root.setPasswd('root')

                            info = await chng.dmon.listen('tcp://127.0.0.1:0/')
                            host, port = info

                            curl = f'tcp://root:root@127.0.0.1:{port}/chng'

                            await core.nodes(f'service.add chng {curl}')
                            await core.nodes('$lib.service.wait(chng)')

                            self.nn(core.getStormCmd('oldcmd'))
                            self.nn(core.getStormCmd('old.bar'))
                            self.nn(core.getStormCmd('old.baz'))
                            self.none(core.getStormCmd('new.baz'))
                            self.none(core.getStormCmd('newcmd'))
                            self.isin('old', core.stormpkgs)
                            self.isin('old.bar', core.stormmods)
                            self.isin('old.baz', core.stormmods)
                            pkg = await core.getStormPkg('old')
                            self.eq(pkg.get('version'), '0.0.1')
                            self.eq('chng', core.getStormPkgSvc('old'))

                            waiter = core.waiter(1, 'stormsvc:client:unready')

                        self.true(await waiter.wait(10))

                        # the same package at a new version replaces the old one
                        async with await ChangingService.anit(svcd, {'updated': 'new'}) as chng:
                            chng.dmon.share('chng', chng)
                            await chng.dmon.listen(f'tcp://127.0.0.1:{port}/')

                            await core.nodes('$lib.service.wait(chng)')

                            self.nn(core.getStormCmd('newcmd'))
                            self.nn(core.getStormCmd('new.baz'))
                            self.nn(core.getStormCmd('old.bar'))
                            self.none(core.getStormCmd('oldcmd'))
                            self.none(core.getStormCmd('old.baz'))
                            self.isin('old', core.stormpkgs)
                            self.isin('old.bar', core.stormmods)
                            self.isin('new.baz', core.stormmods)
                            self.notin('old.baz', core.stormmods)
                            pkg = await core.getStormPkg('old')
                            self.eq(pkg.get('version'), '0.1.0')

                        # a different package name drops the one it replaces
                        async with await ChangingService.anit(svcd, {'updated': 'renamed'}) as chng:
                            chng.dmon.share('chng', chng)
                            await chng.dmon.listen(f'tcp://127.0.0.1:{port}/')

                            await core.nodes('$lib.service.wait(chng)')

                            self.nn(core.getStormCmd('runtecho'))
                            self.isin('new', core.stormpkgs)
                            self.isin('echo', core.stormmods)

                            self.notin('old', core.stormpkgs)
                            self.none(await core.getStormPkg('old'))
                            self.none(core.getStormCmd('newcmd'))
                            self.none(core.getStormPkgSvc('old'))
                            self.eq('chng', core.getStormPkgSvc('new'))

                            svcs = await core.callStorm('return($lib.service.list())')
                            self.len(1, svcs)
                            self.eq('chng', svcs[0].get('name'))
                            self.none(svcs[0].get('iden'))

                        # an unchanged package is not re-registered
                        async with await ChangingService.anit(svcd, {'updated': 'renamed'}) as chng:
                            chng.dmon.share('chng', chng)
                            await chng.dmon.listen(f'tcp://127.0.0.1:{port}/')

                            await core.nodes('$lib.service.wait(chng)')

                events = []
                async for m in wind:
                    if m['event'] in ('svc:add', 'svc:set', 'pkg:add', 'pkg:del'):
                        events.append(m)

                self.eq([
                    ('svc:add', 'chng'),
                    ('svc:set', 'chng'),
                    ('pkg:add', 'old'),

                    # the same package name at a new version is replaced in place,
                    # so it never leaves a window with no package registered
                    ('svc:set', 'chng'),
                    ('pkg:add', 'old'),

                    # a new package name drops the one it replaces
                    ('svc:set', 'chng'),
                    ('pkg:del', 'old'),
                    ('pkg:add', 'new'),

                    # the unchanged redelivery only reports the service
                    ('svc:set', 'chng'),
                ], [(m['event'], m['info'].get('name')) for m in events])

            # storm commands loaded from a previously connected service are still
            # available even though the service is not available now
            with self.getLoggerStream('synapse.lib.nexus') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    self.nn(core.getStormCmd('runtecho'))
                    self.isin('new', core.stormpkgs)
                    self.isin('echo', core.stormmods)
                    self.notin('old', core.stormpkgs)

                    # the package regains its provenance from the service def
                    self.eq('chng', core.getStormPkgSvc('new'))

            stream.seek(0)
            mesgs = stream.read()
            self.notin('Exception while replaying', mesgs)

    async def test_storm_vars(self):

        async with self.getTestCoreProxSvc(StormvarServiceCell) as (core, prox, svc):

            await core.nodes('[ inet:ip=1.2.3.4 inet:ip=5.6.7.8 ]')

            scmd = 'inet:ip=1.2.3.4 $foo=$node.repr() | magic $foo'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('my foo var is 1.2.3.4', msgs)

            scmd = 'inet:ip=1.2.3.4 inet:ip=5.6.7.8 $foo=$node.repr() | magic $foo'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('my foo var is 1.2.3.4', msgs)
            self.stormIsInPrint('my foo var is 5.6.7.8', msgs)

            scmd = '$foo=8.8.8.8 | magic $foo'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('my foo var is 8.8.8.8', msgs)

            scmd = '$foo=8.8.8.8 | magic $foo --debug'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('DEBUG: fooz=8.8.8.8', msgs)
            self.stormIsInPrint('my foo var is 8.8.8.8', msgs)

            scmd = '$foo=8.8.8.8 | magic --debug $foo'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('DEBUG: fooz=8.8.8.8', msgs)
            self.stormIsInPrint('my foo var is 8.8.8.8', msgs)

            scmd = 'inet:ip=1.2.3.4 inet:ip=5.6.7.8 $foo=$node.repr() | magic $foo --debug'
            msgs = await core.stormlist(scmd)
            self.stormIsInPrint('my foo var is 1.2.3.4', msgs)
            self.stormIsInPrint('DEBUG: fooz=1.2.3.4', msgs)
            self.stormIsInPrint('my foo var is 5.6.7.8', msgs)
            self.stormIsInPrint('DEBUG: fooz=5.6.7.8', msgs)

    async def test_storm_svc_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestDmon() as dmon:

                dmon.share('real', RealService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/real'

                async with self.getTestCore(dirn=path00) as core00:
                    await core00.nodes('[ inet:ip=1.2.3.4 ]')

                s_tools_backup.backup(path00, path01)

                async with self.getTestCore(dirn=path00) as core00:

                    url = core00.getLocalUrl()

                    conf = {'parent': url}
                    async with self.getTestCore(dirn=path01, conf=conf) as core01:

                        await core01.sync()

                        # Add a storm service
                        await core01.nodes(f'service.add real {lurl}')
                        await core01.nodes('$lib.service.wait(real)')

                        # Waiting for the svc to be ready on the leader means that any
                        # svc add event has been serviced.
                        await core00.nodes('$lib.service.wait(real)')

                        # Sync the follower to ensure we're caught up.
                        await core01.sync()

                        # the leader retrieves and registers the package
                        msgs = await core00.stormlist('help')
                        self.stormIsInPrint('service: real', msgs)
                        self.stormIsInPrint('package: foo', msgs)
                        self.stormIsInPrint('foobar', msgs)
                        self.isin('foo.bar', core00.stormmods)
                        self.nn(core00.getStormCmd('ohhai'))
                        self.eq('real', core00.getStormPkgSvc('foo'))

                        # the follower gets the package through the nexus rather
                        # than registering it from the service itself
                        msgs = await core01.stormlist('help')
                        self.stormIsInPrint('service: real', msgs)
                        self.stormIsInPrint('package: foo', msgs)
                        self.stormIsInPrint('foobar', msgs)
                        self.isin('foo.bar', core01.stormmods)
                        self.nn(core01.getStormCmd('ohhai'))
                        self.eq('real', core01.getStormPkgSvc('foo'))

                        # the pkgdef is persisted on the follower too
                        self.nn(core01.pkgdefs.get('foo'))

                        # Delete storm service
                        await core01.delStormSvc('real')
                        await core01.sync()

                        # Make sure it got removed from both
                        self.none(core00.getStormCmd('ohhai'))
                        self.none(core00.getStormPkgSvc('foo'))

                        self.none(core01.getStormCmd('ohhai'))
                        self.none(core01.getStormPkgSvc('foo'))

    async def test_storm_svc_share(self):

        async def chkShareFini(s):
            for b in s.tofini:
                if isinstance(b, SvcShare):
                    return await b.waitfini(timeout=5)
            return True

        async with self.getTestCoreProxSvc(ShareServiceCell) as (core, prox, svc):

            # base
            scmd = '''
                $svc = $lib.service.get(sharer)
                $share = $svc.getShare()
                return($share.foo())
            '''
            ret = await core.callStorm(scmd)
            self.eq('bar', ret)
            self.true(await chkShareFini(svc))

            # from sub runtime
            scmd = '''
                $share = $lib.import(sharer).get()
                return($share.foo())
            '''
            ret = await core.callStorm(scmd)
            self.eq('bar', ret)
            self.true(await chkShareFini(svc))

        async with self.getTestCore() as core:
            async with self.getTestCell(ShareServiceCell) as svc:

                opts = {'vars': {'url': svc.getLocalUrl()}}

                # base
                scmd = '''
                    $prox = $lib.telepath.open($url)
                    $share = $prox.getShare()
                    return($share.foo())
                '''
                ret = await core.callStorm(scmd, opts=opts)
                self.eq('bar', ret)
                self.true(await chkShareFini(svc))

                # from sub runtime
                scmd = '''
                    function get(url) {
                        $prox = $lib.telepath.open($url)
                        $share = $prox.getShare()
                        return($share)
                    }
                    $share = $get($url)
                    return($share.foo())
                '''
                ret = await core.callStorm(scmd, opts=opts)
                self.eq('bar', ret)
                self.true(await chkShareFini(svc))
