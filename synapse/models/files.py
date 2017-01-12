def getDataModel():
    return {

        'prefix':'file',
        'version':201701061638,

        'types':(
            ('file:guid',{'subof':'guid','doc':'A unique file identifier'}),
            ('file:sub',{'subof':'sepr','fields':'parent,file:guid|child,file:guid'}),
            ('file:base',{'subof':'str','lower':1,'doc':'A file basename such as foo.exe'}),
        ),

        'forms':(

            ('file:bytes', {'ptype':'file:guid'},(
                ('size',{'ptype':'int'}),
                ('md5',{'ptype':'hash:md5'}),
                ('sha1',{'ptype':'hash:sha1'}),
                ('sha256',{'ptype':'hash:sha256'}),
                ('sha512',{'ptype':'hash:sha512'}),
                ('name',{'ptype':'file:base','doc':'For display purposes only'})
            )),

            ('file:subfile', {'ptype':'file:sub'},(
                ('parent',{'ptype':'file:guid'}),
                ('child',{'ptype':'file:guid'}),
                ('name',{'ptype':'file:base'}),
                #TODO others....
            )),

        ),
    }

#def revDataModel(core):

