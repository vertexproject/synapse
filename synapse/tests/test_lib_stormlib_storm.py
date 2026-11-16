import asyncio

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

            # lint
            lintq = '''
                $retn = ([])
                for $finding in $lib.storm.lint($text, select=$select, ignore=$ignore, enable=$enable, v3_ready=$v3_ready) {
                    $retn.append($finding)
                }
                return($retn)
            '''

            async def lint(text, select=None, ignore=None, enable=None, v3_ready=False):
                opts = {'readonly': True,
                        'vars': {'text': text, 'select': select, 'ignore': ignore, 'enable': enable,
                                 'v3_ready': v3_ready}}
                return await core.callStorm(lintq, opts=opts)

            findings = await lint('$x = $lib.list()')
            self.eq(findings, [{'rule': 'S005', 'severity': 'low', 'line': 1, 'column': 6,
                                'mesg': 'Use a list literal such as ([]) instead of $lib.list().'}])

            self.eq([], await lint('$x = ([])'))

            findings = await lint('$x = (')
            self.len(1, findings)
            self.eq('E001', findings[0]['rule'])
            self.eq('high', findings[0]['severity'])
            self.eq((1, 6), (findings[0]['line'], findings[0]['column']))

            text = 'inet:fqdn | if $x { [ :zone=$x ] }'
            self.eq([], await lint(text))
            self.eq(['S010'], [f['rule'] for f in await lint(text, enable=('S010',))])
            self.eq(['S010'], [f['rule'] for f in await lint(text, enable=('S01',))])

            # select replaces the default rule set, enable adds to it
            text = '$x = $lib.list() return($lib.null) inet:fqdn | if $x { [ :zone=$x ] }'
            self.eq(['S005', 'S004', 'S010'], [f['rule'] for f in await lint(text, enable=('S010',))])
            self.eq(['S010'], [f['rule'] for f in await lint(text, select=('S010',))])
            self.eq(['S010'], [f['rule'] for f in await lint(text, select=(), enable=('S010',))])
            self.eq([], await lint(text, select=()))
            self.eq(['S004', 'S010'], [f['rule'] for f in await lint(text, select=('S004',), enable=('S010',))])

            findings = await lint(text, select=(), v3_ready=True)
            self.eq(['R001'], [f['rule'] for f in findings])

            text = '$x = $lib.list() return($lib.null)'
            self.eq(['S005', 'S004'], [f['rule'] for f in await lint(text)])
            self.eq(['S004'], [f['rule'] for f in await lint(text, ignore=('S005',))])
            self.eq([], await lint(text, ignore=('S',)))
            self.eq([], await lint(text, select=('S005',), ignore=('S005',)))

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = ([])', enable=('Z999',))

            self.eq("Unknown lint rule or prefix: 'Z999'", cm.exception.get('mesg'))
            self.eq('Z999', cm.exception.get('name'))

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = ([])', enable=('newp', 'nada', 'never'))

            self.eq("Unknown lint rule or prefix: 'newp'", cm.exception.get('mesg'))
            self.eq('newp', cm.exception.get('name'))

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = ([])', ignore=('Z',))

            self.eq('Z', cm.exception.get('name'))

            with self.raises(s_exc.BadArg) as cm:
                await lint('$x = ([])', select=('Z',))

            self.eq('Z', cm.exception.get('name'))

            for name in ('select', 'ignore', 'enable'):

                with self.raises(s_exc.BadArg) as cm:
                    await lint('$x = ([])', **{name: 'S010'})

                self.eq(f'{name} must be a list of rule IDs or ID prefixes.', cm.exception.get('mesg'))
                self.eq(name, cm.exception.get('name'))

                with self.raises(s_exc.BadArg) as cm:
                    await lint('$x = ([])', **{name: ('S010', 1)})

                self.eq(f'{name} must be a list of rule IDs or ID prefixes.', cm.exception.get('mesg'))
                self.eq(name, cm.exception.get('name'))

            # positions in an embedded query are relative to its text
            q = '''
                $query = ${
                    inet:fqdn
                    $x = $lib.list()
                }
                $retn = ([])
                for $finding in $lib.storm.lint($query) { $retn.append($finding) }
                return($retn)
            '''
            findings = await core.callStorm(q, opts={'readonly': True})
            self.eq(findings, [{'rule': 'S005', 'severity': 'low', 'line': 3, 'column': 26,
                                'mesg': 'Use a list literal such as ([]) instead of $lib.list().'}])

            # S012 only reports a prop which is in the Cortex data model
            await core.callStorm('''
                $lib.model.ext.addForm(_foo:bar, str, ({}), ({}))
                $lib.model.ext.addFormProp(_foo:bar, baz, (str, ({})), ({}))
            ''')
            self.eq(['S012'], [f['rule'] for f in await lint('_foo:bar +:baz=woot')])
            self.eq([], await lint('_foo:newp +:baz=woot'))

            self.eq([], await lint('inet:ipv4'))
            findings = await lint('inet:ipv4', v3_ready=True)
            self.eq(findings, [{'rule': 'M001', 'severity': 'high', 'line': 1, 'column': 1,
                                'mesg': 'inet:ipv4 is renamed to inet:ip in 3.x.'}])
            self.eq([], await lint('inet:ipv4', ignore=('M',), v3_ready=True))
            self.eq(['M001'], [f['rule'] for f in await lint('inet:ipv4', select=('M001',))])

            # storm.lint command
            msgs = await core.stormlist('storm.lint "$x = $lib.list() return($lib.null)"', opts={'readonly': True})
            self.stormHasNoWarnErr(msgs)
            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.eq(prints, [
                '1:6: S005 Use a list literal such as ([]) instead of $lib.list().',
                '1:18: S004 Use return() to return (null).',
                'Found 2 errors.',
            ])

            msgs = await core.stormlist('storm.lint "$x = $lib.list()"')
            self.eq(['1:6: S005 Use a list literal such as ([]) instead of $lib.list().', 'Found 1 error.'],
                    [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            msgs = await core.stormlist('storm.lint "$x = ([])"')
            self.eq(['All checks passed!'], [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            msgs = await core.stormlist('storm.lint "$x = ("')
            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.len(2, prints)
            self.true(prints[0].startswith('1:6: E001 '))
            self.eq('Found 1 error.', prints[1])

            text = '$x = $lib.list() return($lib.null) inet:fqdn | if $x { [ :zone=$x ] }'
            opts = {'vars': {'text': text}}

            msgs = await core.stormlist('storm.lint $text --enable " S010 , S00 "', opts=opts)
            self.eq(['S005', 'S004', 'S010'], [m[1]['mesg'].split()[1] for m in msgs if m[0] == 'print'][:-1])
            self.stormIsInPrint('Found 3 errors.', msgs)

            msgs = await core.stormlist('storm.lint $text --select S010,S004 --ignore S004', opts=opts)
            self.eq(['S010'], [m[1]['mesg'].split()[1] for m in msgs if m[0] == 'print'][:-1])

            msgs = await core.stormlist('storm.lint $text --select "" --enable S01', opts=opts)
            self.eq(['S010'], [m[1]['mesg'].split()[1] for m in msgs if m[0] == 'print'][:-1])

            msgs = await core.stormlist('storm.lint $text --select "" --v3-ready', opts=opts)
            self.eq(['R001'], [m[1]['mesg'].split()[1] for m in msgs if m[0] == 'print'][:-1])

            msgs = await core.stormlist('storm.lint inet:ipv4 --v3-ready')
            self.stormIsInPrint('1:1: M001 inet:ipv4 is renamed to inet:ip in 3.x.', msgs)

            msgs = await core.stormlist('storm.lint inet:ipv4 --v3-ready --ignore M')
            self.stormIsInPrint('All checks passed!', msgs)

            msgs = await core.stormlist('storm.lint "$x = ([])" --enable newp,nada,never')
            self.stormIsInErr("Unknown lint rule or prefix: 'newp'", msgs)

            msgs = await core.stormlist('storm.lint')
            self.stormIsInErr('storm.lint requires text to lint unless --show-rules is given.', msgs)

            msgs = await core.stormlist('storm.lint ${ $x = (1) }', opts={'readonly': True})
            self.stormIsInPrint('All checks passed!', msgs)

            # positions in an embedded query are relative to its text
            msgs = await core.stormlist('''
                storm.lint ${
                    inet:fqdn
                    $x = $lib.list()
                }
            ''')
            self.stormIsInPrint('3:26: S005 Use a list literal such as ([]) instead of $lib.list().', msgs)

            # runtsafe text is linted once and inbound nodes pass through
            await core.nodes('[ it:dev:str="$x = $lib.list()" it:dev:str="$y = ([])" ]')
            msgs = await core.stormlist('it:dev:str storm.lint "$x = $lib.dict()"')
            self.len(2, [m for m in msgs if m[0] == 'node'])
            self.eq(['1:6: S005 Use a dict literal such as ({}) instead of $lib.dict().', 'Found 1 error.'],
                    [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            nodes = await core.nodes('it:dev:str storm.lint "$x = ([])"')
            self.eq(['$x = $lib.list()', '$y = ([])'], sorted(n.ndef[1] for n in nodes))

            # non-runtsafe text is linted for each inbound node
            msgs = await core.stormlist('it:dev:str storm.lint $node.value()')
            self.len(2, [m for m in msgs if m[0] == 'node'])
            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.isin('1:6: S005 Use a list literal such as ([]) instead of $lib.list().', prints)
            self.isin('Found 1 error.', prints)
            self.isin('All checks passed!', prints)
            self.len(3, prints)

            msgs = await core.stormlist('it:dev:str storm.lint $node.value() --ignore S005')
            self.eq(['All checks passed!', 'All checks passed!'], [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            # --show-rules prints the rules and lints nothing
            msgs = await core.stormlist('storm.lint --show-rules')
            self.stormHasNoWarnErr(msgs)
            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.eq(prints[0], 'ID    SEVERITY  DEFAULT  NAME                 DESCRIPTION')
            self.true(prints[1].startswith('E001  high      yes      parse-failure        The Storm code failed'))
            self.isin('S010  low       no       guarded-prop-set     '
                      'An if statement which only sets a property to the variable it tests. Use ?= which skips a',
                      prints)
            self.true(any(p.startswith('M001  high      v3       renamed-form ') for p in prints))
            self.notin('All checks passed!', prints)

            nodes = await core.nodes('it:dev:str storm.lint --show-rules "$x = $lib.list()"')
            self.len(2, nodes)

            msgs = await core.stormlist('it:dev:str storm.lint --show-rules')
            self.len(2, [m for m in msgs if m[0] == 'node'])
            self.notin('Found 1 error.', [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            # lintRules
            rules = await core.callStorm('return($lib.storm.lintRules())', opts={'readonly': True})
            self.eq([r['rule'] for r in rules], sorted(r['rule'] for r in rules))
            byid = {r['rule']: r for r in rules}
            self.eq(byid['S005'], {'rule': 'S005', 'name': 'lib-list-dict', 'severity': 'low',
                                   'default': True, 'v3': False, 'desc': byid['S005']['desc']})
            self.true(byid['S005']['desc'].startswith('$lib.list() and $lib.dict() should be list and dict literals'))
            self.false(byid['S010']['default'])
            self.false(byid['S010']['v3'])
            self.true(byid['S010']['desc'].endswith('This rule is off by default. Turn it on with enable.'))
            self.false(byid['M001']['default'])
            self.true(byid['M001']['v3'])
            self.true(byid['R004']['default'])
            self.false(byid['R004']['v3'])
            self.eq('E001', rules[0]['rule'])

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
                (inet:ipv4=1.2.3.4 :asn=4)
                (inet:ipv4=1.2.3.5 :asn=5)
                (inet:ipv4=1.2.3.6 :asn=10)
            ]'''))

            # runtsafe storm.exec
            with self.getLoggerStream('synapse.storm') as stream:
                q = '''
                $filter = '-:asn=10'
                inet:ipv4:asn
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
                inet:ipv4:asn
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
