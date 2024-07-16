import synapse.exc as s_exc
import synapse.lib.parser as s_parser

import synapse.tests.utils as s_test

class LibStormTest(s_test.SynTest):

    async def test_lib_stormlib_storm_eval(self):
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

    async def test_lib_stormlib_storm(self):

        async with self.getTestCore() as core:

            q = '''
            $query = '[ inet:fqdn=foo.com inet:fqdn=bar.com ]'
            storm.exec $query
            '''
            self.len(2, await core.nodes(q))

            q = '''[
            (inet:ipv4=1.2.3.4 :asn=4)
            (inet:ipv4=1.2.3.5 :asn=5)
            (inet:ipv4=1.2.3.6 :asn=10)
            ]'''
            await core.nodes(q)

            q = '''
            $filter = '-:asn=10'
            inet:ipv4:asn
            storm.exec $filter
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            for node in nodes:
                self.ne(node.get('asn'), 10)

            q = '''
            $pivot = ${ -> inet:asn }
            inet:ipv4:asn
            storm.exec $pivot
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            for node in nodes:
                self.eq(node.form.name, 'inet:asn')

            # Exec a non-runtsafe query
            q = '''
            inet:ipv4:asn
            $filter = `+:asn={$node.repr().split('.').'-1'}`
            storm.exec $filter
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            for node in nodes:
                self.ne(node.get('asn'), 10)

            iden = await core.callStorm('return($lib.view.get().fork().iden)')
            msgs = await core.stormlist('''
                $query = "[inet:fqdn=vertex.link +#haha] $lib.print(woot)"
                $opts = ({"view": $view})
                for $mesg in $lib.storm.run($query, opts=$opts) {
                    if ($mesg.0 = "print") { $lib.print($mesg.1.mesg) }
                }
            ''', opts={'vars': {'view': iden}})
            self.stormIsInPrint('woot', msgs)
            self.len(1, await core.nodes('inet:fqdn#haha', opts={'view': iden}))

            visi = await core.auth.addUser('visi')
            msgs = await core.stormlist('''
                $opts=({"user": $lib.auth.users.byname(root).iden})
                for $mesg in $lib.storm.run("$lib.print(lolz)", opts=$opts) {
                    if ($mesg.0 = "err") { $lib.print($mesg) }
                    if ($mesg.0 = "print") { $lib.print($mesg) }
                }
            ''', opts={'user': visi.iden})
            self.stormIsInErr('must have permission impersonate', msgs)
            self.stormNotInPrint('lolz', msgs)

            # no opts provided
            msgs = await core.stormlist('''
                $q = ${ $lib.print('hello') }
                for $mesg in $lib.storm.run($q) {
                    if ( $mesg.0 = 'print' ) {
                        $lib.print(`mesg={$mesg.1.mesg}`)
                    }
                }
            ''')
            self.stormIsInPrint('mesg=hello', msgs)
