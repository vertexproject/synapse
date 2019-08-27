import synapse.tests.utils as s_test

class FakeService:

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
            fake = FakeService()
            core.dmon.share('fake', fake)
            lurl = core.getLocalUrl(share='fake')

            sdef = {
                'name': 'fake',
                'iden': 'bf3043ab6992644e82db254bc7c1f868',
                'url': lurl,
            }
            await core.setStormSvc(sdef)
            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ]')

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ] $asn = $lib.service(fake).doit(:asn) [ :asn=$asn ]')

            self.eq(40, nodes[0].props['asn'])

            nodes = await core.nodes('for $fqdn in $lib.service(fake).fqdns() { [ inet:fqdn=$fqdn ] }')
            self.len(2, nodes)

            nodes = await core.nodes('for $ipv4 in $lib.service(fake).ipv4s() { [ inet:ipv4=$ipv4 ] }')
            self.len(2, nodes)
