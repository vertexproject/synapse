geojsonschema = {

    'definitions': {

        'BoundingBox': {'type': 'array', 'minItems': 4, 'items': {'type': 'number'}},
        'PointCoordinates': {'type': 'array', 'minItems': 2, 'items': {'type': 'number'}},
        'LineStringCoordinates': {'type': 'array', 'minItems': 2, 'items': {'$ref': '#/definitions/PointCoordinates'}},
        'LinearRingCoordinates': {'type': 'array', 'minItems': 4, 'items': {'$ref': '#/definitions/PointCoordinates'}},
        'PolygonCoordinates': {'type': 'array', 'items': {'$ref': '#/definitions/LinearRingCoordinates'}},

        'Point': {
            'title': 'GeoJSON Point',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['Point']},
                'coordinates': {'$ref': '#/definitions/PointCoordinates'},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
         },

        'LineString': {
            'title': 'GeoJSON LineString',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['LineString']},
                'coordinates': {'$ref': '#/definitions/LineStringCoordinates'},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
         },

        'Polygon': {
            'title': 'GeoJSON Polygon',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['Polygon']},
                'coordinates': {'$ref': '#/definitions/PolygonCoordinates'},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },

        'MultiPoint': {
            'title': 'GeoJSON MultiPoint',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['MultiPoint']},
                'coordinates': {'type': 'array', 'items': {'$ref': '#/definitions/PointCoordinates'}},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },

        'MultiLineString': {
            'title': 'GeoJSON MultiLineString',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['MultiLineString']},
                'coordinates': {'type': 'array', 'items': {'$ref': '#/definitions/LineStringCoordinates'}},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
         },

        'MultiPolygon': {
            'title': 'GeoJSON MultiPolygon',
            'type': 'object',
            'required': ['type', 'coordinates'],
            'properties': {
                'type': {'type': 'string', 'enum': ['MultiPolygon']},
                'coordinates': {'type': 'array', 'items': {'$ref': '#/definitions/PolygonCoordinates'}},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },

        'GeometryCollection': {
            'title': 'GeoJSON GeometryCollection',
            'type': 'object',
            'required': ['type', 'geometries'],
            'properties': {
                'type': {'type': 'string', 'enum': ['GeometryCollection']},
                'geometries': {'type': 'array', 'items': {'oneOf': [
                    {'$ref': '#/definitions/Point'},
                    {'$ref': '#/definitions/LineString'},
                    {'$ref': '#/definitions/Polygon'},
                    {'$ref': '#/definitions/MultiPoint'},
                    {'$ref': '#/definitions/MultiLineString'},
                    {'$ref': '#/definitions/MultiPolygon'},
                ]}},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },

        'Feature': {
            'title': 'GeoJSON Feature',
            'type': 'object',
            'required': ['type', 'properties', 'geometry'],
            'properties': {
                'type': {'type': 'string', 'enum': ['Feature']},
                'geometry': {'oneOf': [
                    {'type': 'null'},
                    {'$ref': '#/definitions/Point'},
                    {'$ref': '#/definitions/LineString'},
                    {'$ref': '#/definitions/Polygon'},
                    {'$ref': '#/definitions/MultiPoint'},
                    {'$ref': '#/definitions/MultiLineString'},
                    {'$ref': '#/definitions/MultiPolygon'},
                    {'$ref': '#/definitions/GeometryCollection'},
                ]},
                'properties': {'oneOf': [{'type': 'null'}, {'type': 'object'}]},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },

        'FeatureCollection': {
            'title': 'GeoJSON FeatureCollection',
            'type': 'object',
            'required': ['type', 'features'],
            'properties': {
                'type': {'type': 'string', 'enum': ['FeatureCollection']},
                'features': {'type': 'array', 'items': {'$ref': '#/definitions/Feature'}},
                'bbox': {'$ref': '#/definitions/BoundingBox'},
            },
        },
    },

    'oneOf': [
        {'$ref': '#/definitions/Point'},
        {'$ref': '#/definitions/LineString'},
        {'$ref': '#/definitions/Polygon'},
        {'$ref': '#/definitions/MultiPoint'},
        {'$ref': '#/definitions/MultiLineString'},
        {'$ref': '#/definitions/MultiPolygon'},
        {'$ref': '#/definitions/GeometryCollection'},
        {'$ref': '#/definitions/Feature'},
        {'$ref': '#/definitions/FeatureCollection'},
    ],
}

modeldefs = (
    ('geo', {

        'ctors': (
            ('geo:dist', 'synapse.lib.types.Dist', {}, {
                'doc': 'A geographic distance (base unit is mm).', 'ex': '10 km'
            }),
            ('geo:area', 'synapse.lib.types.Area', {}, {
                'doc': 'A geographic area (base unit is square mm).', 'ex': '10 sq.km'
            }),
            ('geo:latlong', 'synapse.lib.types.LatLong', {}, {
                'doc': 'A Lat/Long string specifying a point on Earth.',
                'ex': '-12.45,56.78'
            }),
        ),

        'interfaces': (

            ('geo:locatable', {
                'doc': 'Properties common to items and events which may be geolocated.',
                'prefix': 'place',
                'template': {'title': 'item', 'happened': 'was located'},
                'props': (
                    ('', ('geo:place', {}), {
                        'doc': 'The place where the {title} {happened}.'}),

                    ('loc', ('loc', {}), {
                        'doc': 'The geopolitical location where the {title} {happened}.'}),

                    ('name', ('geo:name', {}), {
                        'doc': 'The name where the {title} {happened}.'}),

                    ('address', ('geo:address', {}), {
                        'doc': 'The postal address where the {title} {happened}.'}),

                    ('address:city', ('base:name', {}), {
                        'doc': 'The city where the {title} {happened}.'}),

                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The latlong where the {title} {happened}.'}),

                    ('latlong:accuracy', ('geo:dist', {}), {
                        'doc': 'The accuracy of the latlong where the {title} {happened}.'}),

                    ('altitude', ('geo:altitude', {}), {
                        'doc': 'The altitude where the {title} {happened}.'}),

                    ('altitude:accuracy', ('geo:dist', {}), {
                        'doc': 'The accuracy of the altitude where the {title} {happened}.'}),

                    ('country', ('pol:country', {}), {
                        'doc': 'The country where the {title} {happened}.'}),

                    ('country:code', ('iso:3166:alpha2', {}), {
                        'doc': 'The country code where the {title} {happened}.'}),

                    ('bbox', ('geo:bbox', {}), {
                        'doc': 'A bounding box which encompasses where the {title} {happened}.'}),

                    ('geojson', ('geo:json', {}), {
                        'doc': 'A GeoJSON representation of where the {title} {happened}.'}),
                ),
            }),
        ),

        'types': (

            ('geo:telem', ('guid', {}), {
                'interfaces': (
                    ('phys:object', {'template': {'title': 'object'}}),
                    ('geo:locatable', {'template': {'title': 'object'}}),
                ),
                'doc': 'The geospatial position and physical characteristics of a node at a given time.'}),

            ('geo:json', ('data', {'schema': geojsonschema}), {
                'doc': 'GeoJSON structured JSON data.'}),

            ('geo:name', ('base:name', {}), {
                'doc': 'An unstructured place name or address.'}),

            ('geo:place', ('guid', {}), {
                'template': {'title': 'place'},
                'interfaces': (
                    ('geo:locatable', {'prefix': ''}),
                ),
                'doc': 'A geographic place.'}),

            ('geo:place:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of place types.',
            }),

            ('geo:address', ('str', {'lower': True, 'onespace': True}), {
                'doc': 'A street/mailing address string.'}),

            ('geo:longitude', ('float', {'min': -180.0, 'max': 180.0,
                               'minisvalid': False, 'maxisvalid': True}), {
                'ex': '31.337',
                'doc': 'A longitude in floating point notation.'}),

            ('geo:latitude', ('float', {'min': -90.0, 'max': 90.0,
                              'minisvalid': True, 'maxisvalid': True}), {
                'ex': '31.337',
                'doc': 'A latitude in floating point notation.'}),

            ('geo:bbox', ('comp', {'sepr': ',', 'fields': (
                                        ('xmin', 'geo:longitude'),
                                        ('xmax', 'geo:longitude'),
                                        ('ymin', 'geo:latitude'),
                                        ('ymax', 'geo:latitude'))}), {
                'doc': 'A geospatial bounding box in (xmin, xmax, ymin, ymax) format.'}),

            ('geo:altitude', ('geo:dist', {'baseoff': 6371008800}), {
                'doc': "A negative or positive offset from Mean Sea Level (6,371.0088km from Earth's core)."}),
        ),

        'edges': (
            (('geo:place', 'contains', 'geo:place'), {
                'doc': 'The source place completely contains the target place.'}),
        ),

        'forms': (

            ('geo:name', {}, ()),

            ('geo:telem', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time that the telemetry measurements were taken.'}),

                ('desc', ('str', {}), {
                    'doc': 'A description of the telemetry sample.'}),

                ('node', ('ndef', {}), {
                    'doc': 'The node that was observed at the associated time and place.'}),
            )),

            ('geo:place:type:taxonomy', {
                'prevnames': ('geo:place:taxonomy',)}, ()),

            ('geo:place', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'A type specific identifier such as an airport ID.'}),

                ('type', ('geo:place:type:taxonomy', {}), {
                    'doc': 'The type of place.'}),

                ('name', ('geo:name', {}), {
                    'alts': ('names',),
                    'doc': 'The name of the place.'}),

                ('names', ('array', {'type': 'geo:name'}), {
                    'doc': 'An array of alternative place names.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the place.'}),

                ('photo', ('file:bytes', {}), {
                    'doc': 'The image file to use as the primary image of the place.'}),
            )),
        )
    }),
)
