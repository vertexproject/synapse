
def getDataModel():
    return {
        'prefix':'ps',
        'version':201703271415,

        'types':(
            ('ps:person',{'subof':'guid','doc':'A GUID for a person or suspected person'}),
            ('ps:fullname',{'subof':'sepr','sep':',','fields':'sur,ps:name|given,ps:name',
                            'ex':'smith,bob',
                            'doc':'A last,first person full name'}),

            ('ps:name',{'subof':'str:lwr','doc':'A single name element (potentially given or sur)','ex':'mike'}),

            ('ps:has:user',{'subof':'sepr','sep':'/','fields':'person,ps:person|user,inet:user'}),
            ('ps:has:alias',{'subof':'sepr','sep':'/','fields':'person,ps:person|fullname,ps:fullname'}),
            ('ps:has:phone',{'subof':'sepr','sep':'/','fields':'person,ps:person|phone,tel:phone'}),
            ('ps:has:email',{'subof':'sepr','sep':'/','fields':'person,ps:person|email,inet:email'}),
            ('ps:has:netuser',{'subof':'sepr','sep':'/','fields':'person,ps:person|netuser,inet:netuser'}),

            #('ps:has:host',{'subof','sepr','sep':'/','fields':'person,ps:person|host,it:host'}),
            # FIXME add wireless elemements like NMEI and IMEI once modeled
        ),

        'forms':(
            ('ps:name',{'ptype':'ps:name'},[]),
            ('ps:fullname',{'ptype':'ps:fullname'},[
                ('sur',{'ptype':'ps:name','doc':'The "surname" part of ps:fullname','ex':'stark'}),
                ('given',{'ptype':'ps:name','doc':'The "given name" part of ps:fullname','ex':'tony'}),
            ]),
            ('ps:person',{'ptype':'ps:person'},[
                ('dob',{'ptype':'time','doc':'The Date of Birth (DOB) if known'}),
                ('name',{'ptype':'ps:fullname'}),
                ('name:sur',{'ptype':'ps:name'}),
                ('name:given',{'ptype':'ps:name'}),
            ]),

        ),
    }
