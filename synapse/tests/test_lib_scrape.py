import synapse.lib.scrape as s_scrape

import synapse.tests.utils as s_t_utils

data0 = '''

visi@vertex.link is an email address

and BOB@WOOT.COM is another

    hehe.taxi

    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

    aa:bb:cc:dd:ee:ff

    1.2.3.4

    5.6.7.8:16

'''

import unittest
raise unittest.SkipTest('SHOULD WORK. REGEX DEBUGGING?')

class ScrapeTest(s_t_utils.SynTest):

    def test_scrape(self):

        nodes = dict(s_scrape.scrape(data0))

        print(repr(nodes))

        nodes.pop(('inet:email', 'visi@vertex.link'))

        nodes.pop(('inet:email', 'BOB@WOOT.COM'))
        nodes.pop(('inet:fqdn', 'hehe.taxi'))

        nodes.pop(('inet:ipv4', 0x01020304))
        nodes.pop(('inet:ipv4', 0x05060708))
        nodes.pop(('inet:tcp4', 0x050607080010))

        nodes.pop(('hash:md5', 'a' * 32))

        self.len(0, nodes)
