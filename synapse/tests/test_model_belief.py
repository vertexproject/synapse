import synapse.tests.utils as s_test

class BeliefModelTest(s_test.SynTest):

    async def test_model_belief(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ belief:system=*
                    :name="Woot  Woot"
                    :desc="Lulz Gronk"
                    :type=hehe.haha
                    :began=20230209
                    +(has)> {[
                        (belief:tenet=* :name="Zip  Zop" :desc=Lol)
                        (belief:tenet=* :name="Blah Blah" :desc=Lol)
                    ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'woot woot')
            self.eq(nodes[0].get('desc'), 'Lulz Gronk')
            self.eq(nodes[0].get('type'), 'hehe.haha.')
            self.eq(nodes[0].get('began'), 1675900800000)

            self.len(2, await core.nodes('belief:system -(has)> belief:tenet +:desc=Lol'))

            nodes = await core.nodes('''[
                belief:subscriber=*
                    :contact={[ ps:contact=* :name=visi ]}
                    :system={ belief:system:type=hehe.haha }
                    :began=20230209
                    :ended=20230210
                    +(follows)> { belief:tenet:name="zip zop" }
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('system'))
            self.nn(nodes[0].get('contact'))

            self.eq(nodes[0].get('began'), 1675900800000)
            self.eq(nodes[0].get('ended'), 1675987200000)

            self.len(1, await core.nodes('belief:subscriber -(follows)> belief:tenet'))
