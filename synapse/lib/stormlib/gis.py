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
                      {'name': 'lon', 'type': 'float', 'desc': 'The longitude in degrees.'},
                      {'name': 'lat', 'type': 'float', 'desc': 'The latitude in degrees.'},
                      {'name': 'dist', 'type': 'int', 'desc': 'A distance in geo:dist base units (mm).'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple of (lonmin, lonmax, latmin, latmax).', }
        }},
    )
    _storm_lib_path = ('gis',)

    def getObjLocals(self):
        return {
            'bbox': self._methBbox,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methBbox(self, lon, lat, dist):
        try:
            lon = float(await s_stormtypes.toprim(lon))
            lat = float(await s_stormtypes.toprim(lat))
            dist = await s_stormtypes.toint(dist)
        except ValueError as e:
            raise s_exc.BadArg(mesg=f'$lib.gis.bbox(): {e}')
        except s_exc.BadCast as e:
            raise s_exc.BadArg(mesg=f'$lib.gis.bbox(): {e.get("mesg")}')

        (latmin, latmax, lonmin, lonmax) = s_gis.bbox(lat, lon, dist)
        return (lonmin, lonmax, latmin, latmax)
