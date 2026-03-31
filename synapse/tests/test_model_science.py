import synapse.tests.utils as s_t_utils

class SciModelTest(s_t_utils.SynTest):

    async def test_model_sci(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ sci:hypothesis=*
                    :name="Light  travels as a WAVE"
                    :type=physics.quantum
                    :desc="Light travels as a wave not a particle."
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'physics.quantum.')
            self.propeq(nodes[0], 'name', 'light travels as a wave')
            self.propeq(nodes[0], 'desc', 'Light travels as a wave not a particle.')

            nodes = await core.nodes('''
                [ sci:experiment=*
                    :name=double-slit
                    :period=(20240319, 20240320)
                    :type=lab.light
                    :desc="Foo bar baz."
                    :actor={[ entity:contact=* :name=feynman ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'lab.light.')
            self.propeq(nodes[0], 'name', 'double-slit')
            self.propeq(nodes[0], 'desc', 'Foo bar baz.')
            self.propeq(nodes[0], 'period', (1710806400000000, 1710892800000000, 86400000000))
            self.nn(nodes[0].get('actor'))
            self.len(1, await core.nodes('sci:experiment :actor -> entity:contact +:name=feynman'))

            nodes = await core.nodes('''
                [ sci:evidence=*
                    :observation={[ sci:observation=*
                        :time=2024-03-19
                        :actor={[ entity:contact=* :name=researcher ]}
                        :experiment={sci:experiment:name=double-slit}
                        :desc="Shadows cast on the wall in a diffusion pattern."
                    ]}
                    :hypothesis={ sci:hypothesis:name="light travels as a wave" }
                    :desc="Shadows in wave diffusion pattern support the hypothesis."
                    :refutes=(false)
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('hypothesis'))
            self.nn(nodes[0].get('observation'))
            self.propeq(nodes[0], 'refutes', False)
            self.propeq(nodes[0], 'desc', "Shadows in wave diffusion pattern support the hypothesis.")

            nodes = await core.nodes('sci:observation')
            self.len(1, nodes)
            self.nn(nodes[0].get('experiment'))
            self.nn(nodes[0].get('actor'))
            self.propeq(nodes[0], 'time', 1710806400000000)
            self.propeq(nodes[0], 'desc', "Shadows cast on the wall in a diffusion pattern.")
            self.len(1, await core.nodes('sci:observation :actor -> entity:contact +:name=researcher'))
