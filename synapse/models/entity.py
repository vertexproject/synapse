import synapse.lib.module as s_module

class EntityModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('entity', {

            'types': (
                ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A name used to refer to an entity.'}),

                ('entity:actor', ('ndef', {'forms': ('ou:org', 'ps:person', 'ps:contact', 'risk:threat')}), {
                    'doc': 'An entity which has initiative to act.'}),

                ('entity:relationship:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy', ),
                    'doc': 'A hierarchical taxonomy of entity relationship types.'}),

                ('entity:relationship', ('guid', {}), {
                    'doc': 'A directional relationship between two actor entities.'}),
            ),

            'forms': (
                ('entity:name', {}, ()),

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
        }),)
