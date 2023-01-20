import json
import asyncio
import datetime
import itertools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.storm as s_storm
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class StormTest(s_t_utils.SynTest):

    async def test_lib_storm_jsonexpr(self):
        async with self.getTestCore() as core:

            # test a pure const for the msgpack optimization
            retn = await core.callStorm('return((["foo"]))')
            self.eq(retn, ('foo',))

            # test a dynamic multi-entry list
            retn = await core.callStorm('$foo = "foo" return(([$foo, $foo, $foo]))')
            self.eq(retn, ('foo', 'foo', 'foo'))

            retn = await core.callStorm('return(({"foo": "bar", "baz": 10}))')
            self.eq(retn, {'foo': 'bar', 'baz': 10})

            retn = await core.callStorm('$foo=foo $bar=bar return(({$foo: $bar, "baz": 10}))')
            self.eq(retn, {'foo': 'bar', 'baz': 10})

            retn = await core.callStorm('return(({"foo": "bar", "baz": 0x10}))')
            self.eq(retn, {'foo': 'bar', 'baz': 16})

            retn = await core.callStorm('''
                $list = (["foo"])
                $list.append(bar)
                return($list)
            ''')
            self.eq(retn, ('foo', 'bar'))

            retn = await core.callStorm('''
                $dict = ({"foo": "bar"})
                $dict.baz = (10)
                return($dict)
            ''')
            self.eq(retn, {'foo': 'bar', 'baz': 10})

            retn = await core.callStorm('return(([]))')
            self.eq(retn, ())

            retn = await core.callStorm('return((["foo",]))')
            self.eq(retn, ('foo',))

            retn = await core.callStorm('return((["foo" , ]))')
            self.eq(retn, ('foo',))

            retn = await core.callStorm('return(({}))')
            self.eq(retn, {})

            retn = await core.callStorm('return(({"foo": "bar", "baz": 10,}))')
            self.eq(retn, {'foo': 'bar', 'baz': 10})

            retn = await core.callStorm('return(({"foo": "bar", "baz": 10 , }))')
            self.eq(retn, {'foo': 'bar', 'baz': 10})

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('return((["foo" "foo"]))')

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('return((["foo", "foo", ,]))')

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('return(({"foo": "bar" "baz": 10}))')

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('return(({"foo": "bar", "baz": 10, ,}))')

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('return(({"foo": "bar", "baz": foo}))')

    async def test_lib_storm_triplequote(self):
        async with self.getTestCore() as core:
            retn = await core.callStorm("""
            return($lib.yaml.load('''
                foo: bar
                baz:
                    - hehe's
                    - haha's
            '''))
            """)
            self.eq(retn, {'foo': 'bar', 'baz': ("hehe's", "haha's")})

            self.eq(''' '"lol"' ''', await core.callStorm("""return(''' '"lol"' ''')"""))

            retn = await core.callStorm("""return(('''foo bar''', '''baz faz'''))""")
            self.eq(retn, ('foo bar', 'baz faz'))
            self.eq("'''", await core.callStorm("""return("'''")"""))

    async def test_lib_storm_formatstring(self):
        async with self.getTestCore() as core:

            msgs = await core.stormlist('''
                [(inet:ipv4=0.0.0.0 :asn=5 .seen=((0), (1)) +#foo)
                 (inet:ipv4=1.1.1.1 :asn=6 .seen=((1), (2)) +#foo=((3),(4)))]

                $lib.print(`ip={$node.repr()} asn={:asn} .seen={.seen} foo={#foo} {:asn=5}`)
            ''')
            self.stormIsInPrint('ip=0.0.0.0 asn=5 .seen=(0, 1) foo=(None, None) True', msgs)
            self.stormIsInPrint('ip=1.1.1.1 asn=6 .seen=(1, 2) foo=(3, 4) False', msgs)

            retn = await core.callStorm('''
                $foo = mystr
                return(`format string \\`foo=\\{$foo}\\` returns foo={$foo}`)
            ''')
            self.eq('format string `foo={$foo}` returns foo=mystr', retn)

            self.eq('', await core.callStorm('return(``)'))

            retn = await core.callStorm('''
                $foo=(2)
                function test(x, y) { return(($x+$y)) }

                return(`valu={(1)+$foo+$test(3,(4+$foo))}`)
            ''')
            self.eq('valu=12', retn)

            retn = await core.callStorm('''
                $foo=(2)
                function test(x, y) { return(($x+$y)) }

                return(`valu={(1)+$foo+$test(0x03,(4+$foo))}`)
            ''')
            self.eq('valu=12', retn)

            q = "$hehe=({'k': 'v'}) $fs=$lib.str.format('{v}56', v=$hehe) return((`{$hehe}56`, $fs))"
            retn = await core.callStorm(q)
            self.eq("{'k': 'v'}56", retn[0])
            self.eq(retn[0], retn[1])

            retn = await core.callStorm('''$foo=bar $baz=faz return(`foo={$foo}
            baz={$baz}
            `)''')
            self.eq(retn, '''foo=bar
            baz=faz
            ''')

    async def test_lib_storm_emit(self):
        async with self.getTestCore() as core:
            self.eq(('foo', 'bar'), await core.callStorm('''
                function generate() {
                    emit foo
                    emit bar
                }
                function makelist() {
                    $retn = $lib.list()
                    for $item in $generate() { $retn.append($item) }
                    return($retn)
                }
                return($makelist())
            '''))

            self.eq(('vertex.link', 'woot.com'), await core.callStorm('''
                function generate() {
                    [ inet:fqdn=vertex.link inet:fqdn=woot.com ]
                    emit $node.repr()
                }
                function makelist() {
                    $retn = $lib.list()
                    for $item in $generate() { $retn.append($item) }
                    return($retn)
                }
                return($makelist())
            '''))

            msgs = await core.stormlist('''
                function generate() {
                    emit foo
                    $lib.raise(omg, omg)
                }
                for $item in $generate() { $lib.print($item) }
            ''')
            self.stormIsInPrint('foo', msgs)
            self.len(1, [m for m in msgs if m[0] == 'err' and m[1][0] == 'StormRaise'])

            msgs = await core.stormlist('''
                function generate(items) {
                    for $item in $items {
                        if ($item = "woot") { stop }
                        emit $item
                    }
                }
                for $item in $generate((foo, woot, bar)) { $lib.print($item) }
            ''')
            self.stormIsInPrint('foo', msgs)
            self.stormNotInPrint('woot', msgs)
            self.stormNotInPrint('bar', msgs)

            msgs = await core.stormlist('''
                function generate(items) {
                    for $item in $items {
                        [ it:dev:str=$item ]
                        if ($node.repr() = "woot") { stop }
                        emit $item
                    }
                }
                for $item in $generate((foo, woot, bar)) { $lib.print($item) }
            ''')
            self.stormIsInPrint('foo', msgs)
            self.stormNotInPrint('woot', msgs)
            self.stormNotInPrint('bar', msgs)

            nodes = await core.nodes('''
                function generate(items) {
                    for $item in $items {
                        if ($item = "woot") { stop }
                        [ it:dev:str=$item ]
                    }
                }
                yield $generate((foo, woot, bar))
            ''')
            self.len(1, nodes)
            self.eq('foo', nodes[0].ndef[1])

            msgs = await core.stormlist('''
                function generate() {
                    for $i in $lib.range(3) {
                        $lib.print(`inner {$i}`)
                        emit $i
                    }
                }
                for $i in $generate() {
                    $lib.print(`outer {$i}`)
                    for $_ in $lib.range(5) {}
                    break
                }
            ''')
            prnt = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.eq(prnt, ['inner 0', 'outer 0'])

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('emit foo'))

            # include a quick test for using stop in a node yielder

    async def test_lib_storm_intersect(self):
        async with self.getTestCore() as core:
            await core.nodes('''
                [(ou:org=* :names=(foo, bar))]
                [(ou:org=* :names=(foo, baz))]
                [(ou:org=* :names=(foo, hehe))]
            ''')
            nodes = await core.nodes('ou:org | intersect { -> ou:name }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'foo')

            msgs = await core.stormlist('ou:org $foo=$node.value() | intersect $foo')
            self.stormIsInErr('intersect arguments must be runtsafe', msgs)

    async def test_lib_storm_trycatch(self):

        async with self.getTestCore() as core:
            self.eq(1, await core.callStorm('''
                try {
                    $lib.raise(FooBar, "Foo that bars!", baz=faz)
                    return((0))
                } catch FooBar as err {
                    return((1))
                }
            '''))

            self.eq(1, await core.callStorm('''
                try {
                    $lib.raise(FooBar, "Foo that bars!", baz=faz)
                    return((0))
                } catch (FooBar, BazFaz) as err {
                    return((1))
                } catch * as err {
                    return((2))
                }
            '''))

            self.eq('Gronk', await core.callStorm('''
                try {
                    $lib.raise(Gronk, "Foo that bars!", baz=faz)
                    return((0))
                } catch (FooBar, BazFaz) as err {
                    return((1))
                } catch * as err {
                    return($err.name)
                }
            '''))

            self.eq('Foo', await core.callStorm('''
                try {
                    $lib.telepath.open($url).callStorm("$lib.raise(Foo, bar, hehe=haha)")
                } catch Foo as err {
                    return($err.name)
                }
            ''', opts={'vars': {'url': core.getLocalUrl()}}))

            msgs = await core.stormlist('''
                [ inet:fqdn=vertex.link ]
                try {
                    [ :lolz = 10 ]
                } catch * as err {
                    $lib.print($err.name)
                }
            ''')
            self.stormIsInPrint('NoSuchProp', msgs)
            self.len(1, [m for m in msgs if m[0] == 'node'])

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('''
                    [ inet:fqdn=vertex.link ]
                    try {
                        [ :lolz = 10 ]
                    } catch FooBar as err {}
                ''')

            with self.raises(s_exc.NoSuchForm):
                await core.nodes('''
                    try {
                        [ hurr:durr=vertex.link ]
                    } catch FooBar as err {}
                ''')

            # We will do lookups with the Raises command to raise the proper synerr
            with self.raises(s_exc.NoSuchForm):
                await core.nodes('''
                    try {
                        $lib.raise(NoSuchForm, 'mesg here')
                    } catch FooBar as err {}
                ''')

            # We punch through the errname in the exception
            with self.raises(s_exc.StormRaise) as cm:
                await core.nodes('''
                    try {
                        $lib.raise(NoSuchExceptionNewpers, 'mesg here')
                    } catch FooBar as err {}
                ''')
            self.eq(cm.exception.errname, 'NoSuchExceptionNewpers')
            self.eq(cm.exception.get('errname'), 'NoSuchExceptionNewpers')

            self.len(1, await core.nodes('''
                [ inet:fqdn=vertex.link ]
                try {
                    $lib.print($node.repr())
                } catch FooBar as err {
                    $lib.print(FooBar)
                }
            '''))

            self.len(1, await core.nodes('''
                try {
                    [ inet:fqdn=vertex.link ]
                } catch FooBar as err {
                    $lib.print(FooBar)
                }
            '''))

            self.len(1, await core.nodes('''
                try {
                    $lib.raise(FooBar, foobar)
                } catch FooBar as err {
                    [ inet:fqdn=vertex.link ]
                }
            '''))

            self.len(2, await core.nodes('''
                [ inet:fqdn=woot.link ]
                try {
                    $lib.raise(FooBar, foobar)
                } catch FooBar as err {
                    [ inet:fqdn=vertex.link ]
                }
            '''))

            # Nesting works
            q = '''
            $lib.print('init')
            try {
                $lib.print('nested try catch')
                try {
                    $lib.print('nested raise')
                    $lib.raise($errname, mesg='inner error!')
                } catch foo as err {
                    $lib.print('caught foo e={e}', e=$err)
                    if $innerRaise {
                        $lib.raise($innererrname, mesg='inner error!')
                    }
                }
                $lib.print('no foo err!')
            } catch bar as err {
                $lib.print('caught bar e={e}', e=$err)
            }
            $lib.print('fin')'''
            msgs = await core.stormlist(q, {'vars': {'errname': 'foo', 'innererrname': '', 'innerRaise': False, }})
            self.stormIsInPrint('caught foo', msgs)
            self.stormNotInPrint('caught bar', msgs)
            self.stormIsInPrint('fin', msgs)

            msgs = await core.stormlist(q, {'vars': {'errname': 'bar', 'innererrname': '', 'innerRaise': False, }})
            self.stormNotInPrint('caught foo', msgs)
            self.stormIsInPrint('caught bar', msgs)
            self.stormIsInPrint('fin', msgs)

            msgs = await core.stormlist(q, {'vars': {'errname': 'baz', 'innererrname': '', 'innerRaise': False, }})
            self.stormNotInPrint('caught foo', msgs)
            self.stormNotInPrint('caught bar', msgs)
            self.stormNotInPrint('fin', msgs)

            # We can also raise inside of a catch block
            msgs = await core.stormlist(q, {'vars': {'errname': 'foo', 'innererrname': 'bar', 'innerRaise': True, }})
            self.stormIsInPrint('caught foo', msgs)
            self.stormIsInPrint('caught bar', msgs)
            self.stormIsInPrint('fin', msgs)

            msgs = await core.stormlist(q, {'vars': {'errname': 'foo', 'innererrname': 'baz', 'innerRaise': True, }})
            self.stormIsInPrint('caught foo', msgs)
            self.stormNotInPrint('caught bar', msgs)
            self.stormNotInPrint('fin', msgs)

            # The items in the catch list must be a a str or list of iterables.
            # Anything else raises a Storm runtime error
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('''
                try {
                    $lib.raise(foo, test)
                } catch $lib.true as err{
                    $lib.print('caught')
                }
                ''')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('''
                try {
                    $lib.raise(foo, test)
                } catch (1) as err {
                    $lib.print('caught')
                }
                ''')

            # A list of mixed objects works
            msgs = await core.stormlist('''
            try {
                $lib.raise(foo, test)
            } catch (1, $lib.true, foo) as err {
                $lib.print('caught err={e}', e=$err)
            }
            ''')
            self.stormIsInPrint('caught err=', msgs)

    async def test_storm_ifcond_fix(self):

        async with self.getTestCore() as core:
            msgs = await core.stormlist('''
                [ inet:fqdn=vertex.link inet:fqdn=foo.com inet:fqdn=bar.com ]

                function stuff(x) {
                  if ($x.0 = "vertex.link") {
                      return((1))
                  }
                  return((0))
                }

                $alerts = $lib.list()
                { $alerts.append($node.repr()) }

                $bool = $stuff($alerts)

                if $bool { $lib.print($alerts) }

                | spin
            ''')
            self.stormNotInPrint('foo.com', msgs)

    async def test_lib_storm_basics(self):
        # a catch-all bucket for simple tests to avoid cortex construction
        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchVar):
                await core.nodes('inet:ipv4=$ipv4')

            # test that runtsafe vars stay runtsafe
            msgs = await core.stormlist('$foo=bar $lib.print($foo) if $node { $foo=$node.value() }')
            self.stormIsInPrint('bar', msgs)

            # test storm background command
            await core.nodes('''
                $lib.queue.add(foo)
                [inet:ipv4=1.2.3.4]
                background {
                    [it:dev:str=haha]
                    fini{
                        $lib.queue.get(foo).put(hehe)
                    }
                }''')
            self.eq((0, 'hehe'), await core.callStorm('return($lib.queue.get(foo).get())'))

            await core.nodes('''$lib.queue.gen(bar)
            background ${ $lib.queue.get(bar).put(haha) }
            ''')
            self.eq((0, 'haha'), await core.callStorm('return($lib.queue.get(bar).get())'))

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ ou:org=*] $text = $node.repr() | background $text')

            with self.raises(s_exc.NoSuchVar):
                await core.nodes('background { $lib.print($foo) }')

            # test the parallel command
            nodes = await core.nodes('parallel --size 4 { [ ou:org=* ] }')
            self.len(4, nodes)

            # check that subquery validation happens
            with self.raises(s_exc.NoSuchVar):
                await core.nodes('parallel --size 4 { [ ou:org=$foo ] }')

            # check that an exception on inbound percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=* ou:org=foo ] | parallel { [:name=bar] }')

            # check that an exception in the parallel pipeline percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('parallel { [ou:org=foo] }')

            nodes = await core.nodes('ou:org | parallel {[ :name=foo ]}')
            self.true(all([n.get('name') == 'foo' for n in nodes]))

            # Runtsafety test
            q = '[ inet:fqdn=www.vertex.link ] $q={ :domain -> inet:fqdn } | parallel $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            # test $lib.exit() and the StormExit handlers
            msgs = [m async for m in core.view.storm('$lib.exit()')]
            self.eq(msgs[-1][0], 'fini')

            # test that the view command functions correctly
            iden = s_common.guid()
            view0 = await core.callStorm('return($lib.view.get().fork().iden)')
            with self.raises(s_exc.NoSuchVar):
                opts = {'vars': {'view': view0}}
                await core.nodes('view.exec $view { [ ou:org=$iden] }', opts=opts)

            opts = {'vars': {'view': view0, 'iden': iden}}
            self.len(0, await core.nodes('view.exec $view { [ ou:org=$iden] }', opts=opts))

            opts = {'view': view0, 'vars': {'iden': iden}}
            self.len(1, await core.nodes('ou:org=$iden', opts=opts))

            # check safe per-node execution of view.exec
            view1 = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'vars': {'view': view1}}
            # lol...
            self.len(1, await core.nodes('''
                [ ou:org=$view :name="[ inet:ipv4=1.2.3.4 ]" ]
                $foo=$node.repr() $bar=:name
                | view.exec $foo $bar
            ''', opts=opts))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4', opts={'view': view1}))

            self.len(0, await core.nodes('$x = $lib.null if ($x and $x > 20) { [ ps:contact=* ] }'))
            self.len(1, await core.nodes('$x = $lib.null if ($lib.true or $x > 20) { [ ps:contact=* ] }'))

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            cmd0 = {
                'name': 'asroot.not',
                'storm': '[ ou:org=* ]',
            }
            cmd1 = {
                'name': 'asroot.yep',
                'storm': '[ it:dev:str=$lib.user.allowed(node.add.it:dev:str) ]',
                'asroot': True,
            }
            await core.setStormCmd(cmd0)
            await core.setStormCmd(cmd1)

            opts = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.nodes('asroot.not', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('asroot.yep', opts=opts)

            await visi.addRule((True, ('storm', 'asroot', 'cmd', 'asroot', 'yep')))

            nodes = await core.nodes('asroot.yep', opts=opts)
            self.len(1, nodes)
            self.eq('false', nodes[0].ndef[1])

            await visi.addRule((True, ('storm', 'asroot', 'cmd', 'asroot')))
            self.len(1, await core.nodes('asroot.not', opts=opts))

            pkg0 = {
                'name': 'foopkg',
                'version': (0, 0, 1),
                'modules': (
                    {
                        'name': 'foo.bar',
                        'storm': '''
                            function lol() {
                                [ ou:org=* ]
                                return($node.iden())
                            }
                            function dyncall() {
                                return($lib.feed.list())
                            }
                            function dyniter() {
                                for $item in $lib.queue.add(dyniter).gets(wait=$lib.false) {}
                                return(woot)
                            }
                        ''',
                        'asroot': True,
                    },
                    {
                        'name': 'foo.baz',
                        'storm': 'function lol() { [ ou:org=* ] return($node.iden()) }',
                    },
                )
            }

            emptypkg = {
                'name': 'emptypkg',
                'modules': ({'name': 'emptymod'},),
            }

            strverpkg = {
                'name': 'strvers',
                'version': (0, 0, 1),
                'modules': ({'name': 'strvers', 'storm': ''},),
                'configvars': (
                    {
                        'name': 'foo',
                        'varname': 'foo',
                        'desc': 'foo desc',
                        'scopes': ['self'],
                        'type': 'inet:fqdn',
                    },
                    {
                        'name': 'bar',
                        'varname': 'bar',
                        'desc': 'bar desc',
                        'scopes': ['global'],
                        'type': ['inet:fqdn', ['str', 'inet:url']],
                    },
                )
            }
            await core.loadStormPkg(emptypkg)
            await core.addStormPkg(strverpkg)

            await core.loadStormPkg(pkg0)

            await core.nodes('$lib.import(foo.baz)', opts=opts)
            await core.nodes('$lib.import(foo.baz, reqvers="==0.0.1")', opts=opts)
            await core.nodes('$lib.import(foo.baz, reqvers=">=0.0.1")', opts=opts)
            await core.nodes('$lib.import(strvers, reqvers="==0.0.1")', opts=opts)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.import(emptymod, reqvers=">=0.0.1")', opts=opts)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.import(foo.baz, reqvers=">=0.0.2")', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.import(foo.bar)', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.import(foo.baz).lol()', opts=opts)

            await visi.addRule((True, ('storm', 'asroot', 'mod', 'foo', 'bar')))
            self.len(1, await core.nodes('yield $lib.import(foo.bar).lol()', opts=opts))

            await visi.addRule((True, ('storm', 'asroot', 'mod', 'foo')))
            self.len(1, await core.nodes('yield $lib.import(foo.baz).lol()', opts=opts))

            # coverage for dyncall/dyniter with asroot...
            await core.nodes('$lib.import(foo.bar).dyncall()', opts=opts)
            await core.nodes('$lib.import(foo.bar).dyniter()', opts=opts)

            # Call a non-existent function on the lib
            msgs = await core.stormlist('$mod = $lib.import(foo.bar) $lib.print($mod) $mod.newp()')
            self.stormIsInPrint('Imported Module foo.bar', msgs)
            self.stormIsInErr('Cannot find name [newp]', msgs)

            self.eq(s_version.commit, await core.callStorm('return($lib.version.commit())'))
            self.eq(s_version.version, await core.callStorm('return($lib.version.synapse())'))
            self.true(await core.callStorm('return($lib.version.matches($lib.version.synapse(), ">=2.9.0"))'))
            self.false(await core.callStorm('return($lib.version.matches($lib.version.synapse(), ">0.0.1,<2.0"))'))

            # check that the feed API uses toprim
            email = await core.callStorm('''
                $iden = $lib.guid()
                $props = $lib.dict(email=visi@vertex.link)
                $lib.feed.ingest(syn.nodes, (
                    ( (ps:contact, $iden), $lib.dict(props=$props)),
                ))
                ps:contact=$iden
                return(:email)
            ''')
            self.eq(email, 'visi@vertex.link')

            email = await core.callStorm('''
                $iden = $lib.guid()
                $props = $lib.dict(email=visi@vertex.link)
                yield $lib.feed.genr(syn.nodes, (
                    ( (ps:contact, $iden), $lib.dict(props=$props)),
                ))
                return(:email)
            ''')
            self.eq(email, 'visi@vertex.link')

            pkg0 = {'name': 'hehe', 'version': '1.2.3'}
            await core.addStormPkg(pkg0)
            self.eq('1.2.3', await core.callStorm('return($lib.pkg.get(hehe).version)'))

            self.eq(None, await core.callStorm('return($lib.pkg.get(nopkg))'))

            pkg1 = {'name': 'haha', 'version': '1.2.3'}
            await core.addStormPkg(pkg1)
            msgs = await core.stormlist('pkg.list')
            self.isin('haha', msgs[2][1]['mesg'])
            self.isin('hehe', msgs[3][1]['mesg'])

            self.true(await core.callStorm('return($lib.pkg.has(haha))'))

            await core.delStormPkg('haha')
            self.none(await core.callStorm('return($lib.pkg.get(haha))'))
            self.false(await core.callStorm('return($lib.pkg.has(haha))'))

            # test for $lib.queue.gen()
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))
            # and again to test *not* creating it...
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))

            self.eq({'foo': 'bar'}, await core.callStorm('return($lib.dict(    foo    =    bar   ))'))

            ddef0 = await core.callStorm('return($lib.dmon.add(${ $lib.queue.gen(hehedmon).put(lolz) $lib.time.sleep(10) }, name=hehedmon))')
            ddef1 = await core.callStorm('return($lib.dmon.get($iden))', opts={'vars': {'iden': ddef0.get('iden')}})
            self.none(await core.callStorm('return($lib.dmon.get(newp))'))

            self.eq(ddef0['iden'], ddef1['iden'])

            self.eq((0, 'lolz'), await core.callStorm('return($lib.queue.gen(hehedmon).get(0))'))

            task = core.stormdmons.getDmon(ddef0['iden']).task
            self.true(await core.callStorm(f'return($lib.dmon.bump($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.ne(task, core.stormdmons.getDmon(ddef0['iden']).task)

            self.true(await core.callStorm(f'return($lib.dmon.stop($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.none(core.stormdmons.getDmon(ddef0['iden']).task)
            self.false(await core.callStorm(f'return($lib.dmon.get($iden).enabled)', opts={'vars': {'iden': ddef0['iden']}}))
            self.false(await core.callStorm(f'return($lib.dmon.stop($iden))', opts={'vars': {'iden': ddef0['iden']}}))

            self.true(await core.callStorm(f'return($lib.dmon.start($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.nn(core.stormdmons.getDmon(ddef0['iden']).task)
            self.true(await core.callStorm(f'return($lib.dmon.get($iden).enabled)', opts={'vars': {'iden': ddef0['iden']}}))
            self.false(await core.callStorm(f'return($lib.dmon.start($iden))', opts={'vars': {'iden': ddef0['iden']}}))

            self.false(await core.callStorm(f'return($lib.dmon.bump(newp))'))
            self.false(await core.callStorm(f'return($lib.dmon.stop(newp))'))
            self.false(await core.callStorm(f'return($lib.dmon.start(newp))'))

            self.eq((1, 'lolz'), await core.callStorm('return($lib.queue.gen(hehedmon).get(1))'))

            async with core.getLocalProxy() as proxy:
                self.nn(await proxy.getStormDmon(ddef0['iden']))
                self.true(await proxy.bumpStormDmon(ddef0['iden']))
                self.true(await proxy.disableStormDmon(ddef0['iden']))
                self.true(await proxy.enableStormDmon(ddef0['iden']))
                self.false(await proxy.bumpStormDmon('newp'))
                self.false(await proxy.disableStormDmon('newp'))
                self.false(await proxy.enableStormDmon('newp'))

            await core.callStorm('[ inet:ipv4=11.22.33.44 :asn=56 inet:asn=99]')
            await core.callStorm('[ ps:person=* +#foo ]')

            view, layr = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')

            opts = {'view': view}
            self.len(0, await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for $item in $layr.getStorNodes() {
                    $list.append($item)
                }
                return($list)''', opts=opts))

            await core.addTagProp('score', ('int', {}), {})
            await core.callStorm('[ inet:ipv4=11.22.33.44 :asn=99 inet:fqdn=55667788.link +#foo=2020 +#foo:score=100]', opts=opts)
            await core.callStorm('inet:ipv4=11.22.33.44 $node.data.set(foo, bar)', opts=opts)
            await core.callStorm('inet:ipv4=11.22.33.44 [ +(blahverb)> { inet:asn=99 } ]', opts=opts)

            sodes = await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for $item in $layr.getStorNodes() {
                    $list.append($item)
                }
                return($list)''', opts=opts)
            self.len(2, sodes)

            ipv4 = await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for ($buid, $sode) in $layr.getStorNodes() {
                    yield $buid
                }
                +inet:ipv4
                return($node.repr())''', opts=opts)
            self.eq('11.22.33.44', ipv4)

            sodes = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getStorNodes())', opts=opts)
            self.eq((1577836800000, 1577836800001), sodes[0]['tags']['foo'])
            self.eq((99, 9), sodes[0]['props']['asn'])
            self.eq((185999660, 4), sodes[1]['valu'])
            self.eq(('unicast', 1), sodes[1]['props']['type'])
            self.eq((56, 9), sodes[1]['props']['asn'])

            bylayer = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getByLayer())', opts=opts)
            self.ne(bylayer['ndef'], layr)
            self.eq(bylayer['props']['asn'], layr)
            self.eq(bylayer['tags']['foo'], layr)
            self.ne(bylayer['props']['type'], layr)

            msgs = await core.stormlist('inet:ipv4=11.22.33.44 | merge', opts=opts)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4:asn = 99', msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo = ('2020/01/01 00:00:00.000', '2020/01/01 00:00:00.001')", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo:score = 100", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 DATA foo = 'bar'", msgs)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 +(blahverb)> a0df14eab785847912993519f5606bbe741ad81afb51b81455ac6982a5686436', msgs)

            msgs = await core.stormlist('ps:person | merge --diff', opts=opts)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4:asn = 99', msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo = ('2020/01/01 00:00:00.000', '2020/01/01 00:00:00.001')", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo:score = 100", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 DATA foo = 'bar'", msgs)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 +(blahverb)> a0df14eab785847912993519f5606bbe741ad81afb51b81455ac6982a5686436', msgs)

            await core.callStorm('inet:ipv4=11.22.33.44 | merge --apply', opts=opts)
            nodes = await core.nodes('inet:ipv4=11.22.33.44')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo'))
            self.eq(99, nodes[0].get('asn'))

            bylayer = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getByLayer())', opts=opts)
            self.ne(bylayer['ndef'], layr)
            self.ne(bylayer['props']['asn'], layr)
            self.ne(bylayer['tags']['foo'], layr)

            # confirm that we moved node data and light edges
            self.eq('bar', await core.callStorm('inet:ipv4=11.22.33.44 return($node.data.get(foo))'))
            self.eq(99, await core.callStorm('inet:ipv4=11.22.33.44 -(blahverb)> inet:asn return($node.value())'))
            self.eq(100, await core.callStorm('inet:ipv4=11.22.33.44 return(#foo:score)'))

            sodes = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getStorNodes())', opts=opts)
            self.eq(sodes[0], {})

            with self.raises(s_exc.CantMergeView):
                await core.callStorm('inet:ipv4=11.22.33.44 | merge')

            # test printing a merge that the node was created in the top layer
            msgs = await core.stormlist('[ inet:fqdn=mvmnasde.com ] | merge', opts=opts)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn = mvmnasde.com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:host = mvmnasde', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:domain = com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:issuffix = False', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:iszone = True', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:zone = mvmnasde.com', msgs)

            # test that a user without perms can diff but not apply
            await visi.addRule((True, ('view', 'read')))

            msgs = await core.stormlist('merge --diff --apply', opts={'view': view, 'user': visi.iden})
            self.stormIsInErr('must have permission node.del.inet:fqdn', msgs)

            msgs = await core.stormlist('ps:person | merge --diff', opts={'view': view, 'user': visi.iden})
            self.stormIsInPrint('inet:fqdn = mvmnasde.com', msgs)

            # merge all the nodes with anything stored in the top layer...
            await core.callStorm('''
                for ($buid, $sode) in $lib.view.get().layers.0.getStorNodes() {
                    yield $buid
                }
                | merge --apply
            ''', opts=opts)

            self.len(0, await core.callStorm('''
                $list = $lib.list()
                for ($buid, $sode) in $lib.view.get().layers.0.getStorNodes() {
                    $list.append($buid)
                }
                return($list)
            ''', opts=opts))

            self.eq('c8af8cfbcc36ba5dec9858124f8f014d', await core.callStorm('''
                $iden = c8af8cfbcc36ba5dec9858124f8f014d
                [ inet:fqdn=vertex.link <(woots)+ {[ meta:source=$iden ]} ]
                <(woots)- meta:source
                return($node.value())
            '''))

            with self.raises(s_exc.BadArg):
                await core.callStorm('inet:fqdn=vertex.link $tags = $node.globtags(foo.***)')

            nodes = await core.nodes('$form=inet:fqdn [ *$form=visi.com ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'visi.com'))

            # test non-runtsafe invalid form deref node add
            with self.raises(s_exc.NoSuchForm):
                await core.callStorm('[ it:dev:str=hehe:haha ] $form=$node.value() [*$form=lol]')

            async def sleeper():
                await asyncio.sleep(2)
            task = core.schedCoro(sleeper())
            self.false(await s_coro.waittask(task, timeout=0.1))

            # test some StormRuntime APIs directly...
            await core.nodes('[ inet:ipv4=1.2.3.4 ]')
            await core.nodes('[ ou:org=* ou:org=* :name=dupcorp ]')
            async with await core.view.snap(user=core.auth.rootuser) as snap:

                query = await core.getStormQuery('')
                async with snap.getStormRuntime(query) as runt:

                    self.len(1, await alist(runt.storm('inet:ipv4=1.2.3.4')))

                    self.nn(await runt.getOneNode('inet:ipv4', 0x01020304))

                    counter = itertools.count()

                    async def skipone(n):
                        if next(counter) == 0:
                            return True
                        return False

                    self.nn(await runt.getOneNode('ou:org:name', 'dupcorp', filt=skipone))

                    with self.raises(s_exc.StormRuntimeError):
                        await runt.getOneNode('ou:org:name', 'dupcorp')

            count = 5
            for i in range(count):
                await core.nodes('[ test:guid=$lib.guid() +#foo.bar]')
                await core.nodes('[ test:str=$lib.guid() ]')

            # test the node importing works...
            class ExpHandler(s_httpapi.StormHandler):
                async def get(self, name):
                    self.set_header('Content-Type', 'application/x-synapse-nodes')
                    core = self.getCore()
                    if name == 'kewl':
                        form = 'test:guid'
                    elif name == 'neat':
                        form = 'test:str'
                    else:
                        return
                    async for pode in core.exportStorm(form):
                        self.write(s_msgpack.en(pode))
                        self.flush()

            core.addHttpApi('/api/v1/exptest/(.*)', ExpHandler, {'cell': core})
            port = (await core.addHttpsPort(0, host='127.0.0.1'))[1]
            async with self.getTestCore() as subcore:
                # test that we get nodes, but in this vase, incoming node get priority
                byyield = await subcore.nodes(f'[inet:url="https://127.0.0.1:{port}/api/v1/exptest/neat"] | nodes.import --no-ssl-verify https://127.0.0.1:{port}/api/v1/exptest/kewl')
                self.len(count, byyield)
                for node in byyield:
                    self.eq(node.form.name, 'test:str')
                # we shouldn't grab any of the nodes tagged #foo.bar (ie, all the test:guid nodes)
                bytag = await subcore.nodes('#foo.bar')
                self.len(0, bytag)

                url = await subcore.nodes('inet:url')
                self.len(1, url)
                url = url[0]
                self.eq('https', url.props['proto'])
                self.eq('/api/v1/exptest/neat', url.props['path'])
                self.eq('', url.props['params'])
                self.eq(2130706433, url.props['ipv4'])
                self.eq(f'https://127.0.0.1:{port}/api/v1/exptest/neat', url.props['base'])
                self.eq(port, url.props['port'])

                # now test that param works
                byyield = await subcore.nodes(f'nodes.import --no-ssl-verify https://127.0.0.1:{port}/api/v1/exptest/kewl')
                self.len(count, byyield)
                for node in byyield:
                    self.eq(node.form.name, 'test:guid')
                    self.isin('foo.bar', node.tags)

                # bad response should give no nodes
                msgs = await subcore.stormlist(f'nodes.import --no-ssl-verify https://127.0.0.1:{port}/api/v1/lolnope/')
                self.stormHasNoErr(msgs)
                self.stormIsInWarn('nodes.import got HTTP error code', msgs)
                nodes = [x for x in msgs if x[0] == 'node']
                self.len(0, nodes)

            pkgdef = {
                'name': 'foobar',
                'version': '1.2.3',
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (),
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'conflicts': (
                        {'name': 'foobar'},
                    ),
                }
            }

            with self.raises(s_exc.StormPkgConflicts):
                await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (
                    {'name': 'foobar', 'version': None, 'desc': None, 'ok': False, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'conflicts': (
                        {'name': 'foobar', 'version': '>=1.0.0', 'desc': 'foo'},
                    ),
                }
            }

            with self.raises(s_exc.StormPkgConflicts):
                await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (
                    {'name': 'foobar', 'version': '>=1.0.0', 'desc': 'foo', 'ok': False, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'foobar', 'version': '>=2.0.0,<3.0.0'},
                    ),
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'desc': None, 'ok': False, 'actual': '1.2.3'},
                ),
                'conflicts': ()
            }, deps)

            pkgdef = {
                'name': 'lolzlolz',
                'version': '1.2.3',
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (),
                'conflicts': (),
            }, deps)

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'lolzlolz', 'version': '>=1.0.0,<2.0.0', 'desc': 'lol'},
                    ),
                    'conflicts': (
                        {'name': 'foobar', 'version': '>=3.0.0'},
                    ),
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'lolzlolz', 'version': '>=1.0.0,<2.0.0', 'desc': 'lol', 'ok': True, 'actual': '1.2.3'},
                ),
                'conflicts': (
                    {'name': 'foobar', 'version': '>=3.0.0', 'desc': None, 'ok': True, 'actual': '1.2.3'},
                )
            }, deps)

            pkgdef = {
                'name': 'zoinkszoinks',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'newpnewp', 'version': '1.2.3'},
                    ),
                    'conflicts': (
                        {'name': 'newpnewp'},
                    ),
                }
            }

            await core.addStormPkg(pkgdef)

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'newpnewp', 'version': '1.2.3', 'desc': None, 'ok': False, 'actual': None},
                ),
                'conflicts': (
                    {'name': 'newpnewp', 'version': None, 'desc': None, 'ok': True, 'actual': None},
                )
            }, deps)

            # force old-cron behavior which lacks a view
            await core.nodes('cron.add --hourly 03 { inet:ipv4 }')
            for (iden, cron) in core.agenda.list():
                cron.view = None
            await core.nodes('cron.list')

            # test that stormtypes nodes can be yielded
            self.len(1, await core.nodes('for $x in ${ [inet:ipv4=1.2.3.4] } { yield $x }'))

            self.eq({'foo': 'bar', 'baz': 'faz'}, await core.callStorm('''
                return($lib.dict( // do foo thing
                    foo /* hehe */ = /* haha */ bar, //lol
                    baz // hehe
                    = // haha
                    faz // hehe
                ))
            '''))

            self.eq(('foo', 'bar', 'baz'), await core.callStorm('''
                return($lib.list( // do foo thing
                    /* hehe */ foo /* hehe */ , /* hehe */ bar /* hehe */ , /* hehe */ baz /* hehe */
                ))
            '''))

    async def test_storm_diff_merge(self):

        async with self.getTestCore() as core:
            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')

            altview = {'view': viewiden}
            await core.nodes('[ ou:org=* :name=hehe +#hehe ]')
            await core.nodes('[ ou:org=* :name=haha +#haha ]', opts=altview)

            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('diff')

            nodes = await core.nodes('diff --prop ".created" | +ou:org', opts=altview)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'haha')

            nodes = await core.nodes('diff --prop ou:org', opts=altview)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'haha')

            nodes = await core.nodes('diff --prop ou:org:name', opts=altview)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'haha')

            nodes = await core.nodes('diff --tag haha', opts=altview)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'haha')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('diff --prop foo:bar', opts=altview)

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('diff --prop foo:bar --tag newp.newp', opts=altview)
            self.eq(cm.exception.get('mesg'),
                    'You may specify --tag *or* --prop but not both.')

            nodes = await core.nodes('diff | +ou:org', opts=altview)
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'haha')

            self.len(3, await core.nodes('ou:org | diff | +ou:org', opts=altview))
            nodes = await core.nodes('diff | merge --no-tags --apply', opts=altview)

            nodes = await core.nodes('diff | +ou:org', opts=altview)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('haha'))

            nodes = await core.nodes('ou:org:name=haha')
            self.len(1, nodes)
            self.none(nodes[0].getTag('haha'))

            self.len(2, await core.nodes('ou:org'))
            self.len(1, await core.nodes('ou:name=haha'))
            self.len(1, await core.nodes('ou:org:name=haha'))

            self.len(0, await core.nodes('#haha'))
            self.len(0, await core.nodes('ou:org#haha'))
            self.len(0, await core.nodes('syn:tag=haha'))

            self.len(1, await core.nodes('#haha', opts=altview))
            self.len(1, await core.nodes('ou:org#haha', opts=altview))
            self.len(1, await core.nodes('syn:tag=haha', opts=altview))
            self.len(1, await core.nodes('diff | +ou:org', opts=altview))

            self.len(2, await core.nodes('diff | merge --apply', opts=altview))

            self.len(1, await core.nodes('#haha'))
            self.len(1, await core.nodes('ou:org#haha'))

            self.len(0, await core.nodes('diff', opts=altview))

            q = '''
            [ ou:name=foo +(bar)> {[ ou:name=bar ]} ]
            { for $i in $lib.range(1001) { $node.data.set($i, $i) }}
            '''
            nodes = await core.nodes(q, opts=altview)

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            altview['user'] = visi.iden

            uppriden = core.views[viewiden].layers[0].iden
            lowriden = core.views[viewiden].layers[1].iden

            await visi.addRule((True, ('view',)), gateiden=viewiden)
            await visi.addRule((True, ('node',)), gateiden=uppriden)
            await visi.addRule((True, ('node', 'add')), gateiden=lowriden)
            await visi.addRule((True, ('node', 'prop')), gateiden=lowriden)
            await visi.addRule((True, ('node', 'data')), gateiden=lowriden)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('ou:name | merge --apply', opts=altview)

            self.len(0, await core.nodes('ou:name=foo'))

            await visi.addRule((True, ('node', 'edge')), gateiden=lowriden)

            await core.nodes('ou:name | merge --apply', opts=altview)
            self.len(1, await core.nodes('ou:name=foo -(bar)> *'))

            with self.getAsyncLoggerStream('synapse.lib.snap') as stream:
                await core.stormlist('ou:name | merge --apply', opts=altview)

            stream.seek(0)
            buf = stream.read()
            self.notin("No form named None", buf)

            await core.nodes('[ ou:name=baz ]')
            await core.nodes('ou:name=baz [ +#new.tag .seen=now ]', opts=altview)
            await core.nodes('ou:name=baz | delnode')

            self.stormHasNoErr(await core.stormlist('diff', opts=altview))
            self.stormHasNoErr(await core.stormlist('diff --tag new.tag', opts=altview))
            self.stormHasNoErr(await core.stormlist('diff --prop ".seen"', opts=altview))
            self.stormHasNoErr(await core.stormlist('merge --diff', opts=altview))

    async def test_storm_merge_opts(self):

        async with self.getTestCore() as core:
            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            altview = {'view': viewiden}

            await core.addTagProp('score', ('int', {}), {})

            await core.nodes('[ ou:org=(org1,) :name=hehe ]')

            q = '''
            [ ou:org=(org1,)
                :url=https://vertex.link
                :name=haha
                :desc=cool
                :founded=2021
                .seen=2022
                +#one:score=1
                +#two:score=2
                +#three:score=3
                +#haha.four
                +#haha.five
            ]
            '''
            await core.nodes(q, opts=altview)

            self.len(0, await core.nodes('syn:tag'))
            self.len(6, await core.nodes('syn:tag', opts=altview))

            await core.nodes('diff | merge --only-tags --include-tags one two --apply', opts=altview)
            nodes = await core.nodes('ou:org')
            self.sorteq(list(nodes[0].tags.keys()), ['one', 'two'])
            self.eq(nodes[0].tagprops['one']['score'], 1)
            self.eq(nodes[0].tagprops['two']['score'], 2)
            self.none(nodes[0].tagprops.get('three'))
            self.len(2, await core.nodes('syn:tag'))

            await core.nodes('diff | merge --only-tags --exclude-tags three haha.four --apply', opts=altview)
            nodes = await core.nodes('ou:org')
            self.sorteq(list(nodes[0].tags.keys()), ['one', 'two', 'haha', 'haha.five'])
            self.none(nodes[0].tagprops.get('three'))
            self.len(4, await core.nodes('syn:tag'))

            await core.nodes('diff | merge --include-props ou:org:name ou:org:desc --apply', opts=altview)
            nodes = await core.nodes('ou:org')
            self.sorteq(list(nodes[0].tags.keys()), ['one', 'two', 'three', 'haha', 'haha.four', 'haha.five'])
            self.eq(nodes[0].props.get('name'), 'haha')
            self.eq(nodes[0].props.get('desc'), 'cool')
            self.none(nodes[0].props.get('url'))
            self.none(nodes[0].props.get('founded'))
            self.none(nodes[0].props.get('.seen'))
            self.eq(nodes[0].tagprops['three']['score'], 3)
            self.len(6, await core.nodes('syn:tag'))

            await core.nodes('diff | merge --exclude-props ou:org:url ".seen" --apply', opts=altview)
            nodes = await core.nodes('ou:org')
            self.eq(nodes[0].props.get('founded'), 1609459200000)
            self.none(nodes[0].props.get('url'))
            self.none(nodes[0].props.get('.seen'))

            await core.nodes('diff | merge --include-props ".seen" --apply', opts=altview)
            nodes = await core.nodes('ou:org')
            self.nn(nodes[0].props.get('.seen'))
            self.none(nodes[0].props.get('url'))

            await core.nodes('[ ou:org=(org2,) +#six ]', opts=altview)
            await core.nodes('diff | merge --only-tags --apply', opts=altview)

            self.len(0, await core.nodes('ou:org=(org2,)'))

            sodes = await core.callStorm('ou:org=(org2,) return($node.getStorNodes())', opts=altview)
            self.nn(sodes[0]['tags']['six'])

            await core.nodes('[ ou:org=(org3,) +#glob.tags +#more.glob.tags +#more.gob.tags ]', opts=altview)
            await core.nodes('diff | merge --include-tags glob.* more.gl** --apply', opts=altview)
            nodes = await core.nodes('ou:org=(org3,)')
            exp = ['glob', 'more', 'more.glob', 'more.glob.tags', 'glob.tags']
            self.sorteq(list(nodes[0].tags.keys()), exp)

            q = '''
            [ file:bytes=*
              :md5=00000a5758eea935f817dd1490a322a5

              inet:ssl:cert=(1.2.3.4, $node)
            ]
            '''
            await core.nodes(q, opts=altview)

            self.len(0, await core.nodes('hash:md5'))
            await core.nodes('file:bytes | merge --apply', opts=altview)
            self.len(1, await core.nodes('hash:md5'))

            self.len(0, await core.nodes('inet:ipv4'))
            await core.nodes('inet:ssl:cert | merge --apply', opts=altview)
            self.len(1, await core.nodes('inet:ipv4'))

    async def test_storm_movenodes(self):

        async with self.getTestCore() as core:
            view2iden = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = {'view': view2iden}

            view3iden = await core.callStorm('return($lib.view.get().fork().iden)', opts=view2)
            view3 = {'view': view3iden}

            layrs = await core.callStorm('return($lib.view.get().layers)', opts=view3)
            layr3 = layrs[0]['iden']
            layr2 = layrs[1]['iden']
            layr1 = layrs[2]['iden']

            await core.addTagProp('score', ('int', {}), {})

            msgs = await core.stormlist('[ inet:fqdn=foo.com ] | movenodes --destlayer $node')
            self.stormIsInErr('movenodes arguments must be runtsafe.', msgs)

            msgs = await core.stormlist('ou:org | movenodes')
            self.stormIsInErr('You may only move nodes in views with multiple layers.', msgs)

            msgs = await core.stormlist('ou:org | movenodes --destlayer foo', opts=view2)
            self.stormIsInErr('No layer with iden foo in this view', msgs)

            msgs = await core.stormlist('ou:org | movenodes --srclayers foo', opts=view2)
            self.stormIsInErr('No layer with iden foo in this view', msgs)

            msgs = await core.stormlist(f'ou:org | movenodes --srclayers {layr2} --destlayer {layr2}', opts=view2)
            self.stormIsInErr('cannot also be the destination layer', msgs)

            msgs = await core.stormlist(f'ou:org | movenodes --precedence foo', opts=view2)
            self.stormIsInErr('No layer with iden foo in this view', msgs)

            msgs = await core.stormlist(f'ou:org | movenodes --precedence {layr2}', opts=view2)
            self.stormIsInErr('must be included when specifying precedence', msgs)

            q = '''
            [ ou:org=(foo,)
                :desc=layr1
                .seen=2022
                +#hehe.haha=2022
                +#one:score=1
                +(bar)> {[ ou:org=(bar,) ]}
            ]
            $node.data.set(foo, bar)
            '''
            nodes = await core.nodes(q)
            nodeiden = nodes[0].iden()

            msgs = await core.stormlist('ou:org | movenodes', opts=view2)
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint(f'{layr2} add {nodeiden}', msgs)
            self.stormIsInPrint(f'{layr2} set {nodeiden} ou:org:.created', msgs)
            self.stormIsInPrint(f'{layr2} set {nodeiden} ou:org:desc', msgs)
            self.stormIsInPrint(f'{layr2} set {nodeiden} ou:org#hehe.haha', msgs)
            self.stormIsInPrint(f'{layr2} set {nodeiden} ou:org#one:score', msgs)
            self.stormIsInPrint(f'{layr2} set {nodeiden} ou:org DATA', msgs)
            self.stormIsInPrint(f'{layr2} add {nodeiden} ou:org +(bar)>', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden}', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org:.created', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org:desc', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org#hehe.haha', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org#one:score', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org DATA', msgs)
            self.stormIsInPrint(f'{layr1} delete {nodeiden} ou:org +(bar)>', msgs)

            nodes = await core.nodes('ou:org | movenodes --apply', opts=view2)

            self.len(0, await core.nodes('ou:org=(foo,)'))

            sodes = await core.callStorm('ou:org=(foo,) return($node.getStorNodes())', opts=view2)
            sode = sodes[0]
            self.eq(sode['props'].get('desc')[0], 'layr1')
            self.eq(sode['props'].get('.seen')[0], (1640995200000, 1640995200001))
            self.eq(sode['tags'].get('hehe.haha'), (1640995200000, 1640995200001))
            self.eq(sode['tagprops'].get('one').get('score')[0], 1)
            self.len(1, await core.nodes('ou:org=(foo,) -(bar)> *', opts=view2))
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(foo))', opts=view2)
            self.eq(data, 'bar')

            q = '''
            [ ou:org=(foo,)
                :desc=overwritten
                .seen=2023
                +#hehe.haha=2023
                +#one:score=2
                +#two:score=1
                +(baz)> {[ ou:org=(baz,) ]}
            ]
            $node.data.set(foo, baz)
            $node.data.set(bar, baz)
            '''
            await core.nodes(q)

            nodes = await core.nodes('ou:org | movenodes --apply', opts=view3)

            self.len(0, await core.nodes('ou:org=(foo,)'))
            self.len(0, await core.nodes('ou:org=(foo,)', opts=view2))

            sodes = await core.callStorm('ou:org=(foo,) return($node.getStorNodes())', opts=view3)
            sode = sodes[0]
            self.eq(sode['props'].get('desc')[0], 'layr1')
            self.eq(sode['props'].get('.seen')[0], (1640995200000, 1672531200001))
            self.eq(sode['tags'].get('hehe.haha'), (1640995200000, 1672531200001))
            self.eq(sode['tagprops'].get('one').get('score')[0], 1)
            self.eq(sode['tagprops'].get('two').get('score')[0], 1)
            self.len(1, await core.nodes('ou:org=(foo,) -(bar)> *', opts=view3))
            self.len(1, await core.nodes('ou:org=(foo,) -(baz)> *', opts=view3))
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(foo))', opts=view3)
            self.eq(data, 'bar')
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(bar))', opts=view3)
            self.eq(data, 'baz')

            q = f'ou:org | movenodes --apply --srclayers {layr3} --destlayer {layr2}'
            nodes = await core.nodes(q, opts=view3)

            sodes = await core.callStorm('ou:org=(foo,) return($node.getStorNodes())', opts=view2)
            sode = sodes[0]
            self.eq(sode['props'].get('.seen')[0], (1640995200000, 1672531200001))
            self.eq(sode['tags'].get('hehe.haha'), (1640995200000, 1672531200001))
            self.eq(sode['tagprops'].get('one').get('score')[0], 1)
            self.eq(sode['tagprops'].get('two').get('score')[0], 1)
            self.len(1, await core.nodes('ou:org=(foo,) -(bar)> *', opts=view2))
            self.len(1, await core.nodes('ou:org=(foo,) -(baz)> *', opts=view2))
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(foo))', opts=view2)
            self.eq(data, 'bar')
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(bar))', opts=view2)
            self.eq(data, 'baz')

            q = '''
            [ ou:org=(foo,)
                :desc=prio
                .seen=2024
                +#hehe.haha=2024
                +#one:score=2
                +#two:score=2
                +(prio)> {[ ou:org=(prio,) ]}
            ]
            $node.data.set(foo, prio)
            $node.data.set(bar, prio)
            '''
            await core.nodes(q)

            q = f'ou:org | movenodes --apply --precedence {layr1} {layr2} {layr3}'
            nodes = await core.nodes(q, opts=view3)

            sodes = await core.callStorm('ou:org=(foo,) return($node.getStorNodes())', opts=view3)
            sode = sodes[0]
            self.eq(sode['props'].get('desc')[0], 'prio')
            self.eq(sode['props'].get('.seen')[0], (1640995200000, 1704067200001))
            self.eq(sode['tags'].get('hehe.haha'), (1640995200000, 1704067200001))
            self.eq(sode['tagprops'].get('one').get('score')[0], 2)
            self.eq(sode['tagprops'].get('two').get('score')[0], 2)
            self.len(1, await core.nodes('ou:org=(foo,) -(bar)> *', opts=view3))
            self.len(1, await core.nodes('ou:org=(foo,) -(baz)> *', opts=view3))
            self.len(1, await core.nodes('ou:org=(foo,) -(prio)> *', opts=view3))
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(foo))', opts=view3)
            self.eq(data, 'prio')
            data = await core.callStorm('ou:org=(foo,) return($node.data.get(bar))', opts=view3)
            self.eq(data, 'prio')

            for i in range(1001):
                await core.addFormProp('ou:org', f'_test{i}', ('int', {}), {})

            await core.nodes('''
            [ ou:org=(cov,) ]

            { for $i in $lib.range(1001) {
                $prop = $lib.str.format('_test{i}', i=$i)
                [ :$prop = $i
                  +#$prop:score = $i
                  +($i)> { ou:org=(cov,) }
                ]
                $node.data.set($prop, $i)
            }}
            ''')

            q = f'ou:org | movenodes --apply --srclayers {layr1} --destlayer {layr2}'
            nodes = await core.nodes(q, opts=view3)

            sodes = await core.callStorm('ou:org=(cov,) return($node.getStorNodes())', opts=view2)
            sode = sodes[0]
            self.len(1002, sode['props'])
            self.len(1001, sode['tags'])
            self.len(1001, sode['tagprops'])
            self.len(1001, await core.callStorm('ou:org=(cov,) return($node.data.list())', opts=view2))

            msgs = await core.stormlist('ou:org=(cov,) -(*)> * | count | spin', opts=view2)
            self.stormIsInPrint('1001', msgs)

    async def test_storm_embeds(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:asn=10 :name=hehe ]')

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=10 ]')
            await nodes[0].getEmbeds({'asn::newp': {}})
            await nodes[0].getEmbeds({'newp::newp': {}})
            await nodes[0].getEmbeds({'asn::name::foo': {}})

            opts = {'embeds': {'inet:ipv4': {'asn': ('name',)}}}
            msgs = await core.stormlist('inet:ipv4=1.2.3.4', opts=opts)

            nodes = [m[1] for m in msgs if m[0] == 'node']

            node = nodes[0]
            self.eq('hehe', node[1]['embeds']['asn']['name'])
            self.eq('796d67b92a6ffe9b88fa19d115b46ab6712d673a06ae602d41de84b1464782f2', node[1]['embeds']['asn']['*'])

            opts = {'embeds': {'ou:org': {'hq::email': ('user',)}}}
            msgs = await core.stormlist('[ ou:org=* :hq=* ] { -> ps:contact [ :email=visi@vertex.link ] }', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']

            node = nodes[0]
            self.eq('visi', node[1]['embeds']['hq::email']['user'])
            self.eq('2346d7bed4b0fae05e00a413bbf8716c9e08857eb71a1ecf303b8972823f2899', node[1]['embeds']['hq::email']['*'])

    async def test_storm_wget(self):

        async def _getRespFromSha(core, mesgs):
            for m in mesgs:
                if m[0] == 'node' and m[1][0][0] == 'file:bytes':
                    node = m[1]
                    sha = node[1]['props']['sha256']

            buf = b''
            async for bytz in core.axon.get(s_common.uhex(sha)):
                buf += bytz

            resp = json.loads(buf.decode('utf8'))
            return resp

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            core.addHttpApi('/api/v0/test', s_t_utils.HttpReflector, {'cell': core})
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url}}

            # Headers as list of tuples, params as dict
            q = '''
            $params=$lib.dict(key=valu, foo=bar)
            $hdr = (
                    ("User-Agent", "my fav ua"),
            )|
            wget $url --headers $hdr --params $params --no-ssl-verify | -> file:bytes $lib.print($node)
            '''

            mesgs = await alist(core.storm(q, opts=opts))

            resp = await _getRespFromSha(core, mesgs)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})
            self.eq(data.get('headers').get('User-Agent'), 'my fav ua')

            # no default headers(from wget command)
            q = '''
            $hdr = (
                    ("User-Agent", "my fav ua"),
            )|
            wget $url --headers $hdr --no-headers --no-ssl-verify | -> file:bytes $lib.print($node)
            '''
            mesgs = await alist(core.storm(q, opts=opts))

            resp = await _getRespFromSha(core, mesgs)
            data = resp.get('result')
            self.ne(data.get('headers').get('User-Agent'), 'my fav ua')

            # params as list of key/value pairs
            q = '''
            $params=((foo, bar), (key, valu))
            | wget $url --params $params --no-ssl-verify | -> file:bytes $lib.print($node)
            '''
            mesgs = await alist(core.storm(q, opts=opts))

            resp = await _getRespFromSha(core, mesgs)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})

    async def test_storm_vars_fini(self):

        async with self.getTestCore() as core:

            query = await core.getStormQuery('inet:ipv4')
            async with core.getStormRuntime(query) as runt:

                base0 = await s_base.Base.anit()
                base0._syn_refs = 0
                await runt.setVar('base0', base0)
                await runt.setVar('base0', base0)
                self.false(base0.isfini)
                await runt.setVar('base0', None)
                self.true(base0.isfini)

                base1 = await s_base.Base.anit()
                base1._syn_refs = 0
                await runt.setVar('base1', base1)
                await runt.popVar('base1')
                self.true(base1.isfini)

                base2 = await s_base.Base.anit()
                base2._syn_refs = 0
                await runt.setVar('base2', base2)

            self.true(base2.isfini)

    async def test_storm_dmon_user_locked(self):
        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('dmon', 'add')))
            async with core.getLocalProxy(user='visi') as asvisi:
                q = '''return($lib.dmon.add(${{ $lib.queue.gen(hehedmon).put(lolz) $lib.time.sleep(10) }},
                                            name=hehedmon))'''
                ddef0 = await asvisi.callStorm(q)

            with self.getAsyncLoggerStream('synapse.lib.storm', 'user is locked') as stream:
                await visi.setLocked(True)
                q = 'return($lib.dmon.bump($iden))'
                self.true(await core.callStorm(q, opts={'vars': {'iden': ddef0['iden']}}))
                self.true(await stream.wait(2))

    async def test_storm_dmon_user_autobump(self):
        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('dmon', 'add')))
            async with core.getLocalProxy(user='visi') as asvisi:
                with self.getAsyncLoggerStream('synapse.lib.storm', 'Dmon query exited') as stream:
                    q = '''return($lib.dmon.add(${{ $lib.print(foobar) $lib.time.sleep(10) }},
                                                name=hehedmon))'''
                    await asvisi.callStorm(q)

                with self.getAsyncLoggerStream('synapse.lib.storm', 'user is locked') as stream:
                    await core.setUserLocked(visi.iden, True)
                    self.true(await stream.wait(2))

                with self.getAsyncLoggerStream('synapse.lib.storm', 'Dmon query exited') as stream:
                    await core.setUserLocked(visi.iden, False)
                    self.true(await stream.wait(2))

    async def test_storm_pipe(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                $crap = (foo, bar, baz)

                $pipe = $lib.pipe.gen(${
                    $pipe.puts($crap)
                    $pipe.put(hehe)
                    $pipe.put(haha)

                    // cause the generator to tick once for coverage...
                    [ ou:org=* ]
                })

                for $items in $pipe.slices(size=2) {
                    for $devstr in $items {
                        [ it:dev:str=$devstr ]
                    }
                }
            ''')
            self.len(5, nodes)
            nvals = [n.ndef[1] for n in nodes]
            self.eq(('foo', 'bar', 'baz', 'hehe', 'haha'), nvals)

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.pipe.gen(${}, size=999999)')

            with self.raises(s_exc.BadArg):
                await core.nodes('$pipe = $lib.pipe.gen(${}) for $item in $pipe.slices(size=999999) {}')

            with self.raises(s_exc.BadArg):
                await core.nodes('$pipe = $lib.pipe.gen(${}) for $item in $pipe.slice(size=999999) {}')

            msgs = await core.stormlist('''
                $pipe = $lib.pipe.gen(${ $pipe.put((0 + "woot")) })
                for $items in $pipe.slices() { $lib.print($items) }
            ''')

            self.stormIsInWarn('pipe filler error: BadCast', msgs)
            self.false(any([m for m in msgs if m[0] == 'err']))

            self.eq(0, await core.callStorm('return($lib.pipe.gen(${}).size())'))

            with self.raises(s_exc.BadArg):
                await core.nodes('''
                    $pipe = $lib.pipe.gen(${ $pipe.put(woot) })

                    for $items in $pipe.slices() { $lib.print($items) }

                    $pipe.put(hehe)
                ''')

            with self.raises(s_exc.BadArg):
                await core.nodes('''
                    $pipe = $lib.pipe.gen(${ $pipe.put(woot) })

                    for $items in $pipe.slices() { $lib.print($items) }

                    $pipe.puts((hehe, haha))
                ''')

            nodes = await core.nodes('''
                $crap = (foo, bar, baz)

                $pipe = $lib.pipe.gen(${ $pipe.puts((foo, bar, baz)) })

                for $devstr in $pipe.slice(size=2) {
                    [ it:dev:str=$devstr ]
                }
            ''')
            self.len(2, nodes)
            nvals = [n.ndef[1] for n in nodes]
            self.eq(('foo', 'bar'), nvals)

    async def test_storm_undef(self):

        async with self.getTestCore() as core:

            # pernode variants
            self.none(await core.callStorm('''
                [ ps:contact = * ]
                if $node {
                    $foo = $lib.dict()
                    $foo.bar = $lib.undef
                    return($foo.bar)
                }
            '''))
            with self.raises(s_exc.NoSuchVar):
                await core.callStorm('[ps:contact=*] $foo = $node.repr() $foo = $lib.undef return($foo)')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('''
                    [ps:contact=*]
                    $path.vars.foo = lol
                    $path.vars.foo = $lib.undef
                    return($path.vars.foo)
                ''')

            # runtsafe variants
            self.eq(('foo', 'baz'), await core.callStorm('$foo = (foo, bar, baz) $foo.1 = $lib.undef return($foo)'))
            self.eq(('foo', 'bar'), await core.callStorm('$foo = (foo, bar, baz) $foo."-1" = $lib.undef return($foo)'))
            self.none(await core.callStorm('$foo = $lib.dict() $foo.bar = 10 $foo.bar = $lib.undef return($foo.bar)'))
            self.eq(('woot',), await core.callStorm('''
                $foo = (foo, bar, baz)
                $foo.0 = $lib.undef
                $foo.0 = $lib.undef
                $foo.0 = $lib.undef
                // one extra to test the exc handler
                $foo.0 = $lib.undef
                $foo.append(hehe)
                $foo.0 = woot
                return($foo)
            '''))
            with self.raises(s_exc.NoSuchVar):
                await core.callStorm('$foo = 10 $foo = $lib.undef return($foo)')

    async def test_storm_pkg_load(self):
        cont = s_common.guid()
        pkg = {
            'name': 'testload',
            'version': '0.3.0',
            'modules': (
                {
                    'name': 'testload',
                    'storm': 'function x() { return((0)) }',
                },
            ),
            'onload': f'[ ps:contact={cont} ] $lib.print(teststring) $lib.warn(testwarn, key=valu) return($path.vars.newp)'
        }
        class PkgHandler(s_httpapi.Handler):

            async def get(self, name):

                if name == 'notok':
                    self.sendRestErr('FooBar', 'baz faz')
                    return

                self.sendRestRetn(pkg)

        class PkgHandlerRaw(s_httpapi.Handler):
            async def get(self, name):
                self.set_header('Content-Type', 'application/json')
                return self.write(pkg)

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/pkgtest/(.*)', PkgHandler, {'cell': core})
            core.addHttpApi('/api/v1/pkgtestraw/(.*)', PkgHandlerRaw, {'cell': core})
            port = (await core.addHttpsPort(0, host='127.0.0.1'))[1]

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/newp/newp')
            self.stormIsInWarn('pkg.load got HTTP code: 404', msgs)

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/notok')
            self.stormIsInWarn('pkg.load got JSON error: FooBar', msgs)

            with self.getAsyncLoggerStream('synapse.cortex') as stream:
                msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

                msgs = await core.stormlist(f'pkg.load --ssl-noverify --raw https://127.0.0.1:{port}/api/v1/pkgtestraw/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)

            stream.seek(0)
            buf = stream.read()
            self.isin("testload onload output: teststring", buf)
            self.isin("testload onload output: testwarn", buf)
            self.isin("No var with name: newp", buf)
            self.len(1, await core.nodes(f'ps:contact={cont}'))

    async def test_storm_tree(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=www.vertex.link ] | tree { :domain -> inet:fqdn }')
            vals = [n.ndef[1] for n in nodes]
            self.eq(('www.vertex.link', 'vertex.link', 'link'), vals)

            # Max recursion fail
            q = '[ inet:fqdn=www.vertex.link ] | tree { inet:fqdn=www.vertex.link }'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            # Runtsafety test
            q = '[ inet:fqdn=www.vertex.link ] $q={ :domain -> inet:fqdn } | tree $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_movetag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe.haha', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))

                await tagnode.set('doc', 'haha doc')
                await tagnode.set('title', 'haha title')

            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag hehe hehe')

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(0, await core.nodes('#hehe.haha'))

            self.len(1, await core.nodes('#woot'))
            self.len(1, await core.nodes('#woot.haha'))

            async with await core.snap() as snap:

                newt = await core.getNodeByNdef(('syn:tag', 'woot.haha'))

                self.eq(newt.get('doc'), 'haha doc')
                self.eq(newt.get('title'), 'haha title')

                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq((20, 30), node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                self.eq('woot', node.get('isnow'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))
                self.eq('woot.haha', node.get('isnow'))

                node = await snap.addNode('test:str', 'bar')

                # test isnow plumbing
                await node.addTag('hehe.haha')

                self.nn(node.tags.get('woot'))
                self.nn(node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe'))

                await tagnode.set('doc', 'haha doc')

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(1, await core.nodes('#woot'))

            async with await core.snap() as snap:
                newt = await core.getNodeByNdef(('syn:tag', 'woot'))

                self.eq(newt.get('doc'), 'haha doc')

        # Test moving a tag which has tags on it.
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('a.b.c', (None, None))
                tnode = await snap.getNodeByNdef(('syn:tag', 'a.b'))
                await tnode.addTag('foo', (None, None))

            await core.nodes('movetag a.b a.m')
            self.len(2, await core.nodes('#foo'))
            self.len(1, await core.nodes('syn:tag=a.b +#foo'))
            self.len(1, await core.nodes('syn:tag=a.m +#foo'))

        # Test moving a tag to another tag which is a string prefix of the source
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('aaa.b.ccc', (None, None))
                await node.addTag('aaa.b.ddd', (None, None))
                node = await snap.addNode('test:str', 'Q')
                await node.addTag('aaa.barbarella.ccc', (None, None))

            await core.nodes('movetag aaa.b aaa.barbarella')

            self.len(7, await core.nodes('syn:tag'))
            self.len(1, await core.nodes('syn:tag=aaa.barbarella.ccc'))
            self.len(1, await core.nodes('syn:tag=aaa.barbarella.ddd'))

        # Move a tag with tagprops
        async def seed_tagprops(core):
            await core.addTagProp('test', ('int', {}), {})
            await core.addTagProp('note', ('str', {}), {})
            q = '[test:int=1 +#hehe.haha +#hehe:test=1138 +#hehe.beep:test=8080 +#hehe.beep:note="oh my"]'
            nodes = await core.nodes(q)
            self.eq(nodes[0].getTagProp('hehe', 'test'), 1138)
            self.eq(nodes[0].getTagProp('hehe.beep', 'test'), 8080)
            self.eq(nodes[0].getTagProp('hehe.beep', 'note'), 'oh my')

        async with self.getTestCore() as core:
            await seed_tagprops(core)
            await core.nodes('movetag hehe woah')

            self.len(0, await core.nodes('#hehe'))
            nodes = await core.nodes('#woah')
            self.len(1, nodes)
            self.eq(nodes[0].tagprops, {'woah': {'test': 1138},
                                        'woah.beep': {'test': 8080,
                                                      'note': 'oh my'}
                                       })

        async with self.getTestCore() as core:
            await seed_tagprops(core)
            await core.nodes('movetag hehe.beep woah.beep')

            self.len(1, await core.nodes('#hehe'))
            nodes = await core.nodes('#woah')
            self.len(1, nodes)
            self.eq(nodes[0].tagprops, {'hehe': {'test': 1138},
                                        'woah.beep': {'test': 8080,
                                                      'note': 'oh my'}
                                       })

            # Test perms
            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            async with core.getLocalProxy(user='visi') as asvisi:
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'movetag woah perm')

                await visi.addRule((True, ('node', 'tag', 'del', 'woah')))

                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'movetag woah perm')

                await visi.addRule((True, ('node', 'tag', 'add', 'perm')))

                await asvisi.callStorm(f'movetag woah perm')

            self.len(0, await core.nodes('#woah'))
            self.len(1, await core.nodes('#perm'))

        # make a cycle of tags via move tag
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'neato')
                await node.addTag('basic.one', (None, None))
                await node.addTag('basic.two', (None, None))
                await node.addTag('unicycle', (None, None))
                await node.addTag('bicycle', (None, None))
                await node.addTag('tricycle', (None, None))

            # basic 2-cycle test
            await core.nodes('movetag basic.one basic.two')
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag basic.two basic.one')

            # 3-cycle test
            await core.nodes('movetag bicycle tricycle')
            await core.nodes('movetag unicycle bicycle')
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag tricycle unicycle')

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'badcycle')
                await node.addTag('unicycle')

            # 4 cycle test
            node = await snap.addNode('test:str', 'burrito')
            await node.addTag('there.picard', (None, None))
            await node.addTag('are.is', (None, None))
            await node.addTag('four.best', (None, None))
            await node.addTag('tags.captain', (None, None))

            # A -> B -> C -> D -> A
            await core.nodes('movetag there are')   # A -> B
            await core.nodes('movetag four tags')   # C -> D
            await core.nodes('movetag tags there')  # D -> A
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag are four')    # B -> C (creates the cycle)

            # make a pre-existing cycle to ensure we can break break that with move tag
            async with await core.snap() as snap:

                node = await snap.addNode('syn:tag', 'existing')
                await node.set('isnow', 'cycle')

                node = await snap.addNode('syn:tag', 'cycle')
                await node.set('isnow', 'existing')

            await core.nodes('movetag cycle breaker')

            node = await core.getNodeByNdef(('syn:tag', 'existing'))
            self.eq('cycle', node.get('isnow'))
            node = await core.getNodeByNdef(('syn:tag', 'cycle'))
            self.eq('breaker', node.get('isnow'))
            node = await core.getNodeByNdef(('syn:tag', 'breaker'))
            self.eq(None, node.get('isnow'))

            # make a pre-existing cycle to ensure we can catch that if an chain is encountered
            # B -> C -> D -> E -> C
            # Then movetag to make A -> B
            async with await core.snap() as snap:
                node = await snap.addNode('syn:tag', 'this')

                node = await snap.addNode('syn:tag', 'is')
                await node.set('isnow', 'not')
                node = await snap.addNode('syn:tag', 'not')
                await node.set('isnow', 'a')
                node = await snap.addNode('syn:tag', 'a')
                await node.set('isnow', 'test')
                node = await snap.addNode('syn:tag', 'test')
                await node.set('isnow', 'not')
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag this is')

        # Sad path
        async with self.getTestCore() as core:
            # Test moving a tag to itself
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag foo.bar foo.bar')
            # Test moving a tag which does not exist
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag foo.bar duck.knight')

            # Runtsafety test
            q = '[ test:str=hehe ]  | movetag $node.iden() haha'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_spin(self):

        async with self.getTestCore() as core:
            self.len(0, await core.nodes('[ test:str=foo test:str=bar ] | spin'))
            self.len(2, await core.nodes('test:str=foo test:str=bar'))

    async def test_storm_reindex_sudo(self):

        async with self.getTestCore() as core:

            mesgs = await core.stormlist('reindex')
            self.stormIsInWarn('reindex currently does nothing', mesgs)

            msgs = await core.stormlist('.created | sudo')
            self.stormIsInWarn('Sudo is deprecated and does nothing', msgs)

    async def test_storm_count(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:str=foo test:str=bar ]')
            self.len(2, nodes)

            msgs = await core.stormlist('test:str=foo test:str=bar | count')
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(0, nodes)
            self.stormIsInPrint('Counted 2 nodes.', msgs)

            msgs = await core.stormlist('test:str=foo test:str=bar | count --yield')
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.stormIsInPrint('Counted 2 nodes.', msgs)

            msgs = await alist(core.storm('test:str=newp | count'))
            self.stormIsInPrint('Counted 0 nodes.', msgs)
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(0, nodes)

    async def test_storm_uniq(self):
        async with self.getTestCore() as core:
            q = "[test:comp=(123, test) test:comp=(123, duck) test:comp=(123, mode)]"
            self.len(3, await core.nodes(q))
            nodes = await core.nodes('test:comp -> *')
            self.len(3, nodes)
            nodes = await core.nodes('test:comp -> * | uniq')
            self.len(1, nodes)

    async def test_storm_once_cmd(self):
        async with self.getTestCore() as core:
            await core.nodes('[test:str=foo test:str=bar test:str=neato test:str=burrito test:str=awesome test:str=possum]')
            q = 'test:str=foo | once tagger | [+#my.cool.tag]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.len(3, nodes[0].tags)
            self.isin('my.cool.tag', nodes[0].tags)

            # run it again and see all the things get swatted to the floor
            q = 'test:str=foo | once tagger | [+#less.cool.tag]'
            self.len(0, await core.nodes(q))
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            self.notin('less.cool.tag', nodes[0].tags)

            # make a few more and see at least some of them make it through
            nodes = await core.nodes('test:str=neato test:str=burrito | once tagger | [+#my.cool.tag]')
            self.len(2, nodes)
            for node in nodes:
                self.isin('my.cool.tag', node.tags)

            q = 'test:str | once tagger | [ +#yet.another.tag ]'
            nodes = await core.nodes(q)
            self.len(3, nodes)
            for node in nodes:
                self.isin('yet.another.tag', node.tags)
                self.notin('my.cool.tag', node.tags)

            q = 'test:str | once tagger'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # it kinda works like asof in stormtypes, so if as is too far out,
            # we won't update it
            q = 'test:str=foo | once tagger --asof -30days | [+#another.tag]'
            self.len(0, await core.nodes(q))
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            self.notin('less.cool.tag', nodes[0].tags)

            # but if it's super recent, we can override it
            q = 'test:str | once tagger --asof now | [ +#tag.the.third ]'
            nodes = await core.nodes(q)
            self.len(6, nodes)
            for node in nodes:
                self.isin('tag.the.third', node.tags)

            # for coverage
            await core.nodes('test:str=foo $node.data.set(once:tagger, $lib.dict(lol=yup))')
            nodes = await core.nodes('test:str=foo | once tagger | [ +#fourth ]')
            self.len(1, nodes)
            self.isin('fourth', nodes[0].tags)

            # keys shouldn't interact
            nodes = await core.nodes('test:str | once ninja | [ +#lottastrings ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('lottastrings', node.tags)

            nodes = await core.nodes('test:str | once beep --asof -30days | [ +#boop ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('boop', node.tags)

            # timestamp is more recent than the last, so the things get to run again
            nodes = await core.nodes('test:str | once beep --asof -15days | [ +#zomg ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('zomg', node.tags)

            # we update to the more recent timestamp, so providing now should update things
            nodes = await core.nodes('test:str | once beep --asof now | [ +#bbq ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('bbq', node.tags)

            # but still, no time means if it's ever been done
            nodes = await core.nodes('test:str | once beep | [ +#metal]')
            self.len(0, nodes)
            for node in nodes:
                self.notin('meta', node.tags)

    async def test_storm_iden(self):
        async with self.getTestCore() as core:
            q = "[test:str=beep test:str=boop]"
            nodes = await core.nodes(q)
            self.len(2, nodes)
            idens = [node.iden() for node in nodes]

            iq = ' '.join(idens)
            # Demonstrate the iden lift does pass through previous nodes in the pipeline
            nodes = await core.nodes(f'[test:str=hehe] | iden {iq}')
            self.len(3, nodes)

            q = 'iden newp'
            with self.getLoggerStream('synapse.lib.snap', 'Failed to decode iden') as stream:
                self.len(0, await core.nodes(q))
                self.true(stream.wait(1))

            q = 'iden deadb33f'
            with self.getLoggerStream('synapse.lib.snap', 'iden must be 32 bytes') as stream:
                self.len(0, await core.nodes(q))
                self.true(stream.wait(1))

            # Runtsafety test
            q = 'test:str=hehe | iden $node.iden()'
            with self.raises(s_exc.StormRuntimeError):
                await core.nodes(q)

    async def test_minmax(self):

        async with self.getTestCore() as core:

            minval = core.model.type('time').norm('2015')[0]
            midval = core.model.type('time').norm('2016')[0]
            maxval = core.model.type('time').norm('2017')[0]

            async with await core.snap() as snap:
                # Ensure each node we make has its own discrete created time.
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2015',
                                                             '.seen': '2015'})
                minc = node.get('.created')
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2016',
                                                             '.seen': '2016'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2017',
                                                             '.seen': '2017'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:str', '1', {'tick': '2016'})

            # Relative paths
            nodes = await core.nodes('test:guid | max :tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            nodes = await core.nodes('test:guid | min :tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Universal prop for relative path
            nodes = await core.nodes('.created>=$minc | max .created',
                                     {'vars': {'minc': minc}})
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            nodes = await core.nodes('.created>=$minc | min .created',
                                     {'vars': {'minc': minc}})
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Variables nodesuated
            nodes = await core.nodes('test:guid ($tick, $tock) = .seen | min $tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            nodes = await core.nodes('test:guid ($tick, $tock) = .seen | max $tock')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | min $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x01020304, nodes[0].ndef[1])

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | max $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x05060708, nodes[0].ndef[1])

            # Sad paths where the specify an invalid property name
            with self.raises(s_exc.NoSuchProp):
                self.len(0, await core.nodes('test:guid | max :newp'))

            with self.raises(s_exc.NoSuchProp):
                self.len(0, await core.nodes('test:guid | min :newp'))

            # test that intervals work
            maxnodes = await core.nodes('[ ou:org=* ]')
            maxnodes = await core.nodes('[ ou:org=* +#minmax ]')
            minnodes = await core.nodes('[ ou:org=* +#minmax=(1981, 2010) ]')
            await core.nodes('[ ou:org=* +#minmax=(1982, 2018) ]')
            maxnodes = await core.nodes('[ ou:org=* +#minmax=(1997, 2020) ]')

            testmin = await core.nodes('ou:org | min #minmax')
            self.eq(testmin[0].ndef, minnodes[0].ndef)

            testmax = await core.nodes('ou:org | max #minmax')
            self.eq(testmax[0].ndef, maxnodes[0].ndef)

    async def test_scrape(self):

        async with self.getTestCore() as core:

            # runtsafe tests
            nodes = await core.nodes('$foo=6.5.4.3 | scrape $foo')
            self.len(0, nodes)

            self.len(1, await core.nodes('inet:ipv4=6.5.4.3'))

            nodes = await core.nodes('$foo=6.5.4.3 | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('[inet:ipv4=9.9.9.9 ] $foo=6.5.4.3 | scrape $foo')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x09090909))

            nodes = await core.nodes('[inet:ipv4=9.9.9.9 ] $foo=6.5.4.3 | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('$foo="6[.]5[.]4[.]3" | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('$foo="6[.]5[.]4[.]3" | scrape $foo --yield --skiprefang')
            self.len(0, nodes)

            # per-node tests

            guid = s_common.guid()

            await core.nodes(f'[ inet:search:query={guid} :text="hi there 5.5.5.5" ]')
            # test the special runtsafe but still per-node invocation
            nodes = await core.nodes('inet:search:query | scrape')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:search:query')

            self.len(1, await core.nodes('inet:ipv4=5.5.5.5'))

            nodes = await core.nodes('inet:search:query | scrape :text --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            nodes = await core.nodes('inet:search:query | scrape :text --refs | -(refs)> *')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            # test runtsafe and non-runtsafe failure to create node
            msgs = await core.stormlist('scrape "https://t.c\\\\"')
            self.stormIsInWarn('BadTypeValue', msgs)
            msgs = await core.stormlist('[ media:news=* :title="https://t.c\\\\" ] | scrape :title')
            self.stormIsInWarn('BadTypeValue', msgs)

            await core.nodes('trigger.add node:add --query {[ +#foo.com ]} --form inet:ipv4')
            msgs = await core.stormlist('syn:trigger | scrape :storm --refs')
            self.stormIsInWarn('Edges cannot be used with runt nodes: syn:trigger', msgs)

    async def test_storm_tee(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                guid = s_common.guid()
                await snap.addNode('edge:refs', (('media:news', guid), ('inet:ipv4', '1.2.3.4')))
                await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=0 ]')

            nodes = await core.nodes('inet:ipv4=1.2.3.4 | tee { -> * }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))

            nodes = await core.nodes('inet:ipv4=1.2.3.4 | tee --join { -> * }')
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

            q = '''
            inet:ipv4=1.2.3.4 | tee
            { spin | [ inet:ipv4=2.2.2.2 ]}
            { spin | [ inet:ipv4=3.3.3.3 ]}
            { spin | [ inet:ipv4=4.4.4.4 ]}
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)

            q = '''
            inet:ipv4=1.2.3.4 | tee --join
            { spin | inet:ipv4=2.2.2.2 }
            { spin | inet:ipv4=3.3.3.3 }
            { spin | inet:ipv4=4.4.4.4 }
            '''
            nodes = await core.nodes(q)
            self.len(4, nodes)

            q = 'inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }'
            nodes = await core.nodes(q)
            self.len(3, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef, ('inet:ipv4', 0x01020304))

            q = 'inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * } { -> edge:refs:n2 :n1 -> * }'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('media:news'))
            self.eq(nodes[3].ndef, ('inet:ipv4', 0x01020304))

            # Queries can be a heavy list
            q = '$list = $lib.list(${ -> * }, ${ <- * }, ${ -> edge:refs:n2 :n1 -> * }) inet:ipv4=1.2.3.4 | tee --join $list'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('media:news'))
            self.eq(nodes[3].ndef, ('inet:ipv4', 0x01020304))

            # A empty list of queries still works as an nop
            q = '$list = $lib.list() | tee $list'
            msgs = await core.stormlist(q)
            self.len(2, msgs)
            self.eq(('init', 'fini'), [m[0] for m in msgs])

            q = 'inet:ipv4=1.2.3.4 $list = $lib.list() | tee --join $list'
            msgs = await core.stormlist(q)
            self.len(3, msgs)
            self.eq(('init', 'node', 'fini'), [m[0] for m in msgs])

            q = '$list = $lib.list() | tee --parallel $list'
            msgs = await core.stormlist(q)
            self.len(2, msgs)
            self.eq(('init', 'fini'), [m[0] for m in msgs])

            q = 'inet:ipv4=1.2.3.4 $list = $lib.list() | tee --parallel --join $list'
            msgs = await core.stormlist(q)
            self.len(3, msgs)
            self.eq(('init', 'node', 'fini'), [m[0] for m in msgs])

            # Queries can be a input list
            q = 'inet:ipv4=1.2.3.4 | tee --join $list'
            queries = ('-> *', '<- *', '-> edge:refs:n2 :n1 -> *')
            nodes = await core.nodes(q, {'vars': {'list': queries}})
            self.len(4, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('media:news'))
            self.eq(nodes[3].ndef, ('inet:ipv4', 0x01020304))

            # Empty queries are okay - they will just return the input node
            q = 'inet:ipv4=1.2.3.4 | tee {}'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # Subqueries are okay too but will just yield the input back out
            q = 'inet:ipv4=1.2.3.4 | tee {{ -> * }}'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # Sad path
            q = 'inet:ipv4=1.2.3.4 | tee'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            # Runtsafe tee
            q = 'tee { inet:ipv4=1.2.3.4 } { inet:ipv4 -> * }'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            exp = {
                ('inet:asn', 0),
                ('inet:ipv4', 0x01020304),
            }
            self.eq(exp, {x.ndef for x in nodes})

            q = '$foo=woot.com tee { inet:ipv4=1.2.3.4 } { inet:fqdn=$foo <- * }'
            nodes = await core.nodes(q)
            self.len(3, nodes)
            exp = {
                ('inet:ipv4', 0x01020304),
                ('inet:fqdn', 'woot.com'),
                ('inet:dns:a', ('woot.com', 0x01020304)),
            }
            self.eq(exp, {n.ndef for n in nodes})

            # Variables are scoped down into the sub runtime
            q = (
                f'$foo=5 tee '
                f'{{ [ inet:asn=3 ] }} '
                f'{{ [ inet:asn=4 ] $lib.print("made asn node: {{node}}", node=$node) }} '
                f'{{ [ inet:asn=$foo ] }}'
            )
            msgs = await core.stormlist(q)
            self.stormIsInPrint("made asn node: Node{(('inet:asn', 4)", msgs)
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.eq({('inet:asn', 3), ('inet:asn', 4), ('inet:asn', 5)},
                    {p[0] for p in podes})

            # Node variables modified in sub runtimes don't affect parent node path
            q = '''[test:int=123] $foo=$node.value()
            | tee --join { $foo=($foo + 1) [test:str=$foo] +test:str } { $foo=($foo + 2) [test:str=$foo] +test:str } |
            $lib.fire(data, foo=$foo, ndef=$node.ndef()) | spin
            '''
            msgs = await core.stormlist(q)
            datas = [m[1].get('data') for m in msgs if m[0] == 'storm:fire']
            self.eq(datas, [
                {'foo': 124, 'ndef': ('test:str', '124')},
                {'foo': 125, 'ndef': ('test:str', '125')},
                {'foo': 123, 'ndef': ('test:int', 123)},
            ])

            # lift a non-existent node and feed to tee.
            q = 'inet:fqdn=newp.com tee { inet:ipv4=1.2.3.4 } { inet:ipv4 -> * }'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            exp = {
                ('inet:asn', 0),
                ('inet:ipv4', 0x01020304),
            }
            self.eq(exp, {x.ndef for x in nodes})

            # --parallel allows out of order execution. This test demonstrates that but controls the output by time

            q = '$foo=woot.com tee --parallel { $lib.time.sleep("0.5") inet:ipv4=1.2.3.4 }  { $lib.time.sleep("0.25") inet:fqdn=$foo <- * | sleep 1} { [inet:asn=1234] }'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            exp = [
                ('inet:asn', 1234),
                ('inet:dns:a', ('woot.com', 0x01020304)),
                ('inet:ipv4', 0x01020304),
                ('inet:fqdn', 'woot.com'),
            ]
            self.eq(exp, [x.ndef for x in nodes])

            # A fatal execption is fatal to the runtime
            q = '$foo=woot.com tee --parallel { $lib.time.sleep("0.5") inet:ipv4=1.2.3.4 }  { $lib.time.sleep("0.25") inet:fqdn=$foo <- * | sleep 1} { [inet:asn=newp] }'
            msgs = await core.stormlist(q)
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.len(0, podes)
            self.stormIsInErr("invalid literal for int() with base 0: 'newp'", msgs)

            # Each input node to the query is also subject to parallel execution
            q = '$foo=woot.com inet:fqdn=$foo inet:fqdn=com | tee --parallel { inet:ipv4=1.2.3.4 } { inet:fqdn=$foo <- * } | uniq'
            nodes = await core.nodes(q)

            self.eq({node.ndef for node in nodes}, {
                ('inet:fqdn', 'woot.com'),
                ('inet:ipv4', 16909060),
                ('inet:dns:a', ('woot.com', 16909060)),
                ('inet:fqdn', 'com'),
            })

            # Per-node exceptions can also tear down the runtime (coverage test)
            q = 'inet:fqdn=com | tee --parallel { [inet:asn=newp] }'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q)

            # No input test
            q = 'tee'
            with self.raises(s_exc.StormRuntimeError):
                await core.nodes(q)

            # Runtsafety test
            q = '[ inet:fqdn=www.vertex.link ] $q={ :domain -> inet:fqdn } | tee $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_yieldvalu(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')

            buid0 = nodes[0].buid
            iden0 = s_common.ehex(buid0)

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': (iden0,)}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            def genr():
                yield iden0

            async def agenr():
                yield iden0

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': (iden0,)}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': buid0}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': genr()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': agenr()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': nodes[0]}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': None}})
            self.len(0, nodes)

            with self.raises(s_exc.BadLiftValu):
                await core.nodes('yield $foo', opts={'vars': {'foo': 'asdf'}})

    async def test_storm_splicelist(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            mesgs = await core.stormlist('[ test:str=foo ]')
            await asyncio.sleep(0.01)

            mesgs = await core.stormlist('[ test:str=bar ]')

            tick = mesgs[0][1]['tick']
            tickdt = datetime.datetime.utcfromtimestamp(tick / 1000.0)
            tickstr = tickdt.strftime('%Y/%m/%d %H:%M:%S.%f')

            tock = mesgs[-1][1]['tock']
            tockdt = datetime.datetime.utcfromtimestamp(tock / 1000.0)
            tockstr = tockdt.strftime('%Y/%m/%d %H:%M:%S.%f')

            await asyncio.sleep(0.01)
            mesgs = await core.stormlist('[ test:str=baz ]')

            nodes = await core.nodes(f'splice.list')
            self.len(9, nodes)

            nodes = await core.nodes(f'splice.list --mintimestamp {tick}')
            self.len(4, nodes)

            nodes = await core.nodes(f'splice.list --mintime "{tickstr}"')
            self.len(4, nodes)

            nodes = await core.nodes(f'splice.list --maxtimestamp {tock}')
            self.len(7, nodes)

            nodes = await core.nodes(f'splice.list --maxtime "{tockstr}"')
            self.len(7, nodes)

            nodes = await core.nodes(f'splice.list --mintimestamp {tick} --maxtimestamp {tock}')
            self.len(2, nodes)

            nodes = await core.nodes(f'splice.list --mintime "{tickstr}" --maxtime "{tockstr}"')
            self.len(2, nodes)

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('splice.list --mintime badtime'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('splice.list --maxtime nope'))

            visi = await prox.addUser('visi', passwd='secret')

            await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

            async with core.getLocalProxy(user='visi') as asvisi:

                # make sure a normal user only gets their own splices
                nodes = await alist(asvisi.eval("[ test:str=hehe ]"))

                nodes = await alist(asvisi.eval("splice.list"))
                self.len(2, nodes)

                # should get all splices now as an admin
                await prox.setUserAdmin(visi['iden'], True)

                nodes = await alist(asvisi.eval("splice.list"))
                self.len(11, nodes)

            msgs = await core.stormlist('splice.undo')
            self.stormIsInWarn('deprecated', msgs)

    async def test_storm_spliceundo(self):

        self.skip('order is different and this is deprecated')
        async with self.getTestCoreAndProxy() as (core, prox):

            await core.addTagProp('risk', ('int', {'min': 0, 'max': 100}), {'doc': 'risk score'})

            visi = await prox.addUser('visi', passwd='secret')

            await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

            async with core.getLocalProxy(user='visi') as asvisi:

                nodes = await alist(asvisi.eval("[ test:str=foo ]"))
                await asyncio.sleep(0.01)

                mesgs = await alist(asvisi.storm("[ test:str=bar ]"))
                tick = mesgs[0][1]['tick']
                tock = mesgs[-1][1]['tock']

                mesgs = await alist(asvisi.storm("test:str=bar [ +#test.tag ]"))

                # undo a node add

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(1, nodes)

                # undo adding a node fails without tag:del perms if is it tagged
                q = f'splice.list --mintimestamp {tick} --maxtimestamp {tock} | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del')))

                # undo adding a node fails without node:del perms
                q = f'splice.list --mintimestamp {tick} --maxtimestamp {tock} | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'del')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(0, nodes)

                # undo a node delete

                # undo deleting a node fails without node:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'add')))

                q = 'splice.list | limit 2 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(1, nodes)

                # undo adding a prop

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=2000 ]"))
                self.nn(nodes[0][1]['props'].get('tick'))

                # undo adding a prop fails without prop:del perms
                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'del',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['props'].get('tick'))

                # undo updating a prop

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=2000 ]"))
                oldv = nodes[0][1]['props']['tick']
                self.nn(oldv)

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=3000 ]"))
                self.ne(oldv, nodes[0][1]['props']['tick'])

                # undo updating a prop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['props']['tick'])

                # undo deleting a prop

                nodes = await alist(asvisi.eval("test:str=foo [ -:tick ]"))
                self.none(nodes[0][1]['props'].get('tick'))

                # undo deleting a prop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['props']['tick'])

                # undo adding a tag

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=2000 ]"))
                tagv = nodes[0][1]['tags'].get('rep')
                self.nn(tagv)

                # undo adding a tag fails without tag:del perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'del',)))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['tags'].get('rep'))

                # undo deleting a tag

                # undo deleting a tag fails without tag:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tags'].get('rep'))

                # undo updating a tag
                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=2000 ]"))
                oldv = nodes[0][1]['tags'].get('rep')
                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=3000 ]"))
                self.ne(oldv, nodes[0][1]['tags'].get('rep'))

                q = 'splice.list | limit 1 | splice.undo'
                await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['tags'].get('rep'))

                # undo adding a tagprop

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep:risk=50 ]"))
                tagv = nodes[0][1]['tagprops']['rep'].get('risk')
                self.nn(tagv)

                # undo adding a tagprop fails without tag:del perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'del')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['tagprops'].get('rep'))

                # undo deleting a tagprop

                # undo deleting a tagprop fails without tag:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # undo updating a tagprop

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep:risk=0 ]"))
                self.ne(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # undo updating a tagprop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # sending nodes of form other than syn:splice doesn't work
                q = 'test:str | limit 1 | splice.undo'
                await self.agenraises(s_exc.StormRuntimeError, asvisi.eval(q))

                # must be admin to use --force for node deletion
                await alist(asvisi.eval('[ test:cycle0=foo :cycle1=bar ]'))
                await alist(asvisi.eval('[ test:cycle1=bar :cycle0=foo ]'))

                nodes = await alist(asvisi.eval("test:cycle0"))
                self.len(1, nodes)

                q = 'splice.list | +:type="node:add" +:form="test:cycle0" | limit 1 | splice.undo'
                await self.agenraises(s_exc.CantDelNode, asvisi.eval(q))

                q = 'splice.list | +:type="node:add" +:form="test:cycle0" | limit 1 | splice.undo --force'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.setUserAdmin(visi['iden'], True)

                nodes = await alist(asvisi.eval(q))
                nodes = await alist(asvisi.eval("test:cycle0"))
                self.len(0, nodes)

    async def test_storm_argv_parser(self):

        pars = s_storm.Parser(prog='hehe')
        pars.add_argument('--hehe')
        self.none(pars.parse_args(['--lol']))
        mesg = "Expected 0 positional arguments. Got 1: ['--lol']"
        self.eq(('BadArg', {'mesg': mesg}), (pars.exc.errname, pars.exc.errinfo))

        pars = s_storm.Parser(prog='hehe')
        pars.add_argument('hehe')
        opts = pars.parse_args(['-h'])
        self.none(opts)
        self.notin("ERROR: The argument <hehe> is required.", pars.mesgs)
        self.isin('Usage: hehe [options] <hehe>', pars.mesgs)
        self.isin('Options:', pars.mesgs)
        self.isin('  --help                      : Display the command usage.', pars.mesgs)
        self.isin('Arguments:', pars.mesgs)
        self.isin('  <hehe>                      : No help available', pars.mesgs)
        self.none(pars.exc)

        pars = s_storm.Parser(prog='hehe')
        pars.add_argument('hehe')
        opts = pars.parse_args(['newp', '-h'])
        self.none(opts)
        mesg = 'Extra arguments and flags are not supported with the help flag: hehe newp -h'
        self.eq(('BadArg', {'mesg': mesg}), (pars.exc.errname, pars.exc.errinfo))

        pars = s_storm.Parser()
        pars.add_argument('--no-foo', default=True, action='store_false')
        opts = pars.parse_args(['--no-foo'])
        self.false(opts.no_foo)

        pars = s_storm.Parser()
        pars.add_argument('--no-foo', default=True, action='store_false')
        opts = pars.parse_args([])
        self.true(opts.no_foo)

        pars = s_storm.Parser()
        pars.add_argument('--no-foo', default=True, action='store_false')
        pars.add_argument('--valu', default=8675309, type='int')
        pars.add_argument('--ques', nargs=2, type='int', default=(1, 2))
        pars.parse_args(['-h'])
        self.isin('  --no-foo                    : No help available.', pars.mesgs)
        self.isin('  --valu <valu>               : No help available. (default: 8675309)', pars.mesgs)
        self.isin('  --ques <ques>               : No help available. (default: (1, 2))', pars.mesgs)

        pars = s_storm.Parser()
        pars.add_argument('--yada')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', action='append')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', nargs='?')
        opts = pars.parse_args(['--yada'])
        self.none(opts.yada)

        pars = s_storm.Parser()
        pars.add_argument('--yada', nargs='+')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='int')
        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)

        # check help output formatting of optargs
        pars = s_storm.Parser()
        pars.add_argument('--star', nargs='*')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--star [<star> ...]', helptext)

        pars = s_storm.Parser()
        pars.add_argument('--plus', nargs='+')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--plus <plus> [<plus> ...]', helptext)

        pars = s_storm.Parser()
        pars.add_argument('--woot', nargs='+', default=[
            'The 1st Battalion, 26th Infantry Regiment "Blue Spaders" hosted Steve Rogers ',
            'for much of WWII. While initially using his sidearm,',
            'his Vibranium/steel alloy shield made by metallurgist Dr. Myron MacLain,',
            'quickly became his weapon of choice.'])
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('default: \n[', helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='?')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--ques [ques]', helptext)

        # Check formatting for store_true / store_false optargs
        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2, type='int')
        pars.add_argument('--beep', action='store_true', help='beep beep')
        pars.add_argument('--boop', action='store_false', help='boop boop')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--ques <ques>               : No help available', helptext)
        self.isin('--beep                      : beep beep', helptext)
        self.isin('--boop                      : boop boop', helptext)

        # test some nargs type intersections
        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='?', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        self.eq("Invalid value for type (int): asdf", pars.exc.errinfo['mesg'])

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='*', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        self.eq("Invalid value for type (int): asdf", pars.exc.errinfo['mesg'])

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='+', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        self.eq("Invalid value for type (int): asdf", pars.exc.errinfo['mesg'])

        pars = s_storm.Parser()
        pars.add_argument('foo', type='int')
        self.none(pars.parse_args(['asdf']))
        self.eq("Invalid value for type (int): asdf", pars.exc.errinfo['mesg'])

        # argument count mismatch
        pars = s_storm.Parser()
        pars.add_argument('--ques')
        self.none(pars.parse_args(['--ques']))
        self.eq("An argument is required for --ques.", pars.exc.errinfo['mesg'])

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2)
        self.none(pars.parse_args(['--ques', 'lolz']))
        self.eq("2 arguments are required for --ques.", pars.exc.errinfo['mesg'])

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2, type='int')
        self.none(pars.parse_args(['--ques', 'lolz', 'hehe']))
        self.eq("Invalid value for type (int): lolz", pars.exc.errinfo['mesg'])

        # test time argtype
        ttyp = s_datamodel.Model().type('time')

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='time')
        args = pars.parse_args(['--yada', '20201021-1day'])
        self.nn(args)
        self.eq(ttyp.norm('20201021-1day')[0], args.yada)

        args = pars.parse_args(['--yada', 1603229675444])
        self.nn(args)
        self.eq(ttyp.norm(1603229675444)[0], args.yada)

        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)
        self.eq("Invalid value for type (time): hehe", pars.exc.errinfo['mesg'])

        # test ival argtype
        ityp = s_datamodel.Model().type('ival')

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='ival')
        args = pars.parse_args(['--yada', '20201021-1day'])
        self.nn(args)
        self.eq(ityp.norm('20201021-1day')[0], args.yada)

        args = pars.parse_args(['--yada', 1603229675444])
        self.nn(args)
        self.eq(ityp.norm(1603229675444)[0], args.yada)

        args = pars.parse_args(['--yada', ('20201021', '20201023')])
        self.nn(args)
        self.eq(ityp.norm(('20201021', '20201023'))[0], args.yada)

        args = pars.parse_args(['--yada', (1603229675444, '20201021')])
        self.nn(args)
        self.eq(ityp.norm((1603229675444, '20201021'))[0], args.yada)

        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)
        self.eq("Invalid value for type (ival): hehe", pars.exc.errinfo['mesg'])

        # check adding argument with invalid type
        with self.raises(s_exc.BadArg):
            pars = s_storm.Parser()
            pars.add_argument('--yada', type=int)

    async def test_storm_cmd_help(self):

        async with self.getTestCore() as core:
            pdef = {
                'name': 'testpkg',
                'version': '0.0.1',
                'commands': (
                    {'name': 'woot', 'cmdinputs': (
                        {'form': 'hehe:haha'},
                        {'form': 'hoho:lol', 'help': 'We know whats up'}
                    )},
                ),
            }
            await core.loadStormPkg(pdef)
            msgs = await core.stormlist('woot --help')
            helptext = '\n'.join([m[1].get('mesg') for m in msgs if m[0] == 'print'])
            self.isin('Inputs:\n\n    hehe:haha\n    hoho:lol  - We know whats up', helptext)

    async def test_liftby_edge(self):
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=test1 +(refs)> { [test:int=7] } ]')
            await core.nodes('[ test:str=test1 +(refs)> { [test:int=8] } ]')
            await core.nodes('[ test:str=test2 +(refs)> { [test:int=8] } ]')

            nodes = await core.nodes('lift.byverb refs')
            self.eq(sorted([n.ndef[1] for n in nodes]), ['test1', 'test2'])

            nodes = await core.nodes('lift.byverb --n2 refs ')
            self.eq(sorted([n.ndef[1] for n in nodes]), [7, 8])

            nodes = await core.nodes('lift.byverb $v', {'vars': {'v': 'refs'}})
            self.eq(sorted([n.ndef[1] for n in nodes]), ['test1', 'test2'])

            q = '[(test:str=refs) (test:str=foo)] $v=$node.value() | lift.byverb $v'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq({n.ndef[1] for n in nodes},
                    {'test1', 'test2', 'refs', 'foo'})

    async def test_storm_nested_root(self):
        async with self.getTestCore() as core:
            self.eq(20, await core.callStorm('''
            $foo = (100)
            function x() {
                function y() {
                    function z() {
                        $foo = (20)
                    }
                    $z()
                }
                $y()
            }
            $x()
            return ($foo)
            '''))

    async def test_edges_del(self):
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=test1 +(refs)> { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=test1 +(seen)> { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 -(*)> *'))

            await core.nodes('test:str=test1 | edges.del refs')
            self.len(0, await core.nodes('test:str=test1 -(refs)> *'))
            self.len(2, await core.nodes('test:str=test1 -(seen)> *'))

            await core.nodes('test:str=test1 [ +(refs)> { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 -(*)> *'))

            await core.nodes('test:str=test1 | edges.del *')
            self.len(0, await core.nodes('test:str=test1 -(*)> *'))

            # Test --n2
            await core.nodes('test:str=test1 [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('test:str=test1 [ <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 <(*)- *'))

            await core.nodes('test:str=test1 | edges.del refs --n2')
            self.len(0, await core.nodes('test:str=test1 <(refs)- *'))
            self.len(2, await core.nodes('test:str=test1 <(seen)- *'))

            await core.nodes('test:str=test1 [ <(refs)+ { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 <(*)- *'))

            await core.nodes('test:str=test1 | edges.del * --n2')
            self.len(0, await core.nodes('test:str=test1 <(*)- *'))

            # Test non-runtsafe usage
            await core.nodes('[ test:str=refs +(refs)> { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=seen +(seen)> { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs -(refs)> *'))
            self.len(2, await core.nodes('test:str=seen -(seen)> *'))

            await core.nodes('test:str=refs test:str=seen $v=$node.value() | edges.del $v')

            self.len(0, await core.nodes('test:str=refs -(refs)> *'))
            self.len(0, await core.nodes('test:str=seen -(seen)> *'))

            await core.nodes('test:str=refs [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('test:str=seen [ <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs <(refs)- *'))
            self.len(2, await core.nodes('test:str=seen <(seen)- *'))

            await core.nodes('test:str=refs test:str=seen $v=$node.value() | edges.del $v --n2')

            self.len(0, await core.nodes('test:str=refs <(refs)- *'))
            self.len(0, await core.nodes('test:str=seen <(seen)- *'))

            await core.nodes('test:str=refs [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=* <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs <(refs)- *'))
            self.len(2, await core.nodes('test:str=* <(seen)- *'))

            await core.nodes('test:str=refs test:str=* $v=$node.value() | edges.del $v --n2')

            self.len(0, await core.nodes('test:str=refs <(refs)- *'))
            self.len(0, await core.nodes('test:str=* <(seen)- *'))

            # Test perms
            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            await core.nodes('test:str=test1 [ +(refs)> { test:int=7 } ]')
            self.len(1, await core.nodes('test:str=test1 -(refs)> *'))

            async with core.getLocalProxy(user='visi') as asvisi:
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm('test:str=test1 | edges.del refs')

                await visi.addRule((True, ('node', 'edge', 'del', 'refs')))

                await asvisi.callStorm('test:str=test1 | edges.del refs')
                self.len(0, await core.nodes('test:str=test1 -(refs)> *'))

                await core.nodes('test:str=test1 [ +(refs)> { test:int=7 } ]')
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm('test:str=test1 | edges.del *')

                await visi.addRule((True, ('node', 'edge', 'del')))

                await asvisi.callStorm('test:str=test1 | edges.del *')
                self.len(0, await core.nodes('test:str=test1 -(refs)> *'))

    async def test_storm_pushpull(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                visi = await core.auth.addUser('visi')
                await visi.setPasswd('secret')

                await core.auth.rootuser.setPasswd('secret')
                host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

                # setup a trigger so we know when the nodes move...
                view0, layr0 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')
                view1, layr1 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')
                view2, layr2 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')

                opts = {'vars': {
                    'view0': view0,
                    'view1': view1,
                    'view2': view2,
                    'layr0': layr0,
                    'layr1': layr1,
                    'layr2': layr2,
                }}

                # lets get some auth denies...
                async with core.getLocalProxy(user='visi') as asvisi:

                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr0).addPush(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr0).delPush(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).addPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).delPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).addPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).delPull(hehe)', opts=opts)

                actv = len(core.activecoros)
                # view0 -push-> view1 <-pull- view2
                await core.callStorm(f'$lib.layer.get($layr0).addPush("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)
                await core.callStorm(f'$lib.layer.get($layr2).addPull("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)

                purl = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr2).get(pulls) { return($pdef.url) }', opts=opts)
                self.true(purl.startswith('tcp://root:****@127.0.0.1'))
                purl = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr0).get(pushs) { return($pdef.url) }', opts=opts)
                self.true(purl.startswith('tcp://root:****@127.0.0.1'))

                msgs = await core.stormlist('layer.push.list $layr0', opts=opts)
                self.stormIsInPrint('tcp://root:****@127.0.0.1', msgs)

                msgs = await core.stormlist('layer.pull.list $layr2', opts=opts)
                self.stormIsInPrint('tcp://root:****@127.0.0.1', msgs)

                self.eq(2, len(core.activecoros) - actv)
                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(1, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(1, [t for t in tasks if t.get('name').startswith('layer push:')])

                await core.nodes('[ ps:contact=* ]', opts={'view': view0})

                # wait for first write so we can get the correct offset
                await core.layers.get(layr2).waitEditOffs(0, timeout=3)
                offs = await core.layers.get(layr2).getEditOffs()

                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.layers.get(layr2).waitEditOffs(offs + 10, timeout=3)

                self.len(3, await core.nodes('ps:contact', opts={'view': view1}))
                self.len(3, await core.nodes('ps:contact', opts={'view': view2}))

                # Check offset reporting
                q = '$layer=$lib.layer.get($layr0) return ($layer.pack())'
                layrinfo = await core.callStorm(q, opts=opts)
                pushs = layrinfo.get('pushs')
                self.len(1, pushs)
                pdef = list(pushs.values())[0]
                self.lt(10, pdef.get('offs', 0))

                q = '$layer=$lib.layer.get($layr2) return ($layer.pack())'
                layrinfo = await core.callStorm(q, opts=opts)
                pulls = layrinfo.get('pulls')
                self.len(1, pulls)
                pdef = list(pulls.values())[0]
                self.lt(10, pdef.get('offs', 0))

                # remove and ensure no replay on restart
                await core.nodes('ps:contact | delnode', opts={'view': view2})
                self.len(0, await core.nodes('ps:contact', opts={'view': view2}))

            conf = {'dmon:listen': f'tcp://127.0.0.1:{port}'}
            async with self.getTestCore(dirn=dirn, conf=conf) as core:

                await asyncio.sleep(0)

                offs = await core.layers.get(layr2).getEditOffs()
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.layers.get(layr2).waitEditOffs(offs + 6, timeout=3)

                # confirm we dont replay and get the old one back...
                self.len(3, await core.nodes('ps:contact', opts={'view': view2}))

                actv = len(core.activecoros)
                # remove all pushes / pulls
                await core.callStorm('''
                    for $layr in $lib.layer.list() {
                        $pushs = $layr.get(pushs)
                        if $pushs {
                            for ($iden, $pdef) in $pushs { $layr.delPush($iden) }
                        }
                        $pulls = $layr.get(pulls)
                        if $pulls {
                            for ($iden, $pdef) in $pulls { $layr.delPull($iden) }
                        }
                    }
                ''')
                self.eq(actv - 2, len(core.activecoros))
                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(0, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(0, [t for t in tasks if t.get('name').startswith('layer push:')])

                # code coverage for push/pull dict exists but has no entries
                self.none(await core.callStorm('return($lib.layer.get($layr2).delPull($lib.guid()))', opts=opts))
                self.none(await core.callStorm('return($lib.layer.get($layr0).delPush($lib.guid()))', opts=opts))

                msgs = await core.stormlist('layer.push.list $layr0', opts=opts)
                self.stormIsInPrint('No pushes configured', msgs)

                msgs = await core.stormlist('layer.pull.list $layr2', opts=opts)
                self.stormIsInPrint('No pulls configured', msgs)

                # Test storm command add/del
                q = f'layer.push.add $layr0 "tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}"'
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Layer push added', msgs)

                q = f'layer.pull.add $layr2 "tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}"'
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Layer pull added', msgs)

                msgs = await core.stormlist('layer.push.list $layr0', opts=opts)
                self.stormIsInPrint('tcp://root:****@127.0.0.1', msgs)

                msgs = await core.stormlist('layer.pull.list $layr2', opts=opts)
                self.stormIsInPrint('tcp://root:****@127.0.0.1', msgs)

                pidn = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr0).get(pushs) { return($iden) }', opts=opts)
                msgs = await core.stormlist(f'layer.push.del $layr0 {pidn}', opts=opts)
                self.stormIsInPrint('Layer push deleted', msgs)
                msgs = await core.stormlist('layer.push.list $layr0', opts=opts)
                self.stormIsInPrint('No pushes configured', msgs)

                pidn = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr2).get(pulls) { return($iden) }', opts=opts)
                msgs = await core.stormlist(f'layer.pull.del $layr2 {pidn}', opts=opts)
                self.stormIsInPrint('Layer pull deleted', msgs)
                msgs = await core.stormlist('layer.pull.list $layr2', opts=opts)
                self.stormIsInPrint('No pulls configured', msgs)

                # add a push/pull and remove the layer to cancel it...
                await core.callStorm(f'$lib.layer.get($layr0).addPush("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)
                await core.callStorm(f'$lib.layer.get($layr2).addPull("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)

                await asyncio.sleep(0)

                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(1, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(1, [t for t in tasks if t.get('name').startswith('layer push:')])
                self.eq(actv, len(core.activecoros))

                pushpulls = set()
                for ldef in await core.getLayerDefs():
                    pushpulls.update(ldef.get('pushs', {}))
                    pushpulls.update(ldef.get('pulls', {}))

                tasks = [cdef.get('task') for iden, cdef in core.activecoros.items() if iden in pushpulls]

                await core.callStorm('$lib.view.del($view0)', opts=opts)
                await core.callStorm('$lib.view.del($view1)', opts=opts)
                await core.callStorm('$lib.view.del($view2)', opts=opts)
                await core.callStorm('$lib.layer.del($layr0)', opts=opts)
                await core.callStorm('$lib.layer.del($layr1)', opts=opts)
                await core.callStorm('$lib.layer.del($layr2)', opts=opts)

                # Wait for the active coros to die
                for task in [t for t in tasks if t is not None]:
                    self.true(await s_coro.waittask(task, timeout=5))

                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(0, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(0, [t for t in tasks if t.get('name').startswith('layer push:')])
                self.eq(actv - 2, len(core.activecoros))

                with self.raises(s_exc.SchemaViolation):
                    await core.addLayrPush('newp', {})
                with self.raises(s_exc.SchemaViolation):
                    await core.addLayrPull('newp', {})

                # sneak a bit of coverage for the raw library in here...
                fake = {
                    'time': s_common.now(),
                    'iden': s_common.guid(),
                    'user': s_common.guid(),
                    'url': 'tcp://localhost',
                }
                self.none(await core.addLayrPush('newp', fake))
                self.none(await core.addLayrPull('newp', fake))

                self.none(await core.delLayrPull('newp', 'newp'))
                self.none(await core.delLayrPull(layr0, 'newp'))
                self.none(await core.delLayrPush('newp', 'newp'))
                self.none(await core.delLayrPush(layr0, 'newp'))

                # main view/layer have None for pulls/pushs
                self.none(await core.delLayrPull(core.getView().layers[0].iden, 'newp'))
                self.none(await core.delLayrPush(core.getView().layers[0].iden, 'newp'))

                async with await s_telepath.openurl(f'tcp://visi:secret@127.0.0.1:{port}/*/view') as proxy:
                    self.eq(core.getView().iden, await proxy.getCellIden())
                    with self.raises(s_exc.AuthDeny):
                        await proxy.storNodeEdits((), {})

                with self.raises(s_exc.NoSuchPath):
                    async with await s_telepath.openurl(f'tcp://root:secret@127.0.0.1:{port}/*/newp'):
                        pass

                class LayrBork:
                    async def syncNodeEdits(self, offs, wait=True):
                        if False: yield None
                        raise s_exc.SynErr()

                fake = {'iden': s_common.guid(), 'user': s_common.guid()}
                # this should fire the reader and exit cleanly when he explodes
                await core._pushBulkEdits(LayrBork(), LayrBork(), fake)

                class FastPull:
                    async def syncNodeEdits(self, offs, wait=True):
                        yield (0, range(2000))

                class FastPush:
                    def __init__(self):
                        self.edits = []
                    async def storNodeEdits(self, edits, meta):
                        self.edits.extend(edits)

                pull = FastPull()
                push = FastPush()

                await core._pushBulkEdits(pull, push, fake)
                self.eq(push.edits, tuple(range(2000)))

                # a quick/ghetto test for coverage...
                layr = core.getView().layers[0]
                layr.logedits = False
                with self.raises(s_exc.BadArg):
                    await layr.waitEditOffs(200)

    async def test_storm_tagprune(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('parent.child.grandchild')

                node = await snap.addNode('test:str', 'bar')
                await node.addTag('parent.childtag')
                await node.addTag('parent.child.step')
                await node.addTag('parent.child.grandchild')

                node = await snap.addNode('test:str', 'baz')
                await node.addTag('parent.child.step')
                await node.addTag('parent.child.step.two')
                await node.addTag('parent.child.step.three')

            # Won't do anything but should work
            nodes = await core.nodes('test:str | tag.prune')
            self.len(3, nodes)

            node = (await core.nodes('test:str=foo'))[0]
            exp = [
                'parent',
                'parent.child',
                'parent.child.grandchild'
            ]
            self.eq(list(node.tags.keys()), exp)

            node = (await core.nodes('test:str=bar'))[0]
            exp = [
                'parent',
                'parent.childtag',
                'parent.child',
                'parent.child.step',
                'parent.child.grandchild'
            ]
            self.eq(list(node.tags.keys()), exp)

            node = (await core.nodes('test:str=baz'))[0]
            exp = [
                'parent',
                'parent.child',
                'parent.child.step',
                'parent.child.step.two',
                'parent.child.step.three'
            ]
            self.eq(list(node.tags.keys()), exp)

            await core.nodes('test:str | tag.prune parent.child.grandchild')

            # Should remove all tags
            node = (await core.nodes('test:str=foo'))[0]
            self.eq(list(node.tags.keys()), [])

            # Should only remove parent.child.grandchild
            node = (await core.nodes('test:str=bar'))[0]
            exp = ['parent', 'parent.childtag', 'parent.child', 'parent.child.step']
            self.eq(list(node.tags.keys()), exp)

            await core.nodes('test:str | tag.prune parent.child.step')

            # Should only remove parent.child.step and parent.child
            node = (await core.nodes('test:str=bar'))[0]
            self.eq(list(node.tags.keys()), ['parent', 'parent.childtag'])

            # Should remove all tags
            node = (await core.nodes('test:str=baz'))[0]
            self.eq(list(node.tags.keys()), [])

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('tag.tree.one')
                await node.addTag('tag.tree.two')
                await node.addTag('another.tag.tree')

                node = await snap.addNode('test:str', 'baz')
                await node.addTag('tag.tree.one')
                await node.addTag('tag.tree.two')
                await node.addTag('another.tag.tree')
                await node.addTag('more.tags.to.remove')
                await node.addTag('tag.that.stays')

            # Remove multiple tags
            tags = '''
                tag.tree.one
                tag.tree.two
                another.tag.tree
                more.tags.to.remove
            '''
            await core.nodes(f'test:str | tag.prune {tags}')

            node = (await core.nodes('test:str=foo'))[0]
            self.eq(list(node.tags.keys()), [])

            node = (await core.nodes('test:str=baz'))[0]
            exp = ['tag', 'tag.that', 'tag.that.stays']
            self.eq(list(node.tags.keys()), exp)

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'runtsafety')
                await node.addTag('runtsafety')

                node = await snap.addNode('test:str', 'foo')
                await node.addTag('runtsafety')

                node = await snap.addNode('test:str', 'runt.safety.two')
                await node.addTag('runt.safety.two')
                await node.addTag('runt.child')

            # Test non-runtsafe usage
            await core.nodes('test:str | tag.prune $node.value()')

            node = (await core.nodes('test:str=runtsafety'))[0]
            self.eq(list(node.tags.keys()), [])

            node = (await core.nodes('test:str=foo'))[0]
            self.eq(list(node.tags.keys()), ['runtsafety'])

            node = (await core.nodes('test:str=runt.safety.two'))[0]
            self.eq(list(node.tags.keys()), ['runt', 'runt.child'])

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('runt.need.perms')

                node = await snap.addNode('test:str', 'runt.safety.two')
                await node.addTag('runt.safety.two')

            # Test perms
            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            async with core.getLocalProxy(user='visi') as asvisi:
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'test:str | tag.prune runt.need.perms')

                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'test:str | tag.prune $node.value()')

            await visi.addRule((True, ('node', 'tag', 'del', 'runt')))

            async with core.getLocalProxy(user='visi') as asvisi:
                await asvisi.callStorm(f'test:str | tag.prune runt.need.perms')

                node = (await core.nodes('test:str=foo'))[0]
                self.eq(list(node.tags.keys()), ['runtsafety'])

                await asvisi.callStorm(f'test:str=runt.safety.two | tag.prune $node.value()')

                node = (await core.nodes('test:str=runt.safety.two'))[0]
                self.eq(list(node.tags.keys()), ['runt', 'runt.child'])

    async def test_storm_cmdscope(self):

        async with self.getTestCore() as core:
            await core.loadStormPkg({
                'name': 'testpkg',
                'version': '0.0.1',
                'commands': (
                    {'name': 'woot', 'cmdargs': (('hehe', {}),), 'storm': 'spin | [ inet:ipv4=1.2.3.4 ]'},
                    {'name': 'stomp', 'storm': '$fqdn=lol'},
                    {'name': 'gronk', 'storm': 'init { $fqdn=foo } $lib.print($fqdn)'},
                ),
            })
            # Success for the next two tests is that these don't explode with errors..
            self.len(1, await core.nodes('''
                [ inet:fqdn=vertex.link ]
                $fqdn=$node.repr()
                | woot lol |
                $lib.print($path.vars.fqdn)
            '''))
            # Non-runtsafe scope
            self.len(1, await core.nodes('''
                [ inet:fqdn=vertex.link ]
                $fqdn=$node.repr()
                | woot $node |
                $lib.print($path.vars.fqdn)
            '''))

            msgs = await core.stormlist('''
                [ inet:fqdn=vertex.link ]
                $fqdn=$node.repr()
                | stomp |
                $lib.print($fqdn)
            ''')
            self.stormIsInPrint('vertex.link', msgs)
            self.stormNotInPrint('lol', msgs)

            msgs = await core.stormlist('''
                [ inet:fqdn=vertex.link ]
                $fqdn=$node.repr()
                | gronk
            ''')
            self.stormIsInPrint('foo', msgs)
            self.stormNotInPrint('vertex.link', msgs)

    async def test_storm_version(self):

        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                msgs = await core.stormlist('version')

                self.stormIsInPrint('Synapse Version:', msgs)
                self.stormIsInPrint('Commit Hash:', msgs)

    async def test_storm_runas(self):
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            nodes = await core.nodes('[ inet:fqdn=foo.com ]')
            self.len(1, nodes)

            q = 'runas visi { [ inet:fqdn=bar.com ] }'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q))

            await visi.addRule((True, ('node', 'add')))

            await core.nodes('runas visi { [ inet:fqdn=bar.com ] }')

            items = await alist(core.syncLayersEvents({}, wait=False))
            self.len(4, [item for item in items if item[-1]['user'] == visi.iden])

            await core.nodes(f'runas {visi.iden} {{ [ inet:fqdn=baz.com ] }}')

            items = await alist(core.syncLayersEvents({}, wait=False))
            self.len(8, [item for item in items if item[-1]['user'] == visi.iden])

            q = 'inet:fqdn $n=$node runas visi { yield $n [ +#atag ] }'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q))

            await visi.addRule((True, ('node', 'tag', 'add')))

            nodes = await core.nodes(q)
            for node in nodes:
                self.nn(node.tags.get('atag'))

            async with core.getLocalProxy(user='visi') as asvisi:
                await self.asyncraises(s_exc.AuthDeny, asvisi.callStorm(q))

            q = '$tag=btag runas visi { inet:fqdn=foo.com [ +#$tag ] }'
            await core.nodes(q)
            nodes = await core.nodes('inet:fqdn=foo.com')
            self.nn(nodes[0].tags.get('btag'))

            await self.asyncraises(s_exc.NoSuchUser, core.nodes('runas newp { inet:fqdn=foo.com }'))

            cmd0 = {
                'name': 'asroot.not',
                'storm': 'runas visi { inet:fqdn=foo.com [-#btag ] }',
                'asroot': True,
            }
            cmd1 = {
                'name': 'asroot.yep',
                'storm': 'runas visi --asroot { inet:fqdn=foo.com [-#btag ] }',
                'asroot': True,
            }
            await core.setStormCmd(cmd0)
            await core.setStormCmd(cmd1)

            await self.asyncraises(s_exc.AuthDeny, core.nodes('asroot.not'))

            nodes = await core.nodes('asroot.yep | inet:fqdn=foo.com')
            for node in nodes:
                self.none(node.tags.get('btag'))

    async def test_storm_queries(self):
        async with self.getTestCore() as core:

            q = '''
            [ inet:ipv4=1.2.3.4
                // add an asn
                :asn=1234
                /* also set .seen
                   to now
                */
                .seen = now
            ]'''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('asn'), 1234)
            self.nn(nodes[0].props.get('.seen'))

            case = [
                ('+', 'plus'),
                ('-', 'minus'),
                ('/', 'div'),
                ('+-', 'plusminus'),
                ('-+', 'minusplus'),
                ('--', 'minusminus'),
                ('++', 'plusplus'),
            ]

            for valu, exp in case:
                q = f'$x={valu}'
                q += '''
                switch $x {
                    +: { $lib.print(plus) }
                    //comm
                    -: { $lib.print(minus) }
                    /*comm*/ +-: { $lib.print(plusminus) }
                    -+ : { $lib.print(minusplus) }
                    // -+: { $lib.print(fake) }
                    /* -+: { $lib.print(fake2) } */
                    --: { $lib.print(minusminus) }
                    ++: { $lib.print(plusplus) }
                    /: { $lib.print(div) }
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint(exp, msgs)

            q = 'iden			Jul 17, 2019, 8:14:22 PM		10	 hostname'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('Failed to decode iden: [Jul]', msgs)
            self.stormIsInWarn('Failed to decode iden: [17, ]', msgs)
            self.stormIsInWarn('Failed to decode iden: [2019, ]', msgs)
            self.stormIsInWarn('Failed to decode iden: [8:14:22]', msgs)
            self.stormIsInWarn('Failed to decode iden: [PM]', msgs)
            self.stormIsInWarn('iden must be 32 bytes [10]', msgs)
            self.stormIsInWarn('Failed to decode iden: [hostname]', msgs)

            q = 'iden https://intelx.io/?s=3NBtmP3tZtZQHKrTCtTEiUby9dgujnmV6q --test=asdf'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('Failed to decode iden: [https://intelx.io/?s=3NBtmP3tZtZQHKrTCtTEiUby9dgujnmV6q]', msgs)
            self.stormIsInWarn('Failed to decode iden: [--test]', msgs)
            self.stormIsInWarn('Failed to decode iden: [asdf]', msgs)

            q = 'iden 192[.]foo[.]bar'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('Failed to decode iden: [192[.]foo[.]bar]', msgs)

            q = '''file:bytes#aka.feye.thr.apt1 ->it:exec:file:add  ->file:path |uniq| ->file:base |uniq ->file:base:ext=doc'''
            msgs = await core.stormlist(q)
            self.stormIsInErr("Expected 0 positional arguments. Got 2: ['->', 'file:base:ext=doc']", msgs)

            msgs = await core.stormlist('help yield')
            self.stormIsInPrint('No commands found matching "yield"', msgs)

            q = '''inet:fqdn:zone=earthsolution.org -> inet:dns:request -> file:bytes | uniq -> inet.dns.request'''
            msgs = await core.stormlist(q)
            self.stormIsInErr("Expected 0 positional arguments. Got 1: ['->inet.dns.request']", msgs)

            await core.nodes('''$token=foo $lib.print(({"Authorization":$lib.str.format("Bearer {token}", token=$token)}))''')

            q = '#rep.clearsky.dreamjob -># +syn:tag^=rep |uniq -syn:tag~=rep.clearsky'
            msgs = await core.stormlist(q)
            self.stormIsInErr("Expected 0 positional arguments", msgs)

            q = 'service.add svcrs ssl://svcrs:27492?certname=root'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('(svcrs): ssl://svcrs:27492?certname=root', msgs)

            q = 'iden ssl://svcrs:27492?certname=root=bar'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('Failed to decode iden: [ssl://svcrs:27492?certname=root=bar]', msgs)

            q = "$foo=one $bar=two $lib.print($lib.str.concat($foo, '=', $bar))"
            msgs = await core.stormlist(q)
            self.stormIsInPrint("one=two", msgs)

            q = "function test(){ $asdf=foo $return () }"
            msgs = await core.stormlist(q)
            self.stormIsInErr("Unexpected token '}'", msgs)

            retn = await core.callStorm('return((60*60))')
            self.eq(retn, 3600)

            retn = await core.callStorm('return((1*2 * 3))')
            self.eq(retn, 6)

            retn = await core.callStorm('return((0x10))')
            self.eq(retn, 16)

            retn = await core.callStorm('return((0x10*0x10))')
            self.eq(retn, 256)

            retn = await core.callStorm('return((0x10*0x10 + 5))')
            self.eq(retn, 261)

            retn = await core.callStorm('return((0x10*0x10,))')
            self.eq(retn, ('0x10*0x10',))

            nodes = await core.nodes('[inet:whois:email=(usnewssite.com, contact@privacyprotect.org) .seen=(2008/07/10 00:00:00.000, 2020/06/29 00:00:00.001)] +inet:whois:email.seen@=(2018/01/01, now)')
            self.len(1, nodes)

            retn = await core.callStorm('return((2021/12 00, 2021/12 :foo))')
            self.eq(retn, ('2021/12 00', '2021/12 :foo'))

            q = '''
            $foo=(123)
            if ($foo = 123 or not $foo = "cool, str("
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(success)
            }
            if ($foo = 123 or not $foo = "cool, \\"str("
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(escaped)
            }
            if ($foo = 123 or not $foo = \'\'\'cool, "'str(\'\'\'
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(triple)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("success", msgs)
            self.stormIsInPrint("escaped", msgs)
            self.stormIsInPrint("triple", msgs)

            q = '''
            $foo=(123)
            if ($foo = 123 or $lib.concat('foo),b"ar', 'baz')) {
                $lib.print(nest1)
            }
            if ($foo = 123 or (not $foo='baz' and $lib.concat("foo),b'ar", 'baz'))) {
                $lib.print(nest2)
            }
            if ($foo = 123 or (not $foo='baz' and $lib.concat(\'\'\'foo),b'"ar\'\'\', 'baz'))) {
                $lib.print(nest3)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("nest1", msgs)
            self.stormIsInPrint("nest2", msgs)
            self.stormIsInPrint("nest3", msgs)

            q = '''
            $foo=(0x40)
            if ($foo = 64 and $foo = 0x40 and not $foo = "cool, str("
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(success)
            }
            if ($foo = 64 and $foo = 0x40 and not $foo = "cool, \\"str("
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(escaped)
            }
            if ($foo = 64 and $foo = 0x40 and not $foo = \'\'\'cool, "'str(\'\'\'
                or $lib.concat("foo,bar", 'baz', 'cool)')) {
                $lib.print(triple)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("success", msgs)
            self.stormIsInPrint("escaped", msgs)
            self.stormIsInPrint("triple", msgs)

            q = '''
            $foo=(0x40)
            if ($foo = 64 or $lib.concat('foo),b"ar', 'baz')) {
                $lib.print(nest1)
            }
            if ($foo = 64 or (not $foo='baz' and $lib.concat("foo),b'ar", 'baz'))) {
                $lib.print(nest2)
            }
            if ($foo = 64 or (not $foo='baz' and $lib.concat(\'\'\'foo),b'"ar\'\'\', 'baz'))) {
                $lib.print(nest3)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("nest1", msgs)
            self.stormIsInPrint("nest2", msgs)
            self.stormIsInPrint("nest3", msgs)

            await core.addTagProp('score', ('int', {}), {})

            await core.nodes('[(media:news=* :org=foo) (inet:ipv4=1.2.3.4 +#test:score=1)]')

            q = 'media:news:org #test'
            self.len(2, await core.nodes(q))
            self.len(1, await core.nodes('#test'))

            q = 'media:news:org #test:score'
            self.len(2, await core.nodes(q))
            self.len(1, await core.nodes('#test:score'))

            q = 'media:news:org#test'
            msgs = await core.stormlist(q)
            self.stormIsInErr('No form media:news:org', msgs)

            q = 'media:news:org#test:score'
            msgs = await core.stormlist(q)
            self.stormIsInErr('No form media:news:org', msgs)

            q = 'media:news:org#test.*.bar'
            msgs = await core.stormlist(q)
            self.stormIsInErr('Invalid wildcard usage in tag test.*.bar', msgs)

            q = '#test.*.bar'
            msgs = await core.stormlist(q)
            self.stormIsInErr('Invalid wildcard usage in tag test.*.bar', msgs)

            q = 'media:news:org#test.*.bar:score'
            msgs = await core.stormlist(q)
            self.stormIsInErr('Invalid wildcard usage in tag test.*.bar', msgs)
