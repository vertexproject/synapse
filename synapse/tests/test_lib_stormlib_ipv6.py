import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormIpv6Test(s_test.SynTest):

    async def test_storm_ipv6(self):
        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[inet:ipv6=2001:4860:4860::8888]'))
            query = 'inet:ipv6=2001:4860:4860::8888 return ( $lib.inet.ipv6.expand($node.value()) )'
            self.eq('2001:4860:4860:0000:0000:0000:0000:8888',
                    await core.callStorm(query))

            query = '$valu="2001:4860:4860::8888 " return ( $lib.inet.ipv6.expand($valu) )'
            self.eq('2001:4860:4860:0000:0000:0000:0000:8888',
                    await core.callStorm(query))

            query = '$valu="2001:4860:4860::XXXX" return ( $lib.inet.ipv6.expand($valu) )'
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm(query)
