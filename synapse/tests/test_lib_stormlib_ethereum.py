from unittest import mock
import synapse.tests.utils as s_test

class EthereumTest(s_test.SynTest):

    async def test_storm_ethereum(self):

        async with self.getTestCore() as core:

            addr = '0x0f0186fd42B545DcEAA0732fF40c4c0DCb8EE421'

            retn = await core.callStorm(f'return($lib.crypto.coin.ethereum.eip55({addr}))')
            self.eq(retn, (True, addr))

            laddr = addr.lower()
            retn = await core.callStorm(f'return($lib.crypto.coin.ethereum.eip55({laddr}))')
            self.eq(retn, (True, addr))

            retn = await core.callStorm(f'return($lib.crypto.coin.ethereum.eip55(foo))')
            self.eq(retn, (False, None))

            retn = await core.callStorm(f'return($lib.crypto.coin.ethereum.eip55($lib.null))')
            self.eq(retn, (False, None))
