'''
A data model focused on material objects.
'''
import synapse.lib.module as s_module

massunits = {
    'µg': '0.000001',
    'microgram': '0.000001',
    'micrograms': '0.000001',

    'mg': '0.001',
    'milligram': '0.001',
    'milligrams': '0.001',

    'g': '1',
    'grams': '1',

    'kg': '1000',
    'kilogram': '1000',
    'kilograms': '1000',

    'lb': '453.592',
    'lbs': '453.592',
    'pound': '453.592',
    'pounds': '453.592',

    'stone': '6350.29',
}

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

                ('mass', ('hugenum', {'units': massunits}), {
                    'doc': 'A mass which converts to grams as a base unit.'}),
                # TODO add base type for volume
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
