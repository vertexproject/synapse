import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils

class LangModuleTest(s_t_utils.SynTest):

    async def test_model_language(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                lang:translation=*
                    :input=Hola
                    :input:lang=ES
                    :output=Hi
                    :output:lang=en.us
                    :desc=Greetings
                    :engine=*
            ]''')
            self.len(1, nodes)
            self.eq('Hola', nodes[0].get('input'))
            self.eq('Hi', nodes[0].get('output'))
            self.eq('es', nodes[0].get('input:lang'))
            self.eq('en.us', nodes[0].get('output:lang'))
            self.eq('Greetings', nodes[0].get('desc'))
            self.len(1, await core.nodes('lang:translation -> it:prod:softver'))

            self.none(await core.callStorm('return($lib.gen.langByCode(neeeeewp, try=$lib.true))'))
            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('return($lib.gen.langByCode(neeeeewp))')

            nodes = await core.nodes('[ lang:phrase="For   The  People" ]')
            self.len(1, nodes)
            self.eq('for the people', nodes[0].repr())

    async def test_forms_idiom(self):
        async with self.getTestCore() as core:
            valu = 'arbitrary text 123'

            props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_ndef = ('lang:idiom', valu)

            opts = {'vars': {'valu': valu, 'p': props}}
            q = '[(lang:idiom=$valu :desc:en=$p."desc:en" :url=$p.url)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.ndef, expected_ndef)
            for prop, valu in expected_props.items():
                self.eq(node.get(prop), valu)

    async def test_forms_trans(self):
        async with self.getTestCore() as core:
            valu = 'arbitrary text 123'

            props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_ndef = ('lang:trans', valu)

            opts = {'vars': {'valu': valu, 'p': props}}
            q = '[(lang:trans=$valu :desc:en=$p."desc:en" :text:en=$p."text:en")]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.ndef, expected_ndef)
            for prop, valu in expected_props.items():
                self.eq(node.get(prop), valu)

    async def test_types_unextended(self):
        # The following types are subtypes that do not extend their base type
        async with self.getTestCore() as core:
            self.nn(core.model.type('lang:idiom'))  # str
            self.nn(core.model.type('lang:trans'))  # str
