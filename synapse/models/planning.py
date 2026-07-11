modeldefs = (
    {
        'types': (
            ('plan:system', ('guid', {}), {
                'template': {'title': 'planning system'},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'ex': 'mitre att&ck flow',
                        'doc': 'The name of the planning system.'}),

                    ('url', None, {
                        'doc': 'The URL where the {title} is documented.'}),
                ),
                'doc': 'A planning or behavioral analysis system that defines phases and procedures.'}),

            ('plan:phase', ('guid', {}), {
                'template': {'title': 'phase'},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (

                    ('id', (
                        ('it:mitre:attack:tactic:id', {}),
                        ('base:id', {}),
                    ), {
                        'alts': ('ids',),
                        'doc': 'The phase ID.'}),

                    ('ids', (('it:mitre:attack:tactic:id', {}), ('base:id', {})), {
                        'array': {},
                        'doc': 'An array of alternate IDs for the phase.'}),

                    ('title', ('title', {}), {
                        'ex': 'Reconnaissance Phase',
                        'doc': 'The title of the phase.'}),

                    ('index', ('int', {}), {
                        'doc': 'The index of this phase within the phases of the system.'}),

                    ('url', None, {
                        'doc': 'The URL where the {title} is documented.'}),

                    ('system', ('plan:system', {}), {
                        'doc': 'The planning system which defines this phase.'}),
                ),
                'doc': 'A phase within a planning system which may be used to group steps within a procedure.'}),

            ('plan:procedure', ('guid', {}), {
                'template': {'title': 'procedure'},
                'interfaces': (
                    ('doc:document', {}),
                ),
                'props': (

                    ('system', ('plan:system', {}), {
                        'doc': 'The planning system which defines this procedure.'}),

                    ('type', ('plan:procedure:type:taxonomy', {}), {
                        'doc': 'A type classification for the procedure.'}),

                    ('inputs', ('plan:procedure:variable', {}), {
                        'array': {},
                        'doc': 'An array of inputs required to execute the procedure.'}),

                    ('firststep', ('plan:procedure:step', {}), {
                        'doc': 'The first step in the procedure.'}),
                ),
                'doc': 'A procedure consisting of steps.'}),

            ('plan:procedure:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of procedure types.'}),

            ('plan:procedure:variable', ('guid', {}), {
                'props': (

                    ('name', ('str', {}), {
                        'doc': 'The name of the variable.'}),

                    ('type', ('str', {}), {
                        'doc': 'The type for the input. Types are specific to the planning system.'}),

                    ('default', ('data', {}), {
                        'doc': 'The optional default value if the procedure is invoked without the input.'}),

                    ('procedure', ('plan:procedure', {}), {
                        'doc': 'The procedure which defines the variable.'}),
                ),
                'doc': 'A variable used by a procedure.'}),

            ('plan:procedure:step', ('guid', {}), {
                'props': (

                    ('phase', ('plan:phase', {}), {
                        'doc': 'The phase that the step belongs within.'}),

                    ('procedure', ('plan:procedure', {}), {
                        'doc': 'The procedure which defines the step.'}),

                    ('title', ('title', {}), {
                        'ex': 'Scan the IPv4 address range for open ports',
                        'doc': 'The title of the step.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the tasks executed within the step.'}),

                    ('outputs', ('plan:procedure:variable', {}), {
                        'array': {},
                        'doc': 'An array of variables defined in this step.'}),

                    ('links', ('plan:procedure:link', {}), {
                        'array': {'sorted': False},
                        'doc': 'An array of links to subsequent steps.'}),

                ),
                'doc': 'A step within a procedure.'}),

            ('plan:procedure:link', ('guid', {}), {
                'props': (

                    ('condition', ('bool', {}), {
                        'doc': 'Set to true/false if this link is conditional based on a decision step.'}),

                    ('next', ('plan:procedure:step', {}), {
                        'doc': 'The next step in the plan.'}),

                    ('procedure', ('plan:procedure', {}), {
                        'doc': 'The procedure which defines the link.'}),
                ),
                'doc': 'A link between steps in a procedure.'}),
        ),

        'edges': (
            (('plan:procedure:step', 'uses', 'meta:usable'), {
                'doc': 'The step in the procedure makes use of the target node.'}),
            (('plan:phase', 'uses', 'meta:usable'), {
                'doc': 'The plan phase makes use of the target node.'}),
        ),
    },
)
