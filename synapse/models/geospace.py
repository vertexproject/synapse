from synapse.lib.types import DataType,subtype

latlongre = '^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$'

def getDataModel():
    return {
        'prefix':'geo',
        'version':201611251209,

        'types':(
            ('geo:latlong',{'subof':'str', 'regex':latlongre}),
        ),
    }
