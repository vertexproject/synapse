modeldefs = (
    ('ps', {
        'types': (
            ('edu:course', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'title': 'course'}}),
                ),
                'doc': 'A course of study taught by an org.'}),

            ('edu:class', ('guid', {}), {
                'interfaces': (
                    ('ou:attendable', {'template': {'title': 'class'}}),
                ),
                'doc': 'An instance of an edu:course taught at a given time.'}),

            ('ps:education', ('guid', {}), {
                'doc': 'A period of education for an individual.'}),

            ('ps:achievement', ('guid', {}), {
                'doc': 'An instance of an individual receiving an award.'}),

            ('ps:person', ('guid', {}), {
                'template': {'title': 'person'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:singular', {}),
                ),
                'doc': 'A person or persona.'}),

            ('ps:workhist', ('guid', {}), {
                'doc': "An entry in a contact's work history."}),

            ('ps:vitals', ('guid', {}), {
                'template': {'title': 'person'},
                'interfaces': (
                    ('phys:object', {}),
                ),
                'doc': 'Statistics and demographic data about a person.'}),

            ('edu:learnable', ('ndef', {'interface': 'edu:learnable'}), {
                'doc': 'An interface inherited by nodes which represent something which can be learned.'}),

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
                'doc': 'A specific skill which a person or organization may have.'}),

            ('ps:skill:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of skill types.'}),

            ('ps:proficiency', ('guid', {}), {
                'doc': 'The assessment that a given contact possesses a specific skill.',
                'display': {
                    'columns': (
                        # FIXME interface embed props
                        # {'type': 'prop', 'opts': {'name': 'contact::name'}},
                        # {'type': 'prop', 'opts': {'name': 'skill::name'}},
                    ),
                }}),
        ),
        'interfaces': (

            ('edu:learnable', {
                'doc': 'An interface inherited by nodes which represent a skill which can be learned.'}),

        ),
        'edges': (

            (('ps:education', 'included', 'edu:class'), {
                'doc': 'The class was taken by the student as part of their education process.'}),
        ),
        'forms': (

            ('ps:workhist', {}, (

                ('contact', ('entity:individual', {}), {
                    'doc': 'The contact which has the work history.'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The org that this work history orgname refers to.'}),

                ('org:name', ('meta:name', {}), {
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

                ('pay:currency', ('econ:currency', {}), {
                    'doc': 'The currency of the pay.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('started', 'ended', 'duration'),
                    'doc': 'The period of time that the contact worked for the organization.'}),
            )),
            ('edu:course', {}, (

                ('name', ('meta:name', {}), {
                    'ex': 'organic chemistry for beginners',
                    'doc': 'The name of the course.'}),

                ('desc', ('str', {}), {
                    'doc': 'A brief course description.'}),

                ('id', ('meta:id', {}), {
                    'ex': 'chem101',
                    'prevnames': ('code',),
                    'doc': 'The course catalog number or ID.'}),

                ('institution', ('ou:org', {}), {
                    'doc': 'The org or department which teaches the course.'}),

                ('prereqs', ('array', {'type': 'edu:course'}), {
                    'doc': 'The pre-requisite courses for taking this course.'}),

            )),
            ('edu:class', {}, (

                ('course', ('edu:course', {}), {
                    'doc': 'The course being taught in the class.'}),

                ('instructor', ('entity:individual', {}), {
                    'doc': 'The primary instructor for the class.'}),

                ('assistants', ('array', {'type': 'entity:individual'}), {
                    'doc': 'An array of assistant/co-instructor contacts.'}),

                ('period', ('ival', {'precision': 'day'}), {
                    'prevnames': ('date:first', 'date:last'),
                    'doc': 'The period over which the class was run.'}),

                ('isvirtual', ('bool', {}), {
                    'doc': 'Set if the class is virtual.'}),

                ('virtual:url', ('inet:url', {}), {
                    'doc': 'The URL a student would use to attend the virtual class.'}),

                ('virtual:provider', ('entity:actor', {}), {
                    'doc': 'Contact info for the virtual infrastructure provider.'}),
            )),
            ('ps:education', {}, (

                ('student', ('entity:individual', {}), {
                    'doc': 'The student who attended the educational institution.'}),

                ('institution', ('ou:org', {}), {
                    'doc': 'The organization providing educational services.'}),

                ('period', ('ival', {'precision': 'day'}), {
                    'prevnames': ('attended:first', 'attended:last'),
                    'doc': 'The period of time when the student attended the institution.'}),

                ('achievement', ('ps:achievement', {}), {
                    'doc': 'The degree or certificate awarded to the individual.'}),

            )),
            ('ps:achievement', {}, (

                ('awardee', ('entity:individual', {}), {
                    'doc': 'The recipient of the award.'}),

                ('award', ('ou:award', {}), {
                    'doc': 'The award bestowed on the awardee.'}),

                ('awarded', ('time', {}), {
                    'doc': 'The date the award was granted to the awardee.'}),

                ('expires', ('time', {}), {
                    'doc': 'The date the award or certification expires.'}),

                ('revoked', ('time', {}), {
                    'doc': 'The date the award was revoked by the org.'}),

            )),

            ('ps:person', {}, (
                ('vitals', ('ps:vitals', {}), {
                    'doc': 'The most recent vitals for the person.'}),
            )),
            ('ps:vitals', {}, (

                ('time', ('time', {}), {
                    'prevnames': ('asof',),
                    'doc': 'The time the vitals were gathered or computed.'}),

                ('individual', ('entity:individual', {}), {
                    'prevnames': ('contact', 'person'),
                    'doc': 'The individual that the vitals are about.'}),

                ('econ:currency', ('econ:currency', {}), {
                    'doc': 'The currency that the price values are recorded using.'}),

                ('econ:net:worth', ('econ:price', {}), {
                    'doc': 'The net worth of the contact.'}),

                ('econ:annual:income', ('econ:price', {}), {
                    'doc': 'The yearly income of the contact.'}),

                # TODO: eye color etc. color names / rgb values?
            )),

            ('ps:skill:type:taxonomy', {}, ()),
            ('ps:skill', {}, (
                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The name of the skill.'}),
                ('type', ('ps:skill:type:taxonomy', {}), {
                    'doc': 'The type of skill as a taxonomy.'})
            )),

            ('ps:proficiency', {}, (
                ('skill', ('edu:learnable', {}), {
                    'doc': 'The topic or skill in which the contact is proficient.'}),

                ('contact', ('entity:actor', {}), {
                    'doc': 'The entity which is proficient in the skill.'}),
            )),
        )
    }),
)
