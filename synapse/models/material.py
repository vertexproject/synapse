'''
A data model focused on material objects.
'''
import synapse.lib.module as s_module

class MatModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('mat:item', ('guid', {}), {'doc': 'A GUID assigned to a material object.'}),
                ('mat:type', ('taxonomy', {}), {
                    'doc': 'A taxonomy of material item/specification types.'}),
                ('mat:spec', ('guid', {}), {'doc': 'A GUID assigned to a material specification.'}),
                ('mat:specimage', ('comp', {'fields': (('spec', 'mat:spec'), ('file', 'file:bytes'))}), {}),
                ('mat:itemimage', ('comp', {'fields': (('item', 'mat:item'), ('file', 'file:bytes'))}), {}),
                # TODO add base types for mass / volume
            ),

            'forms': (

                ('mat:item', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'The name of the material item.'}),
                    ('type', ('mat:type', {}), {
                        'doc': 'The taxonomy type of the item.'}),
                    ('spec', ('mat:spec', {}), {
                        'doc': 'The specification which defines this item.'}),

                    ('place', ('geo:place', {}), {'doc': 'The most recent place the item is known to reside.'}),
                    ('latlong', ('geo:latlong', {}), {'doc': 'The last known lat/long location of the node.'}),

                    ('loc', ('loc', {}), {
                        'doc': 'The geo-political location string for the node.',
                    }),
                )),

                ('mat:spec', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'The name of the material specification.'}),
                    ('type', ('mat:type', {}), {
                        'doc': 'The taxonomy type for the specification.'}),
                )),

                ('mat:itemimage', {}, (
                    ('item', ('mat:item', {}), {'doc': 'The item contained within the image file.', 'ro': True, }),
                    ('file', ('file:bytes', {}), {'doc': 'The file containing an image of the item.', 'ro': True, }),
                )),

                ('mat:specimage', {}, (
                    ('spec', ('mat:spec', {}), {'doc': 'The spec contained within the image file.', 'ro': True, }),
                    ('file', ('file:bytes', {}), {'doc': 'The file containing an image of the spec.', 'ro': True, }),
                )),
            ),
        }
        name = 'mat'
        return ((name, modl), )
