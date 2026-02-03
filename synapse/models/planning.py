modeldefs = (
    ('plan', {
        'types': (
            ('plan:system', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'title': 'planning system'}}),
                ),
                'doc': 'A planning or behavioral analysis system that defines phases and procedures.'}),

            ('plan:phase', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {
                        'document': 'phase',
                        'title': 'phase'}}),
                ),
                'doc': 'A phase within a planning system which may be used to group steps within a procedure.'}),

            ('plan:procedure', ('guid', {}), {
                'interfaces': (
                    ('doc:document', {'template': {
                        'document': 'procedure',
                        'title': 'procedure'}}),
                ),
                'doc': 'A procedure consisting of steps.'}),

            ('plan:procedure:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of procedure types.'}),

            ('plan:procedure:variable', ('guid', {}), {
                'doc': 'A variable used by a procedure.'}),

            ('plan:procedure:step', ('guid', {}), {
                'doc': 'A step within a procedure.'}),

            ('plan:procedure:link', ('guid', {}), {
                'doc': 'A link between steps in a procedure.'}),
        ),

        'edges': (
            (('plan:procedure:step', 'uses', 'meta:usable'), {
                'doc': 'The step in the procedure makes use of the target node.'}),
            (('plan:phase', 'uses', 'meta:usable'), {
                'doc': 'The plan phase makes use of the target node.'}),
        ),

        'forms': (
            ('plan:system', {}, (

                ('name', ('meta:name', {}), {
                    'ex': 'mitre att&ck flow',
                    'doc': 'The name of the planning system.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the planning system.'}),

                ('author', ('entity:actor', {}), {
                    'doc': 'The contact of the person or organization which authored the system.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the planning system was first created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the planning system was last updated.'}),

                ('version', ('it:version', {}), {
                    'doc': 'The version of the planning system.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The primary URL which documents the planning system.'}),
            )),
            ('plan:phase', {}, (

                ('title', ('str', {}), {
                    'ex': 'Reconnaissance Phase',
                    'doc': 'The title of the phase.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the definition of the phase.'}),

                ('index', ('int', {}), {
                    'doc': 'The index of this phase within the phases of the system.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which links to the full documentation about the phase.'}),

                ('system', ('plan:system', {}), {
                    'doc': 'The planning system which defines this phase.'}),
            )),
            ('plan:procedure:type:taxonomy', {}, ()),
            ('plan:procedure', {}, (

                ('system', ('plan:system', {}), {
                    'doc': 'The planning system which defines this procedure.'}),

                ('type', ('plan:procedure:type:taxonomy', {}), {
                    'doc': 'A type classification for the procedure.'}),

                ('inputs', ('array', {'type': 'plan:procedure:variable'}), {
                    'doc': 'An array of inputs required to execute the procedure.'}),

                ('firststep', ('plan:procedure:step', {}), {
                    'doc': 'The first step in the procedure.'}),
            )),
            ('plan:procedure:variable', {}, (

                ('name', ('str', {}), {
                    'doc': 'The name of the variable.'}),

                ('type', ('str', {}), {
                    'doc': 'The type for the input. Types are specific to the planning system.'}),

                ('default', ('data', {}), {
                    'doc': 'The optional default value if the procedure is invoked without the input.'}),

                ('procedure', ('plan:procedure', {}), {
                    'doc': 'The procedure which defines the variable.'}),
            )),
            ('plan:procedure:step', {}, (

                ('phase', ('plan:phase', {}), {
                    'doc': 'The phase that the step belongs within.'}),

                ('procedure', ('plan:procedure', {}), {
                    'doc': 'The procedure which defines the step.'}),

                ('title', ('str', {}), {
                    'ex': 'Scan the IPv4 address range for open ports',
                    'doc': 'The title of the step.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the tasks executed within the step.'}),

                ('outputs', ('array', {'type': 'plan:procedure:variable'}), {
                    'doc': 'An array of variables defined in this step.'}),

                ('links', ('array', {'type': 'plan:procedure:link', 'sorted': False}), {
                    'doc': 'An array of links to subsequent steps.'}),

            )),
            ('plan:procedure:link', {}, (

                ('condition', ('bool', {}), {
                    'doc': 'Set to true/false if this link is conditional based on a decision step.'}),

                ('next', ('plan:procedure:step', {}), {
                    'doc': 'The next step in the plan.'}),

                ('procedure', ('plan:procedure', {}), {
                    'doc': 'The procedure which defines the link.'}),
            )),
        ),
    }),
)
