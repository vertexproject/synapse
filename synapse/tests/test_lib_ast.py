import json
import math
import asyncio

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.ast as s_ast
import synapse.lib.snap as s_snap

import synapse.tests.utils as s_test

foo_stormpkg = {
    'name': 'foo',
    'desc': 'The Foo Module',
    'version': (0, 0, 1),
    'synapse_minversion': [2, 144, 0],
    'synapse_version': '>=2.8.0,<3.0.0',
    'modules': [
        {
            'name': 'hehe.haha',
            'storm': '''
                $intval = $(10)
                function lolz(x, y) {
                    return ($( $x + $y ))
                }
            ''',
        },
        {
            'name': 'hehe.hoho',
            'storm': '''
                function nodes (x, y) {
                    [ test:str=$x ]
                    [ test:str=$y ]
                }
            ''',
        },
        {
            'name': 'test',
            'storm': '''
            function pprint(arg1, arg2, arg3) {
                $lib.print('arg1: {arg1}', arg1=$arg1)
                $lib.print('arg2: {arg2}', arg2=$arg2)
                $lib.print('arg3: {arg3}', arg3=$arg3)
                return()
            }
            '''
        },
        {
            'name': 'testdefault',
            'storm': '''
            function doit(arg1, arg2, arg3=foo, arg4=(42)) {
                return(($arg1, $arg2, $arg3, $arg4))
            }
            '''
        },
        {
            'name': 'importnest',
            'storm': '''
            $foobar = $(0)
            $counter = $(0)

            function inner(arg2, add) {
                $foobar = $( $foobar + $add )
                $lib.print('counter is {c}', c=$counter)
                if $( $arg2 ) {
                    $retn = "foo"
                } else {
                    $retn = "bar"
                }
                return ($retn)
            }

            function outer(arg1, add) {
                $strbase = $lib.str.format("(Run: {c}) we got back ", c=$counter)
                $reti = $inner($arg1, $add)
                $mesg = $lib.str.concat($strbase, $reti)
                $counter = $( $counter + $add )
                $lib.print("foobar is {foobar}", foobar=$foobar)
                return ($mesg)
            }
            ''',
        },
        {
            'name': 'yieldsforever',
            'storm': '''
            $splat = 18
            function rockbottom(arg1) {
                [test:str = $arg1]
            }

            function middlechild(arg2) {
                yield $rockbottom($arg2)
            }

            function yieldme(arg3) {
                yield $middlechild($arg3)
            }
            ''',
        },
    ],
    'commands': [
        {
            'name': 'foo.bar',
            'storm': '''
                init {
                    $foolib = $lib.import(hehe.haha)
                    [ test:int=$foolib.lolz($(20), $(30)) ]
                }
            ''',
        },
        {
            'name': 'test.nodes',
            'storm': '''
                $foolib = $lib.import(hehe.hoho)
                yield $foolib.nodes(asdf, qwer)
            ''',
        },
    ],
}

