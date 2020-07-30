import synapse.exc as s_exc

import synapse.lib.gis as s_gis
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.grammar as s_grammar

units = {
    'mm': 1,
    'cm': 10,

    'm': 1000,
    'meters': 1000,

    'km': 1000000,
}

distrepr = (
    (1000000.0, 'km'),
    (1000.0, 'm'),
    (10.0, 'cm'),
)

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

class Dist(s_types.Int):

    def postTypeInit(self):
        s_types.Int.postTypeInit(self)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.baseoff = self.opts.get('baseoff', 0)

    def _normPyInt(self, valu):
        return valu, {}

    def _normPyStr(self, text):
        try:
            valu, off = s_grammar.parse_float(text, 0)
        except Exception:
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg='Dist requires a valid float and dist '
                                         'unit, no valid float found') from None

        unit, off = s_grammar.nom(text, off, s_grammar.alphaset)

        mult = units.get(unit.lower())
        if mult is None:
            raise s_exc.BadTypeValu(valu=text, name=self.name,
                                    mesg='invalid/unknown dist unit: %s' % (unit,))

        norm = int(valu * mult) + self.baseoff
        if norm < 0:
            mesg = 'A geo:dist may not be negative.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        return norm, {}

    def repr(self, norm):

        valu = norm - self.baseoff

        text = None

        absv = abs(valu)
        for base, unit in distrepr:
            if absv >= base:
                size = absv / base
                text = '%s %s' % (size, unit)
                break

        if text is None:
            text = '%d mm' % (absv,)

        if valu < 0:
            text = f'-{text}'

        return text

class LatLong(s_types.Type):

    stortype = s_layer.STOR_TYPE_LATLONG

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.setCmprCtor('near=', self._cmprNear)
        self.storlifts.update({
            'near=': self._storLiftNear,
        })

    def _normCmprValu(self, valu):
        latlong, dist = valu
        rlatlong = self.modl.type('geo:latlong').norm(latlong)[0]
        rdist = self.modl.type('geo:dist').norm(dist)[0]
        return rlatlong, rdist

    def _cmprNear(self, valu):
        latlong, dist = self._normCmprValu(valu)

        def cmpr(valu):
            if s_gis.haversine(valu, latlong) <= dist:
                return True
            return False
        return cmpr

    def _storLiftNear(self, cmpr, valu):
        latlong = self.norm(valu[0])[0]
        dist = self.modl.type('geo:dist').norm(valu[1])[0]
        return ((cmpr, (latlong, dist), self.stortype),)

    def _normPyStr(self, valu):
        valu = tuple(valu.strip().split(','))
        return self._normPyTuple(valu)

    def _normPyTuple(self, valu):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Valu must contain valid latitude,longitude')

        try:
            latv = self.modl.type('geo:latitude').norm(valu[0])[0]
            lonv = self.modl.type('geo:longitude').norm(valu[1])[0]
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=str(e)) from None

        return (latv, lonv), {'subs': {'lat': latv, 'lon': lonv}}

    def repr(self, norm):
        return f'{norm[0]},{norm[1]}'

class GeoModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('geo', {

                'ctors': (
                    ('geo:dist', 'synapse.models.geospace.Dist', {}, {
                        'doc': 'A geographic distance (base unit is mm).', 'ex': '10 km'
                    }),
                    ('geo:latlong', 'synapse.models.geospace.LatLong', {}, {
                        'doc': 'A Lat/Long string specifying a point on Earth.',
                        'ex': '-12.45,56.78'
                    }),
                ),

                'types': (

                    ('geo:nloc', ('comp', {'fields': (('ndef', 'ndef'), ('latlong', 'geo:latlong'), ('time', 'time'))}), {
                        'doc': 'Records a node latitude/longitude in space-time.'
                    }),

                    ('geo:json', ('data', {'schema': geojsonschema}), {
                        'doc': 'GeoJSON structured JSON data.',
                    }),

                    ('geo:place', ('guid', {}), {
                        'doc': 'A GUID for a geographic place.'}),

                    ('geo:address', ('str', {'lower': 1, 'onespace': 1, 'strip': True}), {
                        'doc': 'A street/mailing address string.',
                    }),
                    ('geo:longitude', ('float', {'min': -180.0, 'max': 180.0,
                                       'minisvalid': False, 'maxisvalid': True}), {}),
                    ('geo:latitude', ('float', {'min': -90.0, 'max': 90.0,
                                      'minisvalid': True, 'maxisvalid': True}), {}),

                    ('geo:bbox', ('comp', {'sepr': ',', 'fields': (
                                                ('xmin', 'geo:longitude'),
                                                ('xmax', 'geo:longitude'),
                                                ('ymin', 'geo:latitude'),
                                                ('ymax', 'geo:latitude'))}), {
                        'doc': 'A geospatial bounding box in (xmin, xmax, ymin, ymax) format.',
                    }),
                    ('geo:altitude', ('geo:dist', {'baseoff': 6371008800}), {
                        'doc': 'A negative or positive offset from Mean Sea Level (6,371.0088km from Earths core).'
                    }),
                ),

                'forms': (

                    ('geo:nloc', {}, (

                        ('ndef', ('ndef', {}), {'ro': True,
                            'doc': 'The node with location in geospace and time.'}),

                        ('ndef:form', ('str', {}), {'ro': True,
                            'doc': 'The form of node referenced by the ndef.'}),

                        ('latlong', ('geo:latlong', {}), {'ro': True,
                            'doc': 'The latitude/longitude the node was observed.'}),

                        ('time', ('time', {}), {'ro': True,
                            'doc': 'The time the node was observed at location.'}),

                        ('place', ('geo:place', {}), {
                            'doc': 'The place corresponding to the latlong property.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the node.'}),

                    )),

                    ('geo:place', {}, (

                        ('name', ('str', {'lower': 1, 'onespace': 1}), {
                            'doc': 'The name of the place.'}),

                        ('parent', ('geo:place', {}), {
                            'doc': 'A parent place, possibly from reverse geocoding.'}),

                        ('desc', ('str', {}), {
                            'doc': 'A long form description of the place.'}),

                        ('loc', ('loc', {}), {
                            'doc': 'The geo-political location string for the node.'}),

                        ('address', ('geo:address', {}), {
                            'doc': 'The street/mailing address for the place.'}),

                        ('geojson', ('geo:json', {}), {
                            'doc': 'A GeoJSON representation of the place.'}),

                        ('latlong', ('geo:latlong', {}), {
                            'doc': 'The lat/long position for the place.'}),

                        ('bbox', ('geo:bbox', {}), {
                            'doc': 'A bounding box which encompases the place.'}),

                        ('radius', ('geo:dist', {}), {
                            'doc': 'An approximate radius to use for bounding box calculation.'}),
                    )),
                )
            }),
        )
