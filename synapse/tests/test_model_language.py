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
            self.eq('hola', nodes[0].get('input'))
            self.eq('hi', nodes[0].get('output'))
            self.eq('es', nodes[0].get('input:lang'))
            self.eq('en.us', nodes[0].get('output:lang'))
            self.eq('Greetings', nodes[0].get('desc'))
            self.len(1, await core.nodes('lang:translation -> it:software'))

            self.none(await core.callStorm('return($lib.gen.langByCode(neeeeewp, try=$lib.true))'))
            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('return($lib.gen.langByCode(neeeeewp))')

            nodes = await core.nodes('[ lang:phrase="For   The  People" ]')
            self.len(1, nodes)
            self.eq('for the people', nodes[0].repr())

            nodes = await core.nodes('''
                [ lang:statement=*
                    :time=20150823
                    :speaker={[ ps:person=({"name": "visi"}) ]}
                    :text="We should be handing out UNCs like candy."
                    :transcript={[ ou:meet=* ]}
                    :transcript:offset=02:00
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('time'), 1440288000000000)
            self.eq(nodes[0].get('transcript:offset'), 120000000)
            self.eq(nodes[0].get('text'), 'We should be handing out UNCs like candy.')
            self.len(1, await core.nodes('lang:statement :speaker -> ps:person +:name=visi'))
            self.len(1, await core.nodes('lang:statement :transcript -> ou:meet'))
