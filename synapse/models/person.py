modeldefs = (
    ('ps', {
        'types': (
            ('edu:course', ('guid', {}), {
                'doc': 'A course of study taught by an org.'}),

            ('edu:class', ('guid', {}), {
                'doc': 'An instance of an edu:course taught at a given time.'}),

            ('ps:education', ('guid', {}), {
                'doc': 'A period of education for an individual.'}),

            ('ps:achievement', ('guid', {}), {
                'doc': 'An instance of an individual receiving an award.'}),

            ('ps:person', ('guid', {}), {
                'interfaces': ('entity:actor',),
                'template': {'contactable': 'person'},
                'aliases': (
                    ('dob', {'target': 'lifespan*min',
                        'doc': 'The date of birth for the entity.'}),

                    ('dod', {'target': 'lifespan*max',
                        'doc': 'The date of birth for the entity.'}),
                ),
                'doc': 'A person.'}),

            ('ps:workhist', ('guid', {}), {
                'doc': "An entry in a contact's work history."}),

            ('ps:vitals', ('guid', {}), {
                'interfaces': ('phys:object',),
                'template': {'phys:object': 'person'},
                'doc': 'Statistics and demographic data about a person or contact.'}),

            ('ps:skill', ('guid', {}), {
                'doc': 'A specific skill which a person or organization may have.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                }}),

            ('ps:skill:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of skill types.'}),

            ('ps:proficiency', ('guid', {}), {
                'doc': 'The assessment that a given contact possesses a specific skill.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'contact::name'}},
                        {'type': 'prop', 'opts': {'name': 'skill::name'}},
                    ),
                }}),
        ),
        'edges': (
            # FIXME
            # (('ps:contact', 'has', None), {
            #     'doc': 'The contact is or was in possession of the target node.'}),
            # (('ps:person', 'has', None), {
            #     'doc': 'The person is or was in possession of the target node.'}),
            # (('ps:contact', 'owns', None), {
            #     'doc': 'The contact owns or owned the target node.'}),
            # (('ps:person', 'owns', None), {
            #     'doc': 'The person owns or owned the target node.'}),
        ),
        'forms': (
            ('ps:workhist', {}, (

                ('contact', ('entity:individual', {}), {
                    'doc': 'The contact which has the work history.'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The org that this work history orgname refers to.'}),

                ('org:name', ('entity:name', {}), {
                    'prevnames': ('orgname',),
                    'doc': 'The reported name of the org the contact worked for.'}),

                ('org:fqdn', ('inet:fqdn', {}), {
                    'prevnames': ('orgname',),
                    'doc': 'The reported fqdn of the org the contact worked for.'}),

                ('job:type', ('ou:job:type:taxonomy', {}), {
                    'doc': 'The type of job.',
                    'prevnames': ('jobtype',)}),

                ('employment:type', ('ou:employment:type:taxonomy', {}), {
                    'doc': 'The type of employment.',
                    'prevnames': ('employment',)}),

                ('jobtitle', ('ou:jobtitle', {}), {
                    'doc': 'The job title.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('started', 'ended', 'duration'),
                    'doc': 'The period of time that the contact worked for the organization.'}),

                ('pay', ('econ:price', {}), {
                    'doc': 'The estimated/average yearly pay for the work.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency that the yearly pay was delivered in.'}),
            )),
            ('edu:course', {}, (

                # FIXME event names?
                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'ex': 'organic chemistry for beginners',
                    'doc': 'The name of the course.'}),

                ('desc', ('str', {}), {
                    'doc': 'A brief course description.'}),

                ('code', ('str', {'lower': True, 'strip': True}), {
                    'ex': 'chem101',
                    'doc': 'The course catalog number or designator.'}),

                # FIXME
                ('institution', ('ou:org', {}), {
                    'doc': 'The org or department which teaches the course.'}),

                ('prereqs', ('array', {'type': 'edu:course', 'uniq': True, 'sorted': True}), {
                    'doc': 'The pre-requisite courses for taking this course.'}),

            )),
            ('edu:class', {}, (

                ('course', ('edu:course', {}), {
                    'doc': 'The course being taught in the class.'}),

                ('instructor', ('entity:individual', {}), {
                    'doc': 'The primary instructor for the class.'}),

                ('assistants', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of assistant/co-instructor contacts.'}),

                ('period', ('ival', {'precision': 8, 'inclusive': True}), {
                    'prevnames': ('date:first', 'date:last'),
                    'doc': 'The preiod over which the class was run.'}),

                ('isvirtual', ('bool', {}), {
                    'doc': 'Set if the class is virtual.'}),

                ('virtual:url', ('inet:url', {}), {
                    'doc': 'The URL a student would use to attend the virtual class.'}),

                ('virtual:provider', ('entity:actor', {}), {
                    'doc': 'Contact info for the virtual infrastructure provider.'}),

                # FIXME event interface?
                # FIXME geo:locatable?
                ('place', ('geo:place', {}), {
                    'doc': 'The place that the class is held.'}),

            )),
            ('ps:education', {}, (

                ('student', ('entity:individual', {}), {
                    'doc': 'The student who attended the educational institution.'}),

                # FIXME entity:multi?
                ('institution', ('ou:org', {}), {
                    'doc': 'The organization providing educational services.'}),

                ('period', ('ival', {'precision': 8, 'inclusive': True}),
                    'prevnames': ('attended:first', 'attended:last'),
                    'doc': 'The period of time when the student attended the institution.'}),

                # FIXME NEWP
                ('classes', ('array', {'type': 'edu:class', 'uniq': True, 'sorted': True}), {
                    'doc': 'The classes attended by the student.'}),

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

            ('ps:person', {}, ()),
            ('ps:vitals', {}, (

                ('asof', ('time', {}), {
                    'doc': 'The time the vitals were gathered or computed.'}),

                ('individual', ('entity:individual', {}), {
                    'prevnames': ('contact', 'person'),
                    'doc': 'The individual that the vitals are about.'}),

                # FIXME physical interface?
                ('height', ('geo:dist', {}), {
                    'doc': 'The height of the person or contact.'}),

                ('weight', ('mass', {}), {
                    'doc': 'The weight of the person or contact.'}),

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

                ('skill', ('ps:skill', {}), {
                    'doc': 'The skill in which the contact is proficient.'}),

                ('contact', ('entity:actor', {}), {
                    'doc': 'The entity which is proficient in the skill.'}),
            )),
        )
    }),
)
