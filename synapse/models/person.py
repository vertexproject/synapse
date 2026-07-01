modeldefs = (
    {
        'types': (
            ('edu:course', ('guid', {}), {
                'template': {'title': 'course'},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'ex': 'organic chemistry for beginners',
                        'doc': 'The name of the course.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A brief course description.'}),

                    ('id', ('base:id', {}), {
                        'ex': 'chem101',
                        'prevnames': ('code',),
                        'doc': 'The course catalog number or ID.'}),

                    ('institution', ('ou:org', {}), {
                        'doc': 'The org or department which teaches the course.'}),

                    ('prereqs', ('array', {'type': 'edu:course'}), {
                        'doc': 'The pre-requisite courses for taking this course.'}),

                ),
                'doc': 'A course of study taught by an org.'}),

            ('edu:class', ('guid', {}), {
                'template': {'title': 'class'},
                'interfaces': (
                    ('geo:locatable', {}),
                    ('meta:recordable', {}),
                    ('entity:attendable', {}),
                    ('entity:participable', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the class.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the class.'}),

                    ('type', ('edu:class:type:taxonomy', {}), {
                        'doc': 'The type of class.'}),

                    ('course', ('edu:course', {}), {
                        'doc': 'The course being taught in the class.'}),

                    ('instructor', ('entity:individual', {}), {
                        'doc': 'The primary instructor for the class.'}),

                    ('assistants', ('array', {'type': 'entity:individual'}), {
                        'doc': 'An array of assistant/co-instructor contacts.'}),

                    ('period', ('ival', {'precision': 'day', 'names': {'min': 'began', 'max': 'ended'}}), {
                        'prevnames': ('date:first', 'date:last'),
                        'doc': 'The period over which the class was run.'}),

                    ('remote', ('percent', {}), {
                        'doc': 'The percentage of the class which may be attended remotely.'}),

                    ('remote:url', ('inet:url', {}), {
                        'doc': 'The URL a student would use to attend the class remotely.'}),

                    ('remote:provider', ('entity:actor', {}), {
                        'doc': 'Contact info for the remote infrastructure provider.'}),

                    ('remote:provider:name', ('entity:name', {}), {
                        'doc': 'The name of the remote infrastructure provider.'}),
                ),
                'doc': 'An instance of an edu:course taught at a given time.'}),

            ('edu:class:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of edu:class types.'}),

            ('ps:person', ('guid', {}), {
                'template': {'title': 'person'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:singular', {}),
                    ('risk:targetable', {}),
                    ('entity:contactable', {}),
                ),
                'props': (
                    ('vitals', ('ps:vitals', {}), {
                        'doc': 'The most recent vitals for the person.'}),
                ),
                'doc': 'A person or persona.'}),

            ('ps:workhist', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'contact::name'}},
                        {'type': 'prop', 'opts': {'name': 'title'}},
                        {'type': 'prop', 'opts': {'name': 'org:name'}},
                        # TODO allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period.min'}},
                        # {'type': 'prop', 'opts': {'name': 'period.max'}},
                    ),
                },
                'props': (

                    ('contact', ('entity:individual', {}), {
                        'doc': 'The contact which has the work history.'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The org that this work history orgname refers to.'}),

                    ('org:name', ('entity:name', {}), {
                        'prevnames': ('orgname',),
                        'doc': 'The reported name of the org the contact worked for.'}),

                    ('org:fqdn', ('inet:fqdn', {}), {
                        'prevnames': ('orgfqdn',),
                        'doc': 'The reported fqdn of the org the contact worked for.'}),

                    ('job:type', ('ou:job:type:taxonomy', {}), {
                        'doc': 'The type of job.',
                        'prevnames': ('jobtype',)}),

                    ('employment:type', ('ou:employment:type:taxonomy', {}), {
                        'doc': 'The type of employment.',
                        'prevnames': ('employment',)}),

                    ('title', ('entity:title', {}), {
                        'prevnames': ('jobtitle',),
                        'doc': 'The title held by the contact.'}),

                    ('pay', ('econ:price', {}), {
                        'doc': 'The average yearly income paid to the contact.'}),

                    ('period', ('ival', {}), {
                        'prevnames': ('started', 'ended', 'duration'),
                        'doc': 'The period of time that the contact worked for the organization.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the work done as part of the job.'}),
                ),
                'doc': "An entry in a contact's work history."}),

            ('ps:vitals', ('guid', {}), {
                'template': {'title': 'person'},
                'interfaces': (
                    ('phys:tangible', {}),
                ),
                'props': (

                    ('time', ('time', {}), {
                        'prevnames': ('asof',),
                        'doc': 'The time the vitals were gathered or computed.'}),

                    ('individual', ('entity:individual', {}), {
                        'prevnames': ('contact', 'person'),
                        'doc': 'The individual that the vitals are about.'}),

                    ('econ:net:worth', ('econ:price', {}), {
                        'doc': 'The net worth of the contact.'}),

                    ('econ:annual:income', ('econ:price', {}), {
                        'doc': 'The yearly income of the contact.'}),

                    # TODO: eye color etc. color names / rgb values?
                ),
                'doc': 'Statistics and demographic data about a person.'}),

            ('ps:skill', ('guid', {}), {
                'interfaces': (
                    ('edu:learnable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the skill.'}),

                    ('type', ('ps:skill:type:taxonomy', {}), {
                        'doc': 'The type of skill as a taxonomy.'})
                ),
                'doc': 'A specific skill which a person or organization may have.'}),

            ('ps:skill:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of skill types.'}),

        ),
        'interfaces': (

            ('edu:learnable', {
                'doc': 'An interface implemented by nodes which represent a skill which can be learned.'}),

        ),
    },
)
