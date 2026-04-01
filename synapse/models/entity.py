modeldefs = (
    ('entity', {

        'interfaces': (

            ('entity:identifier', {
                'doc': 'An interface which is inherited by entity identifier forms.'}),

            ('entity:action', {
                'template': {'title': 'action'},
                'doc': 'Properties which are common to actions taken by entities.',
                'props': (

                    ('actor', ('entity:actor', {}), {
                        'doc': 'The actor who carried out the {title}.'}),

                    ('actor:name', ('entity:name', {}), {
                        'doc': 'The name of the actor who carried out the {title}.'}),
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

            ('entity:supportable', {
                'doc': 'An interface implemented by activities which may be supported in by an actor.'}),

            ('entity:contactable', {

                'template': {'title': 'entity'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('id', ('meta:id', {}), {
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

                    ('names', ('array', {'type': 'entity:name'}), {
                        'doc': 'An array of alternate entity names for the {title}.'}),

                    ('lifespan', ('ival', {}), {
                        'virts': (

                            ('min', None, {
                                'doc': 'The date of birth for an individual or founded date for an organization.'}),

                            ('max', None, {
                                'doc': 'The date of death for an individual or dissolved date for an organization.'}),

                            ('duration', None, {
                                'doc': 'The duration of the lifespan of the individual or organziation.'}),
                        ),
                        'doc': 'The lifespan of the {title}.'}),

                    # FIXME place of birth / death?

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('lang', ('lang:language', {}), {
                        'doc': 'The primary language of the {title}.'}),

                    ('langs', ('array', {'type': 'lang:language'}), {
                        'doc': 'An array of alternate languages for the {title}.'}),

                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {title}.'}),

                    ('emails', ('array', {'type': 'inet:email'}), {
                        'doc': 'An array of alternate email addresses for the {title}.'}),

                    ('phone', ('tel:phone', {}), {
                        'alts': ('phones',),
                        'doc': 'The primary phone number for the {title}.'}),

                    ('phones', ('array', {'type': 'tel:phone'}), {
                        'doc': 'An array of alternate telephone numbers for the {title}.'}),

                    ('user', ('inet:user', {}), {
                        'alts': ('users',),
                        'doc': 'The primary user name for the {title}.'}),

                    ('users', ('array', {'type': 'inet:user'}), {
                        'doc': 'An array of alternate user names for the {title}.'}),

                    ('creds', ('array', {'type': 'auth:credential'}), {
                        'doc': 'An array of non-ephemeral credentials.'}),

                    ('identifiers', ('array', {'type': 'entity:identifier'}), {
                        'doc': 'Additional entity identifiers.'}),

                    ('social:accounts', ('array', {'type': 'inet:service:account'}), {
                        'doc': 'Social media or other online accounts listed for the {title}.'}),

                    ('crypto:currency:addresses', ('array', {'type': 'crypto:currency:address'}), {
                        'doc': 'Crypto currency addresses listed for the {title}.'}),

                    ('websites', ('array', {'type': 'inet:url'}), {
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

                    ('titles', ('array', {'type': 'entity:title'}), {
                        'doc': 'An array of alternate entity titles or roles for this {title}.'}),
                ),
                'doc': 'Properties which apply to entities which may represent a person.'}),

            ('entity:multiple', {
                'doc': 'Properties which apply to entities which may represent a group or organization.'}),

            ('entity:resolvable', {
                'template': {'title': 'entity'},
                'props': (
                    ('resolved', (('ou:org', 'ps:person'), {}), {
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

            ('entity:individual', ('poly', {'forms': ('ps:person', 'entity:contact', 'inet:service:account')}), {
                'doc': 'A singular entity such as a person.'}),

            ('entity:name', ('base:name', {}), {
                'doc': 'A name used to refer to an entity.'}),

            # FIXME syn:user is an actor...

            ('entity:title', ('str', {'onespace': True, 'lower': True}), {
                'interfaces': (
                    ('risk:targetable', {}),
                ),
                'prevnames': ('ou:jobtitle', 'ou:role'),
                'doc': 'A title or position name used by an entity.'}),

            ('entity:contact:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of entity contact types.'}),

            ('entity:contact', ('guid', {}), {
                'template': {'title': 'contact'},
                'interfaces': (
                    ('entity:actor', {}),
                    ('entity:singular', {}),
                    ('entity:multiple', {}),
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

                'doc': 'A set of contact information which is used by an entity.'}),

            ('entity:history', ('guid', {}), {
                'template': {'title': 'contact history'},
                'interfaces': (
                    ('entity:contactable', {}),
                ),
                'doc': 'Historical contact information about another contact.'}),

            ('entity:contactlist', ('guid', {}), {
                'doc': 'A list of contacts.'}),

            ('entity:relationship:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of entity relationship types.'}),

            ('entity:relationship:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of entity relationship statuses.'}),

            ('entity:relationship', ('guid', {}), {
                'template': {'title': 'relationship'},
                'interfaces': (
                    ('meta:reported', {}),
                ),
                'doc': 'A directional relationship between two actor entities.'}),

            ('entity:had:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of types of possession.'}),

            ('entity:had', ('guid', {}), {
                'doc': 'An item which was possessed by an actor.'}),

            ('entity:conversation', ('guid', {}), {
                'doc': 'A conversation between entities.'}),

            # FIXME entity:goal needs an interface ( for extensible goals without either/or props? )
            # FIXME entity:goal needs to clearly differentiate actor/action goals vs goal types
            # FIXME entity:goal should consider a backlink to entity:actor/entity:action SO specifics
            ('entity:goal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of goal types.'}),

            ('entity:goal:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of goal statuses.'}),

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
                'doc': 'A stated or assessed goal.'}),

            ('entity:campaign:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of campaign types.'}),

            ('entity:campaign:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of campaign statuses.'}),

            ('entity:campaign', ('guid', {}), {
                'template': {'title': 'campaign'},
                'interfaces': (
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
                'doc': 'Activity in pursuit of a goal.'}),

            ('entity:conflict', ('guid', {}), {
                'template': {'title': 'conflict'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'doc': 'Represents a conflict where two or more campaigns have mutually exclusive goals.'}),

            ('entity:contribution', ('guid', {}), {
                'template': {'title': 'contribution'},
                'interfaces': (
                    ('entity:action', {}),
                ),
                'doc': 'Represents a specific instance of contributing material support to a campaign.'}),

            ('entity:discovery', ('guid', {}), {
                'doc': 'A discovery made by an actor.'}),

            ('entity:studied', ('guid', {}), {
                'template': {'title': 'studied'},
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
                'template': {'title': 'achieved'},
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
                'template': {'title': 'believed'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (
                    ('belief', ('meta:believable', {}), {
                        'doc': 'The belief held by the actor.'}),
                ),
                'doc': 'A period where an actor held a belief.'}),

            ('entity:discovered', ('guid', {}), {
                'template': {'title': 'discovery'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('item', ('meta:discoverable', {}), {
                        'doc': 'The item discovered by the actor.'}),
                ),
                'doc': 'An event where an entity made a discovery.'}),

            ('entity:signed', ('guid', {}), {
                'template': {'title': 'signed'},
                'interfaces': (
                    ('entity:event', {}),
                ),
                'props': (
                    ('doc', ('doc:signable', {}), {
                        'doc': 'The document which the actor signed.'}),
                ),
                'doc': 'An event where an actor signed a document.'}),

            ('entity:asked', ('guid', {}), {
                'template': {'title': 'ask'},
                'interfaces': (
                    ('entity:stance', {}),
                ),
                'props': (),
                'doc': 'An event where an actor made an ask as part of a negotiation.'}),

            ('entity:offered', ('guid', {}), {
                'template': {'title': 'offer'},
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
                    ('activity', ('base:activity', {}), {
                        'doc': 'The activity attended by the actor.'}),

                    ('role', ('base:name', {}), {
                        'doc': 'The role the actor played in attending the activity.'}),
                ),
                'doc': 'A period where an actor attended an event or activity.'}),

            ('entity:supported', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('role', ('entity:title', {}), {
                        'ex': 'sponsor',
                        'doc': 'The role the actor played in supporting the event.'}),

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
                    ('activity', ('entity:participable', {}), {
                        'doc': 'The activity which the actor participated in.'}),

                    ('role', ('entity:title', {}), {
                        'ex': 'organizer',
                        'doc': 'The role which the actor played in the activity.'}),
                ),
                'doc': 'A period where an actor participated in an activity.'}),

            ('entity:said', ('guid', {}), {
                'template': {'title': 'statement'},
                'interfaces': (
                    ('entity:activity', {}),
                    ('meta:recordable', {}),
                ),
                'props': (
                    ('text', ('str', {}), {
                        'doc': 'The transcribed text of what the actor said.'}),
                ),
                'doc': 'A statement made by an actor.'}),

            ('entity:created', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    # this will eventually grow to include additional interfaces
                    ('item', ('doc:authorable', {}), {
                        'doc': 'The item which the actor created or helped to create.'}),

                    ('role', ('entity:title', {}), {
                        'ex': 'illustrator',
                        'doc': 'The role which the actor played in creating the item.'}),
                ),
                'doc': 'An activity where an actor created or helped create an item.'}),
        ),

        'edges': (
            (('entity:actor', 'had', 'entity:goal'), {
                'doc': 'The actor had the goal.'}),

            (('entity:actor', 'used', 'meta:usable'), {
                'doc': 'The actor used the target node.'}),

            (('entity:actor', 'used', 'meta:observable'), {
                'doc': 'The actor used the target node.'}),

            (('entity:contactlist', 'has', 'entity:contact'), {
                'doc': 'The contact list contains the contact.'}),

            (('entity:action', 'used', 'meta:usable'), {
                'doc': 'The action was taken using the target node.'}),

            (('entity:action', 'used', 'meta:observable'), {
                'doc': 'The action was taken using the target node.'}),

            (('entity:action', 'had', 'entity:goal'), {
                'doc': 'The action was taken in pursuit of the goal.'}),

            (('entity:contribution', 'had', 'econ:lineitem'), {
                'doc': 'The contribution includes the line item.'}),

            (('entity:contribution', 'had', 'econ:payment'), {
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

        'forms': (

            ('entity:title', {}, ()),

            ('entity:name', {}, ()),

            ('entity:contact:type:taxonomy', {}, ()),
            ('entity:contact', {}, (

                ('type', ('entity:contact:type:taxonomy', {}), {
                    'doc': 'The contact type.'}),

            )),

            ('entity:history', {}, (

                ('current', ('entity:contactable', {}), {
                    'doc': 'The current version of this historical contact.'}),
            )),

            ('entity:contactlist', {}, (

                ('name', ('base:name', {}), {
                    'doc': 'The name of the contact list.'}),

                ('source', (('it:host', 'inet:service:account', 'file:bytes'), {}), {
                    'doc': 'The source that the contact list was extracted from.'}),
            )),

            ('entity:had:type:taxonomy', {}, ()),
            ('entity:had', {}, (

                ('item', ('meta:havable', {}), {
                    'doc': 'The item owned by the entity.'}),

                ('actor', ('entity:actor', {}), {
                    'doc': 'The entity which possessed the item.'}),

                ('type', ('entity:had:type:taxonomy', {}), {
                    'doc': 'A taxonomy for different types of possession.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the entity had the item.'}),

                ('percent', ('hugenum', {}), {
                    'doc': 'The percentage of the item owned by the owner.'}),

                # TODO: add a purchase property to link back to a purchase event?

            )),
            ('entity:relationship:type:taxonomy', {}, ()),
            ('entity:relationship', {}, (

                ('type', ('entity:relationship:type:taxonomy', {}), {
                    'doc': 'The type of relationship.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the relationship existed.'}),

                ('source', ('entity:actor', {}), {
                    'doc': 'The source entity in the relationship.'}),

                ('target', ('entity:actor', {}), {
                    'doc': 'The target entity in the relationship.'}),
            )),

            ('entity:goal:type:taxonomy', {}, ()),
            ('entity:goal', {}, (

                ('name', ('base:name', {}), {
                    'alts': ('names',),
                    'doc': 'A terse name for the goal.'}),

                ('names', ('array', {'type': 'base:name'}), {
                    'doc': 'Alternative names for the goal.'}),

                ('type', ('entity:goal:type:taxonomy', {}), {
                    'doc': 'A type taxonomy entry for the goal.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the goal.'}),
            )),

            ('entity:campaign:type:taxonomy', {
                'prevnames': ('ou:camptype',)}, ()),

            ('entity:campaign', {}, (

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

                ('budget', ('econ:price', {}), {
                    'doc': 'The budget allocated to execute the campaign.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes that are associated with the campaign.'}),
            )),

            ('entity:conflict', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the conflict.'}),

                ('adversaries', ('array', {'type': 'entity:actor'}), {
                    'doc': 'The primary adversaries in conflict with one another.'}),
            )),
            ('entity:contribution', {}, (

                ('campaign', ('entity:campaign', {}), {
                    'doc': 'The campaign receiving the contribution.'}),

                # FIXME - :price / :price:currency ( and the interface )
                ('value', ('econ:price', {}), {
                    'doc': 'The assessed value of the contribution.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the contribution occurred.'}),
            )),

            ('entity:discovery', {}, (

                ('actor', ('entity:actor', {}), {
                    'doc': 'The actor who made the discovery.'}),

                ('time', ('time', {}), {
                    'doc': 'The time when the discovery was made.'}),

                ('item', ('meta:discoverable', {}), {
                    'doc': 'The item which was discovered.'}),
            )),

        ),
    }),
)
