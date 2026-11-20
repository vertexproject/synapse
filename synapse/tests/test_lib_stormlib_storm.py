import asyncio

import synapse.exc as s_exc
import synapse.lib.parser as s_parser
import synapse.lib.stormlint as s_stormlint

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
            self.eq(('inet:fqdn', 'woot.com'), await core.callStorm('return($lib.storm.eval($text, cast=inet:dns:a:fqdn))', opts=opts))

            opts = {'vars': {'text': '(10 + 20)', 'cast': 'inet:port'}}
            self.eq(30, await core.callStorm('return($lib.storm.eval($text, cast=$cast))', opts=opts))

            with self.raises(s_exc.NoSuchType):
                await core.callStorm('return($lib.storm.eval(foo, cast=newp))')

            # for coverage of forked call...
            self.nn(s_parser.parseEval('woot'))

            # Readonly functionality is sane
            msgs = await core.stormlist('$lib.print($lib.storm.eval( "{$lib.print(wow)}" ))')
            self.stormIsInPrint('wow', msgs)
            self.stormIsInPrint('null', msgs)

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('$lib.storm.eval( "{$lib.auth.users.add(readonly)}" )', opts={'readonly': True})

            with self.getLoggerStream('synapse.storm') as stream:
                core.stormlog = True
                opts = {'vars': {'q': 'woot'}}
                ret = await core.callStorm('return( $lib.storm.eval($q) )', opts=opts)
                self.eq(ret, 'woot')

                # Check that we saw the logs
                await stream.expect('Executing storm query via $lib.storm.eval() {woot} as [root]')
                await stream.expect('Executing storm query {return( $lib.storm.eval($q) )} as [root]')

    async def test_lib_stormlib_storm(self):

        async with self.getTestCore() as core:

            q = '''
            $query = '[ inet:fqdn=foo.com inet:fqdn=bar.com ]'
            storm.exec $query
            '''
            self.len(2, await core.nodes(q))

            q = '''[
            (inet:ip=1.2.3.4 :asn=4)
            (inet:ip=1.2.3.5 :asn=5)
            (inet:ip=1.2.3.6 :asn=10)
            ]'''
            await core.nodes(q)

            q = '''
            $filter = '-:asn=10'
            inet:ip:asn
            storm.exec $filter
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            for node in nodes:
                self.ne(node.get('asn'), 10)

            q = '''
            $pivot = ${ -> inet:asn }
            inet:ip:asn
            storm.exec $pivot
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            for node in nodes:
                self.eq(node.form.name, 'inet:asn')

            # Exec a non-runtsafe query
            q = '''
            inet:ip:asn
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
            self.stormIsInErr('requires global admin permissions', msgs)
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

            # $lib.storm.lint.scan()
            q = '''
                $retn = ([])
                for $finding in $lib.storm.lint.scan($text, select=$select, ignore=$ignore, enable=$enable) {
                    $retn.append($finding)
                }
                return($retn)
            '''

            async def lint(text, select=None, ignore=None, enable=None, readonly=False):
                opts = {'vars': {'text': text, 'select': select, 'ignore': ignore, 'enable': enable},
                        'readonly': readonly}
                return await core.callStorm(q, opts=opts)

            finding = {'rule': 'S005', 'severity': 'low', 'line': 2, 'column': 6,
                       'mesg': 'Use a list literal such as ([]) instead of $lib.list().'}
            self.eq([finding], await lint('$y = 1\n$x = $lib.list()'))
            self.eq([finding], await lint('$y = 1\n$x = $lib.list()', readonly=True))
            self.eq([], await lint('$x = ([])'))
            self.eq([], await lint('$x = $lib.list()', ignore=['S005']))
            self.eq([], await lint('$x = $lib.list()', ignore=['S']))

            findings = await lint('$x = (')
            self.len(1, findings)
            self.eq('E001', findings[0]['rule'])
            self.eq('high', findings[0]['severity'])

            text = 'if $x { [ :name=$x ] }\n$y = $lib.list()\n$z = $lib.true'
            self.eq(['S005', 'R001'], [f['rule'] for f in await lint(text)])
            self.eq(['S010', 'S005', 'R001'], [f['rule'] for f in await lint(text, enable=['S010'])])
            self.eq(['S010', 'S005', 'R001'], [f['rule'] for f in await lint(text, enable=['S01'])])
            self.eq(['S010', 'R001'], [f['rule'] for f in await lint(text, ignore=['S005'], enable=['S010'])])
            self.eq(['S005', 'R001'], [f['rule'] for f in await lint(text, ignore=['S01'], enable=['S010'])])

            self.eq(['S010', 'S005'], [f['rule'] for f in await lint(text, select=['S'])])
            self.eq(['S005'], [f['rule'] for f in await lint(text, select=['S005'])])
            self.eq(['S010', 'S005'], [f['rule'] for f in await lint(text, select=['S005'], enable=['S010'])])
            self.eq([], await lint(text, select=[]))
            self.eq(['S010'], [f['rule'] for f in await lint(text, select=[], enable=['S010'])])

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = 1', enable=['Z999'])

            self.isin('Unknown lint rule or prefix', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = 1', enable=['newp', 'nada', 'never'])

            self.eq("Unknown lint rule or prefix: 'newp'", cm.exception.get('mesg'))
            self.eq('newp', cm.exception.get('name'))

            with self.raises(s_exc.BadArg):
                await lint('$x = 1', ignore=['Z'])

            with self.raises(s_exc.BadArg):
                await lint('$x = 1', select=['Z'])

            for name in ('select', 'ignore', 'enable'):

                with self.raises(s_exc.BadArg) as cm:
                    await lint(text, **{name: 'S010'})

                self.eq(name, cm.exception.get('name'))
                self.eq(f'{name} must be a list of rule IDs or ID prefixes.', cm.exception.get('mesg'))

                with self.raises(s_exc.BadArg) as cm:
                    await lint(text, **{name: ('S005', 1)})

                self.eq(name, cm.exception.get('name'))
                self.eq(f'{name} must be a list of rule IDs or ID prefixes.', cm.exception.get('mesg'))

            # an embedded query is linted by its text
            findings = await core.callStorm('''
                $query = ${
                    $x = 1
                      $y = $lib.list()
                }
                $retn = ([])
                for $finding in $lib.storm.lint.scan($query) {
                    $retn.append($finding)
                }
                return($retn)
            ''')
            self.eq([('S005', 3, 28)], [(f['rule'], f['line'], f['column']) for f in findings])

            # model names come from the Cortex model, including extended forms
            text = '_test:lint +:_name=foo\n_test:bogus +:_name=foo'
            self.eq([], await lint(text))

            await core.addForm('_test:lint', 'str', {}, {})
            await core.addFormProp('_test:lint', '_name', ('str', {}), {})

            findings = await lint(text)
            self.len(1, findings)
            self.eq(('S012', 1), (findings[0]['rule'], findings[0]['line']))

            # storm.lint
            async def lintcmd(q, opts=None):
                msgs = await core.stormlist(q, opts=opts)
                return msgs, [m[1]['mesg'] for m in msgs if m[0] == 'print']

            text = 'if $x { [ :name=$x ] }\n$y = $lib.list()\n$z = $lib.true'
            opts = {'vars': {'text': text}, 'readonly': True}

            msgs, prints = await lintcmd('storm.lint $text', opts=opts)
            self.stormHasNoWarnErr(msgs)
            self.eq(prints, [
                '2:6: S005 Use a list literal such as ([]) instead of $lib.list().',
                '3:6: R001 $lib.true was removed, use (true).',
                'Found 2 errors.',
            ])

            msgs, prints = await lintcmd('storm.lint $text --select R', opts=opts)
            self.eq(prints, ['3:6: R001 $lib.true was removed, use (true).', 'Found 1 error.'])

            msgs, prints = await lintcmd('storm.lint $text --select " R , S005 ," --enable S01 --ignore R001', opts=opts)
            self.eq(['S010', 'S005'], [p.split()[1] for p in prints[:-1]])
            self.eq('Found 2 errors.', prints[-1])

            msgs, prints = await lintcmd('storm.lint $text --select ""', opts=opts)
            self.eq(prints, ['All checks passed!'])

            msgs, prints = await lintcmd('storm.lint "$x = ([])"')
            self.eq(prints, ['All checks passed!'])

            msgs, prints = await lintcmd('storm.lint "$x = ("')
            self.len(2, prints)
            self.true(prints[0].startswith('1:'))
            self.isin(': E001 ', prints[0])
            self.eq('Found 1 error.', prints[1])

            msgs = await core.stormlist('storm.lint $text --enable newp,nada,never', opts=opts)
            self.stormIsInErr("Unknown lint rule or prefix: 'newp'", msgs)

            msgs = await core.stormlist('storm.lint $text --select Z', opts=opts)
            self.stormIsInErr("Unknown lint rule or prefix: 'Z'", msgs)

            msgs = await core.stormlist('storm.lint')
            self.stormIsInErr('storm.lint requires text to lint unless --show-rules is given.', msgs)

            # a null per-node text is not linted as the text None
            q = '[ test:str=a :hehe="$x = 1" test:str=b :hehe="$y = 2" test:str=c ] | storm.lint :hehe'
            with self.raises(s_exc.BadArg) as cm:
                await core.nodes(q)

            self.eq('text', cm.exception.get('name'))
            self.eq('storm.lint text is null.', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await core.nodes('storm.lint (null)')

            self.eq('text', cm.exception.get('name'))
            self.eq('storm.lint text is null.', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await core.nodes('test:str=a | storm.lint --select $node.value')

            self.eq('text', cm.exception.get('name'))
            self.eq('storm.lint requires text to lint unless --show-rules is given.', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('for $f in $lib.storm.lint.scan((null)) { }')

            self.eq('text', cm.exception.get('name'))
            self.eq('$lib.storm.lint.scan() requires text to lint.', cm.exception.get('mesg'))

            msgs, prints = await lintcmd('''
                storm.lint ${
                    $x = 1
                      $y = $lib.list()
                }
            ''')
            self.eq(prints, ['3:28: S005 Use a list literal such as ([]) instead of $lib.list().', 'Found 1 error.'])

            # runtsafe text is linted once and the nodes pass through
            await core.nodes('[ test:str=foo test:str=bar ]')
            nodes = await core.nodes('test:str=foo test:str=bar | storm.lint $text --select R', opts=opts)
            self.eq(['foo', 'bar'], [n.ndef[1] for n in nodes])

            msgs, prints = await lintcmd('test:str=foo test:str=bar | storm.lint $text --select R', opts=opts)
            self.len(2, [m for m in msgs if m[0] == 'node'])
            self.eq(prints, ['3:6: R001 $lib.true was removed, use (true).', 'Found 1 error.'])

            # text which is not runtsafe is linted for each node
            msgs, prints = await lintcmd('[ test:str="$lib.true" test:str="$lib.list()" ] | storm.lint $node.value')
            self.eq(prints, [
                '1:1: R001 $lib.true was removed, use (true).',
                'Found 1 error.',
                '1:1: S005 Use a list literal such as ([]) instead of $lib.list().',
                'Found 1 error.',
            ])

            msgs, prints = await lintcmd('storm.lint --show-rules')
            self.eq(prints, s_stormlint.getRuleTable())
            self.true(prints[0].startswith('ID    SEVERITY  DEFAULT  NAME'))

            nodes = await core.nodes('test:str=foo | storm.lint --show-rules')
            self.eq(['foo'], [n.ndef[1] for n in nodes])

            # $lib.storm.lint.rules()
            rules = await core.callStorm('return($lib.storm.lint.rules())', opts={'readonly': True})
            self.eq([r.iden for r in s_stormlint.rules.values()], [r['rule'] for r in rules])
            self.eq(sorted(r['rule'] for r in rules), [r['rule'] for r in rules])

            ruledict = {r['rule']: r for r in rules}
            self.eq(('lib-list-dict', 'low', True), (ruledict['S005']['name'], ruledict['S005']['severity'],
                                                    ruledict['S005']['default']))
            self.false(ruledict['S010']['default'])
            self.eq(s_stormlint.rules['S010'].doc, ruledict['S010']['desc'])
            self.eq({'rule', 'name', 'severity', 'default', 'desc'}, set(ruledict['E001'].keys()))

            msgs = await core.stormlist('$lib.print($lib.storm.lint)')
            self.stormIsInPrint('Library $lib.storm.lint', msgs)

    async def test_lib_stormlib_storm_logging(self):

        # storm.exec is gated on storm:log just like every other query path, at
        # the default conf of storm:log=False.
        async with self.getTestCore() as core:

            with self.getLoggerStream('synapse.storm') as stream:
                q = '''
                $query = '[ inet:fqdn=vertex.link ]'
                storm.exec $query
                '''
                self.len(1, await core.nodes(q))
                self.eq('', stream.getvalue())

        conf = {'storm:log': True, 'storm:log:level': 'DEBUG'}
        async with self.getTestCore(conf=conf) as core:

            self.len(3, await core.nodes('''[
                (inet:ip=1.2.3.4 :asn=4)
                (inet:ip=1.2.3.5 :asn=5)
                (inet:ip=1.2.3.6 :asn=10)
            ]'''))

            # runtsafe storm.exec
            with self.getLoggerStream('synapse.storm') as stream:
                q = '''
                $filter = '-:asn=10'
                inet:ip:asn
                storm.exec $filter
                '''
                nodes = await core.nodes(q)
                self.len(2, nodes)

                await stream.expect('Executing storm query via storm.exec {-:asn=10} as [root]')

                mesgs = [m for m in stream.jsonlines() if 'via storm.exec' in m['message']]
                self.len(1, mesgs)
                self.eq(mesgs[0]['level'], 'DEBUG')
                self.nn(mesgs[0]['params'].get('hash'))
                self.eq(mesgs[0]['params'].get('view'), core.view.iden)

            # non-runtsafe storm.exec: one record for the first item, one per
            # subsequent item
            with self.getLoggerStream('synapse.storm') as stream:
                q = '''
                inet:ip:asn
                $filter = `+:asn={$node.repr().split('.').'-1'}`
                storm.exec $filter
                '''
                nodes = await core.nodes(q)
                self.len(2, nodes)

                mesgs = [m for m in stream.jsonlines() if 'via storm.exec' in m['message']]
                self.len(3, mesgs)
                for mesg in mesgs:
                    self.eq(mesg['level'], 'DEBUG')
                    self.nn(mesg['params'].get('hash'))

            # $lib.storm.eval()
            with self.getLoggerStream('synapse.storm') as stream:
                ret = await core.callStorm('return($lib.storm.eval(woot))')
                self.eq(ret, 'woot')

                await stream.expect('Executing storm query via $lib.storm.eval() {woot} as [root]')

                mesgs = [m for m in stream.jsonlines() if 'via $lib.storm.eval()' in m['message']]
                self.len(1, mesgs)
                self.eq(mesgs[0]['level'], 'DEBUG')
                self.nn(mesgs[0]['params'].get('hash'))

    async def test_lib_stormlib_storm_tasks(self):

        with self.getLoggerStream('synapse') as stream:

            async with self.getTestCore() as core:

                async with core.getLocalProxy() as prox:

                    event = asyncio.Event()

                    q = 'for $mesg in $lib.storm.run("$lib.time.sleep(120)") { $lib.fire(storm, mesg=$mesg) }'

                    async def doit():
                        async for mesg in prox.storm(q):
                            if mesg[0] == 'storm:fire':
                                event.set()

                    task00 = core.schedCoro(doit())
                    await asyncio.wait_for(event.wait(), timeout=10)

                    viewiden = core.getView().iden

                    # One task for the main query
                    tasks = core.boss.ps()
                    self.len(1, tasks)
                    self.eq(tasks[0].name, 'storm')
                    self.eq(tasks[0].info, {'query': q, 'view': viewiden})
                    self.len(1, tasks[0].kids)

                    # The main query has one kid, the worker
                    kid = list(tasks[0].kids.values())[0]
                    self.nn(kid.iden)
                    self.nn(kid.user)
                    self.eq(kid.name, 'runstorm')
                    self.eq(kid.info, {})

                    # The worker has a kid which is the $lib.storm.run() worker
                    self.len(1, kid.kids)
                    gkid = list(kid.kids.values())[0]
                    self.eq(gkid.name, 'runstorm')
                    self.eq(gkid.info, {})

                    # Kill the main task
                    tasks = core.boss.ps()
                    self.len(1, tasks)
                    await tasks[0].kill()

                    # No tasks running
                    tasks = core.boss.ps()
                    self.len(0, tasks)

                    task00.cancel('oh bye')

        # Verify we saw two storm runtime cancellations
        msgs = stream.jsonlines()
        self.gt(len(msgs), 0)

        msgs = [(k.get('message'), k['params'].get('text')) for k in msgs]
        self.isin(('Storm runtime cancelled.', '$lib.time.sleep(120)'), msgs)
        self.isin(('Storm runtime cancelled.', q), msgs)
