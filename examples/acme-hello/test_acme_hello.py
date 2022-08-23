import os

import synapse.tests.utils as s_test
import synapse.tools.genpkg as s_genpkg

dirname = os.path.abspath(os.path.dirname(__file__))
pkgpath = os.path.join(dirname, 'acme-hello.yaml')

class AcmeHelloTest(s_test.SynTest):

    async def test_acme_hello(self):

        async with self.getTestCore() as core:

            await s_genpkg.main((pkgpath, '--push', core.getLocalUrl()))

            msgs = await core.stormlist('acme.hello.sayhi')
            self.stormIsInPrint('hello storm!', msgs)

            valu = await core.callStorm('return($lib.import(acme.hello.example00).foo())')
            self.eq(10, valu)
