import synapse.lib.module as s_module

contracttypes = (
    'nda',
    'other',
    'grant',
    'treaty',
    'purchase',
    'indemnity',
    'partnership',
)

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
                ('ou:isic', ('str', {'regex': r'^[A-Z]([0-9]{2}[0-9]{0,2})?$'}), {
                    'doc': 'An International Standard Industrial Classification of All Economic Activities (ISIC) code.',
                    'ex': 'C1393',
                }),
                ('ou:org', ('guid', {}), {
                    'doc': 'A GUID for a human organization such as a company or military unit.',
                }),
                ('ou:contract', ('guid', {}), {
                    'doc': 'An contract between multiple entities.',
                }),
                ('ou:contract:type', ('str', {'enum': contracttypes}), {
                    'doc': 'A pre-defined set of contract types.',
                }),
                ('ou:industry', ('guid', {}), {
                    'doc': 'An industry classification type.',
                }),
                ('ou:alias', ('str', {'lower': True, 'regex': r'^[0-9a-z_]+$'}), {
                    'doc': 'An alias for the org GUID.',
                    'ex': 'vertexproject',
                }),
                ('ou:hasalias', ('comp', {'fields': (('org', 'ou:org'), ('alias', 'ou:alias'))}), {
                    'deprecated': True,
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
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:position.',
                }),
                ('ou:position', ('guid', {}), {
                    'doc': 'A position within an org.  May be organized into an org chart.',
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
                ('ou:role', ('str', {'lower': True, 'regex': r'^\w+$'}), {
                    'ex': 'staff',
                    'doc': 'A named role when participating in an event.',
                }),
                ('ou:attendee', ('guid', {}), {
                    'doc': 'A node representing a person attending a meeting, conference, or event.',
                }),
                ('ou:meet', ('guid', {}), {
                    'doc': 'An informal meeting of people which has no title or sponsor.  See also: ou:conference.',
                }),
                ('ou:meet:attendee', ('comp', {'fields': (('meet', 'ou:meet'), ('person', 'ps:person'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:attendee.',
                }),
                ('ou:conference', ('guid', {}), {
                    'doc': 'A conference with a name and sponsoring org.',
                }),
                ('ou:conference:attendee', ('comp', {'fields': (('conference', 'ou:conference'), ('person', 'ps:person'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:attendee.',
                }),
                ('ou:conference:event', ('guid', {}), {
                    'doc': 'A conference event with a name and associated conference.',
                }),
                ('ou:conference:event:attendee', ('comp', {'fields': (('conference', 'ou:conference:event'), ('person', 'ps:person'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:attendee.',
                }),
                ('ou:contest', ('guid', {}), {
                    'doc': 'A competitive event resulting in a ranked set of participants.',
                }),
                ('ou:contest:result', ('comp', {'fields': (('contest', 'ou:contest'), ('participant', 'ps:contact'))}), {
                    'doc': 'The results from a single contest participant.',
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
                ('ou:id:type', ('guid', {}), {
                    'doc': 'A type of id number issued by an org.',
                }),
                ('ou:id:value', ('str', {'strip': True}), {
                    'doc': 'The value of an org:id:number.',
                }),
                ('ou:id:number', ('comp', {'fields': (('type', 'ou:id:type'), ('value', 'ou:id:value'))}), {
                    'doc': 'A unique id number issued by a specific organization.',
                }),
                ('ou:id:update', ('guid', {}), {
                    'doc': 'A status update to an org:id:number.',
                }),
                ('ou:award', ('guid', {}), {
                    'doc': 'An award issued by an organization.',
                }),
            ),
            'forms': (
                ('ou:award', {}, (
                    ('name', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'doc': 'The name of the award.',
                        'ex': 'Bachelors of Science',
                    }),
                    ('type', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'doc': 'The type of award.',
                        'ex': 'certification',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The organization which issues the award.',
                    }),
                )),
                ('ou:id:type', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which issues id numbers of this type.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'The friendly name of the id number type.',
                    }),
                )),
                ('ou:id:number', {}, (
                    ('type', ('ou:id:type', {}), {
                        'doc': 'The type of org id',
                    }),
                    ('value', ('ou:id:value', {}), {
                        'doc': 'The type of org id',
                    }),
                    ('status', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A freeform status such as valid, suspended, expired.',
                    }),
                    ('issued', ('time', {}), {
                        'doc': 'The time at which the org issued the ID number.',
                    }),
                    ('expires', ('time', {}), {
                        'doc': 'The time at which the ID number expires.',
                    }),
                )),
                ('ou:id:update', {}, (
                    ('number', ('ou:id:number', {}), {
                        'doc': 'The id number that was updated.',
                    }),
                    ('status', ('str', {'strip': True, 'lower': True}), {
                        'doc': 'The updated status of the id number.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The date/time that the id number was updated.',
                    }),
                )),
                ('ou:goal', {}, (
                    ('name', ('str', {}), {
                        'doc': 'A terse name for the goal.',
                    }),
                    ('type', ('str', {}), {
                        'doc': 'A user specified goal type.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the goal.',
                        'disp': {'hint': 'text'},
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
                    ('actors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Actors who participated in the campaign.',
                    }),
                    ('goals', ('array', {'type': 'ou:goal', 'split': ',', 'uniq': True, 'sorted': True}), {
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
                        'disp': {'hint': 'text'},
                    }),
                )),
                ('ou:org', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'Location for an organization.'
                    }),
                    ('name', ('ou:name', {}), {
                        'doc': 'The localized name of an organization.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the org.',
                    }),
                    ('logo', ('file:bytes', {}), {
                        'doc': 'An image file representing the logo for the organization.',
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
                        'deprecated': True,
                        'doc': 'The Standard Industrial Classification code for the organization.',
                    }),
                    ('naics', ('ou:naics', {}), {
                        'deprecated': True,
                        'doc': 'The North American Industry Classification System code for the organization.',
                    }),
                    ('industries', ('array', {'type': 'ou:industry'}), {
                        'doc': 'The industries associated with the org.',
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
                    ('subs', ('array', {'type': 'ou:org'}), {
                        'doc': 'An array of sub-organizations.'
                    }),
                    ('orgchart', ('ou:position', {}), {
                        'doc': 'The root node for an orgchart made up ou:position nodes.',
                    }),
                    ('hq', ('ps:contact', {}), {
                        'doc': 'A collection of contact information for the "main office" of an org.',
                    }),
                    ('locations', ('array', {'type': 'ps:contact'}), {
                        'doc': 'An array of contacts for facilities operated by the org.',
                    }),
                    ('dns:mx', ('array', {'type': 'inet:fqdn'}), {
                        'doc': 'An array of MX domains used by email addresses issued by the org.',
                    }),
                )),
                ('ou:position', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which has the position.',
                    }),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact info for the person who holds the position.',
                    }),
                    ('title', ('str', {'lower': True, 'onespace': True, 'strip': True}), {
                        'doc': 'The title of the position.',
                    }),
                    ('reports', ('array', {'type': 'ou:position'}), {
                        'doc': 'An array of positions which report to this position.',
                    }),
                )),
                ('ou:name', {}, ()),
                ('ou:contract', {}, (
                    ('title', ('str', {}), {
                        'doc': 'A terse title for the contract.'}),
                    ('types', ('array', {'type': 'ou:contract:type', 'uniq': True, 'split': ','}), {
                        'doc': 'A list of types that apply to the contract.'}),
                    ('sponsor', ('ps:contact', {}), {
                        'doc': 'The contract sponsor.'}),
                    ('parties', ('array', {'type': 'ps:contact', 'uniq': True}), {
                        'doc': 'The non-sponsor entities bound by the contract.'}),
                    ('document', ('file:bytes', {}), {
                        'doc': 'The best/current contract document.'}),
                    ('signed', ('time', {}), {
                        'doc': 'The date that the contract signing was complete.'}),
                    ('begins', ('time', {}), {
                        'doc': 'The date that the contract goes into effect.'}),
                    ('expires', ('time', {}), {
                        'doc': 'The date that the contract expires.'}),
                    ('completed', ('time', {}), {
                        'doc': 'The date that the contract was completed.'}),
                    ('terminated', ('time', {}), {
                        'doc': 'The date that the contract was terminated.'}),
                    ('award:price', ('econ:currency', {}), {
                        'doc': 'The value of the contract at time of award.'}),
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'Purchase details of the contract.'}),
                    ('requirements', ('array', {'type': 'ou:goal', 'uniq': True}), {
                        'doc': 'The requirements levied upon the parties.'}),
                )),
                ('ou:industry', {}, (
                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A terse name for the industry.'}),
                    ('subs', ('array', {'type': 'ou:industry', 'uniq': True, 'split': ','}), {
                        'doc': 'An array of sub-industries.'}),
                    ('sic', ('array', {'type': 'ou:sic', 'uniq': True, 'split': ','}), {
                        'doc': 'An array of SIC codes that map to the industry.'}),
                    ('naics', ('array', {'type': 'ou:naics', 'uniq': True, 'split': ','}), {
                        'doc': 'An array of NAICS codes that map to the industry.'}),
                    ('isic', ('array', {'type': 'ou:isic', 'uniq': True, 'split': ','}), {
                        'doc': 'An array of ISIC codes that map to the industry.'}),
                )),
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
                    ('founded', ('time', {}), {
                        'doc': 'The date on which the suborg relationship was founded.',
                    }),
                    ('dissolved', ('time', {}), {
                        'doc': 'The date on which the suborg relationship was dissolved.',
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
                ('ou:attendee', {}, (
                    ('person', ('ps:contact', {}), {
                        'doc': 'The contact information for the person who attended the event.',
                    }),
                    ('arrived', ('time', {}), {
                        'doc': 'The time when a person arrived.',
                    }),
                    ('departed', ('time', {}), {
                        'doc': 'The time when a person departed.',
                    }),
                    ('roles', ('array', {'type': 'ou:role', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'List of the roles the person had at the event.',
                    }),
                    ('meet', ('ou:meet', {}), {
                        'doc': 'The meeting that the person attended.',
                    }),
                    ('conference', ('ou:conference', {}), {
                        'doc': 'The conference that the person attended.',
                    }),
                    ('conference:event', ('ou:conference:event', {}), {
                        'doc': 'The conference event that the person attended.',
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
                        'disp': {'hint': 'text'},
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
                        'disp': {'hint': 'text'},
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
                ('ou:contest', {}, (
                    ('name', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'doc': 'The name of the contest.',
                        'ex': 'defcon ctf 2020',
                    }),
                    ('type', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'doc': 'The type of contest.',
                        'ex': 'cyber ctf',
                    }),
                    ('family', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                        'doc': 'A name for a series of recurring contests.',
                        'ex': 'defcon ctf',
                    }),
                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A description of the contest.',
                        'ex': 'the capture-the-flag event hosted at defcon 2020',
                        'disp': {'hint': 'text'},
                    }),
                    ('start', ('time', {}), {
                        'doc': 'The contest start date / time.',
                    }),
                    ('end', ('time', {}), {
                        'doc': 'The contest end date / time.',
                    }),
                    ('loc', ('loc', {}), {
                        'doc': 'The geopolitical affiliation of the contest.',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The geo:place where the contest was held.',
                    }),
                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The latlong where the contest was held.',
                    }),
                    ('conference', ('ou:conference', {}), {
                        'doc': 'The conference that the contest is associated with.',
                    }),
                    ('contests', ('array', {'type': 'ou:contest', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of sub-contests that contributed to the rankings.',
                    }),
                    ('sponsors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Contact information for contest sponsors.',
                    }),
                    ('organizers', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Contact information for contest organizers.',
                    }),
                    ('participants', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Contact information for contest participants.',
                    }),
                )),
                ('ou:contest:result', {}, (
                    ('contest', ('ou:contest', {}), {
                        'ro': True,
                        'doc': 'The contest.',
                    }),
                    ('participant', ('ps:contact', {}), {
                        'ro': True,
                        'doc': 'The participant',
                    }),
                    ('rank', ('int', {}), {
                        'doc': 'The rank order of the participant.',
                    }),
                    ('score', ('int', {}), {
                        'doc': 'The score of the participant.',
                    }),
                    #TODO duration ('duration'
                )),
            )
        }

        name = 'ou'
        return ((name, modl),)
