modeldefs = (
    {

        'interfaces': (

            ('entity:identifier', {
                'doc': 'An interface which is implemented by entity identifier forms.'}),

            ('entity:action', {
                'template': {'title': 'action', 'verb': 'carried out'},
                'doc': 'Properties which are common to actions taken by entities.',
                'props': (

                    ('actor', ('entity:actor', {}), {
                        'doc': 'The actor who {verb} the {title}.'}),

                    ('actor:name', ('entity:name', {}), {
                        'doc': 'The name of the actor who {verb} the {title}.'}),
                ),
            }),

            ('entity:event', {
                'template': {'title': 'event'},
                'interfaces': (
                    ('base:event', {}),
                    ('entity:action', {}),
                ),
                'doc': 'Properties common to events carried out by an actor.'}),

            ('entity:activity', {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('base:activity', {}),
                    ('entity:action', {}),
                ),
                'doc': 'Properties common to activity carried out by an actor.'}),

            ('entity:participable', {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'doc': 'An interface implemented by activities which an actor may participate in.'}),

            ('entity:attendable', {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'doc': 'An interface implemented by activities which an actor may attend.'}),

            ('entity:supportable', {
                'doc': 'An interface implemented by activities which may be supported in by an actor.'}),

            ('entity:creatable', {
                'template': {'title': 'item'},
                'props': (
                    ('creator', ('entity:actor', {}), {
                        'doc': 'The primary actor which created the {title}.'}),

                    ('creator:name', ('entity:name', {}), {
                        'doc': 'The name of the primary actor which created the {title}.'}),
                ),
                'doc': 'An interface implemented by forms which represent things made or created by an actor.'}),

            ('entity:destroyable', {
                'doc': 'An interface implemented by forms which represent things which can be destroyed.'}),

            ('entity:contactable', {

                'template': {'title': 'entity'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'A type or source specific ID for the {title}.'}),

                    ('bio', ('text', {}), {
                        'doc': 'A tagline or bio provided for the {title}.'}),

                    ('photo', ('file:bytes', {}), {
                        'doc': 'The profile picture or avatar for this {title}.'}),

                    ('banner', ('file:bytes', {}), {
                        'doc': 'A banner or hero image used on the profile page.'}),

                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary entity name of the {title}.'}),

                    ('names', ('entity:name', {}), {
                        'array': {},
                        'doc': 'An array of alternate entity names for the {title}.'}),

                    ('lifespan', ('entity:lifespan', {}), {
                        'virts': (

                            ('began', None, {
                                'doc': 'The date of birth for an individual or founded date for an organization.'}),

                            ('ended', None, {
                                'doc': 'The date of death for an individual or dissolved date for an organization.'}),

                            ('duration', None, {
                                'doc': 'The duration of the lifespan of the individual or organziation.'}),
                        ),
                        'doc': 'The lifespan of the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('lang', ('lang:language', {}), {
                        'doc': 'The primary language of the {title}.'}),

                    ('langs', ('lang:language', {}), {
                        'array': {},
                        'doc': 'An array of alternate languages for the {title}.'}),

                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {title}.'}),

                    ('emails', ('inet:email', {}), {
                        'array': {},
                        'doc': 'An array of alternate email addresses for the {title}.'}),

                    ('phone', ('tel:phone', {}), {
                        'alts': ('phones',),
                        'doc': 'The primary phone number for the {title}.'}),

                    ('phones', ('tel:phone', {}), {
                        'array': {},
                        'doc': 'An array of alternate telephone numbers for the {title}.'}),

                    ('username', ('entity:name', {}), {
                        'alts': ('usernames',),
                        'doc': 'The primary user name for the {title}.'}),

                    ('usernames', ('entity:name', {}), {
                        'array': {},
                        'doc': 'An array of alternate user names for the {title}.'}),

                    ('creds', ('auth:credential', {}), {
                        'array': {},
                        'doc': 'An array of non-ephemeral credentials.'}),

                    ('identifiers', ('entity:identifier', {}), {
                        'array': {},
                        'doc': 'Additional entity identifiers.'}),

                    ('social:accounts', ('inet:service:account', {}), {
                        'array': {},
                        'doc': 'Social media or other online accounts listed for the {title}.'}),

                    ('crypto:currency:addresses', ('crypto:currency:address', {}), {
                        'array': {},
                        'doc': 'Crypto currency addresses listed for the {title}.'}),

                    ('websites', ('inet:url', {}), {
                        'array': {},
                        'doc': 'Web sites listed for the {title}.'}),
                ),
                'doc': 'An interface for forms which contain contact info.'}),

            ('entity:actor', {
                'doc': 'An interface for entities which have initiative to act.'}),

            ('entity:singular', {
                'interfaces': (
                    ('geo:locatable', {'prefix': 'birth:place', 'template': {'happened': 'was born'}}),
                    ('geo:locatable', {'prefix': 'death:place', 'template': {'happened': 'died'}}),
                ),
                'props': (
                    ('org', ('ou:org', {}), {
                        'doc': 'An associated organization listed as part of the contact information.'}),

                    ('org:name', ('entity:name', {}), {
                        'doc': 'The name of an associated organization listed as part of the contact information.'}),

                    ('title', ('entity:title', {}), {
                        'doc': 'The entity title or role for this {title}.'}),

                    ('titles', ('entity:title', {}), {
                        'array': {},
                        'doc': 'An array of alternate entity titles or roles for this {title}.'}),
                ),
                'doc': 'Properties which apply to entities which may represent a person.'}),

            ('entity:multiple', {
                'doc': 'Properties which apply to entities which may represent a group or organization.'}),

            ('entity:resolvable', {
                'template': {'title': 'entity'},
                'props': (
                    ('resolved', (
                            ('ou:org', {}),
                            ('ps:person', {})
                        ), {
                        'doc': 'The resolved entity to which this {title} belongs.'}),
                ),
                'doc': 'An abstract entity which can be resolved to an organization or person.'}),

            ('entity:stance', {
                'template': {'title': 'stance'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (

                    ('value', ('econ:price', {}), {
                        'doc': 'The value of the {title}.'}),

                    ('expires', ('time', {}), {
                        'doc': 'The time that the {title} expires.'}),

                    ('activity', ('meta:negotiable', {}), {
                        'doc': 'The negotiation activity this {title} was part of.'}),
                ),
                'doc': 'An interface for asks/offers in a negotiation.'}),
        ),

        'types': (

            ('entity:lifespan', ('ival', {'names': {'min': 'began', 'max': 'ended'}}), {
                'doc': 'An interval representing the lifespan of an entity, from when it began until it ended.'}),

            ('entity:individual', (
                    ('ps:person', {}),
                    ('entity:contact', {}),
                    ('inet:service:account', {})
                ), {
                'doc': 'A singular entity such as a person.'}),

            ('entity:name', ('base:name', {}), {
                'modes': {
                    'lookup': [
                        {'cmpr': '^='}
                    ]
                },
                'props': (),
                'doc': 'A name used to refer to an entity.'}),

            ('entity:title', ('title', {}), {
                'interfaces': (
                    ('risk:targetable', {}),
                ),
                'prevnames': ('ou:jobtitle', 'ou:role'),
                'props': (),
                'doc': 'A title or position name used by an entity.'}),

            ('entity:contact:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of entity contact types.'}),

            ('entity:contact', ('guid', {}), {
                'template': {'title': 'contact'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:singular', {}),
                    ('entity:multiple', {}),
                    ('risk:targetable', {}),
                    ('entity:resolvable', {}),
                    ('entity:contactable', {}),
                    ('meta:observable', {}),
                ),

                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'email'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },

                'props': (

                    ('type', ('entity:contact:type:taxonomy', {}), {
                        'doc': 'The contact type.'}),

                ),
                'doc': 'A set of contact information which is used by an entity.'}),

            ('entity:history', ('guid', {}), {
                'template': {'title': 'contact history'},
                'interfaces': (
                    ('entity:contactable', {}),
                ),
                'props': (

                    ('current', ('entity:contactable', {}), {
                        'doc': 'The current version of this historical contact.'}),
                ),
                'doc': 'Historical contact information about another contact.'}),

            ('entity:contactlist', ('guid', {}), {
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the contact list.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the contact list.'}),

                    ('source', (
                            ('it:host', {}),
                            ('inet:service:account', {}),
                            ('file:bytes', {})
                        ), {
                        'doc': 'The source that the contact list was extracted from.'}),
                ),
                'doc': 'A list of contacts.'}),

            ('entity:contactlist:entry', ('guid', {}), {
                'props': (
                    ('list', ('entity:contactlist', {}), {
                        'doc': 'The contact list which contains the entry.'}),

                    ('contact', ('entity:contact', {}), {
                        'doc': 'The contact which was included in the list.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The time period when the contact was included in the list.'}),
                ),
                'doc': 'An entry in a contact list.'}),

            ('entity:relationship:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of entity relationship types.'}),

            ('entity:relationship', ('guid', {}), {
                'template': {'title': 'relationship'},
                'interfaces': (
                    ('meta:reported', {}),
                ),
                'props': (

                    ('type', ('entity:relationship:type:taxonomy', {}), {
                        'doc': 'The type of relationship.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The time period when the relationship existed.'}),

                    ('source', ('entity:actor', {}), {
                        'doc': 'The source entity in the relationship.'}),

                    ('target', ('entity:actor', {}), {
                        'doc': 'The target entity in the relationship.'}),
                ),
                'doc': 'A directional relationship between two actor entities.'}),

            ('entity:had:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of types of possession.'}),

            ('entity:had', ('guid', {}), {
                'template': {'title': 'possession'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('actor', ('entity:actor', {}), {
                        'doc': 'The entity which had the item.'}),

                    ('actor:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which had the item.'}),

                    ('period', None, {
                        'doc': 'The time period when the entity had the item.'}),

                    ('item', ('meta:havable', {}), {
                        'doc': 'The item possessed by the entity.'}),

                    ('type', ('entity:had:type:taxonomy', {}), {
                        'doc': 'A taxonomy for different types of possession.'}),

                    # TODO: add a purchase property to link back to a purchase event?

                ),
                'doc': 'An item which was possessed by an actor.'}),

            ('entity:owned', ('entity:had', {}), {
                'template': {'title': 'ownership'},
                'props': (

                    ('actor', None, {
                        'doc': 'The entity which owned the item.'}),

                    ('actor:name', None, {
                        'doc': 'The name of the entity which owned the item.'}),

                    ('percent', ('percent', {}), {
                        'doc': 'The percentage of the item owned by the owner.'}),

                ),
                'doc': 'An item which was owned by an actor.'}),

            ('entity:conversation', ('guid', {}), {
                'doc': 'A conversation between entities.'}),

            ('entity:goal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of goal types.'}),

            ('entity:goal', ('guid', {}), {
                'template': {'title': 'goal'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('meta:achievable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                    ),
                },
                'props': (

                    ('name', ('base:name', {}), {
                        'alts': ('names',),
                        'doc': 'A terse name for the goal.'}),

                    ('names', ('base:name', {}), {
                        'array': {},
                        'doc': 'Alternative names for the goal.'}),

                    ('type', ('entity:goal:type:taxonomy', {}), {
                        'doc': 'A type taxonomy entry for the goal.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the goal.'}),
                ),
                'doc': 'A stated or assessed goal.'}),

            ('entity:motive', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (
                    ('goal', ('entity:goal', {}), {
                        'doc': 'The goal which motivated the actor.'}),
                ),
                'doc': 'A goal held by an actor for a period of time.'}),

            ('entity:campaign:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('ou:camptype',),
                'props': (),
                'doc': 'A hierarchical taxonomy of campaign types.'}),

            ('entity:campaign', ('guid', {}), {
                'template': {'title': 'campaign'},
                'interfaces': (
                    ('econ:budgetable', {}),
                    ('entity:activity', {}),
                    ('meta:reported', {}),
                    ('meta:observable', {}),
                    ('entity:supportable', {}),
                    ('entity:participable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'names'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                        {'type': 'prop', 'opts': {'name': 'period'}},
                    ),
                },
                'props': (

                    ('id', (
                        ('it:mitre:attack:campaign:id', {}),
                        ('base:id', {}),
                    ), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the campaign.'}),

                    ('ids', (('it:mitre:attack:campaign:id', {}), ('base:id', {})), {
                        'array': {},
                        'doc': 'An array of alternate IDs given to the campaign.'}),

                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {title}.'}),

                    ('names', ('entity:name', {}), {
                        'array': {},
                        'doc': 'A list of alternate names for the {title}.'}),

                    ('slogan', ('lang:phrase', {}), {
                        'doc': 'The slogan used by the campaign.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Set to true if the campaign achieved its goals.'}),

                    ('sophistication', ('meta:score', {}), {
                        'doc': 'The assessed sophistication of the campaign.'}),

                    ('type', ('entity:campaign:type:taxonomy', {}), {
                        'doc': 'A type taxonomy entry for the campaign.',
                        'prevnames': ('camptype',)}),

                    ('cost', ('econ:price', {}), {
                        'doc': 'The actual cost of the campaign.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are associated with the campaign.'}),
                ),
                'doc': 'Activity in pursuit of a goal.'}),

            ('entity:conflict', ('guid', {}), {
                'template': {'title': 'conflict'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'props': (

                    ('name', ('event:name', {}), {
                        'doc': 'The name of the conflict.'}),

                    ('adversaries', ('entity:actor', {}), {
                        'array': {},
                        'doc': 'The primary adversaries in conflict with one another.'}),
                ),
                'doc': 'Represents a conflict where two or more campaigns have mutually exclusive goals.'}),

            ('entity:contributed', ('guid', {}), {
                'template': {'title': 'contribution', 'verb': 'made'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (

                    ('campaign', ('entity:campaign', {}), {
                        'doc': 'The campaign receiving the contribution.'}),

                    ('value', ('econ:price', {}), {
                        'doc': 'The assessed value of the contribution.'}),
                ),
                'doc': 'Represents a specific instance of contributing material support to a campaign.'}),

            ('entity:studied', ('guid', {}), {
                'template': {'title': 'study', 'verb': 'undertook'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'institution::name'}},
                        # TODO allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period.min'}},
                        # {'type': 'prop', 'opts': {'name': 'period.max'}},
                    ),
                },
                'props': (
                    ('institution', ('ou:org', {}), {
                        'doc': 'The organization providing educational services.'}),
                ),
                'doc': 'A period when an actor studied or was educated.'}),

            ('entity:achieved', ('guid', {}), {
                'template': {'title': 'achievement', 'verb': 'earned'},
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'achievement::name'}},
                        {'type': 'prop', 'opts': {'name': 'achievement::org::name'}},
                        {'type': 'prop', 'opts': {'name': 'time'}},
                    ),
                },
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('achievement', ('meta:achievable', {}), {
                        'doc': 'The achievement that the actor reached.'}),
                ),
                'doc': 'An event where an actor achieved a goal or was given an award.'}),

            ('entity:believed', ('guid', {}), {
                'template': {'title': 'belief', 'activity': 'was held', 'verb': 'held'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (
                    ('belief', ('meta:believable', {}), {
                        'doc': 'The belief held by the actor.'}),
                ),
                'doc': 'A period where an actor held a belief.'}),

            ('entity:discovered', ('guid', {}), {
                'template': {'title': 'discovery', 'verb': 'made'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('item', ('meta:discoverable', {}), {
                        'doc': 'The item discovered by the actor.'}),
                ),
                'doc': 'An event where an entity made a discovery.'}),

            ('entity:destroyed', ('guid', {}), {
                'template': {'title': 'destruction'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('item', ('entity:destroyable', {}), {
                        'doc': 'The item destroyed by the actor.'}),
                ),
                'doc': 'An event where an actor destroyed an item.'}),

            ('entity:signed', ('guid', {}), {
                'template': {'title': 'signing'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('doc', ('doc:signable', {}), {
                        'doc': 'The document which the actor signed.'}),
                ),
                'doc': 'An event where an actor signed a document.'}),

            ('entity:asked', ('guid', {}), {
                'template': {'title': 'ask', 'verb': 'made'},
                'interfaces': (
                    ('entity:stance', {}),
                ),
                'props': (),
                'doc': 'An event where an actor made an ask as part of a negotiation.'}),

            ('entity:offered', ('guid', {}), {
                'template': {'title': 'offer', 'verb': 'made'},
                'interfaces': (
                    ('entity:stance', {}),
                ),
                'props': (),
                'doc': 'An event where an actor made an offer as part of a negotiation.'}),

            ('entity:attended', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (
                    ('activity', ('entity:attendable', {}), {
                        'doc': 'The activity attended by the actor.'}),

                    ('role', ('entity:title', {}), {
                        'doc': 'The role the actor played in attending the activity.'}),

                    ('inperson', ('bool', {}), {
                        'doc': 'Set if the actor attended the activity in person.'}),
                ),
                'doc': 'A period where an actor attended an event or activity.'}),

            ('entity:supported', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('role', ('entity:title', {}), {
                        'ex': 'sponsor',
                        'doc': 'The role the actor played in supporting the activity.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the actors support of the activity.'}),

                    ('activity', ('entity:supportable', {}), {
                        'doc': 'The activity which the actor supported.'}),

                    ('value', ('econ:price', {}), {
                        'doc': 'The financial value of the support given by the actor.'}),
                ),
                'doc': 'A period where an actor supported, sponsored, or materially contributed to an activity or cause.'}),

            ('entity:registered', ('guid', {}), {
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (

                    ('activity', ('entity:participable', {}), {
                        'doc': 'The activity which the actor registered for.'}),

                    ('role', ('entity:title', {}), {
                        'ex': 'attendee',
                        'doc': 'The role which the actor registered for.'}),

                    # TODO: this could eventually include non-inet registration like postal mail...
                    ('request', ('inet:proto:request', {}), {
                        'doc': 'The request which the actor sent in order to register.'}),
                ),
                'doc': 'An event where an actor registered for an event or activity.'}),

            ('entity:participated', ('guid', {}), {
                'template': {'title': 'participation'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (
                    ('actor', None, {
                        'doc': 'The actor who participated in the activity.'}),

                    ('actor:name', None, {
                        'doc': 'The name of the actor who participated in the activity.'}),

                    ('activity', ('entity:participable', {}), {
                        'doc': 'The activity which the actor participated in.'}),

                    ('role', ('entity:title', {}), {
                        'ex': 'organizer',
                        'doc': 'The role which the actor played in the activity.'}),
                ),
                'doc': 'A period where an actor participated in an activity.'}),

            ('entity:said', ('guid', {}), {
                'template': {'title': 'statement', 'verb': 'made'},
                'interfaces': (
                    ('entity:activity', {}),
                    ('meta:recordable', {}),
                ),
                'props': (
                    ('text', ('text', {}), {
                        'doc': 'The transcribed text of what the actor said.'}),
                ),
                'doc': 'A statement made by an actor.'}),

            ('entity:created', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    # this will eventually grow to include additional interfaces
                    ('item', ('entity:creatable', {}), {
                        'doc': 'The item which the actor helped to create.'}),

                    ('role', ('entity:title', {}), {
                        'ex': 'illustrator',
                        'doc': 'The role which the actor played in creating the item.'}),
                ),
                'doc': 'An activity where an actor helped to create an item.'}),

            ('entity:proficiency', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'skill::name'}},
                    ),
                },
                'props': (
                    ('level', ('meta:score', {}), {
                        'doc': 'The level of proficiency.'}),

                    ('skill', ('edu:learnable', {}), {
                        'doc': 'The topic or skill in which the contact is proficient.'}),
                ),
                'doc': 'A period of time where an actor had proficiency with a skill.'}),
        ),

        'edges': (

            (('entity:actor', 'used', 'meta:usable'), {
                'doc': 'The actor used the target node.'}),

            (('entity:contactlist', 'has', 'entity:contact'), {
                'doc': 'The contact list contains the contact.'}),

            (('entity:action', 'used', 'meta:usable'), {
                'doc': 'The action was taken using the target node.'}),

            (('entity:activity', 'supported', 'entity:goal'), {
                'doc': 'The activity supported the goal.'}),

            (('entity:contributed', 'had', 'econ:lineitem'), {
                'doc': 'The contribution includes the line item.'}),

            (('entity:contributed', 'had', 'econ:payment'), {
                'doc': 'The contribution includes the payment.'}),

            (('entity:studied', 'included', 'edu:class'), {
                'doc': 'The class was taken by the student as part of their studies.'}),

            (('entity:studied', 'included', 'edu:learnable'), {
                'doc': 'The target node was included by the actor as part of their studies.'}),

            (('entity:believed', 'followed', 'belief:tenet'), {
                'doc': 'The actor followed the tenet during the period.'}),

            (('entity:campaign', 'ledto', 'econ:purchase'), {
                'doc': 'The campaign led to the purchase.'}),
        ),
    },
)
