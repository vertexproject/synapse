
def getDataModel():
    return {
        'version':201702030845,

        'types': (
            ('tech:av:sig',     {'subof':'sepr', 'sep':'/', 'fields':'org,ou:alias|sig,str:lwr', 'doc':'An antivirus signature' }),
            ('tech:av:filehit', {'subof':'sepr', 'sep':'/', 'fields':'file,file:guid|sig,tech:av:sig', 'doc':'An antivirus hit' }),
        ),

        'forms': (
            ('tech:av:sig', {'ptype':'tech:av:sig'},[
                ('sig',{'ptype':'str:lwr'}),
                ('org',{'ptype':'ou:alias'}),
                ('desc',{'ptype':'str'}),
                ('url',{'ptype':'inet:url'}),
            ]),
            ('tech:av:filehit', {'ptype':'tech:av:filehit'},[
                ('file',{'ptype':'file:guid'}),
                ('sig',{'ptype':'tech:av:sig'}),
            ])
        ),

    }
