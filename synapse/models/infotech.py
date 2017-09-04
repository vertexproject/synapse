import synapse.common as s_common

from synapse.eventbus import on
from synapse.lib.module import CoreModule, modelrev

class ItMod(CoreModule):

    @staticmethod
    def getBaseModels():

        models = (

            ( 'it', 0, {

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
            }),

            ('it', 201708161120, {

                'types':(

                    ('it:dev:str', {'subof':'str', 'doc':'A developer selected string'}),
                    ('it:dev:int', {'subof':'int', 'doc':'A developer selected int constant'}),

                    ('it:dev:filestr', {'subof':'comp', 'fields':'file=file:bytes,str=it:dev:str'}),
                    #('it:dev:encstr', {'subof':'comp', 'fields':'encoded=it:dev:str,dec=it:dev:str,codec'})

                    ('it:exec:proc', {'subof':'guid', 'doc':'A unique process execution on a host'}),
                    ('it:exec:subproc', {'subof':'comp', 'fields':'proc=it:exec:proc,child=it:exec:proc'}),

                    ('it:dev:pipe', {'subof':'it:dev:str', 'doc':'A  named pipe string'}),
                    ('it:dev:mutex', {'subof':'it:dev:str', 'doc':'A named mutex string'}),
                    ('it:dev:regkey', {'subof':'it:dev:str', 'doc':'A windows registry key string'}),

                    ('it:dev:regval', {'subof':'comp', 'fields':'key=it:dev:regkey',
                                       'optfields':'str=it:dev:str,int=int,bytes=file:bytes',
                                       'doc':'A windows registry key/val pair'}),

                    ('it:fs:file', {'subof':'comp', 'fields':'host=it:host',
                                      'optfields':'path=file:path,file=file:bytes',
                                      'doc':'A file instance on a host filesystem'}),

                    # TODO filesystem specific metadata... ( it:fs:ntfs:file )

                    ('it:exec:file:create', {'subof':'comp', 'fields':'host=it:host',
                                      'optfields':'path=file:path,file=file:bytes,time=time,exe=file:bytes,proc=it:exec:proc',
                                      'doc':'A file create event on a host'}),

                    ('it:exec:file:delete', {'subof':'comp', 'fields':'host=it:host',
                                      'optfields':'path=file:path,file=file:bytes,time=time,exe=file:bytes,proc=it:exec:proc',
                                      'doc':'A file delete event on a host'}),

                    ('it:exec:file:read', {'subof':'comp', 'fields':'host=it:host',
                                      'optfields':'path=file:path,file=file:bytes,time=time,exe=file:bytes,proc=it:exec:proc',
                                      'doc':'A file read event on a host'}),

                    ('it:exec:file:write', {'subof':'comp', 'fields':'host=it:host',
                                      'optfields':'path=file:path,file=file:bytes,time=time,exe=file:bytes,proc=it:exec:proc',
                                      'doc':'A file write event on a host'}),

                    ('it:exec:pipe', {'subof':'comp', 'fields':'host=it:host,name=it:dev:pipe',
                                       'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A named pipe instance created on a host'}),

                    ('it:exec:mutex', {'subof':'comp', 'fields':'host=it:host,name=it:dev:mutex',
                                       'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                       'doc':'A named mutex instance created on a host'}),

                    ('it:exec:url', {'subof':'comp', 'fields':'host=it:host,url=inet:url',
                                     'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                     'doc':'A IPv4/TCP session made by a host'}),

                    ('it:exec:dns:a', {'subof':'comp', 'fields':'host=it:host,fqdn=inet:fqdn',
                                     'optfields':'answ=inet:ipv4,exe=file:bytes,proc=it:exec:proc,time=time',
                                     'doc':'A DNS A lookup made by a host'}),

                    ('it:exec:dns:mx', {'subof':'comp', 'fields':'host=it:host,fqdn=inet:fqdn',
                                     'optfields':'answ=inet:fqdn,exe=file:bytes,proc=it:exec:proc,time=time',
                                     'doc':'A DNS MX lookup made by a host'}),

                    ('it:exec:dns:ns', {'subof':'comp', 'fields':'host=it:host,fqdn=inet:fqdn',
                                     'optfields':'answ=inet:fqdn,exe=file:bytes,proc=it:exec:proc,time=time',
                                     'doc':'A DNS NS lookup made by a host'}),

                    ('it:exec:dns:rev4', {'subof':'comp', 'fields':'host=it:host,ipv4=inet:ipv4',
                                     'optfields':'answ=inet:fqdn,exe=file:bytes,proc=it:exec:proc,time=time',
                                     'doc':'A normalized PTR lookup made by a host'}),

                    ('it:exec:conn:tcp4', {'subof':'comp', 'fields':'host=it:host,tcp4=inet:tcp4',
                                      'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A IPv4/TCP session made by a host'}),

                    ('it:exec:conn:udp4', {'subof':'comp', 'fields':'host=it:host,udp4=inet:udp4',
                                      'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A IPv4/UDP session made by a host'}),

                    ('it:exec:conn:tcp6', {'subof':'comp', 'fields':'host=it:host,tcp6=inet:tcp6',
                                      'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A IPv6/TCP session made by a host'}),

                    ('it:exec:conn:udp6', {'subof':'comp', 'fields':'host=it:host,udp6=inet:udp6',
                                      'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A IPv6/UDP session made by a host'}),

                    ('it:exec:bind:tcp', {'subof':'comp', 'fields':'host=it:host,port=inet:port',
                                      'optfields':'ipv4=inet:ipv4,ipv6=inet:ipv6,exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A TCP bound listener on a host'}),

                    ('it:exec:bind:udp', {'subof':'comp', 'fields':'host=it:host,port=inet:port',
                                      'optfields':'ipv4=inet:ipv4,ipv6=inet:ipv6,exe=file:bytes,proc=it:exec:proc,time=time',
                                      'doc':'A UDP bound listener on a host'}),

                    ('it:exec:reg:get', {'subof':'comp', 'fields':'host=it:host,regval=it:dev:regval',
                                        'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                        'doc':'A registry value read on a host'}),

                    ('it:exec:reg:set', {'subof':'comp', 'fields':'host=it:host,regval=it:dev:regval',
                                        'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                        'doc':'A registry value set on a host'}),

                    ('it:exec:reg:del', {'subof':'comp', 'fields':'host=it:host,regval=it:dev:regval',
                                        'optfields':'exe=file:bytes,proc=it:exec:proc,time=time',
                                        'doc':'A registry value deleted on a host'}),
                ),

                'forms':(

                    ('it:dev:str', {}, (
                        # make hex str based file:bytes ctor
                        ('norm', {'ptype':'str', 'ro':1, 'lower':1, 'doc':'Lower case normalized version of it:dev:str'}),
                    )),

                    ('it:dev:int', {}, (
                    )),

                    ('it:dev:pipe', {}, ()),
                    ('it:dev:mutex', {}, ()),
                    ('it:dev:regkey', {}, ()),

                    ('it:dev:regval', {}, (
                        ('key', {'ptype':'it:reg:key', 'ro':1}),
                        ('str', {'ptype':'it:dev:str', 'ro':1}),
                        ('int', {'ptype':'int', 'ro':1}),
                        ('bytes', {'ptype':'file:bytes', 'ro':1}),
                    )),

                    ('it:exec:pipe', {}, (
                        ('time', {'ptype':'time', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('name', {'ptype':'it:dev:pipe', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the pipe'}),
                    )),

                    ('it:exec:mutex', {}, (
                        ('time', {'ptype':'time', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('name', {'ptype':'it:dev:mutex', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the mutex'}),
                    )),

                    ('it:exec:reg:set', {}, (
                        ('time', {'ptype':'time', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('regval', {'ptype':'it:dev:regval', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which set the registry value'}),
                    )),

                    ('it:exec:proc', {}, (
                        ('pid', {'ptype':'int', 'doc':'The process ID'}),
                        ('time', {'ptype':'time', 'doc':'The start time for the process'}),
                        ('host', {'ptype':'it:host', 'doc':'The host which executed the process'}),
                        ('user', {'ptype':'inet:user', 'doc':'The user name of the process owner'}),
                        ('exe', {'ptype':'file:bytes', 'doc':'The file considered the "main" executable for the process'}),
                    )),

                    ('it:exec:subproc', {}, (
                        ('proc', {'ptype':'it:exec:proc', 'ro':1, 'doc':'The parent process'}),
                        ('child', {'ptype':'it:exec:proc', 'ro':1, 'doc':'The child process'}),
                        ('host', {'ptype':'it:host', 'doc':'The host which executed the process'}),
                    )),

                    ('it:exec:url', {}, (
                        ('url', {'ptype':'inet:url', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which retrieved the URL'}),
                        ('ipv4', {'ptype':'inet:ipv4', 'doc':'The IPv4 address of the host during URL retrieval'}),
                        ('ipv6', {'ptype':'inet:ipv6', 'doc':'The IPv6 address of the host during URL retrieval'}),
                    )),

                    ('it:exec:conn:tcp4', {}, (
                        ('tcp4', {'ptype':'inet:tcp4', 'ro':1}),
                        ('tcp4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                        ('tcp4:port', {'ptype':'inet:port', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('src4', {'ptype':'inet:srv4', 'ro':0}),
                        ('src4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                        ('src4:port', {'ptype':'inet:port', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the TCPv4 session'}),
                    )),

                    ('it:exec:conn:udp4', {}, (
                        ('udp4', {'ptype':'inet:udp4', 'ro':1}),
                        ('udp4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                        ('udp4:port', {'ptype':'inet:port', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('src4', {'ptype':'inet:srv4', 'ro':0}),
                        ('src4:ipv4', {'ptype':'inet:ipv4', 'ro':1}),
                        ('src4:port', {'ptype':'inet:port', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the UDPv4 session'}),
                    )),

                    ('it:exec:conn:tcp6', {}, (
                        ('tcp6', {'ptype':'inet:tcp6', 'ro':1}),
                        ('tcp6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                        ('tcp6:port', {'ptype':'inet:port', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('src6', {'ptype':'inet:srv6', 'ro':0}),
                        ('src6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                        ('src6:port', {'ptype':'inet:port', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the TCPv6 session'}),
                    )),

                    ('it:exec:conn:udp6', {}, (
                        ('udp6', {'ptype':'inet:udp6', 'ro':1}),
                        ('udp6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                        ('udp6:port', {'ptype':'inet:port', 'ro':1}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('src6', {'ptype':'inet:srv6', 'ro':0}),
                        ('src6:ipv6', {'ptype':'inet:ipv6', 'ro':1}),
                        ('src6:port', {'ptype':'inet:port', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which created the UDPv6 session'}),
                    )),

                    ('it:exec:bind:tcp', {}, (
                        ('port', {'ptype':'inet:port', 'ro':1, 'doc':'The bound TCP port'}),

                        ('ipv4', {'ptype':'inet:ipv4', 'ro':1, 'doc':'The (optional) IPv4 specified to bind()'}),
                        ('ipv6', {'ptype':'inet:ipv6', 'ro':1, 'doc':'The (optional) IPv6 specified to bind()'}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which bound the listener'}),
                    )),

                    ('it:exec:bind:udp', {}, (
                        ('port', {'ptype':'inet:port', 'ro':1, 'doc':'The bound UDP port'}),

                        ('ipv4', {'ptype':'inet:ipv4', 'ro':1, 'doc':'The (optional) IPv4 specified to bind()'}),
                        ('ipv6', {'ptype':'inet:ipv6', 'ro':1, 'doc':'The (optional) IPv6 specified to bind()'}),
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),

                        ('exe', {'ptype':'file:bytes', 'doc':'The file containing code which bound the listener'}),
                    )),

                    ('it:fs:file', {}, (
                        ('host', {'ptype': 'it:host', 'ro': 1}),

                        ('path', {'ptype': 'file:path', 'ro': 1}),
                        ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                        ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                        ('path:base', {'ptype': 'file:base', 'ro': 1}),
                        ('file', {'ptype': 'file:bytes', 'ro': 1}),

                        # unified / accepted file create/modify/access times
                        ('ctime', {'ptype': 'time', 'doc': 'File creation time'}),
                        ('mtime', {'ptype': 'time', 'doc': 'File modification time'}),
                        ('atime', {'ptype': 'time', 'doc': 'File access time'}),

                        ('user', {'ptype':'inet:user', 'doc':'The owner of the file'}),
                        ('group', {'ptype':'inet:user', 'doc':'The group owner of the file'}),
                    )),

                    # FIXME seed for hex file bytes
                    ('it:exec:file:create', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('path', {'ptype':'file:path', 'ro':1}),
                        ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                        ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                        ('path:base', {'ptype': 'file:base', 'ro': 1}),
                        ('file', {'ptype':'file:bytes', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype': 'file:bytes', 'ro':1, 'doc':'The file containing the code that created the file'}),

                    )),

                    ('it:exec:file:delete', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('path', {'ptype':'file:path', 'ro':1}),
                        ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                        ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                        ('path:base', {'ptype': 'file:base', 'ro': 1}),
                        ('file', {'ptype':'file:bytes', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype': 'file:bytes', 'ro':1, 'doc':'The file containing the code that deleted the file'}),

                    )),

                    ('it:exec:file:read', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('path', {'ptype':'file:path', 'ro':1}),
                        ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                        ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                        ('path:base', {'ptype': 'file:base', 'ro': 1}),
                        ('file', {'ptype':'file:bytes', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype': 'file:bytes', 'ro':1, 'doc':'The file containing the code that read the file'}),

                    )),

                    ('it:exec:file:write', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('path', {'ptype':'file:path', 'ro':1}),
                        ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                        ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                        ('path:base', {'ptype': 'file:base', 'ro': 1}),
                        ('file', {'ptype':'file:bytes', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('exe', {'ptype': 'file:bytes', 'ro':1, 'doc':'The file containing the code that wrote to the file'}),

                    )),

                    ('it:exec:reg:get', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('regval', {'ptype':'it:dev:regval', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                    )),

                    ('it:exec:reg:set', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('regval', {'ptype':'it:dev:regval', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                    )),

                    ('it:exec:reg:del', {}, (
                        ('host', {'ptype':'it:host', 'ro':1}),
                        ('regval', {'ptype':'it:dev:regval', 'ro':1}),
                        ('exe', {'ptype':'file:bytes', 'ro':1}),
                        ('proc', {'ptype':'it:exec:proc', 'ro':1}),
                        ('time', {'ptype':'time', 'ro':1}),
                    )),
                ),
            }),
        )
        return models

    @on('node:form', form='it:dev:str')
    def _onFormItDevStr(self, mesg):
        props = mesg[1].get('props')
        props['it:dev:str:norm'] = mesg[1].get('valu').lower()

    @on('node:form', form='it:exec:file:create')
    def _onFormFileCreate(self, mesg):

        props = mesg[1].get('props')

        byts = props.get('it:exec:file:create:file')
        if byts is None:
            return

        path = props.get('it:exec:file:create:path')
        if path is None:
            return

        self.core.formTufoByProp('file:filepath', (byts,path))

    @on('node:form', form='it:exec:file:delete')
    def _onFormFileCreate(self, mesg):

        props = mesg[1].get('props')

        byts = props.get('it:exec:file:delete:file')
        if byts is None:
            return

        path = props.get('it:exec:file:delete:path')
        if path is None:
            return

        self.core.formTufoByProp('file:filepath', (byts,path))

    @on('node:form', form='it:exec:file:read')
    def _onFormFileCreate(self, mesg):

        props = mesg[1].get('props')

        byts = props.get('it:exec:file:read:file')
        if byts is None:
            return

        path = props.get('it:exec:file:read:path')
        if path is None:
            return

        self.core.formTufoByProp('file:filepath', (byts,path))

    @on('node:form', form='it:exec:file:write')
    def _onFormFileCreate(self, mesg):

        props = mesg[1].get('props')

        byts = props.get('it:exec:file:write:file')
        if byts is None:
            return

        path = props.get('it:exec:file:write:path')
        if path is None:
            return

        self.core.formTufoByProp('file:filepath', (byts,path))
