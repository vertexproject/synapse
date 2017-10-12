from synapse.lib.module import CoreModule, modelrev

class ItMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                
                ('it:host', {
                    'subof': 'guid',
                    'doc': 'A GUID that represents a host or system.'}),

                ('it:hostname', {
                    'subof': 'str:lwr',
                    'doc': 'The name of a host or system.'}),

                ('it:hosturl', {
                    'subof': 'comp',
                    'fields': 'host,it:host|url,inet:url',
                    'doc': 'A URL hosted on or served by a host or system.'}),

                ('it:sec:cve', {
                    'subof': 'str:lwr',
                    'regex': '(?i)^CVE-[0-9]{4}-[0-9]{4,}$',
                    'doc': 'A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.',
                    'ex': 'CVE-2012-0158'}),

                ('it:av:sig', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'org,ou:alias|sig,str:lwr',
                    'doc': 'A vendor- or organization-specific antivirus signature name.'}),

                ('it:av:filehit', {
                    'subof': 'sepr',
                    'sep': '/',
                    'fields': 'file,file:bytes|sig,it:av:sig',
                    'doc': 'A file that triggered an alert on an antivirus signature.'}),

                ('it:dev:str', {
                    'subof': 'str',
                    'doc': 'A developer-selected string.'}),

                ('it:dev:int', {
                    'subof': 'int',
                    'doc': 'A developer-selected integer constant.'}),

                ('it:exec:proc', {
                    'subof': 'guid',
                    'doc': 'An instance of a process ("file") executing on a host. May be an actual (e.g., endpoint) or virtual (e.g., malware sandbox) host.'}),

                ('it:exec:subproc', {
                    'subof': 'comp',
                    'fields': 'proc=it:exec:proc,child=it:exec:proc'
                     'doc': 'An instance of a process launching or spawning a subprocess.'}),

                ('it:dev:pipe', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a named pipe.'}),

                ('it:dev:mutex', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a mutex.'}),

                ('it:dev:regkey', {
                    'subof': 'it:dev:str',
                    'doc': 'A Windows registry key.'
                    'ex': 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'}),

                ('it:dev:regval', {
                    'subof': 'comp',
                    'fields': 'key=it:dev:regkey',
                    'optfields': 'str=it:dev:str,int=it:dev:int,bytes=file:bytes',
                    'doc': 'A Windows registry key/value pair.'}),
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
                ]),

                ('it:dev:str', {}, (
                    ('norm', {'ptype': 'str', 'ro': 1, 'lower': 1, 'doc': 'Lower case normalized version of it:dev:str'}),
                )),

                ('it:dev:int', {}, (
                )),

                ('it:dev:pipe', {}, ()),
                ('it:dev:mutex', {}, ()),
                ('it:dev:regkey', {}, ()),

                ('it:dev:regval', {}, (
                    ('key', {'ptype': 'it:dev:regkey', 'ro': 1}),
                    ('str', {'ptype': 'it:dev:str', 'ro': 1}),
                    ('int', {'ptype': 'it:dev:int', 'ro': 1}),
                    ('bytes', {'ptype': 'file:bytes', 'ro': 1}),
                )),

                ('it:exec:pipe', {'ptype': 'guid'}, (
                    ('time', {'ptype': 'time'}),
                    ('host', {'ptype': 'it:host'}),
                    ('name', {'ptype': 'it:dev:pipe'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code which created the pipe'}),
                )),

                ('it:exec:mutex', {'ptype': 'guid'}, (
                    ('time', {'ptype': 'time'}),
                    ('host', {'ptype': 'it:host'}),
                    ('name', {'ptype': 'it:dev:mutex'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code which created the mutex'}),
                )),

                ('it:exec:proc', {'ptype': 'guid'}, (
                    ('pid', {'ptype': 'int', 'doc': 'The process ID'}),
                    ('time', {'ptype': 'time', 'doc': 'The start time for the process'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host which executed the process'}),
                    ('user', {'ptype': 'inet:user', 'doc': 'The user name of the process owner'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file considered the "main" executable for the process'}),
                    ('cmd', {'ptype': 'str', 'doc': 'The command string for the process'}),
                )),

                ('it:exec:subproc', {}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The parent process'}),
                    ('child', {'ptype': 'it:exec:proc', 'doc': 'The child process'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host which executed the process'}),
                )),

                ('it:exec:url', {'ptype': 'guid'}, (
                    ('url', {'ptype': 'inet:url'}),
                    ('host', {'ptype': 'it:host'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),

                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code which retrieved the URL'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address of the host during URL retrieval'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 address of the host during URL retrieval'}),
                )),

                ('it:exec:bind:tcp', {'ptype': 'guid'}, (
                    ('port', {'ptype': 'inet:port', 'doc': 'The bound TCP port'}),

                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The (optional) IPv4 specified to bind()'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The (optional) IPv6 specified to bind()'}),
                    ('host', {'ptype': 'it:host'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),

                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code which bound the listener'}),
                )),

                ('it:exec:bind:udp', {'ptype': 'guid'}, (
                    ('port', {'ptype': 'inet:port', 'doc': 'The bound UDP port'}),

                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The (optional) IPv4 specified to bind()'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The (optional) IPv6 specified to bind()'}),
                    ('host', {'ptype': 'it:host'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),

                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code which bound the listener'}),
                )),

                ('it:fs:file', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),

                    ('path', {'ptype': 'file:path'}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes'}),

                    ('ctime', {'ptype': 'time', 'doc': 'File creation time'}),
                    ('mtime', {'ptype': 'time', 'doc': 'File modification time'}),
                    ('atime', {'ptype': 'time', 'doc': 'File access time'}),

                    ('user', {'ptype': 'inet:user', 'doc': 'The owner of the file'}),
                    ('group', {'ptype': 'inet:user', 'doc': 'The group owner of the file'}),
                )),

                # FIXME seed for hex file bytes
                ('it:exec:file:add', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('path', {'ptype': 'file:path'}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes'}),
                    ('time', {'ptype': 'time'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing the code that created the file'}),

                )),

                ('it:exec:file:del', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('path', {'ptype': 'file:path'}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes'}),
                    ('time', {'ptype': 'time'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing the code that deleted the file'}),

                )),

                ('it:exec:file:read', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('path', {'ptype': 'file:path'}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes'}),
                    ('time', {'ptype': 'time'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing the code that read the file'}),

                )),

                ('it:exec:file:write', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('path', {'ptype': 'file:path'}),
                    ('path:dir', {'ptype': 'file:path', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes'}),
                    ('time', {'ptype': 'time'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing the code that wrote to the file'}),

                )),

                ('it:exec:reg:get', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('reg', {'ptype': 'it:dev:regval'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'ro': 1}),
                    ('exe', {'ptype': 'file:bytes'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),
                )),

                ('it:exec:reg:set', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('reg', {'ptype': 'it:dev:regval'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'ro': 1}),
                    ('exe', {'ptype': 'file:bytes'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),
                )),

                ('it:exec:reg:del', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host'}),
                    ('reg', {'ptype': 'it:dev:regval'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'ro': 1}),
                    ('exe', {'ptype': 'file:bytes'}),
                    ('proc', {'ptype': 'it:exec:proc'}),
                    ('time', {'ptype': 'time'}),
                )),
            ),

        }

        models = (
            ('it', modl),
        )

        return models

    def initCoreModule(self):
        self.onFormNode('it:dev:str', self._onFormItDevStr)

    def _onFormItDevStr(self, form, valu, props, mesg):
        props['it:dev:str:norm'] = valu.lower()
