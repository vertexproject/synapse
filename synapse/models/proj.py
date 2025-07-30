statusenums = (
    (0, 'new'),
    (10, 'in validation'),
    (20, 'in backlog'),
    (30, 'in sprint'),
    (40, 'in progress'),
    (50, 'in review'),
    (60, 'completed'),
    (70, 'done'),
    (80, 'blocked'),
)

modeldefs = (
    ('proj', {

        'interfaces': (

            ('proj:doable', {

                'doc': 'A common interface for tasks.',

                'template': {
                    'task': 'task'},

                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'The ID of the {task}.'}),

                    ('parent', ('proj:doable', {}), {
                        'doc': 'The parent task which includes this {task}.'}),

                    ('project', ('proj:project', {}), {
                        'doc': 'The project containing the {task}.'}),

                    ('status', ('int', {'enums': statusenums}), {
                        # TODO: make runtime setable int enum typeopts
                        'doc': 'The status of the {task}.'}),

                    ('sprint', ('proj:sprint', {}), {
                        'doc': 'The sprint that contains the {task}.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The priority of the {task}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the {task} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the {task} was last updated.'}),

                    ('due', ('time', {}), {
                        'doc': 'The time the {task} must be complete.'}),

                    ('completed', ('time', {}), {
                        'doc': 'The time the {task} was completed.'}),

                    ('creator', ('syn:user', {}), {
                        'doc': 'The user which created the {task}.'}),

                    ('assignee', ('syn:user', {}), {
                        'doc': 'The user assigned to complete the {task}.'}),

                    ('ext:creator', ('entity:contact', {}), {
                        'doc': 'The contact information of the creator from an external system.'}),

                    ('ext:assignee', ('entity:contact', {}), {
                        'doc': 'The contact information of the assignee from an external system.'}),
                ),
            }),
        ),
        'types': (

            ('proj:doable', ('ndef', {'interface': 'proj:doable'}), {
                'doc': 'Any node which implements the proj:doable interface.'}),

            ('proj:task:type:taxonomy', ('taxonomy', {}), {
                'prevnames': ('proj:ticket:type:taxonomy',),
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of project task types.'}),

            ('proj:task', ('guid', {}), {
                'prevnames': ('proj:ticket',),
                'interfaces': (
                    ('proj:doable', {'template': {'task': 'task'}}),
                ),
                'doc': 'A task.'}),

            ('proj:project:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A type taxonomy for projects.'}),

            ('proj:sprint', ('guid', {}), {
                'doc': 'A timeboxed period to complete a set amount of work.'}),

            ('proj:project', ('guid', {}), {
                'doc': 'A project in a ticketing system.'}),
        ),

        'edges': (

            (('meta:note', 'about', 'proj:task'), {
                'doc': 'The note is a comment about the task.'}),

            (('proj:doable', 'has', 'file:attachment'), {
                'doc': 'The task includes the file attachment.'}),
        ),

        'forms': (

            ('proj:project:type:taxonomy', {}, {}),
            ('proj:project', {}, (

                ('name', ('str', {}), {
                    'doc': 'The project name.'}),

                ('type', ('proj:project:type:taxonomy', {}), {
                    'doc': 'The project type.'}),

                ('desc', ('text', {}), {
                    'doc': 'The project description.'}),

                ('creator', ('syn:user', {}), {
                    'doc': 'The synapse user who created the project.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the project was created.'}),
            )),

            ('proj:sprint', {}, (

                ('name', ('str', {}), {
                    'doc': 'The name of the sprint.'}),

                ('status', ('str', {'enums': 'planned,current,completed'}), {
                    'doc': 'The sprint status.'}),

                ('project', ('proj:project', {}), {
                    'doc': 'The project containing the sprint.'}),

                ('creator', ('syn:user', {}), {
                    'doc': 'The synapse user who created the sprint.'}),

                ('created', ('time', {}), {
                    'doc': 'The date the sprint was created.'}),

                ('period', ('ival', {}), {
                    'doc': 'The interval for the sprint.'}),

                ('desc', ('str', {}), {
                    'doc': 'A description of the sprint.'}),
            )),

            ('proj:task:type:taxonomy', {}, {}),
            ('proj:task', {}, (

                ('url', ('inet:url', {}), {
                    'prevnames': ('ext:url',),
                    'doc': 'A URL which contains details about the task.'}),

                ('name', ('str', {}), {
                    'doc': 'The name of the ticket.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the ticket.'}),

                ('points', ('int', {}), {
                    'doc': 'Optional SCRUM style story points value.'}),

                ('type', ('proj:task:type:taxonomy', {}), {
                    'doc': 'The type of task.',
                    'ex': 'bug'}),
            )),
        ),
    }),
)
