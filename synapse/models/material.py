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

            'interfaces': (

                ('phys:object', {
                    'doc': 'Properties common to all physical objects.',
                    'template': {'phys:object': 'object'},
                    'props': (

                        ('phys:mass', ('mass', {}), {
                            'doc': 'The mass of the {phys:object}.'}),

                        ('phys:volume', ('geo:dist', {}), {
                            'doc': 'The cubed volume of the {phys:object}.'}),

                        ('phys:length', ('geo:dist', {}), {
                            'doc': 'The length of the {phys:object}.'}),

                        ('phys:width', ('geo:dist', {}), {
                            'doc': 'The width of the {phys:object}.'}),

                        ('phys:height', ('geo:dist', {}), {
                            'doc': 'The height of the {phys:object}.'}),
                    ),
                }),
            ),

            'types': (

                ('phys:object', ('ndef', {'interface': 'phys:object'}), {
                    'doc': 'A node which represents a physical object.'}),

                ('phys:contained:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy for types of contained relationships.'}),

                ('phys:contained', ('guid', {}), {
                    'doc': 'A node which represents a physical object containing another physical object.'}),

                ('mat:item', ('guid', {}), {
                    'interfaces': ('phys:object', 'geo:locatable'),
                    'template': {'phys:object': 'item', 'geo:locatable': 'item'},
                    'doc': 'A GUID assigned to a material object.'}),

                ('mat:type', ('taxonomy', {}), {
                    'doc': 'A taxonomy of material item/specification types.',
                    'interfaces': ('meta:taxonomy',)}),

                ('mat:spec', ('guid', {}), {'doc': 'A GUID assigned to a material specification.'}),
                ('mat:specimage', ('comp', {'fields': (('spec', 'mat:spec'), ('file', 'file:bytes'))}), {}),
                ('mat:itemimage', ('comp', {'fields': (('item', 'mat:item'), ('file', 'file:bytes'))}), {}),

                ('mass', ('hugenum', {'units': massunits}), {
                    'doc': 'A mass which converts to grams as a base unit.'}),
            ),

            'forms': (

                ('phys:contained:type:taxonomy', {}, ()),
                ('phys:contained', {}, (

                    ('type', ('phys:contained:type:taxonomy', {}), {
                        'doc': 'The type of container relationship.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period where the container held the object.'}),

                    ('object', ('phys:object', {}), {
                        'doc': 'The object held within the container.'}),

                    ('container', ('phys:object', {}), {
                        'doc': 'The container which held the object.'}),
                )),
                ('mat:item', {}, (

                    ('name', ('str', {'lower': True}), {
                        'doc': 'The name of the material item.'}),

                    ('type', ('mat:type', {}), {
                        'doc': 'The taxonomy type of the item.'}),

                    ('spec', ('mat:spec', {}), {
                        'doc': 'The specification which defines this item.'}),

                    ('latlong', ('geo:latlong', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :place:latlong.'}),

                    ('loc', ('loc', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :place:loc.'}),
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
