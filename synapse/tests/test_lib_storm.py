import copy
import asyncio
import datetime
import itertools
import urllib.parse as u_parse
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.storm as s_storm
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

import synapse.tools.backup as s_tools_backup

class StormTest(s_t_utils.SynTest):

    async def test_lib_storm_guidctor(self):
        async with self.getTestCore() as core:

            nodes00 = await core.nodes('[ ou:org=({"name": "vertex"}) ]')
            self.len(1, nodes00)
            self.eq('vertex', nodes00[0].get('name'))

            nodes01 = await core.nodes('[ ou:org=({"name": "vertex"}) :names+="the vertex project"]')
            self.len(1, nodes01)
            self.eq('vertex', nodes01[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes02 = await core.nodes('[ ou:org=({"name": "the vertex project"}) ]')
            self.len(1, nodes02)
            self.eq('vertex', nodes02[0].get('name'))
            self.eq(nodes01[0].ndef, nodes02[0].ndef)

            nodes03 = await core.nodes('[ ou:org=({"name": "vertex", "type": "woot"}) :names+="the vertex project" ]')
            self.len(1, nodes03)
            self.ne(nodes02[0].ndef, nodes03[0].ndef)

            nodes04 = await core.nodes('[ ou:org=({"name": "the vertex project", "type": "woot"}) ]')
            self.len(1, nodes04)
            self.eq(nodes03[0].ndef, nodes04[0].ndef)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({"hq": "woot"}) ]')

            nodes05 = await core.nodes('[ ou:org=({"name": "vertex", "$props": {"motto": "for the people"}}) ]')
            self.len(1, nodes05)
            self.eq('vertex', nodes05[0].get('name'))
            self.eq('for the people', nodes05[0].get('motto'))
            self.eq(nodes00[0].ndef, nodes05[0].ndef)

            nodes06 = await core.nodes('[ ou:org=({"name": "acme", "$props": {"motto": "HURR DURR"}}) ]')
            self.len(1, nodes06)
            self.eq('acme', nodes06[0].get('name'))
            self.eq('hurr durr', nodes06[0].get('motto'))
            self.ne(nodes00[0].ndef, nodes06[0].ndef)

            goals = [s_common.guid(), s_common.guid()]
            goals.sort()

            nodes07 = await core.nodes('[ ou:org=({"name": "goal driven", "goals": $goals}) ]', opts={'vars': {'goals': goals}})
            self.len(1, nodes07)
            self.eq(goals, nodes07[0].get('goals'))

            nodes08 = await core.nodes('[ ou:org=({"name": "goal driven", "goals": $goals}) ]', opts={'vars': {'goals': goals}})
            self.len(1, nodes08)
            self.eq(goals, nodes08[0].get('goals'))
            self.eq(nodes07[0].ndef, nodes08[0].ndef)

            nodes09 = await core.nodes('[ ou:org=({"name": "vertex"}) :name=foobar :names=() ]')
            nodes10 = await core.nodes('[ ou:org=({"name": "vertex"}) :type=lulz ]')
            self.len(1, nodes09)
            self.len(1, nodes10)
            self.ne(nodes09[0].ndef, nodes10[0].ndef)

            await core.nodes('[ ou:org=* :type=lulz ]')
            await core.nodes('[ ou:org=* :type=hehe ]')
            nodes11 = await core.nodes('[ ou:org=({"name": "vertex", "$props": {"type": "lulz"}}) ]')
            self.len(1, nodes11)

            nodes12 = await core.nodes('[ ou:org=({"name": "vertex", "type": "hehe"}) ]')
            self.len(1, nodes12)
            self.ne(nodes11[0].ndef, nodes12[0].ndef)

            # GUID ctor has a short-circuit where it tries to find an existing ndef before it does,
            # some property deconfliction, and `<form>=({})` when pushed through guid generation gives
            # back the same guid as `<form>=()`, which if we're not careful could lead to an
            # inconsistent case where you fail to make a node because you don't provide any props,
            # make a node with that matching ndef, and then run that invalid GUID ctor query again,
            # and have it return back a node due to the short circuit. So test that we're consistent here.
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({}) ]')

            self.len(1, await core.nodes('[ ou:org=() ]'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({}) ]')

            msgs = await core.stormlist('[ ou:org=({"$props": {"desc": "lol"}})]')
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInErr('No values provided for form ou:org', msgs)

            msgs = await core.stormlist('[ou:org=({"name": "burrito corp", "$props": {"phone": "lolnope"}})]')
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInErr('Bad value for prop ou:org:phone: requires a digit string', msgs)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({"$try": true}) ]')

            # $try only affects $props
            msgs = await core.stormlist('[ ou:org=({"founded": "lolnope", "$try": true}) ]')
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInErr('Bad value for prop ou:org:founded: Unknown time format for lolnope', msgs)

            msgs = await core.stormlist('[ou:org=({"name": "burrito corp", "$try": true, "$props": {"phone": "lolnope", "desc": "burritos man"}})]')
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            node = nodes[0][1]
            props = node[1]['props']
            self.none(props.get('phone'))
            self.eq(props.get('name'), 'burrito corp')
            self.eq(props.get('desc'), 'burritos man')
            self.stormIsInWarn('Skipping bad value for prop ou:org:phone: requires a digit string', msgs)

            await self.asyncraises(s_exc.BadTypeValu, core.addNode(core.auth.rootuser, 'ou:org', {'name': 'org name 77', 'phone': 'lolnope'}, props={'desc': 'an org desc'}))

            await self.asyncraises(s_exc.BadTypeValu, core.addNode(core.auth.rootuser, 'ou:org', {'name': 'org name 77'}, props={'desc': 'an org desc', 'phone': 'lolnope'}))

            node = await core.addNode(core.auth.rootuser, 'ou:org', {'$try': True, '$props': {'phone': 'invalid'}, 'name': 'org name 77'}, props={'desc': 'an org desc'})
            self.nn(node)
            props = node[1]['props']
            self.none(props.get('phone'))
            self.eq(props.get('name'), 'org name 77')
            self.eq(props.get('desc'), 'an org desc')

            nodes = await core.nodes('ou:org=({"name": "the vertex project", "type": "lulz"})')
            self.len(1, nodes)
            orgn = nodes[0].ndef
            self.eq(orgn, nodes11[0].ndef)

            q = '[ ps:contact=* :org={ ou:org=({"name": "the vertex project", "type": "lulz"}) } ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            cont = nodes[0]
            self.eq(cont.get('org'), orgn[1])

            nodes = await core.nodes('ps:contact:org=({"name": "the vertex project", "type": "lulz"})')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, cont.ndef)

            self.len(0, await core.nodes('ps:contact:org=({"name": "vertex", "type": "newp"})'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('inet:flow:from=({"name": "vertex", "type": "newp"})')

            await core.nodes('[ ou:org=({"name": "origname"}) ]')
            self.len(1, await core.nodes('ou:org=({"name": "origname"}) [ :name=newname ]'))
            self.len(0, await core.nodes('ou:org=({"name": "origname"})'))

            nodes = await core.nodes('[ it:exec:proc=(notime,) ]')
            self.len(1, nodes)

            nodes = await core.nodes('[ it:exec:proc=(nulltime,) ]')
            self.len(1, nodes)

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

            q = '''
            $foo = ({"bar": ${[inet:fqdn=foo.com]}})
            for $n in $foo.bar { return($n.repr()) }
            '''
            retn = await core.callStorm(q)
            self.eq(retn, 'foo.com')

            q = '''
            $foo = ([${[inet:fqdn=foo.com]}])
            for $n in $foo.0 { return($n.repr()) }
            '''
            retn = await core.callStorm(q)
            self.eq(retn, 'foo.com')

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
            self.stormIsInPrint('ip=0.0.0.0 asn=5 .seen=(0, 1) foo=(None, None) true', msgs)
            self.stormIsInPrint('ip=1.1.1.1 asn=6 .seen=(1, 2) foo=(3, 4) false', msgs)

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

            self.eq("foo 'bar'", await core.callStorm("$foo=bar return(`foo '{$foo}'`)"))
            self.eq(r"\'''''bar'''", await core.callStorm(r"$foo=bar return(`\\'\''''{$foo}'''`)"))

    async def test_lib_storm_emit(self):
        async with self.getTestCore() as core:
            self.eq(('foo', 'bar'), await core.callStorm('''
                function generate() {
                    emit foo
                    emit bar
                }
                function makelist() {
                    $retn = ()
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
                    $retn = ()
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

            # Emit outside an emitter function raises a runtime error with posinfo
            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('emit foo')
            self.nn(cm.exception.get('highlight'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('[test:str=emit] emit foo')
            self.nn(cm.exception.get('highlight'))

            # stop cannot cross function boundaries
            q = '''
            function inner(v) {
                if ( $v = 2 ) {
                    stop
                }
                return ( $v )
            }
            function outer(n) {
                for $i in $lib.range($n) {
                    emit $inner($i)
                }
            }
            $N = (5)
            for $valu in $outer($N) {
                $lib.print(`{$valu}/{$N}`)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('1/5', msgs)
            self.stormNotInPrint('2/5', msgs)
            self.stormIsInErr('function inner - Generator control statement "stop" used outside of a generator '
                              'function.',
                              msgs)

            # The function exception raised can be caught.
            q = '''
            function inner(v) {
                if ( $v = 2 ) {
                    stop
                }
                return ( $v )
            }
            function outer(n) {
                for $i in $lib.range($n) {
                    emit $inner($i)
                }
            }
            $N = (5)
            try {
                for $valu in $outer($N) {
                    $lib.print(`{$valu}/{$N}`)
                }
            } catch StormRuntimeError as err {
                $lib.print(`caught: {$err.mesg}`)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('1/5', msgs)
            self.stormNotInPrint('2/5', msgs)
            self.stormIsInPrint('caught: function inner - Generator control statement "stop" used outside of a'
                                ' generator function.',
                                msgs)

            # Outside a function, StopStorm is caught and converted into a StormRuntimeError for the message stream.
            # Since this is tearing down the runtime, it cannot be caught.
            q = '''
            $N = (5)
            for $j in $lib.range($N) {
                if ($j = 2) {
                    stop
                }
                $lib.print(`{$j}/{$N}`)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('1/5', msgs)
            self.stormNotInPrint('2/5', msgs)
            self.stormIsInErr('Generator control statement "stop" used outside of a generator function.',
                              msgs)
            errname = [m[1][0] for m in msgs if m[0] == 'err'][0]
            self.eq(errname, 'StormRuntimeError')

            q = '''
            $N = (5)
            try {
                for $j in $lib.range($N) {
                    if ($j = 2) {
                        stop
                    }
                    $lib.print(`{$j}/{$N}`)
                }
            } catch StormRuntimeError as err {
                $lib.print(`caught: {$err.mesg}`)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('1/5', msgs)
            self.stormNotInPrint('2/5', msgs)
            self.stormNotInPrint('caught:', msgs)
            self.stormIsInErr('Generator control statement "stop" used outside of a generator function.',
                              msgs)

            # Mixing a Loop control flow statement in an emitter to stop its processing
            # will be converted into a catchable StormRuntimeError
            q = '''
            function inner(n) {
                emit $n
                $n = ( $n + 1 )
                emit $n
                $n = ( $n + 1 )
                if ( $n >= 2 ) {
                    break
                }
                emit $n
            }
            $N = (0)
            try {
                for $valu in $inner($N) {
                    $lib.print(`got {$valu}`)
                }
            } catch StormRuntimeError as err {
                $lib.print(`caught: {$err.mesg}`)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('got 1', msgs)
            self.stormNotInPrint('got 2', msgs)
            self.stormIsInPrint('caught: function inner - Loop control statement "break" used outside of a loop.',
                                msgs)

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

            # The items in the catch list must be a str or list of iterables.
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

            # Non-runtsafe Storm works without inbound nodes
            msgs = await core.stormlist('''
            try {
                [ inet:ipv4=0 ]
                $lib.raise(foo, $node.repr())
            } catch * as err {
                $lib.print($err.mesg)
            }
            ''')
            self.stormIsInPrint('0.0.0.0', msgs)

            # info must be json safe
            with self.raises(s_exc.MustBeJsonSafe):
                await core.callStorm('$x="foo" $x=$x.encode() $lib.raise(foo, test, bar=$x)')

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

                $alerts = ()
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

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.print(newp)', opts={'vars': {123: 'newp'}})

            # test that runtsafe vars stay runtsafe
            msgs = await core.stormlist('$foo=bar $lib.print($foo) if $node { $foo=$node.value() }')
            self.stormIsInPrint('bar', msgs)

            # test storm background command
            await core.nodes('''
                $x = foo
                $lib.queue.add($x)
                function stuff() {
                    [inet:ipv4=1.2.3.4]
                    background {
                        [it:dev:str=haha]
                        fini{
                            $lib.queue.get($x).put(hehe)
                        }
                    }
                }
                yield $stuff()
            ''')
            self.eq((0, 'hehe'), await core.callStorm('return($lib.queue.get(foo).get())'))

            await core.nodes('''$lib.queue.gen(bar)
            background ${ $lib.queue.get(bar).put(haha) }
            ''')
            self.eq((0, 'haha'), await core.callStorm('return($lib.queue.get(bar).get())'))

            await core.nodes('$foo = (foo,) background ${ $foo.append(bar) $lib.queue.get(bar).put($foo) }')
            self.eq((1, ['foo', 'bar']), await core.callStorm('return($lib.queue.get(bar).get(1))'))

            await core.nodes('$foo = ([["foo"]]) background ${ $foo.0.append(bar) $lib.queue.get(bar).put($foo) }')
            self.eq((2, [['foo', 'bar']]), await core.callStorm('return($lib.queue.get(bar).get(2))'))

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ ou:org=*] $text = $node.repr() | background $text')

            with self.raises(s_exc.NoSuchVar):
                await core.nodes('background { $lib.print($foo) }')

            await core.nodes('background ${ $foo=test $lib.print($foo) }')

            await core.nodes('background { $lib.time.sleep(4) }')
            task = await core.callStorm('for $t in $lib.ps.list() { if $t.info.background { return($t) } }')
            self.nn(task)
            self.none(task['info'].get('opts'))
            self.eq(core.view.iden, task['info'].get('view'))

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
            core.loadStormPkg(emptypkg)
            await core.addStormPkg(strverpkg)

            core.loadStormPkg(pkg0)

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
                $props = ({"email": "visi@vertex.link"})
                $lib.feed.ingest(syn.nodes, (
                    ( (ps:contact, $iden), ({"props": $props})),
                ))
                ps:contact=$iden
                return(:email)
            ''')
            self.eq(email, 'visi@vertex.link')

            email = await core.callStorm('''
                $iden = $lib.guid()
                $props = ({"email": "visi@vertex.link"})
                yield $lib.feed.genr(syn.nodes, (
                    ( (ps:contact, $iden), ({"props": $props})),
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
            self.stormIsInPrint('haha', msgs)
            self.stormIsInPrint('hehe', msgs)

            self.true(await core.callStorm('return($lib.pkg.has(haha))'))

            await core.delStormPkg('haha')
            self.none(await core.callStorm('return($lib.pkg.get(haha))'))
            self.false(await core.callStorm('return($lib.pkg.has(haha))'))

            msgs = await core.stormlist('pkg.list --verbose')
            self.stormIsInPrint('not available', msgs)

            pkg2 = {'name': 'hoho', 'version': '4.5.6', 'build': {'time': 1732017600000}}
            await core.addStormPkg(pkg2)
            self.eq('4.5.6', await core.callStorm('return($lib.pkg.get(hoho).version)'))
            msgs = await core.stormlist('pkg.list --verbose')
            self.stormIsInPrint('2024-11-19 12:00:00', msgs)

            # test for $lib.queue.gen()
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))
            # and again to test *not* creating it...
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))

            self.eq({'foo': 'bar'}, await core.callStorm('return(({    "foo"    :    "bar"   }))'))

            ddef0 = await core.callStorm('return($lib.dmon.add(${ $lib.queue.gen(hehedmon).put(lolz) $lib.time.sleep(10) }, name=hehedmon))')
            ddef1 = await core.callStorm('return($lib.dmon.get($iden))', opts={'vars': {'iden': ddef0.get('iden')}})
            self.none(await core.callStorm('return($lib.dmon.get(newp))'))

            tasks = [t for t in core.boss.tasks.values() if t.name == 'storm:dmon']
            self.true(len(tasks) == 1 and tasks[0].info.get('view') == core.view.iden)

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
                $list = ()
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
                $list = ()
                $layr = $lib.view.get().layers.0
                for $item in $layr.getStorNodes() {
                    $list.append($item)
                }
                return($list)''', opts=opts)
            self.len(2, sodes)

            ipv4 = await core.callStorm('''
                $list = ()
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

            nodes = await core.nodes('inet:ipv4=11.22.33.44 [ +#bar:score=200 ]', opts=opts)
            bylayer = nodes[0].getByLayer()
            self.eq(bylayer['tagprops']['bar']['score'], layr)

            nodes = await core.nodes('inet:ipv4=11.22.33.44 [ -#bar:score ]', opts=opts)
            bylayer = nodes[0].getByLayer()
            self.none(bylayer['tagprops'].get('bar'))

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

            # test printing a merge that the node was created in the top layer. We also need to make sure the layer
            # is in a steady state for layer merge --diff tests.

            real_layer = core.layers.get(layr)  # type: s_layer.Layer
            if real_layer.dirty:
                waiter = real_layer.layrslab.waiter(1, 'commit')
                await waiter.wait(timeout=12)

            waiter = real_layer.layrslab.waiter(1, 'commit')
            msgs = await core.stormlist('[ inet:fqdn=mvmnasde.com ] | merge', opts=opts)

            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn = mvmnasde.com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:host = mvmnasde', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:domain = com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:issuffix = false', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:iszone = true', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:zone = mvmnasde.com', msgs)

            # Ensure that the layer has sync()'d to avoid getting data from
            # dirty sodes in the merge --diff tests.
            self.len(1, await waiter.wait(timeout=12))

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

            # make a few more edits and merge some of them to test --wipe
            await core.stormlist('[ inet:fqdn=hehehaha.com inet:fqdn=woottoow.com ]')

            layrcount = len(core.layers.values())
            await core.stormlist('[ inet:fqdn=hehehaha.com inet:fqdn=woottoow.com ]', opts=opts)
            oldlayr = await core.callStorm('return($lib.view.get().layers.0.iden)', opts=opts)
            msgs = await core.stormlist('inet:fqdn=hehehaha.com | merge --apply --wipe', opts=opts)
            self.stormHasNoWarnErr(msgs)
            newlayr = await core.callStorm('return($lib.view.get().layers.0.iden)', opts=opts)
            self.ne(oldlayr, newlayr)
            msgs = await core.stormlist('''
                $layr = $lib.view.get().layers.0.iden
                $user = $lib.auth.users.byname(visi)
                $role = $lib.auth.roles.add(ninjas)

                $user.grant($role.iden)

                $user.setAdmin((true), gateiden=$layr)
                $user.addRule(([true, ["foo", "bar"]]), gateiden=$layr)
                $role.addRule(([true, ["baz", "faz"]]), gateiden=$layr)
            ''', opts=opts)
            self.stormHasNoWarnErr(msgs)
            await core.callStorm('$lib.view.get().swapLayer()', opts=opts)
            self.ne(newlayr, await core.callStorm('return($lib.view.get().layers.0.iden)', opts=opts))

            self.true(await core.callStorm('''
                $layr = $lib.view.get().layers.0.iden
                return($lib.auth.users.byname(visi).allowed(foo.bar, gateiden=$layr))
            ''', opts=opts))
            self.true(await core.callStorm('''
                $layr = $lib.view.get().layers.0.iden
                return($lib.auth.users.byname(visi).allowed(baz.faz, gateiden=$layr))
            ''', opts=opts))

            self.len(0, await core.nodes('diff', opts=opts))

            self.len(0, await core.callStorm('''
                $list = ()
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

            with self.getAsyncLoggerStream('synapse.cortex', 'bazfaz requirement') as stream:
                await core.addStormPkg(pkgdef)
                self.true(await stream.wait(timeout=1))

            pkgdef = {
                'name': 'bazfaz',
                'version': '2.2.2',
                'depends': {
                    'requires': (
                        {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'optional': True},
                    ),
                }
            }

            with self.getAsyncLoggerStream('synapse.cortex', 'bazfaz optional requirement') as stream:
                await core.addStormPkg(pkgdef)
                self.true(await stream.wait(timeout=1))

            deps = await core.callStorm('return($lib.pkg.deps($pkgdef))', opts={'vars': {'pkgdef': pkgdef}})
            self.eq({
                'requires': (
                    {'name': 'foobar', 'version': '>=2.0.0,<3.0.0', 'desc': None,
                     'ok': False, 'actual': '1.2.3', 'optional': True},
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

            self.eq({'foo': 'bar', 'baz': 'faz'}, await core.callStorm('''
                return(({ // do foo thing
                    "foo" /* hehe */ : /* haha */ "bar", //lol
                    "baz" // hehe
                    : // haha
                    "faz" // hehe
                }))
            '''))

            self.eq(('foo', 'bar', 'baz'), await core.callStorm('''
                return(([ // do foo thing
                    /* hehe */ "foo" /* hehe */ , /* hehe */ "bar" /* hehe */ , /* hehe */ "baz" /* hehe */
                ]))
            '''))

            # surrogate escapes are allowed
            nodes = await core.nodes(" [ test:str='pluto\udcbaneptune' ]")
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'pluto\udcbaneptune'))

            nodes = await core.nodes('[ media:news=* :publisher:name=woot ] $name=:publisher:name [ :publisher={ gen.ou.org $name } ]')
            self.len(1, nodes)
            self.nn(nodes[0].get('publisher'))

            # test regular expressions are case insensitive by default
            self.len(1, await core.nodes('test:str~=Pluto'))
            self.len(1, await core.nodes('test:str +test:str~=Pluto'))
            self.true(await core.callStorm('return(("Foo" ~= "foo"))'))
            self.len(0, await core.nodes('test:str~="(?-i:Pluto)"'))
            self.len(0, await core.nodes('test:str +test:str~="(?-i:Pluto)"'))
            self.false(await core.callStorm('return(("Foo" ~= "(?-i:foo)"))'))
            self.true(await core.callStorm('return(("Foo" ~= "(?-i:Foo)"))'))

            async with await core.view.snap(user=visi) as snap:
                query = await core.getStormQuery('')
                async with snap.getStormRuntime(query) as runt:
                    with self.raises(s_exc.AuthDeny):
                        runt.reqAdmin(gateiden=layr)

            await core.stormlist('[ inet:fqdn=vertex.link ]')
            fork = await core.callStorm('return($lib.view.get().fork().iden)')

            opts = {'view': fork, 'show:storage': True}
            msgs = await core.stormlist('inet:fqdn=vertex.link [ +#foo ]', opts=opts)
            nodes = [mesg[1] for mesg in msgs if mesg[0] == 'node']
            self.len(1, nodes)
            self.nn(nodes[0][1]['storage'][1]['props']['.created'])
            self.eq((None, None), nodes[0][1]['storage'][0]['tags']['foo'])

    async def test_storm_diff_merge(self):

        async with self.getTestCore() as core:
            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')

            altview = {'view': viewiden}
            await core.nodes('[ ou:org=* :name=hehe +#hehe ]')
            await core.nodes('[ ou:org=* :name=haha +#haha ]', opts=altview)

            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('diff')

            altro = {'view': viewiden, 'readonly': True}
            nodes = await core.nodes('diff --prop ".created" | +ou:org', opts=altro)
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

            await core.nodes('[ ps:contact=* :name=con0 +#con0 +#con0.foo +#conalt ]', opts=altview)
            await core.nodes('[ ps:contact=* :name=con1 +#con1 +#conalt ]', opts=altview)

            nodes = await core.nodes('diff --tag conalt con1 con0.foo con0 newp', opts=altview)
            self.sorteq(['con0', 'con1'], [n.get('name') for n in nodes])

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

            await visi.delRule((True, ('node', 'add')), gateiden=lowriden)

            self.len(1, await core.nodes('ou:name=foo [ .seen=now ]', opts=altview))
            await core.nodes('ou:name=foo | merge --apply', opts=altview)

            await visi.addRule((True, ('node', 'add')), gateiden=lowriden)

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

            oldn = await core.nodes('[ ou:name=readonly ]', opts=altview)
            newn = await core.nodes('[ ou:name=readonly ]')
            self.ne(oldn[0].props['.created'], newn[0].props['.created'])

            with self.getAsyncLoggerStream('synapse.lib.snap') as stream:
                await core.stormlist('ou:name | merge --apply', opts=altview)

            stream.seek(0)
            buf = stream.read()
            self.notin("Property is read only: ou:name.created", buf)

            newn = await core.nodes('ou:name=readonly')
            self.eq(oldn[0].props['.created'], newn[0].props['.created'])

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)', opts={'view': viewiden})

            oldn = await core.nodes('[ ou:name=readonly2 ]', opts=altview)
            newn = await core.nodes('[ ou:name=readonly2 ]')
            self.ne(oldn[0].props['.created'], newn[0].props['.created'])

            altview2 = {'view': viewiden2}
            q = 'ou:name=readonly2 | movenodes --apply --srclayers $lib.view.get().layers.2.iden'
            await core.nodes(q, opts=altview2)

            with self.getAsyncLoggerStream('synapse.lib.snap') as stream:
                await core.stormlist('ou:name | merge --apply', opts=altview2)

            stream.seek(0)
            buf = stream.read()
            self.notin("Property is read only: ou:name.created", buf)

            newn = await core.nodes('ou:name=readonly2', opts=altview)
            self.eq(oldn[0].props['.created'], newn[0].props['.created'])

            await core.nodes('[ test:ro=bad :readable=foo ]', opts=altview)
            await core.nodes('[ test:ro=bad :readable=bar ]')

            msgs = await core.stormlist('test:ro | merge', opts=altview)
            self.stormIsInWarn("Cannot merge read only property with conflicting value", msgs)

            await core.nodes('[ test:str=foo +(refs)> { for $i in $lib.range(1001) {[ test:int=$i ]}}]', opts=altview)
            await core.nodes('test:str=foo -(refs)+> * merge --apply', opts=altview)
            self.len(1001, await core.nodes('test:str=foo -(refs)> *'))

    async def test_storm_merge_stricterr(self):

        conf = {'modules': [('synapse.tests.utils.DeprModule', {})]}
        async with self.getTestCore(conf=copy.deepcopy(conf)) as core:

            await core.nodes('$lib.model.ext.addFormProp(test:deprprop, _str, (str, ({})), ({}))')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            asfork = {'view': viewiden}

            await core.nodes('[ test:deprprop=base ]')

            self.len(1, await core.nodes('test:deprprop=base [ :_str=foo +#test ]', opts=asfork))
            await core.nodes('[ test:deprprop=fork test:str=other ]', opts=asfork)

            await core.nodes('model.deprecated.lock test:deprprop')

            msgs = await core.stormlist('diff | merge --apply --no-tags', opts=asfork)
            self.stormIsInWarn('Form test:deprprop is locked due to deprecation for valu=base', msgs)
            self.stormIsInWarn('Form test:deprprop is locked due to deprecation for valu=fork', msgs)
            self.stormHasNoErr(msgs)

            msgs = await core.stormlist('diff | merge --apply --only-tags', opts=asfork)
            self.stormIsInWarn('Form test:deprprop is locked due to deprecation for valu=base', msgs)
            self.stormHasNoErr(msgs)

            self.eq({
                'meta:source': 1,
                'syn:tag': 1,
                'test:deprprop': 1,
                'test:str': 1,
            }, await core.callStorm('return($lib.view.get().getFormCounts())'))

            nodes = await core.nodes('test:deprprop')
            self.eq(['base'], [n.ndef[1] for n in nodes])
            self.eq([], nodes[0].getTags())

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

    async def test_storm_merge_perms(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})

            visi = await core.auth.addUser('visi')
            opts = {'user': visi.iden}

            view2 = await core.callStorm('return($lib.view.get().fork())')
            view2opts = opts | {'view': view2['iden']}
            layr2 = view2['layers'][0]['iden']
            layr1 = view2['layers'][1]['iden']

            await visi.addRule((True, ('view',)))
            await visi.addRule((True, ('node', 'add')), gateiden=layr2)
            await visi.addRule((True, ('node', 'prop', 'set')), gateiden=layr2)
            await visi.addRule((True, ('node', 'tag', 'add')), gateiden=layr2)
            await visi.addRule((True, ('node', 'data', 'set')), gateiden=layr2)
            await visi.addRule((True, ('node', 'edge', 'add')), gateiden=layr2)

            await core.nodes('[ ou:name=test ]')

            await core.nodes('''
                [ ps:contact=*
                    :name=test0
                    +(test)> { ou:name=test }
                    +#test1.foo=now
                    +#test2
                    +#test3:score=42
                ]
                $node.data.set(foo, bar)
            ''', opts=view2opts)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.del.ps:contact', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'del')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.add.ps:contact', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'add')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.prop.del.ps:contact..created', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'prop', 'del')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.prop.set.ps:contact..created', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'prop', 'set')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.del.test1.foo', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'del', 'test1', 'foo')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.add.test1.foo', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'add', 'test1', 'foo')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.del.test3', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'del', 'test3')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.add.test3', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'add', 'test3')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.del.test2', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'del', 'test2')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.tag.add.test2', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'tag', 'add', 'test2')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.data.pop.foo', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'data', 'pop')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.data.set.foo', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'data', 'set')), gateiden=layr1)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.edge.del.test', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'edge', 'del')), gateiden=layr2)

            with self.raises(s_exc.AuthDeny) as ecm:
                await core.nodes('ps:contact merge --apply', opts=view2opts)
            self.eq('node.edge.add.test', ecm.exception.errinfo['perm'])
            await visi.addRule((True, ('node', 'edge', 'add')), gateiden=layr1)

            await core.nodes('ps:contact merge --apply', opts=view2opts)

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

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('view', 'add')))

            view2iden = await core.callStorm('return($lib.view.get().fork().iden)', opts={'user': visi.iden})
            view2 = {'view': view2iden, 'user': visi.iden}

            view3iden = await core.callStorm('return($lib.view.get().fork().iden)', opts=view2)
            view3 = {'view': view3iden, 'user': visi.iden}

            self.len(1, await core.nodes('[ou:org=(perms,) :desc=foo]', opts=view2))
            await core.nodes('ou:org=(perms,) | movenodes --apply', opts=view3)

    async def test_cortex_keepalive(self):
        async with self.getTestCore() as core:
            opts = {'keepalive': 1}
            q = '[test:str=one] $lib.time.sleep(2.5)'
            msgs = await core.stormlist(q, opts=opts)
            pings = [m for m in msgs if m[0] == 'ping']
            self.len(2, pings)

            opts = {'keepalive': 0}
            with self.raises(s_exc.BadArg) as cm:
                msgs = await core.stormlist(q, opts=opts)
            self.eq('keepalive must be > 0; got 0', cm.exception.get('mesg'))

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
            msgs = await core.stormlist('[ ou:org=* :country=* :hq=* ] { -> ps:contact [ :email=visi@vertex.link ] }', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            node = nodes[0]

            self.eq('visi', node[1]['embeds']['hq::email']['user'])
            self.eq('2346d7bed4b0fae05e00a413bbf8716c9e08857eb71a1ecf303b8972823f2899', node[1]['embeds']['hq::email']['*'])

            fork = await core.callStorm('return($lib.view.get().fork().iden)')

            opts['vars'] = {
                'md5': '12345a5758eea935f817dd1490a322a5',
                'sha1': '40b8e76cff472e593bd0ba148c09fec66ae72362'
            }
            opts['view'] = fork
            opts['show:storage'] = True
            opts['embeds']['ou:org']['lol::nope'] = ('notreal',)
            opts['embeds']['ou:org']['country::flag'] = ('md5', 'sha1')
            opts['embeds']['ou:org']['country::tld'] = ('domain',)

            await core.stormlist('pol:country [ :flag={[ file:bytes=* :md5=fa818a259cbed7ce8bc2a22d35a464fc ]} ]')

            msgs = await core.stormlist('''
                ou:org {
                    -> pol:country
                    [ :tld=co.uk ]
                    {
                        :flag -> file:bytes [ :md5=$md5 :sha1=$sha1 ]
                    }
                }
            ''', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            node = nodes[0]

            storage = node[1]['storage']
            self.len(2, storage)
            top = storage[0].get('embeds')
            bot = storage[1].get('embeds')
            self.nn(top)
            self.nn(bot)

            self.nn(top.get('country::flag::md5'))
            self.eq(top['country::flag::md5'][0], '12345a5758eea935f817dd1490a322a5')

            self.nn(top.get('country::flag::sha1'))
            self.eq(top['country::flag::sha1'][0], '40b8e76cff472e593bd0ba148c09fec66ae72362')

            self.nn(top.get('country::tld::domain'))
            self.eq(top['country::tld::domain'][0], 'uk')

            self.nn(bot.get('hq::email::user'))
            self.eq(bot['hq::email::user'][0], 'visi')

            self.nn(bot.get('country::flag::md5'))
            self.eq(bot['country::flag::md5'][0], 'fa818a259cbed7ce8bc2a22d35a464fc')

            empty = await core.callStorm('return($lib.view.get().fork().iden)', opts=opts)
            opts['view'] = empty

            msgs = await core.stormlist('ou:org', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            node = nodes[0]
            storage = node[1]['storage']
            self.len(3, storage)
            top = storage[0].get('embeds')
            mid = storage[1].get('embeds')
            bot = storage[2].get('embeds')
            self.none(top)

            self.nn(mid)
            self.nn(bot)

            self.nn(mid.get('country::flag::md5'))
            self.eq(mid['country::flag::md5'][0], '12345a5758eea935f817dd1490a322a5')

            self.nn(mid.get('country::flag::sha1'))
            self.eq(mid['country::flag::sha1'][0], '40b8e76cff472e593bd0ba148c09fec66ae72362')

            self.nn(mid.get('country::tld::domain'))
            self.eq(mid['country::tld::domain'][0], 'uk')

            self.nn(bot.get('hq::email::user'))
            self.eq(bot['hq::email::user'][0], 'visi')

            self.nn(bot.get('country::flag::md5'))
            self.eq(bot['country::flag::md5'][0], 'fa818a259cbed7ce8bc2a22d35a464fc')

            await core.nodes('''
                [( risk:vulnerable=*
                    :mitigated=true
                    :node={ [ it:prod:hardware=* :name=foohw ] return($node.ndef()) }
                    :vuln={[ risk:vuln=* :name=barvuln ]}
                    +#test
                )]
                [( inet:service:rule=*
                    :object={ risk:vulnerable#test return($node.ndef()) }
                    :grantee={ [ inet:service:account=* :id=foocon ] return($node.ndef()) }
                    +#test
                )]
            ''')

            opts = {
                'embeds': {
                    'risk:vulnerable': {
                        'vuln': ['name'],
                        'node': ['name'],
                    },
                    'inet:service:rule': {
                        'object': ['mitigated', 'newp'],
                        'object::node': ['name', 'newp'],
                        'grantee': ['id', 'newp'],
                    }
                }
            }
            msgs = await core.stormlist('inet:service:rule#test :object -+> risk:vulnerable', opts=opts)
            nodes = sorted([m[1] for m in msgs if m[0] == 'node'], key=lambda p: p[0][0])
            self.eq(['inet:service:rule', 'risk:vulnerable'], [n[0][0] for n in nodes])

            embeds = nodes[0][1]['embeds']
            self.eq(1, embeds['object']['mitigated'])
            self.eq(None, embeds['object']['newp'])
            self.eq('foohw', embeds['object::node']['name'])
            self.eq(None, embeds['object::node']['newp'])
            self.eq('foocon', embeds['grantee']['id'])
            self.eq(None, embeds['grantee']['newp'])

            embeds = nodes[1][1]['embeds']
            self.eq('barvuln', embeds['vuln']['name'])
            self.eq('foohw', embeds['node']['name'])

    async def test_storm_wget(self):

        async def _getRespFromSha(core, mesgs):
            for m in mesgs:
                if m[0] == 'node' and m[1][0][0] == 'file:bytes':
                    node = m[1]
                    sha = node[1]['props']['sha256']

            buf = b''
            async for bytz in core.axon.get(s_common.uhex(sha)):
                buf += bytz

            resp = s_json.loads(buf)
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
            $params=({"key": "valu", "foo": "bar"})
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

            # URL fragments are preserved.
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test#fragmented-bits'
            q = '[inet:url=$url] | wget --no-ssl-verify | -> *'
            msgs = await core.stormlist(q, opts={'vars': {'url': url}})
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.isin(('inet:url', url), [pode[0] for pode in podes])

            # URL encoded data plays nicely
            params = (('foo', 'bar'), ('baz', 'faz'))
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test?{u_parse.urlencode(params)}'
            q = '[inet:url=$url] | wget --no-ssl-verify | -> *'
            msgs = await core.stormlist(q, opts={'vars': {'url': url}})
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.isin(('inet:url', url), [pode[0] for pode in podes])

            # Redirects still record the original address
            durl = f'https://127.0.0.1:{port}/api/v1/active'
            params = (('redirect', durl),)
            url = f'https://127.0.0.1:{port}/api/v0/test?{u_parse.urlencode(params)}'
            # Redirect again...
            url = f'https://127.0.0.1:{port}/api/v0/test?{u_parse.urlencode((("redirect", url),))}'

            q = '[inet:url=$url] | wget --no-ssl-verify | -> *'
            msgs = await core.stormlist(q, opts={'vars': {'url': url}})
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.isin(('inet:url', url), [pode[0] for pode in podes])

            # $lib.axon.urlfile makes redirect nodes for the chain, starting from
            # the original request URL to the final URL
            q = 'inet:url=$url -> inet:urlredir | tree { :dst -> inet:urlredir:src }'
            nodes = await core.nodes(q, opts={'vars': {'url': url}})
            self.len(2, nodes)

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

    async def test_storm_dmon_caching(self):

        async with self.getTestCore() as core:

            q = f'''
            $lib.dmon.add(${{
                for $x in $lib.range(2) {{
                    inet:ipv4=1.2.3.4
                    if $node {{
                        $lib.queue.gen(foo).put($node.props.asn)
                        $lib.queue.gen(bar).get(1)
                    }}
                    [ inet:ipv4=1.2.3.4 :asn=5 ]
                    $lib.queue.gen(foo).put($node.props.asn)
                    $lib.queue.gen(bar).get(0)
                }}
                | spin
            }}, name=foo)'''
            await core.nodes(q)

            self.eq((0, 5), await core.callStorm('return($lib.queue.gen(foo).get(0))'))

            await core.nodes('inet:ipv4=1.2.3.4 [ :asn=6 ] $lib.queue.gen(bar).put(0)')

            self.eq((1, 6), await core.callStorm('return($lib.queue.gen(foo).get(1))'))

    async def test_storm_dmon_query_state(self):
        with self.getTestDir() as dirn:
            dirn00 = s_common.gendir(dirn, 'core00')
            dirn01 = s_common.gendir(dirn, 'core01')
            dirn02 = s_common.gendir(dirn, 'core02')

            async with self.getTestCore(dirn=dirn00) as core00:

                msgs = await core00.stormlist('[ inet:ipv4=1.2.3.4 ]')
                self.stormHasNoWarnErr(msgs)

            s_tools_backup.backup(dirn00, dirn01)
            s_tools_backup.backup(dirn00, dirn02)

            async with self.getTestCore(dirn=dirn00) as core00:
                conf01 = {'mirror': core00.getLocalUrl()}

                async with self.getTestCore(dirn=dirn01, conf=conf01) as core01:

                    conf02 = {'mirror': core01.getLocalUrl()}

                    async with self.getTestCore(dirn=dirn02, conf=conf02) as core02:

                        await core02.sync()

                        nodes = await core01.nodes('inet:ipv4')
                        self.len(1, nodes)
                        self.eq(nodes[0].ndef, ('inet:ipv4', 16909060))

                        q = '''
                        $lib.queue.gen(dmonloop)
                        return(
                            $lib.dmon.add(${
                                $queue = $lib.queue.get(dmonloop)
                                while $lib.true {
                                    ($offs, $mesg) = $queue.get()

                                    switch $mesg.0 {
                                        "print": { $lib.print($mesg.1) }
                                        "warn": { $lib.warn($mesg.1) }
                                        "leave": {
                                            $lib.print(leaving)
                                            break
                                        }
                                        *: { continue }
                                    }

                                    $queue.cull($offs)
                                }
                            }, name=dmonloop)
                        )
                        '''
                        ddef = await core02.callStorm(q)
                        self.nn(ddef['iden'])

                        dmons = await core02.getStormDmons()
                        self.len(1, dmons)
                        self.eq(dmons[0]['iden'], ddef['iden'])

                        info = await core02.getStormDmon(ddef['iden'])
                        self.eq(info['iden'], ddef['iden'])
                        self.eq(info['name'], 'dmonloop')
                        self.eq(info['status'], 'running')

                        await core02.callStorm('$lib.queue.get(dmonloop).put((print, printfoo))')
                        await core02.callStorm('$lib.queue.get(dmonloop).put((warn, warnfoo))')

                        info = await core02.getStormDmon(ddef['iden'])
                        self.eq(info['status'], 'running')

                        logs = await core02.getStormDmonLog(ddef['iden'])
                        msgs = [k[1] for k in logs]
                        self.stormIsInPrint('printfoo', msgs)
                        self.stormIsInWarn('warnfoo', msgs)

                        await core02.callStorm('$lib.queue.get(dmonloop).put((leave,))')

                        info = await core02.getStormDmon(ddef['iden'])
                        self.eq(info['status'], 'sleeping')

                        logs = await core02.getStormDmonLog(ddef['iden'])
                        msgs = [k[1] for k in logs]
                        self.stormIsInPrint('leaving', msgs)

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
                    $foo = ({})
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
            self.none(await core.callStorm('$foo = ({}) $foo.bar = 10 $foo.bar = $lib.undef return($foo.bar)'))
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
                assert self.request.headers.get('X-Synapse-Version') == s_version.verstring

                if name == 'notok':
                    self.sendRestErr('FooBar', 'baz faz')
                    return

                self.sendRestRetn(pkg)

        class PkgHandlerRaw(s_httpapi.Handler):
            async def get(self, name):
                assert self.request.headers.get('X-Synapse-Version') == s_version.verstring

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

            # onload will on fire once. all other pkg.load events will effectively bounce
            # because the pkg hasn't changed so no loading occurs
            waiter = core.waiter(1, 'core:pkg:onload:complete')

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

            evnts = await waiter.wait(timeout=4)
            exp = [
                ('core:pkg:onload:complete', {'pkg': 'testload'})
            ]
            self.eq(exp, evnts)

    async def test_storm_tree(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=www.vertex.link ] | tree ${ :domain -> inet:fqdn }')
            vals = [n.ndef[1] for n in nodes]
            self.eq(('www.vertex.link', 'vertex.link', 'link'), vals)

            # Max recursion fail
            q = '[ inet:fqdn=www.vertex.link ] | tree { inet:fqdn=www.vertex.link }'
            await self.asyncraises(s_exc.RecursionLimitHit, core.nodes(q))

            # Runtsafety test
            q = '[ inet:fqdn=www.vertex.link ] $q=:domain | tree $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_movetag(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[test:str=foo +#hehe.haha=((20), (30)) ]'))
            self.len(1, await core.nodes('syn:tag=hehe.haha [:doc="haha doc" :title="haha title"]'))

            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag hehe hehe')

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(0, await core.nodes('#hehe.haha'))

            self.len(1, await core.nodes('#woot'))
            self.len(1, await core.nodes('#woot.haha'))

            nodes = await core.nodes('syn:tag=woot.haha')
            self.len(1, nodes)
            newt = nodes[0]
            self.eq(newt.get('doc'), 'haha doc')
            self.eq(newt.get('title'), 'haha title')

            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            node = nodes[0]
            self.eq((20, 30), node.tags.get('woot.haha'))
            self.none(node.tags.get('hehe'))
            self.none(node.tags.get('hehe.haha'))

            nodes = await core.nodes('syn:tag=hehe')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('isnow'), 'woot')

            nodes = await core.nodes('syn:tag=hehe.haha')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('isnow'), 'woot.haha')

            # test isnow plumbing
            nodes = await core.nodes('[test:str=bar +#hehe.haha]')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.tags.get('woot'))
            self.nn(node.tags.get('woot.haha'))
            self.none(node.tags.get('hehe'))
            self.none(node.tags.get('hehe.haha'))

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[test:str=foo +#hehe=((20), (30)) ]'))
            self.len(1, await core.nodes('syn:tag=hehe [:doc="haha doc" :doc:url="http://haha.doc.com"]'))

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(1, await core.nodes('#woot'))

            nodes = await core.nodes('syn:tag=woot')
            self.len(1, nodes)
            newt = nodes[0]
            self.eq(newt.get('doc'), 'haha doc')
            self.eq(newt.get('doc:url'), 'http://haha.doc.com')

        # Test moving a tag which has tags on it.
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=V +#a.b.c]'))
            self.len(1, await core.nodes('syn:tag=a.b [+#foo]'))

            await core.nodes('movetag a.b a.m')
            self.len(2, await core.nodes('#foo'))
            self.len(1, await core.nodes('syn:tag=a.b +#foo'))
            self.len(1, await core.nodes('syn:tag=a.m +#foo'))

        # Test moving a tag to another tag which is a string prefix of the source
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=V +#aaa.b.ccc +#aaa.b.ddd]'))
            self.len(1, await core.nodes('[test:str=Q +#aaa.barbarella.ccc]'))

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
            self.len(1, await core.nodes('[test:str=neato +#basic.one +#basic.two +#unicycle +#tricyle +#bicycle]'))

            # basic 2-cycle test
            await core.nodes('movetag basic.one basic.two')
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag basic.two basic.one')

            # 3-cycle test
            await core.nodes('movetag bicycle tricycle')
            await core.nodes('movetag unicycle bicycle')
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag tricycle unicycle')

            self.len(1, await core.nodes('[test:str=badcycle +#unicycle]'))

            # 4 cycle test
            self.len(1, await core.nodes('[test:str=burrito +#there.picard +#are.is +#four.best +#tags.captain]'))

            # A -> B -> C -> D -> A
            await core.nodes('movetag there are')   # A -> B
            await core.nodes('movetag four tags')   # C -> D
            await core.nodes('movetag tags there')  # D -> A
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag are four')    # B -> C (creates the cycle)

            # make a pre-existing cycle to ensure we can break break that with move tag
            self.len(1, await core.nodes('[syn:tag=existing :isnow=cycle]'))
            self.len(1, await core.nodes('[syn:tag=cycle :isnow=existing]'))

            await core.nodes('movetag cycle breaker')

            nodes = await core.nodes('syn:tag=existing')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('isnow'), 'cycle')

            nodes = await core.nodes('syn:tag=cycle')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('isnow'), 'breaker')

            nodes = await core.nodes('syn:tag=breaker')
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('isnow'))

            # make a pre-existing cycle to ensure we can catch that if an chain is encountered
            # B -> C -> D -> E -> C
            # Then movetag to make A -> B

            self.len(1, await core.nodes('[syn:tag=this]'))
            self.len(1, await core.nodes('[syn:tag=is :isnow=not]'))
            self.len(1, await core.nodes('[syn:tag=not :isnow=a]'))
            self.len(1, await core.nodes('[syn:tag=a :isnow=test]'))
            self.len(1, await core.nodes('[syn:tag=test :isnow=not]'))

            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag this is')

        async with self.getTestCore() as core:
            await core.nodes('[ syn:tag=hehe :isnow=haha ]')
            nodes = await core.nodes('[ ou:org=* +#hehe.qwer ]')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('haha.qwer'))
            self.none(nodes[0].getTag('hehe.qwer'))
            self.len(1, await core.nodes('syn:tag=haha.qwer'))

            # this should hit the already existing redirected tag now...
            nodes = await core.nodes('[ ou:org=* +#hehe.qwer ]')
            self.len(1, nodes)

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
            nodes = await core.nodes('test:comp | uniq :hehe')
            self.len(1, nodes)
            nodes = await core.nodes('test:comp $valu=:hehe | uniq $valu')
            self.len(1, nodes)
            nodes = await core.nodes('test:comp $valu=({"foo": :hehe}) | uniq $valu')
            self.len(1, nodes)
            q = '''
                [(tel:mob:telem=(n1,) :data=(({'hehe': 'haha', 'foo': 'bar'}),))
                 (tel:mob:telem=(n2,) :data=(({'hehe': 'haha', 'foo': 'baz'}),))
                 (tel:mob:telem=(n3,) :data=(({'foo': 'bar', 'hehe': 'haha'}),))]
                uniq :data
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)

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
            self.len(0, await core.nodes('test:str=foo | once tagger --asof -30days | [+#another.tag]'))
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            self.notin('less.cool.tag', nodes[0].tags)

            # but if it's super recent, we can override it
            nodes = await core.nodes('test:str | once tagger --asof now | [ +#tag.the.third ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('tag.the.third', node.tags)

            # keys shouldn't interact
            nodes = await core.nodes('test:str | once ninja | [ +#lottastrings ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('lottastrings', node.tags)

            nodes = await core.nodes('test:str | once beep --asof -30days | [ +#boop ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('boop', node.tags)

            # we update to the more recent timestamp, so providing now should update things
            nodes = await core.nodes('test:str | once beep --asof now | [ +#bbq ]')
            self.len(6, nodes)
            for node in nodes:
                self.isin('bbq', node.tags)

            # but still, no time means if it's ever been done
            self.len(0, await core.nodes('test:str | once beep | [ +#metal]'))
            self.len(0, await core.nodes('test:str $node.data.set(once:beep, ({})) | once beep'))

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

            nodes = await core.nodes('[test:guid=* :tick=2015 .seen=2015]')
            self.len(1, nodes)
            minc = nodes[0].get('.created')
            await asyncio.sleep(0.01)
            self.len(1, await core.nodes('[test:guid=* :tick=2016 .seen=2016]'))
            await asyncio.sleep(0.01)
            self.len(1, await core.nodes('[test:guid=* :tick=2017 .seen=2017]'))
            await asyncio.sleep(0.01)
            self.len(1, await core.nodes('[test:str=1 :tick=2016]'))

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

            q = '$foo="http://fxp.com 1.2.3.4" | scrape $foo --yield --forms (inet:fqdn, inet:ipv4)'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:fqdn', 'fxp.com'))

            q = '$foo="http://fxp.com 1.2.3.4" | scrape $foo --yield --forms inet:fqdn,inet:ipv4'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:fqdn', 'fxp.com'))

            q = '''
            $foo="http://fxp.com 1.2.3.4" $forms=(inet:fqdn, inet:ipv4)
            | scrape $foo --yield --forms $forms'''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:fqdn', 'fxp.com'))

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

            nodes = await core.nodes('inet:search:query | scrape :text --yield --forms inet:ipv4')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            nodes = await core.nodes('inet:search:query | scrape :text --yield --forms inet:ipv4,inet:fqdn')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            nodes = await core.nodes('inet:search:query | scrape :text --yield --forms inet:fqdn')
            self.len(0, nodes)

            nodes = await core.nodes('inet:search:query | scrape :text --yield --forms (1)')
            self.len(0, nodes)

            nodes = await core.nodes('$foo="1.2.3.4" | scrape $foo --yield --forms (1)')
            self.len(0, nodes)

            msgs = await core.stormlist('scrape "https://t.c\\\\"')
            self.stormHasNoWarnErr(msgs)
            msgs = await core.stormlist('[ media:news=* :title="https://t.c\\\\" ] | scrape :title')
            self.stormHasNoWarnErr(msgs)

            await core.nodes('trigger.add node:add --query {[ +#foo.com ]} --form inet:ipv4')
            msgs = await core.stormlist('syn:trigger | scrape :storm --refs')
            self.stormIsInWarn('Edges cannot be used with runt nodes: syn:trigger', msgs)

    async def test_storm_tee(self):

        async with self.getTestCore() as core:

            guid = s_common.guid()
            self.len(1, await core.nodes('[edge:refs=((media:news, $valu), (inet:ipv4, 1.2.3.4))]',
                                         opts={'vars': {'valu': guid}}))
            self.len(1, await core.nodes('[inet:dns:a=(woot.com, 1.2.3.4)]'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 [ :asn=0 ]'))

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
            msgs = await core.stormlist(q, opts={'links': True})
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(4, nodes)

            self.eq(nodes[0][0], ('inet:asn', 0))
            links = nodes[0][1]['links']
            self.len(1, links)
            self.eq({'type': 'prop', 'prop': 'asn'}, links[0][1])

            self.eq(nodes[1][0][0], ('inet:dns:a'))
            links = nodes[1][1]['links']
            self.len(1, links)
            self.eq({'type': 'prop', 'prop': 'ipv4', 'reverse': True}, links[0][1])

            self.eq(nodes[2][0][0], ('edge:refs'))
            links = nodes[2][1]['links']
            self.len(1, links)
            self.eq({'type': 'prop', 'prop': 'n2', 'reverse': True}, links[0][1])

            self.eq(nodes[3][0], ('inet:ipv4', 0x01020304))
            links = nodes[2][1]['links']
            self.len(1, links)
            self.eq({'type': 'prop', 'prop': 'n2', 'reverse': True}, links[0][1])

            q = 'inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * } { -> edge:refs:n2 :n1 -> * }'
            nodes = await core.nodes(q)
            self.len(5, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('edge:refs'))
            self.eq(nodes[3].ndef[0], ('media:news'))
            self.eq(nodes[4].ndef, ('inet:ipv4', 0x01020304))

            # Queries can be a heavy list
            q = '$list = ([${ -> * }, ${ <- * }, ${ -> edge:refs:n2 :n1 -> * }]) inet:ipv4=1.2.3.4 | tee --join $list'
            nodes = await core.nodes(q)
            self.len(5, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('edge:refs'))
            self.eq(nodes[3].ndef[0], ('media:news'))
            self.eq(nodes[4].ndef, ('inet:ipv4', 0x01020304))

            # A empty list of queries still works as an nop
            q = '$list = () | tee $list'
            msgs = await core.stormlist(q)
            self.len(2, msgs)
            self.eq(('init', 'fini'), [m[0] for m in msgs])

            q = 'inet:ipv4=1.2.3.4 $list = () | tee --join $list'
            msgs = await core.stormlist(q)
            self.len(3, msgs)
            self.eq(('init', 'node', 'fini'), [m[0] for m in msgs])

            q = '$list = () | tee --parallel $list'
            msgs = await core.stormlist(q)
            self.len(2, msgs)
            self.eq(('init', 'fini'), [m[0] for m in msgs])

            q = 'inet:ipv4=1.2.3.4 $list = () | tee --parallel --join $list'
            msgs = await core.stormlist(q)
            self.len(3, msgs)
            self.eq(('init', 'node', 'fini'), [m[0] for m in msgs])

            # Queries can be a input list
            q = 'inet:ipv4=1.2.3.4 | tee --join $list'
            queries = ('-> *', '<- *', '-> edge:refs:n2 :n1 -> *')
            nodes = await core.nodes(q, {'vars': {'list': queries}})
            self.len(5, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('edge:refs'))
            self.eq(nodes[3].ndef[0], ('media:news'))
            self.eq(nodes[4].ndef, ('inet:ipv4', 0x01020304))

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

            q = '$foo=woot.com tee --parallel { $lib.time.sleep("1") inet:ipv4=1.2.3.4 }  { $lib.time.sleep("0.5") inet:fqdn=$foo <- * | sleep 2} { [inet:asn=1234] }'
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
            q = '[ inet:fqdn=www.vertex.link ] $q=:domain | tee $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_parallel(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('parallel --size 4 { [ ou:org=* ] }')
            self.len(4, nodes)

            # check that subquery validation happens
            with self.raises(s_exc.NoSuchVar):
                await core.nodes('parallel --size 4 { [ ou:org=$foo ] }')

            # check that an exception on inbound percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=(foo,) ou:org=foo ] | parallel { [:name=bar] }')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=(foo,) ou:org=foo ] | parallel --size 1 { [:name=bar] }')

            # check that an exception in the parallel pipeline percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('parallel { [ou:org=foo] }')

            nodes = await core.nodes('ou:org | parallel {[ :name=foo ]}')
            self.true(all([n.get('name') == 'foo' for n in nodes]))

            # Runtsafety test
            q = '[ inet:fqdn=www.vertex.link ] $q=:domain | parallel $q'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            nodes = await core.nodes('ou:org | parallel ${ $foo=bar [ :name=$foo ]}')
            self.true(all([n.get('name') == 'bar' for n in nodes]))

            orig = s_storm.ParallelCmd.pipeline
            tsks = {'cnt': 0}

            async def pipecnt(self, runt, query, inq, outq, runtprims):
                tsks['cnt'] += 1
                await orig(self, runt, query, inq, outq, runtprims)

            with mock.patch('synapse.lib.storm.ParallelCmd.pipeline', pipecnt):

                nodes = await core.nodes('ou:org parallel --size 4 {[ :name=bar ]}')
                self.len(5, nodes)
                self.true(all([n.get('name') == 'bar' for n in nodes]))
                self.eq(4, tsks['cnt'])

                tsks['cnt'] = 0

                nodes = await core.nodes('ou:org parallel --size 5 {[ :name=bar ]}')
                self.len(5, nodes)
                self.true(all([n.get('name') == 'bar' for n in nodes]))
                self.eq(5, tsks['cnt'])

                tsks['cnt'] = 0

                # --size greater than number of nodes only creates a pipeline for each node
                nodes = await core.nodes('ou:org parallel --size 10 {[ :name=foo ]}')
                self.len(5, nodes)
                self.true(all([n.get('name') == 'foo' for n in nodes]))
                self.eq(5, tsks['cnt'])

                tsks['cnt'] = 0

                nodes = await core.nodes('parallel --size 4 {[ ou:org=* ]}')
                self.len(4, nodes)
                self.eq(4, tsks['cnt'])

            self.len(20, await core.nodes('for $i in $lib.range(20) {[ test:str=$i ]}'))
            q = '''
            test:str
            parallel --size 4 {
                if (not $lib.vars.get(vals)) {
                    $vals = ()
                }
                $vals.append($node.repr())
                fini { $lib.fire(resu, vals=$vals) }
            }
            | spin
            '''
            vals = []
            msgs = await core.stormlist(q)
            for m in msgs:
                if m[0] == 'storm:fire':
                    vals.extend(m[1]['data']['vals'])

            self.len(20, vals)

            q = '''
            $vals = ()
            test:str
            parallel --size 4 { $vals.append($node.repr()) }
            fini { return($vals) }
            '''
            self.len(20, await core.callStorm(q))

            q = '''
            function test(n) { $lib.fire(foo, valu=$n.repr()) return() }
            test:str
            parallel --size 4 { $test($node) }
            '''
            msgs = await core.stormlist(q)
            self.len(20, [m for m in msgs if m[0] == 'storm:fire' and m[1]['type'] == 'foo'])

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

            # test that stormtypes nodes can be yielded
            self.len(1, await core.nodes('for $x in ${ [inet:ipv4=1.2.3.4] } { yield $x }'))

            # Some sad path tests
            with self.raises(s_exc.BadLiftValu):
                await core.nodes('yield $foo', opts={'vars': {'foo': 'asdf'}})

            # Nodes from other views do not lift
            view = await core.callStorm('return( $lib.view.get().iden )')
            fork = await core.callStorm('return( $lib.view.get().fork().iden )')

            q = '''
            $nodes = ()
            view.exec $view { inet:ipv4=1.2.3.4 $nodes.append($node) } |
            for $n in $nodes {
                yield $n
            }
            '''
            msgs = await core.stormlist(q, opts={'view': fork, 'vars': {'view': view}})
            self.stormIsInErr('Node is not from the current view.', msgs)

            q = '''
            $nodes = ()
            view.exec $view { for $x in ${ inet:ipv4=1.2.3.4 } { $nodes.append($x) } } |
            for $n in $nodes {
                yield $n
            }
            '''
            msgs = await core.stormlist(q, opts={'view': fork, 'vars': {'view': view}})
            self.stormIsInErr('Node is not from the current view.', msgs)

            q = 'view.exec $view { $x=${inet:ipv4=1.2.3.4} } | yield $x'
            msgs = await core.stormlist(q, opts={'view': fork, 'vars': {'view': view}})
            self.stormIsInErr('Node is not from the current view.', msgs)

            # Nodes lifted from another view and referred to by iden() works
            q = '''
            $nodes = ()
            view.exec $view { inet:ipv4=1.2.3.4 $nodes.append($node) } |
            for $n in $nodes {
                yield $n.iden()
            }
            '''
            nodes = await core.nodes(q, opts={'view': fork, 'vars': {'view': view}})
            self.len(1, nodes)

            q = '''
            $nodes = ()
            view.exec $view { for $x in ${ inet:ipv4=1.2.3.4 } { $nodes.append($x) } } |
            for $n in $nodes {
                yield $n.iden()
            }
            '''
            nodes = await core.nodes(q, opts={'view': fork, 'vars': {'view': view}})
            self.len(1, nodes)

            q = 'view.exec $view { $x=${inet:ipv4=1.2.3.4} } | for $n in $x { yield $n.iden() }'
            nodes = await core.nodes(q, opts={'view': fork, 'vars': {'view': view}})
            self.len(1, nodes)

    async def test_storm_viewexec(self):

        async with self.getTestCore() as core:

            view = await core.callStorm('return( $lib.view.get().iden )')
            fork = await core.callStorm('return( $lib.view.get().fork().iden )')

            await core.addStormPkg({
                'name': 'testpkg',
                'version': (0, 0, 1),
                'modules': (
                    {'name': 'priv.exec',
                     'asroot:perms': [['power-ups', 'testpkg']],
                     'modconf': {'viewiden': fork},
                     'storm': '''
                        function asroot () {
                            view.exec $modconf.viewiden { $foo=bar } | return($foo)
                        }
                     '''},
                ),
            })

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            await core.stormlist('auth.user.addrule visi power-ups.testpkg')

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return(woot)', opts={'user': visi.iden, 'view': fork})

            self.eq('bar', await core.callStorm('return($lib.import(priv.exec).asroot())', opts=asvisi))

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
        self.isin('default:\n                                [', helptext)

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

        # choices - bad setup
        pars = s_storm.Parser()
        with self.raises(s_exc.BadArg) as cm:
            pars.add_argument('--foo', action='store_true', choices=['newp'])
        self.eq('Argument choices are not supported when action is store_true or store_false', cm.exception.get('mesg'))

        # choices - basics
        pars = s_storm.Parser()
        pars.add_argument('foo', type='int', choices=[3, 1, 2], help='foohelp')
        pars.add_argument('--bar', choices=['baz', 'bam'], help='barhelp')
        pars.add_argument('--cam', action='append', choices=['cat', 'cool'], help='camhelp')

        opts = pars.parse_args(['1', '--bar', 'bam', '--cam', 'cat', '--cam', 'cool'])
        self.eq(1, opts.foo)
        self.eq('bam', opts.bar)
        self.eq(['cat', 'cool'], opts.cam)

        opts = pars.parse_args([32])
        self.none(opts)
        self.eq('Invalid choice for argument <foo> (choose from: 3, 1, 2): 32', pars.exc.errinfo['mesg'])

        opts = pars.parse_args([2, '--bar', 'newp'])
        self.none(opts)
        self.eq('Invalid choice for argument --bar (choose from: baz, bam): newp', pars.exc.errinfo['mesg'])

        opts = pars.parse_args([2, '--cam', 'cat', '--cam', 'newp'])
        self.none(opts)
        self.eq('Invalid choice for argument --cam (choose from: cat, cool): newp', pars.exc.errinfo['mesg'])

        pars.mesgs.clear()
        pars.help()
        self.eq('  --bar <bar>                 : barhelp (choices: baz, bam)', pars.mesgs[5])
        self.eq('  --cam <cam>                 : camhelp (choices: cat, cool)', pars.mesgs[6])
        self.eq('  <foo>                       : foohelp (choices: 3, 1, 2)', pars.mesgs[10])

        # choices - default does not have to be in choices
        pars = s_storm.Parser()
        pars.add_argument('--foo', default='def', choices=['faz'], help='foohelp')

        opts = pars.parse_args([])
        self.eq('def', opts.foo)

        pars.help()
        self.eq('  --foo <foo>                 : foohelp (default: def, choices: faz)', pars.mesgs[-1])

        # choices - like defaults, choices are not normalized
        pars = s_storm.Parser()
        ttyp = s_datamodel.Model().type('time')
        pars.add_argument('foo', type='time', choices=['2022', ttyp.norm('2023')[0]], help='foohelp')

        opts = pars.parse_args(['2023'])
        self.eq(ttyp.norm('2023')[0], opts.foo)

        opts = pars.parse_args(['2022'])
        self.none(opts)
        errmesg = pars.exc.errinfo['mesg']
        self.eq('Invalid choice for argument <foo> (choose from: 2022, 1672531200000): 1640995200000', errmesg)

        pars.help()
        self.eq('  <foo>                       : foohelp (choices: 2022, 1672531200000)', pars.mesgs[-1])

        # choices - nargs
        pars = s_storm.Parser()
        pars.add_argument('foo', nargs='+', choices=['faz'])
        pars.add_argument('--bar', nargs='?', choices=['baz'])
        pars.add_argument('--cat', nargs=2, choices=['cam', 'cool'])

        opts = pars.parse_args(['newp'])
        self.none(opts)
        self.eq('Invalid choice for argument <foo> (choose from: faz): newp', pars.exc.errinfo['mesg'])

        opts = pars.parse_args(['faz', '--bar', 'newp'])
        self.none(opts)
        self.eq('Invalid choice for argument --bar (choose from: baz): newp', pars.exc.errinfo['mesg'])

        opts = pars.parse_args(['faz', '--cat', 'newp', 'newp2'])
        self.none(opts)
        self.eq('Invalid choice for argument --cat (choose from: cam, cool): newp', pars.exc.errinfo['mesg'])

        opts = pars.parse_args(['faz', '--cat', 'cam', 'cool'])
        self.nn(opts)

        pars = s_storm.Parser()
        pars.add_argument('--baz', nargs=3, help='''
             This is the top line, nothing special.
             This is my second line with sublines that should have some leading spaces:
                subline 1: this is a line which has three spaces.
                  subline 2: this is another line with five leading spaces.
               subline 3: yet another line with only two leading spaces.
              subline 4: this line has one space and is long which should wrap around because it exceeds the default display width.
             This is the final line with no leading spaces.''')
        pars.add_argument('--taz', type='bool', default=True, help='Taz option')
        pars.help()
        self.eq('  --baz <baz>                 : This is the top line, nothing special.', pars.mesgs[5])
        self.eq('                                This is my second line with sublines that should have some leading spaces:', pars.mesgs[6])
        self.eq('                                   subline 1: this is a line which has three spaces.', pars.mesgs[7])
        self.eq('                                     subline 2: this is another line with five leading spaces.', pars.mesgs[8])
        self.eq('                                  subline 3: yet another line with only two leading spaces.', pars.mesgs[9])
        self.eq('                                 subline 4: this line has one space and is long which should wrap around because it', pars.mesgs[10])
        self.eq('                                 exceeds the default display width.', pars.mesgs[11])
        self.eq('                                This is the final line with no leading spaces.', pars.mesgs[12])
        self.eq('  --taz <taz>                 : Taz option (default: True)', pars.mesgs[13])

    async def test_storm_cmd_help(self):

        async with self.getTestCore() as core:
            pdef = {
                'name': 'testpkg',
                'version': '0.0.1',
                'commands': (
                    {'name': 'woot', 'cmdinputs': (
                        {'form': 'hehe:haha'},
                        {'form': 'hoho:lol', 'help': 'We know whats up'}
                    ), 'endpoints': (
                        {'path': '/v1/test/one', 'desc': 'My multi-line endpoint description which spans multiple lines and has a second line. This is the second line of the description.'},
                        {'path': '/v1/test/two', 'host': 'vertex.link', 'desc': 'Single line endpoint description.'},
                    )},
                ),
            }
            core.loadStormPkg(pdef)
            msgs = await core.stormlist('woot --help')
            helptext = '\n'.join([m[1].get('mesg') for m in msgs if m[0] == 'print'])
            self.isin('Inputs:\n\n    hehe:haha\n    hoho:lol  - We know whats up', helptext)
            self.isin('Endpoints:\n\n    /v1/test/one              : My multi-line endpoint description which spans multiple lines and has a second line.', helptext)
            self.isin('This is the second line of the description.', helptext)
            self.isin('/v1/test/two              : Single line endpoint description.', helptext)

    async def test_storm_help_cmd(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('.created | limit 1 | help')
            self.printed(msgs, 'package: synapse')
            self.stormIsInPrint('help', msgs)
            self.stormIsInPrint('List available information about Storm and brief descriptions of different items.',
                                msgs)
            self.len(1, [n for n in msgs if n[0] == 'node'])

            msgs = await core.stormlist('help')
            self.printed(msgs, 'package: synapse')
            self.stormIsInPrint('help', msgs)
            self.stormIsInPrint('List available information about Storm and brief descriptions of different items.',
                                msgs)

            msgs = await core.stormlist('help view')
            self.stormIsInPrint('Storm api for a View instance', msgs)
            self.stormIsInPrint('view.merge', msgs)
            self.stormNotInPrint('tee', msgs)

            msgs = await core.stormlist('help newp')
            self.stormIsInPrint('No commands found matching "newp"', msgs)
            self.stormNotInPrint('uniq', msgs)

            otherpkg = {
                'name': 'foosball',
                'version': '0.0.1',
                'synapse_version': '>=2.8.0,<3.0.0',
                'commands': ({
                                 'name': 'testcmd',
                                 'descr': 'test command',
                                 'storm': '[ inet:ipv4=1.2.3.4 ]',
                             },),
                'modules': (
                    {
                        'name': 'foosmod',
                        'storm': '''
                                function f(a) {return ($a)}
                                ''',
                    },
                ),

            }
            self.none(await core.addStormPkg(otherpkg))

            msgs = await core.stormlist('help')
            self.printed(msgs, 'package: foosball')
            self.stormIsInPrint('testcmd', msgs)
            self.stormIsInPrint(': test command', msgs)

            msgs = await core.stormlist('help testcmd')
            self.stormIsInPrint('testcmd', msgs)
            self.stormNotInPrint('view.merge', msgs)

            msgs = await core.stormlist('[test:str=uniq] | help $node.value')
            self.stormIsInPrint('Get the value of the primary property of the Node.', msgs)

            msgs = await core.stormlist('[test:str=uniq] | help $node.value()')
            self.stormNotInPrint('Get the value of the primary property of the Node.', msgs)
            self.stormIsInPrint('uniq: Filter nodes by their uniq iden values.', msgs)

            msgs = await core.stormlist('[ test:str=uniq ] | help $node.props')
            self.stormIsInPrint('A Storm Primitive representing the properties on a Node.', msgs)
            self.stormIsInPrint('set(prop, valu)\nSet a specific property value by name.', msgs)

            msgs = await core.stormlist('[ test:str=uniq ] | help $node')
            self.stormIsInPrint('Implements the Storm api for a node instance.', msgs)

            msgs = await core.stormlist('[ test:str=uniq ] | help $path')
            self.stormIsInPrint('Implements the Storm API for the Path object.', msgs)

            # $lib helps
            msgs = await core.stormlist('help $lib')
            self.stormIsInPrint('$lib.auth                     : A Storm Library for interacting with Auth in the '
                                'Cortex.',
                                msgs)
            self.stormIsInPrint('$lib.import(name, debug=(false), reqvers=(null))\nImport a Storm module.',
                                msgs)
            self.stormIsInPrint('$lib.debug\nTrue if the current runtime has debugging enabled.', msgs)
            self.stormNotInPrint('Examples', msgs)

            msgs = await core.stormlist('help -v $lib')

            self.stormIsInPrint('$lib.import(name, debug=(false), reqvers=(null))\n'
                                '================================================\n'
                                'Import a Storm module.', msgs)

            msgs = await core.stormlist('help $lib.macro')
            self.stormIsInPrint('$lib.macro.del(name)\nDelete a Storm Macro by name from the Cortex.', msgs)

            msgs = await core.stormlist('help list')
            self.stormIsInPrint('***\nlist\n****\nImplements the Storm API for a List instance.', msgs)
            self.stormIsInPrint('append(valu)\nAppend a value to the list.', msgs)
            self.stormIsInPrint('auth.user.list     : List all users.', msgs)

            # email stor / gettr has a multi value return type
            msgs = await core.stormlist('help -v auth:user')
            self.stormIsInPrint('Implements the Storm API for a User.', msgs)
            self.stormIsInPrint("A user's email. This can also be used to set the user's email.", msgs)
            self.stormIsInPrint('The return type may be one of the following: str, null.', msgs)

            msgs = await core.stormlist('help $lib.regex')
            self.stormIsInPrint('The following references are available:\n\n'
                                '$lib.regex.flags.i\n'
                                'Regex flag to indicate that case insensitive matches are allowed.\n\n'
                                '$lib.regex.flags.m\n'
                                'Regex flag to indicate that multiline matches are allowed.', msgs)

            msgs = await core.stormlist('help $lib.inet.http.get')
            self.stormIsInPrint('$lib.inet.http.get(url, headers=(null)', msgs)
            self.stormIsInPrint('Get the contents of a given URL.', msgs)

            msgs = await core.stormlist('$str=hehe help $str.split')
            self.stormIsInPrint('Split the string into multiple parts based on a separator.', msgs)

            msgs = await core.stormlist('help $lib.gen.orgByName')
            self.stormIsInPrint('Returns an ou:org by name, adding the node if it does not exist.', msgs)

            msgs = await core.stormlist('help --verbose $lib.gen.orgByName')
            self.stormIsInPrint('Returns an ou:org by name, adding the node if it does not exist.\n'
                                'Args:\n    name (str): The name of the org.', msgs)

            msgs = await core.stormlist('help --verbose $lib.infosec.cvss.saveVectToNode')
            self.stormIsInPrint('Warning', msgs)
            self.stormIsInPrint('``$lib.infosec.cvss.saveVectToNode`` has been deprecated and will be removed in version v3.0.0.', msgs)

            msgs = await core.stormlist('help --verbose $lib.inet.whois.guid')
            self.stormIsInPrint('Warning', msgs)
            self.stormIsInPrint('``$lib.inet.whois.guid`` has been deprecated and will be removed in version v3.0.0.', msgs)
            self.stormIsInPrint('Please use the GUID constructor syntax.', msgs)

            msgs = await core.stormlist('help $lib.inet')
            self.stormIsInPrint('The following libraries are available:\n\n'
                                '$lib.inet.http                : A Storm Library exposing an HTTP client API.\n'
                                '$lib.inet.http.oauth.v1       : A Storm library to handle OAuth v1 authentication.\n'
                                '$lib.inet.http.oauth.v2       : A Storm library for managing OAuth V2 clients.\n',
                                msgs)
            self.stormNotInPrint('$lib.inet.http.get(', msgs)

            msgs = await core.stormlist('help $lib.regex.flags')
            err = 'Item must be a Storm type name, a Storm library, or a Storm command name to search for. Got dict'
            self.stormIsInErr(err, msgs)

            url = core.getLocalUrl()
            msgs = await core.stormlist('$prox=$lib.telepath.open($url) help $prox.getCellInfo',
                                        opts={'vars': {'url': url}})
            self.stormIsInPrint('Implements the call methods for the telepath:proxy.', msgs)

            msgs = await core.stormlist('$prox=$lib.telepath.open($url) help $prox.storm',
                                        opts={'vars': {'url': url}})
            self.stormIsInPrint('Implements the generator methods for the telepath:proxy.', msgs)

            msgs = await core.stormlist('function f(){} help $f')
            self.stormIsInErr('help does not currently support runtime defined functions.', msgs)

            msgs = await core.stormlist('$mod=$lib.import(foosmod) help $mod')
            self.stormIsInErr('Help does not currently support imported Storm modules.', msgs)

            msgs = await core.stormlist('$mod=$lib.import(foosmod) help $mod.f')
            self.stormIsInErr('help does not currently support runtime defined functions.', msgs)

            msgs = await core.stormlist('help --verbose $lib.bytes')
            self.stormIsInPrint('Warning', msgs)
            self.stormIsInPrint('$lib.bytes.put`` has been deprecated and will be removed in version v3.0.0', msgs)
            self.stormIsInPrint('$lib.bytes.has`` has been deprecated and will be removed in version v3.0.0', msgs)
            self.stormIsInPrint('$lib.bytes.size`` has been deprecated and will be removed in version v3.0.0', msgs)
            self.stormIsInPrint('$lib.bytes.upload`` has been deprecated and will be removed in version v3.0.0', msgs)
            self.stormIsInPrint('$lib.bytes.hashset`` has been deprecated and will be removed in version v3.0.0', msgs)
            self.stormIsInPrint('Use the corresponding ``$lib.axon`` function.', msgs)

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
            msgs = await core.stormlist(q, opts={'links': True})
            nodes = [n[1] for n in msgs if n[0] == 'node']
            self.len(4, nodes)
            self.eq({n[0][1] for n in nodes},
                    {'test1', 'test2', 'refs', 'foo'})
            links = nodes[1][1]['links']
            self.len(1, links)
            self.eq({'type': 'runtime'}, links[0][1])

            links = nodes[2][1]['links']
            self.len(1, links)
            self.eq({'type': 'runtime'}, links[0][1])

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
            view = await core.callStorm('return ($lib.view.get().fork().iden)')
            opts = {'view': view}

            await core.nodes('[test:int=8191 test:int=127]')
            await core.stormlist('test:int=127 | [ <(refs)+ { test:int=8191 } ]', opts=opts)

            # Delete the N1 out from under the fork
            msgs = await core.stormlist('test:int=8191 | delnode')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('test:int=127 | edges.del * --n2', opts=opts)
            self.stormHasNoWarnErr(msgs)

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
                view3, layr3 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')

                opts = {'vars': {
                    'view0': view0,
                    'view1': view1,
                    'view2': view2,
                    'view3': view3,
                    'layr0': layr0,
                    'layr1': layr1,
                    'layr2': layr2,
                    'layr3': layr3,
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

                # Add slow pushers
                q = f'''$url="tcp://root:secret@127.0.0.1:{port}/*/layer/{layr3}"
                $pdef = $lib.layer.get($layr0).addPush($url, queue_size=10, chunk_size=1)
                return($pdef.iden)'''
                slowpush = await core.callStorm(q, opts=opts)
                q = f'''$url="tcp://root:secret@127.0.0.1:{port}/*/layer/{layr0}"
                $pdef = $lib.layer.get($layr3).addPull($url, queue_size=20, chunk_size=10)
                return($pdef.iden)'''
                slowpull = await core.callStorm(q, opts=opts)

                pushs = await core.callStorm('return($lib.layer.get($layr0).get(pushs))', opts=opts)
                self.isin(slowpush, pushs)

                pulls = await core.callStorm('return($lib.layer.get($layr3).get(pulls))', opts=opts)
                self.isin(slowpull, pulls)

                self.none(await core.callStorm(f'return($lib.layer.get($layr0).delPush({slowpush}))', opts=opts))
                self.none(await core.callStorm(f'return($lib.layer.get($layr3).delPull({slowpull}))', opts=opts))

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
                await core.callStorm('$lib.view.del($view3)', opts=opts)
                await core.callStorm('$lib.layer.del($layr0)', opts=opts)
                await core.callStorm('$lib.layer.del($layr1)', opts=opts)
                await core.callStorm('$lib.layer.del($layr2)', opts=opts)
                await core.callStorm('$lib.layer.del($layr3)', opts=opts)

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

                await core.addUserRule(visi.iden, (True, ('layer', 'add')))
                l1 = await core.callStorm('$layer=$lib.layer.add() return ($layer) ', opts={'user': visi.iden})
                l2 = await core.callStorm('$layer=$lib.layer.add() return ($layer) ', opts={'user': visi.iden})
                varz = {'iden': l1.get('iden'), 'tgt': l2.get('iden'), 'port': port}
                pullq = '$layer=$lib.layer.get($iden).addPull(`tcp://root:secret@127.0.0.1:{$port}/*/layer/{$tgt}`)'
                pushq = '$layer=$lib.layer.get($iden).addPush(`tcp://root:secret@127.0.0.1:{$port}/*/layer/{$tgt}`)'
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(pullq, opts={'user': visi.iden, 'vars': varz})
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(pullq, opts={'user': visi.iden, 'vars': varz})

                await core.addUserRule(visi.iden, (True, ('storm', 'lib', 'telepath', 'open', 'tcp')))

                msgs = await core.stormlist(pullq, opts={'user': visi.iden, 'vars': varz})
                self.stormHasNoWarnErr(msgs)

                msgs = await core.stormlist(pushq, opts={'user': visi.iden, 'vars': varz})
                self.stormHasNoWarnErr(msgs)

                l1iden = l1.get('iden')
                pdef = list(core.getLayer(l1iden).layrinfo['pushs'].values())[0]
                self.none(await core.addLayrPush(l1iden, pdef))
                self.len(1, list(core.getLayer(l1iden).layrinfo['pushs'].values()))

                pdef = list(core.getLayer(l1iden).layrinfo['pulls'].values())[0]
                self.none(await core.addLayrPull(l1iden, pdef))
                self.len(1, list(core.getLayer(l1iden).layrinfo['pulls'].values()))

    async def test_storm_tagprune(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[test:str=foo +#parent.child.grandchild]'))
            self.len(1, await core.nodes('[test:str=bar +#parent.childtag +#parent.child.step +#parent.child.grandchild]'))
            self.len(1, await core.nodes('[test:str=baz +#parent.child.step +#parent.child.step.two +#parent.child.step.three]'))

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

            self.len(1, await core.nodes('[test:str=foo +#tag.tree.one +#tag.tree.two +#another.tag.tree]'))
            self.len(1, await core.nodes('[test:str=baz +#tag.tree.one +#tag.tree.two +#another.tag.tree +#more.tags.to.remove +#tag.that.stays]'))

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

            self.len(1, await core.nodes('[test:str=runtsafety +#runtsafety]'))
            self.len(1, await core.nodes('[test:str=foo +#runtsafety]'))
            self.len(1, await  core.nodes('[test:str=runt.safety.two +#runt.safety.two +#runt.child]'))

            # Test non-runtsafe usage
            await core.nodes('test:str | tag.prune $node.value()')

            node = (await core.nodes('test:str=runtsafety'))[0]
            self.eq(list(node.tags.keys()), [])

            node = (await core.nodes('test:str=foo'))[0]
            self.eq(list(node.tags.keys()), ['runtsafety'])

            node = (await core.nodes('test:str=runt.safety.two'))[0]
            self.eq(list(node.tags.keys()), ['runt', 'runt.child'])

            self.len(1, await core.nodes('[test:str=foo +#runt.need.perms]'))
            self.len(1, await core.nodes('[test:str=runt.safety.two +#runt.safety.two]'))

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
            core.loadStormPkg({
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
            self.len(2, [item for item in items if item[-1]['user'] == visi.iden])

            await core.nodes(f'runas {visi.iden} {{ [ inet:fqdn=baz.com ] }}')

            items = await alist(core.syncLayersEvents({}, wait=False))
            self.len(4, [item for item in items if item[-1]['user'] == visi.iden])

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
            await core.addStormPkg({
                'name': 'synapse-woot',
                'version': (0, 0, 1),
                'modules': (
                    {'name': 'woot.runas',
                     'asroot:perms': [['power-ups', 'woot', 'user']],
                     'storm': 'function asroot () { runas root { $lib.print(woot) return() }}'},
                ),
            })

            asvisi = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.import(woot.runas).asroot())', opts=asvisi)

            await core.stormlist('auth.user.addrule visi power-ups.woot.user')
            await core.callStorm('return($lib.import(woot.runas).asroot())', opts=asvisi)

            await self.asyncraises(s_exc.AuthDeny, core.nodes('asroot.not'))

            nodes = await core.nodes('asroot.yep | inet:fqdn=foo.com')
            for node in nodes:
                self.none(node.tags.get('btag'))

    async def test_storm_batch(self):
        async with self.getTestCore() as core:
            q = '''
                for $i in $lib.range(12) {[ test:str=$i ]}

                batch $lib.true --size 5 ${
                    $vals=([])
                    for $n in $nodes { $vals.append($n.repr()) }
                    $lib.print($lib.str.join(',', $vals))
                }
            '''
            msgs = await core.stormlist(q)
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInPrint('0,1,2,3,4', msgs)
            self.stormIsInPrint('5,6,7,8,9', msgs)
            self.stormIsInPrint('10,11', msgs)

            q = '''
                for $i in $lib.range(12) { test:str=$i }

                batch $lib.false --size 5 {
                    $vals=([])
                    for $n in $nodes { $vals.append($n.repr()) }
                    $lib.print($lib.str.join(',', $vals))
                }
            '''
            msgs = await core.stormlist(q)
            self.len(12, [m for m in msgs if m[0] == 'node'])
            self.stormIsInPrint('0,1,2,3,4', msgs)
            self.stormIsInPrint('5,6,7,8,9', msgs)
            self.stormIsInPrint('10,11', msgs)

            q = '''
                for $i in $lib.range(12) { test:str=$i }
                batch $lib.true --size 5 { yield $nodes }
            '''
            msgs = await core.stormlist(q)
            self.len(12, [m for m in msgs if m[0] == 'node'])

            q = '''
                for $i in $lib.range(12) { test:str=$i }
                batch $lib.false --size 5 { yield $nodes }
            '''
            msgs = await core.stormlist(q)
            self.len(12, [m for m in msgs if m[0] == 'node'])

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('batch $lib.true --size 20000 {}')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('test:str batch $lib.true --size $node {}')

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
            self.stormIsInErr("Expected 1 positional arguments. Got 2: ['->', 'file:base:ext=doc']", msgs)

            msgs = await core.stormlist('help yield')
            self.stormIsInPrint('No commands found matching "yield"', msgs)

            q = '''inet:fqdn:zone=earthsolution.org -> inet:dns:request -> file:bytes | uniq -> inet.dns.request'''
            msgs = await core.stormlist(q)
            self.stormHasNoErr(msgs)

            await core.nodes('''$token=foo $lib.print(({"Authorization":$lib.str.format("Bearer {token}", token=$token)}))''')

            q = '#rep.clearsky.dreamjob -># +syn:tag^=rep |uniq -syn:tag~=rep.clearsky'
            msgs = await core.stormlist(q)
            self.stormIsInErr("Expected 1 positional arguments", msgs)

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
            self.stormIsInErr('No form named media:news:org', msgs)

            q = 'media:news:org#test:score'
            msgs = await core.stormlist(q)
            self.stormIsInErr('No form named media:news:org', msgs)

            q = 'media:news:org#test.*.bar'
            msgs = await core.stormlist(q)
            self.stormIsInErr("Unexpected token 'default case'", msgs)

            q = '#test.*.bar'
            msgs = await core.stormlist(q)
            self.stormIsInErr("Unexpected token 'default case'", msgs)

            q = 'media:news:org#test.*.bar:score'
            msgs = await core.stormlist(q)
            self.stormIsInErr("Unexpected token 'default case'", msgs)

    async def test_storm_copyto(self):

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})

            msgs = await core.stormlist('[ inet:user=visi ] | copyto $node.repr()')
            self.stormIsInErr('copyto arguments must be runtsafe', msgs)

            msgs = await core.stormlist('[ inet:user=visi ] | copyto newp')
            self.stormIsInErr('No such view:', msgs)

            layr = await core.callStorm('return($lib.layer.add().iden)')

            opts = {'vars': {'layers': (layr,)}}
            view = await core.callStorm('return($lib.view.add(layers=$layers).iden)', opts=opts)

            msgs = await core.stormlist('''
                [ media:news=* :title=vertex :url=https://vertex.link
                    +(refs)> { [ inet:ipv4=1.1.1.1 inet:ipv4=2.2.2.2 ] }
                    <(bars)+ { [ inet:ipv4=5.5.5.5 inet:ipv4=6.6.6.6 ] }
                    +#foo.bar:score=10
                ]
                $node.data.set(foo, bar)
            ''')
            self.stormHasNoWarnErr(msgs)

            opts = {'view': view}
            msgs = await core.stormlist('[ inet:ipv4=1.1.1.1 inet:ipv4=5.5.5.5 ]', opts=opts)
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('media:news | copyto $view', opts={'vars': {'view': view}})
            self.stormHasNoWarnErr(msgs)

            self.len(1, await core.nodes('media:news +#foo.bar:score>1'))
            self.len(1, await core.nodes('media:news +:title=vertex :url -> inet:url', opts=opts))
            nodes = await core.nodes('media:news +:title=vertex -(refs)> inet:ipv4', opts=opts)
            self.len(1, nodes)
            self.eq(('inet:ipv4', 0x01010101), nodes[0].ndef)

            nodes = await core.nodes('media:news +:title=vertex <(bars)- inet:ipv4', opts=opts)
            self.len(1, nodes)
            self.eq(('inet:ipv4', 0x05050505), nodes[0].ndef)
            self.eq('bar', await core.callStorm('media:news return($node.data.get(foo))', opts=opts))

            oldn = await core.nodes('[ inet:ipv4=2.2.2.2 ]', opts=opts)
            await asyncio.sleep(0.1)
            newn = await core.nodes('[ inet:ipv4=2.2.2.2 ]')
            self.ne(oldn[0].props['.created'], newn[0].props['.created'])

            msgs = await core.stormlist('inet:ipv4=2.2.2.2 | copyto $view', opts={'vars': {'view': view}})
            self.stormHasNoWarnErr(msgs)

            oldn = await core.nodes('inet:ipv4=2.2.2.2', opts=opts)
            self.eq(oldn[0].props['.created'], newn[0].props['.created'])

            await core.nodes('[ test:ro=bad :readable=foo ]', opts=opts)
            await core.nodes('[ test:ro=bad :readable=bar ]')

            msgs = await core.stormlist('test:ro=bad | copyto $view', opts={'vars': {'view': view}})
            self.stormIsInWarn("Cannot overwrite read only property with conflicting value", msgs)

            nodes = await core.nodes('test:ro=bad', opts=opts)
            self.eq(nodes[0].props.get('readable'), 'foo')

    async def test_lib_storm_delnode(self):
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('node',)))

            size, sha256 = await core.callStorm('return($lib.axon.put($buf))', {'vars': {'buf': b'asdfasdf'}})

            self.len(1, await core.nodes(f'[ file:bytes={sha256} ]'))

            await core.nodes(f'file:bytes={sha256} | delnode')
            self.len(0, await core.nodes(f'file:bytes={sha256}'))
            self.true(await core.axon.has(s_common.uhex(sha256)))

            self.len(1, await core.nodes(f'[ file:bytes={sha256} ]'))

            async with core.getLocalProxy(user='visi') as asvisi:

                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'file:bytes={sha256} | delnode --delbytes')

                await visi.addRule((True, ('storm', 'lib', 'axon', 'del')))

                await asvisi.callStorm(f'file:bytes={sha256} | delnode --delbytes')
                self.len(0, await core.nodes(f'file:bytes={sha256}'))
                self.false(await core.axon.has(s_common.uhex(sha256)))

    async def test_lib_dmon_embed(self):

        async with self.getTestCore() as core:
            await core.nodes('''
                function dostuff(mesg) {
                    $query = ${
                        $lib.queue.gen(hehe).put($mesg)
                        $lib.dmon.del($auto.iden)
                    }
                    $lib.dmon.add($query)
                    return()
                }
                $dostuff(woot)
            ''')

            self.eq('woot', await core.callStorm('return($lib.queue.gen(hehe).get().1)'))

            await core.nodes('''
                function dostuff(mesg) {
                    $query = ${
                        $lib.queue.gen(haha).put($lib.vars.get(mesg))
                        $lib.dmon.del($auto.iden)
                    }
                    $lib.dmon.add($query)
                    return()
                }
                $dostuff($lib.set())
            ''')

            self.none(await core.callStorm('return($lib.queue.gen(haha).get().1)'))

            await core.nodes('''
                $foo = (foo,)
                $query = ${
                    $foo.append(bar)
                    $lib.queue.gen(hoho).put($foo)
                    $lib.dmon.del($auto.iden)
                }
                $lib.dmon.add($query)
            ''')

            self.eq(['foo', 'bar'], await core.callStorm('return($lib.queue.gen(hoho).get().1)'))
