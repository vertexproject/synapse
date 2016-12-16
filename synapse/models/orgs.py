def getDataModel():
    return {
        'prefix':'ou',
        'version':201611301215,

        'types':(
            ('ou:org',{'subof':'guid','doc':'A GUID for a human organization such as a company or military unit'}),
            ('ou:host',{'subof':'guid','doc':'A GUID for a host within an organization'}),
            ('ou:user',{'subof':'sepr','sep':'/','fields':'org,ou:org|user,inet:user','doc':'A user name within an organization'}),

            ('ou:alias',{'subof':'str','lower':1,'regex':'^[0-9a-z]+$','doc':'An alias for the org GUID','ex':'vertexproj'}),
        ),

        'forms':(

            ('ou:org',{'ptype':'ou:org'},[
                ('cc',{'ptype':'pol:iso2'}),
                ('name',{'ptype':'str:lwr'}),
                ('alias',{'ptype':'ou:alias'}),
            ]),

            ('ou:member',{'ptype':'sepr','sep':'/','fields':'org,ou:org|person,ou:person'},[
                ('start',{'ptype':'time:min','defval':0}),
                ('title',{'ptype':'str:lwr','defval':'??'}),
            ]),

            ('ou:owns',{'ptype':'sepr','sep':'/','fields':'owner,ou:org|owned,ou:org'},[
            ]),
        ),

    }
