import synapse.lib.module as s_module

class PsModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('edu:course', ('guid', {}), {
                    'doc': 'A course of study taught by an org.',
                }),
                ('edu:class', ('guid', {}), {
                    'doc': 'An instance of an edu:course taught at a given time.',
                }),
                ('ps:education', ('guid', {}), {
                    'doc': 'A period of education for an individual.',
                }),
                ('ps:achievement', ('guid', {}), {
                    'doc': 'An instance of an individual receiving an award.',
                }),
                ('ps:tokn', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'A single name element (potentially given or sur).',
                    'ex': 'robert'
                }),
                ('ps:name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'An arbitrary, lower spaced string with normalized whitespace.',
                    'ex': 'robert grey'
                }),
                ('ps:person', ('guid', {}), {
                    'doc': 'A GUID for a person.',
                }),
                ('ps:persona', ('guid', {}), {
                    'deprecated': True,
                    'doc': 'A GUID for a suspected person.',
                }),
                ('ps:person:has', ('comp', {'fields': (('person', 'ps:person'), ('node', 'ndef'))}), {
                    'deprecated': True,
                    'doc': 'A person owns, controls, or has exclusive use of an object or'
                           ' resource, potentially during a specific period of time.'
                }),
                ('ps:persona:has', ('comp', {'fields': (('persona', 'ps:persona'), ('node', 'ndef'))}), {
                    'deprecated': True,
                    'doc': 'A persona owns, controls, or has exclusive use of an object or'
                           ' resource, potentially during a specific period of time.'
                }),
                ('ps:contact', ('guid', {}), {
                    'doc': 'A GUID for a contact info record.',
                }),
                ('ps:contactlist', ('guid', {}), {
                    'doc': 'A GUID for a list of associated contacts.',
                }),
                ('ps:workhist', ('guid', {}), {
                    'doc': "A GUID representing entry in a contact's work history.",
                }),
            ),
            'forms': (
                ('ps:workhist', {}, (
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact which has the work history.',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The org that this work history orgname refers to.',
                    }),
                    ('orgname', ('ou:name', {}), {
                        'doc': 'The reported name of the org the contact worked for.',
                    }),
                    ('orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The reported fqdn of the org the contact worked for.',
                    }),
                    ('jobtype', ('ou:jobtype', {}), {
                        'doc': 'The type of job.',
                    }),
                    ('employment', ('ou:employment', {}), {
                        'doc': 'The type of employment.',
                    }),
                    ('jobtitle', ('ou:jobtitle', {}), {
                        'doc': 'The job title.',
                    }),
                    ('started', ('time', {}), {
                        'doc': 'The date that the contact began working.',
                    }),
                    ('ended', ('time', {}), {
                        'doc': 'The date that the contact stopped working.',
                    }),
                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the period of work.',
                    }),
                    ('pay', ('econ:price', {}), {
                        'doc': 'The estimated/average yearly pay for the work.',
                    }),
                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency that the yearly pay was delivered in.',
                    }),
                )),
                ('edu:course', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': 'organic chemistry for beginners',
                        'doc': 'The name of the course.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A brief course description.',
                    }),
                    ('code', ('str', {'lower': True, 'strip': True}), {
                        'ex': 'chem101',
                        'doc': 'The course catalog number or designator.',
                    }),
                    ('institution', ('ps:contact', {}), {
                        'doc': 'The org or department which teaches the course.',
                    }),
                    ('prereqs', ('array', {'type': 'edu:course', 'uniq': True, 'sorted': True}), {
                        'doc': 'The pre-requisite courses for taking this course.',
                    }),
                )),
                ('edu:class', {}, (
                    ('course', ('edu:course', {}), {
                        'doc': 'The course being taught in the class.',
                    }),
                    ('instructor', ('ps:contact', {}), {
                        'doc': 'The primary instructor for the class.',
                    }),
                    ('assistants', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of assistant/co-instructor contacts.',
                    }),
                    ('date:first', ('time', {}), {
                        'doc': 'The date of the first day of class.'
                    }),
                    ('date:last', ('time', {}), {
                        'doc': 'The date of the last day of class.'
                    }),
                    ('isvirtual', ('bool', {}), {
                        'doc': 'Set if the class is known to be virtual.',
                    }),
                    ('virtual:url', ('inet:url', {}), {
                        'doc': 'The URL a student would use to attend the virtual class.',
                    }),
                    ('virtual:provider', ('ps:contact', {}), {
                        'doc': 'Contact info for the virtual infrastructure provider.',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The place that the class is held.',
                    }),
                )),
                ('ps:education', {}, (
                    ('student', ('ps:contact', {}), {
                        'doc': 'The contact of the person being educated.',
                    }),
                    ('institution', ('ps:contact', {}), {
                        'doc': 'The contact info for the org providing educational services.',
                    }),
                    ('attended:first', ('time', {}), {
                        'doc': 'The first date the student attended a class.',
                    }),
                    ('attended:last', ('time', {}), {
                        'doc': 'The last date the student attended a class.',
                    }),
                    ('classes', ('array', {'type': 'edu:class', 'uniq': True, 'sorted': True}), {
                        'doc': 'The classes attended by the student',
                    }),
                    ('achievement', ('ps:achievement', {}), {
                        'doc': 'The achievement awarded to the individual.',
                    }),
                )),
                ('ps:achievement', {}, (
                    ('awardee', ('ps:contact', {}), {
                        'doc': 'The recipient of the award.',
                    }),
                    ('award', ('ou:award', {}), {
                        'doc': 'The award bestowed on the awardee.',
                    }),
                    ('awarded', ('time', {}), {
                        'doc': 'The date the award was granted to the awardee.',
                    }),
                    ('expires', ('time', {}), {
                        'doc': 'The date the award or certification expires.',
                    }),
                    ('revoked', ('time', {}), {
                        'doc': 'The date the award was revoked by the org.',
                    }),
                )),
                ('ps:tokn', {}, ()),
                ('ps:name', {}, (
                    ('sur', ('ps:tokn', {}), {
                        'doc': 'The surname part of the name.'
                    }),
                    ('middle', ('ps:tokn', {}), {
                        'doc': 'The middle name part of the name.'
                    }),
                    ('given', ('ps:tokn', {}), {
                        'doc': 'The given name part of the name.'
                    }),
                )),
                ('ps:person', {}, (
                    ('dob', ('time', {}), {
                        'doc': 'The date on which the person was born.',
                    }),
                    ('dod', ('time', {}), {
                        'doc': 'The date on which the person died.',
                    }),
                    ('img', ('file:bytes', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated: use ps:person:photo.'
                    }),
                    ('photo', ('file:bytes', {}), {
                        'doc': 'The primary image of a person.'
                    }),
                    ('nick', ('inet:user', {}), {
                        'doc': 'A username commonly used by the person.',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The localized name for the person.',
                    }),
                    ('name:sur', ('ps:tokn', {}), {
                        'doc': 'The surname of the person.'
                    }),
                    ('name:middle', ('ps:tokn', {}), {
                        'doc': 'The middle name of the person.'
                    }),
                    ('name:given', ('ps:tokn', {}), {
                        'doc': 'The given name of the person.'
                    }),
                    ('names', ('array', {'type': 'ps:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'Variations of the name for the person.'
                    }),
                    ('nicks', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'Usernames used by the  person.'
                    }),
                )),
                ('ps:persona', {}, (
                    ('person', ('ps:person', {}), {
                        'doc': 'The real person behind the persona.',
                    }),
                    ('dob', ('time', {}), {
                        'doc': 'The Date of Birth (DOB) if known.',
                    }),
                    ('img', ('file:bytes', {}), {
                        'doc': 'The primary image of a suspected person.'
                    }),
                    ('nick', ('inet:user', {}), {
                        'doc': 'A username commonly used by the suspected person.',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The localized name for the suspected person.',
                    }),
                    ('name:sur', ('ps:tokn', {}), {
                        'doc': 'The surname of the suspected person.'
                    }),
                    ('name:middle', ('ps:tokn', {}), {
                        'doc': 'The middle name of the suspected person.'
                    }),
                    ('name:given', ('ps:tokn', {}), {
                        'doc': 'The given name of the suspected person.'
                    }),
                    ('names', ('array', {'type': 'ps:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'Variations of the name for a persona.'
                    }),
                    ('nicks', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'Usernames used by the persona.'
                    }),
                )),
                ('ps:person:has', {}, (
                    ('person', ('ps:person', {}), {
                        'ro': True,
                        'doc': 'The person who owns or controls the object or resource.',
                    }),
                    ('node', ('ndef', {}), {
                        'ro': True,
                        'doc': 'The object or resource that is owned or controlled by the person.',
                    }),
                    ('node:form', ('str', {}), {
                        'ro': True,
                        'doc': 'The form of the object or resource that is owned or controlled by the person.',
                    }),
                )),
                ('ps:persona:has', {}, (
                    ('persona', ('ps:persona', {}), {
                        'ro': True,
                        'doc': 'The persona who owns or controls the object or resource.',
                    }),
                    ('node', ('ndef', {}), {
                        'ro': True,
                        'doc': 'The object or resource that is owned or controlled by the persona.',
                    }),
                    ('node:form', ('str', {}), {
                        'ro': True,
                        'doc': 'The form of the object or resource that is owned or controlled by the persona.',
                    }),
                )),
                ('ps:contact', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which this contact represents.',
                    }),
                    ('asof', ('time', {}), {
                        'date': 'The time this contact was created or modified.',
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': 'The ps:person GUID which owns this contact.',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The person name listed for the contact.',
                    }),
                    ('title', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The job/org title listed for this contact.',
                    }),
                    ('photo', ('file:bytes', {}), {
                        'doc': 'The photo listed for this contact.',
                    }),
                    ('orgname', ('ou:name', {}), {
                        'doc': 'The listed org/company name for this contact.',
                    }),
                    ('orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The listed org/company FQDN for this contact.',
                    }),
                    ('user', ('inet:user', {}), {
                        'doc': 'The username or handle for this contact.',
                    }),
                    ('web:acct', ('inet:web:acct', {}), {
                        'doc': 'The social media account for this contact.',
                    }),
                    ('web:group', ('inet:web:group', {}), {
                        'doc': 'A web group representing this contact.',
                    }),
                    ('birth:place', ('geo:place', {}), {
                        'doc': 'A fully resolved place of birth for this contact.',
                    }),
                    ('birth:place:loc', ('loc', {}), {
                        'doc': 'The loc of the place of birth of this contact.',
                    }),
                    ('birth:place:name', ('geo:name', {}), {
                        'doc': 'The name of the place of birth of this contact.',
                    }),
                    ('death:place', ('geo:place', {}), {
                        'doc': 'A fully resolved place of death for this contact.',
                    }),
                    ('death:place:loc', ('loc', {}), {
                        'doc': 'The loc of the place of death of this contact.',
                    }),
                    ('death:place:name', ('geo:name', {}), {
                        'doc': 'The name of the place of death of this contact.',
                    }),
                    ('dob', ('time', {}), {
                        'doc': 'The date of birth for this contact.',
                    }),
                    ('dod', ('time', {}), {
                        'doc': 'The date of death for this contact.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The home or main site for this contact.',
                    }),
                    ('email', ('inet:email', {}), {
                        'doc': 'The main email address for this contact.',
                    }),
                    ('email:work', ('inet:email', {}), {
                        'doc': 'The work email address for this contact.'
                    }),
                    ('loc', ('loc', {}), {
                        'doc': 'Best known contact geopolitical location.'
                    }),
                    ('address', ('geo:address', {}), {
                        'doc': 'The street address listed for the contact.',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The place associated with this contact.',
                    }),
                    ('phone', ('tel:phone', {}), {
                        'doc': 'The main phone number for this contact.',
                    }),
                    ('phone:fax', ('tel:phone', {}), {
                        'doc': 'The fax number for this contact.',
                    }),
                    ('phone:work', ('tel:phone', {}), {
                        'doc': 'The work phone number for this contact.',
                    }),
                    ('id:number', ('ou:id:number', {}), {
                        'doc': 'An ID number issued by an org and associated with this contact.',
                    }),
                    ('adid', ('it:adid', {}), {
                        'doc': 'A Advertising ID associated with this contact.',
                    }),
                    ('imid', ('tel:mob:imid', {}), {
                        'doc': 'An IMID associated with the contact.',
                    }),
                    ('imid:imei', ('tel:mob:imei', {}), {
                        'doc': 'An IMEI associated with the contact.',
                    }),
                    ('imid:imsi', ('tel:mob:imsi', {}), {
                        'doc': 'An IMSI associated with the contact.',
                    }),
                    # A few probable multi-fields for entity resolution
                    ('names', ('array', {'type': 'ps:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'The person name listed for the contact.',
                    }),
                    ('emails', ('array', {'type': 'inet:email', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of secondary/associated email addresses.',
                    }),
                    ('web:accts', ('array', {'type': 'inet:web:acct', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of secondary/associated web accounts.',
                    }),
                    ('id:numbers', ('array', {'type': 'ou:id:number', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of secondary/associated IDs.',
                    }),
                    ('users', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of secondary/associated user names.',
                    }),
                    ('crypto:address', ('crypto:currency:address', {}), {
                        'doc': 'A crypto currency address associated with the contact.'
                    }),
                )),
                ('ps:contactlist', {}, (
                    ('contacts', ('array', {'type': 'ps:contact', 'uniq': True, 'split': ',', 'sorted': True}), {
                        'doc': 'The array of contacts contained in the list.'
                    }),
                    ('source:host', ('it:host', {}), {
                        'doc': 'The host from which the contact list was extracted.',
                    }),
                    ('source:file', ('file:bytes', {}), {
                        'doc': 'The file from which the contact list was extracted.',
                    }),
                    ('source:acct', ('inet:web:acct', {}), {
                        'doc': 'The web account from which the contact list was extracted.',
                    }),
                )),
            )
        }
        name = 'ps'
        return ((name, modl), )
