import synapse.lib.types as s_types
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
                # FIXME - 00x ps model supported guid alias 'ps:person:guidname'
                ('ps:person', ('guid', {}), {
                    'doc': 'A GUID for a person.',
                }),
                # FIXME - 00x ps model supported guid alias 'ps:persona:guidname'
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
                # FIXME requires file:bytes
                # ('ps:image', ('comp', {'fields': (('person', 'ps:person'), ('image', 'file:bytes'))}), {
                #     'doc': 'An image of a given person',
                # }),
                ('ps:contact', ('guid', {}), {
                    'doc': 'A GUID for a contact info record',
                }),

                # FIXME add wireless elemements like NMEI and IMEI once modeled - pre 010 item

            ),
            'forms': (
                ('ps:tokn', {}, ()),
                ('ps:name', {}, ()),
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
                    ('name:en', ('ps:name', {}), {
                        'doc': 'The English version of the name for the person.',
                    }),
                    ('name:en:sur', ('ps:tokn', {}), {
                        'doc': 'The English version of the surname of the person'
                    }),
                    ('name:en:middle', ('ps:tokn', {}), {
                        'doc': 'The English version of the middle name of the person'
                    }),
                    ('name:en:given', ('ps:tokn', {}), {
                        'doc': 'The English version of the given name of the person'
                    }),
                )),
                ('ps:persona', {}, (
                    # FIXME aliases?
                    # ('guidname', ('str', {'lower': True}), {
                    #     'doc': 'The GUID resolver alias for the suspected person.',
                    # }),
                    ('dob', ('time', {}), {
                        'doc': 'The Date of Birth (DOB) if known.',
                    }),
                    # FIXME need file:bytes
                    # ('img', ('file:bytes', {}), {
                    #     'doc': 'The primary image of a suspected person.'
                    # }),
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
                    ('name:en', ('ps:name', {}), {
                        'doc': 'The English version of the name for the person.',
                    }),
                    ('name:en:sur', ('ps:tokn', {}), {
                        'doc': 'The English version of the surname of the suspected person.'
                    }),
                    ('name:en:middle', ('ps:tokn', {}), {
                        'doc': 'The English version of the middle name of the suspected person.'
                    }),
                    ('name:en:given', ('ps:tokn', {}), {
                        'doc': 'The English version of the given name of the suspected person.'
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
                    # FIXME Add seen:min and seen:max
                    # ('seen:min', {'ptype': 'time:min',
                    #               'doc': 'The earliest known time when the person owned or controlled the resource.'}),
                    # ('seen:max', {'ptype': 'time:max',
                    #               'doc': 'The most recent known time when the person owned or controlled the resource.'}),
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
                    # FIXME Add seen:min and seen:max
                    # ('seen:min', {'ptype': 'time:min',
                    #               'doc': 'The earliest known time when the person owned or controlled the resource.'}),
                    # ('seen:max', {'ptype': 'time:max',
                    #               'doc': 'The most recent known time when the person owned or controlled the resource.'}),
                )),
                # FIXME requires file:bytes
                # ('ps:image', {}, (
                #     ('person', ('ps:person', {}), {
                #         'doc': '',
                #     }),
                #     ('image', ('file:bytes', {}), {
                #         'doc': '',
                #     }),
                # # FIXME add an optional bounding box
                # )),
                ('ps:contact', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The ou:org GUID which owns this contact.',
                    }),
                    ('asof', ('time', {}), {
                        'date': 'The time this contact was created or modified.',
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': ' The ps:person GUID which owns this contact.',
                    }),
                    ('name', ('ps:name', {}), {
                        'doc': 'The person name listed for the contact',
                    }),
                    ('title', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The job/org title listed for this contact.',
                    }),
                    # FIXME requires file:bytes
                    # ('photo', ('file:bytes', {}), {
                    #     'doc': 'The photo listed for this contact.',
                    # }),
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
                    # FIXME - Should we have a `address:loc` or `loc` property as well?
                    ('address', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The free-form address listed for the contact',
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

# FIXME - what do we want to do with seed ctors?
class Fixme:
    def initCoreModule(self):
        self.core.addSeedCtor('ps:person:guidname', self.seedPersonGuidName)
        self.core.addSeedCtor('ps:persona:guidname', self.seedPersonaGuidName)

    def seedPersonGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:person:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:person', None, guidname=valu, **props)
        return node

    def seedPersonaGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:persona:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:persona', None, guidname=valu, **props)
        return node

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (




            ),

            'forms': (



            ),
        }
        name = 'ps'
        return ((name, modl), )
