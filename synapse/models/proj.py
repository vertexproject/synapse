modeldefs = (
    {

        'types': (

            ('proj:sprint:status', ('str', {'enums': 'planned,current,completed'}), {
                'doc': 'A project sprint status.'}),

            ('proj:ticket:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of project task types.'}),

            ('proj:ticket', ('guid', {}), {
                'template': {'title': 'ticket'},
                'interfaces': (
                    ('meta:task', {}),
                ),
                'doc': 'A ticket in a project management system.'}),

            ('proj:project:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A type taxonomy for projects.'}),

            ('proj:sprint', ('guid', {}), {
                'doc': 'A timeboxed period to complete a set amount of work.'}),

            ('proj:project', ('guid', {}), {
                'doc': 'A project in a tasking system.'}),
        ),

        'edges': (

            (('proj:sprint', 'has', 'meta:task'), {
                'doc': 'The task was worked on during the sprint.'}),
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

                ('creator', ('entity:actor', {}), {
                    'doc': 'The actor who created the project.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the project was created.'}),

                ('platform', ('inet:service:platform', {}), {
                    'doc': 'The platform where the project is hosted.'}),
            )),

            ('proj:sprint', {}, (

                ('name', ('str', {}), {
                    'doc': 'The name of the sprint.'}),

                ('status', ('proj:sprint:status', {}), {
                    'doc': 'The sprint status.'}),

                ('project', ('proj:project', {}), {
                    'doc': 'The project containing the sprint.'}),

                ('creator', ('entity:actor', {}), {
                    'doc': 'The actor who created the sprint.'}),

                ('created', ('time', {}), {
                    'doc': 'The date the sprint was created.'}),

                ('period', ('ival', {}), {
                    'doc': 'The interval for the sprint.'}),

                ('desc', ('str', {}), {
                    'doc': 'A description of the sprint.'}),
            )),

            ('proj:ticket:type:taxonomy', {}, {}),
            ('proj:ticket', {}, (

                ('url', ('inet:url', {}), {
                    'prevnames': ('ext:url',),
                    'doc': 'A URL which contains details about the task.'}),

                ('name', ('str', {}), {
                    'doc': 'The name of the task.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the task.'}),

                ('points', ('int', {}), {
                    'doc': 'Optional SCRUM style story points value.'}),

                ('type', ('proj:ticket:type:taxonomy', {}), {
                    'doc': 'The type of task.',
                    'ex': 'bug'}),
            )),
        ),
    },
)
