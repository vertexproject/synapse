import synapse.exc as s_exc

import synapse.tests.utils as s_test

class AstTest(s_test.SynTest):

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
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('haha', msgs)

            # Show that a computed variable being smashed by a
            # subquery variable assignment with multiple nodes
            # traveling through a subquery.
            async with await core.snap() as snap:
                await snap.addNode('test:comp', (30, 'w00t'))
                await snap.addNode('test:comp', (40, 'w00t'))
                await snap.addNode('test:int', 30, {'loc': 'sol'})
                await snap.addNode('test:int', 40, {'loc': 'mars'})

            q = '''
                test:comp:haha=w00t
                { -> test:int $loc=:loc }
                $lib.print($loc)
                -test:comp
            '''
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('sol', msgs)
            self.stormIsInPrint('mars', msgs)

    async def test_ast_runtsafe_bug(self):
        '''
        A regression test where the runtsafety of $newvar was incorrect
        '''
        async with self.getTestCore() as core:
            q = '''
            [test:str=another]
            $s = $lib.text("Foo")
            $newvar=:hehe -.created
            $s.add("yar {x}", x=$newvar)
            $lib.print($s.str())'''
            mesgs = await core.streamstorm(q).list()
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

            # Test for nonsensicalness
            q = 'test:str=foo [(test:str=:hehe)]'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

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

    async def test_ast_array_pivot(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:arrayprop="*" :ints=(1, 2, 3) ]')
            nodes = await core.nodes('test:arrayprop -> *')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop -> test:int')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints -> test:int')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop:ints -> *')
            self.len(3, nodes)

            nodes = await core.nodes('test:arrayprop :ints -> *')
            self.len(3, nodes)

            nodes = await core.nodes('test:int=1 <- * +test:arrayprop')
            self.len(1, nodes)

            nodes = await core.nodes('test:int=2 -> test:arrayprop')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:arrayprop')

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
        # currently a simple smoke test for the EmbedQuery.compute method
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 test:int=20 ]  $q=${#foo.bar}')
            self.len(2, nodes)
