import synapse.lib.module as s_module

class ScienceModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('sci', {
            'types': (
                ('sci:hypothesis:type:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of hypothesis types.'}),
                ('sci:hypothesis', ('guid', {}), {
                    'doc': 'A hypothesis or theory.'}),

                # TODO link experiment to eventual procedure node
                ('sci:experiment:type:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of experiment types.'}),
                ('sci:experiment', ('guid', {}), {
                    'doc': 'An instance of running an experiment.'}),

                ('sci:observation', ('guid', {}), {
                    'doc': 'An observation which may have resulted from an experiment.'}),

                ('sci:evidence', ('guid', {}), {
                    'doc': 'An assessment of how an observation supports or refutes a hypothesis.'}),
            ),

            'edges': (
                (('sci:experiment', 'uses', None), {
                    'doc': 'The experiment used the target nodes when it was run.'}),
                (('sci:observation', 'has', None), {
                    'doc': 'The observations are summarized from the target nodes.'}),
                (('sci:evidence', 'has', None), {
                    'doc': 'The evidence includes observations from the target nodes.'}),
            ),

            'forms': (
                # TODO many of these forms need author/contact props
                ('sci:hypothesis:type:taxonomy', {}, {}),
                ('sci:hypothesis', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the hypothesis.'}),

                    ('type', ('sci:hypothesis:type:taxonomy', {}), {
                        'doc': 'The type of hypothesis as a user defined taxonomy.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the hypothesis.'}),
                )),

                # TODO eventually link to a procedure form
                ('sci:experiment:type:taxonomy', {}, {}),
                ('sci:experiment', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the experiment.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the experiment.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time when the experiment was initiated.'}),

                    ('type', ('sci:experiment:type:taxonomy', {}), {
                        'doc': 'The type of experiment as a user defined taxonomy.'}),

                    ('window', ('ival', {}), {
                        'doc': 'The time window where the experiment was run.'}),

                )),

                ('sci:observation', {}, (

                    ('experiment', ('sci:experiment', {}), {
                        'doc': 'The experiment which produced the observation.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the observation.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the observation occurred.'}),
                )),

                ('sci:evidence', {}, (

                    ('hypothesis', ('sci:experiment', {}), {
                        'doc': 'The hypothesis which the evidence supports or refutes.'}),

                    ('observation', ('sci:observation', {}), {
                        'doc': 'The observation which supports or refutes the hypothesis.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of how the observation supports or refutes the hypothesis.'}),

                    ('refutes', ('bool', {}), {
                        'doc': 'Set to true if the evidence refutes the hypothesis or false if it supports the hypothesis.'}),
                )),
            ),
        }),)
