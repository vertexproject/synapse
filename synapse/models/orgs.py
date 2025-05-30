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
                'template': {'ou:attendable': 'event'},
                'interfaces': (
                    ('geo:locatable', {
                        'template': {'geo:locatable': 'event'}}),
                ),
                'props': (
                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'doc': 'The name of the {ou:attendable}.'}),

                    ('names', ('array', {'type': 'meta:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the {ou:attendable}.'}),

                    ('desc', ('text', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'An organizer provided description of the {ou:attendable}.'}),

                    ('family', ('meta:name', {}), {
                        'ex': 'cyberwarcon',
                        'doc': 'A base name for a series of recurring {ou:attendable}s.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period of time over which the {ou:attendable} occurred.'}),

                    ('website', ('inet:url', {}), {
                        'prevnames': ('url',),
                        'doc': 'The URL of the {ou:attendable} website.'}),

                    ('parent', ('ou:attendable', {}), {
                        'doc': 'The parent event which hosts the {ou:attendable}.'}),

                    ('accounts', ('array', {'type': 'inet:service:account', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of social media accounts for the {ou:attendable}.'}),

                    ('sponsors', ('array', {'type': 'entity:actor', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of {ou:attendable}  sponsors.'}),

                    ('organizers', ('array', {'type': 'entity:actor', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of {ou:attendable} organizers.'}),
                ),
                'doc': 'An interface which is inherited by all organized events.'}),
        ),
        'types': (
            ('ou:attendable', ('ndef', {'interface': 'ou:attendable'}), {
                'doc': 'An event which can be formally attended.'}),

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
                'interfaces': (
                    ('entity:actor', {
                        'template': {'contactable': 'organization'}}),
                ),
                'doc': 'An organization, such as a company or military unit.',
                'aliases': (
                    ('founded', {'target': 'lifespan*max',
                        'doc': 'The founded time for the entity.'}),

                    ('dissolved', {'target': 'lifespan*max',
                        'doc': 'The dissolved time for the entity.'}),
                ),
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

            ('ou:contract', ('guid', {}), {
                'doc': 'An contract between multiple entities.'}),

            ('ou:contract:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of contract types.'}),

            ('ou:industry', ('guid', {}), {
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
                'doc': 'An IP address block which belongs to an orgnaization.'}),

            ('ou:position', ('guid', {}), {
                'doc': 'A position within an org which can be organized into an org chart with replacable contacts.'}),

            ('ou:attendee', ('guid', {}), {
                'doc': 'An individual attending an organized event.'}),

            ('ou:meet', ('guid', {}), {
                'interfaces': (
                    ('ou:attendable', {
                        'template': {
                            'ou:attendable': 'meet',
                            'geo:locatable': 'meet'}}),
                ),
                'doc': 'A meeting of people which has no title or sponsor.'}),

            ('ou:preso', ('guid', {}), {
                'interfaces': (
                    ('ou:attendable', {}),
                ),
                'doc': 'A webinar, conference talk, or other type of presentation.'}),

            ('ou:conference', ('guid', {}), {
                'interfaces': (
                    ('ou:attendable', {
                        'template': {
                            'ou:attendable': 'conference',
                            'geo:locatable': 'conference'}}),
                ),

                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        # FIXME allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period*min'}},
                        # {'type': 'prop', 'opts': {'name': 'period*max'}},
                    ),
                },
                'doc': 'A conference.'}),

            ('ou:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of event types.'}),

            ('ou:event', ('guid', {}), {
                'prevnames': ('ou:conference:event',),
                'interfaces': (
                    ('ou:attendable', {}),
                ),
                'doc': 'An generic organized event.'}),

            ('ou:contest:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of contest types.'}),

            ('ou:contest', ('guid', {}), {
                'interfaces': (
                    ('ou:attendable', {}),
                ),
                'doc': 'A competitive event resulting in a ranked set of participants.'}),

            ('ou:contest:result', ('guid', {}), {
                'doc': 'The results from a single contest participant.'}),

            ('ou:goal', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                    ),
                },
                'doc': 'An assessed or stated goal which may be abstract or org specific.'}),

            ('ou:goal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of goal types.'}),

            ('ou:campaign:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of campaign types.'}),

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
                'doc': 'Represents a conflict where two or more campaigns have mutually exclusive goals.'}),

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

            ('ou:technique:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of technique types.'}),

            ('ou:id', ('guid', {}), {
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

            ('ou:id:update', ('guid', {}), {
                'doc': 'An update to an ID status.'}),

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
                    ('proj:task', {
                        'template': {
                            'task': 'adoption task'}}),
                ),
                'doc': 'An organization enacting a document.'}),
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

            (('ou:org', 'has', None), {
                'doc': 'The organization is or was in possession of the target node.'}),

            (('ou:org', 'owns', None), {
                'doc': 'The organization owns or owned the target node.'}),
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

                ('posted', ('time', {}), {
                    'doc': 'The date/time that the job opening was posted.'}),

                ('removed', ('time', {}), {
                    'doc': 'The date/time that the job opening was removed.'}),

                ('postings', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                    'doc': 'URLs where the opening is listed.'}),

                ('contact', ('entity:actor', {}), {
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

                ('yearlypay', ('econ:price', {}), {
                    'doc': 'The yearly income associated with the opening.'}),

                ('paycurrency', ('econ:currency', {}), {
                    'doc': 'The currency that the yearly pay was delivered in.'}),

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

                ('resume', ('file:bytes', {}), {
                    'doc': "The candidate's resume or CV."}),

                ('opening', ('ou:opening', {}), {
                    'doc': 'The opening that the candidate is being considered for.'}),

                ('agent', ('entity:contact', {}), {
                    'doc': 'The contact information of an agent who advocates for the candidate.'}),

                ('recruiter', ('entity:contact', {}), {
                    'doc': 'The contact information of a recruiter who works on behalf of the organization.'}),

                ('attachments', ('array', {'type': 'file:attachment', 'sorted': True, 'uniq': True}), {
                    'doc': 'An array of additional files submitted by the candidate.'}),

                # TODO: doc:questionare / responses
                # TODO: :skills=[<ps:skill>]? vs :contact -> ps:proficiency?
                # TODO: proj:task to track evaluation of the candidate?

            )),
            ('ou:vitals', {}, (

                ('asof', ('time', {}), {
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

                # FIXME interface for issued IDs and make this an ndef prop?
                ('value', ('meta:id', {}), {
                    'doc': 'The ID value.'}),

                ('issued', ('date', {}), {
                    'doc': 'The date when the ID was initially issued.'}),

                ('updated', ('date', {}), {
                    'doc': 'The date when the ID was most recently updated.'}),

                ('issuer', ('ou:org', {}), {
                    'doc': 'The organization which issued the ID.'}),

                ('issuer:name', ('meta:name', {}), {
                    'doc': 'The name of the issuer.'}),

                ('recipient', ('entity:actor', {}), {
                    'doc': 'The entity which was issued the ID.'}),
            )),
            ('ou:id:update', {}, (

                ('id', ('ou:id', {}), {
                    'doc': 'The ID which was updated.'}),

                ('updated', ('date', {}), {
                    'doc': 'The time the ID status was updated.'}),

                ('status', ('ou:id:status:taxonomy', {}), {
                    'doc': 'The new status of the ID.'}),
            )),
            ('ou:goal:type:taxonomy', {}, ()),
            ('ou:goal', {}, (

                ('name', ('meta:name', {}), {
                    'alts': ('names',),
                    'doc': 'A terse name for the goal.'}),

                ('names', ('array', {'type': 'meta:name', 'sorted': True, 'uniq': True}), {
                    'doc': 'An array of alternate names for the goal. Used to merge/resolve goals.'}),

                ('type', ('ou:goal:type:taxonomy', {}), {
                    'doc': 'A type taxonomy entry for the goal.'}),

                ('desc', ('text', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the goal.'}),
            )),
            ('ou:campaign:type:taxonomy', {
                'prevnames': ('ou:camptype',)}, ()),

            ('ou:campaign', {}, (

                ('id', ('meta:id', {}), {
                    'prevnames': ('id',),
                    'doc': 'The campaign ID.'}),

                # political campaign, funding round, ad campaign, fund raising
                ('org', ('ou:org', {}), {
                    'doc': 'The org carrying out the campaign.'}),

                ('org:name', ('meta:name', {}), {
                    'doc': 'The name of the org responsible for the campaign. Used for entity resolution.'}),

                ('org:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN of the org responsible for the campaign. Used for entity resolution.'}),

                ('goal', ('ou:goal', {}), {
                    'alts': ('goals',),
                    'doc': 'The assessed primary goal of the campaign.'}),

                ('slogan', ('lang:phrase', {}), {
                    'doc': 'The slogan used by the campaign.'}),

                # TODO: move to contribution?
                ('actors', ('array', {'type': 'entity:actor', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'Actors who participated in the campaign.'}),

                ('goals', ('array', {'type': 'ou:goal', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'Additional assessed goals of the campaign.'}),

                ('success', ('bool', {}), {
                    'doc': 'Records the success/failure status of the campaign if known.'}),

                ('name', ('meta:name', {}), {
                    'alts': ('names',),
                    'ex': 'operation overlord',
                    'doc': 'A terse name of the campaign.'}),

                ('names', ('array', {'type': 'meta:name', 'sorted': True, 'uniq': True}), {
                    'doc': 'An array of alternate names for the campaign.'}),

                ('reporter', ('ou:org', {}), {
                    'doc': 'The organization reporting on the campaign.'}),

                ('reporter:name', ('meta:name', {}), {
                    'doc': 'The name of the organization reporting on the campaign.'}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': 'The assessed sophistication of the campaign.'}),

                ('timeline', ('meta:timeline', {}), {
                    'doc': 'A timeline of significant events related to the campaign.'}),

                ('type', ('ou:campaign:type:taxonomy', {}), {
                    'doc': 'The campaign type taxonomy.',
                    'prevnames': ('camptype',)}),

                ('desc', ('text', {}), {
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

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes that are associated with the campaign.'}),

                ('mitre:attack:campaign', ('it:mitre:attack:campaign', {}), {
                    'doc': 'A mapping to a MITRE ATT&CK campaign if applicable.'}),

            )),
            ('ou:conflict', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the conflict.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period of time when the conflict was ongoing.'}),

                # FIXME timeline interface?
                ('timeline', ('meta:timeline', {}), {
                    'doc': 'A timeline of significant events related to the conflict.'}),
            )),
            ('ou:contribution', {}, (

                ('from', ('entity:actor', {}), {
                    'doc': 'The actor who made the contribution.'}),

                ('campaign', ('ou:campaign', {}), {
                    'doc': 'The campaign receiving the contribution.'}),

                ('value', ('econ:price', {}), {
                    'doc': 'The assessed value of the contribution.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency used for the assessed value.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the contribution occurred.'}),

                # FIXME aggregates?
                ('material:spec', ('mat:spec', {}), {
                    'doc': 'The specification of material items contributed.'}),

                ('material:count', ('int', {}), {
                    'doc': 'The number of material items contributed.'}),

                ('monetary:payment', ('econ:acct:payment', {}), {
                    'doc': 'Payment details for a monetary contribution.'}),

                ('personnel:count', ('int', {}), {
                    'doc': 'Number of personnel contributed to the campaign.'}),

                ('personnel:title', ('entity:title', {}), {
                    'prevnames': ('personnel:jobtitle',),
                    'doc': 'Title or designation for the contributed personnel.'}),
            )),
            ('ou:technique', {}, (

                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The normalized name of the technique.'}),

                ('type', ('ou:technique:type:taxonomy', {}), {
                    'doc': 'The taxonomy classification of the technique.'}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': 'The assessed sophistication of the technique.'}),

                ('desc', ('text', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the technique.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes where the technique was employed.'}),

                ('mitre:attack:technique', ('it:mitre:attack:technique', {}), {
                    'doc': 'A mapping to a MITRE ATT&CK technique if applicable.'}),

                ('reporter', ('ou:org', {}), {
                    'doc': 'The organization reporting on the technique.'}),

                ('reporter:name', ('meta:name', {}), {
                    'doc': 'The name of the organization reporting on the technique.'}),

                ('id', ('meta:id', {}), {
                    'prevnames': ('id',),
                    'doc': 'The technique ID.'}),
            )),
            ('ou:technique:type:taxonomy', {
                'prevnames': ('ou:technique:taxonomy',)}, ()),

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
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the organization.'}),

                ('logo', ('file:bytes', {}), {
                    'doc': 'An image file representing the logo for the organization.'}),

                ('industries', ('array', {'type': 'ou:industry', 'uniq': True, 'sorted': True}), {
                    'doc': 'The industries associated with the org.'}),

                # FIXME: invert this or use org ID?
                ('gov:us:cage', ('gov:us:cage', {}), {
                    'prevnames': ('us:cage',),
                    'doc': 'The US Commercial and Government Entity (CAGE) code for the organization.'}),

                # FIXME discuss
                ('subs', ('array', {'type': 'ou:org', 'uniq': True, 'sorted': True}), {
                    'doc': 'An set of sub-organizations.'}),

                ('orgchart', ('ou:position', {}), {
                    'doc': 'The root node for an orgchart made up ou:position nodes.'}),

                # FIXME geo:locatable
                # FIXME geo:place with owner/operator?
                # ('locations', ('array', {'type': 'entity:contact', 'uniq': True, 'sorted': True}), {
                #   'doc': 'An array of contacts for facilities operated by the org.',
                # }),

                ('dns:mx', ('array', {'type': 'inet:fqdn', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of MX domains used by email addresses issued by the org.'}),

                ('goals', ('array', {'type': 'ou:goal', 'sorted': True, 'uniq': True}), {
                    'doc': 'The assessed goals of the organization.'}),

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

                ('reports', ('array', {'type': 'ou:position', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of positions which report to this position.'}),
            )),

            ('ou:contract:type:taxonomy', {
                'prevnames': ('ou:conttype',)}, ()),

            ('ou:contract', {}, (

                ('title', ('str', {}), {
                    'doc': 'A terse title for the contract.'}),

                ('type', ('ou:contract:type:taxonomy', {}), {
                    'doc': 'The type of contract.'}),

                ('sponsor', ('entity:actor', {}), {
                    'doc': 'The contract sponsor.'}),

                ('parties', ('array', {'type': 'entity:actor', 'uniq': True, 'sorted': True}), {
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

                # FIXME should this be modified?
                ('requirements', ('array', {'type': 'ou:goal', 'uniq': True, 'sorted': True}), {
                    'doc': 'The requirements levied upon the parties.'}),
            )),
            ('ou:industry:type:taxonomy', {}, ()),
            ('ou:industry', {}, (

                ('name', ('meta:name', {}), {
                    'alts': ('names',),
                    'doc': 'The name of the industry.'}),

                ('names', ('array', {'type': 'meta:name', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of alternative names for the industry.'}),

                ('type', ('ou:industry:type:taxonomy', {}), {
                    'doc': 'A taxonomy entry for the industry.'}),

                # FIXME source?
                ('reporter', ('entity:actor', {}), {
                    'doc': 'The organization reporting on the industry.'}),

                ('reporter:name', ('meta:name', {}), {
                    'doc': 'The name of the organization reporting on the industry.'}),

                ('sic', ('array', {'type': 'ou:sic', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of SIC codes that map to the industry.'}),

                ('naics', ('array', {'type': 'ou:naics', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of NAICS codes that map to the industry.'}),

                ('isic', ('array', {'type': 'ou:isic', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of ISIC codes that map to the industry.'}),

                ('desc', ('text', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the industry.'}),
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
            ('ou:attendee', {}, (

                ('person', ('entity:individual', {}), {
                    'doc': 'The individual who attended the event.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the person attended the event.'}),

                ('roles', ('array', {'type': 'entity:title', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'List of the titles/roles the person had at the event.'}),

                ('event', ('ou:attendable', {}), {
                    'prevnames': ('meet', 'conference', 'conference:event', 'contest', 'preso'),
                    'doc': 'The event that the person attended.'}),
            )),
            ('ou:preso', {}, (

                ('presenters', ('array', {'type': 'entity:individual', 'uniq': True, 'sorted': True}), {
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
            ('ou:meet', {}, ()),
            ('ou:conference', {}, (
                # FIXME remove?
                ('org', ('ou:org', {}), {
                    'doc': 'The org which created/managed the conference.'}),
            )),
            ('ou:event', {}, (
                # FIXME make type part of the interface template
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
