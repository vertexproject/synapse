def getDataModel():
    return {
        'prefix':'media',
        'version':201703271454,

        'types':(
            ('media:news',{'subof':'guid','doc':'A GUID for a news article or report'}),
            # TODO types and forms...
            #('media:doi',{}),
            #('media:isbn',{}),
            #('media:issn',{}),
        ),

        'forms':(
            ('media:news',{'ptype':'media:news','doc':'A published news item, report, or article GUID'},[
                ('url',{'ptype':'inet:url','doc':'The (optional) URL where the news was published','ex':'http://cnn.com/news/mars-lander.html'}),
                ('url:fqdn',{'ptype':'inet:fqdn','doc':'The FQDN within the news URL','ex':'cnn.com'}),

                #('doi',{'ptype':'media:issn','doc':'The (optional) ISSN number for the news publication'})
                #('issn',{'ptype':'media:issn','doc':'The (optional) ISSN number for the news publication'})

                ('file',{'ptype':'file:bytes','doc':'The (optional) file blob containing or published as the news'}),

                ('title',{'ptype':'str:lwr','doc':'Title/Headline for the news','defval':'??','ex':'mars lander reaches mars'}),
                ('summary',{'ptype':'str:lwr','defval':'??','doc':'A brief summary of the news item','ex':'lorum ipsum'}),
                ('published',{'ptype':'time','defval':0,'doc':'The date the news item was published','ex':'20161201180433'}),

                ('org',{'ptype':'ou:alias','defval':'??','doc':'The org alias which published the news','ex':'microsoft'}),
                ('author',{'ptype':'ps:name','defval':'?,?','doc':'The free-form author of the news','ex':'stark,anthony'}),
            ]),
        ),
    }
