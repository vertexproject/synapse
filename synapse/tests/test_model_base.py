import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class BaseTest(s_t_utils.SynTest):

    async def test_model_base_timeline(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:timeline=* :title=Woot :desc=4LOLZ :type=lol.cats ]')
            self.len(1, nodes)
            nodes = await core.nodes('''[
                meta:event=* :title=Hehe
                    :desc=Haha :period=(202203221400, 202203221600)
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
            self.len(1, await core.nodes('meta:event +:title=Hehe +:desc=Haha +:period.duration=2:00:00 +:type=hehe.haha'))

    async def test_model_base_meta_taxonomy(self):
        async with self.getTestCore() as core:
            q = '''
            $info = ({"doc": "test taxonomy", "interfaces": [["meta:taxonomy", {}]]})
            $lib.model.ext.addForm(_test:taxonomy, taxonomy, ({}), $info)
            '''
            await core.callStorm(q)
            nodes = await core.nodes('[_test:taxonomy=foo.bar.baz :title="title words" :desc="a test taxonomy" :sort=1 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('_test:taxonomy', 'foo.bar.baz.'))
            self.propeq(node, 'title', 'title words')
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
            self.len(1, await core.nodes('meta:note:creator=(syn:user, $lib.user.iden)'))
            self.len(1, await core.nodes('meta:note:text="foo bar baz"'))
            self.len(2, await core.nodes('meta:note -(about)> inet:fqdn'))
            self.len(1, await core.nodes('meta:note [ :creator={[ entity:contact=* :name=visi ]} ]'))
            self.len(1, await core.nodes('entity:contact:name=visi -> meta:note'))
            self.len(1, await core.nodes('meta:note:type=hehe.haha -> meta:note:type:taxonomy'))

            # Notes are always unique when made by note.add
            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add "foo bar baz"')
            self.len(2, await core.nodes('meta:note'))
            self.ne(nodes[0].ndef, nodes[1].ndef)
            self.eq(nodes[0].get('text'), nodes[1].get('text'))

            nodes = await core.nodes('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] | note.add --yield "yieldnote"')
            self.len(1, nodes)
            self.propeq(nodes[0], 'text', 'yieldnote')

            nodes = await core.nodes('note.add --yield "nonodes" | [ :replyto=* ]')
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
            self.propeq(sorc, 'name', 'foo bar')
            self.propeq(sorc, 'url', 'https://foo.bar/index.html')
            self.propeq(sorc, 'ingest:offset', 17)
            self.propeq(sorc, 'ingest:cursor', 'Woot Woot')
            self.propeq(sorc, 'ingest:latest', 1733356800000000)

            valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))

    async def test_model_base_rules(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ meta:ruleset=*
                    :created=20200202 :updated=20220401 :author={[ entity:contact=* ]}
                    :name=" My Rules" :desc="My cool ruleset" ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('author'))
            self.propeq(nodes[0], 'created', 1580601600000000)
            self.propeq(nodes[0], 'updated', 1648771200000000)
            self.propeq(nodes[0], 'name', 'My Rules')
            self.propeq(nodes[0], 'desc', 'My cool ruleset')

            nodes = await core.nodes('''
                [ meta:rule=*
                    :created=20200202 :updated=20220401 :author={[ entity:contact=* ]}
                    :name=" My Rule" :desc="My cool rule"
                    :type=foo.bar
                    :text="while TRUE { BAD }"
                    :id=WOOT-20 :url=https://vertex.link/rules/WOOT-20
                    <(has)+ { meta:ruleset }
                    +(matches)> { [inet:ip=123.123.123.123] }
                ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('author'))
            self.propeq(nodes[0], 'type', 'foo.bar.')
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
            self.propeq(nodes[0], 'count', 99)
            self.propeq(nodes[0], 'type', 'bottles.')
            self.propeq(nodes[0], 'time', 1706832000000000)
            self.len(1, await core.nodes('meta:aggregate -> meta:aggregate:type:taxonomy'))

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
