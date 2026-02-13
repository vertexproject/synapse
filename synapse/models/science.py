modeldefs = (
    ('sci', {
        'types': (
            ('sci:hypothesis:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of hypothesis types.'}),

            ('sci:hypothesis', ('guid', {}), {
                'interfaces': (
                    ('meta:believable', {}),
                ),
                'doc': 'A hypothesis or theory.'}),

            # TODO link experiment to eventual procedure node
            ('sci:experiment:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of experiment types.'}),

            ('sci:experiment', ('guid', {}), {
                'doc': 'An instance of running an experiment.'}),

            ('sci:observation', ('entity:event', {}), {
                'template': {'title': 'observation'},
                'props': (
                    ('experiment', ('sci:experiment', {}), {
                        'doc': 'The experiment which produced the observation.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the observation.'}),
                ),
                'doc': 'An observation which may have resulted from an experiment.'}),

            ('sci:evidence', ('guid', {}), {
                'doc': 'An assessment of how an observation supports or refutes a hypothesis.'}),
        ),

        'edges': (

            (('sci:experiment', 'used', None), {
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

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the hypothesis.'}),

                ('type', ('sci:hypothesis:type:taxonomy', {}), {
                    'doc': 'The type of hypothesis as a user defined taxonomy.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the hypothesis.'}),
            )),

            # TODO eventually link to a procedure form
            ('sci:experiment:type:taxonomy', {}, {}),
            ('sci:experiment', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the experiment.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the experiment.'}),

                ('type', ('sci:experiment:type:taxonomy', {}), {
                    'doc': 'The type of experiment as a user defined taxonomy.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('window', 'time'),
                    'doc': 'The time period when the experiment was run.'}),

            )),
            ('sci:evidence', {}, (

                ('hypothesis', ('sci:experiment', {}), {
                    'doc': 'The hypothesis which the evidence supports or refutes.'}),

                ('observation', ('sci:observation', {}), {
                    'doc': 'The observation which supports or refutes the hypothesis.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of how the observation supports or refutes the hypothesis.'}),

                ('refutes', ('bool', {}), {
                    'doc': 'Set to true if the evidence refutes the hypothesis or false if it supports the hypothesis.'}),
            )),
        ),
    }),
)
