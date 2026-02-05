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
            self.propeq(nodes[0], 'name', 'woot woot')
            self.propeq(nodes[0], 'desc', 'Lulz Gronk')
            self.propeq(nodes[0], 'type', 'hehe.haha.')
            self.propeq(nodes[0], 'began', 1675900800000000)

            self.len(2, await core.nodes('belief:system -(has)> belief:tenet +:desc=Lol'))

            nodes = await core.nodes('''[
                belief:subscriber=*
                    :contact={[ entity:contact=* :name=visi ]}
                    :system={ belief:system:type=hehe.haha }
                    :period=(20230209, 20230210)
                    +(follows)> { belief:tenet:name="zip zop" }
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('system'))
            self.nn(nodes[0].get('contact'))

            self.propeq(nodes[0], 'period', (1675900800000000, 1675987200000000, 86400000000))

            self.len(1, await core.nodes('belief:subscriber -(follows)> belief:tenet'))
