import os

import synapse.exc as s_exc

import synapse.lib.gis as s_gis
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

class Dist(s_types.IntBase):

    def postTypeInit(self):
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

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

        return int(valu * mult), {}

    def indx(self, norm):
        return norm.to_bytes(8, 'big')

    def repr(self, norm):

        for base, unit in distrepr:
            if norm >= base:
                size = norm / base
                return '%s %s' % (size, unit)

        return '%d mm' % (norm,)

class Latitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 90 * 10**8

    def postTypeInit(self):
        self.setNormFunc(int, self._normIntStr)
        self.setNormFunc(str, self._normIntStr)
        self.setNormFunc(float, self._normFloat)

    def _normFloat(self, valu):
        if valu > 90.0 or valu < -90.0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Latitude may only be -90.0 to 90.0')

        valu = int(valu * Latitude.SCALE) / Latitude.SCALE

        return valu, {}

    def _normIntStr(self, valu):
        try:
            valu = float(valu)
        except Exception:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid float format')
        return self._normFloat(valu)

    @staticmethod
    def getLatInt(norm):
        return int(norm * Latitude.SCALE + Latitude.SPACE)

    def indx(self, norm):
        return self.getLatInt(norm).to_bytes(5, 'big')

class LatLong(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(list, self._normPyTuple)
        self.setNormFunc(tuple, self._normPyTuple)

        self.setCmprCtor('near=', self._cmprNear)
        self.setLiftHintCmprCtor('near=', self._cmprNear)
        self.indxcmpr['near='] = self._indxNear

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

    def _indxNear(self, valu):

        (lat, lon), dist = self._normCmprValu(valu)

        latmin, latmax, lonmin, lonmax = s_gis.bbox(lat, lon, dist)

        zipmin, zipmax = self.getLatLonZipRange((latmin, lonmin), (latmax, lonmax))

        return (
            ('range', (zipmin, zipmax)),
        )

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

    def indx(self, valu):
        zstr = self.getLatLonZip(*valu)
        return int(self.getLatLonZip(*valu), 2).to_bytes(10, 'big')

    def repr(self, norm):
        return f'{norm[0]},{norm[1]}'

    @staticmethod
    def getLatLonZip(lat, lon):
        '''
        Return a magic big-endian zip of the bits from intified lat, lon
        '''
        latint = Latitude.getLatInt(lat)
        lonint = Longitude.getLonInt(lon)
        return ''.join(map(lambda x, y: x + y, f'{latint:040b}', f'{lonint:040b}'))

    @staticmethod
    def getLatLonZipRange(minxy, maxxy):
        minzip = LatLong.getLatLonZip(*minxy)
        maxzip = LatLong.getLatLonZip(*maxxy)
        prefix = os.path.commonprefix([minzip, maxzip])
        zstr = prefix.ljust(80, '0')
        fstr = prefix.ljust(80, '1')
        minval = int(zstr, 2).to_bytes(10, 'big')
        maxval = int(fstr, 2).to_bytes(10, 'big')
        return minval, maxval

class Longitude(s_types.Type):
    SCALE = 10**8  # ~1mm resolution
    SPACE = 180 * 10**8

    def postTypeInit(self):
        self.setNormFunc(int, self._normIntStr)
        self.setNormFunc(str, self._normIntStr)
        self.setNormFunc(float, self._normFloat)

    def _normIntStr(self, valu):
        try:
            valu = float(valu)
        except Exception:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Invalid float format')
        return self._normFloat(valu)

    def _normFloat(self, valu):

        if valu > 180.0 or valu < -180.0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Longitude may only be -180.0 to 180.0')

        valu = int(valu * Longitude.SCALE) / Longitude.SCALE

        return valu, {}

    @staticmethod
    def getLonInt(norm):
        return int(norm * Longitude.SCALE + Longitude.SPACE)

    def indx(self, norm):
        return self.getLonInt(norm).to_bytes(5, 'big')

class GeoModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('geo', {

                'ctors': (
                    ('geo:dist', 'synapse.models.geospace.Dist', {}, {
                        'doc': 'A geographic distance (base unit is mm)', 'ex': '10 km'
                    }),
                    ('geo:latitude', 'synapse.models.geospace.Latitude', {}, {}),
                    ('geo:longitude', 'synapse.models.geospace.Longitude', {}, {}),
                    ('geo:latlong', 'synapse.models.geospace.LatLong', {}, {
                        'doc': 'A Lat/Long string specifying a point on Earth',
                        'ex': '-12.45,56.78'
                    }),
                ),

                'types': (

                    ('geo:nloc', ('comp', {'fields': (('ndef', 'ndef'), ('latlong', 'geo:latlong'), ('time', 'time'))}), {
                        'doc': 'Records a node latitude/longitude in space-time.'
                    }),

                    ('geo:place', ('guid', {}), {
                        'doc': 'A GUID for a geographic place.'}),

                    ('geo:address', ('str', {'lower': 1, 'onespace': 1, 'strip': True}), {
                        'doc': 'A street/mailing address string.',
                    }),

                    ('geo:bbox', ('comp', {'sepr': ',', 'fields': (
                                                ('xmin', 'geo:longitude'),
                                                ('xmax', 'geo:longitude'),
                                                ('ymin', 'geo:latitude'),
                                                ('ymax', 'geo:latitude'))}), {
                        'doc': 'A geospatial bounding box in (xmin, xmax, ymin, ymax) format.',
                    }),
                ),

                'forms': (

                    ('geo:nloc', {}, (

                        ('ndef', ('ndef', {}), {'ro': True,
                            'doc': 'The node with location in geo/time'}),

                        ('ndef:form', ('str', {}), {'ro': True,
                            'doc': 'The form of node referenced by the ndef.'}),

                        ('latlong', ('geo:latlong', {}), {'ro': True,
                            'doc': 'The latitude/longitude the node was observed.'}),

                        ('time', ('time', {}), {'ro': True,
                            'doc': 'The time the node was observed at location'}),

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
