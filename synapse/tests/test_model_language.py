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
