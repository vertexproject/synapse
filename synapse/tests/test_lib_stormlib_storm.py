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

            # Readonly functionality is sane
            msgs = await core.stormlist('$lib.print($lib.storm.eval( "{$lib.print(wow)}" ))')
            self.stormIsInPrint('wow', msgs)
            self.stormIsInPrint('$lib.null', msgs)

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('$lib.storm.eval( "{$lib.auth.users.add(readonly)}" )', opts={'readonly': True})

            with self.getLoggerStream('synapse.storm') as stream:
                q = '''{
                    $lib.log.info(hehe)
                    [test:str=omg]
                    $lib.log.info($node)
                    fini { return(wow) }
                }
                '''

                core.stormlog = True
                opts = {'vars': {'q': q}}
                ret = await core.callStorm('return( $lib.storm.eval($q) )', opts=opts)
                self.eq(ret, 'wow')
                self.len(1, await core.nodes('test:str=omg'))

                # Check that we saw the logs
                stream.seek(0)
                data = stream.read()

                mesg = 'Executing storm query {return( $lib.storm.eval($q) )} as [root]'
                self.isin(mesg, data)

                mesg = f'Executing storm query via $lib.storm.eval() {{{q}}} as [root]'
                self.isin(mesg, data)
