# stdlib
import logging
# third party code
# custom code
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

class SemVer(s_types.Type):
    '''
    Provides support for parsing a semantic version string into its component
    parts. This normalizes a version string into a integer to allow version
    ordering.  Prerelease information is disregarded for integer comparison
    purposes, as we cannot map an arbitrary pre-release version into a integer
    value

    Major, minor and patch levels are represented as integers, with a max
    width of 20 bits.  The comparable integer value representing the semver
    is the bitwise concatenation of the major, minor and patch levels.

    Prerelease and build information will be parsed out and available as
    strings if that information is present.
    '''
    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyStr(self, valu):
        valu = valu.strip()
        if not valu:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='No text left after stripping whitespace')

        subs = s_version.parseSemver(valu)
        if subs is None:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='Unable to parse string as a semver.')
        valu = s_version.packVersion(subs.get('major'), subs.get('minor'), subs.get('patch'))
        return valu, {'subs': subs}

    def _normPyInt(self, valu):
        if valu < 0:
            raise s_exc.BadTypeValu(valu=valu, mesg='Cannot norm a negative integer as a semver.')
        if valu > s_version.mask60:
            raise s_exc.BadTypeValu(valu=valu,
                               mesg='Cannot norm a integer larger than 1152921504606846975 as a semver.')
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.packVersion(major, minor, patch)
        subs = {'major': major,
                'minor': minor,
                'patch': patch}
        return valu, {'subs': subs}

    def repr(self, valu, defval=None):
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.fmtVersion(major, minor, patch)
        return valu

    def indx(self, valu):
        return valu.to_bytes(8, 'big')

