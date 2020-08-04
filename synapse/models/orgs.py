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
                    'doc': 'A GUID for a human organization such as a company or military unit.',
                }),
                ('ou:alias', ('str', {'lower': True, 'regex': r'^[0-9a-z_]+$'}), {
                    'doc': 'An alias for the org GUID.',
                    'ex': 'vertexproject',
                }),
                ('ou:hasalias', ('comp', {'fields': (('org', 'ou:org'), ('alias', 'ou:alias'))}), {
                    'doc': 'The knowledge that an organization has an alias.',
                }),
                ('ou:orgnet4', ('comp', {'fields': (('org', 'ou:org'), ('net', 'inet:net4'))}), {
                    'doc': "An organization's IPv4 netblock.",
                }),
                ('ou:orgnet6', ('comp', {'fields': (('org', 'ou:org'), ('net', 'inet:net6'))}), {
                    'doc': "An organization's IPv6 netblock.",
                }),
                ('ou:name', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'The name of an organization. This may be a formal name or informal name of the '
                           'organization.',
                    'ex': 'acme corporation',
                }),
                ('ou:member', ('comp', {'fields': (('org', 'ou:org'), ('person', 'ps:person'))}), {
                    'doc': 'A person who is (or was) a member of an organization.',
                }),
                ('ou:suborg', ('comp', {'fields': (('org', 'ou:org'), ('sub', 'ou:org'))}), {
                    'doc': 'Any parent/child relationship between two orgs. May represent ownership, organizational structure, etc.',
                }),
                ('ou:org:has', ('comp', {'fields': (('org', 'ou:org'), ('node', 'ndef'))}), {
                    'doc': 'An org owns, controls, or has exclusive use of an object or resource, '
                           'potentially during a specific period of time.',
                }),
                ('ou:user', ('comp', {'fields': (('org', 'ou:org'), ('user', 'inet:user'))}), {
                    'doc': 'A user name within an organization.',
                }),
                ('ou:meet', ('guid', {}), {
                    'doc': 'An informal meeting of people which has no title or sponsor.  See also: ou:conference.',
                }),
                ('ou:meet:attendee', ('comp', {'fields': (('meet', 'ou:meet'), ('person', 'ps:person'))}), {
                    'doc': 'Represents a person attending a meeting represented by an ou:meet node.',
                }),
                ('ou:conference', ('guid', {}), {
                    'doc': 'A conference with a name and sponsoring org.',
                }),
                ('ou:conference:attendee', ('comp', {'fields': (('conference', 'ou:conference'), ('person', 'ps:person'))}), {
                    'doc': 'Represents a person attending a conference represented by an ou:conference node.',
                }),
                ('ou:conference:event', ('guid', {}), {
                    'doc': 'A conference event with a name and associated conference.',
                }),
                ('ou:conference:event:attendee', ('comp', {'fields': (('conference', 'ou:conference:event'), ('person', 'ps:person'))}), {
                    'doc': 'Represents a person attending a conference event represented by an ou:conference:event node.',
                }),
                ('ou:goal', ('guid', {}), {
                    'doc': 'An assessed or stated goal which may be abstract or org specific.',
                }),
                ('ou:hasgoal', ('comp', {'fields': (('org', 'ou:org'), ('goal', 'ou:goal'))}), {
                    'doc': 'An org has an assessed or stated goal.',
                }),
                ('ou:campaign', ('guid', {}), {
                    'doc': 'Represents an orgs activity in pursuit of a goal.',
                }),
            ),
            'forms': (
                ('ou:goal', {}, (
                    ('name', ('str', {}), {
                        'doc': 'A terse name for the goal.',
                    }),
                    ('type', ('str', {}), {
                        'doc': 'A user specified goal type.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the goal.',
                    }),
                    ('prev', ('ou:goal', {}), {
                        'doc': 'The previous/parent goal in a list or hierarchy.',
                    }),
                )),
                ('ou:hasgoal', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which has the goal.',
                    }),
                    ('goal', ('ou:goal', {}), {
                        'doc': 'The goal which the org has.',
                    }),
                    ('stated', ('bool', {}), {
                        'doc': 'Set to true/false if the goal is known to be self stated.',
                    }),
                    ('window', ('ival', {}), {
                        'doc': 'Set if a goal has a limited time window.',
                    }),
                )),
                ('ou:campaign', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org carrying out the campaign.',
                    }),
                    ('goal', ('ou:goal', {}), {
                        'doc': 'The assessed primary goal of the campaign.',
                    }),
                    ('goals', ('array', {'type': 'ou:goal'}), {
                        'doc': 'Additional assessed goals of the campaign.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'A terse name of the campaign.',
                    }),
                    ('type', ('str', {}), {
                        'doc': 'A user specified campaign type.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the campaign.',
                    }),
                )),
                ('ou:org', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'Location for an organization.'
                    }),
                    ('name', ('ou:name', {}), {
                        'doc': 'The localized name of an organization.',
                    }),
                    ('names', ('array', {'type': 'ou:name'}), {
                       'doc': 'A list of alternate names for the organization.',
                    }),
                    ('alias', ('ou:alias', {}), {
                        'doc': 'The default alias for an organization.'
                    }),
                    ('phone', ('tel:phone', {}), {
                        'doc': 'The primary phone number for the organization.',
                    }),
                    ('sic', ('ou:sic', {}), {
                        'doc': 'The Standard Industrial Classification code for the organization.',
                    }),
                    ('naics', ('ou:naics', {}), {
                        'doc': 'The North American Industry Classification System code for the organization.',
                    }),
                    ('us:cage', ('gov:us:cage', {}), {
                        'doc': 'The Commercial and Government Entity (CAGE) code for the organization.',
                    }),
                    ('founded', ('time', {}), {
                        'doc': 'The date on which the org was founded.'}),
                    ('dissolved', ('time', {}), {
                        'doc': 'The date on which the org was dissolved.'}),
                    ('url', ('inet:url', {}), {
                        'doc': 'The primary url for the organization.',
                    }),
                )),
                ('ou:name', {}, ()),
                ('ou:hasalias', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org guid which has the alias.',
                    }),
                    ('alias', ('ou:alias', {}), {
                        'ro': True,
                        'doc': 'Alias for the organization.',
                    }),
                )),
                ('ou:orgnet4', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org guid which owns the netblock.',
                    }),
                    ('net', ('inet:net4', {}), {
                        'ro': True,
                        'doc': 'Netblock owned by the organization.',
                    }),
                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The name that the organization assigns to this netblock.'
                    }),
                )),
                ('ou:orgnet6', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org guid which owns the netblock.',
                    }),
                    ('net', ('inet:net6', {}), {
                        'ro': True,
                        'doc': 'Netblock owned by the organization.',
                    }),
                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The name that the organization assigns to this netblock.'
                    }),
                )),
                ('ou:member', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The GUID of the org the person is a member of.',
                    }),
                    ('person', ('ps:person', {}), {
                        'ro': True,
                        'doc': 'The GUID of the person that is a member of an org.',
                    }),
                    ('title', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The persons normalized title.'
                    }),
                    ('start', ('time', {'ismin': True}), {
                        'doc': 'Earliest known association of the person with the org.',
                    }),
                    ('end', ('time', {'ismax': True}), {
                        'doc': 'Most recent known association of the person with the org.',
                    })
                )),
                ('ou:suborg', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org which owns the sub organization.',
                    }),
                    ('sub', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The sub org which owned by the org.',
                    }),
                    ('perc', ('int', {'min': 0, 'max': 100}), {
                        'doc': 'The optional percentage of sub which is owned by org.',
                    }),
                    ('current', ('bool', {}), {
                        'doc': 'Bool indicating if the suborg relationship still current.',
                    }),
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
                )),
                ('ou:user', {}, (
                    ('org', ('ou:org', {}), {
                        'ro': True,
                        'doc': 'The org guid which owns the netblock.',
                    }),
                    ('user', ('inet:user', {}), {
                        'ro': True,
                        'doc': 'The username associated with the organization.',
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
                    ('place', ('geo:place', ()), {
                        'doc': 'The geo:place node where the meet was held.',
                    }),
                )),
                ('ou:meet:attendee', {}, (
                    ('meet', ('ou:meet', {}), {
                        'ro': True,
                        'doc': 'The meeting which was attended.',
                    }),
                    ('person', ('ps:person', {}), {
                        'ro': True,
                        'doc': 'The person who attended the meeting.',
                    }),
                    ('arrived', ('time', {}), {
                        'doc': 'The time when a person arrived to the meeting.',
                    }),
                    ('departed', ('time', {}), {
                        'doc': 'The time when a person departed from the meeting.',
                    }),
                )),
                ('ou:conference', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which created/managed the conference.',
                    }),
                    ('name', ('str', {'lower': True}), {
                        'doc': 'The full name of the conference.',
                        'ex': 'decfon 2017',
                    }),
                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A description of the conference.',
                        'ex': 'annual cybersecurity conference',
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
                    ('place', ('geo:place', ()), {
                        'doc': 'The geo:place node where the conference was held.',
                    }),
                    ('url', ('inet:url', ()), {
                        'doc': 'The inet:url node for the conference website.',
                    }),
                )),
                ('ou:conference:attendee', {}, (
                    ('conference', ('ou:conference', {}), {
                        'ro': True,
                        'doc': 'The conference which was attended.',
                    }),
                    ('person', ('ps:person', {}), {
                        'ro': True,
                        'doc': 'The person who attended the conference.',
                    }),
                    ('arrived', ('time', {}), {
                        'doc': 'The time when a person arrived to the conference.',
                    }),
                    ('departed', ('time', {}), {
                        'doc': 'The time when a person departed from the conference.',
                    }),
                    ('role:staff', ('bool', {}), {
                        'doc': 'The person worked as staff at the conference.',
                    }),
                    ('role:speaker', ('bool', {}), {
                        'doc': 'The person was a speaker or presenter at the conference.',
                    }),
                    ('roles', ('array', {'type': 'str', 'lower': True}), {
                        'doc': 'List of the roles the person had at the conference.',
                    }),
                 )),
                ('ou:conference:event', {}, (
                    ('conference', ('ou:conference', {}), {
                        'ro': True,
                        'doc': 'The conference to which the event is associated.',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The geo:place where the event occurred.',
                    }),
                    ('name', ('str', {'lower': True}), {
                        'doc': 'The name of the conference event.',
                        'ex': 'foobar conference dinner',
                    }),
                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A description of the conference event.',
                        'ex': 'foobar conference networking dinner at ridge hotel',
                    }),
                    ('url', ('inet:url', ()), {
                        'doc': 'The inet:url node for the conference event website.',
                    }),
                    ('contact', ('ps:contact', ()), {
                        'doc': 'Contact info for the event.',
                    }),
                    ('start', ('time', {}), {
                        'doc': 'The event start date / time.',
                    }),
                    ('end', ('time', {}), {
                        'doc': 'The event end date / time.',
                    }),
                )),
                ('ou:conference:event:attendee', {}, (

                    ('event', ('ou:conference:event', {}), {
                        'ro': True,
                        'doc': 'The conference event which was attended.',
                    }),
                    ('person', ('ps:person', {}), {
                        'ro': True,
                        'doc': 'The person who attended the conference event.',
                    }),
                    ('arrived', ('time', {}), {
                        'doc': 'The time when a person arrived to the conference event.',
                    }),
                    ('departed', ('time', {}), {
                        'doc': 'The time when a person departed from the conference event.',
                    }),
                    ('roles', ('array', {'type': 'str', 'lower': True}), {
                        'doc': 'List of the roles the person had at the conference event.',
                    }),
                )),
            )
        }

        name = 'ou'
        return ((name, modl),)
