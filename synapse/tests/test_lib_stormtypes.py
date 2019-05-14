import synapse.common as s_common
import synapse.tests.utils as s_test

class StormTypesTest(s_test.SynTest):

    async def test_storm_node_tags(self):

        async with self.getTestCore() as core:

            await core.eval('[ test:comp=(20, haha) +#foo +#bar test:comp=(30, hoho) ]').list()

            q = '''
            test:comp
            for $tag in $node.tags() {
                -> test:int [ +#$tag ]
            }
            '''

            await core.eval(q).list()

            self.len(1, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

            q = '''
            test:comp
            for $tag in $node.tags(fo*) {
                -> test:int [ -#$tag ]
            }
            '''
            await core.eval(q).list()

            self.len(0, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

    async def test_storm_lib_base(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:asn=$lib.min(20, 0x30) ]')
            self.len(1, nodes)
            self.eq(20, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.min(20, (10, 30)) ]')
            self.len(1, nodes)
            self.eq(10, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.max(20, 0x30) ]')
            self.len(1, nodes)
            self.eq(0x30, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.max(20, (10, 30)) ]')
            self.len(1, nodes)
            self.eq(30, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.len(asdf) ]')
            self.len(1, nodes)
            self.eq(4, nodes[0].ndef[1])

            nodes = await core.nodes('[ test:str=$lib.guid() test:str=$lib.guid() ]')
            self.len(2, nodes)
            self.true(s_common.isguid(nodes[0].ndef[1]))
            self.true(s_common.isguid(nodes[1].ndef[1]))
            self.ne(nodes[0].ndef[1], nodes[1].ndef[1])

            nodes = await core.nodes('[ test:str=$lib.guid(hehe,haha) test:str=$lib.guid(hehe,haha) ]')
            self.len(2, nodes)
            self.true(s_common.isguid(nodes[0].ndef[1]))
            self.true(s_common.isguid(nodes[1].ndef[1]))
            self.eq(nodes[0].ndef[1], nodes[1].ndef[1])

            async with core.getLocalProxy() as prox:
                mesgs = [m async for m in prox.storm('$lib.print("hi there")') if m[0] == 'print']
                self.len(1, mesgs)
                self.stormIsInPrint('hi there', mesgs)

                mesgs = [m async for m in prox.storm('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] $lib.print(:zone)')]
                mesgs = [m for m in mesgs if m[0] == 'print']
                self.len(2, mesgs)
                self.eq('vertex.link', mesgs[0][1]['mesg'])
                self.eq('woot.com', mesgs[1][1]['mesg'])

                mesgs = [m async for m in prox.storm("$lib.print('woot at: {s} {num}', s=hello, num=$(42+43))")]
                self.stormIsInPrint('woot at: hello 85', mesgs)

    async def test_storm_lib_dict(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('$blah = $lib.dict(foo=vertex.link) [ inet:fqdn=$blah.foo ]')
            self.len(1, nodes)
            self.eq('vertex.link', nodes[0].ndef[1])

    # flake8: noqa: E501
    async def test_storm_lib_str(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('$v=vertex $l=link $fqdn=$lib.str.concat($v, ".", $l) [ inet:email=$lib.str.format("visi@{domain}", domain=$fqdn) ]')
            self.len(1, nodes)
            self.eq('visi@vertex.link', nodes[0].ndef[1])

    async def test_storm_lib_list(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('$v=(foo,bar,baz) [ test:str=$v.index(1) test:int=$v.length() ]')
            self.eq(nodes[0].ndef, ('test:str', 'bar'))
            self.eq(nodes[1].ndef, ('test:int', 3))

            nodes = await core.nodes('[ test:comp=(10,lol) ] $x=$node.ndef().index(1).index(1) [ test:str=$x ]')
            self.eq(nodes[1].ndef, ('test:str', 'lol'))

    async def test_storm_lib_fire(self):

        async with self.getTestCore() as core:
            text = '$lib.fire(foo:bar, baz=faz)'

            gotn = [mesg async for mesg in core.streamstorm(text) if mesg[0] == 'storm:fire']

            self.len(1, gotn)

            self.eq(gotn[0][1]['type'], 'foo:bar')
            self.eq(gotn[0][1]['data']['baz'], 'faz')
