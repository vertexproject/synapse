modeldefs = (
    ('entity', {

        'interfaces': (

            # FIXME phys:made? ( product :manufacturer :made=<time> etc
            # FIXME meta:sourced?
            # FIXME attendable? entity:attended?

            ('entity:contactable', {

                'doc': 'An interface for forms which contain contact info.',
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A type or source specific unique ID for the {contactable}.'}),

                    # FIXME
                    # ('type', ('entity:contact:type:taxonomy',
                    ('photo', ('file:bytes', {}), {
                        'doc': 'The primary photo or profile picture for this contact.'}),

                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {contactable}.'}),

                    ('names', ('array', {'type': 'entity:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the {contactable}.'}),

                    ('title', ('ou:jobtitle', {}), {
                        'doc': 'The primary job or role for this {contactable}.'}),

                    ('titles', ('array', {'type': 'ou:jobtitle', 'uniq': True, 'sorted': True}), {
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

                    ('adid', ('it:adid', {}), {
                        'doc': 'The primary advertizing ID for the {contactable}.'}),

                    ('adids', ('array', {'type': 'inet:user', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate user names for the {contactable}.'}),
                ),
            }),

            ('entity:actor', {
                'interfaces': ('entity:contactable', 'geo:locatable'),
                'doc': 'An interface for entities which have initiative to act.',
            }),

            ('entity:abstract', {
                'interfaces': ('entity:actor',),
                'doc': 'An abstract entity which can be resolved to an organization or person.',
                'props': (

                    # FIXME name? :isreally :owner?
                    ('resolved', ('entity:resolved', {}), {
                        'doc': 'The resolved entity to which this {contactable} belongs.'}),
                ),
            }),
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
                'prevnames': ('ps:name', 'ou:name'),
                'doc': 'A name used to refer to an entity.'}),

            ('entity:contact:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of entity contact types.'}),

            ('entity:contact', ('guid', {}), {
                'interfaces': ('entity:abstract',),
                'template': {'contactable': 'contact'},

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
                'interfaces': ('entity:contactable',),
                'template': {'contactable': 'contact'},
                'doc': 'Historical contact information about another contact.'}),
        ),

        'edges': (
            # FIXME like so?
            #(('entity:actor', 'had', 'entity:havable'), {
                #'doc': 'The source entity was in possession of the target node.'}),

            #(('entity:actor', 'owned', 'entity:havable'), {
                #'doc': 'The source entity owned the target node.'}),
        ),

        'forms': (

            ('entity:name', {}, ()),

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
        ),
    }),
)
