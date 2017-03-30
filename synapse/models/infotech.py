def getDataModel():
    return {
        'prefix':'it',
        'version':201703301552,

        'types': (
            ('it:host',         {'subof':'guid','doc':'A GUID for a host/system'}),
            ('it:sec:cve',      {'subof':'str', 'regex':'^CVE-[0-9]{4}-[0-9]{4,6}$','doc':'A CVE entry from Mitre'}),

            ('it:av:sig',       {'subof':'sepr', 'sep':'/', 'fields':'org,ou:alias|sig,str:lwr', 'doc':'An antivirus signature' }),
            ('it:av:filehit',   {'subof':'sepr', 'sep':'/', 'fields':'file,file:bytes|sig,it:av:sig', 'doc':'An antivirus hit' }),
        ),

        'forms': (

            ('it:host', {'ptype':'it:host'},[
                #FIXME we probably eventually need a bunch of stuff here...
            ]),

            ('it:sec:cve', {'ptype':'it:sec:cve'},[
                ('desc',{'ptype':'str'}),
            ]),

            ('it:av:sig', {'ptype':'it:av:sig'},[
                ('sig',{'ptype':'str:lwr'}),
                ('org',{'ptype':'ou:alias'}),
                ('desc',{'ptype':'str'}),
                ('url',{'ptype':'inet:url'}),
            ]),

            ('it:av:filehit', {'ptype':'it:av:filehit'},[
                ('file',{'ptype':'file:bytes'}),
                ('sig',{'ptype':'it:av:sig'}),
            ])
        ),
    }
