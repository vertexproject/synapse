import os

import synapse.tests.utils as s_test

dirname = os.path.abspath(os.path.dirname(__file__))

class AcmeHelloTest(s_test.StormPkgTest):

    assetdir = os.path.join(dirname, 'testassets')
    pkgprotos = (os.path.join(dirname, 'acme-hello.yaml'),)

    async def test_acme_hello(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('acme.hello.sayhi')
            self.stormIsInPrint('hello storm!', msgs)
            self.stormHasNoWarnErr(msgs)

    async def test_acme_hello_mayyield(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0][0])

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield --yield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(('inet:dns:a', ('vertex.link', (4, 0x01020304))), nodes[0][0])
            self.eq(('inet:dns:a', ('vertex.link', (4, 0x7b7b7b7b))), nodes[1][0])
