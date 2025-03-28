import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class BaseTest(s_t_utils.SynTest):

    async def test_model_base_timeline(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:timeline=* :title=Woot :summary=4LOLZ :type=lol.cats ]')
            self.len(1, nodes)
            nodes = await core.nodes('''
                [ meta:event=* :title=Zip :duration=1:30:00 :index=0
                    :summary=Zop :time=20220321 :type=zip.zop :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)
            self.eq(0, nodes[0].get('index'))
            nodes = await core.nodes('''[ meta:event=* :title=Hehe :duration=2:00
                    :summary=Haha :time=20220322 :type=hehe.haha :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)

            self.len(2, await core.nodes('meta:timeline +:title=Woot +:summary=4LOLZ +:type=lol.cats -> meta:event'))
            self.len(1, await core.nodes('meta:timeline -> meta:timeline:taxonomy'))
            self.len(2, await core.nodes('meta:event -> meta:event:taxonomy'))
            self.len(1, await core.nodes('meta:event +:title=Hehe +:summary=Haha +:time=20220322 +:duration=120 +:type=hehe.haha +:timeline'))

    async def test_model_base_meta_taxonomy(self):
        async with self.getTestCore() as core:
            q = '''
            $info = ({"doc": "test taxonomy", "interfaces": ["meta:taxonomy"]})
            $lib.model.ext.addForm(_test:taxonomy, taxonomy, ({}), $info)
            '''
            await core.callStorm(q)
            nodes = await core.nodes('[_test:taxonomy=foo.bar.baz :title="title words" :desc="a test taxonomy" :sort=1 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('_test:taxonomy', 'foo.bar.baz.'))
            self.eq(node.get('title'), 'title words')
            self.eq(node.get('desc'), 'a test taxonomy')
            self.eq(node.get('sort'), 1)
            self.eq(node.get('base'), 'baz')
            self.eq(node.get('depth'), 2)
            self.eq(node.get('parent'), 'foo.bar.')

    async def test_model_base_note(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add --type hehe.haha "foo bar baz"')
            self.len(2, nodes)
            self.len(1, await core.nodes('meta:note'))
            self.len(1, await core.nodes('meta:note:created<=now'))
            self.len(1, await core.nodes('meta:note:updated<=now'))
            self.len(1, await core.nodes('meta:note:created +(:created = :updated)'))
            self.len(1, await core.nodes('meta:note:creator=$lib.user.iden'))
            self.len(1, await core.nodes('meta:note:text="foo bar baz"'))
            self.len(2, await core.nodes('meta:note -(about)> inet:fqdn'))
            self.len(1, await core.nodes('meta:note [ :author={[ ps:contact=* :name=visi ]} ]'))
            self.len(1, await core.nodes('ps:contact:name=visi -> meta:note'))
            self.len(1, await core.nodes('meta:note:type=hehe.haha -> meta:note:type:taxonomy'))

            # Notes are always unique when made by note.add
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add "foo bar baz"')
            self.len(2, await core.nodes('meta:note'))
            self.ne(nodes[0].ndef, nodes[1].ndef)
            self.eq(nodes[0].get('text'), nodes[1].get('text'))

            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add --yield "yieldnote"')
            self.len(1, nodes)
            self.eq(nodes[0].get('text'), 'yieldnote')

            nodes = await core.nodes('note.add --yield "nonodes" | [ :replyto=* ]')
            self.len(1, nodes)
            self.eq(nodes[0].get('text'), 'nonodes')
            self.nn(nodes[0].get('created'))
            self.nn(nodes[0].get('updated'))

            self.len(0, await core.nodes('meta:note:text=nonodes -(about)> *'))
            self.len(1, await core.nodes('meta:note:text=nonodes -> meta:note'))

    async def test_model_base_node(self):

        async with self.getTestCore() as core:
            iden = s_common.guid()

            nodes = await core.nodes('[(graph:node=$valu :type="hehe haha" :data=(some, data, here))]',
                                     opts={'vars': {'valu': iden}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('graph:node', iden))
            self.eq(node.get('type'), 'hehe haha')
            self.eq(node.get('data'), ('some', 'data', 'here'))

    async def test_model_base_link(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[test:int=20 test:str=foo]')
            self.len(2, nodes)
            node1 = nodes[0]
            node2 = nodes[1]

            nodes = await core.nodes('[graph:edge=$valu]', opts={'vars': {'valu': (node1.ndef, node2.ndef)}})
            self.len(1, nodes)
            link = nodes[0]

            self.eq(link.ndef, ('graph:edge', (('test:int', 20), ('test:str', 'foo'))))
            self.eq(link.get('n1'), ('test:int', 20))
            self.eq(link.get('n1:form'), 'test:int')
            self.eq(link.get('n2'), ('test:str', 'foo'))
            self.eq(link.get('n2:form'), 'test:str')

            nodes = await core.nodes('[graph:timeedge=$valu]',
                                     opts={'vars': {'valu': (node1.ndef, node2.ndef, '2015')}})
            self.len(1, nodes)
            timeedge = nodes[0]

            self.eq(timeedge.ndef, ('graph:timeedge', (('test:int', 20), ('test:str', 'foo'), 1420070400000)))
            self.eq(timeedge.get('time'), 1420070400000)
            self.eq(timeedge.get('n1'), ('test:int', 20))
            self.eq(timeedge.get('n1:form'), 'test:int')
            self.eq(timeedge.get('n2'), ('test:str', 'foo'))
            self.eq(timeedge.get('n2:form'), 'test:str')

    async def test_model_base_event(self):

        async with self.getTestCore() as core:
            iden = s_common.guid()

            props = {
                'type': 'HeHe HaHa',
                'time': '2015',
                'name': 'Magic Pony',
                'data': ('some', 'data', 'here'),
            }
            opts = {'vars': {'valu': iden, 'p': props}}
            q = '[(graph:event=$valu :type=$p.type :time=$p.time :name=$p.name :data=$p.data)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('graph:event', iden))

            self.eq(node.get('type'), 'HeHe HaHa')
            self.eq(node.get('time'), 1420070400000)
            self.eq(node.get('data'), ('some', 'data', 'here'))
            self.eq(node.get('name'), 'Magic Pony')

            # Raise on non-json-safe values
            props['data'] = {(1, 2): 'foo'}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q, opts=opts)

            props['data'] = b'bindata'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q, opts=opts)

    async def test_model_base_edge(self):

        async with self.getTestCore() as core:

            pers = s_common.guid()
            plac = s_common.guid()

            n1def = ('ps:person', pers)
            n2def = ('geo:place', plac)

            nodes = await core.nodes('[edge:has=$valu]', opts={'vars': {'valu': (n1def, n2def)}})
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.get('n1'), n1def)
            self.eq(node.get('n1:form'), 'ps:person')
            self.eq(node.get('n2'), n2def)
            self.eq(node.get('n2:form'), 'geo:place')

            nodes = await core.nodes('[edge:wentto=$valu]', opts={'vars': {'valu': (n1def, n2def, '2016')}})
            self.len(1, nodes)
            node = nodes[0]

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
            with self.raises(s_exc.BadTypeValu):
                t.norm((n1def, ('test:int', 1)))
            with self.raises(s_exc.BadTypeValu):
                t.norm((('test:int', 1), n2def))

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

            nodes = await core.nodes('''
                [meta:source="*"
                    :name="FOO Bar"
                    :type=osint
                    :url="https://foo.bar/index.html"
                    :ingest:cursor="Woot Woot "
                    :ingest:latest=20241205
                    :ingest:offset=17
                ]
            ''')
            self.len(1, nodes)
            sorc = nodes[0]

            self.eq(sorc.get('type'), 'osint')
            self.eq(sorc.get('name'), 'foo bar')
            self.eq(sorc.get('url'), 'https://foo.bar/index.html')
            self.eq(sorc.get('ingest:offset'), 17)
            self.eq(sorc.get('ingest:cursor'), 'Woot Woot ')
            self.eq(sorc.get('ingest:latest'), 1733356800000)

            valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))
            nodes = await core.nodes('[meta:seen=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            seen = nodes[0]

            self.eq(seen.get('source'), sorc.ndef[1])
            self.eq(seen.get('node'), ('inet:fqdn', 'woot.com'))

    async def test_model_base_cluster(self):

        async with self.getTestCore() as core:
            guid = s_common.guid()
            q = '[(graph:cluster=$valu :name="Test Cluster" :desc="a test cluster" :type=similarity)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': guid}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('type'), 'similarity')
            self.eq(node.get('name'), 'test cluster')
            self.eq(node.get('desc'), 'a test cluster')

            await core.nodes('[(edge:refs=($ndef, (test:str, 1234)))]', opts={'vars': {'ndef': node.ndef}})
            await core.nodes('[(edge:refs=($ndef, (test:int, (1234))))]', opts={'vars': {'ndef': node.ndef}})

            # Gather up all the nodes in the cluster
            nodes = await core.nodes(f'graph:cluster=$valu -+> edge:refs -+> * | uniq', opts={'vars': {'valu': guid}})
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
                    :type=foo.bar
                    :text="while TRUE { BAD }"
                    :ext:id=WOOT-20 :url=https://vertex.link/rules/WOOT-20
                    <(has)+ { meta:ruleset }
                    +(matches)> { [inet:ipv4=123.123.123] }
                ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('author'))
            self.eq(nodes[0].get('type'), 'foo.bar.')
            self.eq(nodes[0].get('created'), 1580601600000)
            self.eq(nodes[0].get('updated'), 1648771200000)
            self.eq(nodes[0].get('name'), 'my rule')
            self.eq(nodes[0].get('desc'), 'My cool rule')
            self.eq(nodes[0].get('text'), 'while TRUE { BAD }')
            self.eq(nodes[0].get('url'), 'https://vertex.link/rules/WOOT-20')
            self.eq(nodes[0].get('ext:id'), 'WOOT-20')

            self.len(1, await core.nodes('meta:rule -> ps:contact'))
            self.len(1, await core.nodes('meta:rule -> meta:rule:type:taxonomy'))
            self.len(1, await core.nodes('meta:ruleset -> ps:contact'))
            self.len(1, await core.nodes('meta:ruleset -(has)> meta:rule -(matches)> *'))

    async def test_model_doc_strings(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('syn:type:doc="" -:ctor^="synapse.tests"')
            self.len(0, nodes)

            SYN_6315 = [
                'inet:dns:query:client', 'inet:dns:query:name', 'inet:dns:query:name:ipv4',
                'inet:dns:query:name:ipv6', 'inet:dns:query:name:fqdn', 'inet:dns:query:type',
                'inet:dns:request:time', 'inet:dns:request:query', 'inet:dns:request:query:name',
                'inet:dns:request:query:name:ipv4', 'inet:dns:request:query:name:ipv6',
                'inet:dns:request:query:name:fqdn', 'inet:dns:request:query:type',
                'inet:dns:request:server', 'inet:dns:answer:ttl', 'inet:dns:answer:request',
                'ou:team:org', 'ou:team:name', 'edge:has:n1', 'edge:has:n1:form', 'edge:has:n2',
                'edge:has:n2:form', 'edge:refs:n1', 'edge:refs:n1:form', 'edge:refs:n2',
                'edge:refs:n2:form', 'edge:wentto:n1', 'edge:wentto:n1:form', 'edge:wentto:n2',
                'edge:wentto:n2:form', 'edge:wentto:time', 'graph:edge:n1', 'graph:edge:n1:form',
                'graph:edge:n2', 'graph:edge:n2:form', 'graph:timeedge:time', 'graph:timeedge:n1',
                'graph:timeedge:n1:form', 'graph:timeedge:n2', 'graph:timeedge:n2:form',
                'ps:contact:asof', 'pol:country:iso2', 'pol:country:iso3', 'pol:country:isonum',
                'pol:country:tld', 'tel:mob:carrier:mcc', 'tel:mob:carrier:mnc',
                'tel:mob:telem:time', 'tel:mob:telem:latlong', 'tel:mob:telem:cell',
                'tel:mob:telem:cell:carrier', 'tel:mob:telem:imsi', 'tel:mob:telem:imei',
                'tel:mob:telem:phone', 'tel:mob:telem:mac', 'tel:mob:telem:ipv4',
                'tel:mob:telem:ipv6', 'tel:mob:telem:wifi', 'tel:mob:telem:wifi:ssid',
                'tel:mob:telem:wifi:bssid', 'tel:mob:telem:name', 'tel:mob:telem:email',
                'tel:mob:telem:app', 'tel:mob:telem:data',
                'inet:http:request:response:time', 'inet:http:request:response:code',
                'inet:http:request:response:reason', 'inet:http:request:response:body',
                'gov:us:cage:street', 'gov:us:cage:city', 'gov:us:cage:state', 'gov:us:cage:zip',
                'gov:us:cage:cc', 'gov:us:cage:country', 'gov:us:cage:phone0', 'gov:us:cage:phone1',
                'biz:rfp:requirements',
            ]

            nodes = await core.nodes('syn:prop:doc=""')
            keep = []
            skip = []
            for node in nodes:
                name = node.ndef[1]

                if name in SYN_6315:
                    skip.append(node)
                    continue

                if name.startswith('test:'):
                    continue

                keep.append(node)

            self.len(0, keep, msg=[node.ndef[1] for node in keep])
            self.len(len(SYN_6315), skip)

            for edge in core.model.edges.values():
                doc = edge.edgeinfo.get('doc')
                self.nn(doc)
                self.ge(len(doc), 3)

            for ifdef in core.model.ifaces.values():
                doc = ifdef.get('doc')
                self.nn(doc)
                self.ge(len(doc), 3)

    async def test_model_doc_deprecated(self):

        async with self.getTestCore() as core:

            # Check properties that have "deprecated" in the doc string. Skip "isnow" because it's
            # likely to have "deprecated" in the doc string due to what it does.
            nodes = await core.nodes('syn:prop:doc~="(?i)deprecate"')
            for node in nodes:
                prop = core.model.prop(node.ndef[1])
                if prop.name == 'isnow':
                    continue

                self.true(prop.deprecated, msg=prop)

            # Check types that have "deprecated" in the doc string.
            nodes = await core.nodes('syn:type:doc="(?i)deprecate"')
            for node in nodes:
                typo = core.model.type(node.ndef[1])
                self.true(typo.deprecated, msg=typo)

            # Check forms that have "deprecated" in the doc string.
            nodes = await core.nodes('syn:form:doc="(?i)deprecate"')
            for node in nodes:
                form = core.model.form(node.ndef[1])
                self.true(form.deprecated, msg=form)

    async def test_model_aggregate(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:aggregate=* :count=99 :type=bottles :time=20240202 ]')
            self.len(1, nodes)
            self.eq(99, nodes[0].get('count'))
            self.eq('bottles.', nodes[0].get('type'))
            self.eq(1706832000000, nodes[0].get('time'))
            self.len(1, await core.nodes('meta:aggregate -> meta:aggregate:type:taxonomy'))

    async def test_model_feed(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                meta:feed=*
                    :name="woot (foo bar baz)"
                    :type=foo.bar.baz
                    :source={[ meta:source=* :name=woot ]}
                    :url=https://v.vtx.lk/slack
                    :query="Hi There"
                    :opts=({"foo": "bar"})
                    :period=(2024,2025)
                    :latest=2025
                    :offset=17
                    :cursor=FooBar
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('source'))

            self.eq(nodes[0].get('name'), 'woot (foo bar baz)')
            self.eq(nodes[0].get('type'), 'foo.bar.baz.')
            self.eq(nodes[0].get('url'), 'https://v.vtx.lk/slack')
            self.eq(nodes[0].get('query'), 'Hi There')
            self.eq(nodes[0].get('opts'), {"foo": "bar"})
            self.eq(nodes[0].get('period'), (1704067200000, 1735689600000))
            self.eq(nodes[0].get('latest'), 1735689600000)
            self.eq(nodes[0].get('offset'), 17)
            self.eq(nodes[0].get('cursor'), 'FooBar')

            self.len(1, await core.nodes('meta:feed -> meta:source +:name=woot'))
            self.len(1, await core.nodes('meta:feed -> meta:feed:type:taxonomy'))
