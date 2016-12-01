def getDataModel():
    return {
        'prefix':'ou',
        'version':201611301215,

        'types':(
            ('ou:pop',{'subof':'int'}),
            ('ou:fname',{'subof':'str:lwr','doc':'A persons first/given name'}),
            ('ou:lname',{'subof':'str:lwr','doc':'A persons family name'}),

            ('ou:org',{'subof':'guid'}),
            ('ou:host',{'subof':'guid'}),
            ('ou:person',{'subof':'guid'}),

            ('ou:user',{'subof':'sepr','sep':'/','fields':'org,ou:org|user,inet:user'}),
            ('ou:fullname',{'subof':'sepr','sep':'/','fields':'last,ou:lname|first,ou:fname'}),
        ),

        'forms':(

            ('ou:org',{'ptype':'ou:org'},[
                ('cc',{'ptype':'pol:iso2'}),
                ('name',{'ptype':'str:lwr'}),
                ('alias',{'ptype':'str:lwr'}),
            ]),

            ('ou:person',{'ptype':'ou:person'},[
                ('dob',{'ptype':'time'}),
                ('fullname',{'ptype':'ou:fullname'}),
                ('fullname:fname',{'ptype':'ou:fname'}),
                ('fullname:lname',{'ptype':'ou:lname'}),
            ]),

            ('ou:member',{'ptype':'sepr','sep':'/','fields':'org,ou:org|person,ou:person'},[
                ('start',{'ptype':'time:min','defval':0}),
                ('title',{'ptype':'str:lwr','defval':'??'}),
            ]),

            ('ou:owns',{'ptype':'sepr','sep':'/','fields':'owner,ou:org|owned,ou:org'},[
            ]),
        ),

    }
