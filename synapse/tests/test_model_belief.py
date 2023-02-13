import synapse.tests.utils as s_test

class BeliefModelTest(s_test.SynTest):

    async def test_model_belief(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ belief:system=* :name="Woot  Woot" :type=hehe.haha :began=20230209 ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'woot woot')
            self.eq(nodes[0].get('type'), 'hehe.haha.')
            self.eq(nodes[0].get('began'), 1675900800000)

            nodes = await core.nodes('''[
                belief:subscriber=*
                    :contact={[ ps:contact=* :name=visi ]}
                    :system={ belief:system:type=hehe.haha }
                    :began=20230209
                    :ended=20230210
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('system'))
            self.nn(nodes[0].get('contact'))

            self.eq(nodes[0].get('began'), 1675900800000)
            self.eq(nodes[0].get('ended'), 1675987200000)
