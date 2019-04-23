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

            nodes = await core.nodes('[ inet:asn=$lib.max(20, 0x30) ]')
            self.len(1, nodes)
            self.eq(0x30, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.len(asdf) ]')
            self.len(1, nodes)
            self.eq(4, nodes[0].ndef[1])

            async with core.getLocalProxy() as prox:
                mesgs = [m async for m in prox.storm('$lib.print("hi there")')]
                mesgs = [m for m in mesgs if m[0] == 'print']
                self.len(1, mesgs)
                self.eq('hi there', mesgs[0][1]['mesg'])

                mesgs = [m async for m in prox.storm('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] $lib.print(:zone)')]
                mesgs = [m for m in mesgs if m[0] == 'print']
                self.len(2, mesgs)
                self.eq('vertex.link', mesgs[0][1]['mesg'])
                self.eq('woot.com', mesgs[1][1]['mesg'])

    async def test_storm_lib_dict(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('$blah = $lib.dict(foo=vertex.link) [ inet:fqdn=$blah.foo ]')
            self.len(1, nodes)
            self.eq('vertex.link', nodes[0].ndef[1])

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
