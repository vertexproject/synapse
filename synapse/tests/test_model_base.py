import synapse.tests.utils as s_t_utils

class BaseTest(s_t_utils.SynTest):

    async def test_model_base_timeline(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:timeline=* :title=Woot :desc=4LOLZ :type=lol.cats ]')
            self.len(1, nodes)
            nodes = await core.nodes('''[
                meta:event=* :title=Hehe
                    :desc=Haha
                    :time=202203221400
                    :type=hehe.haha
                    <(has)+ {meta:timeline:title=Woot}
                    +(about)> {[ inet:fqdn=vertex.link ]}
            ]''')
            self.len(1, nodes)

            self.len(1, await core.nodes('meta:timeline +:title=Woot +:desc=4LOLZ +:type=lol.cats -(has)> meta:event'))
            self.len(1, await core.nodes('meta:timeline -> meta:timeline:type:taxonomy'))

            self.len(1, await core.nodes('meta:event -(about)> inet:fqdn'))
            self.len(1, await core.nodes('meta:event <(has)- meta:timeline'))
            self.len(1, await core.nodes('meta:event -> meta:event:type:taxonomy'))
            self.len(1, await core.nodes('meta:event +:title=Hehe +:desc=Haha +:type=hehe.haha'))

    async def test_model_base_meta_taxonomy(self):
        async with self.getTestCore() as core:
            q = '''
            $info = ({"doc": "test taxonomy", "interfaces": [["meta:taxonomy", {}]]})
            $lib.model.ext.addForm(_test:taxonomy, taxonomy, ({}), $info)
            '''
            await core.callStorm(q)
            nodes = await core.nodes('[_test:taxonomy=foo.bar.baz :name="title words" :desc="a test taxonomy" :sort=1 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('_test:taxonomy', 'foo.bar.baz.'))
            self.propeq(node, 'name', 'title words')
            self.propeq(node, 'desc', 'a test taxonomy')
            self.propeq(node, 'sort', 1)
            self.propeq(node, 'base', 'baz')
            self.propeq(node, 'depth', 2)
            self.propeq(node, 'parent', 'foo.bar.')

    async def test_model_base_note(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add --type hehe.haha "foo bar baz"')
            self.len(2, nodes)
            self.len(1, await core.nodes('meta:note'))
            self.len(1, await core.nodes('meta:note:created<=now'))
            self.len(1, await core.nodes('meta:note:updated<=now'))
            self.len(1, await core.nodes('meta:note:created +(:created = :updated)'))
            self.len(1, await core.nodes('meta:note:creator=$lib.auth.users.get().iden'))
            self.len(1, await core.nodes('meta:note:text="foo bar baz"'))
            self.len(2, await core.nodes('meta:note -(about)> inet:fqdn'))
            self.len(1, await core.nodes('meta:note [ :creator={[ entity:contact=* :name=visi ]} ]'))
            self.len(1, await core.nodes('entity:contact:name=visi -> meta:note'))
            self.len(1, await core.nodes('meta:note:type=hehe.haha -> meta:note:type:taxonomy'))

            # meta:note implements entity:creatable
            self.true(core.model.form('meta:note').implements('entity:creatable'))
            self.len(1, await core.nodes('meta:note [ :creator:name=visi ] +:creator:name=visi'))

            # Notes are always unique when made by note.add
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add "foo bar baz"')
            self.len(2, await core.nodes('meta:note'))
            self.ne(nodes[0].ndef, nodes[1].ndef)
            self.eq(nodes[0].get('text'), nodes[1].get('text'))

            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add --yield "yieldnote"')
            self.len(1, nodes)
            self.propeq(nodes[0], 'text', 'yieldnote')

            nodes = await core.nodes('note.add --yield "nonodes" | [ :replyto=* as meta:note ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'text', 'nonodes')
            self.nn(nodes[0].get('created'))
            self.nn(nodes[0].get('updated'))

            self.len(0, await core.nodes('meta:note:text=nonodes -(about)> *'))
            self.len(1, await core.nodes('meta:note:text=nonodes -> meta:note'))

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

            self.propeq(sorc, 'type', 'osint.')
            self.propeq(sorc, 'name', 'FOO Bar')
            self.propeq(sorc, 'url', 'https://foo.bar/index.html')
            self.propeq(sorc, 'ingest:offset', 17)
            self.propeq(sorc, 'ingest:cursor', 'Woot Woot')
            self.propeq(sorc, 'ingest:latest', 1733356800000000)

            valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))

    async def test_model_base_rules(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ meta:ruleset=*
                    :created=20200202 :updated=20220401 :creator={[ entity:contact=* ]}
                    :name=" My Rules" :desc="My cool ruleset" ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('creator'))
            self.propeq(nodes[0], 'created', 1580601600000000)
            self.propeq(nodes[0], 'updated', 1648771200000000)
            self.propeq(nodes[0], 'name', 'My Rules')
            self.propeq(nodes[0], 'desc', 'My cool ruleset')

            nodes = await core.nodes('''
                [ meta:rule=*
                    :created=20200202 :updated=20220401 :creator={[ entity:contact=* ]}
                    :name=" My Rule" :desc="My cool rule"
                    :type=foo.bar
                    :status=disabled.falsepos
                    :text="while TRUE { BAD }"
                    :id=WOOT-20 :url=https://vertex.link/rules/WOOT-20
                    :seen=(20200101, 20200201)
                    <(has)+ { meta:ruleset }
                    +(matches)> { [inet:ip=123.123.123.123] }
                ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('creator'))
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'status', 'disabled.falsepos')
            self.propeq(nodes[0], 'created', 1580601600000000)
            self.propeq(nodes[0], 'updated', 1648771200000000)
            self.propeq(nodes[0], 'name', 'My Rule')
            self.propeq(nodes[0], 'desc', 'My cool rule')
            self.propeq(nodes[0], 'text', 'while TRUE { BAD }')
            self.propeq(nodes[0], 'url', 'https://vertex.link/rules/WOOT-20')
            self.propeq(nodes[0], 'id', 'WOOT-20')

            self.len(1, await core.nodes('meta:rule -> entity:contact'))
            self.len(1, await core.nodes('meta:rule -> meta:rule:type:taxonomy'))
            self.len(1, await core.nodes('meta:ruleset -> entity:contact'))
            self.len(1, await core.nodes('meta:ruleset -(has)> meta:rule -(matches)> *'))

    async def test_model_doc_strings(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('syn:type:doc="" -:ctor^="synapse.tests"')
            self.len(0, nodes)

            nodes = await core.nodes('syn:prop:doc=""')
            keep = []
            for node in nodes:
                name = node.ndef[1]

                if name.startswith('test:'):
                    continue

                keep.append(node)

            self.len(0, keep, msg=[node.ndef[1] for node in keep])

            for edge in core.model.edges.values():
                doc = edge.edgeinfo.get('doc')
                self.nn(doc)
                self.ge(len(doc), 3)

            for name, ifdef in core.model.ifaces.items():
                doc = ifdef.get('doc')
                self.nn(doc, msg=f'Interface has not doc: {name}')
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
            self.propeq(nodes[0], 'count', 99)
            self.propeq(nodes[0], 'type', 'bottles.')
            self.propeq(nodes[0], 'time', 1706832000000000)
            self.len(1, await core.nodes('meta:aggregate -> meta:aggregate:type:taxonomy'))

    async def test_model_cluster(self):

        async with self.getTestCore() as core:

            self.true(core.model.form('meta:cluster').implements('meta:reported'))

            org0 = (await core.nodes('[ ou:org=* ]'))[0].ndef[1]

            nodes = await core.nodes('''[
                meta:cluster=*
                    :id=" 1234-5678 "
                    :ids=(" alt-id-1 ", " alt-id-2 ")
                    :name="activity cluster 1"
                    :names=("cluster one", "cluster alpha")
                    :type=fraud.scam
                    :desc="A cluster of scam-related addresses."
                    :tag=rep.vertex.cluster.1234
                    :reporter={ ou:org=$org }
                    :reporter:name=vertex
                    :reporter:url=https://vertex.link/clusters/1234
                    :reporter:period=(2020, 2023)
                    :reporter:deprecated=20230101
                    :reporter:supersedes={[ meta:cluster=* :name="old cluster" ]}
            ]''', opts={'vars': {'org': org0}})
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'id', '1234-5678')
            self.propeq(node, 'ids', ('alt-id-1', 'alt-id-2'))
            self.propeq(node, 'name', 'activity cluster 1')
            self.propeq(node, 'names', ('cluster alpha', 'cluster one'))
            self.propeq(node, 'type', 'fraud.scam.')
            self.propeq(node, 'desc', 'A cluster of scam-related addresses.')
            self.propeq(node, 'tag', 'rep.vertex.cluster.1234')
            self.propeq(node, 'reporter', org0)
            self.propeq(node, 'reporter:name', 'vertex')
            self.propeq(node, 'reporter:url', 'https://vertex.link/clusters/1234')
            self.propeq(node, 'reporter:deprecated', 1672531200000000)

            # meta:reported uses an ival :reporter:period with created/removed virts and no longer has a :created prop
            self.none(core.model.form('meta:cluster').prop('created'))
            self.eq(1577836800000000, node.get('reporter:period.created'))
            self.eq(1672531200000000, node.get('reporter:period.removed'))
            self.len(1, await core.nodes('meta:cluster +:reporter:period.created>=2019'))
            self.len(0, await core.nodes('meta:cluster +:reporter:period.created>=2021'))
            self.len(1, await core.nodes('meta:cluster:name="activity cluster 1" :reporter:supersedes -> meta:cluster +:name="old cluster"'))
            self.len(1, await core.nodes('meta:cluster -> meta:cluster:type:taxonomy'))

    async def test_model_feed(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                meta:feed=*
                    :id="feed/THING/my rss feed     "
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

            self.propeq(nodes[0], 'id', 'feed/THING/my rss feed')
            self.propeq(nodes[0], 'name', 'woot (foo bar baz)')
            self.propeq(nodes[0], 'type', 'foo.bar.baz.')
            self.propeq(nodes[0], 'url', 'https://v.vtx.lk/slack')
            self.propeq(nodes[0], 'query', 'Hi There')
            self.propeq(nodes[0], 'opts', {"foo": "bar"})
            self.propeq(nodes[0], 'period', (1704067200000000, 1735689600000000, 31622400000000))
            self.propeq(nodes[0], 'latest', 1735689600000000)
            self.propeq(nodes[0], 'offset', 17)
            self.propeq(nodes[0], 'cursor', 'FooBar')

            self.len(1, await core.nodes('meta:feed -> meta:source +:name=woot'))
            self.len(1, await core.nodes('meta:feed -> meta:feed:type:taxonomy'))

    async def test_model_meta_algorithm(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ meta:algorithm=*
                    :name="sha-256"
                    :type=crypto.hash
                    :desc="A cryptographic hash function."
                    :created=20200101
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'sha-256')
            self.propeq(nodes[0], 'type', 'crypto.hash.')
            self.propeq(nodes[0], 'desc', 'A cryptographic hash function.')
            self.propeq(nodes[0], 'created', 1577836800000000)

            self.len(1, await core.nodes('meta:algorithm -> meta:algorithm:type:taxonomy'))

            # edges
            nodes = await core.nodes('''
                [ it:software=*
                    +(uses)> { meta:algorithm:name=sha-256 }
                ]
            ''')
            self.len(1, await core.nodes('it:software -(uses)> meta:algorithm'))

            nodes = await core.nodes('''
                [ file:bytes="*"
                    +(uses)> { meta:algorithm:name=sha-256 }
                ]
            ''')
            self.len(1, await core.nodes('file:bytes -(uses)> meta:algorithm'))

            nodes = await core.nodes('''
                meta:algorithm:name=sha-256
                [ +(generated)> { [inet:ip=1.2.3.4] } ]
            ''')
            self.len(1, await core.nodes('meta:algorithm -(generated)> inet:ip'))

    async def test_model_base_meta_activity(self):

        async with self.getTestCore() as core:

            form = core.model.form('meta:activity')
            self.true(form.implements('entity:attendable'))
            self.true(form.implements('base:activity'))

            nodes = await core.nodes('''
                [ meta:activity=*
                    :name="company offsite"
                    :desc="annual offsite"
                    :period=(20250101, 20250102)
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'company offsite')
            self.propeq(nodes[0], 'period', (1735689600000000, 1735776000000000, 86400000000))

            self.len(1, await core.nodes('''
                [ entity:attended=*
                    :actor={[ ps:person=* ]}
                    :activity={ meta:activity:name="company offsite" }
                    :inperson=0
                ]
            '''))
            self.len(1, await core.nodes('entity:attended :activity -> meta:activity +:name="company offsite"'))

    async def test_model_base_meta_task(self):

        async with self.getTestCore() as core:

            for fname in ('proj:ticket', 'risk:alert', 'risk:vulnerable', 'ou:enacted', 'it:dev:repo:issue'):
                form = core.model.form(fname)
                self.true(form.implements('meta:task'))
                self.true(form.implements('entity:participable'))
                self.true(form.implements('base:activity'))
                self.true(form.implements('meta:causal'))

            nodes = await core.nodes('''
                [ proj:ticket=*
                    :name=tkt
                    :period=(20250101, 20250201)
                    :creator={[ syn:user=root ]}
                    :created=20250101
                ]
            ''')
            self.propeq(nodes[0], 'period', (1735689600000000, 1738368000000000, 2678400000000))

            self.len(1, await core.nodes('''
                [ entity:participated=*
                    :actor={[ syn:user=root ]}
                    :activity={ proj:ticket:name=tkt }
                    :role=reporter
                ]
            '''))
            self.len(1, await core.nodes('entity:participated:role=reporter :activity -> proj:ticket +:name=tkt'))

            self.len(1, await core.nodes('[ ( proj:ticket=* :name=src ) +(ledto)> { proj:ticket:name=tkt } ]'))
            self.len(1, await core.nodes('proj:ticket:name=src -(ledto)> proj:ticket'))
