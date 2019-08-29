import synapse.tests.utils as s_test
import synapse.lib.stormsvc as s_stormsvc

class RealService(s_stormsvc.StormSvc):
    _storm_svc_cmds = (
        {
            'name': 'ohhai',
            'cmdopts': (
                ('--verbose', {'default': False, 'action': 'store_true'}),
            ),
            'storm': '[ inet:ipv4=1.2.3.4 :asn=$cmdconf.svc.asn() ]',
            # TODO perm? synvers? runas? (svc perms?)
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

    async def test_storm_svcs(self):

        async with self.getTestCore() as core:

            real = RealService()

            core.dmon.share('real', real)
            lurl = core.getLocalUrl(share='real')

            iden = 'bf3043ab6992644e82db254bc7c1f868'
            sdef = {
                'iden': iden,
                'name': 'fake',
                'url': lurl,
            }

            await core.setStormSvc(sdef)

            await core.svcsbyiden[iden].ready.wait()

            nodes = await core.nodes('[ inet:ipv4=5.5.5.5 ] | ohhai')

            self.len(2, nodes)
            self.eq(nodes[0].get('asn'), 20)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            self.eq(nodes[1].get('asn'), 20)
            self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))
