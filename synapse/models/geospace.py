import struct

import synapse.exc as s_exc
import synapse.lib.gis as s_gis
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.syntax as s_syntax

units = {
    'mm': 1,
    'cm': 10,

    'm': 1000,
    'meters': 1000,

    'km': 1000000,
}


class Latitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 90 * 10**8

    def norm(self, valu):

        try:
            valu = float(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu, mesg='Invalid float format')

        if valu > 90.0 or valu < -90.0:
            raise s_exc.BadTypeValu(valu, mesg='Latitude may only be -90.0 to 90.0')

        return valu, {}

    def indx(self, norm):
        return ((norm * Latitude.SCALE) + Latitude.SPACE).to_bytes(5, 'big')

class Longitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 180 * 10**8

    def norm(self, valu):

        try:
            valu = float(valu)
        except Exception as e:
            raise s_exc.BadTypeValu(valu, mesg='Invalid float format')

        if valu > 180.0 or valu < -180.0:
            raise s_exc.BadTypeValu(valu, mesg='Longitude may only be -180.0 to 180.0')

        return valu, {}

    def indx(self, norm):
        return ((norm * Longitude.SCALE) + Longitude.SPACE).to_bytes(5, 'big')

class LatLong(s_types.Type):
    # FIXME nothing uses these props
    # FIXME should these be indexed as something other than a string?

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        valu = valu.strip().split(',')
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu, mesg='Valu must contain valid latitude,longitude')

        try:
            latv = self.modl.type('geo:latitude').norm(valu[0])[0]
            lonv = self.modl.type('geo:longitude').norm(valu[1])[0]
        except Exception as e:
            raise s_exc.BadTypeValu(valu, mesg=e)

        return (latv, lonv), {'subs': {'lat': latv, 'lon': lonv}}

    def indx(self, valu):
        # to unpack:
        # latv, lonv = struct.unpack('>qq', norm)
        # latv, lonv = latv / 10**8, lonv / 10**8
        return struct.pack('>qq', int(valu[0] * 10**8), int(valu[1] * 10**8))

    def repr(self, norm):
        return f'{norm[0]},{norm[1]}'

class GeoModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('geo', {

                'ctors': (
                    ('geo:latitude', 'synapse.models.geospace.Latitude', {}, {}),
                    ('geo:longitude', 'synapse.models.geospace.Longitude', {}, {}),

                    ('geo:latlong', 'synapse.models.geospace.LatLong', {}, {
                        'doc': 'A Lat/Long string specifying a point on Earth',
                        'ex': '-12.45,56.78'
                    }),

                ),
            }),
        )

'''
class DistType(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

    def _normPyInt(self, valu):
        return valu, {}

    def _normPyStr(self, text):
        valu, off = s_syntax.parse_float(text, 0)
        unit, off = s_syntax.nom(text, off, s_syntax.alphaset)

        mult = units.get(unit.lower())
        if mult is None:
            raise BadTypeValu(text, mesg='invalid/unknown dist unit: %s' % (unit,))

        return valu * mult, {}

class GeoModule(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('geo:alias', {'subof': 'str:lwr', 'regex': '^[0-9a-z]+$', 'doc': 'An alias for the place GUID', 'ex': 'foobar'}),
                ('geo:dist', {'ctor': 'synapse.models.geospace.Dist',
                    'doc': 'A geographic distance (base unit is mm)', 'ex': '10 km'}),
                ('geo:latitude', {'ctor': 'synapse.models.geospace.Latitude',}),
                ('geo:longitude', {'ctor': 'synapse.models.geospace.Longitude',}),
                ('geo:latlong', {'ctor': 'synapse.models.geospace.LatLong',
                    'doc': 'A Lat/Long string specifying a point on Earth'}),
                ('geo:nloc', {'subof': 'comp',
                    'fields': 'prop=syn:prop,ndef=ndef,latlong=geo:latlong,time=time',
                    'doc': 'Records a node latitude/longitude in space-time.'}),
                ('geo:place', {'subof': 'guid', 'alias': 'geo:place:alias', 'doc': 'A GUID for a specific place'}),
            ),

            'forms': (

                ('geo:place', {'ptype': 'geo:place'}, [
                    ('alias', {'ptype': 'geo:alias'}),
                    ('name', {'ptype': 'str', 'lower': 1, 'doc': 'The name of the place'}),
                    ('latlong', {'ptype': 'geo:latlong', 'defval': '??', 'doc': 'The location of the place'}),
                ]),

                ('geo:nloc', {}, [

                    ('prop', {'ptype': 'syn:prop', 'ro': 1, 'req': 1,
                        'doc': 'The latlong property name on the original node'}),

                    ('ndef', {'ptype': 'ndef', 'ro': 1, 'req': 1,
                        'doc': 'The node with location in geo/time'}),

                    ('latlong', {'ptype': 'geo:latlong', 'ro': 1, 'req': 1,
                        'doc': 'The latitude/longitude the node was observed'}),

                    ('time', {'ptype': 'time', 'ro': 1, 'req': 1,
                        'doc': 'The time the node was observed at location'}),

                ]),
            ),
        }
        name = 'geo'
        return ((name, modl), )
'''
