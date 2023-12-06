import synapse.exc as s_exc

import synapse.lib.gis as s_gis
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class GisLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for earth based geospatial calculations.
    '''
    _storm_locals = (
        {'name': 'bbox', 'desc': 'Calculate a min/max bounding box for the specified circle.',
         'type': {'type': 'function', '_funcname': '_methBbox',
                  'args': (
                      {'name': 'lat', 'type': 'float', 'desc': 'The latitude in degrees.'},
                      {'name': 'lon', 'type': 'float', 'desc': 'The longitude in degrees.'},
                      {'name': 'dist', 'type': 'int', 'desc': 'A distance in geo:dist base units (mm).'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple of (latmin, latmax, lonmin, lonmax).', }
        }},
    )
    _storm_lib_path = ('gis',)

    def getObjLocals(self):
        return {
            'bbox': self._methBbox,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methBbox(self, lat, lon, dist):
        try:
            lat = float(await s_stormtypes.toprim(lat))
            lon = float(await s_stormtypes.toprim(lon))
        except ValueError as e:
            raise s_exc.BadArg(mesg=f'$lib.gis.bbox(): {e}')
        dist = await s_stormtypes.toint(dist)

        return s_gis.bbox(lat, lon, dist)
