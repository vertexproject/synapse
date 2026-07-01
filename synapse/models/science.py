modeldefs = (
    {
        'types': (
            ('sci:hypothesis:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of hypothesis types.'}),

            ('sci:hypothesis', ('guid', {}), {
                'template': {'title': 'hypothesis'},
                'interfaces': (
                    ('meta:believable', {}),
                ),
                'props': (

                    ('type', ('sci:hypothesis:type:taxonomy', {}), {
                        'doc': 'The type of hypothesis as a user defined taxonomy.'}),
                ),
                'doc': 'A hypothesis or theory.'}),

            # TODO link experiment to eventual procedure node
            ('sci:experiment:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of experiment types.'}),

            ('sci:experiment', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the experiment.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the experiment.'}),

                    ('type', ('sci:experiment:type:taxonomy', {}), {
                        'doc': 'The type of experiment as a user defined taxonomy.'}),

                    ('period', None, {
                        'prevnames': ('window', 'time'),
                        'doc': 'The time period when the experiment was run.'}),

                ),
                'doc': 'An instance of running an experiment.'}),

            ('sci:observation', ('guid', {}), {
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (

                    ('experiment', ('sci:experiment', {}), {
                        'doc': 'The experiment which produced the observation.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the observation.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the observation occurred.'}),
                ),
                'doc': 'An observation which may have resulted from an experiment.'}),

            ('sci:evidence', ('guid', {}), {
                'props': (

                    ('hypothesis', ('sci:hypothesis', {}), {
                        'doc': 'The hypothesis which the evidence supports or refutes.'}),

                    ('observation', ('sci:observation', {}), {
                        'doc': 'The observation which supports or refutes the hypothesis.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of how the observation supports or refutes the hypothesis.'}),

                    ('refutes', ('bool', {}), {
                        'doc': 'Set to true if the evidence refutes the hypothesis or false if it supports the hypothesis.'}),
                ),
                'doc': 'An assessment of how an observation supports or refutes a hypothesis.'}),
        ),

        'edges': (

            (('sci:observation', 'has', None), {
                'doc': 'The observations are summarized from the target nodes.'}),

            (('sci:evidence', 'has', None), {
                'doc': 'The evidence includes observations from the target nodes.'}),
        ),
    },
)
