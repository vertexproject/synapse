import synapse.lib.module as s_module

class PlanModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('plan', {
            'types': (
                ('plan:system', ('guid', {}), {
                    'doc': 'A planning or behavioral analysis system that defines phases and procedures.'}),

                ('plan:phase', ('guid', {}), {
                    'doc': 'A phase within a planning system which may be used to group steps within a procedure.'}),

                ('plan:procedure', ('guid', {}), {
                    'doc': 'A procedure consisting of steps.'}),

                ('plan:procedure:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of procedure types.'}),

                ('plan:procedure:variable', ('guid', {}), {
                    'doc': 'A variable used by a procedure.'}),

                ('plan:procedure:step', ('guid', {}), {
                    'doc': 'A step within a procedure.'}),

                ('plan:procedure:link', ('guid', {}), {
                    'doc': 'A link between steps in a procedure.'}),
            ),

            'edges': (
                (('plan:procedure:step', 'uses', None), {
                    'doc': 'The step in the procedure makes use of the target node.'}),
            ),

            'forms': (
                ('plan:system', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': 'mitre att&ck flow',
                        'doc': 'The name of the planning system.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the purpose and use case for the planning system.'}),

                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact of the person or organization which authored the system.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the planning system was first created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the planning system was last updated.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The version of the planning system.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The primary URL which documents the planning system.'}),
                )),
                ('plan:phase', {}, (
                    ('title', ('str', {}), {
                        'ex': 'Reconnaissance Phase',
                        'doc': 'The title of the phase.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the definition of the phase.'}),

                    ('index', ('int', {}), {
                        'doc': 'The index of this phase within the phases of the system.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which links to the full documentation about the phase.'}),

                    ('system', ('plan:system', {}), {
                        'doc': 'The planning system which defines this phase.'}),
                )),
                ('plan:procedure:type:taxonomy', {}, ()),
                ('plan:procedure', {}, (

                    ('title', ('str', {}), {
                        'ex': 'Network Reconnaissance Procedure',
                        'doc': 'The name of the procedure.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the purpose and use cases for the procedure.'}),

                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact of the person or organization which authored the procedure.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the procedure was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the procedure was last updated.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The version of the procedure.'}),

                    ('system', ('plan:system', {}), {
                        'doc': 'The planning system which defines this procedure.'}),

                    ('type', ('plan:procedure:type:taxonomy', {}), {
                        'doc': 'A type classification for the procedure.'}),

                    ('inputs', ('array', {'type': 'plan:procedure:variable', 'uniq': True, 'sorted': True}), {
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

                    ('summary', ('str', {}), {
                        'doc': 'A summary of the tasks executed within the step.'}),

                    ('outputs', ('array', {'type': 'plan:procedure:variable', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of variables defined in this step.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of techniques used when executing this step.'}),

                    ('links', ('array', {'type': 'plan:procedure:link', 'uniq': True}), {
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
        }),)
