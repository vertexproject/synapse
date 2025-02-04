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
                ('ou:naics', ('str', {'regex': r'^[1-9][0-9]{1,5}?$', 'strip': True}), {
                    'doc': 'North American Industry Classification System codes and prefixes.',
                    'ex': '541715',
                }),
                ('ou:isic', ('str', {'regex': r'^[A-Z]([0-9]{2}[0-9]{0,2})?$'}), {
                    'doc': 'An International Standard Industrial Classification of All Economic Activities (ISIC) code.',
                    'ex': 'C1393'}),

                ('ou:org', ('guid', {}), {
                    'doc': 'A GUID for a human organization such as a company or military unit.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'names'}},
                            {'type': 'prop', 'opts': {'name': 'country:code'}},
                        ),
                    }}),

                ('ou:team', ('guid', {}), {
                    'doc': 'A GUID for a team within an organization.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'org::name'}},
                        ),
                    }}),

                ('ou:asset:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'An asset type taxonomy.'}),

                ('ou:asset:status:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'An asset status taxonomy.'}),

                ('ou:asset', ('guid', {}), {
                    'doc': 'A node for tracking assets which belong to an organization.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'id'}},
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'org::name'}},
                        ),
                    }}),

                ('ou:orgtype', ('taxonomy', {}), {
                    'doc': 'An org type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('ou:contract', ('guid', {}), {
                    'doc': 'An contract between multiple entities.',
                }),
                ('ou:conttype', ('taxonomy', {}), {
                    'doc': 'A contract type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('ou:contract:type', ('str', {'enum': contracttypes}), {
                    'deprecated': True,
                    'doc': 'A pre-defined set of contract types.',
                }),
                ('ou:industry', ('guid', {}), {
                    'doc': 'An industry classification type.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                        ),
                    },
                }),
                ('ou:industry:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'An industry type taxonomy.',
                }),
                ('ou:industryname', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The name of an industry.',
                }),
                ('ou:alias', ('str', {'lower': True, 'regex': r'^[\w0-9_]+$'}), {
                    'deprecated': True,
                    'ex': 'vertexproject',
                    'doc': 'Deprecated. Please use ou:name.',
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
                    'deprecated': True,
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
                ('ou:preso', ('guid', {}), {
                    'doc': 'A webinar, conference talk, or other type of presentation.',
                }),
                ('ou:meet:attendee', ('comp', {'fields': (('meet', 'ou:meet'), ('person', 'ps:person'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:attendee.',
                }),
                ('ou:conference', ('guid', {}), {
                    'doc': 'A conference with a name and sponsoring org.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'start'}},
                        ),
                    },
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
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                        ),
                    },
                }),
                ('ou:goalname', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A goal name.',
                }),
                ('ou:goal:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of goal types.',
                }),
                ('ou:hasgoal', ('comp', {'fields': (('org', 'ou:org'), ('goal', 'ou:goal'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use ou:org:goals.',
                }),
                ('ou:camptype', ('taxonomy', {}), {
                    'doc': 'An campaign type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('ou:campname', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A campaign name.'}),

                ('ou:campaign', ('guid', {}), {
                    'doc': "Represents an org's activity in pursuit of a goal.",
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'names'}},
                            {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                            {'type': 'prop', 'opts': {'name': 'tag'}},
                        ),
                    }}),

                ('ou:conflict', ('guid', {}), {
                    'doc': 'Represents a conflict where two or more campaigns have mutually exclusive goals.',
                }),
                ('ou:contribution', ('guid', {}), {
                    'doc': 'Represents a specific instance of contributing material support to a campaign.'}),

                ('ou:technique', ('guid', {}), {
                    'doc': 'A specific technique used to achieve a goal.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'name'}},
                            {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                            {'type': 'prop', 'opts': {'name': 'tag'}},
                        ),
                    }}),

                ('ou:technique:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'An analyst defined taxonomy to classify techniques in different disciplines.',
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
                ('ou:vitals', ('guid', {}), {
                    'doc': 'Vital statistics about an org for a given time period.',
                }),
                ('ou:opening', ('guid', {}), {
                    'doc': 'A job/work opening within an org.'}),

                ('ou:candidate:method:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of methods by which a candidate came under consideration.'}),

                ('ou:candidate', ('guid', {}), {
                    'doc': 'A candidate being considered for a role within an organization.',
                    'display': {
                        'columns': (
                            {'type': 'prop', 'opts': {'name': 'contact::name'}},
                            {'type': 'prop', 'opts': {'name': 'contact::email'}},
                            {'type': 'prop', 'opts': {'name': 'submitted'}},
                            {'type': 'prop', 'opts': {'name': 'org::name'}},
                            {'type': 'prop', 'opts': {'name': 'opening::jobtitle'}},
                        ),
                    }}),

                ('ou:jobtype', ('taxonomy', {}), {
                    'ex': 'it.dev.python',
                    'doc': 'A taxonomy of job types.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('ou:employment', ('taxonomy', {}), {
                    'ex': 'fulltime.salary',
                    'doc': 'An employment type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('ou:jobtitle', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A title for a position within an org.'}),

                ('ou:enacted:status:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of enacted statuses.'}),

                ('ou:enacted', ('guid', {}), {
                    'interfaces': ('proj:task',),
                    'template': {
                        'task': 'adoption task'},
                    'doc': 'An organization enacting a document.'}),

                ('ou:requirement:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of requirement types.'}),

                ('ou:requirement', ('guid', {}), {
                    'doc': 'A specific requirement.'}),

            ),
            'edges': (
                (('ou:campaign', 'uses', 'ou:technique'), {
                    'doc': 'The campaign used the technique.'}),
                (('ou:org', 'uses', 'ou:technique'), {
                    'doc': 'The org uses the technique.'}),
                (('risk:vuln', 'uses', 'ou:technique'), {
                    'doc': 'The vulnerability uses the technique.'}),

                (('ou:org', 'uses', None), {
                    'doc': 'The ou:org makes use of the target node.'}),
                (('ou:org', 'targets', None), {
                    'doc': 'The organization targets the target node.'}),
                (('ou:campaign', 'targets', None), {
                    'doc': 'The campaign targeted the target nodes.'}),
                (('ou:campaign', 'uses', None), {
                    'doc': 'The campaign made use of the target node.'}),
                (('ou:contribution', 'includes', None), {
                    'doc': 'The contribution includes the specific node.'}),
                ((None, 'meets', 'ou:requirement'), {
                    'doc': 'The requirement is met by the source node.'}),
                (('ou:org', 'has', None), {
                    'doc': 'The organization is or was in possession of the target node.'}),
                (('ou:org', 'owns', None), {
                    'doc': 'The organization owns or owned the target node.'}),
            ),
            'forms': (
                ('ou:jobtype', {}, ()),
                ('ou:jobtitle', {}, ()),
                ('ou:employment', {}, ()),
                ('ou:opening', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which has the opening.',
                    }),
                    ('orgname', ('ou:name', {}), {
                        'doc': 'The name of the organization as listed in the opening.',
                    }),
                    ('orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The FQDN of the organization as listed in the opening.',
                    }),
                    ('posted', ('time', {}), {
                        'doc': 'The date/time that the job opening was posted.',
                    }),
                    ('removed', ('time', {}), {
                        'doc': 'The date/time that the job opening was removed.',
                    }),
                    ('postings', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                        'doc': 'URLs where the opening is listed.',
                    }),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact details to inquire about the opening.',
                    }),
                    ('loc', ('loc', {}), {
                        'doc': 'The geopolitical boundary of the opening.',
                    }),
                    ('jobtype', ('ou:jobtype', {}), {
                        'doc': 'The job type taxonomy.',
                    }),
                    ('employment', ('ou:employment', {}), {
                        'doc': 'The type of employment.',
                    }),
                    ('jobtitle', ('ou:jobtitle', {}), {
                        'doc': 'The title of the opening.',
                    }),
                    ('remote', ('bool', {}), {
                        'doc': 'Set to true if the opening will allow a fully remote worker.',
                    }),
                    ('yearlypay', ('econ:price', {}), {
                        'doc': 'The yearly income associated with the opening.',
                    }),
                    ('paycurrency', ('econ:currency', {}), {
                        'doc': 'The currency that the yearly pay was delivered in.',
                    }),
                    # TODO a way to encode/normalize requirements.
                )),
                ('ou:candidate:method:taxonomy', {}, ()),
                ('ou:candidate', {}, (

                    ('org', ('ou:org', {}), {
                        'doc': 'The organization considering the candidate.'}),

                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact information of the candidate.'}),

                    ('method', ('ou:candidate:method:taxonomy', {}), {
                        'doc': 'The method by which the candidate came under consideration.'}),

                    ('submitted', ('time', {}), {
                        'doc': 'The time the candidate was submitted for consideration.'}),

                    ('intro', ('str', {'strip': True}), {
                        'doc': 'An introduction or cover letter text submitted by the candidate.'}),

                    ('resume', ('file:bytes', {}), {
                        'doc': "The candidate's resume or CV."}),

                    ('opening', ('ou:opening', {}), {
                        'doc': 'The opening that the candidate is being considered for.'}),

                    ('agent', ('ps:contact', {}), {
                        'doc': 'The contact information of an agent who advocates for the candidate.'}),

                    ('recruiter', ('ps:contact', {}), {
                        'doc': 'The contact information of a recruiter who works on behalf of the organization.'}),

                    ('attachments', ('array', {'type': 'file:attachment', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of additional files submitted by the candidate.'}),

                    # TODO: doc:questionare / responses
                    # TODO: :skills=[<ps:skill>]? vs :contact -> ps:proficiency?
                    # TODO: proj:task to track evaluation of the candidate?

                )),
                ('ou:vitals', {}, (

                    ('asof', ('time', {}), {
                        'doc': 'The time that the vitals represent.',
                    }),
                    # TODO is modulo time a type?
                    # ('period', ('sec', 'min', 'hour', 'day', 'week', 'month', 'quarter', 'year'
                    ('org', ('ou:org', {}), {
                        'doc': 'The resolved org.',
                    }),
                    ('orgname', ('ou:name', {}), {
                        'doc': 'The org name as reported by the source of the vitals.',
                    }),
                    ('orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The org FQDN as reported by the source of the vitals.',
                    }),
                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the econ:price values.',
                    }),
                    ('costs', ('econ:price', {}), {
                        'doc': 'The costs/expenditures over the period.'}),

                    ('budget', ('econ:price', {}), {
                        'doc': 'The budget allocated for the period.'}),

                    ('revenue', ('econ:price', {}), {
                        'doc': 'The gross revenue over the period.',
                    }),
                    ('profit', ('econ:price', {}), {
                        'doc': 'The net profit over the period.',
                    }),
                    ('valuation', ('econ:price', {}), {
                        'doc': 'The assessed value of the org.',
                    }),
                    ('shares', ('int', {}), {
                        'doc': 'The number of shares outstanding.',
                    }),
                    ('population', ('int', {}), {
                        'doc': 'The population of the org.',
                    }),
                    ('delta:costs', ('econ:price', {}), {
                        'doc': 'The change in costs over last period.',
                    }),
                    ('delta:revenue', ('econ:price', {}), {
                        'doc': 'The change in revenue over last period.',
                    }),
                    ('delta:profit', ('econ:price', {}), {
                        'doc': 'The change in profit over last period.',
                    }),
                    ('delta:valuation', ('econ:price', {}), {
                        'doc': 'The change in valuation over last period.',
                    }),
                    ('delta:population', ('int', {}), {
                        'doc': 'The change in population over last period.',
                    }),
                )),
                ('ou:award', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the award.',
                        'ex': 'Bachelors of Science',
                    }),
                    ('type', ('str', {'lower': True, 'onespace': True}), {
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
                        'alts': ('names',),
                        'doc': 'The friendly name of the ID number type.',
                    }),
                    ('names', ('array', {'type': 'str', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the ID number type.'}),
                    ('url', ('inet:url', {}), {
                        'doc': 'The official URL of the issuer.',
                    }),
                )),
                ('ou:id:number', {}, (

                    ('type', ('ou:id:type', {}), {
                        'doc': 'The type of org ID.', 'ro': True}),

                    ('value', ('ou:id:value', {}), {
                        'doc': 'The value of the org ID.', 'ro': True}),

                    ('status', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A freeform status such as valid, suspended, expired.'}),

                    ('issued', ('time', {}), {
                        'doc': 'The time at which the org issued the ID number.'}),

                    ('expires', ('time', {}), {
                        'doc': 'The time at which the ID number expires.'}),

                    ('issuer', ('ps:contact', {}), {
                        'doc': 'The contact information of the office which issued the ID number.'}),
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
                ('ou:goalname', {}, ()),
                ('ou:goal:type:taxonomy', {}, ()),
                ('ou:goal', {}, (

                    ('name', ('ou:goalname', {}), {
                        'alts': ('names',),
                        'doc': 'A terse name for the goal.'}),

                    ('names', ('array', {'type': 'ou:goalname', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the goal. Used to merge/resolve goals.'}),

                    ('type', ('ou:goal:type:taxonomy', {}), {
                        'doc': 'A type taxonomy entry for the goal.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the goal.'}),

                    ('prev', ('ou:goal', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use ou:goal:type taxonomy.'}),
                )),
                ('ou:hasgoal', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which has the goal.', 'ro': True,
                    }),
                    ('goal', ('ou:goal', {}), {
                        'doc': 'The goal which the org has.', 'ro': True,
                    }),
                    ('stated', ('bool', {}), {
                        'doc': 'Set to true/false if the goal is known to be self stated.',
                    }),
                    ('window', ('ival', {}), {
                        'doc': 'Set if a goal has a limited time window.',
                    }),
                )),
                ('ou:camptype', {}, ()),
                ('ou:campname', {}, ()),
                ('ou:campaign', {}, (
                    # political campaign, funding round, ad campaign, fund raising
                    ('org', ('ou:org', {}), {
                        'doc': 'The org carrying out the campaign.'}),

                    ('org:name', ('ou:name', {}), {
                        'doc': 'The name of the org responsible for the campaign. Used for entity resolution.'}),

                    ('org:fqdn', ('inet:fqdn', {}), {
                        'doc': 'The FQDN of the org responsible for the campaign. Used for entity resolution.'}),

                    ('goal', ('ou:goal', {}), {
                        'alts': ('goals',),
                        'doc': 'The assessed primary goal of the campaign.'}),

                    ('slogan', ('lang:phrase', {}), {
                        'doc': 'The slogan used by the campaign.'}),

                    ('actors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Actors who participated in the campaign.'}),

                    ('goals', ('array', {'type': 'ou:goal', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'Additional assessed goals of the campaign.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Records the success/failure status of the campaign if known.'}),

                    ('name', ('ou:campname', {}), {
                        'alts': ('names',),
                        'ex': 'operation overlord',
                        'doc': 'A terse name of the campaign.'}),

                    ('names', ('array', {'type': 'ou:campname', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the campaign.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the campaign.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the campaign.'}),

                    ('type', ('str', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Use the :camptype taxonomy.', }),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the campaign.',
                    }),

                    ('timeline', ('meta:timeline', {}), {
                        'doc': 'A timeline of significant events related to the campaign.'}),

                    ('camptype', ('ou:camptype', {}), {
                        'disp': {'hint': 'taxonomy'},
                        'doc': 'The campaign type taxonomy.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the campaign.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The time interval when the organization was running the campaign.'}),

                    ('cost', ('econ:price', {}), {
                        'doc': 'The actual cost to the organization.'}),

                    ('budget', ('econ:price', {}), {
                        'doc': 'The budget allocated by the organization to execute the campaign.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used to record econ:price properties.'}),

                    ('goal:revenue', ('econ:price', {}), {
                        'doc': 'A goal for revenue resulting from the campaign.'}),

                    ('result:revenue', ('econ:price', {}), {
                        'doc': 'The revenue resulting from the campaign.'}),

                    ('goal:pop', ('int', {}), {
                        'doc': 'A goal for the number of people affected by the campaign.'}),

                    ('result:pop', ('int', {}), {
                        'doc': 'The count of people affected by the campaign.'}),

                    ('team', ('ou:team', {}), {
                        'doc': 'The org team responsible for carrying out the campaign.'}),

                    ('conflict', ('ou:conflict', {}), {
                        'doc': 'The conflict in which this campaign is a primary participant.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are associated with the campaign.'}),

                    ('mitre:attack:campaign', ('it:mitre:attack:campaign', {}), {
                        'doc': 'A mapping to a MITRE ATT&CK campaign if applicable.'}),

                    ('ext:id', ('str', {'strip': True}), {
                        'doc': 'An external identifier for the campaign.'}),
                )),
                ('ou:conflict', {}, (
                    ('name', ('str', {'onespace': True}), {
                        'doc': 'The name of the conflict.'}),
                    ('started', ('time', {}), {
                        'doc': 'The time the conflict began.'}),
                    ('ended', ('time', {}), {
                        'doc': 'The time the conflict ended.'}),
                    ('timeline', ('meta:timeline', {}), {
                        'doc': 'A timeline of significant events related to the conflict.'}),
                )),
                ('ou:contribution', {}, (
                    ('from', ('ps:contact', {}), {
                        'doc': 'The contact information of the contributor.'}),
                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'The campaign receiving the contribution.'}),
                    ('value', ('econ:price', {}), {
                        'doc': 'The assessed value of the contribution.'}),
                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used for the assessed value.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the contribution occurred.'}),
                    ('material:spec', ('mat:spec', {}), {
                        'doc': 'The specification of material items contributed.'}),
                    ('material:count', ('int', {}), {
                        'doc': 'The number of material items contributed.'}),
                    ('monetary:payment', ('econ:acct:payment', {}), {
                        'doc': 'Payment details for a monetary contribution.'}),
                    ('personnel:count', ('int', {}), {
                        'doc': 'Number of personnel contributed to the campaign.'}),
                    ('personnel:jobtitle', ('ou:jobtitle', {}), {
                        'doc': 'Title or designation for the contributed personnel.'}),
                )),
                ('ou:technique', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The normalized name of the technique.'}),

                    ('type', ('ou:technique:taxonomy', {}), {
                        'doc': 'The taxonomy classification of the technique.'}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the technique.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the technique.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes where the technique was employed.'}),

                    ('mitre:attack:technique', ('it:mitre:attack:technique', {}), {
                        'doc': 'A mapping to a MITRE ATT&CK technique if applicable.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the technique.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the technique.'}),

                    ('ext:id', ('str', {'strip': True}), {
                        'doc': 'An external identifier for the technique.'}),
                )),
                ('ou:technique:taxonomy', {}, ()),
                ('ou:orgtype', {}, ()),
                ('ou:org', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'Location for an organization.'
                    }),
                    ('name', ('ou:name', {}), {
                        'alts': ('names',),
                        'doc': 'The localized name of an organization.',
                    }),
                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'deprecated': True,
                        'doc': 'The type of organization.',
                    }),
                    ('motto', ('lang:phrase', {}), {
                        'doc': 'The motto used by the organization.'}),

                    ('orgtype', ('ou:orgtype', {}), {
                        'doc': 'The type of organization.',
                        'disp': {'hint': 'taxonomy'},
                    }),
                    ('vitals', ('ou:vitals', {}), {
                        'doc': 'The most recent/accurate ou:vitals for the org.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the org.',
                        'disp': {'hint': 'text'}
                    }),
                    ('logo', ('file:bytes', {}), {
                        'doc': 'An image file representing the logo for the organization.',
                    }),
                    ('names', ('array', {'type': 'ou:name', 'uniq': True, 'sorted': True}), {
                       'doc': 'A list of alternate names for the organization.',
                    }),
                    ('alias', ('ou:alias', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use ou:org:names.',
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
                    ('industries', ('array', {'type': 'ou:industry', 'uniq': True, 'sorted': True}), {
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
                    ('subs', ('array', {'type': 'ou:org', 'uniq': True, 'sorted': True}), {
                        'doc': 'An set of sub-organizations.'
                    }),
                    ('orgchart', ('ou:position', {}), {
                        'doc': 'The root node for an orgchart made up ou:position nodes.',
                    }),
                    ('hq', ('ps:contact', {}), {
                        'doc': 'A collection of contact information for the "main office" of an org.',
                    }),
                    ('locations', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of contacts for facilities operated by the org.',
                    }),
                    ('country', ('pol:country', {}), {
                        'doc': "The organization's country of origin."}),

                    ('country:code', ('pol:iso2', {}), {
                        'doc': "The 2 digit ISO 3166 country code for the organization's country of origin."}),

                    ('dns:mx', ('array', {'type': 'inet:fqdn', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of MX domains used by email addresses issued by the org.',
                    }),
                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.',
                    }),
                    ('goals', ('array', {'type': 'ou:goal', 'sorted': True, 'uniq': True}), {
                        'doc': 'The assessed goals of the organization.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'A base tag used to encode assessments made by the organization.'}),

                    ('ext:id', ('str', {'strip': True}), {
                        'doc': 'An external identifier for the organization.'}),
                )),
                ('ou:team', {}, (
                    ('org', ('ou:org', {}), {}),
                    ('name', ('ou:name', {}), {}),
                )),

                ('ou:asset:type:taxonomy', {}, ()),
                ('ou:asset:status:taxonomy', {}, ()),
                ('ou:asset', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The organization which owns the asset.'}),

                    ('id', ('str', {'strip': True}), {
                        'doc': 'The ID of the asset.'}),

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the assset.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period of time when the asset was being tracked.'}),

                    ('status', ('ou:asset:status:taxonomy', {}), {
                        'doc': 'The current status of the asset.'}),

                    ('type', ('ou:asset:type:taxonomy', {}), {
                        'doc': 'The asset type.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The overall priority of protecting the asset.'}),

                    ('priority:confidentiality', ('meta:priority', {}), {
                        'doc': 'The priority of protecting the confidentiality of the asset.'}),

                    ('priority:integrity', ('meta:priority', {}), {
                        'doc': 'The priority of protecting the integrity of the asset.'}),

                    ('priority:availability', ('meta:priority', {}), {
                        'doc': 'The priority of protecting the availability of the asset.'}),

                    ('node', ('ndef', {}), {
                        'doc': 'The node which represents the asset.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the asset is deployed.'}),

                    ('owner', ('ps:contact', {}), {
                        'doc': 'The contact information of the owner or administrator of the asset.'}),

                    ('operator', ('ps:contact', {}), {
                        'doc': 'The contact information of the user or operator of the asset.'}),
                )),
                ('ou:position', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org which has the position.',
                    }),
                    ('team', ('ou:team', {}), {
                        'doc': 'The team that the position is a member of.',
                    }),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact info for the person who holds the position.',
                    }),
                    ('title', ('ou:jobtitle', {}), {
                        'doc': 'The title of the position.',
                    }),
                    ('reports', ('array', {'type': 'ou:position', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of positions which report to this position.',
                    }),
                )),
                ('ou:name', {}, ()),
                ('ou:conttype', {}, ()),
                ('ou:contract', {}, (
                    ('title', ('str', {}), {
                        'doc': 'A terse title for the contract.'}),
                    ('type', ('ou:conttype', {}), {
                        'doc': 'The type of contract.'}),
                    ('sponsor', ('ps:contact', {}), {
                        'doc': 'The contract sponsor.'}),
                    ('parties', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
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
                    ('award:price', ('econ:price', {}), {
                        'doc': 'The value of the contract at time of award.'}),
                    ('budget:price', ('econ:price', {}), {
                        'doc': 'The amount of money budgeted for the contract.'}),
                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the econ:price values.'}),
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'Purchase details of the contract.'}),
                    ('requirements', ('array', {'type': 'ou:goal', 'uniq': True, 'sorted': True}), {
                        'doc': 'The requirements levied upon the parties.'}),
                    ('types', ('array', {'type': 'ou:contract:type', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'deprecated': True,
                        'doc': 'A list of types that apply to the contract.'}),
                )),
                ('ou:industry:type:taxonomy', {}, ()),
                ('ou:industry', {}, (

                    ('name', ('ou:industryname', {}), {
                        'alts': ('names',),
                        'doc': 'The name of the industry.'}),

                    ('type', ('ou:industry:type:taxonomy', {}), {
                        'doc': 'A taxonomy entry for the industry.'}),

                    ('names', ('array', {'type': 'ou:industryname', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternative names for the industry.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the industry.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the industry.'}),

                    ('subs', ('array', {'type': 'ou:industry', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use ou:industry:type taxonomy.'}),

                    ('sic', ('array', {'type': 'ou:sic', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of SIC codes that map to the industry.'}),

                    ('naics', ('array', {'type': 'ou:naics', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of NAICS codes that map to the industry.'}),

                    ('isic', ('array', {'type': 'ou:isic', 'split': ',', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of ISIC codes that map to the industry.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the industry.'}),
                )),
                ('ou:industryname', {}, ()),
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
                        'doc': 'The time when the person arrived.',
                    }),
                    ('departed', ('time', {}), {
                        'doc': 'The time when the person departed.',
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
                    ('contest', ('ou:contest', {}), {
                        'doc': 'The contest that the person attended.',
                    }),
                    ('preso', ('ou:preso', {}), {
                        'doc': 'The presentation that the person attended.',
                    }),
                )),
                ('ou:preso', {}, (

                    ('organizer', ('ps:contact', {}), {
                        'doc': 'Contact information for the primary organizer of the presentation.'}),

                    ('sponsors', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'A set of contacts which sponsored the presentation.'}),

                    ('presenters', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'A set of contacts which gave the presentation.'}),

                    ('title', ('str', {'lower': True}), {
                        'doc': 'The full name of the presentation.',
                        'ex': 'Synapse 101 - 2021/06/22'}),

                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A description of the presentation.',
                        'disp': {'hint': 'text'}}),

                    ('time', ('time', {}), {
                        'doc': 'The scheduled presentation start time.'}),

                    ('duration', ('duration', {}), {
                        'doc': 'The scheduled duration of the presentation.'}),

                    ('loc', ('loc', ()), {
                        'doc': 'The geopolitical location string for where the presentation was given.'}),

                    ('place', ('geo:place', ()), {
                        'doc': 'The geo:place node where the presentation was held.'}),

                    ('deck:url', ('inet:url', ()), {
                        'doc': 'The URL hosting a copy of the presentation materials.'}),

                    ('deck:file', ('file:bytes', ()), {
                        'doc': 'A file containing the presentation materials.'}),

                    ('attendee:url', ('inet:url', ()), {
                        'doc': 'The URL visited by live attendees of the presentation.'}),

                    ('recording:url', ('inet:url', ()), {
                        'doc': 'The URL hosting a recording of the presentation.'}),

                    ('recording:file', ('file:bytes', ()), {
                        'doc': 'A file containing a recording of the presentation.'}),

                    ('conference', ('ou:conference', ()), {
                        'doc': 'The conference which hosted the presentation.'}),
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
                    ('organizer', ('ps:contact', {}), {
                        'doc': 'Contact information for the primary organizer of the conference.',
                    }),
                    ('sponsors', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of contacts which sponsored the conference.',
                    }),
                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The full name of the conference.',
                        'ex': 'defcon 2017'}),

                    ('names', ('array', {'type': 'entity:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the conference.'}),

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
                    ('roles', ('array', {'type': 'str', 'uniq': True, 'sorted': True}), {
                        'doc': 'List of the roles the person had at the conference.',
                    }),
                 )),
                ('ou:conference:event', {}, (
                    ('conference', ('ou:conference', {}), {
                        'ro': True,
                        'doc': 'The conference to which the event is associated.',
                    }),
                    ('organizer', ('ps:contact', {}), {
                        'doc': 'Contact information for the primary organizer of the event.',
                    }),
                    ('sponsors', ('array', {'type': 'ps:contact', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of contacts which sponsored the event.',
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
                    ('roles', ('array', {'type': 'str', 'uniq': True, 'sorted': True}), {
                        'doc': 'List of the roles the person had at the conference event.',
                    }),
                )),
                ('ou:contest', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the contest.',
                        'ex': 'defcon ctf 2020',
                    }),
                    ('type', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The type of contest.',
                        'ex': 'cyber ctf',
                    }),
                    ('family', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for a series of recurring contests.',
                        'ex': 'defcon ctf',
                    }),
                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A description of the contest.',
                        'ex': 'the capture-the-flag event hosted at defcon 2020',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The contest website URL.'
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
                        'doc': 'The contest that the participant took part in.'}),

                    ('participant', ('ps:contact', {}), {
                        'ro': True,
                        'doc': 'The participant in the contest.'}),

                    ('rank', ('int', {}), {
                        'doc': "The participant's rank order in the contest."}),

                    ('score', ('int', {}), {
                        'doc': "The participant's final score in the contest."}),

                    ('period', ('ival', {}), {
                        'doc': 'The period of time when the participant competed in the contest.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The contest result website URL.'}),

                )),
                ('ou:enacted:status:taxonomy', {}, ()),
                ('ou:enacted', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The organization which is enacting the document.'}),

                    ('doc', ('ndef', {'forms': ('doc:policy', 'doc:standard', 'doc:requirement')}), {
                        'doc': 'The document enacted by the organization.'}),

                    ('scope', ('ndef', {}), {
                        'doc': 'The scope of responsbility for the assignee to enact the document.'}),
                )),

                ('ou:requirement:type:taxonomy', {}, ()),
                ('ou:requirement', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the requirement.'}),

                    ('type', ('ou:requirement:type:taxonomy', {}), {
                        'doc': 'The type of requirement.'}),

                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The text of the stated requirement.'}),

                    ('optional', ('bool', {}), {
                        'doc': 'Set to true if the requirement is optional.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The priority of the requirement.'}),

                    ('goal', ('ou:goal', {}), {
                        'doc': 'The goal that the requirement is designed to achieve.'}),

                    ('active', ('bool', {}), {
                        'doc': 'Set to true if the requirement is currently active.'}),

                    ('issued', ('time', {}), {
                        'doc': 'The time that the requirement was first issued.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The time window where the goal must be met. Can be ongoing.'}),

                    ('issuer', ('ps:contact', {}), {
                        'doc': 'The contact information of the entity which issued the requirement.'}),

                    ('assignee', ('ps:contact', {}), {
                        'doc': 'The contact information of the entity which is assigned to meet the requirement.'}),

                    ('deps', ('array', {'type': 'ou:requirement', 'sorted': True, 'uniq': True}), {
                        'doc': 'A list of sub-requirements which must be met to complete the requirement.'}),

                    ('deps:min', ('int', {'min': 0}), {
                        'doc': 'The minimum number dependant requirements which must be met. If unset, assume all must be met.'}),
                )),
            )
        }

        name = 'ou'
        return ((name, modl),)
