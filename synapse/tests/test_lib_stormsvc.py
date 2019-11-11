import contextlib
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.tests.utils as s_test
import synapse.lib.stormsvc as s_stormsvc

class RealService(s_stormsvc.StormSvc):
    _storm_svc_cmds = (
        {
            'name': 'ohhai',
            'cmdopts': (
                ('--verbose', {'default': False, 'action': 'store_true'}),
            ),
            'storm': '[ inet:ipv4=1.2.3.4 :asn=$lib.service.get($cmdconf.svciden).asn() ]',
        },
    )
    _storm_svc_evts = {
        'add': {
            'storm': '$lib.queue.add(vertex)',
        },
        'del': {
            'storm': '$lib.queue.del(vertex)',
        },
    }

    async def asn(self):
        return 20

    async def ipv4s(self):
        yield '1.2.3.4'
        yield '5.5.5.5'
        yield '123.123.123.123'

class BoomService(s_stormsvc.StormSvc):
    _storm_svc_cmds = (
        {
            'name': 'goboom',
            'storm': ']',
        },
    )
    _storm_svc_evts = {
        'add': {
            'storm': '[ inet:ipv4 = 8.8.8.8 ]',
        },
        'del': {
            'storm': '[ inet:ipv4 = OVER9000 ]',
        },
    }

class DeadService(s_stormsvc.StormSvc):
    _storm_svc_cmds = (
        {
            'name': 'dead',
            'storm': '$#$#$#$#',
        },
    )
    _storm_svc_evts = {
        'add': {
            'storm': 'inet:ipv4',
        },
        'del': {
            'storm': 'inet:ipv4',
        },
    }

class NoService:
    def lower(self):
        return 'asdf'

class LifterService(s_stormsvc.StormSvc):
    _storm_svc_cmds = (
        {
            'name': 'lifter',
            'desc': 'Lift inet:ipv4=1.2.3.4',
            'storm': 'inet:ipv4=1.2.3.4',
        },
    )

    _storm_svc_evts = {
        'add': {
            'storm': '+[',
        },
        'del': {
            'storm': '-}',
        },
    }

@contextlib.contextmanager
def patchcore(core, attr, newfunc):
    origvalu = getattr(core, attr)
    try:
        setattr(core, attr, newfunc)
        yield
    finally:
        setattr(core, attr, origvalu)

