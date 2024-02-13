import synapse.lib.module as s_module

class ScienceModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('sci', {
            'types': (
                ('sci:hypothesis:type:taxonomy', {}, {}),
                ('sci:hypothesis', ('guid', {}), {
                    'doc': 'A hypothesis.'}),

                # TODO link experiment to eventual procedure node
                ('sci:experiment:type:taxonomy', {}, {}),
                ('sci:experiment', ('guid', {}), {
                    'doc': 'An instance of running an experiment to test a hypothesis.'}),

                ('sci:evidence', ('guid', {}), {
                    'doc': 'Evidence resulting from an experiement which supports or refutes a hypothesis.'}),
            ),

            'edges': (
                (('sci:experiment', 'uses', None), {
                    'doc': 'The experiement used the target nodes when it was run.'}),
                (('sci:evidence', 'has', None), {
                    'doc': 'The evidence includes observations from the target nodes.'}),
            ),

            'forms': (
                ('sci:hypothesis:type:taxonomy', {}, {}),
                ('sci:hypothesis', {}, (

                    ('name': ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the hypothesis.'}),

                    ('type', ('sci:hypothesis:type:taxonomy', {}), {
                        'doc': 'A taxonomy of hypothesis types.'}),

                    ('text': ('str', {}), {
                        'doc': 'The stated hypothesis.'}),
                )),

                ('sci:experiment', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the experiment.'}),

                    ('summary', ('str', {}), {
                        'doc': 'A description of the experiment and summary of results.'}),

                    ('type', ('sci:experiment:type:taxonomy', {}), {
                        'doc': 'A taxonomy of experiment types.'}),

                    ('window', ('ival', {}), {
                        'doc': 'The time window where the experiment was run.'}),

                )),

                ('sci:evidence', {}, (

                    ('experiment', ('sci:experiment', {}), {
                        'doc': 'The experiment which produced the evidence.'}),

                    ('summary', ('str', {}), {
                        'doc': 'A description of the evidence and how it supports or refutes the hypothesis.'}),

                    ('refutes', ('bool', {}), {
                        'doc': 'Set to true if the evidence refutes the hypothesis or false if it supports the hypothesis.'}),

                )),
            ),
        }),)
