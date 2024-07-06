import synapse.lib.module as s_module

class EntityModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('entity', {

            'types': (
                ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A name used to refer to an entity.'}),
            ),

            'forms': (
                ('entity:name', {}, ()),
            ),
        }),)
