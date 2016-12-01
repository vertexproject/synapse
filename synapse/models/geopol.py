

def getDataModel():
    return {
        'prefix':'pol',
        'version':201611301150,

        'types':(
            ('pol:news',{'subof':'guid'}),
            ('pol:country',{'subof':'guid'}),

            ('pol:iso2',{'subof':'str','lower':1,'regex':'^[a-z0-9]{2}$'}),
            ('pol:iso3',{'subof':'str','lower':1,'regex':'^[a-z0-9]{3}$'}),
            ('pol:isonum',{'subof':'int'}),
        ),

        'forms':(

            ('pol:country',{'ptype':'pol:country'},[
                ('name',{'ptype':'str:lwr'}),
                ('iso2',{'ptype':'pol:iso2'}),
                ('iso3',{'ptype':'pol:iso3'}),
                ('isonum',{'ptype':'pol:isonum'}),
                ('pop',{'ptype':'int','defval':0}),
                ('founded',{'ptype':'time','defval':0}),
            ]),

            ('pol:hist',{'ptype':'pol:country'},[
                #TODO retired/historical countries
            ]),

            ('pol:news',{'ptype':'pol:news'},[
                ('url',{'ptype':'inet:url'}),
                ('url:fqdn',{'ptype':'inet:fqdn'}),
                ('sha256',{'ptype':'hash:sha256'}),

                ('title',{'ptype':'str:lwr'}),
                ('author',{'ptype':'str:lwr','defval':'??'}),
                ('summary',{'ptype':'str:lwr','defval':'??'}),
                ('published',{'ptype':'time','defval':0}),
            ]),
        ),
    }
