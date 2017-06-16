import synapse.compat as s_compat
import synapse.common as s_common

def getDataModel():
    return {
        'prefix':'syn',
        'version':201706032355,

        'types':(
            ('syn:splice', {'subof':'guid'}),
        ),

        'forms':(

            ('syn:splice', {'local':1},(
                ('act', {'ptype':'str:lwr'}),
                ('time', {'ptype':'time'}),
                ('node', {'ptype':'guid'}),
                ('user', {'ptype':'str:lwr'}),

                ('tag', {'ptype':'str:lwr'}),
                ('form', {'ptype':'str:lwr'}),
                ('valu', {'ptype':'str:lwr'}),
            )),

        ),
    }
