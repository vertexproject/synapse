
latlongre = '^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$'

def getDataModel():
    return {
        'prefix':'geo',
        'version':201611251209,

        'types':(
            ('geo:place',{'subof':'guid','doc':'A GUID for a specific place'}),
            ('geo:latlong',{'subof':'str', 'regex':latlongre,
                            'nullval':'??','doc':'A Lat/Long string specifying a point'}),
        ),

        'forms':(
            ('geo:place',{'ptype':'geo:place'},[
                ('name',{'ptype':'str','lower':1,'doc':'The name of the place'}),
                ('latlong',{'ptype':'geo:latlong','defval':'??','doc':'The location of the place'}),
            ]),
        ),
    }
