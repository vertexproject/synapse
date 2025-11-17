contracttypes = (
    'nda',
    'other',
    'grant',
    'treaty',
    'purchase',
    'indemnity',
    'partnership',
)

modeldefs = (
    ('ou', {

        'interfaces': (

            ('ou:attendable', {
                'template': {'title': 'event'},
                'interfaces': (
                    ('meta:havable', {}),
                    ('entity:attendable', {}),
                ),
                'props': (

                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'ex': 'cyberwarcon 2025',
                        'doc': 'The name of the {title}.'}),

                    ('name:base', ('meta:name', {}), {
                        'ex': 'cyberwarcon',
                        'doc': 'The base name of the {title} (for a recurring event).'}),

                    ('names', ('array', {'type': 'meta:name'}), {
                        'doc': 'An array of alternate names for the {title}.'}),
                ),
                'doc': 'An interface which is inherited by all organized events.'}),

            ('ou:sponsored', {
                'template': {'title': 'event'},
                'interfaces': (
                    ('ou:attendable', {}),
                ),
                'props': (

                    ('website', ('inet:url', {}), {
                        'prevnames': ('url',),
                        'doc': 'The URL of the {title} website.'}),

                    ('contact', ('entity:contact', {}), {
                        'doc': 'Contact information for the {title}.'}),

                    ('sponsors', ('array', {'type': 'entity:actor'}), {
                        'doc': 'The entities which sponsored the {title}.'}),

                    ('organizers', ('array', {'type': 'entity:actor'}), {
                        'doc': 'An array of {title} organizers.'}),
                ),
                'doc': 'Properties which are common to events which are hosted or sponsored by organizations.'}),
        ),
        'types': (
            ('ou:sic', ('str', {'regex': r'^[0-9]{4}$'}), {
                'ex': '0111',
                'doc': 'The four digit Standard Industrial Classification Code.'}),

            ('ou:naics', ('str', {'regex': r'^[1-9][0-9]{1,5}?$', 'strip': True}), {
                'ex': '541715',
                'doc': 'North American Industry Classification System codes and prefixes.'}),

            ('ou:isic', ('str', {'regex': r'^[A-Z]([0-9]{2}[0-9]{0,2})?$'}), {
                'ex': 'C1393',
                'doc': 'An International Standard Industrial Classification of All Economic Activities (ISIC) code.'}),

            ('ou:org', ('guid', {}), {
                'template': {'title': 'organization'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:multiple', {}),
                ),
                'doc': 'An organization, such as a company or military unit.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'names'}},
                        {'type': 'prop', 'opts': {'name': 'place:country:code'}},
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

            ('ou:org:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of organization types.'}),

            ('ou:asset:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'An asset type taxonomy.'}),

            ('ou:asset:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
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

            ('ou:industry', ('guid', {}), {
                'interfaces': (
                    ('risk:targetable', {}),
                    ('meta:reported', {'template': {'title': 'industry'}}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                    ),
                },
                'doc': 'An industry classification type.'}),

            ('ou:industry:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of industry types.'}),

            ('ou:orgnet', ('guid', {}), {
                'doc': 'An IP address block which belongs to an organization.'}),

            ('ou:position', ('guid', {}), {
                'doc': 'A position within an org which can be organized into an org chart with replaceable contacts.'}),

            ('ou:meeting', ('guid', {}), {
                'prevnames': ('ou:meet',),
                'interfaces': (
                    ('ou:attendable', {'template': {'title': 'meeting'}}),
                ),
                'doc': 'A meeting.'}),

            ('ou:preso', ('guid', {}), {
                'interfaces': (
                    ('ou:sponsored', {'template': {'title': 'presentation'}}),
                ),
                'doc': 'A webinar, conference talk, or other type of presentation.'}),

            ('ou:conference', ('guid', {}), {
                'template': {'title': 'conference'},
                'interfaces': (
                    ('ou:sponsored', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        # TODO allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period.min'}},
                        # {'type': 'prop', 'opts': {'name': 'period.max'}},
                    ),
                },
                'doc': 'A conference.'}),

            ('ou:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of event types.'}),

            ('ou:event', ('guid', {}), {
                'template': {'title': 'event'},
                'prevnames': ('ou:conference:event',),
                'interfaces': (
                    ('ou:sponsored', {}),
                ),
                'doc': 'An generic organized event.'}),

            ('ou:contest:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of contest types.'}),

            ('ou:contest', ('guid', {}), {
                'template': {'title': 'contest'},
                'interfaces': (
                    ('ou:sponsored', {}),
                ),
                'doc': 'A competitive event resulting in a ranked set of participants.'}),

            ('ou:contest:result', ('guid', {}), {
                'doc': 'The results from a single contest participant.'}),

            ('ou:id', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'ID'}}),
                ),
                'doc': 'An ID value issued by an organization.'}),

            ('ou:id:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of ID types.'}),

            ('ou:id:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of ID status values.'}),

            ('ou:id:history', ('guid', {}), {
                'prevnames': ('ou:id:update',),
                'doc': 'Changes made to an ID over time.'}),

            ('ou:award:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of award types.'}),

            ('ou:award', ('guid', {}), {
                'doc': 'An award issued by an organization.'}),

            ('ou:vitals', ('guid', {}), {
                'doc': 'Vital statistics about an org for a given time period.'}),

            ('ou:opening', ('guid', {}), {
                'doc': 'A job/work opening within an org.'}),

            ('ou:job:type:taxonomy', ('taxonomy', {}), {
                'ex': 'it.dev.python',
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of job types.'}),

            ('ou:candidate:method:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of methods by which a candidate came under consideration.'}),

            ('ou:candidate', ('guid', {}), {
                'doc': 'A candidate being considered for a role within an organization.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'contact::name'}},
                        {'type': 'prop', 'opts': {'name': 'contact::email'}},
                        {'type': 'prop', 'opts': {'name': 'submitted'}},
                        {'type': 'prop', 'opts': {'name': 'org::name'}},
                        {'type': 'prop', 'opts': {'name': 'opening::title'}},
                    ),
                }}),

            ('ou:candidate:referral', ('guid', {}), {
                'doc': 'A candidate being referred by a contact.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'referrer::name'}},
                        {'type': 'prop', 'opts': {'name': 'candidate::contact::name'}},
                        {'type': 'prop', 'opts': {'name': 'candidate::org::name'}},
                        {'type': 'prop', 'opts': {'name': 'candidate::opening::title'}},
                        {'type': 'prop', 'opts': {'name': 'submitted'}},
                    ),
                }}),

            ('ou:employment:type:taxonomy', ('taxonomy', {}), {
                'ex': 'fulltime.salary',
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of employment types.'}),

            ('ou:enacted:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of enacted statuses.'}),

            ('ou:enacted', ('guid', {}), {
                'interfaces': (
                    ('proj:doable', {
                        'template': {
                            'task': 'adoption task'}}),
                ),
                'doc': 'An organization enacting a document.'}),
        ),
        'edges': (

        ),
        'forms': (

            ('ou:job:type:taxonomy', {
                'prevnames': ('ou:jobtype',)}, ()),

            ('ou:employment:type:taxonomy', {
                'prevnames': ('ou:employment',)}, ()),

            ('ou:opening', {}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The org which has the opening.'}),

                ('org:name', ('meta:name', {}), {
                    'doc': 'The name of the organization as listed in the opening.'}),

                ('org:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN of the organization as listed in the opening.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('posted', 'removed'),
                    'doc': 'The time period when the opening existed.'}),

                ('postings', ('array', {'type': 'inet:url'}), {
                    'doc': 'URLs where the opening is listed.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact details to inquire about the opening.'}),

                ('loc', ('loc', {}), {
                    'doc': 'The geopolitical boundary of the opening.'}),

                ('job:type', ('ou:job:type:taxonomy', {}), {
                    'doc': 'The job type taxonomy.',
                    'prevnames': ('jobtype',)}),

                ('employment:type', ('ou:employment:type:taxonomy', {}), {
                    'doc': 'The type of employment.',
                    'prevnames': ('employment',)}),

                ('title', ('entity:title', {}), {
                    'prevnames': ('jobtitle',),
                    'doc': 'The title of the opening.'}),

                ('remote', ('bool', {}), {
                    'doc': 'Set to true if the opening will allow a fully remote worker.'}),

                ('pay:min', ('econ:price', {}), {
                    'prevnames': ('yearlypay',),
                    'doc': 'The minimum pay for the job.'}),

                ('pay:max', ('econ:price', {}), {
                    'doc': 'The maximum pay for the job.'}),

                ('pay:currency', ('econ:currency', {}), {
                    'prevnames': ('paycurrency',),
                    'doc': 'The currency used for payment.'}),

                ('pay:pertime', ('duration', {}), {
                    'ex': '1:00:00',
                    'doc': 'The duration over which the position pays.'}),

            )),
            ('ou:candidate:method:taxonomy', {}, ()),
            ('ou:candidate', {}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The organization considering the candidate.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact information of the candidate.'}),

                ('method', ('ou:candidate:method:taxonomy', {}), {
                    'doc': 'The method by which the candidate came under consideration.'}),

                ('submitted', ('time', {}), {
                    'doc': 'The time the candidate was submitted for consideration.'}),

                ('intro', ('str', {'strip': True}), {
                    'doc': 'An introduction or cover letter text submitted by the candidate.'}),

                ('resume', ('doc:resume', {}), {
                    'doc': "The candidate's resume or CV."}),

                ('opening', ('ou:opening', {}), {
                    'doc': 'The opening that the candidate is being considered for.'}),

                ('agent', ('entity:contact', {}), {
                    'doc': 'The contact information of an agent who advocates for the candidate.'}),

                ('recruiter', ('entity:contact', {}), {
                    'doc': 'The contact information of a recruiter who works on behalf of the organization.'}),

                ('attachments', ('array', {'type': 'file:attachment'}), {
                    'doc': 'An array of additional files submitted by the candidate.'}),

                # TODO: doc:questionare / responses
                # TODO: :skills=[<ps:skill>]? vs :contact -> ps:proficiency?
                # TODO: proj:task to track evaluation of the candidate?

            )),

            ('ou:candidate:referral', {}, (

                ('candidate', ('ou:candidate', {}), {
                    'doc': 'The candidate who was referred.'}),

                ('referrer', ('entity:contact', {}), {
                    'doc': 'The individual who referred the candidate to the opening.'}),

                ('submitted', ('time', {}), {
                    'doc': 'The time the referral was submitted.'}),

                ('text', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'Text of any referrer provided context about the candidate.'}),
            )),

            ('ou:vitals', {}, (

                ('time', ('time', {}), {
                    'prevnames': ('asof',),
                    'doc': 'The time that the vitals represent.'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The resolved org.'}),

                ('org:name', ('meta:name', {}), {
                    'prevnames': ('orgname',),
                    'doc': 'The org name as reported by the source of the vitals.'}),

                ('org:fqdn', ('inet:fqdn', {}), {
                    'prevnames': ('orgfqdn',),
                    'doc': 'The org FQDN as reported by the source of the vitals.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the econ:price values.'}),

                ('costs', ('econ:price', {}), {
                    'doc': 'The costs/expenditures over the period.'}),

                ('budget', ('econ:price', {}), {
                    'doc': 'The budget allocated for the period.'}),

                ('revenue', ('econ:price', {}), {
                    'doc': 'The gross revenue over the period.'}),

                ('profit', ('econ:price', {}), {
                    'doc': 'The net profit over the period.'}),

                ('valuation', ('econ:price', {}), {
                    'doc': 'The assessed value of the org.'}),

                ('shares', ('int', {}), {
                    'doc': 'The number of shares outstanding.'}),

                ('population', ('int', {}), {
                    'doc': 'The population of the org.'}),

                ('delta:costs', ('econ:price', {}), {
                    'doc': 'The change in costs over last period.'}),

                ('delta:revenue', ('econ:price', {}), {
                    'doc': 'The change in revenue over last period.'}),

                ('delta:profit', ('econ:price', {}), {
                    'doc': 'The change in profit over last period.'}),

                ('delta:valuation', ('econ:price', {}), {
                    'doc': 'The change in valuation over last period.'}),

                ('delta:population', ('int', {}), {
                    'doc': 'The change in population over last period.'}),
            )),
            ('ou:award:type:taxonomy', {}, ()),
            ('ou:award', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the award.',
                    'ex': 'Bachelors of Science'}),

                ('type', ('ou:award:type:taxonomy', {}), {
                    'doc': 'The type of award.',
                    'ex': 'certification'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The organization which issues the award.'}),

            )),

            ('ou:id:type:taxonomy', {}, ()),
            ('ou:id:status:taxonomy', {}, ()),
            ('ou:id', {}, (

                ('type', ('ou:id:type:taxonomy', {}), {
                    'doc': 'The type of ID issued.'}),

                ('status', ('ou:id:status:taxonomy', {}), {
                    'ex': 'valid',
                    'doc': 'The most recently known status of the ID.'}),

                ('value', ('entity:identifier', {}), {
                    'doc': 'The ID value.'}),

                ('issued', ('date', {}), {
                    'doc': 'The date when the ID was initially issued.'}),

                ('updated', ('date', {}), {
                    'doc': 'The date when the ID was most recently updated.'}),

                ('expires', ('date', {}), {
                    'doc': 'The date when the ID expires.'}),

                ('issuer', ('ou:org', {}), {
                    'doc': 'The organization which issued the ID.'}),

                ('issuer:name', ('meta:name', {}), {
                    'doc': 'The name of the issuer.'}),

                ('recipient', ('entity:actor', {}), {
                    'doc': 'The entity which was issued the ID.'}),
            )),
            ('ou:id:history', {}, (

                ('id', ('ou:id', {}), {
                    'doc': 'The current ID information.'}),

                ('updated', ('date', {}), {
                    'doc': 'The time the ID was updated.'}),

                ('status', ('ou:id:status:taxonomy', {}), {
                    'doc': 'The status of the ID at the time.'}),
            )),

            ('ou:org:type:taxonomy', {
                'prevnames': ('ou:orgtype',)}, ()),

            ('ou:org', {}, (

                ('motto', ('lang:phrase', {}), {
                    'doc': 'The motto used by the organization.'}),

                ('type', ('ou:org:type:taxonomy', {}), {
                    'doc': 'The type of organization.',
                    'prevnames': ('orgtype',)}),

                ('vitals', ('ou:vitals', {}), {
                    'doc': 'The most recent/accurate ou:vitals for the org.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the organization.'}),

                ('logo', ('file:bytes', {}), {
                    'doc': 'An image file representing the logo for the organization.'}),

                ('industries', ('array', {'type': 'ou:industry'}), {
                    'doc': 'The industries associated with the org.'}),

                ('subs', ('array', {'type': 'ou:org'}), {
                    'doc': 'An set of sub-organizations.'}),

                ('orgchart', ('ou:position', {}), {
                    'doc': 'The root node for an orgchart made up ou:position nodes.'}),

                ('dns:mx', ('array', {'type': 'inet:fqdn'}), {
                    'doc': 'An array of MX domains used by email addresses issued by the org.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'A base tag used to encode assessments made by the organization.'}),
            )),
            ('ou:team', {}, (
                ('org', ('ou:org', {}), {}),
                ('name', ('meta:name', {}), {}),
            )),

            ('ou:asset:type:taxonomy', {}, ()),
            ('ou:asset:status:taxonomy', {}, ()),
            ('ou:asset', {}, (
                ('org', ('ou:org', {}), {
                    'doc': 'The organization which owns the asset.'}),

                ('id', ('meta:id', {}), {
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

                ('owner', ('entity:contact', {}), {
                    'doc': 'The contact information of the owner or administrator of the asset.'}),

                ('operator', ('entity:contact', {}), {
                    'doc': 'The contact information of the user or operator of the asset.'}),
            )),
            ('ou:position', {}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The org which has the position.'}),

                ('team', ('ou:team', {}), {
                    'doc': 'The team that the position is a member of.'}),

                ('contact', ('entity:individual', {}), {
                    'doc': 'The contact info for the person who holds the position.'}),

                ('title', ('entity:title', {}), {
                    'doc': 'The title of the position.'}),

                ('reports', ('array', {'type': 'ou:position'}), {
                    'doc': 'An array of positions which report to this position.'}),
            )),

            ('ou:industry:type:taxonomy', {}, ()),
            ('ou:industry', {}, (

                ('type', ('ou:industry:type:taxonomy', {}), {
                    'doc': 'A taxonomy entry for the industry.'}),

                ('sic', ('array', {'type': 'ou:sic', 'split': ','}), {
                    'doc': 'An array of SIC codes that map to the industry.'}),

                ('naics', ('array', {'type': 'ou:naics', 'split': ','}), {
                    'doc': 'An array of NAICS codes that map to the industry.'}),

                ('isic', ('array', {'type': 'ou:isic', 'split': ','}), {
                    'doc': 'An array of ISIC codes that map to the industry.'}),
            )),
            ('ou:orgnet', {
                'prevnames': ('ou:orgnet4', 'ou:orgnet6')}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The org guid which owns the netblock.'}),

                ('net', ('inet:net', {}), {
                    'doc': 'Netblock owned by the organization.'}),

                ('name', ('base:name', {}), {
                    'doc': 'The name that the organization assigns to this netblock.'}),
            )),
            ('ou:preso', {}, (

                ('presenters', ('array', {'type': 'entity:individual'}), {
                    'doc': 'An array of individuals who gave the presentation.'}),

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
            )),
            ('ou:meeting', {}, (
                ('hosts', ('array', {'type': 'entity:actor'}), {
                    'doc': 'The contacts who hosted or called the meeting.'}),
            )),
            ('ou:conference', {}, ()),
            ('ou:event', {}, (
                ('type', ('ou:event:type:taxonomy', {}), {
                    'doc': 'The type of event.'}),
            )),
            ('ou:contest:type:taxonomy', {}, ()),
            ('ou:contest', {}, (

                ('type', ('ou:contest:type:taxonomy', {}), {
                    'ex': 'cyber.ctf',
                    'doc': 'The type of contest.'}),

            )),
            ('ou:contest:result', {}, (

                ('contest', ('ou:contest', {}), {
                    'doc': 'The contest that the participant took part in.'}),

                ('participant', ('entity:actor', {}), {
                    'doc': 'The participant in the contest.'}),

                ('rank', ('int', {}), {
                    'doc': "The participant's rank order in the contest."}),

                ('score', ('int', {}), {
                    'doc': "The participant's final score in the contest."}),

                ('period', ('ival', {}), {
                    'doc': 'The period of time when the participant competed in the contest.'}),
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
        ),
    }),
)
