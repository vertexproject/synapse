import logging

import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.version as s_version

from synapse.lib.module import CoreModule, modelrev
from synapse.lib.types import DataType

logger = logging.getLogger(__name__)

class SemverType(DataType):
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
    subprops = (
        ('major', {'ptype': 'int'},),
        ('minor', {'ptype': 'int'},),
        ('patch', {'ptype': 'int'},),
        ('build', {'ptype': 'str:txt'},),
        ('prerelease', {'ptype': 'str:txt'},),
    )

    def norm(self, valu, oldval=None):
        if isinstance(valu, int):
            return self._norm_int(valu, oldval=oldval)

        if isinstance(valu, str):
            return self._norm_str(valu, oldval=oldval)

        self._raiseBadValu(valu, mesg='Invalid type encountered when norming a semver', type=type(valu))

    def _norm_str(self, text, oldval=None):
        text = text.strip()
        if not text:
            self._raiseBadValu(text, mesg='No text left after stripping whitespace')

        subs = s_version.parseSemver(text)
        if subs is None:
            self._raiseBadValu(text, mesg='Unable to parse string as a semver.')
        valu = s_version.packVersion(subs.get('major'), subs.get('minor'), subs.get('patch'))
        return valu, subs

    def _norm_int(self, valu, oldval=None):
        if valu < 0:
            self._raiseBadValu(valu, mesg='Cannot norm a negative integer as a semver.')
        if valu > s_version.mask60:
            self._raiseBadValu(valu,
                               mesg='Cannot norm a integer larger than 1152921504606846975 as a semver.')
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.packVersion(major, minor, patch)
        subs = {'major': major,
                'minor': minor,
                'patch': patch}
        return valu, subs

    def repr(self, valu):
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.fmtVersion(major, minor, patch)
        return valu

def bruteVersionValu(valu):
    '''
    Return the system normalized version integer for a given input.

    Args:
        valu: String or integer to normalize.

    Returns:
        int: System normalized version value.
    '''
    return bruteVersion(valu)[0]

def bruteVersion(valu):
    '''
    Attempt to brute force a valu into a semantic version string and its components

    Args:
        valu: A string or integer to attempt to obtain a system normalized version
        valu and subs for.

    Returns:
        int, dict: The system normalized version integer and a subs dictionary.
    '''
    if isinstance(valu, int):
        return s_datamodel.tlib.getTypeNorm('it:semver', valu)

    if isinstance(valu, str):
        return bruteStr(valu)

    else:
        raise s_common.BadTypeValu(valu=valu,
                                   mesg='Unable to brute force a valu',
                                   type=type(valu))

def bruteStr(valu):
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
        valu, subs = s_datamodel.tlib.getTypeNorm('it:semver', valu)
        return valu, subs
    except s_common.BadTypeValu:
        # Try doing version part extraction by noming through the string
        subs = s_version.parseVersionParts(valu)
        if subs is None:
            raise s_common.BadTypeValu(valu=valu,
                                       mesg='Unable to brute force version parts out of the string')
        if subs:
            valu = s_version.packVersion(subs.get('major'),
                                         subs.get('minor', 0),
                                         subs.get('patch', 0))
            return valu, subs

