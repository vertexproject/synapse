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

    def test_chain(self):
        # chain() returns a "$as" guid constructor so the scraped value norms
        # through the crypto:currency:address chain field poly by its type.
        self.eq(s_coin.chain('btc'),
                {'$as': 'crypto:currency:chain', 'symbol': 'btc',
                 'id': 'bip122:000000000019d6689c085ae165831e93'})
        self.eq(s_coin.chain('eth'),
                {'$as': 'crypto:currency:chain', 'symbol': 'eth', 'id': 'eip155:1'})

        # a scrape callback embeds the constructor as the address chain field.
        valu = regex.search(r'(?P<valu>.+)', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')
        (chainval, iden), _ = s_coin.btc_base58_check(valu)
        self.eq(chainval, {'$as': 'crypto:currency:chain', 'symbol': 'btc',
                           'id': 'bip122:000000000019d6689c085ae165831e93'})
        self.eq(iden, '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')
