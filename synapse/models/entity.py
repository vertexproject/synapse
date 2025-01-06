import synapse.lib.module as s_module

class EntityModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('entity', {

            'interfaces': (
                ('entity:actor', {
                    'doc': 'Properties common to nodes with intent or initiative.',
                    'template': {'entity:actor': 'actor'},
                    # interfaces: geo:locatable?
                    'props': (

                        ('name', ('entity:name', {}), {
                            'doc': 'The name of the {entity:actor}.'}),

                        ('names', ('array', {'form': 'entity:name'}), {
                            'doc': 'An array of alternatative names for the {entity:actor}.'}),
                    ),
                }),
            ),

            'types': (

                ('entity:actor', ('ndef', {'interface': 'entity:actor'}), {
                    'doc': 'A node with intent or initiative.'}),

                ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A name used to refer to an entity.'}),

                ('entity:ownership', ('guid', {}), {
                    'doc': 'Property which is owned by an entity over a period of time.'}),
            ),

            'forms': (
                ('entity:name', {}, ()),

                ('entity:ownership', {}, (

                    ('owner', ('entity:actor', {}), {
                        'doc': 'The owner of the property.'}),

                    ('owner:name', ('entity:name', {}), {
                        'doc': 'The name of the owner of the property.'}),

                    ('property', ('ndef', {}), {
                        'doc': 'The property which is owned by the owner.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period where the owner owned the property.'}),

                    ('percent', ('hugenum', {}), {
                        'doc': 'The percent ownership which owner had over the property for the period.'}),
                )),
            ),
        }),)