class ItMod(CoreModule):

    def initCoreModule(self):
        self.onFormNode('it:dev:str', self._onFormItDevStr)
        self.onFormNode('it:prod:softver', self._onFormItSoftVer)
        self.core.addTypeCast('it:version:brute', bruteVersionValu)

    def _onFormItDevStr(self, form, valu, props, mesg):
        props['it:dev:str:norm'] = valu.lower()

    @modelrev('it', 201801041154)
    def _revModl201801041154(self):

        now = s_common.now()

        # mark changed nodes with a dark row...
        dvalu = 'it:201801041154'
        dprop = '_:dark:syn:modl:rev'

        idens = []

        # carve registry keys to being lower case normalized
        with self.core.getCoreXact():

            # bulk cut over all it:dev:regval:key props
            rows = self.core.getRowsByProp('it:dev:regval:key')

            adds = [(i, p, v.lower(), t) for (i, p, v, t) in rows]
            darks = [(i[::-1], dprop, dvalu, now) for (i, p, v, _) in rows]

            self.core.delRowsByProp('it:dev:regval:key')

            self.core.addRows(adds)
            self.core.addRows(darks)

            # bulk update the primary props
            rows = self.core.getRowsByProp('it:dev:regkey')
            adds = [(i, p, v.lower(), t) for (i, p, v, t) in rows]
            darks = [(i[::-1], dprop, dvalu, now) for (i, p, v, _) in rows]

            self.core.delRowsByProp('it:dev:regkey')

            self.core.addRows(adds)
            self.core.addRows(darks)

            # iteratively update the node defs
            for iden, prop, valu, tick in adds:
                ndef = s_common.guid((prop, valu))
                self.core.setRowsByIdProp(iden, 'node:ndef', ndef)

    def _onFormItSoftVer(self, form, valu, props, mesg):
        # Set the :software:name field
        if 'it:prod:softver:software:name' not in props:
            software = props.get('it:prod:softver:software')
            node = self.core.getTufoByProp('it:prod:soft', software)
            if node is not None:
                name = node[1].get('it:prod:soft:name')
                props['it:prod:softver:software:name'] = name
        # Normalize the version string
        vers = props.get('it:prod:softver:vers')
        props['it:prod:softver:vers:norm'] = self.core.getTypeNorm('str:lwr', vers)[0]
        if 'it:prod:softver:semver' in props:
            return
        try:
            valu, subs = bruteVersion(vers)
            props['it:prod:softver:semver'] = valu
            for k, v in subs.items():
                props['it:prod:softver:semver:' + k] = v
        except s_common.BadTypeValu:
            logger.exception('Unable to brute force version string.')

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
                    'doc': 'A file that triggered an alert on a specific antivirus signature.'}),

                ('it:dev:str', {
                    'subof': 'str',
                    'doc': 'A developer-selected string.'}),

                ('it:dev:int', {
                    'subof': 'int',
                    'doc': 'A developer-selected integer constant.'}),

                ('it:exec:proc', {
                    'subof': 'guid',
                    'doc': 'A process executing on a host. May be an actual (e.g., endpoint) or virtual (e.g., malware sandbox) host.'}),

                ('it:dev:pipe', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a named pipe.'}),

                ('it:dev:mutex', {
                    'subof': 'it:dev:str',
                    'doc': 'A string representing a mutex.'}),

                ('it:dev:regkey', {
                    'subof': 'it:dev:str',
                    'lower': 1,
                    'doc': 'A Windows registry key.',
                    'ex': 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'}),

                ('it:dev:regval', {
                    'subof': 'comp',
                    'fields': 'key=it:dev:regkey',
                    'optfields': 'str=it:dev:str,int=it:dev:int,bytes=file:bytes',
                    'doc': 'A Windows registry key/value pair.'}),

                ('it:semver', {
                    'ctor': 'synapse.models.infotech.SemverType',
                    'doc': 'Semantic Version type.'}),

                ('it:prod:soft', {
                    'subof': 'guid',
                    'doc': 'A arbitrary, unversioned software product.'}),

                ('it:prod:softver', {
                    'subof': 'guid',
                    'doc': 'A version of a particular software product.'}),

                ('it:hostsoft', {
                    'subof': 'comp',
                    'fields': 'host,it:host|softver,it:prod:softver',
                    'doc': 'A version of a software product which is present on a given host.'}),

                ('it:auth:passwdhash', {
                    'subof': 'guid',
                    'ex': '(hash:md5=17d3533fba2669f84a225a9a04caa783)'}),
            ),

            'forms': (

                ('it:host', {}, [
                    ('name', {'ptype': 'it:hostname', 'doc': 'The name of the host or system.'}),
                    ('desc', {'ptype': 'str:txt', 'doc': 'A free-form description of the host.'}),

                    # FIXME we probably eventually need a bunch of stuff here...
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The last known ipv4 address for the host.'}),
                    ('latlong', {'ptype': 'geo:latlong', 'doc': 'The last known location for the node'}),
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

                    ('key', {'ptype': 'it:dev:regkey', 'ro': 1,
                        'doc': 'The Windows registry key.'}),

                    ('str', {'ptype': 'it:dev:str', 'ro': 1,
                        'doc': 'The value of the registry key, if the value is a string.'}),

                    ('int', {'ptype': 'it:dev:int', 'ro': 1,
                        'doc': 'The value of the registry key, if the value is an integer.'}),

                    ('bytes', {'ptype': 'file:bytes', 'ro': 1,
                         'doc': 'The file representing the value of the registry key, if the value is binary data.'}),
                )),

                ('it:exec:proc', {'ptype': 'guid'}, (
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host that executed the process. May be an actual or a virtual / notional host.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The file considered the "main" executable for the process. For example, rundll32.exe may be considered the "main" executable for DLLs loaded by that program.'}),
                    ('cmd', {'ptype': 'str',
                         'doc': 'The command string used to launch the process, including any command line parameters.'}),
                    ('pid', {'ptype': 'int', 'doc': 'The process ID.'}),
                    ('time', {'ptype': 'time', 'doc': 'The start time for the process.'}),
                    ('user', {'ptype': 'inet:user', 'doc': 'The user name of the process owner.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path to the executable of the process.'}),
                    ('src:exe', {'ptype': 'file:path', 'doc': 'The executable which created the process.'}),
                    ('src:proc', {'ptype': 'it:exec:proc', 'doc': 'The process which created the process.'}),
                )),

                ('it:exec:pipe', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that created the named pipe.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that created the named pipe. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that created the named pipe. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the named pipe was created.'}),
                    ('name', {'ptype': 'it:dev:pipe', 'doc': 'The named pipe string.'}),
                )),

                ('it:exec:mutex', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that created the mutex.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that created the mutex. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that created the mutex. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the mutex was created.'}),
                    ('name', {'ptype': 'it:dev:mutex', 'doc': 'The mutex string.'}),
                )),

                ('it:exec:url', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that requested the URL.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that requested the URL. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that requested the URL. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the URL was requested.'}),
                    ('url', {'ptype': 'inet:url', 'doc': 'The URL that was requested.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address of the host during URL retrieval.'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 address of the host during URL retrieval.'}),
                )),

                ('it:exec:bind:tcp', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that bound the listening TCP port.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that bound the port. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that bound the port. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the port was bound.'}),
                    ('port', {'ptype': 'inet:port', 'doc': 'The bound (listening) TCP port.'}),
                    ('ipv4', {'ptype': 'inet:ipv4', 'doc': 'The IPv4 address specified to bind().'}),
                    ('ipv6', {'ptype': 'inet:ipv6', 'doc': 'The IPv6 specified to bind().'}),
                )),

                ('it:exec:bind:udp', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that bound the listening UDP port.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that bound the port. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that bound the port. May or may not be the same :exe specified in :proc, if present.'}),
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
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that created the new file.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that created the new file. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that created the new file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was created.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was created.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was created.'}),
                )),

                ('it:exec:file:del', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that deleted the file.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that deleted the file. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that deleted the file. May or may not be the same :exe specified in :proc if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was deleted.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was deleted.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was deleted.'}),
                )),

                ('it:exec:file:read', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that read the file.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that read the file. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that read the file. May or may not be the same :exe specified in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was read.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was read.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was read.'}),
                )),

                ('it:exec:file:write', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that wrote to / modified the existing file.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that wrote to the file. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that wrote to the file. May or may not be the same :exe referenced in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the file was written to / modified.'}),
                    ('path', {'ptype': 'file:path', 'doc': 'The path where the file was modified.'}),
                    ('path:dir', {'ptype': 'file:path', 'doc': 'The parent directory of the file path (parsed from :path).', 'ro': 1}),
                    ('path:ext', {'ptype': 'str:lwr', 'doc': 'The file extension of the file name (parsed from :path).', 'ro': 1}),
                    ('path:base', {'ptype': 'file:base', 'doc': 'The final component of the file path (parsed from :path).', 'ro': 1}),
                    ('file', {'ptype': 'file:bytes', 'doc': 'The file that was modified.'}),
                )),

                ('it:exec:reg:get', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that read the registry.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that read the registry. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that read the registry. May or may not be the same :exe referenced in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the registry was read.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was read.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was read (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was read (parsed from :reg).', 'ro': 1}),
                )),

                ('it:exec:reg:set', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that wrote to the registry.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that wrote to the registry. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that wrote to the registry. May or may not be the same :exe referenced in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the registry was written to.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was written.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was written (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was written (parsed from :reg).', 'ro': 1}),
                )),

                ('it:exec:reg:del', {'ptype': 'guid'}, (
                    ('proc', {'ptype': 'it:exec:proc', 'doc': 'The main process executing code that deleted data from the registry.'}),
                    ('host', {'ptype': 'it:host',
                         'doc': 'The host running the process that deleted data from the registry. Typically the same host referenced in :proc, if present.'}),
                    ('exe', {'ptype': 'file:bytes',
                         'doc': 'The specific file containing code that deleted data from the registry. May or may not be the same :exe referenced in :proc, if present.'}),
                    ('time', {'ptype': 'time', 'doc': 'The time the data from the registry was deleted.'}),
                    ('reg', {'ptype': 'it:dev:regval', 'doc': 'The registry key or value that was deleted.'}),
                    ('reg:key', {'ptype': 'it:dev:regkey', 'doc': 'The registry key that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:str', {'ptype': 'it:dev:str', 'doc': 'The string value that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:int', {'ptype': 'it:dev:int', 'doc': 'The integer value that was deleted (parsed from :reg).', 'ro': 1}),
                    ('reg:bytes', {'ptype': 'file:bytes', 'doc': 'The binary data that was deleted (parsed from :reg).', 'ro': 1}),
                )),
                ('it:prod:soft', {}, (
                    ('name', {'ptype': 'str:lwr', 'ro': 1, 'req': 1,
                              'doc': 'Name of the software'}),
                    ('desc', {'ptype': 'str:txt', 'doc': 'A description of the software'}),
                    ('desc:short', {'ptype': 'str:lwr', 'doc': 'A short description of the software'}),
                    ('author:org', {'ptype': 'ou:org', 'doc': 'Organization responsible for the software', }),
                    ('author:acct', {'ptype': 'inet:web:acct', 'doc': 'Web user responsible for the software', }),
                    ('author:person', {'ptype': 'ps:person', 'doc': 'Person responsible for the software', }),
                    ('url', {'ptype': 'inet:url', 'doc': 'URL relevant for the software', }),
                )),

                ('it:prod:softver', {}, (
                    ('software', {'ptype': 'it:prod:soft', 'req': 1, 'ro': 1,
                                  'doc': 'Software associated with this version instance.'}),
                    ('software:name', {'ptype': 'str:lwr',
                                       'doc': 'The name of the software at a particular version.'}),
                    ('vers', {'ptype': 'it:dev:str', 'req': 1, 'ro': 1, 'ex': '1.0.2'
                                'Version string associated with this version instance.'}),
                    ('vers:norm', {'ptype': 'str:lwr', 'doc': 'Normalized version of the version string.'}),
                    ('arch', {'ptype': 'it:dev:str', 'doc': 'Software architecture.'}),
                    ('semver', {'ptype': 'it:semver', 'doc': 'System normalized semantic version number.', }),
                    ('semver:major', {'ptype': 'int', 'doc': 'Version major number', }),
                    ('semver:minor', {'ptype': 'int', 'doc': 'Version minor number', }),
                    ('semver:patch', {'ptype': 'int', 'doc': 'Version patch number', }),
                    ('semver:pre', {'ptype': 'str:txt', 'doc': 'Semver prerelease string.', }),
                    ('semver:build', {'ptype': 'str:txt', 'doc': 'Semver build string.', }),
                    ('url', {'ptype': 'inet:url',
                             'doc': 'URL where a specific version of the software is available from'}),
                )),

                ('it:hostsoft', {}, (
                    ('host', {'ptype': 'it:host', 'ro': 1, 'req': 1,
                              'doc': 'Host with the software', }),
                    ('softver', {'ptype': 'it:prod:softver', 'ro': 1, 'req': 1,
                                  'doc': 'Software on the host', }),
                    ('seen:min', {'ptype': 'time:min',
                                  'doc': 'Minimum time the software was seen on the host', }),
                    ('seen:max', {'ptype': 'time:max',
                                  'doc': 'Maximum time the software was seen on the host', }),
                )),

                ('it:auth:passwdhash', {}, (

                    ('salt', {'ptype': 'str:hex', 'ro': 1,
                        'doc': 'The (optional) hex encoded salt used to calculate the password hash.'}),

                    ('hash:md5', {'ptype': 'hash:md5', 'ro': 1,
                        'doc': 'The SHA512 password hash value.'}),

                    ('hash:sha1', {'ptype': 'hash:sha1', 'ro': 1,
                        'doc': 'The SHA1 password hash value.'}),

                    ('hash:sha256', {'ptype': 'hash:sha256', 'ro': 1,
                        'doc': 'The SHA256 password hash value.'}),

                    ('hash:sha512', {'ptype': 'hash:sha512', 'ro': 1,
                        'doc': 'The SHA512 password hash value.'}),

                    ('hash:lm', {'ptype': 'hash:lm', 'ro': 1,
                        'doc': 'The LM password hash value.'}),

                    ('hash:ntlm', {'ptype': 'hash:ntlm', 'ro': 1,
                        'doc': 'The NTLM password hash value.'}),

                    ('passwd', {'ptype': 'inet:passwd',
                        'doc': 'The (optional) clear text password for this password hash.'}),
                )),
            ),
        }

        models = (
            ('it', modl),
        )

        return models
