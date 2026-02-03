modeldefs = (
    ('entity', {

        'interfaces': (

            ('entity:identifier', {
                'doc': 'An interface which is inherited by entity identifier forms.'}),

            ('entity:action', {
                'template': {'title': 'action'},
                'props': (
                    ('actor', ('entity:actor', {}), {
                        'doc': 'The actor who carried out the {title}.'}),

                    ('actor:name', ('entity:name', {}), {
                        'doc': 'The name of the actor who carried out the {title}.'}),

                    ('actor:roles', ('array', {'type': 'base:name'}), {
                        'doc': 'The roles of the actor in the {title}.'}),

                ),
                'doc': 'Properties common to actions taken by entities.'}),

            # ('entity:affected', {
            #     'template': {'affected': 'affected'},
            #     'props': (
            #         ('event', ('meta:causal', {}), {
            #             'doc': 'The event which affected the entity.'}),

            #         ('party', ('entity:actor', {}), {
            #             'doc': 'The entity who was {affected}.'}),

            #         ('party:name', ('entity:name', {}), {
            #             'doc': 'The name of the entity who was {affected}.'}),

            #         ('period', ('ival', {}), {
            #             'doc': 'The period over which the entity was {affected}.'}),
            #     ),
            #     'doc': 'Properties common to entities being affected by an event.'}),

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

                    ('url', ('inet:url', {}), {
                        'doc': 'The primary url for the {title}.'}),

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
                    # FIXME lang

                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {title}.'}),

                    ('emails', ('array', {'type': 'inet:email'}), {
                        'doc': 'An array of alternate email addresses for the {title}.'}),

                    ('phone', ('tel:phone', {}), {
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

            ('entity:abstract', {
                'template': {'title': 'entity'},
                'props': (
                    ('resolved', ('entity:resolved', {}), {
                        'doc': 'The resolved entity to which this {title} belongs.'}),
                ),
                'doc': 'An abstract entity which can be resolved to an organization or person.'}),
        ),

        'types': (

            ('entity:attendable', ('ndef', {'interface': 'entity:attendable'}), {
                'doc': 'An event where individuals may attend or participate.'}),

            ('entity:contactable', ('ndef', {'interface': 'entity:contactable'}), {
                'doc': 'A node which implements the entity:contactable interface.'}),

            ('entity:resolved', ('ndef', {'forms': ('ou:org', 'ps:person')}), {
                'doc': 'A fully resolved entity such as a person or organization.'}),

            ('entity:individual', ('ndef', {'forms': ('ps:person', 'entity:contact', 'inet:service:account')}), {
                'doc': 'A singular entity such as a person.'}),

            ('entity:identifier', ('ndef', {'interface': 'entity:identifier'}), {
                'doc': 'A node which inherits the entity:identifier interface.'}),

            #('entity:action', ('ndef', {'interface': 'entity:action'}), {
                #'doc': 'FIXME polyprop place holder'}),

            ('entity:name', ('base:name', {}), {
                'doc': 'A name used to refer to an entity.'}),

            # FIXME syn:user is an actor...
            ('entity:actor', ('ndef', {'interface': 'entity:actor'}), {
                'doc': 'An entity which has initiative to act.'}),

            ('entity:title', ('str', {'onespace': True, 'lower': True}), {
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
                    ('entity:abstract', {}),
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
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                    ),
                },
                'doc': 'A stated or assessed goal.'}),

            # ('entity:campaign:type:taxonomy', ('taxonomy', {}), {
            #     'interfaces': (
            #         ('meta:taxonomy', {}),
            #     ),
            #     'doc': 'A hierarchical taxonomy of campaign types.'}),

            # ('entity:campaign:status:taxonomy', ('taxonomy', {}), {
            #     'interfaces': (
            #         ('meta:taxonomy', {}),
            #     ),
            #     'doc': 'A hierarchical taxonomy of campaign statuses.'}),

            ('entity:campaign', ('meta:activity', {}), {
                'template': {'title': 'campaign'},
                'interfaces': (
                    ('meta:reported', {}),
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

            ('entity:conflict', ('meta:activity', {}), {
                'props': (
                     ('adversaries', ('array', {'type': 'entity:actor'}), {
                         'doc': 'The primary adversaries in conflict with one another.'}),
                ),
                'doc': 'Represents a conflict where two or more actors have mutually exclusive goals.'}),

            # TODO - belief:subscriber=<entity:activity>
            ('entity:event', ('meta:event', {}), {
                'interfaces': (
                    ('entity:action', {}),
                ),
                'doc': 'An event carried out by an actor.'}),

            ('entity:activity', ('meta:activity', {}), {
                'interfaces': (
                    ('entity:action', {}),
                ),
                'doc': 'Activity carried out by an actor.'}),


            ('entity:affected', ('meta:activity', {}), {
                'props': (
                    ('party', ('entity:actor', {}), {
                        'doc': 'The party which was affected.'}),

                    ('party:name', ('entity:name', {}), {
                        'doc': 'The name of the party which was affected.'}),
                ),
                'doc': 'An entity which was affected by events.'}),

            # entity:knew / entity:awareof?
            ('entity:observed', ('entity:affected', {}), {
                'props': (
                    ('event', ('meta:causal', {}), {
                        'doc': 'The event which was observed by the entity.'}),
                ),
                'doc': 'Passive observation of an event by an entity.'}),

            ('entity:involved', ('entity:activity', {}), {
                'props': (
                    ('event', ('meta:causal', {}), {
                        'doc': 'The event or activity the actor was involved in.'}),
                ),
                'doc': "Represents an actor's active involvement with an event."})

            ('entity:support', ('entity:involved', {}), {
                'template': {'title': 'support'},
                'doc': 'Represents an actor having materially supported an event.'}),
                
            #('entity:contribution:type:taxonomy', ('taxonomy', {}), {
                #'doc': 'A hierarchical taxonomy of contribution types.'}),

            ('entity:contribution', ('entity:support', {}), {
                'template': {'title': 'contribution'},
                'props': (
                    ('value', ('econ:price', {}), {
                        'doc': 'The total value of the actors contribution.'}),
                ),
                'doc': 'An actor providing support for an event or activity.'}),

            ('entity:participation', ('entity:involved', {}), {
                'template': {'title': 'participation'},
                'props': (
                    # TODO - :level=<meta:score>?
                ),
                'doc': 'An actor actively participating in an event or activity.'}),

            ('entity:discovered', ('entity:event', {}), {
                'templates': {'title': 'discovery'},
                'props': (
                    ('item', ('meta:discoverable', {}), {
                        'doc': 'The item which was discovered.'}),
                ),
                'doc': 'A discovery made by an actor.'}),

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

                ('source', ('ndef', {'forms': ('it:host', 'inet:service:account', 'file:bytes')}), {
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

                #('actors', ('array', {'type': 'entity:actor', 'split': ','}), {
                    #'doc': 'Actors who participated in the campaign.'}),

                ('success', ('bool', {}), {
                    'doc': 'Set to true if the campaign achieved its goals.'}),

                # TODO: should we create risk:campaign and define this there
                ('sophistication', ('meta:score', {}), {
                    'doc': 'The assessed sophistication of the campaign.'}),

                #('type', ('entity:campaign:type:taxonomy', {}), {
                    #'doc': 'A type taxonomy entry for the campaign.',
                    #'prevnames': ('camptype',)}),

                #('period', ('ival', {}), {
                    #'doc': 'The time interval when the entity was running the campaign.'}),

                # TODO: cost:budget cost:actual ?
                ('cost', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'props': {'time': 'period.min', 'currency': 'currency'}},
                    },
                    'doc': 'The actual cost of the campaign.'}),

                ('budget', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'props': {'time': 'period.min', 'currency': 'currency'}},
                    },
                    'doc': 'The budget allocated to execute the campaign.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency used to record econ:price properties.'}),

                #('team', ('ou:team', {}), {
                    #'doc': 'The org team responsible for carrying out the campaign.'}),

                # FIXME overfit?
                #('conflict', ('entity:conflict', {}), {
                    #'doc': 'The conflict in which this campaign is a primary participant.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes that are associated with the campaign.'}),
            )),

            # ('entity:conflict', {}, (

            #     ('name', ('meta:name', {}), {
            #         'doc': 'The name of the conflict.'}),

            #     ('period', ('ival', {}), {
            #         'doc': 'The period of time when the conflict was ongoing.'}),

            #     ('adversaries', ('array', {'type': 'entity:actor'}), {
            #         'doc': 'The primary adversaries in conflict with one another.'}),
            # )),

            # other terse entity nouns: subject, party, target
            # entity:affected
            #     :event=<event>
            #     :party=<entity:actor

            #   entity:observed
            #       :event=<event>
            #       :party=<entity:actor>


            # entity:activity
            #   :role=attacker

            #   entity:attended
            #       :period
            #       :actor=<entity:actor>
            #       :event=<entity:attendable>

            #   entity:registered
            #       :time
            #       :actor=<entity:actor>
            #       :event=<entity:attendable>

            #   entity:contributed
            #   entity:participated
            #       :actor=<entity:actor>
            #       :event=<entity:action>

            # ('entity:support', {}, (
            #     ('event', ('entity:action', {}), {
            #         'doc': 'The action which the actor {supported}.'}),
            # )),

            ('entity:contribution', ('entity:activity', {}), {
                'props': (

                    ('event', ('meta:causal', {}), {
                        'doc': 'The activity supported by the actor.'}),

                    ('value', ('econ:price', {}), {
                        'doc': 'The assessed value of the contribution.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used for the assessed value.'}),
                ),
                'doc': 'An instance of an entity contributing to an event.'}),

            # ('entity:participated', ('meta:activity', {}), {
            #     'props': (
            #         ('event', ('meta:causal', {}), {
            #             'doc': 'The event that the actor participated in.'}),
            #     ),
            #     'doc': 'An instance of an entity actively participating in an event.'}),

            ('entity:sponsored', ('entity:activity', {}), {
                'props': (
                    ('event', ('meta:sponsorable', {}), {
                        'doc': 'The event which was sponsored by the actor.'}),

                    ('value', ('econ:price', {}), {
                        'doc': 'The assessed value of the contribution.'}),
                ),
                'doc': 'An instance of an actor sponsoring an event.'}),

            ('entity:attended', ('entity:activity', {}), {
                'props': (
                    ('event', ('meta:attendable', {}), {
                        'doc': 'The event which the actor attended.'}),
                ),
                'doc': 'An intance of an entity attending an organized event.'}),

            ('entity:registered', ('entity:event', {}), {
                'props': (
                    ('event', ('meta:attendable', {}), {
                        'doc': 'The event which the actor registered attended.'}),
                ),
                'doc': 'An instance of an entity registering for an organized event.'}),

        ),
    }),
)
