import synapse.lib.module as s_module

class PsModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
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
                    'doc': 'A GUID for a suspected person.',
                }),
                ('ps:person:has', ('comp', {'fields': (('person', 'ps:person'), ('node', 'ndef'))}), {
                    'doc': 'A person owns, controls, or has exclusive use of an object or'
                           ' resource, potentially during a specific period of time.'
                }),
                ('ps:persona:has', ('comp', {'fields': (('persona', 'ps:persona'), ('node', 'ndef'))}), {
                    'doc': 'A persona owns, controls, or has exclusive use of an object or'
                           ' resource, potentially during a specific period of time.'
                }),
                ('ps:contact', ('guid', {}), {
                    'doc': 'A GUID for a contact info record',
                }),
            ),
            'forms': (
                ('ps:tokn', {}, ()),
                ('ps:name', {}, (
                    ('sur', ('ps:tokn', {}), {
                        'doc': 'The surname part of the name'
                    }),
                    ('middle', ('ps:tokn', {}), {
                        'doc': 'The middle name part of the name'
                    }),
                    ('given', ('ps:tokn', {}), {
                        'doc': 'The given name part of the name'
                    }),
                )),
                ('ps:person', {}, (
                    ('dob', ('time', {}), {
                        'doc': 'The Date of Birth (DOB) if known.',
                    }),
                    ('img', ('file:bytes', {}), {
                        'doc': 'The primary image of a person.'
                    }),
                    ('nick', ('inet:user', {}), {
                        'doc': 'A username commonly used by the person',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The localized name for the person.',
                    }),
                    ('name:sur', ('ps:tokn', {}), {
                        'doc': 'The surname of the person'
                    }),
                    ('name:middle', ('ps:tokn', {}), {
                        'doc': 'The middle name of the person'
                    }),
                    ('name:given', ('ps:tokn', {}), {
                        'doc': 'The given name of the person'
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
                        'doc': 'A username commonly used by the suspected person',
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
                        'doc': 'The ou:org GUID which owns this contact.',
                    }),
                    ('asof', ('time', {}), {
                        'date': 'The time this contact was created or modified.',
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': 'The ps:person GUID which owns this contact.',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The person name listed for the contact',
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
                    ('user', ('inet:user', {}), {
                        'doc': 'The username or handle for this contact.',
                    }),
                    ('web:acct', ('inet:web:acct', {}), {
                        'doc': 'The social media account for this contact.',
                    }),
                    ('dob', ('time', {}), {
                        'doc': 'The Date of Birth (DOB) for this contact.',
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
                    ('phone', ('tel:phone', {}), {
                        'doc': 'The main phone number for this contact',
                    }),
                    ('phone:fax', ('tel:phone', {}), {
                        'doc': 'The fax number for this contact.',
                    }),
                    ('phone:work', ('tel:phone', {}), {
                        'doc': 'The work phone number for this contact.',
                    }),
                )),
            )
        }
        name = 'ps'
        return ((name, modl), )
