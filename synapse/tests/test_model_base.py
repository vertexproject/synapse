import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class BaseTest(s_t_utils.SynTest):

    async def test_model_base_timeline(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ meta:timeline=* :title=Woot :desc=4LOLZ :type=lol.cats ]')
            self.len(1, nodes)
            nodes = await core.nodes('''
                [ meta:event=* :title=Zip :period=(202203211400, 202203211520) :index=0
                    :desc=Zop :type=zip.zop :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)
            self.eq(0, nodes[0].get('index'))
            nodes = await core.nodes('''[ meta:event=* :title=Hehe
                    :desc=Haha :period=(202203221400, 202203221600) :type=hehe.haha :timeline={meta:timeline:title=Woot} ]''')
            self.len(1, nodes)

            self.len(2, await core.nodes('meta:timeline +:title=Woot +:desc=4LOLZ +:type=lol.cats -> meta:event'))
            self.len(1, await core.nodes('meta:timeline -> meta:timeline:type:taxonomy'))
            self.len(2, await core.nodes('meta:event -> meta:event:type:taxonomy'))
            self.len(1, await core.nodes('meta:event +:title=Hehe +:desc=Haha +:period.duration=2:00:00 +:type=hehe.haha +:timeline'))

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
            self.len(1, await core.nodes('meta:note [ :author={[ entity:contact=* :name=visi ]} ]'))
            self.len(1, await core.nodes('entity:contact:name=visi -> meta:note'))
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

            self.eq(sorc.get('type'), 'osint.')
            self.eq(sorc.get('name'), 'foo bar')
            self.eq(sorc.get('url'), 'https://foo.bar/index.html')
            self.eq(sorc.get('ingest:offset'), 17)
            self.eq(sorc.get('ingest:cursor'), 'Woot Woot')
            self.eq(sorc.get('ingest:latest'), 1733356800000000)

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
            self.eq(nodes[0].get('created'), 1580601600000000)
            self.eq(nodes[0].get('updated'), 1648771200000000)
            self.eq(nodes[0].get('name'), 'My Rules')
            self.eq(nodes[0].get('desc'), 'My cool ruleset')

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
            self.eq(nodes[0].get('type'), 'foo.bar.')
            self.eq(nodes[0].get('created'), 1580601600000000)
            self.eq(nodes[0].get('updated'), 1648771200000000)
            self.eq(nodes[0].get('name'), 'My Rule')
            self.eq(nodes[0].get('desc'), 'My cool rule')
            self.eq(nodes[0].get('text'), 'while TRUE { BAD }')
            self.eq(nodes[0].get('url'), 'https://vertex.link/rules/WOOT-20')
            self.eq(nodes[0].get('id'), 'WOOT-20')

            self.len(1, await core.nodes('meta:rule -> entity:contact'))
            self.len(1, await core.nodes('meta:rule -> meta:rule:type:taxonomy'))
            self.len(1, await core.nodes('meta:ruleset -> entity:contact'))
            self.len(1, await core.nodes('meta:ruleset -(has)> meta:rule -(matches)> *'))

    async def test_model_doc_strings(self):

        self.skip('FIXME - do we wanna just mop these up?')
        async with self.getTestCore() as core:

            nodes = await core.nodes('syn:type:doc="" -:ctor^="synapse.tests"')
            self.len(0, nodes)

            SYN_6315 = [
                'inet:dns:query:client', 'inet:dns:query:name', 'inet:dns:query:name:ip',
                'inet:dns:query:name:fqdn', 'inet:dns:query:type',
                'inet:dns:request:time', 'inet:dns:request:query', 'inet:dns:request:query:name',
                'inet:dns:request:query:name:ip',
                'inet:dns:request:query:name:fqdn', 'inet:dns:request:query:type',
                'inet:dns:request:server', 'inet:dns:answer:ttl', 'inet:dns:answer:request',
                'ou:team:org', 'ou:team:name',
                'entity:contact:asof', 'pol:country:iso2', 'pol:country:iso3', 'pol:country:isonum',
                'pol:country:tld', 'tel:mob:carrier:mcc', 'tel:mob:carrier:mnc',
                'tel:mob:telem:time', 'tel:mob:telem:latlong', 'tel:mob:telem:cell',
                'tel:mob:telem:cell:carrier', 'tel:mob:telem:imsi', 'tel:mob:telem:imei',
                'tel:mob:telem:phone', 'tel:mob:telem:mac', 'tel:mob:telem:ip',
                'tel:mob:telem:wifi:ap', 'tel:mob:telem:wifi:ap:ssid', 'tel:mob:telem:wifi:ap:bssid',
                'tel:mob:telem:name', 'tel:mob:telem:email',
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
                    skip.append(node.form.name)
                    continue

                if name.startswith('test:'):
                    continue

                keep.append(node)

            self.len(0, keep, msg=[node.ndef[1] for node in keep])
            self.sorteq(SYN_6315, skip)

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
            self.eq(1706832000000000, nodes[0].get('time'))
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

            self.eq(nodes[0].get('id'), 'feed/THING/my rss feed')
            self.eq(nodes[0].get('name'), 'woot (foo bar baz)')
            self.eq(nodes[0].get('type'), 'foo.bar.baz.')
            self.eq(nodes[0].get('url'), 'https://v.vtx.lk/slack')
            self.eq(nodes[0].get('query'), 'Hi There')
            self.eq(nodes[0].get('opts'), {"foo": "bar"})
            self.eq(nodes[0].get('period'), (1704067200000000, 1735689600000000, 31622400000000))
            self.eq(nodes[0].get('latest'), 1735689600000000)
            self.eq(nodes[0].get('offset'), 17)
            self.eq(nodes[0].get('cursor'), 'FooBar')

            self.len(1, await core.nodes('meta:feed -> meta:source +:name=woot'))
            self.len(1, await core.nodes('meta:feed -> meta:feed:type:taxonomy'))