class StormSvcTest(s_test.SynTest):

    async def test_storm_svc_cmds(self):

        async with self.getTestCore() as core:

            msgs = await core.streamstorm('service.add --help').list()
            self.stormIsInPrint(f'Add a storm service to the cortex.', msgs)

            msgs = await core.streamstorm('service.del --help').list()
            self.stormIsInPrint(f'Remove a storm service from the cortex.', msgs)

            msgs = await core.streamstorm('service.list --help').list()
            self.stormIsInPrint(f'List the storm services configured in the cortex.', msgs)

            msgs = await core.streamstorm('service.add fake tcp://localhost:3333/foo').list()
            iden = core.getStormSvcs()[0].iden
            self.stormIsInPrint(f'added {iden} (fake): tcp://localhost:3333/foo', msgs)

            msgs = await core.streamstorm('service.list').list()
            self.stormIsInPrint('Storm service list (iden, ready, name, url):', msgs)
            self.stormIsInPrint(f'    {iden} False (fake): tcp://localhost:3333/foo', msgs)

            msgs = await core.streamstorm(f'service.del {iden[:4]}').list()
            self.stormIsInPrint(f'removed {iden} (fake): tcp://localhost:3333/foo', msgs)

    async def test_storm_svcs_bads(self):

        async with self.getTestCore() as core:

            sdef = {'iden': s_common.guid(), 'name': 'dups', 'url': 'tcp://127.0.0.1:1/'}
            await core.addStormSvc(sdef)
            with self.raises(s_exc.DupStormSvc):
                await core.addStormSvc(sdef)

            with self.raises(s_exc.NoSuchStormSvc):
                await core.delStormSvc(s_common.guid())

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.service.wait(newp)')

            async with self.getTestDmon() as dmon:
                dmon.share('real', RealService())
                host, port = dmon.addr
                lurl = f'tcp://127.0.0.1:{port}/real'

                await core.nodes(f'service.add fake {lurl}')
                await core.nodes('$lib.service.wait(fake)')

                core.svcsbyname['fake'].client._t_conf['timeout'] = 0.1

            await core.svcsbyname['fake'].client._t_proxy.waitfini(6)

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ inet:ipv4=6.6.6.6 ] | ohhai')

    async def test_storm_svcs(self):

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
                durl = f'tcp://127.0.0.1:{port}/dead'

                async with await s_cortex.Cortex.anit(dirn) as core:

                    await core.nodes(f'service.add fake {lurl}')
                    iden = core.getStormSvcs()[0].iden

                    await core.nodes(f'service.add prim {purl}')
                    await core.nodes(f'service.add boom {burl}')
                    await core.nodes(f'service.add lift {curl}')

                    evts = {
                        'add': {
                            'storm': '$lib.queue.add(foo)',
                        },
                        'del': {
                            'storm': '$lib.queue.del(foo)',
                        },
                    }
                    with self.raises(s_exc.NoSuchStormSvc):
                        await core.setStormSvcEvents(s_common.guid(), evts)

                    with self.raises(s_exc.NoSuchStormSvc):
                        await core._runStormSvcAdd(s_common.guid())

                    # force a wait for command loads
                    await core.nodes('$lib.service.wait(fake)')
                    await core.nodes('$lib.service.wait(prim)')
                    await core.nodes('$lib.service.wait(boom)')
                    await core.nodes('$lib.service.wait(lift)')

                    # ensure that the initializer ran, but only the initializers for
                    # RealService and BoomService, since the others should have failed
                    queue = core.multiqueue.list()
                    self.len(1, queue)
                    self.eq('vertex', queue[0]['name'])
                    nodes = await core.nodes('inet:ipv4=8.8.8.8')
                    self.len(1, nodes)
                    self.eq(nodes[0].ndef[1], 134744072)

                    self.nn(core.getStormCmd('ohhai'))
                    self.none(core.getStormCmd('goboom'))

                    nodes = await core.nodes('[ ps:name=$lib.service.get(prim).lower() ]')
                    self.len(1, nodes)
                    self.eq(nodes[0].ndef[1], 'asdf')

                    nodes = await core.nodes('[ inet:ipv4=5.5.5.5 ] | ohhai')

                    self.len(2, nodes)
                    self.eq(nodes[0].get('asn'), 20)
                    self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

                    self.eq(nodes[1].get('asn'), 20)
                    self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

                    nodes = await core.nodes('for $ipv4 in $lib.service.get(fake).ipv4s() { [inet:ipv4=$ipv4] }')
                    self.len(3, nodes)

                    # execute a pure storm service without inbound nodes
                    # even though it has invalid add/del, it should still work
                    nodes = await core.nodes('lifter')
                    self.len(1, nodes)

                async with await s_cortex.Cortex.anit(dirn) as core:

                    nodes = await core.nodes('$lib.service.wait(fake)')
                    nodes = await core.nodes('[ inet:ipv4=6.6.6.6 ] | ohhai')

                    self.len(2, nodes)
                    self.eq(nodes[0].get('asn'), 20)
                    self.eq(nodes[0].ndef, ('inet:ipv4', 0x06060606))

                    self.eq(nodes[1].get('asn'), 20)
                    self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

                    # reach in and close the proxies
                    for ssvc in core.getStormSvcs():
                        await ssvc.client._t_proxy.fini()

                    nodes = await core.nodes('[ inet:ipv4=6.6.6.6 ] | ohhai')
                    self.len(2, nodes)

                    # haven't deleted the service yet, so still should be there
                    queue = core.multiqueue.list()
                    self.len(1, queue)
                    self.eq('vertex', queue[0]['name'])

                    await core.delStormSvc(iden)

                    # ensure fini ran
                    queue = core.multiqueue.list()
                    self.len(0, queue)

                    # specifically call teardown
                    for svc in core.getStormSvcs():
                        mesgs = await s_test.alist(core.streamstorm(f'service.del {svc.iden}'))
                        mesgs = [m[1].get('mesg') for m in mesgs if m[0] == 'print']
                        self.len(1, mesgs)
                        self.isin(f'removed {svc.iden} ({svc.name})', mesgs[0])

                    self.len(0, core.getStormSvcs())
                    # make sure all the dels ran, except for the BoomService (which should fail)
                    nodes = await core.nodes('inet:ipv4')
                    ans = set(['1.2.3.4', '5.5.5.5', '6.6.6.6', '8.8.8.8', '123.123.123.123'])
                    reprs = set(map(lambda k: k.repr(), nodes))
                    self.eq(ans, reprs)

                    badiden = []
                    async def badSetStormSvcEvents(iden, evts):
                        badiden.append(iden)
                        raise s_exc.SynErr('Kaboom')

                    sdef = {
                        'name': 'dead',
                        'iden': s_common.guid(),
                        'url': durl,
                    }
                    with patchcore(core, 'setStormSvcEvents', badSetStormSvcEvents):
                        ssvc = await core.addStormSvc(sdef)
                        await ssvc.ready.wait()
                        await core.delStormSvc(ssvc.iden)

                    self.len(1, badiden)
                    self.eq(ssvc.iden, badiden.pop())

                    async def badRunStormSvcAdd(iden):
                        badiden.append(iden)
                        raise s_exc.SynErr('Kaboom')

                    with patchcore(core, '_runStormSvcAdd', badRunStormSvcAdd):
                        ssvc = await core.addStormSvc(sdef)
                        await ssvc.ready.wait()
                        await core.delStormSvc(ssvc.iden)
                    self.len(1, badiden)
                    self.eq(ssvc.iden, badiden[0])
