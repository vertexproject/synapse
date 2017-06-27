from synapse.lib.module import CoreModule

latlongre = '^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$'

class GeoMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('geo:place', {'subof': 'guid', 'alias': 'geo:place:alias', 'doc': 'A GUID for a specific place'}),
                ('geo:alias',
                 {'subof': 'str:lwr', 'regex': '^[0-9a-z]+$', 'doc': 'An alias for the place GUID', 'ex': 'foobar'}),
                ('geo:latlong',
                 {'subof': 'str', 'regex': latlongre, 'nullval': '??', 'doc': 'A Lat/Long string specifying a point'}),
            ),

            'forms': (
                ('geo:place', {'ptype': 'geo:place'}, [
                    ('alias', {'ptype': 'geo:alias'}),
                    ('name', {'ptype': 'str', 'lower': 1, 'doc': 'The name of the place'}),
                    ('latlong', {'ptype': 'geo:latlong', 'defval': '??', 'doc': 'The location of the place'}),
                ]),
            ),

        }
        name = 'geo'
        return ((name, modl), )
