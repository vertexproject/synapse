
from synapse.lib.types import DataType,subtype

def getDataModel():
    return {

        'version':201611251144,

        'types':(
            ('hash:md5',    {'subof':'str','regex':'^[0-9a-f]{32}$', 'lower':1}),
            ('hash:sha1',   {'subof':'str','regex':'^[0-9a-f]{40}$', 'lower':1}),
            ('hash:sha256', {'subof':'str','regex':'^[0-9a-f]{64}$', 'lower':1}),
            ('hash:sha384', {'subof':'str','regex':'^[0-9a-f]{96}$', 'lower':1}),
            ('hash:sha512', {'subof':'str','regex':'^[0-9a-f]{128}$', 'lower':1}),
        ),
    }
