def getDataModel():
    return {
        'prefix':'it',
        'version':201703301552,

        'types': (
            ('it:host',         {'subof':'guid','doc':'A GUID for a host/system'}),
            ('it:hostname',     {'subof':'str:lwr','doc':'A system/host name'}),

            ('it:hosturl',      {'subof':'comp','fields':'host,it:host|url,inet:url'}),
            ('it:hostfile',     {'subof':'comp','fields':'host,it:host|path,file:path|file,file:bytes','doc':'A file created on a host'}),

            ('it:sec:cve',      {'subof':'str:lwr', 'regex':'(?i)^CVE-[0-9]{4}-[0-9]{4,}$','doc':'A CVE entry from Mitre'}),

            ('it:av:sig',       {'subof':'sepr', 'sep':'/', 'fields':'org,ou:alias|sig,str:lwr', 'doc':'An antivirus signature' }),
            ('it:av:filehit',   {'subof':'sepr', 'sep':'/', 'fields':'file,file:bytes|sig,it:av:sig', 'doc':'An antivirus hit' }),
        ),

        'forms': (

            ('it:host', {}, [
                ('name',{'ptype':'it:hostname','doc':'Optional name for the host'}),
                ('desc',{'ptype':'str:txt','doc':'Optional description of the host'}),

                #FIXME we probably eventually need a bunch of stuff here...
                ('ipv4',{'ptype':'inet:ipv4','doc':'Optional last known ipv4 address for the host'}),

            ]),

            ('it:hostname', {}, ()),

            ('it:hostfile',{},[

                ('host',{'ptype':'it:host','ro':1}),

                ('path',{'ptype':'file:path','ro':1}),

                ('path:ext',{'ptype':'str:lwr','ro':1}),
                ('path:dir',{'ptype':'file:path','ro':1}),
                ('path:base',{'ptype':'file:base','ro':1}),

                ('file',{'ptype':'file:bytes','ro':1}),

                # unified / accepted file create/modify/access times
                ('ctime',{'ptype':'time','doc':'Optional file creation time'}),
                ('mtime',{'ptype':'time','doc':'Optional file modification time'}),
                ('atime',{'ptype':'time','doc':'Optional file access time'}),

                # other filesystem specific options/times may go here...
                #('ntfs:footime',{'ptype':'time'}),

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
