import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon

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

    async def doit(self, x):
        return x + 20

    async def fqdns(self):
        yield 'woot.com'
        yield 'vertex.link'

    async def ipv4s(self):
        return ('1.2.3.4', '5.6.7.8')

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
            self.stormIsInPrint('Storm service list', msgs)
            self.stormIsInPrint(f'    {iden} (fake): tcp://localhost:3333/foo', msgs)

            msgs = await core.streamstorm(f'service.del {iden[:4]}').list()
            self.stormIsInPrint(f'removed {iden} (fake): tcp://localhost:3333/foo', msgs)

    async def test_storm_svcs(self):

        with self.getTestDir() as dirn:

            real = RealService()

            async with await s_daemon.Daemon.anit() as dmon:

                dmon.share('real', RealService())

                host, port = await dmon.listen('tcp://127.0.0.1:0/')
                lurl = f'tcp://127.0.0.1:{port}/real'

                async with await s_cortex.Cortex.anit(dirn) as core:

                    await core.nodes(f'service.add fake {lurl}')
                    iden = core.getStormSvcs()[0].iden

                    # force a wait for command loads
                    await core.nodes('$lib.service.wait(fake)')

                    nodes = await core.nodes('[ inet:ipv4=5.5.5.5 ] | ohhai')

                    self.len(2, nodes)
                    self.eq(nodes[0].get('asn'), 20)
                    self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

                    self.eq(nodes[1].get('asn'), 20)
                    self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

                async with await s_cortex.Cortex.anit(dirn) as core:

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

                async with await s_cortex.Cortex.anit(dirn) as core:
                    with self.raises(s_exc.NoSuchName):
                        nodes = await core.nodes('[ inet:ipv4=6.6.6.6 ] | ohhai')

                    sdef = {
                        'iden': iden,
                        'name': 'fake',
                        'url': lurl,
                    }
