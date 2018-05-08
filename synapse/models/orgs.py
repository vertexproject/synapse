from synapse.common import guid

import synapse.lib.module as s_module


class OuModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('ou:sic', ('str', {'regex': r'^[0-9]{4}$'}), {
                    'doc': 'The four digit Standard Industrial Classification Code.',
                    'ex': '0111',
                }),
                ('ou:naics', ('str', {'regex': r'^[1-9][0-9]{4}[0-9]?$'}), {
                    'doc': 'The five or six digit North American Industry Classification System code.',
                    'ex': '541715',
                }),
                ('ou:org', ('guid', {}), {
                    'doc': 'A GUID for a human organization such as a company or military unit',
                    'ex': '',  # FIXME Add example
                }),
                ('ou:alias', ('str', {'lower': True, 'regex': r'^[0-9a-z]+$'}), {
                    'doc': 'An alias for the org GUID',  # FIXME: How is this actually an alias?
                    'ex': 'vertexproject',
                }),
                ('ou:hasalias', ('comp', {'fields': (('org', 'ou:org'), ('alias', 'ou:alias'))}), {
                    'doc': '',
                    'ex': '', # FIXME
                }),
                ('ou:name', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'The formal name of an organization',
                    'ex': 'acme corporation',
                }),
                ('ou:suborg', ('comp', {'fields': (('org', 'ou:org'), ('sub', 'ou:org'))}), {
                    'doc': 'Any parent/child relationship between two orgs. May represent ownership, organizational structure, etc.',
                    'ex': '', # FIXME add example??
                }),
                ('ou:org:has', ('comp', {'fields': (('org', 'ou:org'), ('node', 'ndef'))}), {
                    'doc': 'An org owns, controls, or has exclusive use of an object or resource, '
                           'potentially during a specific period of time.',
                    'ex': '',  # FIXME add example
                }),
                ('ou:user', ('comp', {'fields': (('org', 'ou:org'), ('user', 'inet:user'))}), {
                    'doc': 'A user name within an organization',
                    'ex': '',  # FIXME add example
                }),

                ('ou:meet', ('guid', {}), {
                    'doc': 'A informal meeting of people which has no title or sponsor.  See also: ou:conference.',
                    'ex': '',  # FIXME
                }),
                ('ou:conference', ('guid', {}), {
                    'doc': 'A conference with a name and sponsoring org.',
                    'ex': '',  # FIXME
                })


            ),
            'forms': (
                ('ou:org', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'Location for an organization'
                    }),
                    ('name', ('ou:name', {}), {
                        'doc': '',
                    }),
                    ('name:en', ('ou:name', {}), {
                        'doc': '',
                    }),
                    ('alias', ('ou:alias', {}), {
                        'doc': ''  # FIXME how is this populated???
                    }),
                    ('phone', ('tel:phone', {}), {
                        'doc': 'The primary phone number for the organization.',
                    }),
                    ('sic', ('ou:sic', {}), {
                        'doc': '',
                    }),
                    ('naics', ('ou:naics', {}), {
                        'doc': '',
                    }),
                    ('us:cage', ('gov:us:cage', {}), {
                        'doc': 'A Commercial and Government Entity (CAGE) code',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The primary url for the organization.',
                    }),
                )),
                ('ou:hasalias', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': '',  # FIXME
                    }),
                    ('alias', ('ou:alias', {}), {
                        'ro': True,
                        'doc': '',  # FIXME
                    }),
                    # FIXME Add seen:min and seen:max
                )),
                ('ou:suborg', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org which owns the sub organization',
                    }),
                    ('sub', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The sub org which owned by the org.',
                    }),
                    # TODO: Should min be 0 or 1?
                    ('perc', ('int', {'min': 1, 'max': 100}), {
                        'doc': 'The optional percentage of sub which is owned by org',
                    }),
                    ('current', ('bool', {}), {
                        'doc': 'Bool indicating if the suborg relationship still current.',
                    }),
                    # FIXME Add seen:min and seen:max to indicate beginning
                    # and end dates of the suborg relationship
                )),
                ('ou:org:has', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org who owns or controls the object or resource.',
                    }),
                    ('node', ('ndef', {}), {
                        'ro': True,
                        'doc': 'The object or resource that is owned or controlled by the org.',
                    }),
                    ('node:form', ('str', {}), {
                        'ro': True,
                        'doc': 'The form of the object or resource that is owned or controlled by the org.',
                    }),
                    # FIXME Add seen:min and seen:max
                    # ('seen:min', {'ptype': 'time:min',
                    #               'doc': 'The earliest known time when the org owned or controlled the resource.'}),
                    # ('seen:max', {'ptype': 'time:max',
                    #               'doc': 'The most recent known time when the org owned or controlled the resource.'}),
                )),
                ('ou:user', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': '',  # Fixme
                    }),
                    ('user', ('inet:user', {}), {
                        'ro': True,
                        'doc': '',  # Fixme
                    }),
                )),
                ('ou:meet', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the meeting.',
                    }),
                    ('start', ('time', {}), {
                        'doc': 'The date / time the meet starts.',
                    }),
                    ('end', ('time', {}), {
                        'doc': 'The date / time the meet ends.',
                    }),
                    # FIXME Needs geospatial model
                    # ('place', ('geo:place', ()), {
                    #     'doc': 'The geo:place node where the meet was held.',
                    # }),
                )),
                ('ou:conference', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which created/managed the conference.',
                    }),
                    ('name', ('str', {'lower': True, 'req': True}), {
                        'doc': 'The full name of the conference.',
                        'ex': 'decfon 2017',
                    }),
                    ('base', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The base name which is shared by all conference instances.',
                        'ex': 'defcon',
                    }),
                    ('start', ('time', {}), {
                        'doc': 'The conference start date / time.',
                    }),
                    ('end', ('time', {}), {
                        'doc': 'The conference end date / time.',
                    }),
                    # FIXME Needs geospatial model
                    # ('place', ('geo:place', ()), {
                    #     'doc': 'The geo:place node where the conference was held.',
                    # }),
                    # TODO: prefix optimized geo political location
                )),
            )
        }

        name = 'ou'
        return ((name, modl),)

