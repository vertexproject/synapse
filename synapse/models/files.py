def getDataModel():
    return {
        'prefix':'file',
        'version':201701061638,

        'types':(
            ('file:sub',{'subof':'sepr','fields':'parent,hash:sha256|child,hash:sha256'}),
            ('file:base',{'subof':'str','lower':1,'doc':'A file basename such as foo.exe'}),
        ),

        'forms':(

            ('file:bytes', {'ptype':'hash:sha256'},(
                ('size',{'ptype':'int'}),
                ('md5',{'ptype':'hash:md5'}),
                ('sha1',{'ptype':'hash:sha1'}),
                ('sha256',{'ptype':'hash:sha256'}),
                ('sha512',{'ptype':'hash:sha512'}),
            )),

            ('file:subfile', {'ptype':'file:sub'},(
                ('parent',{'ptype':'sha256'}),
                ('child',{'ptype':'sha256'}),
                ('name',{'ptype':'file:base'}),
                #TODO others....
            )),

        ),
    }

