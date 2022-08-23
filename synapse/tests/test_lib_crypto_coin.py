import regex

import synapse.common as s_common
import synapse.lib.crypto.coin as s_coin

import synapse.tests.utils as s_t_utils

class CryptoCoinTest(s_t_utils.SynTest):
    def test_eip55(self):
        # Test bad input on eip55
        v = s_common.guid() + 'X'
        self.none(s_coin.ether_eip55(v))

        valu = regex.search(r'(?P<valu>[a-z]+)', 'foobar')
        self.eq(s_coin.eth_check(valu), (None, {}))
