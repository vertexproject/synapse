import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class BaseTest(s_t_utils.SynTest):

    async def test_model_base_timeline(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:timeline=* :title=Woot :summary=4LOLZ :type=lol.cats ]')
            self.len(1, nodes)
            nodes = await core.nodes('''
                [ meta:event=* :title=Zip :duration=1:30:00
                    :summary=Zop :time=20220321 :type=zip.zop :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)
            nodes = await core.nodes('''[ meta:event=* :title=Hehe :duration=2:00
                    :summary=Haha :time=20220322 :type=hehe.haha :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)

            self.len(2, await core.nodes('meta:timeline +:title=Woot +:summary=4LOLZ +:type=lol.cats -> meta:event'))
            self.len(1, await core.nodes('meta:timeline -> meta:timeline:taxonomy'))
            self.len(2, await core.nodes('meta:event -> meta:event:taxonomy'))
            self.len(1, await core.nodes('meta:event +:title=Hehe +:summary=Haha +:time=20220322 +:duration=120 +:type=hehe.haha +:timeline'))

    async def test_model_base_note(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add "foo bar baz"')
            self.len(2, nodes)
            self.len(1, await core.nodes('meta:note'))
            self.len(1, await core.nodes('meta:note:created<=now'))
            self.len(1, await core.nodes('meta:note:creator=$lib.user.iden'))
            self.len(1, await core.nodes('meta:note:text="foo bar baz"'))
            self.len(2, await core.nodes('meta:note -(about)> inet:fqdn'))
            self.len(1, await core.nodes('meta:note [ :author={[ ps:contact=* :name=visi ]} ]'))
            self.len(1, await core.nodes('ps:contact:name=visi -> meta:note'))

            # Notes are always unique when made by note.add
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add "foo bar baz"')
            self.len(2, await core.nodes('meta:note'))
            self.ne(nodes[0].ndef, nodes[1].ndef)
            self.eq(nodes[0].get('text'), nodes[1].get('text'))

    async def test_model_base_node(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                iden = s_common.guid()

                props = {
                    'type': 'hehe haha',
                    'data': ('some', 'data', 'here'),
                }

                node = await snap.addNode('graph:node', iden, props=props)
                self.eq(node.ndef, ('graph:node', iden))
                self.eq(node.get('type'), 'hehe haha')
                self.eq(node.get('data'), ('some', 'data', 'here'))

    async def test_model_base_link(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node1 = await snap.addNode('test:int', 20)
                node2 = await snap.addNode('test:str', 'foo')

                link = await snap.addNode('graph:edge', (node1.ndef, node2.ndef))

                self.eq(link.ndef[1], (('test:int', 20), ('test:str', 'foo')))
                self.eq(link.get('n1'), ('test:int', 20))
                self.eq(link.get('n1:form'), 'test:int')

                self.eq(link.get('n2'), ('test:str', 'foo'))
                self.eq(link.get('n2:form'), 'test:str')

                timeedge = await snap.addNode('graph:timeedge', (node1.ndef, node2.ndef, '2015'))

                self.eq(timeedge.ndef[1], (('test:int', 20), ('test:str', 'foo'), 1420070400000))

                self.eq(timeedge.get('time'), 1420070400000)

                self.eq(timeedge.get('n1'), ('test:int', 20))
                self.eq(timeedge.get('n1:form'), 'test:int')

                self.eq(timeedge.get('n2'), ('test:str', 'foo'))
                self.eq(timeedge.get('n2:form'), 'test:str')

    async def test_model_base_event(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                iden = s_common.guid()

                props = {
                    'type': 'HeHe HaHa',
                    'time': '2015',
                    'name': 'Magic Pony',
                    'data': ('some', 'data', 'here'),
                }

                node = await snap.addNode('graph:event', iden, props=props)

                self.eq(node.ndef, ('graph:event', iden))

                self.eq(node.get('type'), 'HeHe HaHa')
                self.eq(node.get('time'), 1420070400000)
                self.eq(node.get('data'), ('some', 'data', 'here'))
                self.eq(node.get('name'), 'Magic Pony')

                # Raise on non-json-safe values
                props['data'] = {(1, 2): 'foo'}
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('graph:event', iden, props=props))

                props['data'] = b'bindata'
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('graph:event', iden, props=props))

    async def test_model_base_edge(self):

        async with self.getTestCore() as core:

            pers = s_common.guid()
            plac = s_common.guid()

            n1def = ('ps:person', pers)
            n2def = ('geo:place', plac)

            async with await core.snap() as snap:

                node = await snap.addNode('edge:has', (n1def, n2def))

                self.eq(node.get('n1'), n1def)
                self.eq(node.get('n1:form'), 'ps:person')

                self.eq(node.get('n2'), n2def)
                self.eq(node.get('n2:form'), 'geo:place')

                node = await snap.addNode('edge:wentto', (n1def, n2def, '2016'))

                self.eq(node.get('time'), 1451606400000)

                self.eq(node.get('n1'), n1def)
                self.eq(node.get('n1:form'), 'ps:person')

                self.eq(node.get('n2'), n2def)
                self.eq(node.get('n2:form'), 'geo:place')

            opts = {'vars': {'pers': pers}}

            self.eq(1, await core.count('ps:person=$pers -> edge:has -> *', opts=opts))
            self.eq(1, await core.count('ps:person=$pers -> edge:has -> geo:place', opts=opts))
            self.eq(0, await core.count('ps:person=$pers -> edge:has -> inet:ipv4', opts=opts))

            self.eq(1, await core.count('ps:person=$pers -> edge:wentto -> *', opts=opts))
            q = 'ps:person=$pers -> edge:wentto +:time@=(2014,2017) -> geo:place'
            self.eq(1, await core.count(q, opts=opts))
            self.eq(0, await core.count('ps:person=$pers -> edge:wentto -> inet:ipv4', opts=opts))

            opts = {'vars': {'place': plac}}

            self.eq(1, await core.count('geo:place=$place <- edge:has <- *', opts=opts))
            self.eq(1, await core.count('geo:place=$place <- edge:has <- ps:person', opts=opts))
            self.eq(0, await core.count('geo:place=$place <- edge:has <- inet:ipv4', opts=opts))

            # Make a restricted edge and validate that you can only form certain relationships
            copts = {'n1:forms': ('ps:person',), 'n2:forms': ('geo:place',)}
            t = core.model.type('edge').clone(copts)
            norm, info = t.norm((n1def, n2def))
            self.eq(norm, (n1def, n2def))
            self.raises(s_exc.BadTypeValu, t.norm, (n1def, ('test:int', 1)))
            self.raises(s_exc.BadTypeValu, t.norm, (('test:int', 1), n2def))

            # Make sure we don't return None nodes if one node of an edge is deleted
            node = await core.getNodeByNdef(n2def)
            await node.delete()
            opts = {'vars': {'pers': pers}}
            self.eq(0, await core.count('ps:person=$pers -> edge:wentto -> *', opts=opts))

            # Make sure we don't return None nodes on a PropPivotOut
            opts = {'vars': {'pers': pers}}
            self.eq(0, await core.count('ps:person=$pers -> edge:wentto :n2 -> *', opts=opts))

    async def test_model_base_source(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                props = {
                    'name': 'FOO BAR',
                    'type': 'osint',
                }

                sorc = await snap.addNode('meta:source', '*', props=props)

                self.eq(sorc.get('type'), 'osint')
                self.eq(sorc.get('name'), 'foo bar')

                valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))

                seen = await snap.addNode('meta:seen', valu)

                self.eq(seen.get('source'), sorc.ndef[1])
                self.eq(seen.get('node'), ('inet:fqdn', 'woot.com'))

    async def test_model_base_cluster(self):

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                guid = s_common.guid()
                props = {'name': 'Test Cluster', 'desc': 'A cluster for testing', 'type': 'similarity'}
                cnode = await snap.addNode('graph:cluster', guid, props)
                self.eq(cnode.get('type'), 'similarity')
                self.eq(cnode.get('name'), 'test cluster')
                self.eq(cnode.get('desc'), 'a cluster for testing')

                # Example reference nodes
                r1 = await snap.addNode('edge:refs', (cnode.ndef, ('test:str', '1234')))
                r2 = await snap.addNode('edge:refs', (cnode.ndef, ('test:int', 1234)))

                # Gather up all the nodes in the cluster
                nodes = await snap.eval(f'graph:cluster={guid} -+> edge:refs -+> * | uniq').list()
                self.len(5, nodes)

    async def test_model_base_rules(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ meta:ruleset=*
                    :created=20200202 :updated=20220401 :author=*
                    :name=" My  Rules" :desc="My cool ruleset" ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('author'))
            self.eq(nodes[0].get('created'), 1580601600000)
            self.eq(nodes[0].get('updated'), 1648771200000)
            self.eq(nodes[0].get('name'), 'my rules')
            self.eq(nodes[0].get('desc'), 'My cool ruleset')

            nodes = await core.nodes('''
                [ meta:rule=*
                    :created=20200202 :updated=20220401 :author=*
                    :name=" My  Rule" :desc="My cool rule"
                    :text="while TRUE { BAD }"
                    :ext:id=WOOT-20 :url=https://vertex.link/rules/WOOT-20
                    <(has)+ { meta:ruleset }
                    +(matches)> { [inet:ipv4=123.123.123] }
                ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('author'))
            self.eq(nodes[0].get('created'), 1580601600000)
            self.eq(nodes[0].get('updated'), 1648771200000)
            self.eq(nodes[0].get('name'), 'my rule')
            self.eq(nodes[0].get('desc'), 'My cool rule')
            self.eq(nodes[0].get('text'), 'while TRUE { BAD }')
            self.eq(nodes[0].get('url'), 'https://vertex.link/rules/WOOT-20')
            self.eq(nodes[0].get('ext:id'), 'WOOT-20')

            self.len(1, await core.nodes('meta:rule -> ps:contact'))
            self.len(1, await core.nodes('meta:ruleset -> ps:contact'))
            self.len(1, await core.nodes('meta:ruleset -(has)> meta:rule -(matches)> *'))