class ItModule(s_module.CoreModule):
    def initCoreModule(self):
        self.model.form('it:dev:str').onAdd(self._onFormItDevStr)
        self.model.form('it:dev:pipe').onAdd(self._onFormMakeDevStr)
        self.model.form('it:dev:mutex').onAdd(self._onFormMakeDevStr)
        self.model.form('it:dev:regkey').onAdd(self._onFormMakeDevStr)
        self.model.prop('it:prod:softver:arch').onSet(self._onPropSoftverArch)
        self.model.prop('it:prod:softver:vers').onSet(self._onPropSoftverVers)
        self.model.prop('it:prod:softver:software').onSet(self._onPropSoftverSoft)

    def bruteVersionStr(self, valu):
        '''
        Brute force the version out of a string.

        Args:
            valu (str): String to attempt to get version information for.

        Notes:
            This first attempts to parse strings using the it:semver normalization
            before attempting to extract version parts out of the string.

        Returns:
            int, dict: The system normalized version integer and a subs dictionary.
        '''
        try:
            valu, info = self.core.model.type('it:semver').norm(valu)
            subs = info.get('subs')
            return valu, subs
        except s_exc.BadTypeValu:
            # Try doing version part extraction by noming through the string
            subs = s_version.parseVersionParts(valu)
            if subs is None:
                raise s_exc.BadTypeValu(valu=valu,
                                           mesg='Unable to brute force version parts out of the string')
            if subs:
                valu = s_version.packVersion(subs.get('major'),
                                             subs.get('minor', 0),
                                             subs.get('patch', 0))
                return valu, subs

    def _onFormItDevStr(self, node):
        node.set('norm', node.ndef[1])

    def _onFormMakeDevStr(self, node):
        pprop = node.ndef[1]
        nnode = node.snap.addNode('it:dev:str', pprop)

    def _onPropSoftverSoft(self, node, oldv):
        # Check to see if name is available and set it if possible
        prop = node.get('software')
        if prop:
            snodes = list(node.snap.getNodesBy('it:prod:soft', prop))
            if snodes:
                name = snodes[0].get('name')
                if name:
                    node.set('software:name', name)

    def _onPropSoftverArch(self, node, oldv):
        # make it:dev:str for arch
        prop = node.get('arch')
        if prop:
            nnode = node.snap.addNode('it:dev:str', prop)

    def _onPropSoftverVers(self, node, oldv):
        # Set vers:norm and make it's normed valu
        prop = node.get('vers')
        if not prop:
            return

        node.set('vers:norm', prop)

        # Make it:dev:str from version str
        nnode = node.snap.addNode('it:dev:str', prop)

        # form the semver properly or bruteforce parts
        try:
            valu, subs = self.bruteVersionStr(prop)
            node.set('semver', valu)
            for k, v in subs.items():
                node.set(f'semver:{k}', v)
        except Exception as e:
            logger.exception('Failed to brute force version string [%s]', prop)

    def getModelDefs(self):
        modl = {
            'ctors': (
                ('it:semver', 'synapse.models.infotech.SemVer', {}, {
                    'doc': 'Semantic Version type',
                }),
            ),
            'types': (
                ('it:hostname', ('str', {'strip': True, 'lower': True}), {
                    'doc': 'The name of a host or sytsem',
                }),
                ('it:host', ('guid', {}), {
                    'doc': 'A GUID that represents a host or system.'
                }),
                ('it:hosturl', ('comp', {'fields': (('host', 'it:host'), ('url', 'inet:url'))}), {
                    'doc': 'A url hosted on or served by a host or system.',
                }),
                # TODO We probably want a cve to be linked to a softver via comp type
                ('it:sec:cve', ('str', {'lower': True, 'regex': r'(?i)^CVE-[0-9]{4}-[0-9]{4,}$'}), {
                    'doc': 'A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.',
                    'ex': 'cve-2012-0158'
                }),
                ('it:dev:str', ('str', {}), {
                    'doc': 'A developer-selected string.'
                }),
                ('it:dev:pipe', ('str', {}), {
                    'doc': 'A string representing a named pipe.',
                }),
                ('it:dev:mutex', ('str', {}), {
                    'doc': 'A string representing a mutex.',
                }),
                ('it:dev:int', ('int', {}), {
                    'doc': 'A developer selected integer constant.',
                }),
                ('it:dev:regkey', ('str', {}), {
                    'doc': 'A Windows registry key.',
                    'ex': 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run',
                }),
                ('it:dev:regval', ('guid', {}), {
                    'doc': 'A Windows registry key/value pair.',
                }),
                ('it:prod:soft', ('guid', {}), {
                    'doc': 'A arbitrary, unversioned software product.',
                }),
                ('it:prod:softver', ('guid', {}), {
                    'doc': 'A version of a particular software product.'
                }),
                ('it:hostsoft', ('comp', {'fields': (('host', 'it:host'), ('softver', 'it:prod:softver'))}), {
                   'doc': 'A version of a software product which is present on a given host.',
                }),
                ('it:av:sig', ('comp', {'fields': (('soft', 'it:prod:soft'), ('name', ('str', {'lower': True})))}), {
                   'doc': 'A signature name within the namespace of an antivirus engine name.'
                }),
                ('it:av:filehit', ('comp', {'fields': (('file', 'file:bytes'), ('sig', 'it:av:sig'))}), {
                    'doc': 'A file that triggered an alert on a specific antivirus signature.',
                }),
                ('it:auth:passwdhash', ('guid', {}), {
                    'doc': 'An instance of a password hash',
                }),
                ('it:exec:proc', ('guid', {}), {
                    'doc': 'A process executing on a host. May be an actual (e.g., endpoint) or virtual (e.g., malware sandbox) host.',
                }),
                ('it:exec:mutex', ('guid', {}), {
                    'doc': 'A mutex created by a process at runtime.',
                }),
                ('it:exec:pipe', ('guid', {}), {
                    'doc': 'A named pipe created by a process at runtime.',
                }),
                ('it:exec:url', ('guid', {}), {
                    'doc': 'A instance of a host requesting a URL.',
                }),
                ('it:exec:bind', ('guid', {}), {
                    'doc': 'An instance of a host binding a listening port.',
                }),
                ('it:fs:file', ('guid', {}), {
                    'doc': 'A file on a host.'
                }),
                ('it:exec:file:add', ('guid', {}), {
                    'doc': 'An instance of a host adding a file to a filesystem.',
                }),
                ('it:exec:file:del', ('guid', {}), {
                    'doc': 'An instance of a host deleting a file from a filesystem.',
                }),
                ('it:exec:file:read', ('guid', {}), {
                    'doc': 'An instance of a host reading a file from a filesystem.',
                }),
                ('it:exec:file:write', ('guid', {}), {
                    'doc': 'An instance of a host writing a file to a filesystem.',
                }),
                ('it:exec:reg:get', ('guid', {}), {
                    'doc': 'An instance of a host getting a registry key.',
                }),
                ('it:exec:reg:set', ('guid', {}), {
                    'doc': 'An instance of a host creating or setting a registry key',
                }),
                ('it:exec:reg:del', ('guid', {}), {
                    'doc': 'An instance of a host deleting a registry key.',
                })
            ),
            'forms': (
                ('it:hostname', {}, ()),
                ('it:host', {}, (
                    ('name', ('it:hostname', {}), {
                        'doc': 'The name of the host or system.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the host.',
                    }),
                    #  FIXME we probably eventually need a bunch of stuff here...
                    ('ipv4', ('inet:ipv4', {}), {
                        'doc': 'The last known ipv4 address for the host.'
                    }),
                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The last known location for the host.'
                    }),
                )),
                ('it:hosturl', {}, (
                    ('host', ('it:host', {}), {
                        'ro': True,
                        'doc': 'Host serving a url.',
                    }),
                    ('url', ('inet:url', {}), {
                        'ro': True,
                        'doc': 'URL available on the host.',
                    }),
                )),
                ('it:dev:str', {}, (
                    ('norm', ('str', {'lower': True}), {
                        'doc': 'Lower case normalized version of the it:dev:str.',
                    }),
                )),
                ('it:sec:cve', {}, (
                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the CVE vulnerability.',
                    }),
                )),
                ('it:dev:int', {}, ()),
                ('it:dev:pipe', {}, ()),
                ('it:dev:mutex', {}, ()),
                ('it:dev:regkey', {}, ()),
                ('it:dev:regval', {}, (
                    ('key', ('it:dev:regkey', {}), {
                        'doc': 'The Windows registry key.',
                    }),
                    ('str', ('it:dev:str', {}), {
                        'doc': 'The value of the registry key, if the value is a string.',
                    }),
                    ('int', ('it:dev:int', {}), {
                        'doc': 'The value of the registry key, if the value is an integer.',
                    }),
                    ('bytes', ('file:bytes', {}), {
                        'doc': 'The file representing the value of the registry key, if the value is binary data.',
                    }),
                )),
                ('it:prod:soft', {}, (
                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Name of the software.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the software.',
                    }),
                    ('desc:short', ('str', {'lower': True}), {
                        'doc': 'A short description of the software.',
                    }),
                    ('author:org', ('ou:org', {}), {
                        'doc': 'Organization responsible for the software.',
                    }),
                    ('author:acct', ('inet:web:acct', {}), {
                        'doc': 'Web user responsible for the software.',
                    }),
                    ('author:person', ('ps:person', {}), {
                        'doc': 'Person responsible for the software.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'URL relevant for the software.',
                    }),
                )),
                ('it:prod:softver', {}, (
                    ('software', ('it:prod:soft', {}), {
                        'doc': 'Software associated with this version instance',
                    }),
                    ('software:name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The name of the software at a particular version.',
                    }),
                    ('vers', ('it:dev:str', {}), {
                        'doc': 'Version string associated with this version instance.',
                    }),
                    ('vers:norm', ('str', {'lower': True}), {
                        'doc': 'Normalized version of the version string.',
                    }),
                    ('arch', ('it:dev:str', {}), {
                        'doc': 'Software architecture',
                    }),
                    ('semver', ('it:semver', {}), {
                        'doc': 'System normalized semantic version number.',
                    }),
                    ('semver:major', ('int', {}), {
                        'doc': 'Version major number.',
                    }),
                    ('semver:minor', ('int', {}), {
                        'doc': 'Version minor number.',
                    }),
                    ('semver:patch', ('int', {}), {
                        'doc': 'Version patch number.',
                    }),
                    ('semver:pre', ('str', {}), {
                        'doc': 'Semver prerelease string.',
                    }),
                    ('semver:build', ('str', {}), {
                        'doc': 'Semver build string.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'URL where a specific version of the software is available from.',
                    }),
                )),
                ('it:hostsoft', {}, (
                    ('host', ('it:host', {}), {
                        'ro': True,
                        'doc': 'Host with the software.',
                    }),
                    ('softver', ('it:prod:softver', {}), {
                        'ro': True,
                        'doc': 'Software on the host.',
                    })
                )),
                ('it:av:sig', {}, (
                    ('soft', ('it:prod:soft', {}), {
                        'ro': True,
                        'doc': 'The anti-virus product which contains the signature.',
                    }),
                    ('name', ('str', {'lower': True}), {
                        'ro': True,
                        'doc': 'The signature name.'
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the signature',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'A reference URL for information about the signature.',
                    })
                )),
                ('it:av:filehit', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file that triggered the signature hit.',
                    }),
                    ('sig', ('it:av:sig', {}), {
                        'ro': True,
                        'doc': 'The signature that the file triggered on.'
                    }),
                )),
                ('it:auth:passwdhash', {}, (
                    ('salt', ('hex', {}), {
                        'doc': 'The (optional) hex encoded salt value used to calculate the password hash.',
                    }),
                    ('hash:md5', ('hash:md5', {}), {
                        'doc': 'The MD5 password hash value.',
                    }),
                    ('hash:sha1', ('hash:sha1', {}), {
                        'doc': 'The SHA1 password hash value.',
                    }),
                    ('hash:sha256', ('hash:sha256', {}), {
                        'doc': 'The SHA256 password hash value.',
                    }),
                    ('hash:sha512', ('hash:sha512', {}), {
                        'doc': 'The SHA512 password hash value.',
                    }),
                    ('hash:lm', ('hash:lm', {}), {
                        'doc': 'The LM password hash value.',
                    }),
                    ('hash:ntlm', ('hash:ntlm', {}), {
                        'doc': 'The NTLM password hash value.',
                    }),
                    ('passwd', ('inet:passwd', {}), {
                        'doc': 'The (optional) clear text password for this password hash.',
                    }),
                )),
                ('it:exec:proc', ('guid', {}), (
                    ('host', ('it:host', {}), {
                        'doc': 'The host that executed the process. May be an actual or a virtual / notional host.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The file considered the "main" executable for the process. For example, rundll32.exe may be considered the "main" executable for DLLs loaded by that program.',
                    }),
                    ('cmd', ('str', {}), {
                        'doc': 'The command string used to launch the process, including any command line parameters.',
                    }),
                    ('pid', ('int', {}), {
                        'doc': 'The process ID',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The start time for the process.',
                    }),
                    ('user', ('inet:user', {}), {
                        'doc': 'The user name of the process owner.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path to the executable of the process.',
                    }),
                    ('src:exe', ('file:path', {}), {
                        'doc': 'The path to the executable which started the process',
                    }),
                    ('src:proc', ('it:exec:proc', {}), {
                        'doc': 'The process which created the process.'
                    }),
                )),
                ('it:exec:mutex', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that created the mutex.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that created the mutex. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that created the mutex. May or may not be the same :exe specified in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the mutex was created.',
                    }),
                    ('name', ('it:dev:mutex', {}), {
                        'doc': 'The mutex string.',
                    }),
                )),
                ('it:exec:pipe', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that created the named pipe.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that created the named pipe. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that created the named pipe. May or may not be the same :exe specified in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the named pipe was created.',
                    }),
                    ('name', ('it:dev:pipe', {}), {
                        'doc': 'The named pipe string.',
                    }),
                )),
                ('it:exec:url', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that requested the URL.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that requested the URL. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that requested the URL. May or may not be the same :exe specified in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the URL was requested.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that was requested.',
                    }),
                    ('client', ('inet:client', {}), {
                        'doc': 'The address of the client during the URL retrieval.'
                    }),
                    ('client:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 of the client during the URL retrieval..'
                    }),
                    ('client:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 of the client during the URL retrieval..'
                    }),
                    ('client:port', ('inet:port', {}), {
                        'doc': 'The client port during the URL retrieval..'
                    }),
                )),
                ('it:exec:bind', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that bound the listening port.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that bound the listening port. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that bound the listening port. May or may not be the same :exe specified in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the port was bound.',
                    }),
                    ('server', ('inet:server', {}), {
                        'doc': 'The inet:addr of the server when binding the port.'
                    }),
                    ('server:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 address specified to bind().'
                    }),
                    ('server:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 address specified to bind().'
                    }),
                    ('server:port', ('inet:port', {}), {
                        'doc': 'The bound (listening) TCP port.'
                    }),
                )),
                ('it:fs:file', {}, (
                    ('host', ('it:host', {}), {
                        'doc': 'The host containing the file.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path for the file.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory of the file path (parsed from :path).',
                    }),
                    ('path:ext', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The file extension of the file name (parsed from :path).',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The final component of the file path (parsed from :path).',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file on the host.',
                    }),
                    ('ctime', ('time', {}), {
                        'doc': 'The file creation time.',
                    }),
                    ('mtime', ('time', {}), {
                        'doc': 'The file modification time.',
                    }),
                    ('atime', ('time', {}), {
                        'doc': 'The file access time.',
                    }),
                    ('user', ('inet:user', {}), {
                        'doc': 'The owner of the file.',
                    }),
                    ('group', ('inet:user', {}), {
                        'doc': 'The group owner of the file.',
                    }),
                )),
                ('it:exec:file:add', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that created the new file.',
                     }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that created the new file. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that created the new file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the file was created.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path where the file was created.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory of the file path (parsed from :path).',
                    }),
                    ('path:ext', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The file extension of the file name (parsed from :path).',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The final component of the file path (parsed from :path).',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that was created.',
                    }),
                )),
                ('it:exec:file:del', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that deleted the file.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that deleted the file. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that deleted the file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the file was deleted.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path where the file was deleted.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory of the file path (parsed from :path).',
                    }),
                    ('path:ext', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The file extension of the file name (parsed from :path).',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The final component of the file path (parsed from :path).',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that was deleted.',
                    }),
                )),
                ('it:exec:file:read', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that read the file.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that read the file. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that read the file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the file was read.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path where the file was read.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory of the file path (parsed from :path).',
                    }),
                    ('path:ext', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The file extension of the file name (parsed from :path).',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The final component of the file path (parsed from :path).',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that was read.',
                    }),
                )),
                ('it:exec:file:write', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that wrote to / modified the existing file.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that wrote to the file. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that wrote to the file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the file was written to/modified.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path where the file was written to/modified.',
                    }),
                    ('path:dir', ('file:path', {}), {
                        'ro': True,
                        'doc': 'The parent directory of the file path (parsed from :path).',
                    }),
                    ('path:ext', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The file extension of the file name (parsed from :path).',
                    }),
                    ('path:base', ('file:base', {}), {
                        'ro': True,
                        'doc': 'The final component of the file path (parsed from :path).',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that was modified.',
                    }),
                )),
                ('it:exec:reg:get', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that read the registry.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that read the registry. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that read the registry. May or may not be the same :exe referenced in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the registry was read.',
                    }),
                    ('reg', ('it:dev:regval', {}), {
                        'doc': 'The registry key or value that was read.',
                    }),
                    ('reg:key', ('it:dev:regkey', {}), {
                        'ro': True,
                        'doc': 'The registry key that was read (parsed from :reg).',
                    }),
                    ('reg:str', ('it:dev:str', {}), {
                        'ro': True,
                        'doc': 'The string value that was read (parsed from :reg).',
                    }),
                    ('reg:int', ('it:dev:int', {}), {
                        'ro': True,
                        'doc': 'The integer value that was read (parsed from :reg).',
                    }),
                    ('reg:bytes', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The binary data that was read (parsed from :reg).',
                    }),
                )),
                ('it:exec:reg:set', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that wrote to the registry.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that wrote to the registry. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that wrote to the registry. May or may not be the same :exe referenced in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the registry was written to.',
                    }),
                    ('reg', ('it:dev:regval', {}), {
                        'doc': 'The registry key or value that was written to.',
                    }),
                    ('reg:key', ('it:dev:regkey', {}), {
                        'ro': True,
                        'doc': 'The registry key that was written (parsed from :reg).',
                    }),
                    ('reg:str', ('it:dev:str', {}), {
                        'ro': True,
                        'doc': 'The string value that was written (parsed from :reg).',
                    }),
                    ('reg:int', ('it:dev:int', {}), {
                        'ro': True,
                        'doc': 'The integer value that was written (parsed from :reg).',
                    }),
                    ('reg:bytes', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The binary data that was written (parsed from :reg).',
                    }),
                )),
                ('it:exec:reg:del', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that deleted data from the registry.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host running the process that deleted data from the registry. Typically the same host referenced in :proc, if present.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The specific file containing code that deleted data from the registry. May or may not be the same :exe referenced in :proc, if present.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the data from the registry was deleted.',
                    }),
                    ('reg', ('it:dev:regval', {}), {
                        'doc': 'The registry key or value that was deleted.',
                    }),
                    ('reg:key', ('it:dev:regkey', {}), {
                        'ro': True,
                        'doc': 'The registry key that was deleted (parsed from :reg).',
                    }),
                    ('reg:str', ('it:dev:str', {}), {
                        'ro': True,
                        'doc': 'The string value that was deleted (parsed from :reg).',
                    }),
                    ('reg:int', ('it:dev:int', {}), {
                        'ro': True,
                        'doc': 'The integer value that was deleted (parsed from :reg).',
                    }),
                    ('reg:bytes', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The binary data that was deleted (parsed from :reg).',
                    }),
                )),
            ),
        }
        name = 'it'
        return ((name, modl), )
