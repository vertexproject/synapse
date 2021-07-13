import synapse.exc as s_exc
import synapse.lib.parser as s_parser

import synapse.tests.utils as s_test

class LibStormTest(s_test.SynTest):

    async def test_lib_stormlib_storm(self):
        async with self.getTestCore() as core:

            opts = {'vars': {'text': '(10)'}}
            self.eq(10, await core.callStorm('return($lib.storm.eval($text))', opts=opts))

            opts = {'vars': {'text': '10'}}
            self.eq('10', await core.callStorm('return($lib.storm.eval($text))', opts=opts))

            opts = {'vars': {'text': '10'}}
            self.eq(10, await core.callStorm('return($lib.storm.eval($text, cast=int))', opts=opts))

            opts = {'vars': {'text': 'WOOT.COM'}}
            self.eq('woot.com', await core.callStorm('return($lib.storm.eval($text, cast=inet:dns:a:fqdn))', opts=opts))

            opts = {'vars': {'text': '(10 + 20)', 'cast': 'inet:port'}}
            self.eq(30, await core.callStorm('return($lib.storm.eval($text, cast=$cast))', opts=opts))

            with self.raises(s_exc.NoSuchType):
                await core.callStorm('return($lib.storm.eval(foo, cast=newp))')

            # for coverage of forked call...
            self.nn(s_parser.parseEval('woot'))
