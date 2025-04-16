modeldefs = (
    ('entity', {

        'interfaces': (

            # FIXME phys:made? ( product :manufacturer :made=<time> etc
            # FIXME meta:sourced?
            # FIXME attendable? entity:attended?

            ('entity:havable', {
                'template': {'entity:havable': 'item'},
                'props': (
                    ('ownership', ('entity:ownership', {}), {
                        'doc': 'The most recently known ownership of the {entity:havable}.'}),
                ),
                'doc': 'An interface used to describe items that can be possessed by an entity.'}),

            ('entity:contactable', {

                'template': {'contactable': 'entity'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A type or source specific ID for the {contactable}.'}),

                    ('photo', ('file:bytes', {}), {
                        'doc': 'The profile picture or avatar for this {contactable}.'}),

                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {contactable}.'}),

                    ('names', ('array', {'type': 'entity:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the {contactable}.'}),

                    ('title', ('entity:title', {}), {
                        'doc': 'The title or role for this {contactable}.'}),

                    ('titles', ('array', {'type': 'entity:title', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate job titles or roles for this {contactable}.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The primary url for the {contactable}.'}),

                    # FIXME names?
                    ('lifespan', ('ival', {}), {
                        'doc': 'The lifespan of the {contactable}.'}),

                    # FIXME place of birth / death?
                    # FIXME org:name / employer etc?
                    # FIXME social media accounts
                    # FIXME lang
                    # FIXME id numbers ( reverse link! )
                    # FIXME bio / tagline

                    ('email', ('inet:email', {}), {
                        'doc': 'The primary email address for the {contactable}.'}),

                    ('emails', ('array', {'type': 'entity:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate email addresses for the {contactable}.'}),

                    ('phone', ('tel:phone', {}), {
                        'doc': 'The primary phone number for the {contactable}.'}),

                    ('phones', ('array', {'type': 'tel:phone', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate telephone numbers for the {contactable}.'}),

                    ('user', ('inet:user', {}), {
                        'doc': 'The primary user name for the {contactable}.'}),

                    ('users', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate user names for the {contactable}.'}),

                    # FIXME modify to it:adid having back linked props?
                    ('adid', ('it:adid', {}), {
                        'doc': 'The primary advertizing ID for the {contactable}.'}),

                    ('adids', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate user names for the {contactable}.'}),
                ),
                'doc': 'An interface for forms which contain contact info.'}),

            ('entity:actor', {
                'interfaces': (
                    ('geo:locatable', {}),
                    ('entity:contactable', {}),
                ),
                'doc': 'An interface for entities which have initiative to act.'}),

            ('entity:abstract', {
                'interfaces': (
                    ('entity:actor', {}),
                ),
                'props': (

                    # FIXME name? :isreally :owner?
                    ('resolved', ('entity:resolved', {}), {
                        'doc': 'The resolved entity to which this {contactable} belongs.'}),
                ),
                'doc': 'An abstract entity which can be resolved to an organization or person.'}),
        ),

        'types': (

            ('entity:contactable', ('ndef', {'interface': 'entity:contactable'}), {
                'doc': 'A node which implements the entity:contactable interrface..'}),

            ('entity:resolved', ('ndef', {'forms': ('ou:org', 'ps:person')}), {
                'doc': 'A fully resolved entity such as a person or organization.'}),

            ('entity:individual', ('ndef', {'forms': ('ps:person', 'entity:contact', 'inet:service:account')}), {
                'doc': 'A singular entity such as a person.'}),

            # FIXME syn:user is an actor...
            ('entity:actor', ('ndef', {'interface': 'entity:actor'}), {
                'doc': 'An entity which has initiative to act.'}),

            ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                'prevnames': ('ps:name', 'ou:name', 'ou:industryname',
                              'ou:campname', 'ou:goalname', 'lang:name',
                              'risk:vulnname', 'it:prod:softname'),
                'doc': 'A name used to refer to an entity.'}),

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
                        'interfaces': ('entity:contactable', {
                            'template': {'contactable': 'contact'}}),
                    }),
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
                        'doc': 'The date of birth for the {contactable}.'}),

                    ('founded', {'target': 'lifespan*max',
                        'doc': 'The founded time for the {contactable}.'}),

                    ('dissolved', {'target': 'lifespan*max',
                        'doc': 'The dissolved time for the {contactable}.'}),
                ),

                'doc': 'A group of contact information which is used by an entity.'}),

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
                'doc': 'A heirarhical taxonomy of entity relationship types.'}),

            ('entity:relationship', ('guid', {}), {
                'doc': 'A relationship between two entities.'}),

            ('entity:had:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A heirarchical taxonomy of types of possession.'}),

            ('entity:had', ('guid', {}), {
                'doc': 'A representation of possession of an item over time.'}),

            ('entity:havable', ('ndef', {'interface': 'entity:havable'}), {
                'doc': 'An item which may be possessed by an entity.'}),
        ),

        'edges': (),

        'forms': (

            ('entity:name', {}, ()),
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
            # FIXME posession with an :ownership=<bool>?
            ('entity:had:type:taxonomy', {}, ()),
            ('entity:had', {}, (
                # FIXME ou:org -> :had -> :item

                ('actor', ('entity:actor', {}), {
                    'doc': 'The entity which owns the item.'}),

                ('item', ('entity:havable', {}), {
                    'doc': 'The item owned by the entity.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the entity had the item.'}),

                ('percent', ('hugenum', {}), {
                    'doc': 'The percentage of the item owned by the owner.'}),

                # FIXME transaction / exchange event to allow theft or purchase?
                #('purchase', ('econ:purchase', {}), {
                    #'doc': 'The purchase event where the owner bought the item.'}),

                # FIXME shares:count / shares:total
            )),
            ('entity:relationship:type:taxonomy', {}, ()),
            ('entity:relationship', {}, (

                ('source', ('entity:actor', {}), {
                    'doc': 'The entity FIXME.'}),

                ('target', ('entity:actor', {}), {
                    'doc': 'The entity FIXME.'}),

                ('type', ('entity:relationship:type:taxonomy', {}), {
                    'doc': 'The type of relationship.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the relationship existed.'}),
            )),
        ),
    }),
)
