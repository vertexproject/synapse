import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class SciModelTest(s_t_utils.SynTest):

    async def test_model_sci(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ sci:hypothesis=*
                    :name="Light  travels as a WAVE"
                    :type=physics.quantum
                    :summary="Light travels as a wave not a particle."
                ]
            ''')
            self.len(1, nodes)
            self.eq('physics.quantum.', nodes[0].get('type'))
            self.eq('light travels as a wave', nodes[0].get('name'))
            self.eq('Light travels as a wave not a particle.', nodes[0].get('summary'))

            nodes = await core.nodes('''
                [ sci:experiment=*
                    :name=double-slit
                    :time=2024-03-19
                    :type=lab.light
                    :summary="Foo bar baz."
                ]
            ''')
            self.len(1, nodes)
            self.eq(1710806400000, nodes[0].get('time'))
            self.eq('lab.light.', nodes[0].get('type'))
            self.eq('double-slit', nodes[0].get('name'))
            self.eq('Foo bar baz.', nodes[0].get('summary'))

            nodes = await core.nodes('''
                [ sci:evidence=*
                    :observation={[ sci:observation=*
                        :time=2024-03-19
                        :experiment={sci:experiment:name=double-slit}
                        :summary="Shadows cast on the wall in a diffusion pattern."
                    ]}
                    :hypothesis={ sci:hypothesis:name="light travels as a wave" }
                    :summary="Shadows in wave diffusion pattern support the hypothesis."
                    :refutes=(false)
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('hypothesis'))
            self.nn(nodes[0].get('observation'))
            self.eq(False, nodes[0].get('refutes'))
            self.eq("Shadows in wave diffusion pattern support the hypothesis.", nodes[0].get('summary'))

            nodes = await core.nodes('sci:observation')
            self.len(1, nodes)
            self.nn(nodes[0].get('experiment'))
            self.eq(1710806400000, nodes[0].get('time'))
            self.eq("Shadows cast on the wall in a diffusion pattern.", nodes[0].get('summary'))
