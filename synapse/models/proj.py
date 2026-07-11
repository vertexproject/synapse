modeldefs = (
    {

        'types': (


            ('proj:ticket:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of project task types.'}),

            ('proj:ticket', ('guid', {}), {
                'template': {'title': 'ticket'},
                'interfaces': (
                    ('meta:task', {}),
                ),
                'props': (

                    ('url', ('inet:url', {}), {
                        'prevnames': ('ext:url',),
                        'doc': 'A URL which contains details about the task.'}),

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the task.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the task.'}),

                    ('points', ('int', {}), {
                        'doc': 'Optional SCRUM style story points value.'}),

                    ('type', ('proj:ticket:type:taxonomy', {}), {
                        'doc': 'The type of task.',
                        'ex': 'bug'}),
                ),
                'doc': 'A ticket in a project management system.'}),

            ('proj:project:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A type taxonomy for projects.'}),

            ('proj:sprint', ('guid', {}), {
                'interfaces': (
                    ('base:activity', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the sprint.'}),

                    ('status', ('title', {}), {
                        'doc': 'The sprint status.'}),

                    ('project', ('proj:project', {}), {
                        'doc': 'The project containing the sprint.'}),

                    ('creator', ('entity:actor', {}), {
                        'doc': 'The actor who created the sprint.'}),

                    ('created', ('time', {}), {
                        'doc': 'The date the sprint was created.'}),

                    ('period', None, {
                        'doc': 'The interval for the sprint.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the sprint.'}),
                ),
                'doc': 'A timeboxed period to complete a set amount of work.'}),

            ('proj:project', ('guid', {}), {
                'template': {'title': 'project'},
                'interfaces': (
                    ('econ:budgetable', {}),
                    ('entity:creatable', {}),
                    ('entity:participable', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The project name.'}),

                    ('type', ('proj:project:type:taxonomy', {}), {
                        'doc': 'The project type.'}),

                    ('desc', ('text', {}), {
                        'doc': 'The project description.'}),

                    ('assignee', ('entity:actor', {}), {
                        'doc': 'The actor who is assigned to manage the project.'}),

                    ('platform', ('inet:service:platform', {}), {
                        'doc': 'The platform where the project is hosted.'}),
                ),
                'doc': 'A project in a tasking system.'}),
        ),

        'edges': (

            (('proj:sprint', 'has', 'meta:task'), {
                'doc': 'The task was worked on during the sprint.'}),
        ),
    },
)