class AstTest(s_test.SynTest):

    async def test_mode_search(self):

        conf = {'storm:interface:search': False}
        async with self.getTestCore(conf=conf) as core:
            msgs = await core.stormlist('asdf asdf', opts={'mode': 'search'})
            self.stormIsInWarn('Storm search interface is not enabled!', msgs)

        async with self.getTestCore() as core:
            await core.loadStormPkg({
                'name': 'testsearch',
                'modules': [
                    {'name': 'testsearch', 'interfaces': ['search'], 'storm': '''
                        function search(tokens) {
                            for $tokn in $tokens {
                                ou:org:name^=$tokn
                                emit ((0), $lib.hex.decode($node.iden()))
                            }
                        }
                    '''},
                ],
            })
            await core.nodes('[ ou:org=* :name=apt1 ]')
            await core.nodes('[ ou:org=* :name=vertex ]')
            nodes = await core.nodes('apt1', opts={'mode': 'search'})
            self.len(1, nodes)
            nodeiden = nodes[0].iden()
            self.eq('apt1', nodes[0].props.get('name'))

            nodes = await core.nodes('', opts={'mode': 'search'})
            self.len(0, nodes)

            nodes = await core.nodes('| uniq', opts={'mode': 'search', 'idens': [nodeiden]})
            self.len(1, nodes)

            with self.raises(s_exc.BadSyntax):
                await core.nodes('| $$$$', opts={'mode': 'search'})

    async def test_try_set(self):
        '''
        Test ?= assignment
        '''
        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:str?=(1,2,3,4) ]')
            self.len(0, nodes)
            nodes = await core.nodes('[test:int?=4] [ test:int?=nonono ]')
            self.len(1, nodes)
            nodes = await core.nodes('[test:comp?=(yoh,nope)]')
            self.len(0, nodes)

            nodes = await core.nodes('[test:str=foo :hehe=no42] [test:int?=:hehe]')
            self.len(1, nodes)

            nodes = await core.nodes('[ test:str=foo :tick?=2019 ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), 1546300800000)
            nodes = await core.nodes('[ test:str=foo :tick?=notatime ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), 1546300800000)

    async def test_ast_autoadd(self):

        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            with self.raises(s_exc.AuthDeny):
                opts = {'mode': 'autoadd', 'user': visi.iden}
                nodes = await core.nodes('1.2.3.4 woot.com visi@vertex.link', opts=opts)
            opts = {'mode': 'autoadd'}
            nodes = await core.nodes('1.2.3.4 woot.com visi@vertex.link', opts=opts)
            self.len(3, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:fqdn', 'woot.com'))
            self.eq(nodes[2].ndef, ('inet:email', 'visi@vertex.link'))

    async def test_ast_lookup(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                inet:ipv4=1.2.3.4
                inet:fqdn=foo.bar.com
                inet:email=visi@vertex.link
                inet:url="https://[ff::00]:4443/hehe?foo=bar&baz=faz"
                inet:server=tcp://1.2.3.4:123
                it:sec:cve=CVE-2021-44228
            ]''')
            ndefs = [n.ndef for n in nodes]
            self.len(6, ndefs)

            opts = {'mode': 'lookup'}
            q = '1.2.3.4 foo.bar.com visi@vertex.link https://[ff::00]:4443/hehe?foo=bar&baz=faz 1.2.3.4:123 cve-2021-44228'
            nodes = await core.nodes(q, opts=opts)
            self.eq(ndefs, [n.ndef for n in nodes])

            # check lookup refang
            q = '1(.)2.3.4 foo[.]bar.com visi[at]vertex.link hxxps://[ff::00]:4443/hehe?foo=bar&baz=faz 1(.)2.3.4:123 CVE-2021-44228'
            nodes = await core.nodes(q, opts=opts)
            self.len(6, nodes)
            self.eq(ndefs, [n.ndef for n in nodes])

            q = '1.2.3.4 foo.bar.com visi@vertex.link https://[ff::00]:4443/hehe?foo=bar&baz=faz 1.2.3.4:123 CVE-2021-44228 | [ +#hehe ]'
            nodes = await core.nodes(q, opts=opts)
            self.len(6, nodes)
            self.eq(ndefs, [n.ndef for n in nodes])
            self.true(all(n.tags.get('hehe') is not None for n in nodes))

            # AST object passes through inbound genrs
            await core.nodes('[test:str=beep]')
            beep_opts = {'ndefs': [('test:str', 'beep')], 'mode': 'lookup'}
            nodes = await core.nodes('foo.bar.com | [+#beep]', beep_opts)
            self.len(2, nodes)
            self.eq({('test:str', 'beep'), ('inet:fqdn', 'foo.bar.com')},
                    {n.ndef for n in nodes})
            self.true(all([n.tags.get('beep') for n in nodes]))

            # The lookup mode must get *something* to parse.
            self.len(0, await core.nodes('', opts))

            # The lookup must be *before* anything else, otherwise we
            # parse it as a cmd name.
            with self.raises(s_exc.NoSuchName):
                await core.nodes('[+#thebeforetimes] | foo.bar.com', opts)

            # And it works remotely
            async with core.getLocalProxy() as prox:
                msgs = await s_test.alist(prox.storm('1.2.3.4', opts))
                nodes = [m[1] for m in msgs if m[0] == 'node']
                self.len(1, nodes)
                self.eq(nodes[0][0], ('inet:ipv4', 0x01020304))

    async def test_ast_subq_vars(self):

        async with self.getTestCore() as core:

            # Show a runtime variable being smashed by a subquery
            # variable assignment
            q = '''
                $loc=newp
                [ test:comp=(10, lulz) ]
                { -> test:int [ :loc=haha ] $loc=:loc }
                $lib.print($loc)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('haha', msgs)

            # Show that a computed variable being smashed by a
            # subquery variable assignment with multiple nodes
            # traveling through a subquery.
            await core.nodes('[test:comp=(30, w00t)]')
            await core.nodes('[test:comp=(40, w00t)]')
            await core.nodes('[test:int=30 :loc=sol]')
            await core.nodes('[test:int=40 :loc=mars]')

            q = '''
                test:comp:haha=w00t
                { -> test:int $loc=:loc }
                $lib.print($loc)
                -test:comp
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('sol', msgs)
            self.stormIsInPrint('mars', msgs)

    async def test_ast_runtsafe_bug(self):
        '''
        A regression test where the runtsafety of $newvar was incorrect
        '''
        async with self.getTestCore() as core:
            q = '''
                [test:str=another :hehe=asdf]
                $s = $lib.text("Foo")
                $newvar=:hehe
                -.created
                $s.add("yar {x}", x=$newvar)
                $lib.print($s.str())
            '''
            mesgs = await core.stormlist(q)
            prints = [m[1]['mesg'] for m in mesgs if m[0] == 'print']
            self.eq(['Foo'], prints)

    async def test_ast_variable_props(self):
        async with self.getTestCore() as core:
            # editpropset
            q = '$var=hehe [test:str=foo :$var=heval]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('heval', nodes[0].get('hehe'))

            # filter
            q = '[test:str=heval] test:str $var=hehe +:$var'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('heval', nodes[0].get('hehe'))

            # prop del
            q = '[test:str=foo :tick=2019] $var=tick [-:$var]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.none(nodes[0].get('tick'))

            # pivot
            q = 'test:str=foo $var=hehe :$var -> test:str'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('heval', nodes[0].ndef[1])

            q = '[test:pivcomp=(xxx,foo)] $var=lulz :$var -> *'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('foo', nodes[0].ndef[1])

            # univ set
            q = 'test:str=foo $var=seen [.$var=2019]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].get('.seen'))

            # univ filter (no var)
            q = 'test:str -.created'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # univ filter (var)
            q = 'test:str $var="seen" +.$var'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].get('.seen'))

            # univ delete
            q = 'test:str=foo $var="seen" [ -.$var ] | spin | test:str=foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.none(nodes[0].get('.seen'))

            # Sad paths
            q = '[test:str=newp -.newp]'
            await self.asyncraises(s_exc.NoSuchProp, core.nodes(q))
            q = '$newp=newp [test:str=newp -.$newp]'
            await self.asyncraises(s_exc.NoSuchProp, core.nodes(q))

    async def test_ast_editparens(self):

        async with self.getTestCore() as core:

            q = '[(test:str=foo)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '$val=zoo test:str=foo [(test:str=bar test:str=baz :hehe=$val)]'
            nodes = await core.nodes(q)
            self.len(3, nodes)

            # :hehe doesn't get applied to nodes incoming to editparens
            self.none(nodes[0].get('hehe'))
            self.eq('zoo', nodes[1].get('hehe'))
            self.eq('zoo', nodes[2].get('hehe'))

            with self.raises(s_exc.NoSuchForm):
                await core.nodes('[ (newp:newp=20 :hehe=10) ]')

            # Test for nonsensicalness
            q = 'test:str=baz [(test:str=:hehe +#visi)]'
            nodes = await core.nodes(q)

            self.eq(('test:str', 'baz'), nodes[0].ndef)
            self.eq(('test:str', 'zoo'), nodes[1].ndef)

            self.nn(nodes[1].tags.get('visi'))
            self.none(nodes[0].tags.get('visi'))

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]  [ (inet:dns:a=(vertex.link, $node.value()) +#foo ) ]')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.none(nodes[0].tags.get('foo'))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', 0x01020304)))
            self.nn(nodes[1].tags.get('foo'))

            # test nested
            nodes = await core.nodes('[ inet:fqdn=woot.com ( ps:person="*" :name=visi (ps:contact="*" +#foo )) ]')
            self.eq(nodes[0].ndef, ('inet:fqdn', 'woot.com'))

            self.eq(nodes[1].ndef[0], 'ps:person')
            self.eq(nodes[1].props.get('name'), 'visi')
            self.none(nodes[1].tags.get('foo'))

            self.eq(nodes[2].ndef[0], 'ps:contact')
            self.nn(nodes[2].tags.get('foo'))

            user = await core.auth.addUser('newb')
            with self.raises(s_exc.AuthDeny):
                await core.nodes('[ (inet:ipv4=1.2.3.4 :asn=20) ]', opts={'user': user.iden})

    async def test_subquery_yield(self):

        async with self.getTestCore() as core:
            q = '[test:comp=(10,bar)] { -> test:int}'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('test:comp', nodes[0].ndef[0])

            q = '[test:comp=(10,bar)] yield { -> test:int}'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            kinds = [nodes[0].ndef[0], nodes[1].ndef[0]]
            self.sorteq(kinds, ['test:comp', 'test:int'])

    async def test_ast_var_in_tags(self):
        async with self.getTestCore() as core:
            q = '[test:str=foo +#base.tag1=(2014,?)]'
            await core.nodes(q)

            q = '$var=tag1 #base.$var'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '$var=not #base.$var'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            q = 'test:str $var=tag1 +#base.$var'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str $var=tag1 +#base.$var@=2014'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str $var=tag1 -> #base.$var'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str $var=nope -> #base.$var'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            q = 'test:str [+#base.tag1.foo] $var=tag1 -> #base.$var.*'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str $var=tag2 [+#base.$var]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.sorteq(nodes[0].tags, ('base', 'base.tag1', 'base.tag1.foo', 'base.tag2'))

            q = 'test:str $var=(11) [+#base.$var]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.sorteq(nodes[0].tags, ('base', 'base.11', 'base.tag1', 'base.tag1.foo', 'base.tag2'))
            q = '$foo=$lib.null [test:str=bar +?#base.$foo]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].tags, {})

            with self.raises(s_exc.BadTypeValu) as err:
                q = '$foo=$lib.null [test:str=bar +#base.$foo]'
                await core.nodes(q)
            self.isin('Null value from var $foo', err.exception.errinfo.get('mesg'))

            q = 'function foo() { return() } [test:str=bar +?#$foo()]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].tags, {})

            with self.raises(s_exc.BadTypeValu) as err:
                q = 'function foo() { return() } [test:str=bar +#$foo()]'
                nodes = await core.nodes(q)

    async def test_ast_var_in_deref(self):

        async with self.getTestCore() as core:

            self.none(await core.callStorm('$foo = $lib.null return($foo.bar.baz)'))

            q = '''
            $d = $lib.dict(foo=bar, bar=baz, baz=biz)
            for ($key, $val) in $d {
                [ test:str=$d.$key ]
            }
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            reprs = set(map(lambda n: n.repr(), nodes))
            self.eq(set(['bar', 'baz', 'biz']), reprs)

            q = '''
            $data = $lib.dict(foo=$lib.dict(bar=$lib.dict(woot=final)))
            $varkey=woot
            [ test:str=$data.foo.bar.$varkey ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('final', nodes[0].repr())

            q = '''
            $bar = bar
            $car = car

            $f = var
            $g = tar
            $de = $lib.dict(car=$f, zar=$g)
            $dd = $lib.dict(mar=$de)
            $dc = $lib.dict(bar=$dd)
            $db = $lib.dict(var=$dc)
            $foo = $lib.dict(woot=$db)
            [ test:str=$foo.woot.var.$bar.mar.$car ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('var', nodes[0].repr())

            q = '''
            $data = $lib.dict('vertex project'=foobar)
            $"spaced key" = 'vertex project'
            [ test:str = $data.$"spaced key" ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('foobar', nodes[0].repr())

            q = '''
            $data = $lib.dict('bar baz'=woot)
            $'new key' = 'bar baz'
            [ test:str=$data.$'new key' ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('woot', nodes[0].repr())

            q = '''
            $bottom = $lib.dict(lastkey=synapse)
            $subdata = $lib.dict('bar baz'=$bottom)
            $data = $lib.dict(vertex=$subdata)
            $'new key' = 'bar baz'
            $'over key' = vertex
            [ test:str=$data.$'over key'.$"new key".lastkey ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('synapse', nodes[0].repr())

            q = '''
            $data = $lib.dict(foo=bar)
            $key = nope
            [ test:str=$data.$key ]
            '''
            mesgs = await core.stormlist(q)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.eq(errs[0][0], 'BadTypeValu')

    async def test_ast_array_pivot(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:arrayprop="*" :ints=(1, 2, 3) :strs="foo,bar,baz" :strsnosplit=(a,b,c) ]')
            self.len(1, nodes)

            # Check that subs were added
            nodes = await core.nodes('test:int=1')
            self.len(1, nodes)
            nodes = await core.nodes('test:int=2')
            self.len(1, nodes)
            nodes = await core.nodes('test:int=3')
            self.len(1, nodes)
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            nodes = await core.nodes('test:str=c')
            self.len(1, nodes)

            nodes = await core.nodes('test:arrayprop -> *')
            self.len(9, nodes)

            nodes = await core.nodes('test:arrayprop -> test:int')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints -> test:int')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints :ints -> test:int')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints :ints -> *')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints -> *')
            self.len(9, nodes)

            nodes = await core.nodes('test:arrayprop :ints -> *')
            self.len(3, nodes)

            nodes = await core.nodes('test:int=1 <- * +test:arrayprop')
            self.len(1, nodes)

            nodes = await core.nodes('test:int=2 -> test:arrayprop')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:arrayprop')

            nodes = await core.nodes('test:str=bar -> test:arrayprop')
            self.len(1, nodes)

            # This should work...
            nodes = await core.nodes('test:str=bar -> test:arrayprop:strs')
            self.len(1, nodes)

            nodes = await core.nodes('test:str=b -> test:arrayprop:strsnosplit')
            self.len(1, nodes)

            nodes = await core.nodes('[ test:guid=* :size=2 ]')
            self.len(1, nodes)

            nodes = await core.nodes('test:guid:size=2 :size -> test:arrayprop:ints')
            self.len(1, nodes)

    async def test_ast_pivot_ndef(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ edge:refs=((test:int, 10), (test:str, woot)) ]')
            nodes = await core.nodes('edge:refs -> test:str')
            self.eq(nodes[0].ndef, ('test:str', 'woot'))

            nodes = await core.nodes('[ geo:nloc=((inet:fqdn, woot.com), "34.1,-118.3", now) ]')
            self.len(1, nodes)

            # test a reverse ndef pivot
            nodes = await core.nodes('inet:fqdn=woot.com -> geo:nloc')
            self.len(1, nodes)
            self.eq('geo:nloc', nodes[0].ndef[0])

    async def test_ast_pivot(self):
        # a general purpose pivot test. come on in!
        async with self.getTestCore() as core:
            self.len(0, await core.nodes('[ inet:ipv4=1.2.3.4 ] :asn -> *'))
            self.len(0, await core.nodes('[ inet:ipv4=1.2.3.4 ] :foo -> *'))
            self.len(0, await core.nodes('[ inet:ipv4=1.2.3.4 ] :asn -> inet:asn'))

    async def test_ast_edge_walknjoin(self):

        async with self.getTestCore() as core:

            await core.nodes('[test:str=foo :hehe=bar +(foobar)> { [ test:str=baz ] }]')

            nodes = await core.nodes('test:str=foo --+> *')
            self.len(2, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            self.eq(('test:str', 'baz'), nodes[1].ndef)

            nodes = await core.nodes('test:str=baz <+-- *')
            self.len(2, nodes)
            self.eq(('test:str', 'baz'), nodes[0].ndef)
            self.eq(('test:str', 'foo'), nodes[1].ndef)

            nodes = await core.nodes('test:str=foo -(foobar)+> *')
            self.len(2, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            self.eq(('test:str', 'baz'), nodes[1].ndef)

            nodes = await core.nodes('test:str=baz <+(foobar)- *')
            self.len(2, nodes)
            self.eq(('test:str', 'baz'), nodes[0].ndef)
            self.eq(('test:str', 'foo'), nodes[1].ndef)

            await core.nodes('test:str=foo [ +(coffeeone)> { [ test:str=arabica ] } ]')
            await core.nodes('test:str=foo [ +(coffeetwo)> { [ test:str=robusta ] } ]')
            await core.nodes('[ test:int=28 +(coffeethree)> { test:str=arabica } ]')

            nodes = await core.nodes('test:str=foo -((coffeeone, coffeetwo))+> *')
            self.len(3, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            self.eq(('test:str', 'arabica'), nodes[1].ndef)
            self.eq(('test:str', 'robusta'), nodes[2].ndef)

            await core.nodes('[test:str=neato :hehe=haha +(stuff)> { [inet:ipv4=1.2.3.0/24] }]')
            await core.nodes('[test:str=burrito :hehe=stuff <(stuff)+ { test:str=baz }]')
            await core.nodes('test:str=neato [ <(other)+ { test:str=foo } ]')

            nodes = await core.nodes('$edge=stuff test:str=neato -($edge)+> *')
            self.len(257, nodes)
            self.eq(('test:str', 'neato'), nodes[0].ndef)
            for n in nodes[1:]:
                self.eq('inet:ipv4', n.ndef[0])

            nodes = await core.nodes('test:str=neato | tee { --+> * } { <+(other)- * }')
            self.len(259, nodes)
            self.eq(('test:str', 'neato'), nodes[0].ndef)
            self.eq(('test:str', 'foo'), nodes[-1].ndef)
            self.eq(('test:str', 'neato'), nodes[-2].ndef)

            for n in nodes[1:257]:
                self.eq('inet:ipv4', n.ndef[0])

            await core.nodes('test:str=foo [ +(wat)> {[test:int=12]}]')

            nodes = await core.nodes('test:str=foo -(other)+> test:str')
            self.len(2, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            self.eq(('test:str', 'neato'), nodes[1].ndef)

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str=neato --+> test:str')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str <+-- test:str')

            nodes = await core.nodes('test:str=foo -(*)+> test:str')
            self.len(5, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            ndefs = [n.ndef for n in nodes[1:]]
            self.isin(('test:str', 'arabica'), ndefs)
            self.isin(('test:str', 'robusta'), ndefs)
            self.isin(('test:str', 'baz'), ndefs)
            self.isin(('test:str', 'neato'), ndefs)
            self.notin(('test:int', 12), ndefs)

            nodes = await core.nodes('test:str=foo -(*)+> *')
            self.len(6, nodes)
            self.eq(('test:str', 'foo'), nodes[0].ndef)
            ndefs = [n.ndef for n in nodes[1:]]
            self.isin(('test:int', 12), ndefs)

            nodes = await core.nodes('test:str=arabica <+(*)- test:str')
            self.len(2, nodes)
            self.eq(('test:str', 'arabica'), nodes[0].ndef)
            self.eq(('test:str', 'foo'), nodes[1].ndef)

            nodes = await core.nodes('test:str=arabica <+(*)- *')
            self.len(3, nodes)
            self.eq(('test:str', 'arabica'), nodes[0].ndef)
            ndefs = [n.ndef for n in nodes[1:]]
            self.isin(('test:str', 'foo'), ndefs)
            self.isin(('test:int', 28), ndefs)

            await core.nodes('test:str=arabica [ <(place)+ { [ test:str=coffeebar] } ]')
            nodes = await core.nodes('test:str=arabica <+((place, coffeeone))- *')
            self.len(3, nodes)
            self.eq(('test:str', 'arabica'), nodes[0].ndef)
            self.eq(('test:str', 'coffeebar'), nodes[1].ndef)
            self.eq(('test:str', 'foo'), nodes[2].ndef)

    async def test_ast_lift_filt_array(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:arrayprop:ints*[^=asdf]')

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('array', {'type': None}), {})

            with self.raises(s_exc.BadPropDef):
                await core.addTagProp('array', ('array', {'type': 'int'}), {})

            await core.addFormProp('test:int', '_hehe', ('array', {'type': 'int'}), {})
            nodes = await core.nodes('[ test:int=9999 :_hehe=(1, 2, 3) ]')
            self.len(1, nodes)
            nodes = await core.nodes('test:int=9999 :_hehe -> *')
            self.len(0, nodes)
            await core.nodes('test:int=9999 | delnode')
            await core.delFormProp('test:int', '_hehe')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:arrayprop:newp*[^=asdf]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:comp:hehe*[^=asdf]')

            await core.nodes('[ test:comp=(10,asdf) ]')

            with self.raises(s_exc.BadCmprType):
                await core.nodes('test:comp +:hehe*[^=asdf]')

            nodes = await core.nodes('[ test:arrayprop="*" :ints=(1, 2, 3) ]')
            nodes = await core.nodes('[ test:arrayprop="*" :ints=(100, 101, 102) ]')
            nodes = await core.nodes('test:arrayprop +:ints=$lib.list(1,2,3)')
            self.len(1, nodes)

            nodes = await core.nodes('test:arrayprop:ints=$lib.list(1,2,3)')
            self.len(1, nodes)

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:arrayprop +:newp*[^=asdf]')

            nodes = await core.nodes('test:arrayprop:ints*[=3]')
            self.len(1, nodes)
            self.eq(nodes[0].repr('ints'), ('1', '2', '3'))

            nodes = await core.nodes('test:arrayprop:ints*[ range=(50,100) ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('ints'), (100, 101, 102))

            nodes = await core.nodes('test:arrayprop +:ints*[ range=(50,100) ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('ints'), (100, 101, 102))

            nodes = await core.nodes('test:arrayprop:ints=(1, 2, 3) | limit 1 | [ -:ints ]')
            self.len(1, nodes)

            # test filter case where field is None
            nodes = await core.nodes('test:arrayprop +:ints*[=100]')
            self.len(1, nodes)
            self.eq(nodes[0].get('ints'), (100, 101, 102))

    async def test_ast_array_addsub(self):

        async with self.getTestCore() as core:

            guid = s_common.guid()
            nodes = await core.nodes(f'[ test:arrayprop={guid} ]')

            # test starting with the property unset
            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints+=99 ]')
            self.eq((99,), nodes[0].get('ints'))

            # test that removing a non-existant item is ok...
            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints-=22 ]')

            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints-=99 ]')
            self.eq((), nodes[0].get('ints'))

            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints=(1, 2, 3) ]')

            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints+=4 ]')
            self.eq((1, 2, 3, 4), nodes[0].get('ints'))

            nodes = await core.nodes(f'test:arrayprop={guid} [ :ints-=3 ]')
            self.eq((1, 2, 4), nodes[0].get('ints'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes(f'test:arrayprop={guid} [ :ints+=asdf ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes(f'test:arrayprop={guid} [ :ints-=asdf ]')

            await core.nodes(f'test:arrayprop={guid} [ :ints?-=asdf ]')
            self.eq((1, 2, 4), nodes[0].get('ints'))

            await core.nodes(f'test:arrayprop={guid} [ :ints?+=asdf ]')
            self.eq((1, 2, 4), nodes[0].get('ints'))

            # ensure that we get a proper exception when using += (et al) on non-array props
            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn+=10 ]')

            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn?+=10 ]')

            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn-=10 ]')

            with self.raises(s_exc.StormRuntimeError):
                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn?-=10 ]')

    async def test_ast_del_array(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:arrayprop="*" :ints=(1, 2, 3) ]')
            nodes = await core.nodes('test:arrayprop [ -:ints ]')

            self.len(1, nodes)
            self.none(nodes[0].get('ints'))

            nodes = await core.nodes('test:int=2 -> test:arrayprop')
            self.len(0, nodes)

            nodes = await core.nodes('test:arrayprop:ints=(1, 2, 3)')
            self.len(0, nodes)

    async def test_ast_univ_array(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 .univarray=(1, 2, 3) ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('.univarray'), (1, 2, 3))

            nodes = await core.nodes('.univarray*[=2]')
            self.len(1, nodes)

            nodes = await core.nodes('test:int=10 [ .univarray=(1, 3) ]')
            self.len(1, nodes)

            nodes = await core.nodes('.univarray*[=2]')
            self.len(0, nodes)

            nodes = await core.nodes('test:int=10 [ -.univarray ]')
            self.len(1, nodes)

            nodes = await core.nodes('.univarray')
            self.len(0, nodes)

    async def test_ast_embed_compute(self):
        # =${...} assigns a query object to a variable
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 test:int=20 ]  $q=${#foo.bar}')
            self.len(2, nodes)

    async def test_ast_subquery_value(self):
        '''
        Test subqueries as rvals in property sets, filters, lifts
        '''
        async with self.getTestCore() as core:

            # test property assignment with subquery value
            await core.nodes('[(ou:industry=* :name=foo)] [(ou:industry=* :name=bar)] [+#sqa]')
            nodes = await core.nodes('[ ou:org=* :alias=visiacme :industries={ou:industry#sqa}]')
            self.len(1, nodes)
            self.len(2, nodes[0].get('industries'))

            nodes = await core.nodes('[ou:campaign=* :goal={[ou:goal=* :name="paperclip manufacturing" ]} ]')
            self.len(1, nodes)
            # Make sure we're not accidentally adding extra nodes
            nodes = await core.nodes('ou:goal')
            self.len(1, nodes)
            self.nn(nodes[0].get('name'))

            nodes = await core.nodes('[ ps:contact=* :org={ou:org:alias=visiacme}]')
            self.len(1, nodes)
            self.nn(nodes[0].get('org'))

            nodes = await core.nodes('ou:org:alias=visiacme')
            self.len(1, nodes)
            self.len(2, nodes[0].get('industries'))

            nodes = await core.nodes('ou:org:alias=visiacme [ :industries-={ou:industry:name=foo} ]')
            self.len(1, nodes)
            self.len(1, nodes[0].get('industries'))

            nodes = await core.nodes('ou:org:alias=visiacme [ :industries+={ou:industry:name=foo} ]')
            self.len(1, nodes)
            self.len(2, nodes[0].get('industries'))

            await core.nodes('[ it:dev:str=a it:dev:str=b ]')
            q = "ou:org:alias=visiacme [ :name={it:dev:str if ($node='b') {return(penetrode)}} ]"
            nodes = await core.nodes(q)
            self.len(1, nodes)

            nodes = await core.nodes('[ test:arrayprop=* :strs={return ($lib.list(a,b,c,d))} ]')
            self.len(1, nodes)
            self.len(4, nodes[0].get('strs'))

            # Running the query again ensures that the ast hasattr memoizing works
            nodes = await core.nodes(q)
            self.len(1, nodes)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:org:alias=visiacme [ :name={if (0) {return(penetrode)}} ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:org:alias=visiacme [ :name={} ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:org:alias=visiacme [ :name={[it:dev:str=hehe it:dev:str=haha]} ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:org:alias=visiacme [ :industries={[inet:ipv4=1.2.3.0/24]} ]')

            await core.nodes('ou:org:alias=visiacme [ -:name]')
            nodes = await core.nodes('ou:org:alias=visiacme [ :name?={} ]')
            self.notin('name', nodes[0].props)

            nodes = await core.nodes('ou:org:alias=visiacme [ :name?={[it:dev:str=hehe it:dev:str=haha]} ]')
            self.notin('name', nodes[0].props)

            nodes = await core.nodes('ou:org:alias=visiacme [ :industries?={[inet:ipv4=1.2.3.0/24]} ]')
            self.notin('name', nodes[0].props)

            # Filter by Subquery value

            await core.nodes('[it:dev:str=visiacme]')
            nodes = await core.nodes('ou:org +:alias={it:dev:str=visiacme}')
            self.len(1, nodes)

            nodes = await core.nodes('ou:org +:alias={return(visiacme)}')
            self.len(1, nodes)

            nodes = await core.nodes('test:arrayprop +:strs={return ((a,b,c,d))}')
            self.len(1, nodes)

            with self.raises(s_exc.BadTypeValu):
                nodes = await core.nodes('ou:org +:alias={it:dev:str}')

            # Lift by Subquery value

            nodes = await core.nodes('ou:org:alias={it:dev:str=visiacme}')
            self.len(1, nodes)

            nodes = await core.nodes('test:arrayprop:strs={return ((a,b,c,d))}')
            self.len(1, nodes)

            nodes = await core.nodes('ou:org:alias={return(visiacme)}')
            self.len(1, nodes)

            with self.raises(s_exc.BadTypeValu):
                nodes = await core.nodes('ou:org:alias={it:dev:str}')

    async def test_lib_ast_module(self):

        otherpkg = {
            'name': 'foosball',
            'version': '0.0.1',
            'synapse_minversion': [2, 144, 0],
            'synapse_version': '>=2.8.0,<3.0.0',
        }

        stormpkg = {
            'name': 'stormpkg',
            'version': '1.2.3',
            'synapse_minversion': [2, 144, 0],
            'synapse_version': '>=2.8.0,<3.0.0',
            'commands': (
                {
                 'name': 'pkgcmd.old',
                 'storm': '$lib.print(hi)',
                },
            ),
        }

        stormpkgnew = {
            'name': 'stormpkg',
            'version': '1.2.4',
            'synapse_minversion': [2, 144, 0],
            'synapse_version': '>=2.8.0,<3.0.0',
            'commands': (
                {
                 'name': 'pkgcmd.new',
                 'storm': '$lib.print(hi)',
                },
            ),
        }

        jsonpkg = {
            'name': 'jsonpkg',
            'version': '1.2.3',
            'synapse_minversion': [2, 144, 0],
            'synapse_version': '>=2.8.0,<3.0.0',
            'docs': (
                {
                 'title': 'User Guide',
                 'content': '# User Guide\n\nSuper cool guide.',
                },
            )
        }

        async with self.getTestCore() as core:

            await core.addStormPkg(foo_stormpkg)

            nodes = await core.nodes('foo.bar')

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 50))

            nodes = await core.nodes('test.nodes')
            self.len(2, nodes)
            self.eq({('test:str', 'asdf'), ('test:str', 'qwer')},
                    {n.ndef for n in nodes})

            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('foo                             : 0.0.1', msgs)

            msgs = await core.stormlist('pkg.del asdf')
            self.stormIsInPrint('No package names match "asdf". Aborting.', msgs)

            await core.addStormPkg(otherpkg)
            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('foosball', msgs)

            msgs = await core.stormlist('pkg.del foo')
            self.stormIsInPrint('Multiple package names match "foo". Aborting.', msgs)

            msgs = await core.stormlist('pkg.del foosball')
            self.stormIsInPrint('Removing package: foosball', msgs)

            msgs = await core.stormlist('pkg.del foo')
            self.stormIsInPrint('Removing package: foo', msgs)

            # Direct add via stormtypes
            await core.stormlist('$lib.pkg.add($pkg)',
                                 opts={'vars': {'pkg': stormpkg}})
            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('stormpkg', msgs)

            # Make sure a JSON package loads
            jsonpkg = json.loads(json.dumps(jsonpkg))
            await core.stormlist('$lib.pkg.add($pkg)',
                                 opts={'vars': {'pkg': jsonpkg}})
            msgs = await core.stormlist('pkg.list')
            self.stormIsInPrint('jsonpkg', msgs)

            with self.raises(s_exc.NoSuchName):
                nodes = await core.nodes('test.nodes')

            visi = await core.auth.addUser('visi')

            async with core.getLocalProxy(user='visi') as asvisi:

                # Test permissions
                msgs = await s_test.alist(asvisi.storm('$lib.pkg.del(stormpkg)'))
                errs = [m for m in msgs if m[0] == 'err']
                self.len(1, errs)
                self.eq(errs[0][1][0], 'AuthDeny')

                await core.addUserRule(visi.iden, (True, ('pkg', 'del')))

                await s_test.alist(asvisi.storm('$lib.pkg.del(stormpkg)'))

                mesgs = await core.stormlist('pkg.list')
                print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'print'])
                self.notin('stormpkg', print_str)

                msgs = await s_test.alist(asvisi.storm('$lib.pkg.add($pkg)',
                                                       opts={'vars': {'pkg': stormpkg}}))
                errs = [m for m in msgs if m[0] == 'err']
                self.len(1, errs)
                self.eq(errs[0][1][0], 'AuthDeny')

                await core.addUserRule(visi.iden, (True, ('pkg', 'add')))

                await s_test.alist(asvisi.storm('$lib.pkg.add($pkg)',
                                                opts={'vars': {'pkg': stormpkg}}))

                msgs = await core.stormlist('pkg.list')
                self.stormIsInPrint('stormpkg', msgs)

            # Add a newer version of a package
            await core.stormlist('$lib.pkg.add($pkg)',
                                 opts={'vars': {'pkg': stormpkgnew}})
            msgs = await core.stormlist('help pkgcmd')
            self.stormIsInPrint('pkgcmd.new', msgs)
            self.stormNotInPrint('pkgcmd.old', msgs)

            msgs = await core.stormlist('pkg.docs asdf')
            self.stormIsInWarn('Package (asdf) not found!', msgs)

            msgs = await core.stormlist('pkg.docs stormpkg')
            self.stormIsInPrint('Package (stormpkg) contains no documentation.', msgs)

            msgs = await core.stormlist('pkg.docs jsonpkg')
            self.stormIsInPrint('# User Guide\n\nSuper cool guide.', msgs)

    async def test_function(self):
        async with self.getTestCore() as core:
            await core.addStormPkg(foo_stormpkg)

            # No arguments
            q = '''
            function hello() {
                return ("hello")
            }
            $retn=$hello()
            $lib.print('retn is: {retn}', retn=$retn)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('retn is: hello', msgs)

            # Simple echo function
            q = '''
            function echo(arg) {
                return ($arg)
            }
            [(test:str=foo) (test:str=bar)]
            $retn=$echo($node.value())
            $lib.print('retn is: {retn}', retn=$retn)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('retn is: foo', msgs)
            self.stormIsInPrint('retn is: bar', msgs)

            # Return value from a function based on a node value
            # inside of the function
            q = '''
            function echo(arg) {
                $lib.print('arg is {arg}', arg=$arg)
                [(test:str=1234) (test:str=5678)]
                return ($node.value())
            }
            [(test:str=foo) (test:str=bar)]
            $retn=$echo($node.value())
            $lib.print('retn is: {retn}', retn=$retn)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('arg is foo', msgs)
            self.stormIsInPrint('arg is bar', msgs)
            self.stormIsInPrint('retn is: 1234', msgs)

            # Return values may be conditional
            q = '''function cond(arg) {
                if $arg {
                    return ($arg)
                } else {
                    // No action....
                }
            }
            [(test:int=0) (test:int=1)]
            $retn=$cond($node.value())
            $lib.print('retn is: {retn}', retn=$retn)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('retn is: $lib.null', msgs)
            self.stormIsInPrint('retn is: 1', msgs)

            # Allow plumbing through args as keywords
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint('hello', 'world', arg3='goodbye')
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('arg1: hello', msgs)
            self.stormIsInPrint('arg2: world', msgs)
            self.stormIsInPrint('arg3: goodbye', msgs)
            # Allow plumbing through args out of order
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint(arg3='goodbye', arg1='hello', arg2='world')
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('arg1: hello', msgs)
            self.stormIsInPrint('arg2: world', msgs)
            self.stormIsInPrint('arg3: goodbye', msgs)

            # Basic function chaining
            q = '''
            function inner() {
                $lib.print("inner vertex")
                return ("foobarbazbiz")
            }

            function outer() {
                return ($inner())
            }

            $output = $outer()
            $lib.print($output)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('inner vertex', msgs)
            self.stormIsInPrint('foobarbazbiz', msgs)

            # return a directly called function
            q = '''
            function woot(arg1) {
                return ( $($arg1 + 1) )
            }

            function squee(arg2) {
                return ($woot($arg2))
            }
            $output = $squee(17)
            $lib.print('output is {a}', a=$output)
            '''

            msgs = await core.stormlist(q)
            self.stormIsInPrint('output is 18', msgs)

            # recursive functions
            q = '''
            function recurse(cond, count) {
                if $( $cond = 15 ) {
                    return ($count)
                }
                return ($recurse( $($cond - 1), $($count + 1) ))
            }
            $output = $recurse(21, 0)
            $lib.print('final recursive output is {out}', out=$output)
            '''

            msgs = await core.stormlist(q)
            self.stormIsInPrint('final recursive output is 6', msgs)

            # return a function (not a value, but a ref to the function itself)
            q = '''
            function toreturn() {
                $lib.time.sleep(1)
                $lib.print('[{now}, "toreturn called"]', now=$($lib.time.now()))
                $lib.time.sleep(1)
                return ("foobar")
            }

            function wrapper() {
                return ($toreturn)
            }

            $func = $wrapper()
            $lib.print('[{now}, "this should be first"]', now=$($lib.time.now()))
            $output = $func()
            $lib.print('[{now}, "got {out}"]', now=$($lib.time.now()), out=$output)
            '''
            msgs = await core.stormlist(q)
            prints = list(filter(lambda m: m[0] == 'print', msgs))
            self.eq(len(prints), 3)

            jmsgs = list(map(lambda m: json.loads(m[1]['mesg']), prints))
            omsgs = sorted(jmsgs, key=lambda m: m[0])
            self.eq(omsgs[0][1], 'this should be first')
            self.eq(omsgs[1][1], 'toreturn called')
            self.eq(omsgs[2][1], 'got foobar')

            # module level global variables should be accessible to chained functions
            q = '''
            $biz = 0

            function bar() {
                $var1 = "subwoot"
                $var2 = "neato burrito"
                $biz = $( $biz + 10 )
                $lib.print($var2)
                return ("done")
            }

            function boop() {
                $retz = $bar()
                return ($retz)
            }

            function foo() {
                $var1 = "doublewoot"
                $retn = $bar()
                $lib.print($var1)
                return ($retn)
            }
            $lib.print($foo())
            $lib.print($boop())
            $lib.print("biz is now {biz}", biz=$biz)
            '''
            msgs = await core.stormlist(q)
            prints = list(filter(lambda m: m[0] == 'print', msgs))
            self.len(6, prints)
            self.stormIsInPrint("neato burrito", msgs)
            self.stormIsInPrint("done", msgs)
            self.stormIsInPrint("doublewoot", msgs)
            self.stormIsInPrint("biz is now 20", msgs)

            # test that the functions in a module don't pollute our own runts
            with self.raises(s_exc.NoSuchVar):
                await core.nodes('''
                    $test=$lib.import(test)
                    $lib.print($outer("1337"))
                ''')

            # make sure can set variables to the results of other functions in the same query
            q = '''
            function baz(arg1) {
                $lib.print('arg1={a}', a=$arg1)
                return ($arg1)
            }
            function bar(arg2) {
                $lib.print('arg2={a}', a=$arg2)
                $retn = $baz($arg2)
                return ($retn)
            }
            $foo = $bar("hehe")
            $lib.print($foo)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('hehe', msgs)
            self.stormIsInPrint('arg1=hehe', msgs)
            self.stormIsInPrint('arg2=hehe', msgs)

            # call an import and have it's module local variables be mapped in to its own scope
            q = '''
            $test = $lib.import(importnest)
            $haha = $test.outer($lib.false, $(33))
            $lib.print($haha)
            $hehe = $test.outer($lib.true, $(17))
            $lib.print($hehe)
            $retn = $lib.import(importnest).outer($lib.true, $(90))
            $lib.print($retn)
            $lib.print("counter is {c}", c=$test.counter)
            '''
            msgs = await core.stormlist(q)
            prints = list(filter(lambda m: m[0] == 'print', msgs))
            self.len(10, prints)
            self.stormIsInPrint('counter is 0', msgs)
            self.stormIsInPrint('foobar is 33', msgs)
            self.stormIsInPrint('(Run: 0) we got back bar', msgs)
            self.stormIsInPrint('counter is 33', msgs)
            self.stormIsInPrint('foobar is 50', msgs)
            self.stormIsInPrint('(Run: 33) we got back foo', msgs)
            self.stormIsInPrint('counter is 0', msgs)
            self.stormIsInPrint('foobar is 90', msgs)
            self.stormIsInPrint('(Run: 0) we got back foo', msgs)

            # yields all the way down, no imports
            q = '''
            $count = 0
            function baz(arg3) {
                [ test:str = $arg3 ]
                $count = $( $count + 1)
                [ test:str = "cool" ]
            }

            function bar(arg2) {
                yield $baz($arg2)
            }

            function foo(arg1) {
                yield $bar($arg1)
            }

            yield $foo("bleeeergh")
            yield $foo("bloooop")
            $lib.print("nodes added: {c}", c=$count)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('nodes added: 1', msgs)
            self.stormIsInPrint('nodes added: 2', msgs)

            # make sure local variables don't pollute up

            q = '''
            $global = $(346)
            function bar(arg1) {
                $lib.print("arg1 is {arg}", arg=$arg1)
                return ($arg1)
            }
            function foo(arg2) {
                $wat = $( $arg2 + 99 )
                $retn = $bar($wat)
                return ($retn)
            }
            $lib.print("retn is {ans}", ans=$( $foo($global)) )
            '''
            msgs = await core.stormlist(q)
            prints = list(filter(lambda m: m[0] == 'print', msgs))
            self.len(2, prints)
            self.stormIsInPrint('arg1 is 445', msgs)
            self.stormIsInPrint('retn is 445', msgs)

            # make sure we can't override the base lib object
            q = '''
            function wat(arg1) {
                $lib.print($arg1)
                $lib.print("We should have inherited the one true lib")
                return ("Hi :)")
            }
            function override() {
                $lib = "The new lib"
                $retn = $wat($lib)
                return ($retn)
            }

            $lib.print($override())
            $lib.print("NO OVERRIDES FOR YOU")
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('The new lib', msgs)
            self.stormIsInPrint('We should have inherited the one true lib', msgs)
            self.stormIsInPrint('Hi :)', msgs)
            self.stormIsInPrint('NO OVERRIDES FOR YOU', msgs)

            # yields across an import boundary
            q = '''
            $test = $lib.import(yieldsforever)
            yield $test.yieldme("yieldsforimports")
            $lib.print($node.value())
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('yieldsforimports', msgs)

            # Too few args are problematic
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint('hello', 'world')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.isin('missing required argument arg3', erfo[1][1].get('mesg'))

            # Too few args are problematic - kwargs edition
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint(arg1='hello', arg2='world')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.isin('missing required argument arg3', erfo[1][1].get('mesg'))

            # too many arguments
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint('hello', 'world', arg3='world', arg4='newp')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.isin('takes 3 arguments', erfo[1][1].get('mesg'))

            # Bad: unused kwargs
            q = '''
            $test=$lib.import(testdefault)
            $haha=$test.doit('hello', arg2='world', arg99='newp')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.isin('got unexpected keyword argument: arg99', erfo[1][1].get('mesg'))

            # Bad: kwargs which duplicate a positional arg
            q = '''
            $test=$lib.import(testdefault)
            $haha=$test.doit('hello', 'world', arg1='hello')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.isin('got multiple values for parameter', erfo[1][1].get('mesg'))

            # Repeated kwargs are fatal
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint(arg3='goodbye', arg1='hello', arg1='foo', arg2='world')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Positional argument after kwargs disallowed
            q = '''
            $test=$lib.import(test)
            $haha=$test.pprint(arg3='goodbye', arg1='hello', arg1='foo', 'world')
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Default parameter values work
            q = '''
            $test=$lib.import(testdefault)
            return ($test.doit('foo', arg3='goodbye', arg2='world'))
            '''
            retn = await core.callStorm(q)
            self.eq(('foo', 'world', 'goodbye', 42), retn)

            # Can't have positional parameter after default parameter in function definition
            q = 'function badargs(def=foo, bar) {}'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Can't have positional argument after kwarg argument in function *call*
            q = '''
            $test=$lib.import(testdefault)
            return ($test.doit('foo', arg3='goodbye', 'world'))
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Can't have same positional parameter twice in function definition
            q = 'function badargs(x=42, x=43) {}'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Can't have same kwarg parameter twice in function definition
            q = 'function badargs(x=foo, x=foo) {}'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'BadSyntax')

            # Can't use a non-runtsafe variable as a default
            q = '[test:str=foo] function badargs(x=foo, y=$node) {}'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')

            # test variables as parameter defaults
            self.eq(42, await core.callStorm('$val=(42) function x(parm1=$val) { return($parm1) } return($x())'))

            # force sleep in iter with ret
            q = 'function x() { [ inet:asn=2 ] if ($node.value() = (3)) { return((3)) } } $x()'
            self.len(0, await core.nodes(q))

            # test Function.isRuntSafe
            self.len(0, await core.nodes('init { function x() { return((0)) } }'))

            # Can't use a mutable variable as a default
            q = '$var=$lib.list(1,2,3) function badargs(x=foo, y=$var) {} $badargs()'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')

            # libs are not mutable:  OK to have as default parameter
            self.len(0, await core.nodes('$val=$lib function x(parm1=$val) { return($parm1) }'))

            # bytes are OK
            q = '$val=$lib.base64.decode("dmlzaQ==") function x(parm1=$val) { return($parm1) }'
            self.len(0, await core.nodes(q))

            self.eq('foo', await core.callStorm('return($lib.str.format("{func}", func=foo))'))

            msgs = await core.stormlist('$lib.null()')
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.stormIsInErr("'null' object is not callable: lib.null()", msgs)

            msgs = await core.stormlist('$foo=bar $foo()')
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.stormIsInErr("'str' object is not callable: foo()", msgs)

            msgs = await core.stormlist('$lib()')
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.stormIsInErr("'lib' object is not callable: lib()", msgs)

    async def test_ast_function_scope(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''

                function foo (x) {
                    [ test:str=$x ]
                }

                yield $foo(asdf)

            ''')

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'asdf'))

            scmd = {
                'name': 'foocmd',
                'storm': '''

                    function lulz (lulztag) {
                        [ test:str=$lulztag ]
                    }

                    for $tag in $node.tags() {
                        yield $lulz($tag)
                    }

                ''',
            }

            await core.setStormCmd(scmd)

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 +#visi ] | foocmd')
            self.eq(nodes[0].ndef, ('test:str', 'visi'))
            self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

            msgs = await core.stormlist('''
                function lolol() {
                    $lib = "pure lulz"
                    $lolol = "don't do this"
                    return ($lolol)
                }
                $neato = 0
                $myvar = $lolol()
                $lib.print($myvar)
            ''')
            self.stormIsInPrint("don't do this", msgs)

    async def test_ast_setitem(self):

        async with self.getTestCore() as core:

            q = '''
                $x = asdf
                $y = $lib.dict()

                $y.foo = bar
                $y."baz faz" = hehe
                $y.$x = qwer

                for ($name, $valu) in $y {
                    [ test:str=$name test:str=$valu ]
                }
            '''
            nodes = await core.nodes(q)
            self.len(6, nodes)
            self.eq(nodes[0].ndef[1], 'foo')
            self.eq(nodes[1].ndef[1], 'bar')
            self.eq(nodes[2].ndef[1], 'baz faz')
            self.eq(nodes[3].ndef[1], 'hehe')
            self.eq(nodes[4].ndef[1], 'asdf')
            self.eq(nodes[5].ndef[1], 'qwer')

            # non-runtsafe test
            q = '''$dict = $lib.dict()
            [(test:str=key1 :hehe=val1) (test:str=key2 :hehe=val2)]
            $key=$node.value()
            $dict.$key=:hehe
            fini {
                $lib.fire(event, dict=$dict)
            }
            '''
            mesgs = await core.stormlist(q)
            stormfire = [m for m in mesgs if m[0] == 'storm:fire']
            self.len(1, stormfire)
            self.eq(stormfire[0][1].get('data').get('dict'),
                    {'key1': 'val1', 'key2': 'val2'})

            # The default StormType does not support item assignment
            q = '''
            $set=$lib.set()
            $set.foo="bar"
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.eq(erfo[1][1].get('mesg'), 'Set does not support assignment.')

    async def test_ast_initfini(self):

        async with self.getTestCore() as core:

            q = '''
                init { $x = $(0) }

                [ test:int=$x ]

                init { $x = $( $x + 2 ) $lib.fire(lulz, x=$x) }

                [ test:int=$x ]

                [ +#foo ]

                fini { $lib.print('xfini: {x}', x=$x) }
            '''

            msgs = await core.stormlist(q)

            types = [m[0] for m in msgs if m[0] in ('node', 'print', 'storm:fire')]
            self.eq(types, ('storm:fire', 'node', 'node', 'print'))

            nodes = [m[1] for m in msgs if m[0] == 'node']

            self.eq(nodes[0][0], ('test:int', 0))
            self.eq(nodes[1][0], ('test:int', 2))

            nodes = await core.nodes('init { [ test:int=20 ] }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 20))

            # init and fini blocks may also yield nodes
            q = '''
            init {
                [(test:str=init1 :hehe=hi)]
            }
            $hehe=:hehe
            [test:str=init2 :hehe=$hehe]
            '''
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'init1'))
            self.eq(nodes[0].get('hehe'), 'hi')
            self.eq(nodes[1].ndef, ('test:str', 'init2'))
            self.eq(nodes[1].get('hehe'), 'hi')

            # Non-runtsafe init fails to execute
            q = '''
            test:str^=init +:hehe $hehe=:hehe
            init {
                [test:str=$hehe]
            }
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.eq(erfo[1][1].get('mesg'), 'Init block query must be runtsafe')

            # Runtsafe init works and can yield nodes, this has inbound nodes as well
            q = '''
            test:str^=init
            $hehe="const"
            init {
                [test:str=$hehe]
            }
            '''
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'const'))
            self.eq(nodes[1].ndef, ('test:str', 'init1'))
            self.eq(nodes[2].ndef, ('test:str', 'init2'))

            # runtsafe fini with a node example which works
            q = '''
            [test:str=fini1 :hehe=bye]
            $hehe="hehe"
            fini {
                [(test:str=fini2 :hehe=$hehe)]
            }
            '''
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'fini1'))
            self.eq(nodes[0].get('hehe'), 'bye')
            self.eq(nodes[1].ndef, ('test:str', 'fini2'))
            self.eq(nodes[1].get('hehe'), 'hehe')

            # Non-runtsafe fini example which fails
            q = '''
            [test:str=fini3 :hehe="number3"]
            $hehe=:hehe
            fini {
                [(test:str=fini4 :hehe=$hehe)]
            }
            '''
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'StormRuntimeError')
            self.eq(erfo[1][1].get('mesg'), 'Fini block query must be runtsafe')

            # Tally use - case example for counting
            q = '''
            init {
                $tally = $lib.stats.tally()
            }
            test:int $tally.inc('node') | spin |
            fini {
                for ($name, $total) in $tally {
                    $lib.fire(name=$name, total=$total)
                }
            }
            '''
            msgs = await core.stormlist(q)
            firs = [m for m in msgs if m[0] == 'storm:fire']
            self.len(1, firs)
            evnt = firs[0]
            self.eq(evnt[1].get('data'), {'total': 3})

    async def test_ast_emptyblock(self):

        async with self.getTestCore() as core:
            q = '''
            empty {
                $lib.print("a fancy but empty block")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('a fancy but empty block', msgs)

            q = '''
            empty {
                [test:str=neato]
            }
            [ :hehe=stuff ]
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            props = nodes[0][1]['props']
            self.eq('stuff', props.get('hehe'))

            q = '''
                empty {
                    $lib.print("some empty block")
                }
                [test:str=synapse]
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.stormIsInPrint('some empty block', msgs)

            q = '''
                for $i in $lib.range(10) {
                    if ($i > 5) {
                        [test:int=$i]
                    }
                } | empty { $lib.print(`count is {$i}`) }
            '''
            msgs = await core.stormlist(q)
            self.stormNotInPrint('count is', msgs)

            q = '''
                for $i in $lib.range(10) {
                    $lib.print(`count is {$i}`)
                } | empty { $lib.print(`pipeline is empty`) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('count is', msgs)
            self.stormIsInPrint('pipeline is empty', msgs)

            q = '''
            [test:str=burrito]
            empty {
                [test:str=awesome]
            }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:str', 'burrito'), nodes[0][0])

            q = '''
            $lib.print("OH YEA")
            empty {
                [test:str=possum]
            }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:str', 'possum'), nodes[0][0])
            self.stormIsInPrint('OH YEA', msgs)

            q = '''
            empty {
                [test:str=foo]
            }

            empty {
                [test:bstr=bar]
            }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:str', 'foo'), nodes[0][0])

            q = '''
            empty {
                $lib.print('call me')
            }

            $lib.print('ishmael')

            empty {
                $lib.print('some years ago')
            }

            [test:str="moby dick"]

            empty {
                $lib.print('never mind')
            }

            empty {
                $lib.print('how long')
            }

            [ :hehe=haha ]
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('call me', msgs)
            self.stormIsInPrint('ishmael', msgs)
            self.stormIsInPrint('some years ago', msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:str', 'moby dick'), nodes[0][0])
            self.eq('haha', nodes[0][1]['props']['hehe'])
            self.stormNotInPrint('never mind', msgs)
            self.stormNotInPrint('how long', msgs)

            q = '''
            function foo(x) {
                empty {
                    $lib.print($x)
                }

                return()
            }

            [test:str=biz :hehe=baz]
            $foo(:hehe)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("baz", msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:str', 'biz'), nodes[0][0])

            q = '''
            [test:str=coffee :hehe=pourover] $beep=:hehe | spin | empty { $lib.print("blorp") }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(0, nodes)
            self.stormIsInPrint('blorp', msgs)

            q = '''
            [test:str=latte :hehe=milk] $beep=:hehe | spin | empty { $lib.print($beep) }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(0, nodes)
            self.stormIsInErr('Empty block query must be runtsafe', msgs)

            q = '''
            function foo() {
                for $x in $lib.range(10) {
                    emit $x
                }
            }

            for $data in $foo() {
                if ($data > 10000) {
                    [test:int=$data]
                }
            }

            empty {
                [test:int=1000]
            }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:int', 1000), nodes[0][0])

            q = '''
            empty {
                [test:int=12345]
            }
            '''
            idens = [nodes[0][1]['iden'],]
            msgs = await core.stormlist(q, opts={'idens': idens})
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:int', 1000), nodes[0][0])

            q = '''
            function foo() {
                empty {
                    $lib.print('foobarbaz')
                }
                [test:int=12]
            }

            yield $foo()
            empty {
                $lib.print('neato')
            }
            '''
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('test:int', 12), nodes[0][0])
            self.stormIsInPrint('foobarbaz', msgs)
            self.stormNotInPrint('neato', msgs)

            q = '''
            function foo() {
                for $x in $lib.range(2) {
                    emit $x
                    empty {
                        $lib.print(`count is {$x}`)
                    }
                }
            }
            for $x in $foo() {
                [test:int=$x]
            }
            '''
            msgs = await core.stormlist(q)
            order = [m[0] for m in msgs]
            nodes = [m[1] for m in msgs if m[0] == 'node']
            ndefs = [n[0] for n in nodes]

            self.len(2, nodes)
            self.eq(order, ['init', 'node:edits', 'node', 'print', 'node:edits', 'node', 'print', 'fini'])
            self.isin(('test:int', 0), ndefs)
            self.isin(('test:int', 1), ndefs)

            self.stormIsInPrint('count is 0', msgs)
            self.stormIsInPrint('count is 1', msgs)

    async def test_ast_cmdargs(self):

        async with self.getTestCore() as core:

            scmd = {
                'name': 'foo',
                'cmdargs': (
                    ('--bar', {}),
                ),
                'storm': '''
                    $ival = $lib.cast(ival, $cmdopts.bar)
                    [ test:str=1234 +#foo=$ival ]
                ''',
            }

            await core.setStormCmd(scmd)

            nodes = await core.nodes('foo --bar (2020,2021) | +#foo@=202002')
            self.len(1, nodes)

            scmd = {
                'name': 'baz',
                'cmdargs': (
                    ('--faz', {}),
                ),
                'storm': '''
                    // subquery forces per-node evaluation of even runt safe vars
                    {
                        $ival = $lib.cast(ival, $cmdopts.faz)
                        [ test:str=beep +#foo=$ival ]
                    }
                ''',
            }

            await core.setStormCmd(scmd)

            await core.nodes('[ test:int=5678 +#foo=(2018, 2021) ]')
            await core.nodes('[ test:int=1111 +#foo=(1977, 2019) ]')

            nodes = await core.nodes('test:int | baz --faz #foo')
            self.len(2, nodes)

            nodes = await core.nodes('test:str +#foo@=1984 +#foo@=202002')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'beep'))

    async def test_ast_pullone(self):

        async def genr():
            yield 1
            yield 2
            yield 3

        igen, mpty = await s_ast.pullone(genr())
        vals = [x async for x in igen]
        self.eq((1, 2, 3), vals)
        self.false(mpty)

        data = {}

        async def empty():
            data['executed'] = True
            if 0:
                yield None

        igen, mpty = await s_ast.pullone(empty())
        vals = [x async for x in igen]
        self.eq([], vals)
        self.true(data.get('executed'))
        self.true(mpty)

        async def hasone():
            yield 1

        igen, mpty = await s_ast.pullone(hasone())
        vals = [x async for x in igen]
        self.eq((1,), vals)
        self.false(mpty)

    async def test_ast_expr(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('if (true) { [inet:ipv4=1.2.3.4] }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('if (false) { [inet:ipv4=1.2.3.4] }')
            self.len(0, nodes)

            nodes = await core.nodes('[ test:int=(18 + 2) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 20))

            nodes = await core.nodes('[ test:hugenum=(1.23 + 4.56) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:hugenum', '5.79'))\

            nodes = await core.nodes('[ test:hugenum=$lib.cast(float, 5.79) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:hugenum', '5.79'))

            self.eq(2.23, await core.callStorm('return((1.23 + 1))'))
            self.eq(2.43, await core.callStorm('return((1.23 + 1.2))'))
            self.eq(2.2, await core.callStorm('return((1 + 1.2))'))

            self.eq(0.23, await core.callStorm('return((1.23 - 1))'))
            self.eq(0.03, await core.callStorm('return((1.23 - 1.2))'))
            self.eq(-0.2, await core.callStorm('return((1 - 1.2))'))

            self.eq(1.23, await core.callStorm('return((1.23 * 1))'))
            self.eq(1.476, await core.callStorm('return((1.23 * 1.2))'))
            self.eq(1.2, await core.callStorm('return((1 * 1.2))'))

            self.eq(1.23, await core.callStorm('return((1.23 / 1))'))
            self.eq(1.025, await core.callStorm('return((1.23 / 1.2))'))
            self.eq(2.5, await core.callStorm('return((3 / 1.2))'))

            self.eq(8, await core.callStorm('return((2 ** 3))'))
            self.eq(4.84, await core.callStorm('return((2.2 ** 2))'))
            self.eq(2 ** 2.4, await core.callStorm('return((2 ** 2.4))'))

            self.eq(1, await core.callStorm('return((3 % 2))'))
            self.eq(1.0, await core.callStorm('return((3.0 % 2))'))
            self.eq(1.0, await core.callStorm('return((3 % 2.0))'))
            self.eq(0.75, await core.callStorm('return((3.0 % 2.25))'))
            self.eq(0.9, await core.callStorm('return((3.0 % 2.1))'))

            self.eq(-5.2, await core.callStorm('$foo=5.2 return((-$foo))'))
            self.eq(5.2, await core.callStorm('$foo=5.2 return((--$foo))'))
            self.eq(6.2, await core.callStorm('$foo=5.2 return((1--$foo))'))
            self.eq(-4.2, await core.callStorm('$foo=5.2 return((1---$foo))'))
            self.eq(-7, await core.callStorm('$foo=5.2 return((-(3+4)))'))

            self.eq(2.43, await core.callStorm('return((1.23 + $lib.cast(float, 1.2)))'))
            self.eq(0.03, await core.callStorm('return((1.23 - $lib.cast(float, 1.2)))'))
            self.eq(1.476, await core.callStorm('return((1.23 * $lib.cast(float, 1.2)))'))
            self.eq(1.025, await core.callStorm('return((1.23 / $lib.cast(float, 1.2)))'))
            self.eq(0.03, await core.callStorm('return((1.23 % $lib.cast(float, 1.2)))'))

            self.false(await core.callStorm('return((1.23 = 1))'))
            self.false(await core.callStorm('return((1 = 1.23))'))
            self.false(await core.callStorm('return((1.23 = 2.34))'))
            self.false(await core.callStorm('return((1.23 = $lib.cast(float, 2.34)))'))
            self.false(await core.callStorm('return(($lib.cast(float, 2.34) = 1.23))'))

            self.true(await core.callStorm('return((1.23 = 1.23))'))
            self.true(await core.callStorm('return((1.0 = 1))'))
            self.true(await core.callStorm('return((1 = 1.0))'))
            self.true(await core.callStorm('return((1.23 = $lib.cast(float, 1.23)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 1.23) = 1.23))'))

            self.true(await core.callStorm('return((1.23 != 1))'))
            self.true(await core.callStorm('return((1 != 1.23))'))
            self.true(await core.callStorm('return((1.23 != 2.34))'))
            self.true(await core.callStorm('return((1.23 != $lib.cast(float, 2.34)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 2.34) != 1.23))'))

            self.false(await core.callStorm('return((1.23 != 1.23))'))
            self.false(await core.callStorm('return((1.0 != 1))'))
            self.false(await core.callStorm('return((1 != 1.0))'))
            self.false(await core.callStorm('return((1.23 != $lib.cast(float, 1.23)))'))
            self.false(await core.callStorm('return(($lib.cast(float, 1.23) != 1.23))'))

            self.true(await core.callStorm('return((1.23 > 1))'))
            self.true(await core.callStorm('return((2 > 1.23))'))
            self.true(await core.callStorm('return((2.34 > 1.23))'))
            self.true(await core.callStorm('return((2.34 > $lib.cast(float, 1.23)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 2.34) > 1.23))'))

            self.true(await core.callStorm('return((1.23 >= 1))'))
            self.true(await core.callStorm('return((2 >= 1.23))'))
            self.true(await core.callStorm('return((2.34 >= 1.23))'))
            self.true(await core.callStorm('return((2.34 >= $lib.cast(float, 1.23)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 2.34) >= 1.23))'))

            self.true(await core.callStorm('return((1.23 < 2))'))
            self.true(await core.callStorm('return((1 < 1.23))'))
            self.true(await core.callStorm('return((1.23 < 2.34))'))
            self.true(await core.callStorm('return((1.23 < $lib.cast(float, 2.34)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 1.23) < 2.34))'))

            self.true(await core.callStorm('return((1.23 <= 2))'))
            self.true(await core.callStorm('return((1 <= 1.23))'))
            self.true(await core.callStorm('return((1.23 <= 2.34))'))
            self.true(await core.callStorm('return((1.23 <= $lib.cast(float, 2.34)))'))
            self.true(await core.callStorm('return(($lib.cast(float, 1.23) <= 2.34))'))

            self.eq(await core.callStorm('return(($lib.cast(str, (5.3 / 2))))'), '2.65')
            self.eq(await core.callStorm('return(($lib.cast(str, (1.25 + 2.75))))'), '4.0')
            self.eq(await core.callStorm('return(($lib.cast(str, (0.00000000000000001))))'), '0.00000000000000001')
            self.eq(await core.callStorm('return(($lib.cast(str, (0.33333333333333333333))))'), '0.3333333333333333')
            self.eq(await core.callStorm('return(($lib.cast(str, ($valu))))', opts={'vars': {'valu': math.nan}}), 'NaN')
            self.eq(await core.callStorm('return(($lib.cast(str, ($valu))))', opts={'vars': {'valu': math.inf}}), 'Infinity')
            self.eq(await core.callStorm('return(($lib.cast(str, ($valu))))', opts={'vars': {'valu': -math.inf}}), '-Infinity')

            guid = await core.callStorm('return($lib.guid((1.23)))')
            self.eq(guid, '5c293425e676da3823b81093c7cd829e')

    async def test_ast_subgraph_light_edges(self):
        async with self.getTestCore() as core:
            await core.nodes('[ test:int=20 <(refs)+ { [media:news=*] } ]')
            msgs = await core.stormlist('media:news test:int', opts={'graph': True})
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.len(1, nodes[1][1]['path']['edges'])
            self.eq('refs', nodes[1][1]['path']['edges'][0][1]['verb'])

            msgs = await core.stormlist('media:news test:int | graph --no-edges')
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(0, nodes[0][1]['path']['edges'])

    async def test_ast_storm_readonly(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ inet:ipv4=1.2.3.4 ]'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4', opts={'readonly': True}))

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('[ inet:ipv4=1.2.3.4 ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ :asn=20 ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ -:asn ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ +#foo ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ -#foo ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ +#foo:bar=10 ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ -#foo:bar ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ .seen=2020 ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ -.seen ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ +(refs)> { inet:ipv4=1.2.3.4 } ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ -(refs)> { inet:ipv4=1.2.3.4 } ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ <(refs)+ { inet:ipv4=1.2.3.4 } ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4=1.2.3.4 [ <(refs)- { inet:ipv4=1.2.3.4 } ]', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('[ (inet:ipv4=1.2.3.4 :asn=20) ]', opts={'readonly': True})

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 | limit 10', opts={'readonly': True}))
            with self.raises(s_exc.IsReadOnly):
                self.len(1, await core.nodes('inet:ipv4=1.2.3.4 | delnode', opts={'readonly': True}))

            iden = await core.callStorm('return($lib.view.get().iden)')
            await core.nodes('view.list', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes(f'view.fork {iden}', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('$lib.view.get().fork()', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('vertex.link', opts={'readonly': True, 'mode': 'autoadd'})

            with self.raises(s_exc.IsReadOnly):
                await core.nodes('inet:ipv4 | limit 1 | tee { [+#foo] }', opts={'readonly': True})

            q = 'function func(arg) { $lib.print(`hello {$arg}`) return () } $func(world)'
            msgs = await core.stormlist(q, opts={'readonly': True})
            self.stormIsInPrint('hello world', msgs)

            q = 'function func(arg) { [test:str=$arg] return ($node) } $func(world)'
            with self.raises(s_exc.IsReadOnly) as cm:
                await core.nodes(q, opts={'readonly': True})

            q = 'function func(arg) { auth.user.addrule root $arg | return () } $func(hehe.haha)'
            msgs = await core.stormlist(q, opts={'readonly': True})
            self.stormIsInErr('Function (_methUserAddRule) is not marked readonly safe.', msgs)

    async def test_ast_yield(self):

        async with self.getTestCore() as core:
            q = '$nodes = $lib.list() [ inet:asn=10 inet:asn=20 ] $nodes.append($node) | spin | yield $nodes'
            nodes = await core.nodes(q)
            self.len(2, nodes)

            q = '$nodes = $lib.set() [ inet:asn=10 inet:asn=20 ] $nodes.add($node) | spin | yield $nodes'
            nodes = await core.nodes(q)
            self.len(2, nodes)

    async def test_ast_exprs(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=QuickBrownFox]'))

            q = '''test:str $data=$node.value()
            if ($data ~= "Brown") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('yes', msgs)

            q = '''test:str $data=$node.value()
            if ($data ~= "brown") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('yes', msgs)

            q = '''test:str $data=$node.value()
            if ($data ~= "(?-i:brown)") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('no', msgs)

            q = '''test:str $data=$node.value()
            if ($data.lower() ~= "brown") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('yes', msgs)

            q = '''test:str $data=$node.value()
            if ($data ~= "newp") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('no', msgs)

            q = '''test:str $data=$node.value()
            if ($data ^= "Quick") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('yes', msgs)

            q = '''test:str $data=$node.value()
            if ($data ^= "quick") { $lib.print(yes) }
            else { $lib.print(no) }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('no', msgs)

    async def test_ast_optimization(self):

        calls = []

        origprop = s_snap.Snap.nodesByProp
        origvalu = s_snap.Snap.nodesByPropValu

        async def checkProp(self, name, reverse=False):
            calls.append(('prop', name))
            async for node in origprop(self, name):
                yield node

        async def checkValu(self, name, cmpr, valu, reverse=False):
            calls.append(('valu', name, cmpr, valu))
            async for node in origvalu(self, name, cmpr, valu):
                yield node

        with mock.patch('synapse.lib.snap.Snap.nodesByProp', checkProp):
            with mock.patch('synapse.lib.snap.Snap.nodesByPropValu', checkValu):
                async with self.getTestCore() as core:

                    self.len(1, await core.nodes('[inet:asn=200 :name=visi]'))
                    self.len(1, await core.nodes('[inet:ipv4=1.2.3.4 :asn=200]'))
                    self.len(1, await core.nodes('[inet:ipv4=5.6.7.8]'))
                    self.len(1, await core.nodes('[inet:ipv4=5.6.7.9 :loc=us]'))
                    self.len(1, await core.nodes('[inet:ipv4=5.6.7.10 :loc=uk]'))
                    self.len(1, await core.nodes('[test:str=a :bar=(test:str, a) :tick=19990101]'))
                    self.len(1, await core.nodes('[test:str=m :bar=(test:str, m) :tick=20200101]'))

                    await core.nodes('.created [.seen=20200101]')
                    calls = []

                    nodes = await core.nodes('inet:ipv4 +:loc=us')
                    self.len(1, nodes)
                    self.eq(calls, [('valu', 'inet:ipv4:loc', '=', 'us')])
                    calls = []

                    nodes = await core.nodes('inet:ipv4 +:loc')
                    self.len(2, nodes)
                    self.eq(calls, [('prop', 'inet:ipv4:loc')])
                    calls = []

                    nodes = await core.nodes('$loc=us inet:ipv4 +:loc=$loc')
                    self.len(1, nodes)
                    self.eq(calls, [('valu', 'inet:ipv4:loc', '=', 'us')])
                    calls = []

                    nodes = await core.nodes('$prop=loc inet:ipv4 +:$prop=us')
                    self.len(1, nodes)
                    self.eq(calls, [('valu', 'inet:ipv4:loc', '=', 'us')])
                    calls = []

                    # Don't optimize if a non-lift happens before the filter
                    nodes = await core.nodes('$loc=us inet:ipv4 $loc=uk +:loc=$loc')
                    self.len(1, nodes)
                    self.eq(calls, [('prop', 'inet:ipv4')])
                    calls = []

                    nodes = await core.nodes('inet:ipv4:loc {$loc=:loc inet:ipv4 +:loc=$loc}')
                    self.len(2, nodes)
                    exp = [
                        ('prop', 'inet:ipv4:loc'),
                        ('valu', 'inet:ipv4:loc', '=', 'uk'),
                        ('valu', 'inet:ipv4:loc', '=', 'us'),
                    ]
                    self.eq(calls, exp)
                    calls = []

                    nodes = await core.nodes('inet:ipv4 +.seen')
                    self.len(4, nodes)
                    self.eq(calls, [('prop', 'inet:ipv4.seen')])
                    calls = []

                    # Should optimize both lifts
                    nodes = await core.nodes('inet:ipv4 test:str +.seen@=2020')
                    self.len(6, nodes)
                    exp = [
                        ('valu', 'inet:ipv4.seen', '@=', '2020'),
                        ('valu', 'test:str.seen', '@=', '2020'),
                    ]
                    self.eq(calls, exp)
                    calls = []

                    # Optimize pivprop filter a bit
                    nodes = await core.nodes('inet:ipv4 +:asn::name=visi')
                    self.len(1, nodes)
                    self.eq(calls, [('prop', 'inet:ipv4:asn')])
                    calls = []

                    nodes = await core.nodes('inet:ipv4 +:asn::name')
                    self.len(1, nodes)
                    self.eq(calls, [('prop', 'inet:ipv4:asn')])
                    calls = []

                    nodes = await core.nodes('test:str +:tick*range=(19701125, 20151212)')
                    self.len(1, nodes)
                    self.eq(calls, [('valu', 'test:str:tick', 'range=', ['19701125', '20151212'])])
                    calls = []

                    # Lift by value will fail since stortype is MSGP
                    # can still optimize a bit though
                    nodes = await core.nodes('test:str +:bar*range=((test:str, c), (test:str, q))')
                    self.len(1, nodes)

                    exp = [
                        ('valu', 'test:str:bar', 'range=', [['test:str', 'c'], ['test:str', 'q']]),
                        ('prop', 'test:str:bar'),
                    ]

                    self.eq(calls, exp)
                    calls = []

                    # Shouldn't optimize this, make sure the edit happens
                    msgs = await core.stormlist('inet:ipv4 | limit 1 | [.seen=now] +#notag')
                    self.len(1, [m for m in msgs if m[0] == 'node:edits'])
                    self.len(0, [m for m in msgs if m[0] == 'node'])
                    self.eq(calls, [('prop', 'inet:ipv4')])

    async def test_ast_cmdoper(self):

        async with self.getTestCore() as core:

            evtl = asyncio.get_event_loop()
            beforecount = len(evtl._asyncgens)

            await core.nodes('[ inet:fqdn=vertex.link ]')

            # Make sure commands don't leave generators around
            self.eq(beforecount, len(evtl._asyncgens))

            await core.nodes('''
                $i=0
                while ($i < 200) {
                    inet:fqdn=vertex.link | limit 1 | spin |
                    $i = ($i+1)
                }
            ''')

            # Wait a second for cleanup
            await asyncio.sleep(1)
            self.eq(beforecount, len(evtl._asyncgens))

    async def test_ast_condeval(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo ] +$lib.true'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4  +(#foo and $lib.false)'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4  +$(:asn + 20 >= 42)'))

            opts = {'vars': {'asdf': b'asdf'}}
            await core.nodes('[ file:bytes=$asdf ]', opts=opts)
            await core.axon.put(b'asdf')
            self.len(1, await core.nodes('file:bytes +$lib.bytes.has(:sha256)'))

    async def test_ast_walkcond(self):

        async with self.getTestCore() as core:

            iden = await core.callStorm('[ meta:source=* :name=woot ] return($node.repr())')
            opts = {'vars': {'iden': iden}}

            await core.nodes('[ inet:ipv4=5.5.5.5 ]')
            await core.nodes('[ inet:ipv4=1.2.3.4 <(seen)+ { meta:source=$iden } ]', opts=opts)

            with self.raises(s_exc.StormRuntimeError):
                self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- *=woot'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- *'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source=$iden', opts=opts))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name^=wo'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name=woot'))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source=*'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name^=vi'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name=visi'))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- (inet:fqdn, inet:ipv4)'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- (meta:source, inet:fqdn)'))
            self.len(1, await core.nodes('function form() {return(meta:source)} inet:ipv4=1.2.3.4 <(seen)- $form()'))

            await core.nodes('[ inet:ipv4=1.2.3.4 <(seen)+ { [meta:source=*] } ]')
            self.len(2, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 <(seen)- meta:source:name'))

    async def test_ast_contexts(self):
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=vertex.link ]')

            async with s_test.matchContexts(self):

                await core.nodes("inet:fqdn -> { inet:fqdn=vertex.link } | limit 1")
                await core.nodes("function x() { inet:fqdn=vertex.link } yield $x() | limit 1")
                await core.nodes("yield ${inet:fqdn=vertex.link} | limit 1")
                await core.nodes("inet:fqdn parallel { } | limit 1")

                async for node in core.storm("function foo() { emit foo } for $x in $foo() { $lib.raise(foo, bar) }"):
                    pass

    async def test_ast_vars_missing(self):

        async with self.getTestCore() as core:
            q = '$ret = $ret $lib.print($ret)'
            mesgs = await core.stormlist(q)
            self.stormIsInErr('Missing variable: ret', mesgs)

            q = '$lib.concat($ret, foo) $lib.print($ret)'
            mesgs = await core.stormlist(q)
            self.stormIsInErr('Missing variable: ret', mesgs)

            q = '$ret=$lib.squeeeeeee($ret, foo) $lib.print($ret)'
            mesgs = await core.stormlist(q)
            self.stormIsInErr('Missing variable: ret', mesgs)

            mesgs = await core.stormlist(q, opts={'vars': {'ret': 'foo'}})
            self.stormIsInErr('Cannot find name [squeeeeeee]', mesgs)

            q = '$ret=$lib.dict(bar=$ret)'
            mesgs = await core.stormlist(q)
            self.stormIsInErr('Missing variable: ret', mesgs)

            q = '$view = $lib.view.get() $lib.print($view)'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('view', mesgs)

            q = '''
                $pipe = $lib.pipe.gen(${
                    $pipe.put(neato)
                    $pipe.put(burrito)
                })

                $lib.time.sleep(1)
                for $items in $pipe.slices(size=2) {
                    for $thingy in $items {
                        $lib.print($thingy)
                    }
                }
            '''
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('neato', mesgs)
            self.stormIsInPrint('burrito', mesgs)

            q = '''
                $foo = ${ $foo="NEAT" return($foo) }
                $bar = $foo.exec()
                $lib.print($foo)
            '''
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('NEAT', mesgs)

            q = '''
            function foo(x) {
                $x = "some special string"
                return($x)
            }

            $x = $foo((12))
            $lib.print($x)
            '''
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('some special string', mesgs)

            q = '''
            [ inet:fqdn=foo.com ]
            +:newp
            $bar=:newp
            $lib.print($bar)
            $bar=bar
            '''
            with self.raises(s_exc.NoSuchVar) as err:
                await core.nodes(q)
            self.true(err.exception.errinfo.get('runtsafe'))

            q = '''
            [ inet:ipv4=1.2.3.4 ]
            { +:asn $bar=:asn }
            $lib.print($bar)
            '''
            with self.raises(s_exc.NoSuchVar) as err:
                await core.nodes(q)
            self.false(err.exception.errinfo.get('runtsafe'))

    async def test_ast_maxdepth(self):

        async with self.getTestCore() as core:

            q = '['
            for x in range(1000):
                q += f'inet:ipv4={x} '
            q += ']'

            with self.raises(s_exc.RecursionLimitHit) as err:
                msgs = await core.nodes(q)

    async def test_ast_highlight(self):

        async with self.getTestCore() as core:
            text = '[ ps:contact=* :name=$visi ]'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq('visi', text[off:end])

            text = '[ ps:contact=* :foo:bar=haha ]'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq(':foo:bar', text[off:end])

            text = 'init { $foo = :bar }'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq(':bar', text[off:end])

            text = 'inet:ipv5'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq('inet:ipv5', text[off:end])

            text = 'inet:ipv5=127.0.0.1'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq('inet:ipv5', text[off:end])

            text = '[ inet:ipv4=1.2.3.4 ] $x=:haha'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq(':haha', text[off:end])

            text = '$p=haha inet:ipv4 $x=:$p'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq('p', text[off:end])

            text = 'inet:ipv4=haha'
            msgs = await core.stormlist(text)
            errm = [m for m in msgs if m[0] == 'err'][0]
            off, end = errm[1][1]['highlight']['offsets']
            self.eq('haha', text[off:end])

    async def test_ast_bulkedges(self):

        async with self.getTestCore() as core:

            await core.nodes('for $x in $lib.range(1010) {[ it:dev:str=$x ]}')

            strtoffs = await core.getView().layers[0].getEditIndx()

            q = '''
            [ inet:ipv4=1.2.3.4
                +(refs)> { for $x in $lib.range(1005) {[ it:dev:str=$x ]} }
            ]
            '''
            self.len(1, await core.nodes(q))
            self.len(1005, await core.nodes('inet:ipv4=1.2.3.4 -(refs)> *'))

            # node creation + 2 batches of edits
            nextoffs = await core.getView().layers[0].getEditIndx()
            self.eq(strtoffs + 3, nextoffs)

            q = '''
            inet:ipv4=1.2.3.4
            [ -(refs)> { for $x in $lib.range(1010) {[ it:dev:str=$x ]} } ]
            '''
            self.len(1, await core.nodes(q))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 -(refs)> *'))

            # 2 batches of edits
            self.eq(nextoffs + 2, await core.getView().layers[0].getEditIndx())

            nodes = await core.nodes('syn:prop limit 1')
            await self.asyncraises(s_exc.IsRuntForm, nodes[0].delEdge('foo', 'bar'))

            q = 'inet:ipv4=1.2.3.4 [ <(newp)+ { syn:prop } ]'
            await self.asyncraises(s_exc.IsRuntForm, core.nodes(q))

            q = 'syn:prop [ -(newp)> { inet:ipv4=1.2.3.4 } ]'
            await self.asyncraises(s_exc.IsRuntForm, core.nodes(q))

            q = 'inet:ipv4=1.2.3.4 [ <(newp)- { syn:prop } ]'
            await self.asyncraises(s_exc.IsRuntForm, core.nodes(q))

            q = 'inet:ipv4=1.2.3.4 [ -(newp)> { syn:prop } ]'
            await self.asyncraises(s_exc.IsRuntForm, core.nodes(q))

    async def test_ast_subgraph_2pass(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ media:news=40ebf9be8fb56bd60fff542299c1b5c2 +(refs)> {[ inet:ipv4=1.2.3.4 ]} ] inet:ipv4
            ''')
            news = nodes[0]
            ipv4 = nodes[1]

            msgs = await core.stormlist('media:news inet:ipv4', opts={'graph': True})
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(nodes[1][1]['path']['edges'], (('8f66c747665dc3f16603bb25c78323ede90086d255ac07176a98a579069c4bb6',
                        {'type': 'edge', 'verb': 'refs', 'reverse': True}),))

            opts = {'graph': {'existing': (news.iden(),)}}
            msgs = await core.stormlist('inet:ipv4', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1]['path']['edges'], (('8f66c747665dc3f16603bb25c78323ede90086d255ac07176a98a579069c4bb6',
                        {'type': 'edge', 'verb': 'refs', 'reverse': True}),))

            opts = {'graph': {'existing': (ipv4.iden(),)}}
            msgs = await core.stormlist('media:news', opts=opts)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1]['path']['edges'], (('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                        {'type': 'edge', 'verb': 'refs'}),))

            msgs = await core.stormlist('media:news inet:ipv4', opts={'graph': {'maxsize': 1}})
            self.len(1, [m[1] for m in msgs if m[0] == 'node'])
            self.stormIsInWarn('Graph projection hit max size 1. Truncating results.', msgs)

            msgs = await core.stormlist('media:news', opts={'graph': {'pivots': ('--> *',)}})
            nodes = [m[1] for m in msgs if m[0] == 'node']
            # none yet...
            self.len(0, nodes[0][1]['path']['edges'])
            # one for the refs edge (via doedges) and one for the rule..
            self.len(2, nodes[1][1]['path']['edges'])

    async def test_ast_subgraph_caching(self):
        async with self.getTestCore() as core:
            limits = (0, 1, 10, 255, 256, 10000)
            ipv4s = await core.nodes('[inet:ipv4=1.2.3.0/24]')
            neato = await core.nodes('''[
                test:str=neato +(refs)> { inet:ipv4 }
            ]''')
            await core.nodes('[test:str=neato +(selfrefs)> { test:str=neato }]')
            self.len(1, neato)

            iden = neato[0].iden()
            idens = [iden,]
            opts = {
                'graph': {
                    'degrees': None,
                    'edges': True,
                    'refs': True,
                    'existing': idens
                },
                'idens': idens
            }

            def testedges(msgs):
                self.len(259, msgs)
                for m in msgs[:-2]:
                    if m[0] != 'node':
                        continue
                    node = m[1]
                    edges = node[1]['path']['edges']
                    self.len(1, edges)
                    edgeiden, edgedata = edges[0]
                    self.eq(edgeiden, iden)
                    self.true(edgedata.get('reverse', False))
                    self.eq(edgedata['verb'], 'refs')
                    self.eq(edgedata['type'], 'edge')
                selfref = msgs[-2]
                node = selfref[1]
                edges = node[1]['path']['edges']
                self.len(258, edges)

            for limit in limits:
                opts['graph']['edgelimit'] = limit
                msgs = await core.stormlist('tee { --> * } { <-- * }', opts=opts)
                testedges(msgs)

            burrito = await core.nodes('[test:str=burrito <(awesome)+ { inet:ipv4 }]')
            self.len(1, burrito)

            iden = burrito[0].iden()
            for m in msgs:
                if m[0] != 'node':
                    continue
                node = m[1]
                idens.append(node[1]['iden'])

            opts['graph']['existing'] = idens
            opts['idens'] = [ipv4s[0].iden(),]
            ipidens = [n.iden() for n in ipv4s]
            ipidens.append(neato[0].iden())
            for limit in limits:
                opts['graph']['edgelimit'] = limit
                msgs = await core.stormlist('tee { --> * } { <-- * }', opts=opts)
                self.len(4, msgs)

                node = msgs[1][1]
                self.eq(node[0], ('test:str', 'burrito'))
                edges = node[1]['path']['edges']
                self.len(256, edges)

                for edge in edges:
                    edgeiden, edgedata = edge
                    self.isin(edgeiden, ipidens)
                    self.true(edgedata.get('reverse', False))
                    self.eq(edgedata['verb'], 'awesome')
                    self.eq(edgedata['type'], 'edge')

                node = msgs[2][1]
                self.eq(node[0], ('test:str', 'neato'))
                self.len(256, edges)
                edges = node[1]['path']['edges']
                for edge in edges:
                    edgeiden, edgedata = edge
                    self.isin(edgeiden, ipidens)
                    self.eq(edgedata['type'], 'edge')
                    if edgedata['verb'] == 'selfrefs':
                        self.eq(edgeiden, neato[0].iden())
                    else:
                        self.eq(edgedata['verb'], 'refs')
                        self.false(edgedata.get('reverse', False))

            opts['graph'].pop('existing', None)
            opts['idens'] = [neato[0].iden(),]
            for limit in limits:
                opts['graph']['edgelimit'] = limit
                msgs = await core.stormlist('tee { --> * } { <-- * }', opts=opts)
                selfrefs = 0
                for m in msgs:
                    if m[0] != 'node':
                        continue

                    node = m[1]
                    form = node[0][0]
                    edges = node[1]['path'].get('edges', ())
                    if form == 'inet:ipv4':
                        self.len(0, edges)
                    elif form == 'test:str':
                        self.len(258, edges)
                        for e in edges:
                            self.isin(e[0], ipidens)
                            self.eq('edge', e[1]['type'])
                            if e[0] == neato[0].iden():
                                selfrefs += 1
                                self.eq('selfrefs', e[1]['verb'])
                            else:
                                self.eq('refs', e[1]['verb'])
                self.eq(selfrefs, 2)

            boop = await core.nodes('[test:str=boop +(refs)> {[inet:ipv4=5.6.7.0/24]}]')
            await core.nodes('[test:str=boop <(refs)+ {[inet:ipv4=4.5.6.0/24]}]')
            self.len(1, boop)
            boopiden = boop[0].iden()
            opts['idens'] = [boopiden,]
            for limit in limits:
                opts['graph']['edgelimit'] = limit
                msgs = await core.stormlist('tee --join { --> * } { <-- * }', opts=opts)
                self.len(515, msgs)

    async def test_ast_subgraph_existing_prop_edges(self):

        async with self.getTestCore() as core:
            (fn,) = await core.nodes('[ file:bytes=(woot,) :md5=e5a23e8a2c0f98850b1a43b595c08e63 ]')
            fiden = fn.iden()

            rules = {
                'degrees': None,
                'edges': True,
                'refs': True,
                'existing': [fiden]
            }

            nodes = []

            async with await core.snap() as snap:
                async for node, path in snap.storm(':md5 -> hash:md5', opts={'idens': [fiden], 'graph': rules}):
                    nodes.append(node)

                    edges = path.metadata.get('edges')
                    self.len(1, edges)
                    self.eq(edges, [
                        [fn.iden(), {
                            "type": "prop",
                            "prop": "md5",
                            "reverse": True
                        }]
                    ])

                    self.true(path.metadata.get('graph:seed'))

            self.len(1, nodes)

    async def test_ast_double_init_fini(self):
        async with self.getTestCore() as core:
            q = '''
            init {$foo = bar $lib.print(`{$foo} {$wow}`) }
            init {$baz = hehe $lib.print('second init!') }
            $lib.print($baz)
            '''
            msgs = await core.stormlist(q, opts={'vars': {'wow': 'hehe'}})
            pmesgs = [m[1].get('mesg') for m in msgs if m[0] == 'print']
            self.eq(pmesgs, ['bar hehe', 'second init!', 'hehe'])

            q = '''
            init {$foo = bar $lib.print(`{$foo} {$wow}`) }
            init {$baz = hehe $lib.print('second init!') }
            $lib.print($baz)
            [test:str=stuff]
            $stuff = $node.value()
            fini { $lib.print(fini1) }
            fini { $lib.print(`fini {$stuff}`) }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'wow': 'hehe', 'stuff': None}})
            pmesgs = [m[1].get('mesg') for m in msgs if m[0] == 'print']
            self.eq(pmesgs, ['bar hehe', 'second init!', 'hehe', 'fini1', 'fini stuff'])

            q = '''
            init { $foo = bar }
            init { $baz = $lib.str.format('foo={foo}', foo=$foo) }
            $lib.print($baz)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('foo=bar', msgs)

    async def test_ast_tagfilters(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})

            await core.nodes('[ test:str=foo +#tagaa=2023 +#tagaa:score=5 <(foo)+ { test:str=foo } ]')
            await core.nodes('[ test:str=bar +#tagab=2024 +#tagab:score=6 ]')
            await core.nodes('[ test:str=baz +#tagba=2023 +#tagba:score=7 ]')
            await core.nodes('[ test:str=faz +#tagbb=2024 +#tagbb:score=8 ]')

            self.len(2, await core.nodes('test:str +#taga*'))
            self.len(1, await core.nodes('test:str +#tagaa=2023'))
            self.len(1, await core.nodes('test:str +#taga* <(*)- *'))
            self.len(2, await core.nodes('$tag=taga* test:str +#$tag'))
            self.len(1, await core.nodes('$tag=tagaa test:str +#$tag=2023'))

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*@=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*>2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*<(3+5)')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +#taga<(3+5)')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +#taga*min>=2023')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('$tag=taga* test:str +#$tag=2023')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('$tag=taga* test:str +#$"tag"=2023')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('$tag=taga* test:str +#foo.$"tag"=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga* test:str +#foo*.$"tag"=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga test:str +#foo.$"tag".*=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga test:str +#foo.$"tag".*=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga test:str +#foo.$"tag".$"tag".*=2023')

            self.len(2, await core.nodes('test:str +#taga*:score'))
            self.len(1, await core.nodes('test:str +#tagaa:score=5'))
            self.len(1, await core.nodes('test:str +#tagaa:score<(2+4)'))
            self.len(0, await core.nodes('test:str +#tagaa:score<-5'))
            self.len(1, await core.nodes('test:str +#tagaa:score*range=(4,6)'))
            self.len(0, await core.nodes('test:str +#taga*:score <- *'))
            self.len(1, await core.nodes('test:str +#taga*:score <(*)- *'))
            self.len(3, await core.nodes('test:str +#taga*:score <+(*)- *'))
            self.len(2, await core.nodes('$tag=taga* test:str +#$tag:score'))
            self.len(1, await core.nodes('$tag=tagaa test:str +#$tag:score=5'))
            self.len(1, await core.nodes('$tag=tagaa test:str +#$tag:score*range=(4,6)'))

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*:score=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*:score@=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*:score>2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*:score<(3+5)')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str +#taga*:score*min>=2023')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +#taga:score*min>=2023')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('$tag=taga* test:str +#$tag:score=2023')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('$tag=taga* test:str +#foo.$"tag":score=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga* test:str +#foo*.$"tag":score=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga test:str +#foo.$"tag".*:score=2023')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('$tag=taga test:str +#foo.$"tag".$"tag".*:score=2023')

    async def test_ast_righthand_relprop(self):
        async with self.getTestCore() as core:
            await core.nodes('''[
                (test:type10=one :intprop=21 :int2=21)
                (test:type10=two :intprop=21 :int2=29)
                (test:float=13.4 :closed=14.0 :open=14.0)
                (test:float=14.5 :closed=12.0 :open=13.0)
                (test:float=15.6 :closed=12.0)
                (test:float=16.7)
            ]''')

            nodes = await core.nodes('test:type10 +(:intprop = :int2)')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:type10', 'one'))

            nodes = await core.nodes('test:float +(:closed = 12.0 and :open)')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:float', 14.5))

            nodes = await core.nodes('test:float +(:open = $lib.null)')
            self.len(0, nodes)

            nodes = await core.nodes('test:float +(:closed = :open)')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:float', 13.4))

            nodes = await core.nodes('test:float $foobar=:open +(:closed = $foobar)')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:float', 13.4))

            nodes = await core.nodes('test:type10 $foobar=:int2 +(:intprop = $foobar)')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:type10', 'one'))

    async def test_ast_propvalue(self):
        async with self.getTestCore() as core:

            # Create node with data prop, assign data prop to var, update var
            q = '[ it:exec:query=(test1,) :opts=({"foo": "bar"}) ] $opts=:opts $opts.bar = "baz"'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('opts'), {'foo': 'bar'})

            q = '[ it:exec:query=(test1,) :opts=({"foo": "bar"}) ] $opts=:opts $opts.bar = "baz" [ :opts=$opts ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('opts'), {'foo': 'bar', 'bar': 'baz'})

            q = '''
            '''
            msgs = await core.stormlist('[ it:exec:query=(test2,) :opts=({"foo": "bar"}) ]')
            self.stormHasNoWarnErr(msgs)

            # Lift node with data prop, assign data prop to var, update var
            q = 'it:exec:query=(test2,) $opts=:opts $opts.bar = "baz"'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('opts'), {'foo': 'bar'})

            q = 'it:exec:query=(test2,) $opts=:opts $opts.bar = "baz" [ :opts=$opts ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('opts'), {'foo': 'bar', 'bar': 'baz'})

            # Create node for the lift below
            q = '''
            [ it:app:snort:hit=*
                :flow={[ inet:flow=* :raw=({"foo": "bar"}) ]}
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # Lift node, get prop via implicit pivot, assign data prop to var, update var
            q = f'it:app:snort:hit $raw = :flow::raw $raw.baz="box" | spin | inet:flow'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('raw'), {'foo': 'bar'})

            q = f'it:app:snort:hit $raw = :flow::raw $raw.baz="box" | spin | inet:flow [ :raw=$raw ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].props.get('raw'), {'foo': 'bar', 'baz': 'box'})

    async def test_ast_subrunt_safety(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:str=test1]')
            self.len(1, nodes)

            q = '''
            test:str=test1
            $test=$node.value()
            [(test:str=test2 +(refs)> {test:str=$test})]
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)

            nodes = await core.nodes('test:str=test1 <(refs)- test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test2'))

            q = '''
            test:str=test2
            $valu=$node.value()
            | spin |
            test:str=test1 -> { test:str=$valu }
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test2'))

        # Should produce the same results in a macro sub-runtime
        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:str=test1]')
            self.len(1, nodes)

            q = '''
            $q = ${
                test:str=test1
                $test=$node.value()
                [(test:str=test2 +(refs)> {test:str=$test})]
            }
            $lib.macro.set(test.edge, $q)
            return($lib.true)
            '''
            self.true(await core.callStorm(q))

            nodes = await core.nodes('macro.exec test.edge')
            self.len(2, nodes)

            nodes = await core.nodes('test:str=test1 <(refs)- test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test2'))

            q = '''
            $q = ${
                test:str=test2
                $valu=$node.value()
                | spin |
                test:str=test1 -> { test:str=$valu }
            }
            $lib.macro.set(test.pivot, $q)
            return($lib.true)
            '''
            self.true(await core.callStorm(q))

            nodes = await core.nodes('macro.exec test.pivot')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test2'))

    async def test_ast_subq_runtsafety(self):

        async with self.getTestCore() as core:
            msgs = await core.stormlist('$foo={[test:str=foo] return($node.value())} $lib.print($foo)')
            self.stormIsInPrint('foo', msgs)

            msgs = await core.stormlist('$lib.print({[test:str=foo] return($node.value())})')
            self.stormIsInPrint('foo', msgs)
