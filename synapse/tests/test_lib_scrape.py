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

class ScrapeTest(s_t_utils.SynTest):

    def test_scrape(self):

        nodes = set(s_scrape.scrape(data0))

        self.len(9, nodes)
        nodes.remove(('hash:md5', 'a' * 32))
        nodes.remove(('inet:ipv4', '1.2.3.4'))
        nodes.remove(('inet:ipv4', '5.6.7.8'))
        nodes.remove(('inet:fqdn', 'WOOT.COM'))
        nodes.remove(('inet:fqdn', 'hehe.taxi'))
        nodes.remove(('inet:fqdn', 'vertex.link'))
        nodes.remove(('inet:server', '5.6.7.8:16'))
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)

        nodes = set(s_scrape.scrape(data0, 'inet:email'))
        self.len(2, nodes)
        nodes.remove(('inet:email', 'BOB@WOOT.COM'))
        nodes.remove(('inet:email', 'visi@vertex.link'))
        self.len(0, nodes)
