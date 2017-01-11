
def getDataModel():
    return {
        'prefix':'pol',
        'version':201611301150,

        'types':(
            ('pol:news',{'subof':'guid','doc':'A GUID for a news article or report'}),
            ('pol:country',{'subof':'guid','doc':'A GUID for a country'}),

            ('pol:iso2',{'subof':'str','lower':1,'regex':'^[a-z0-9]{2}$','nullval':'??','doc':'The 2 digit ISO country code','ex':'us'}),
            ('pol:iso3',{'subof':'str','lower':1,'regex':'^[a-z0-9]{3}$','nullval':'??','doc':'The 3 digit ISO country code','ex':'usa'}),
            ('pol:isonum',{'subof':'int','doc':'The ISO integer country code','ex':'840'}),
        ),

        'forms':(

            ('pol:country',{'ptype':'pol:country'},[
                ('name',{'ptype':'str:lwr'}),
                ('iso2',{'ptype':'pol:iso2'}),
                ('iso3',{'ptype':'pol:iso3'}),
                ('isonum',{'ptype':'pol:isonum'}),
                ('pop',{'ptype':'int','defval':0}),
                ('founded',{'ptype':'time','defval':0}),
                ('tld',{'ptype':'inet:fqdn','defval':'??'}),
            ]),

            ('pol:flag',{'ptype':'hash:sha256','doc':'The flag image SHA256'},[
                ('cc', {'ptype':'pol:iso2','doc':'The (optional) ISO2 country code for the flag'}),
                ('orgalias',{'ptype':'ou:alias','doc':'The (optional) org alias for the flat'}),
            ]),

            ('pol:hist',{'ptype':'pol:country'},[
                #TODO retired/historical countries
            ]),

            ('pol:news',{'ptype':'pol:news','doc':'A published news item, report, or article GUID'},[
                ('url',{'ptype':'inet:url','doc':'The URL where the news was published','ex':'http://cnn.com/news/mars-lander.html'}),
                ('url:fqdn',{'ptype':'inet:fqdn','doc':'The FQDN within the news URL','ex':'cnn.com'}),
                ('sha256',{'ptype':'hash:sha256','doc':'The SHA256 of a file blob which originated the news'}),

                ('title',{'ptype':'str:lwr','doc':'Title/Headline for the news','ex':'mars lander reaches mars'}),
                ('author',{'ptype':'str:lwr','defval':'??','doc':'The free-form author of the news article','ex':'sarcastic rover <foo@bar.com>'}),
                ('summary',{'ptype':'str:lwr','defval':'??','doc':'A brief summary of the news item','ex':'lorum ipsum'}),
                ('published',{'ptype':'time','defval':0,'doc':'The date the news item was published','ex':'20161201180433'}),
            ]),
        ),
    }
