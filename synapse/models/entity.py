modeldefs = (
    ('entity', {

        'interfaces': (

            # FIXME phys:made? ( product :manufacturer :made=<time> etc
            # FIXME meta:sourced?

            ('entity:identifier', {
                'doc': 'An interface which is inherited by entity identifier forms.',
            }),

            ('entity:contactable', {

                'template': {'contactable': 'entity'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A type or source specific ID for the {contactable}.'}),

                    ('photo', ('file:bytes', {}), {
                        'doc': 'The profile picture or avatar for this {contactable}.'}),

                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {contactable}.'}),

                    ('names', ('array', {'type': 'meta:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the {contactable}.'}),

                    ('title', ('entity:title', {}), {
                        'doc': 'The title or role for this {contactable}.'}),

                    ('titles', ('array', {'type': 'entity:title', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate job titles or roles for this {contactable}.'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'An associated organization listed as part of the contact information.'}),

                    ('org:name', ('meta:name', {}), {
                        'doc': 'The name of an associated organization listed as part of the contact information.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The primary url for the {contactable}.'}),

                    ('lifespan', ('ival', {}), {
                        'doc': 'The lifespan of the {contactable}.'}),

                    # FIXME place of birth / death?
                    # FIXME lang
                    # FIXME bio / tagline

                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {contactable}.'}),

                    ('emails', ('array', {'type': 'inet:email', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate email addresses for the {contactable}.'}),

                    ('phone', ('tel:phone', {}), {
                        'doc': 'The primary phone number for the {contactable}.'}),

                    ('phones', ('array', {'type': 'tel:phone', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate telephone numbers for the {contactable}.'}),

                    ('user', ('inet:user', {}), {
                        'doc': 'The primary user name for the {contactable}.'}),

                    ('users', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate user names for the {contactable}.'}),

                    ('creds', ('array', {'type': 'auth:credential', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of non-ephemeral credentials.'}),

                    ('identifiers', ('array', {'type': 'entity:identifier', 'uniq': True, 'sorted': True}), {
                        'doc': 'Additional entity identifiers.'}),

                    ('social:accounts', ('array', {'type': 'inet:service:account', 'uniq': True, 'sorted': True}), {
                        'doc': 'Social media or other online accounts listed for the {contactable}.'}),

                    ('crypto:currency:addresses', ('array', {'type': 'crypto:currency:address'}), {
                        'doc': 'Crypto currency addresses listed for the {contactable}.'}),

                    ('websites', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                        'doc': 'Web sites listed for the {contactable}.'}),
                ),
                'doc': 'An interface for forms which contain contact info.'}),

            ('entity:actor', {
                'interfaces': (
                    ('geo:locatable', {}),
                    ('entity:contactable', {}),
                ),
                'doc': 'An interface for entities which have initiative to act.'}),

            ('entity:abstract', {
                'template': {'contactable': 'entity'},
                'props': (
                    ('resolved', ('entity:resolved', {}), {
                        'doc': 'The resolved entity to which this {contactable} belongs.'}),
                ),
                'doc': 'An abstract entity which can be resolved to an organization or person.'}),
        ),

        'types': (

            ('entity:contactable', ('ndef', {'interface': 'entity:contactable'}), {
                'doc': 'A node which implements the entity:contactable interface.'}),

            ('entity:resolved', ('ndef', {'forms': ('ou:org', 'ps:person')}), {
                'doc': 'A fully resolved entity such as a person or organization.'}),

            ('entity:individual', ('ndef', {'forms': ('ps:person', 'entity:contact', 'inet:service:account')}), {
                'doc': 'A singular entity such as a person.'}),

            ('entity:identifier', ('ndef', {'interface': 'entity:identifier'}), {
                'doc': 'A node which inherits the entity:identifier interface.'}),

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
                'interfaces': (

                    ('entity:abstract', {
                        'template': {'contactable': 'contact'}}),

                    ('entity:actor', {
                            'template': {'contactable': 'contact'}}),

                    ('meta:observable', {
                        'template': {'observable': 'contact'}}),
                ),

                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'email'}},
                    ),
                },

                'aliases': (

                    ('dob', {'target': 'lifespan*min',
                        'doc': 'The date of birth for the {contactable}.'}),

                    ('dod', {'target': 'lifespan*max',
                        'doc': 'The date of death for the {contactable}.'}),

                    ('founded', {'target': 'lifespan*max',
                        'doc': 'The founded time for the {contactable}.'}),

                    ('dissolved', {'target': 'lifespan*max',
                        'doc': 'The dissolved time for the {contactable}.'}),
                ),

                'doc': 'A set of contact information which is used by an entity.'}),

            ('entity:history', ('guid', {}), {
                'interfaces': (
                    ('entity:contactable', {}),
                ),
                'template': {'contactable': 'contact'},
                'doc': 'Historical contact information about another contact.'}),

            ('entity:relationship:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of entity relationship types.'}),

            ('entity:relationship', ('guid', {}), {
                'doc': 'A directional relationship between two actor entities.'}),

            ('entity:possession:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of types of possession.'}),

            ('entity:possession', ('guid', {}), {
                'doc': 'An item which is possessed by an entity.'}),

        ),

        'edges': (),

        'forms': (

            ('entity:title', {}, ()),

            ('entity:contact:type:taxonomy', {}, ()),
            ('entity:contact', {}, (

                # FIXME should this be part of the template?
                ('type', ('entity:contact:type:taxonomy', {}), {
                    'doc': 'The contact type.'}),

            )),

            ('entity:history', {}, (

                ('current', ('entity:contactable', {}), {
                    'doc': 'The current version of this historical contact.'}),
            )),
            # FIXME possession with an :ownership=<bool>?
            ('entity:possession:type:taxonomy', {}, ()),
            ('entity:possession', {}, (

                ('item', ('meta:havable', {}), {
                    'doc': 'The item owned by the entity.'}),

                ('actor', ('entity:actor', {}), {
                    'doc': 'The entity which possessed the item.'}),

                ('type', ('entity:possession:type:taxonomy', {}), {
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
        ),
    }),
)
