def getDataModel():
    return {
        'prefix':'ou',
        'version':201611301215,

        'types':(
            ('ou:org',{'subof':'guid','doc':'A GUID for a human organization such as a company or military unit'}),
            ('ou:user',{'subof':'sepr','sep':'/','fields':'org,ou:org|user,inet:user','doc':'A user name within an organization'}),
            ('ou:alias',{'subof':'str:lwr','regex':'^[0-9a-z]+$','doc':'An alias for the org GUID','ex':'vertexproj'}),

            ('ou:name',{'subof':'str:lwr'}),
            ('ou:sic',{'subof':'int','doc':'Standard Industrial Classification Code'}),
            ('ou:naics',{'subof':'int','doc':'North American Industry Classification System'})
        ),

        'forms':(

            ('ou:org',{'ptype':'ou:org'},[
                ('cc',{'ptype':'pol:iso2'}),
                ('name',{'ptype':'ou:name'}),
                ('alias',{'ptype':'ou:alias'}),
                ('phone',{'ptype':'tel:phone','doc':'The primary phone number for the organization'}),
                ('sic',{'ptype':'ou:sic'}),
                ('naics',{'ptype':'ou:naics'}),
                ('us:cage',{'ptype':'gov:us:cage'}),
            ]),

            ('ou:member',{'ptype':'sepr','sep':'/','fields':'org,ou:org|person,ou:person'},[
                ('start',{'ptype':'time:min','defval':0}),
                ('title',{'ptype':'str:lwr','defval':'??'}),
            ]),

            ('ou:owns',{'ptype':'sepr','sep':'/','fields':'owner,ou:org|owned,ou:org'},[
            ]),
        ),

    }