# FIXME: What do we want to do with seedCtors?
class Fixme:

    def initCoreModule(self):
        self.core.addSeedCtor('ou:org:name', self.seedOrgName)
        self.core.addSeedCtor('ou:org:alias', self.seedOrgAlias)

    def seedOrgName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ou:org:name', valu)
        if node is None:
            node = self.core.formTufoByProp('ou:org', guid(), name=valu, **props)
        return node

    def seedOrgAlias(self, prop, valu, **props):
        node = self.core.getTufoByProp('ou:org:alias', valu)
        if node is None:
            node = self.core.formTufoByProp('ou:org', guid(), alias=valu, **props)
        return node

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (

                ('ou:member', {
                    'subof': 'comp',
                    'fields': 'org,ou:org|person,ps:person',
                    'doc': 'A person who is (or was) a member of an organization.'}),

                ('ou:meet:attendee', {
                    'subof': 'comp',
                    'fields': 'meet=ou:meet,person=ps:person',
                    'doc': 'Represents a person attending a meeting represented by an ou:meet node.'}),

                ('ou:conference:attendee', {
                    'subof': 'comp',
                    'fields': 'conference=ou:conference,person=ps:person',
                    'doc': 'Represents a person attending a conference represented by an ou:conference node.'}),
            ),

            'forms': (

                ('ou:member', {}, [
                    ('org', {'ptype': 'ou:org', 'ro': 1}),
                    ('person', {'ptype': 'ps:person', 'ro': 1}),
                    ('start', {'ptype': 'time:min'}),
                    ('end', {'ptype': 'time:max'}),
                    ('title', {'ptype': 'str:lwr', 'defval': '??'}),
                ]),

                ('ou:owns', {'ptype': 'sepr', 'sep': '/', 'fields': 'owner,ou:org|owned,ou:org'}, [
                ]),  # FIXME does this become an ou:org:has?

                ('ou:meet:attendee', {}, (
                    ('meet', {'ptype': 'ou:meet', 'req': 1, 'ro': 1,
                        'doc': 'The meeting which was attended.'}),
                    ('person', {'ptype': 'ps:person', 'req': 1, 'ro': 1,
                        'doc': 'The person who attended the meet.'}),
                    ('arrived', {'ptype': 'time',
                        'doc': 'An optional property to annotate when the person arrived.'}),
                    ('departed', {'ptype': 'time',
                        'doc': 'An optional property to annotate when the person departed.'}),
                )),

                ('ou:conference:attendee', {}, (
                    ('conference', {'ptype': 'ou:conference', 'req': 1, 'ro': 1,
                        'doc': 'The conference which was attended.'}),
                    ('person', {'ptype': 'ps:person', 'req': 1, 'ro': 1,
                        'doc': 'The person who attended the conference.'}),
                    ('arrived', {'ptype': 'time',
                        'doc': 'An optional property to annotate when the person arrived.'}),
                    ('departed', {'ptype': 'time',
                        'doc': 'An optional property to annotate when the person departed.'}),
                    ('role:staff', {'ptype': 'bool',
                        'doc': 'The person worked as staff at the conference.'}),
                    ('role:speaker', {'ptype': 'bool',
                        'doc': 'The person was a speaker/presenter at the conference.'}),
                )),

            ),
        }
        name = 'ou'
        return ((name, modl), )
