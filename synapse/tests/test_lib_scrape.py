import synapse.cortex as s_cortex
import synapse.lib.scrape as s_scrape

from synapse.tests.common import *

data0 = '''

    visi@vertex.link is an email address

    BOB@WOOT.COM is another

    hehe.taxi

    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

    aa:bb:cc:dd:ee:ff

    1.2.3.4

    5.6.7.8:16

'''

class ScrapeTest(SynTest):

    def test_scrape_sync(self):
        core = s_cortex.openurl('ram://')
        core.splices(s_scrape.splices(data0))

        self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
        self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))

        self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
        self.nn(core.getTufoByProp('inet:email', 'bob@woot.com'))

        self.nn(core.getTufoByProp('inet:fqdn', 'hehe.taxi'))
        self.nn(core.getTufoByProp('hash:md5', 'a' * 32))

        self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
        self.nn(core.getTufoByProp('inet:ipv4', 0x05060708))
        self.nn(core.getTufoByProp('inet:tcp4', 0x050607080010))
