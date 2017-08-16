import synapse.common as s_common

from synapse.eventbus import on
from synapse.lib.module import CoreModule, modelrev

class ItMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('it:host', {'subof': 'guid', 'doc': 'A GUID for a host/system'}),
                ('it:hostname', {'subof': 'str:lwr', 'doc': 'A system/host name'}),

                ('it:hosturl', {'subof': 'comp', 'fields': 'host,it:host|url,inet:url'}),
                ('it:hostfile', {'subof': 'comp', 'fields': 'host=it:host', 'optfields':'path=file:path,file=file:bytes,time=time', 'doc': 'A file created on a host'}),

                ('it:sec:cve',
                 {'subof': 'str:lwr', 'regex': '(?i)^CVE-[0-9]{4}-[0-9]{4,}$', 'doc': 'A CVE entry from Mitre'}),

                ('it:av:sig',
                 {'subof': 'sepr', 'sep': '/', 'fields': 'org,ou:alias|sig,str:lwr', 'doc': 'An antivirus signature'}),

                ('it:av:filehit',
                 {'subof': 'sepr', 'sep': '/', 'fields': 'file,file:bytes|sig,it:av:sig', 'doc': 'An antivirus hit'}),
            ),

            'forms': (

                ('it:host', {}, [
                    ('name', {'ptype': 'it:hostname', 'doc': 'Optional name for the host'}),
                    ('desc', {'ptype': 'str:txt', 'doc': 'Optional description of the host'}),

                    # FIXME we probably eventually need a bunch of stuff here...
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'Optional last known ipv4 address for the host'}),

                ]),

                ('it:hostname', {}, ()),

                ('it:sec:cve', {'ptype': 'it:sec:cve'}, [
                    ('desc', {'ptype': 'str'}),
                ]),

                ('it:av:sig', {'ptype': 'it:av:sig'}, [
                    ('sig', {'ptype': 'str:lwr'}),
                    ('org', {'ptype': 'ou:alias'}),
                    ('desc', {'ptype': 'str'}),
                    ('url', {'ptype': 'inet:url'}),
                ]),

                ('it:av:filehit', {'ptype': 'it:av:filehit'}, [
                    ('file', {'ptype': 'file:bytes'}),
                    ('sig', {'ptype': 'it:av:sig'}),
                ])
            ),

        }
        name = 'it'
        return ((name, modl), )

    @on('node:form', form='it:dev:str')
    def _onFormItDevStr(self, mesg):
        props = mesg[1].get('props')
        props['it:dev:str:norm'] = mesg[1].get('valu').lower()

    @modelrev('it', 201708161120)
    def _revModl201708161120(self):
        self.core.loadDataModel({
            'types':(

                ('it:dev:str', {'subof':'str', 'doc':'A developer selected string'}),
                ('it:dev:int', {'subof':'int', 'doc':'A developer selected int constant'}),

                ('it:exec:proc', {'subof':'guid', 'doc':'A unique process execution on a host'}),

                ('it:dev:pipe', {'subof':'it:dev:str', 'doc':'A  named pipe string'}),
                ('it:dev:mutex', {'subof':'it:dev:str', 'doc':'A named mutex string'}),
                ('it:dev:regkey', {'subof':'it:dev:str', 'doc':'A windows registry key string'}),

                ('it:dev:regval', {'subof':'comp', 'fields':'key=it:dev:regkey',
                                   'optfields':'str=it:dev:str,int=int,bytes=file:bytes',
                                   'doc':'A windows registry key/val pair'}),

                ('it:exec:file', {'subof':'comp', 'fields':'host=it:host',
                                  'optfields':'path=file:path,file=file:bytes,time=time,proc=it:exec:proc',
                                  'doc':'A file instance created on a host'}),

                ('it:exec:pipe', {'subof':'comp', 'fields':'host=it:host,name=it:dev:pipe', 'optfields':'proc=it:exec:proc,time=time',
                                  'doc':'A named pipe instance created on a host'}),

                ('it:exec:mutex', {'subof':'comp', 'fields':'host=it:host,name=it:dev:mutex', 'optfields':'proc=it:exec:proc,time=time',
                                   'doc':'A named mutex instance created on a host'}),

                ('it:exec:regval', {'subof':'comp', 'fields':'host=it:host,regval=it:dev:regval',
                                    'optfields':'proc=it:exec:proc,time=time',
                                    'doc':'A named mutex instance created on a host'}),

                ('it:exec:url', {'subof':'comp', 'fields':'host=it:host,url=inet:url',
                                 'optfields':'file=file:bytes,proc=it:exec:proc,time=time',
                                 'doc':'A IPv4/TCP session made by a host'})

                ('it:exec:tcp4', {'subof':'comp', 'fields':'host=it:host,tcp4=inet:tcp4',
                                  'optfields':'proc=it:exec:proc,time=time',
                                  'doc':'A IPv4/TCP session made by a host'})

                ('it:exec:udp4', {'subof':'comp', 'fields':'host=it:host,udp4=inet:udp4',
                                  'optfields':'proc=it:exec:proc,time=time',
                                  'doc':'A IPv4/UDP sessoin made by a host'})

                ('it:exec:tcp6', {'subof':'comp', 'fields':'host=it:host,tcp6=inet:tcp6',
                                  'optfields':'proc=it:exec:proc,time=time',
                                  'doc':'A IPv6/TCP session made by a host'})

                ('it:exec:udp6', {'subof':'comp', 'fields':'host=it:host,udp6=inet:udp6',
                                  'optfields':'proc=it:exec:proc,time=time',
                                  'doc':'A IPv6/UDP sessoin made by a host'})
            ),

            'forms':(

                ('it:dev:str', {}, (
                    ('norm', {'ptype':'str', 'ro':1, 'lower':1, 'doc':'Lower case normalized version of it:dev:str'}),
                )),

                ('it:dev:pipe', {}, ()),
                ('it:dev:mutex', {}, ()),
                ('it:dev:regkey', {}, ()),

                ('it:dev:regval', {}, (
                    ('key', {'ptype':'it:reg:key', 'ro':1}),
                    ('val', {'ptype':'it:dev:str', 'ro':1}),
                    ('int', {'ptype':'int', 'ro':1}),
                )),

                ('it:exec:pipe', {}, (
                    ('time', {'ptype':'time', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('name', {'ptype':'it:dev:pipe', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                )),

                ('it:exec:mutex', {}, (
                    ('time', {'ptype':'time', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('name', {'ptype':'it:dev:mutex', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                )),

                ('it:exec:regset', {}, (
                    ('time', {'ptype':'time', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('regval', {'ptype':'it:dev:regval', 'ro':1}),
                )),

                ('it:exec:proc', {}, (
                    ('pid', {'ptype':'int', 'doc':'The process ID'}),
                    ('time', {'ptype':'time', 'doc':'The start time for the process'}),
                    ('host', {'ptype':'it:host', 'doc':'The host which executed the process'}),
                    ('user', {'ptype':'inet:user', 'doc':'The user name of the process owner'}),
                )),

                ('it:exec:url', {}, (
                    ('url', {'ptype':'inet:url', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('time', {'ptype':'time', 'ro':1}),
                )),

                ('it:exec:tcp4', {}, (
                    ('tcp4', {'ptype':'inet:url', 'ro':1}),
                    ('tcp4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                    ('tcp4:port', {'ptype':'inet:port', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('time', {'ptype':'time', 'ro':1}),
                )),

                ('it:exec:udp4', {}, (
                    ('udp4', {'ptype':'inet:url', 'ro':1}),
                    ('udp4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                    ('udp4:port', {'ptype':'inet:port', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('time', {'ptype':'time', 'ro':1}),
                )),

                ('it:exec:tcp6', {}, (
                    ('tcp6', {'ptype':'inet:url', 'ro':1}),
                    ('tcp6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                    ('tcp6:port', {'ptype':'inet:port', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('time', {'ptype':'time', 'ro':1}),
                )),

                ('it:exec:udp6', {}, (
                    ('udp6', {'ptype':'inet:url', 'ro':1}),
                    ('udp6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                    ('udp6:port', {'ptype':'inet:port', 'ro':1}),
                    ('host', {'ptype':'it:host', 'ro':1}),
                    ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                    ('time', {'ptype':'time', 'ro':1}),
                )),

                ('it:exec:file', {}, (
                    ('host', {'ptype': 'it:host', 'ro': 1}),
                    ('proc', {'ptype': 'it:exec:proc', 'ro': 1}),

                    ('path', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),

                    ('time', {'ptype': 'time', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'ro': 1}),

                    # unified / accepted file create/modify/access times
                    ('ctime', {'ptype': 'time', 'doc': 'File creation time'}),
                    ('mtime', {'ptype': 'time', 'doc': 'File modification time'}),
                    ('atime', {'ptype': 'time', 'doc': 'File access time'}),

                    ('user', {'ptype':'inet:user', 'doc':'The owner of the created file'}),
                )),
            ),
        })
