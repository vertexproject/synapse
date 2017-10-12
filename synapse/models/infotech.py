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
                    'fields': 'proc=it:exec:proc,child=it:exec:proc',
                    'doc': 'A process that launches a subprocess.'}),

                ('it:dev:pipe', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a named pipe.'}),

                ('it:dev:mutex', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a mutex.'}),

                ('it:dev:regkey', {
                    'subof': 'it:dev:str',
                    'doc': 'A Windows registry key.',
                    'ex': 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'}),

                ('it:dev:regval', {
                    'subof': 'comp',
                    'fields': 'key=it:dev:regkey',
                    'optfields': 'str=it:dev:str,int=it:dev:int,bytes=file:bytes',
                    'doc': 'A Windows registry key/value pair.'}),
            ),

            'forms': (

                ('it:host', {}, [
                    ('name', {'ptype': 'it:hostname', 'doc': 'The name of the host or system.'}),
                    ('desc', {'ptype': 'str:txt', 'doc': 'A free-form description of the host.'}),

                    # FIXME we probably eventually need a bunch of stuff here...
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The last known ipv4 address for the host.'}),
                ]),

                ('it:hostname', {}, ()),

                ('it:sec:cve', {'ptype': 'it:sec:cve'}, [
                    ('desc', {'ptype': 'str', 'doc': 'A free-form description of the CVE vulnerability.'}),
                ]),

                ('it:av:sig', {'ptype': 'it:av:sig'}, [
                    ('sig', {'ptype': 'str:lwr', 'doc': 'The signature name.', 'ro': 1}),
                    ('org', {'ptype': 'ou:alias', 'doc': 'The organization responsible for the signature.', 'ro': 1}),
                    ('desc', {'ptype': 'str', 'doc': 'A free-form description of the signature.'}),
                    ('url', {'ptype': 'inet:url', 'doc': 'A reference URL for information about the signature.'}),
                ]),

                ('it:av:filehit', {'ptype': 'it:av:filehit'}, [
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that triggered the signature hit.'}),
                    ('sig', {'ptype': 'it:av:sig', 'doc': 'The signature that the file triggered on.'}),
                ]),

                ('it:dev:str', {}, (
                    ('norm', {'ptype': 'str', 'ro': 1, 'lower': 1, 'doc': 'Lower case normalized version of it:dev:str'}),
                )),

                ('it:dev:int', {}, ()),

                ('it:dev:pipe', {}, ()),

                ('it:dev:mutex', {}, ()),

                ('it:dev:regkey', {}, ()),

                ('it:dev:regval', {}, (
                    ('key', {'ptype': 'it:dev:regkey', 'doc': 'The Windows registry key.', 'ro': 1}),
                    ('str', {'ptype': 'it:dev:str', 'doc': 'The value of the registry key, if the value is a string.', 'ro': 1}),
                    ('int', {'ptype': 'it:dev:int', 'doc': 'The value of the registry key, if the value is an integer.', 'ro': 1}),
                    ('bytes', {'ptype': 'file:bytes', 'doc': 'The file representing the value of the registry key, if the value is binary data.', 'ro': 1}),
                )),

                ('it:exec:proc', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host', 'doc': 'The host that executed the process.'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file considered the "main" executable for the process.'}),
                    ('cmd', {'ptype': 'str', 'doc': 'The command string for the process.'}),
                    ('pid', {'ptype': 'int', 'doc': 'The process ID.'}),
                    ('time', {'ptype': 'time', 'doc': 'The start time for the process.'}),
                    ('user', {'ptype': 'inet:user', 'doc': 'The user name of the process owner.'}),
                )),

                ('it:exec:subproc', {}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The parent process'}),
                    ('child', {'ptype': 'it:exec:proc', 'doc': 'The child process'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host which executed the process'}),
                )),

                ('it:exec:pipe', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that created the named pipe.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that created the named pipe (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that created the named pipe (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the named pipe was created.'}),
                    ('name', {'ptype': 'it:dev:pipe', 'doc': 'The named pipe string.'}),
                )),

                ('it:exec:mutex', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that created the mutex.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that created the mutex (parsed :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that created the mutex (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the mutex was created.'}),
                    ('name', {'ptype': 'it:dev:mutex', 'doc': 'The mutex string.'}),
                )),

                ('it:exec:url', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that requested the URL.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that requested the URL (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that requested the URL (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the URL was requested.'}),
                    ('url', {'ptype': 'inet:url', 'doc': 'The URL that was requested.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address of the host during URL retrieval.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 address of the host during URL retrieval.'}),
                )),

                ('it:exec:bind:tcp', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that bound the listening TCP port.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that bound the port (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that bound the port (parsed form :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the port was bound.'}),
                    ('port', {'ptype': 'inet:port', 'doc': 'The bound (listening) TCP port.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address specified to bind().'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 specified to bind().'}),
                )),

                ('it:exec:bind:udp', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that bound the listening UDP port.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that bound the port (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that bound the port (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the port was bound.'}),
                    ('port', {'ptype': 'inet:port', 'doc': 'The bound (listening) UDP port.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 specified to bind().'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 specified to bind().'}),
                )),

                ('it:fs:file', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host', 'doc': 'The host containing the file.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path for the file.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file on the host.'}),
                    ('ctime', {'ptype': 'time', 'doc': 'The file creation time.'}),
                    ('mtime', {'ptype': 'time', 'doc': 'The file modification time.'}),
                    ('atime', {'ptype': 'time', 'doc': 'The file access time.'}),
                    ('user', {'ptype': 'inet:user', 'doc': 'The owner of the file.'}),
                    ('group', {'ptype': 'inet:user', 'doc': 'The group owner of the file.'}),
                )),

                # FIXME seed for hex file bytes

                ('it:exec:file:add', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that created the new file.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that created the new file (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that created the new file.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was created.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was created.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was created.'}),
                )),

                ('it:exec:file:del', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that deleted the file.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that deleted the file (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that deleted the file (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was deleted.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was deleted.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was deleted.'}),
                )),

                ('it:exec:file:read', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that read the file.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that read the file (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that read the file (paresd from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was read.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was read.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was read.'}),
                )),

                ('it:exec:file:write', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that wrote to / modified the existing file.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that wrote to the file (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that wrote to the file (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was written to / modified.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was modified.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base' 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was modified.'}),
                )),

                ('it:exec:reg:get', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that read the registry.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that read the registry (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that read the registry (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the registry was read.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was read.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was read (parsed from :reg).', 'ro': 1}),
                )),

                ('it:exec:reg:set', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that wrote to the registry.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that wrote to the registry (pasrsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that wrote to the registry (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the registry was written to.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was written.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was written (parsed from :reg).', 'ro': 1}),
                )),

                ('it:exec:reg:del', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The process executing code that deleted data from the registry.'}),
                    ('host', {'ptype': 'it:host', 'doc': 'The host running the process that deleted data from the registry (parsed from :proc).'}),
                    ('exe', {'ptype': 'file:bytes', 'doc': 'The file containing code that deleted data from the registry (parsed from :proc).'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the data from the registry was deleted.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was deleted.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was deleted (parsed from :reg).', 'ro': 1}),
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
