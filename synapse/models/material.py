'''
A data model focused on material objects.
'''

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

volunits = {
    'ml': '1',
    'milliliter': '1',
    'milliliters': '1',

    'cl': '10',
    'centiliter': '10',
    'centiliters': '10',

    'dl': '100',
    'deciliter': '100',
    'deciliters': '100',

    'l': '1000',
    'liter': '1000',
    'liters': '1000',

    'kl': '1000000',
    'kiloliter': '1000000',
    'kiloliters': '1000000',

    # cubic metric units
    'mm^3': '0.001',
    'cm^3': '1',
    'cc': '1',
    'dm^3': '1000',
    'm^3': '1000000',

    # US customary liquid units
    'floz': '29.5735',
    'pint': '473.176',
    'pints': '473.176',
    'quart': '946.353',
    'quarts': '946.353',
    'gal': '3785.41',
    'gallon': '3785.41',
    'gallons': '3785.41',

    # cubic customary units
    'in^3': '16.3871',
    'ft^3': '28316.8',
    'yd^3': '764555',

    # petroleum barrel
    'bbl': '158987',
    'barrel': '158987',
    'barrels': '158987',
}

modeldefs = (
    {

        'interfaces': (

            ('phys:tangible', {
                'doc': 'Properties common to nodes which have or capture physical characteristics.',
                'template': {'title': 'object'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('phys:mass', ('phys:mass', {}), {
                        'doc': 'The physical mass of the {title}.'}),

                    ('phys:volume', ('phys:volume', {}), {
                        'doc': 'The physical volume of the {title}.'}),

                    ('phys:length', ('phys:distance', {}), {
                        'doc': 'The physical length of the {title}.'}),

                    ('phys:width', ('phys:distance', {}), {
                        'doc': 'The physical width of the {title}.'}),

                    ('phys:height', ('phys:distance', {}), {
                        'doc': 'The physical height of the {title}.'}),
                ),
            }),

            ('phys:object', {
                'doc': 'Properties common to physical objects.',
                'template': {'title': 'object'},
                'interfaces': (
                    ('meta:havable', {}),
                    ('phys:tangible', {}),
                    ('entity:destroyable', {}),
                ),
                'props': (
                    ('period', ('phys:lifespan', {}), {
                        'doc': 'The period when the {title} existed, from its creation until it was retired or destroyed.'}),
                ),
            }),
        ),

        'types': (
            ('phys:lifespan', ('ival', {'names': {'min': 'created', 'max': 'retired'}}), {
                'doc': 'An interval representing the lifespan of a physical object, from its creation until it is retired or destroyed.'}),

            ('mat:item:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of material object types.',
            }),

            ('mat:spec:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of material specification types.',
            }),

            ('phys:contained:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy for types of contained relationships.'}),

            ('phys:contained', ('guid', {}), {
                'props': (

                    ('type', ('phys:contained:type:taxonomy', {}), {
                        'doc': 'The type of container relationship.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period where the container held the object.'}),

                    ('object', ('phys:object', {}), {
                        'doc': 'The object held within the container.'}),

                    ('container', ('phys:object', {}), {
                        'doc': 'The container which held the object.'}),
                ),
                'doc': 'A relationship in which one physical object contains another.'}),

            ('mat:item', ('guid', {}), {
                'template': {'title': 'item'},
                'interfaces': (
                    ('phys:object', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the material item.'}),

                    ('type', ('mat:item:type:taxonomy', {}), {
                        'doc': 'The taxonomy type of the item.'}),

                    ('spec', ('mat:spec', {}), {
                        'doc': 'The specification which defines this item.'}),
                ),
                'doc': 'A GUID assigned to a material object.'}),

            ('mat:spec', ('guid', {}), {
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the material specification.'}),

                    ('type', ('mat:spec:type:taxonomy', {}), {
                        'doc': 'The taxonomy type for the specification.'}),
                ),
                'doc': 'A GUID assigned to a material specification.'}),

            ('phys:mass', ('hugenum', {'units': massunits}), {
                'doc': 'A mass which converts to grams as a base unit.'}),

            ('phys:volume', ('hugenum', {'units': volunits}), {
                'ex': '10 m^3',
                'doc': 'A volume which converts to milliliters as a base unit.'}),
        ),
    },
)
