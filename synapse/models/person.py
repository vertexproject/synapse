
def getDataModel():
    return {
        'prefix':'ps',
        'version':201612141459,

        'types':(
            ('ps:person',{'subof':'guid','doc':'A GUID for a person or suspected person'}),
            ('ps:givname',{'subof':'str:lwr','doc':'A persons first/given name','ex':'tony'}),
            ('ps:surname',{'subof':'str:lwr','doc':'A persons family/last name','ex':'stark'}),
        ),

        'forms':(
            ('ps:person',{'ptype':'ps:person'},[
                ('dob',{'ptype':'time','doc':'The Date of Birth (DOB) if known'}),
                ('name',{'ptype':'ps:givname','doc':'The given/first name if known'}),
                ('surname',{'ptype':'ps:surname','doc':'The family/last name if known'}),
                ('aliases',{'ptype':'str','doc':'Any known aliases used for token search'}),
            ]),

        ),
    }
