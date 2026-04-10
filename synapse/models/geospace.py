import synapse.exc as s_exc

import synapse.lib.gis as s_gis
import synapse.lib.layer as s_layer
import synapse.lib.types as s_types
import synapse.lib.grammar as s_grammar

units = {
    'mm': 1,
    'millimeter': 1,
    'millimeters': 1,

    'cm': 10,
    'centimeter': 10,
    'centimeters': 10,

    # international foot
    'foot': 304.8,
    'feet': 304.8,

    'm': 1000,
    'meter': 1000,
    'meters': 1000,

    # international mile
    'mile': 1609344,
    'miles': 1609344,

    'km': 1000000,
    'kilometer': 1000000,
    'kilometers': 1000000,

    # international yard
    'yard': 914.4,
    'yards': 914.4,
}

distrepr = (
    (1000000.0, 'km'),
    (1000.0, 'm'),
    (10.0, 'cm'),
)

arearepr = (
    (1000000.0, 'sq.km'),
    (1000.0, 'sq.m'),
    (10.0, 'sq.cm'),
)

areaunits = {
    'mm²': 1,
    'sq.mm': 1,

    'cm²': 10,
    'sq.cm': 10,

    # international foot
    'foot²': 304.8,
    'feet²': 304.8,
    'sq.feet': 304.8,

    'm²': 1000,
    'sq.m': 1000,
    'sq.meters': 1000,

    # international mile
    'mile²': 1609344,
    'miles²': 1609344,
    'sq.miles': 1609344,

    'km²': 1000000,
    'sq.km': 1000000,

    # international yard
    'yard²': 914.4,
    'sq.yards': 914.4,
}

class Dist(s_types.Int):

    _opt_defs = (
        ('baseoff', 0),  # type: ignore
    ) + s_types.Int._opt_defs

    def postTypeInit(self):
        s_types.Int.postTypeInit(self)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)
        self.baseoff = self.opts.get('baseoff')

    async def _normPyInt(self, valu, view=None):
        return valu, {}

    async def _normPyStr(self, text, view=None):
        try:
            valu, off = s_grammar.parse_float(text, 0)
        except Exception:
            mesg = f'Distance requires a valid number and unit. No valid number found: {text}'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

        unit, off = s_grammar.nom(text, off, s_grammar.alphaset)

        mult = units.get(unit.lower())
        if mult is None:
            mesg = f'Unknown unit of distance: {text}'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        norm = int(valu * mult) + self.baseoff
        if norm < 0:
            mesg = f'A geo:dist may not be negative: {text}'
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

areachars = {'.'}.union(s_grammar.alphaset)
class Area(s_types.Int):

    def postTypeInit(self):
        s_types.Int.postTypeInit(self)
        self.setNormFunc(int, self._normPyInt)
        self.setNormFunc(str, self._normPyStr)

    async def _normPyInt(self, valu, view=None):
        return valu, {}

    async def _normPyStr(self, text, view=None):
        try:
            valu, off = s_grammar.parse_float(text, 0)
        except Exception:
            mesg = f'Area requires a valid number and unit, no valid number found: {text}'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

        unit, off = s_grammar.nom(text, off, areachars)

        mult = areaunits.get(unit.lower())
        if mult is None:
            mesg = f'Unknown unit of area: {text}'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        norm = int(valu * mult)
        if norm < 0:
            mesg = f'A geo:area may not be negative: {text}'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        return norm, {}

    def repr(self, norm):

        text = None
        for base, unit in arearepr:
            if norm >= base:
                size = norm / base
                text = f'{size} {unit}'
                break

        if text is None:
            text = f'{norm} sq.mm'

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

        self.lattype = self.modl.type('geo:latitude')
        self.lontype = self.modl.type('geo:longitude')

    async def _normCmprValu(self, valu):
        latlong, dist = valu
        rlatlong = (await self.modl.type('geo:latlong').norm(latlong))[0]
        rdist = (await self.modl.type('geo:dist').norm(dist))[0]
        return rlatlong, rdist

    async def _cmprNear(self, valu):
        latlong, dist = await self._normCmprValu(valu)

        async def cmpr(valu):
            if s_gis.haversine(valu, latlong) <= dist:
                return True
            return False
        return cmpr

    async def _storLiftNear(self, cmpr, valu):
        latlong = (await self.norm(valu[0]))[0]
        dist = (await self.modl.type('geo:dist').norm(valu[1]))[0]
        return ((cmpr, (latlong, dist), self.stortype),)

    async def _normPyStr(self, valu, view=None):
        valu = tuple(valu.strip().split(','))
        return await self._normPyTuple(valu)

    async def _normPyTuple(self, valu, view=None):
        if len(valu) != 2:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Valu must contain valid latitude,longitude')

        try:
            latv, latfo = await self.lattype.norm(valu[0])
            lonv, lonfo = await self.lontype.norm(valu[1])
        except Exception as e:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg=str(e)) from None

        return (latv, lonv), {'subs': {'lat': (self.lattype.typehash, latv, latfo),
                                       'lon': (self.lontype.typehash, lonv, lonfo)}}

    def repr(self, norm):
        return f'{norm[0]},{norm[1]}'
