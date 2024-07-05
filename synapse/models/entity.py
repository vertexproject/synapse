import synapse.lib.module as s_module

class EntityModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('entity', {

            'types': (

                # TODO eventually migrate ps:name / ou:name / it:prod:softname / etc
                ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A name used to refer to an entity.'}),

                ('entity:contact:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of contact types.'}),

                ('entity:contact', ('guid', {}), {
                    'doc': 'A grouping of contact info associated with an entity.'})

                ('entity:identity', ('ndef', {'interfaces': ('entity:contact:info',)}), {
                    'doc': 'A reference to various entity types.'}),

                # FIXME this will replace most uses of :contact=<ps:contact>
                ('entity:actor', ('ndef', {'forms': ('ou:org', 'risk:threat', 'ps:person', 'ps:contact')}), {
                    'doc': 'A subset of entities which have intent.'}),

                ('entity:affiliation:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of affiliation types.'}),

                ('entity:affiliation', ('guid', {}), {
                    'interfaces': ('entity:contact:info',),
                    'doc': 'A non-directional relationship between multiple entities.'}),

                ('entity:relationship:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of relationship types.'}),

                ('entity:relationship', ('guid', {}), {
                    'doc': 'A directional relationship between 2 entities.'}),

            ),

            # FIXME can we currently declare edges based on interfaces?
            'edges': (

                # FIXME maybe entity has/owns should be a form?
                (('entity:contact:info', 'has', None), {
                    'doc': 'The entity is or was in posession of the target node.'}),

                (('entity:contact:info', 'owns', None), {
                    'doc': 'The entity owns or owned the target node.'}),
            ),

            'interfaces': (
                ('entity:contact:info', {
                    'doc': '',
                    'interfaces': ('geo:placed',),
                    'props': (

                        ('name', ('entity:name', {}), {
                            #FIXME allow docs to swap in form names?
                            'doc': 'The primary name of the {form}.'}),

                        ('names', ('array', {'type': 'entity:name', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of alternate names for the {form}.'}),

                        ('email', ('inet:email', {}), {
                            'doc': 'The primary email address associated with the {form}.'}),

                        ('emails', ('array', {'type': 'entity:name', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of alternate email addresses assciated with the {form}.'}),

                        ('type', ('entity:contact:type:taxonomy', {}), {
                            'doc': 'The type of entity.'}),

                        ('photo', ('file:bytes', {}), {
                            'doc': 'The primary image of the {form}.'}),

                        ('url', ('inet:url', {}), {
                            'doc': 'The primary URL assocated with the {form}.'}),
                    ),
                }),
            ),

            'forms': (
                ('entity:name', {}, ()),

                ('entity:contact:type:taxonomy', {}, ()),
                ('entity:contact', {}, (

                    ('name', ('entity:name', {}), {
                        'doc': 'The name of the entity.'}),

                    #
                )),
            ),
        }),)
