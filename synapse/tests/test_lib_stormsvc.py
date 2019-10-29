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

    async def test_storm_svcs(self):

        with self.getTestDir() as dirn:

            async with self.getTestDmon() as dmon:

                dmon.share('prim', NoService())
                dmon.share('real', RealService())
                dmon.share('boom', BoomService())
                dmon.share('lift', LifterService())

                host, port = dmon.addr

                lurl = f'tcp://127.0.0.1:{port}/real'
                purl = f'tcp://127.0.0.1:{port}/prim'
                burl = f'tcp://127.0.0.1:{port}/boom'
                curl = f'tcp://127.0.0.1:{port}/lift'

                async with await s_cortex.Cortex.anit(dirn) as core:

                    await core.nodes(f'service.add fake {lurl}')
                    iden = core.getStormSvcs()[0].iden

                    await core.nodes(f'service.add prim {purl}')
                    await core.nodes(f'service.add boom {burl}')
                    await core.nodes(f'service.add lift {curl}')

                    # force a wait for command loads
                    await core.nodes('$lib.service.wait(fake)')
                    await core.nodes('$lib.service.wait(prim)')
                    await core.nodes('$lib.service.wait(boom)')
                    await core.nodes('$lib.service.wait(lift)')

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

                    await core.delStormSvc(iden)
