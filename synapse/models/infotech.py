import asyncio
import logging

import synapse.exc as s_exc
import synapse.data as s_data

import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

def cpesplit(text):
    part = ''
    parts = []

    genr = iter(text)
    try:
        while True:

            c = next(genr)

            if c == '\\':
                c += next(genr)

            if c == ':':
                parts.append(part)
                part = ''
                continue

            part += c

    except StopIteration:
        parts.append(part)

    return parts

class Cpe22Str(s_types.Str):
    '''
    CPE 2.2 Formatted String
    https://cpe.mitre.org/files/cpe-specification_2.2.pdf
    '''
    def __init__(self, modl, name, info, opts):
        opts['lower'] = True
        s_types.Str.__init__(self, modl, name, info, opts)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)

    def _normPyStr(self, valu):

        text = valu.lower()
        if text.startswith('cpe:/'):
            parts = chopCpe22(text)
        elif text.startswith('cpe:2.3:'):
            parts = cpesplit(text[8:])
        else:
            mesg = 'CPE 2.2 string is expected to start with "cpe:/"'
            raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

        return zipCpe22(parts), {}

    def _normPyList(self, parts):
        return zipCpe22(parts), {}

def zipCpe22(parts):
    parts = list(parts)
    while parts and parts[-1] in ('', '*'):
        parts.pop()
    text = ':'.join(parts[:7])
    return f'cpe:/{text}'

def chopCpe22(text):
    '''
    CPE 2.2 Formatted String
    https://cpe.mitre.org/files/cpe-specification_2.2.pdf
    '''
    if not text.startswith('cpe:/'):
        mesg = 'CPE 2.2 string is expected to start with "cpe:/"'
        raise s_exc.BadTypeValu(valu=text, mesg=mesg)

    _, text = text.split(':/', 1)
    parts = cpesplit(text)
    if len(parts) > 7:
        mesg = f'CPE 2.2 string has {len(parts)} parts, expected <= 7.'
        raise s_exc.BadTypeValu(valu=text, mesg=mesg)

    return parts

class Cpe23Str(s_types.Str):
    '''
    CPE 2.3 Formatted String

    ::

        https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf

        (Section 6.2)

        cpe:2.3: part : vendor : product : version : update : edition :
            language : sw_edition : target_sw : target_hw : other

        * = "any"
        - = N/A
    '''
    def __init__(self, modl, name, info, opts):
        opts['lower'] = True
        s_types.Str.__init__(self, modl, name, info, opts)

    def _normPyStr(self, valu):
        text = valu.lower()
        if text.startswith('cpe:2.3:'):
            parts = cpesplit(text[8:])
            if len(parts) > 11:
                mesg = f'CPE 2.3 string has {len(parts)} fields, expected up to 11.'
                raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

            extsize = 11 - len(parts)
            parts.extend(['*' for _ in range(extsize)])
        elif text.startswith('cpe:/'):
            # automatically normalize CPE 2.2 format to CPE 2.3
            parts = chopCpe22(text)
            extsize = 11 - len(parts)
            parts.extend(['*' for _ in range(extsize)])
        else:
            mesg = 'CPE 2.3 string is expected to start with "cpe:2.3:"'
            raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

        subs = {
            'v2_2': parts,
            'part': parts[0],
            'vendor': parts[1],
            'product': parts[2],
            'version': parts[3],
            'update': parts[4],
            'edition': parts[5],
            'language': parts[6],
            'sw_edition': parts[7],
            'target_sw': parts[8],
            'target_hw': parts[9],
            'other': parts[10],
        }

        return 'cpe:2.3:' + ':'.join(parts), {'subs': subs}

class SemVer(s_types.Int):
    '''
    Provides support for parsing a semantic version string into its component
    parts. This normalizes a version string into an integer to allow version
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
        s_types.Int.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyStr(self, valu):
        valu = valu.strip()
        if not valu:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='No text left after stripping whitespace')

        subs = s_version.parseSemver(valu)
        if subs is None:
            subs = s_version.parseVersionParts(valu)
            if subs is None:
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg='Unable to parse string as a semver.')

        subs.setdefault('minor', 0)
        subs.setdefault('patch', 0)
        valu = s_version.packVersion(subs.get('major'), subs.get('minor'), subs.get('patch'))

        return valu, {'subs': subs}

    def _normPyInt(self, valu):
        if valu < 0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Cannot norm a negative integer as a semver.')
        if valu > s_version.mask60:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Cannot norm a integer larger than 1152921504606846975 as a semver.')
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.packVersion(major, minor, patch)
        subs = {'major': major,
                'minor': minor,
                'patch': patch}
        return valu, {'subs': subs}

    def repr(self, valu):
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.fmtVersion(major, minor, patch)
        return valu

loglevels = (
    (10, 'debug'),
    (20, 'info'),
    (30, 'notice'),
    (40, 'warning'),
    (50, 'err'),
    (60, 'crit'),
    (70, 'alert'),
    (80, 'emerg'),
)

tlplevels = (
    (10, 'clear'),
    (20, 'green'),
    (30, 'amber'),
    (40, 'amber-strict'),
    (50, 'red'),
)

# The published Attack Flow json schema at the below URL is horribly
# broken. It depends on some custom python scripting to validate each
# object individually against the schema for each object's type instead
# of validating the document as a whole. Instead, the
# attack-flow-schema-2.0.0 file that is published in the synapse data
# directory is a heavily modified version of the official schema that
# actually works as a json schema should.
# https://raw.githubusercontent.com/center-for-threat-informed-defense/attack-flow/main/stix/attack-flow-schema-2.0.0.json

attack_flow_schema_2_0_0 = s_data.getJSON('attack-flow/attack-flow-schema-2.0.0')

class ItModule(s_module.CoreModule):
    async def initCoreModule(self):
        self.model.form('it:dev:str').onAdd(self._onFormItDevStr)
        self.model.form('it:dev:pipe').onAdd(self._onFormMakeDevStr)
        self.model.form('it:dev:mutex').onAdd(self._onFormMakeDevStr)
        self.model.form('it:dev:regkey').onAdd(self._onFormMakeDevStr)
        self.model.prop('it:prod:softver:arch').onSet(self._onPropSoftverArch)
        self.model.prop('it:prod:softver:vers').onSet(self._onPropSoftverVers)

    def bruteVersionStr(self, valu):
        '''
        This API is deprecated.

        Brute force the version out of a string.

        Args:
            valu (str): String to attempt to get version information for.

        Notes:
            This first attempts to parse strings using the it:semver normalization
            before attempting to extract version parts out of the string.

        Returns:
            int, dict: The system normalized version integer and a subs dictionary.
        '''
        s_common.deprecated('ItModule.bruteVersionStr')

        valu, info = self.core.model.type('it:semver').norm(valu)
        subs = info.get('subs')
        return valu, subs

    async def _onFormItDevStr(self, node):
        await node.set('norm', node.ndef[1])

    async def _onFormMakeDevStr(self, node):
        pprop = node.ndef[1]
        await node.snap.addNode('it:dev:str', pprop)

    async def _onPropSoftverArch(self, node, oldv):
        # make it:dev:str for arch
        prop = node.get('arch')
        if prop:
            await node.snap.addNode('it:dev:str', prop)

    async def _onPropSoftverVers(self, node, oldv):
        # Set vers:norm and make its normed valu
        prop = node.get('vers')
        if not prop:
            return

        await node.set('vers:norm', prop)

        # Make it:dev:str from version str
        await node.snap.addNode('it:dev:str', prop)

        # form the semver properly or bruteforce parts
        try:
            valu, info = self.core.model.type('it:semver').norm(prop)
            subs = info.get('subs')
            await node.set('semver', valu)
            for k, v in subs.items():
                await node.set(f'semver:{k}', v)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:
            logger.exception('Failed to brute force version string [%s]', prop)

    def getModelDefs(self):
        modl = {
            'ctors': (
                ('it:semver', 'synapse.models.infotech.SemVer', {}, {
                    'doc': 'Semantic Version type.',
                }),
                ('it:sec:cpe', 'synapse.models.infotech.Cpe23Str', {}, {
                    'doc': 'A NIST CPE 2.3 Formatted String',
                }),
                ('it:sec:cpe:v2_2', 'synapse.models.infotech.Cpe22Str', {}, {
                    'doc': 'A NIST CPE 2.2 Formatted String',
                }),
            ),
            'types': (
                ('it:hostname', ('str', {'strip': True, 'lower': True}), {
                    'doc': 'The name of a host or system.',
                }),
                ('it:host', ('guid', {}), {
                    'doc': 'A GUID that represents a host or system.'
                }),
                ('it:log:event:type:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of log event types.',
                    'interfaces': ('taxonomy',),
                }),
                ('it:log:event', ('guid', {}), {
                    'doc': 'A GUID representing an individual log event.',
                    'interfaces': ('it:host:activity',),
                }),
                ('it:network', ('guid', {}), {
                    'doc': 'A GUID that represents a logical network.'
                }),
                ('it:domain', ('guid', {}), {
                    'doc': 'A logical boundary of authentication and configuration such as a windows domain.'
                }),
                ('it:account', ('guid', {}), {
                    'doc': 'A GUID that represents an account on a host or network.'
                }),
                ('it:group', ('guid', {}), {
                    'doc': 'A GUID that represents a group on a host or network.'
                }),
                ('it:logon', ('guid', {}), {
                    'doc': 'A GUID that represents an individual logon/logoff event.'
                }),
                ('it:hosturl', ('comp', {'fields': (('host', 'it:host'), ('url', 'inet:url'))}), {
                    'doc': 'A url hosted on or served by a host or system.',
                }),
                ('it:screenshot', ('guid', {}), {
                    'doc': 'A screenshot of a host.',
                    'interfaces': ('it:host:activity',),
                }),
                ('it:sec:cve', ('str', {'lower': True, 'replace': s_chop.unicode_dashes_replace,
                                        'regex': r'(?i)^CVE-[0-9]{4}-[0-9]{4,}$'}), {
                    'doc': 'A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.',
                    'ex': 'cve-2012-0158'
                }),
                ('it:sec:cwe', ('str', {'regex': r'^CWE-[0-9]{1,8}$'}), {
                    'doc': 'NIST NVD Common Weaknesses Enumeration Specification',
                    'ex': 'CWE-120',
                }),

                ('it:sec:tlp', ('int', {'enums': tlplevels}), {
                    'doc': 'The US CISA Traffic-Light-Protocol used to designate information sharing boundaries.',
                    'ex': 'green'}),

                ('it:sec:metrics', ('guid', {}), {
                    'doc': "A node used to track metrics of an organization's infosec program."}),

                ('it:sec:vuln:scan', ('guid', {}), {
                    'doc': "An instance of running a vulnerability scan."}),

                ('it:sec:vuln:scan:result', ('guid', {}), {
                    'doc': "A vulnerability scan result for an asset."}),

                ('it:mitre:attack:status', ('str', {'enums': 'current,deprecated,withdrawn'}), {
                    'doc': 'A Mitre ATT&CK element status.',
                    'ex': 'current',
                }),
                ('it:mitre:attack:matrix', ('str', {'enums': 'enterprise,mobile,ics'}), {
                    'doc': 'An enumeration of ATT&CK matrix values.',
                    'ex': 'enterprise',
                }),
                ('it:mitre:attack:group', ('str', {'regex': r'^G[0-9]{4}$'}), {
                    'doc': 'A Mitre ATT&CK Group ID.',
                    'ex': 'G0100',
                }),
                ('it:mitre:attack:tactic', ('str', {'regex': r'^TA[0-9]{4}$'}), {
                    'doc': 'A Mitre ATT&CK Tactic ID.',
                    'ex': 'TA0040',
                }),
                ('it:mitre:attack:technique', ('str', {'regex': r'^T[0-9]{4}(.[0-9]{3})?$'}), {
                    'doc': 'A Mitre ATT&CK Technique ID.',
                    'ex': 'T1548',
                }),
                ('it:mitre:attack:mitigation', ('str', {'regex': r'^M[0-9]{4}$'}), {
                    'doc': 'A Mitre ATT&CK Mitigation ID.',
                    'ex': 'M1036',
                }),
                ('it:mitre:attack:software', ('str', {'regex': r'^S[0-9]{4}$'}), {
                    'doc': 'A Mitre ATT&CK Software ID.',
                    'ex': 'S0154',
                }),
                ('it:mitre:attack:flow', ('guid', {}), {
                    'doc': 'A Mitre ATT&CK Flow diagram.',
                }),
                ('it:dev:str', ('str', {}), {
                    'doc': 'A developer selected string.'
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
                ('it:dev:repo:type:taxonomy', ('taxonomy', {}), {
                    'doc': 'A version control system type taxonomy.',
                    'interfaces': ('taxonomy',)
                }),
                ('it:dev:repo:label', ('guid', {}), {
                    'doc': 'A developer selected label.',
                }),
                ('it:dev:repo', ('guid', {}), {
                    'doc': 'A version control system instance.',
                }),
                ('it:dev:repo:remote', ('guid', {}), {
                    'doc': 'A remote repo that is tracked for changes/branches/etc.',
                }),
                ('it:dev:repo:branch', ('guid', {}), {
                    'doc': 'A branch in a version control system instance.',
                }),
                ('it:dev:repo:commit', ('guid', {}), {
                    'doc': 'A commit to a repository.',
                }),
                ('it:dev:repo:diff', ('guid', {}), {
                    'doc': 'A diff of a file being applied in a single commit.',
                }),
                ('it:dev:repo:issue:label', ('guid', {}), {
                    'doc': 'A label applied to a repository issue.',
                }),
                ('it:dev:repo:issue', ('guid', {}), {
                    'doc': 'An issue raised in a repository.',
                }),
                ('it:dev:repo:issue:comment', ('guid', {}), {
                    'doc': 'A comment on an issue in a repository.',
                }),
                ('it:dev:repo:diff:comment', ('guid', {}), {
                    'doc': 'A comment on a diff in a repository.',
                }),
                ('it:prod:soft', ('guid', {}), {
                    'doc': 'A software product.',
                }),
                ('it:prod:softname', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'A software product name.',
                }),
                ('it:prod:soft:taxonomy', ('taxonomy', {}), {
                    'doc': 'A software type taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
                ('it:prod:softid', ('guid', {}), {
                    'doc': 'An identifier issued to a given host by a specific software application.'}),

                ('it:prod:hardware', ('guid', {}), {
                    'doc': 'A specification for a piece of IT hardware.',
                }),
                ('it:prod:component', ('guid', {}), {
                    'doc': 'A specific instance of an it:prod:hardware most often as part of an it:host.',
                }),
                ('it:prod:hardwaretype', ('taxonomy', {}), {
                    'doc': 'An IT hardware type taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
                ('it:adid', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'An advertising identification string.'}),

                ('it:os:windows:sid', ('str', {'regex': r'^S-1-[0-59]-\d{2}-\d{8,10}-\d{8,10}-\d{8,10}-[1-9]\d{3}$'}), {
                    'doc': 'A Microsoft Windows Security Identifier.',
                    'ex': 'S-1-5-21-1220945662-1202665555-839525555-5555',
                }),

                ('it:os:ios:idfa', ('it:adid', {}), {
                    'doc': 'An iOS advertising identification string.'}),

                ('it:os:android:aaid', ('it:adid', {}), {
                    'doc': 'An android advertising identification string.'}),

                ('it:os:android:perm', ('str', {}), {
                    'doc': 'An android permission string.'}),

                ('it:os:android:intent', ('str', {}), {
                    'doc': 'An android intent string.'}),

                ('it:os:android:reqperm', ('comp', {'fields': (
                                                        ('app', 'it:prod:soft'),
                                                        ('perm', 'it:os:android:perm'))}), {
                    'doc': 'The given software requests the android permission.'}),

                ('it:os:android:ilisten', ('comp', {'fields': (
                                                        ('app', 'it:prod:soft'),
                                                        ('intent', 'it:os:android:intent'))}), {
                    'doc': 'The given software listens for an android intent.'}),

                ('it:os:android:ibroadcast', ('comp', {'fields': (
                                                        ('app', 'it:prod:soft'),
                                                        ('intent', 'it:os:android:intent')
                                              )}), {
                    'doc': 'The given software broadcasts the given Android intent.'}),

                ('it:prod:softver', ('guid', {}), {
                    'doc': 'A specific version of a software product.'}),

                ('it:prod:softfile', ('comp', {'fields': (
                                            ('soft', 'it:prod:softver'),
                                            ('file', 'file:bytes'))}), {
                    'doc': 'A file is distributed by a specific software version.'}),

                ('it:prod:softreg', ('comp', {'fields': (
                                            ('softver', 'it:prod:softver'),
                                            ('regval', 'it:dev:regval'))}), {
                    'doc': 'A registry entry is created by a specific software version.'}),

                ('it:prod:softlib', ('comp', {'fields': (
                                            ('soft', 'it:prod:softver'),
                                            ('lib', 'it:prod:softver'))}), {
                    'doc': 'A software version contains a library software version.'}),

                ('it:prod:softos', ('comp', {'fields': (
                                            ('soft', 'it:prod:softver'),
                                            ('os', 'it:prod:softver'))}), {
                    'doc': 'The software version is known to be compatible with the given os software version.'}),

                ('it:hostsoft', ('comp', {'fields': (('host', 'it:host'), ('softver', 'it:prod:softver'))}), {
                   'doc': 'A version of a software product which is present on a given host.',
                }),
                ('it:av:sig', ('comp', {'fields': (('soft', 'it:prod:soft'), ('name', 'it:av:signame'))}), {
                   'doc': 'A signature name within the namespace of an antivirus engine name.'
                }),
                ('it:av:signame', ('str', {'lower': True}), {
                    'doc': 'An antivirus signature name.',
                }),
                ('it:av:filehit', ('comp', {'fields': (('file', 'file:bytes'), ('sig', 'it:av:sig'))}), {
                    'doc': 'A file that triggered an alert on a specific antivirus signature.',
                }),
                ('it:av:prochit', ('guid', {}), {
                    'doc': 'An instance of a process triggering an alert on a specific antivirus signature.'
                }),
                ('it:auth:passwdhash', ('guid', {}), {
                    'doc': 'An instance of a password hash.',
                }),
                ('it:exec:proc', ('guid', {}), {
                    'doc': 'A process executing on a host. May be an actual (e.g., endpoint) or virtual (e.g., malware sandbox) host.',
                }),
                ('it:exec:thread', ('guid', {}), {
                    'doc': 'A thread executing in a process.',
                }),
                ('it:exec:loadlib', ('guid', {}), {
                    'doc': 'A library load event in a process.',
                }),
                ('it:exec:mmap', ('guid', {}), {
                    'doc': 'A memory mapped segment located in a process.',
                }),
                ('it:cmd', ('str', {'strip': True}), {
                    'doc': 'A unique command-line string.',
                    'ex': 'foo.exe --dostuff bar',
                }),
                ('it:query', ('str', {'strip': True}), {
                    'doc': 'A unique query string.',
                }),
                ('it:exec:query', ('guid', {}), {
                    'interfaces': ('it:host:activity',),
                    'doc': 'An instance of an executed query.',
                }),
                ('it:exec:mutex', ('guid', {}), {
                    'doc': 'A mutex created by a process at runtime.',
                }),
                ('it:exec:pipe', ('guid', {}), {
                    'doc': 'A named pipe created by a process at runtime.',
                }),
                ('it:exec:url', ('guid', {}), {
                    'doc': 'An instance of a host requesting a URL.',
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
                    'doc': 'An instance of a host creating or setting a registry key.',
                }),
                ('it:exec:reg:del', ('guid', {}), {
                    'doc': 'An instance of a host deleting a registry key.',
                }),
                ('it:app:yara:rule', ('guid', {}), {
                    'doc': 'A YARA rule unique identifier.',
                }),
                ('it:sec:stix:bundle', ('guid', {}), {
                    'doc': 'A STIX bundle.',
                }),
                ('it:sec:stix:indicator', ('guid', {}), {
                    'doc': 'A STIX indicator pattern.',
                }),
                ('it:app:yara:match', ('comp', {'fields': (('rule', 'it:app:yara:rule'), ('file', 'file:bytes'))}), {
                    'doc': 'A YARA rule match to a file.',
                }),
                ('it:app:yara:procmatch', ('guid', {}), {
                    'doc': 'An instance of a YARA rule match to a process.',
                }),
                ('it:app:snort:rule', ('guid', {}), {
                    'doc': 'A snort rule.',
                }),
                ('it:app:snort:hit', ('guid', {}), {
                    'doc': 'An instance of a snort rule hit.',
                }),
                ('it:reveng:function', ('guid', {}), {
                    'doc': 'A function inside an executable.',
                }),
                ('it:reveng:filefunc', ('comp', {'fields': (('file', 'file:bytes'), ('function', 'it:reveng:function'))}), {
                    'doc': 'An instance of a function in an executable.',
                }),
                ('it:reveng:funcstr', ('comp', {'fields': (('function', 'it:reveng:function'), ('string', 'str'))}), {
                    'deprecated': True,
                    'doc': 'A reference to a string inside a function.',
                }),
                ('it:reveng:impfunc', ('str', {'lower': 1}), {
                    'doc': 'A function from an imported library.',
                }),
                ('it:sec:c2:config', ('guid', {}), {
                    'doc': 'An extracted C2 config from an executable.'}),
            ),
            'interfaces': (
                ('it:host:activity', {
                    'doc': 'Properties common to instances of activity on a host.',
                    'props': (
                        ('exe', ('file:bytes', {}), {
                            'doc': 'The executable file which caused the activity.'}),
                        ('proc', ('it:exec:proc', {}), {
                            'doc': 'The host process which caused the activity.'}),
                        ('thread', ('it:exec:thread', {}), {
                            'doc': 'The host thread which caused the activity.'}),
                        ('host', ('it:host', {}), {
                            'doc': 'The host on which the activity occurred.'}),
                        ('time', ('time', {}), {
                            'doc': 'The time that the activity started.'}),
                        ('sandbox:file', ('file:bytes', {}), {
                            'doc': 'The initial sample given to a sandbox environment to analyze.'}),
                    ),
                }),
            ),
            'edges': (
                (('it:prod:soft', 'uses', 'ou:technique'), {
                    'doc': 'The software uses the technique.'}),
                (('it:exec:query', 'found', None), {
                    'doc': 'The target node was returned as a result of running the query.'}),
                (('it:app:snort:rule', 'detects', None), {
                    'doc': 'The snort rule is intended for use in detecting the target node.'}),
                (('it:app:yara:rule', 'detects', None), {
                    'doc': 'The YARA rule is intended for use in detecting the target node.'}),
            ),
            'forms': (
                ('it:hostname', {}, ()),

                ('it:host', {}, (
                    ('name', ('it:hostname', {}), {
                        'doc': 'The name of the host or system.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the host.'}),

                    ('domain', ('it:domain', {}), {
                        'doc': 'The authentication domain that the host is a member of.'}),

                    ('ipv4', ('inet:ipv4', {}), {
                        'doc': 'The last known ipv4 address for the host.'}),

                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The last known location for the host.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the host resides.'}),

                    ('loc', ('loc', {}), {
                        'doc': 'The geo-political location string for the node.'}),

                    ('os', ('it:prod:softver', {}), {
                        'doc': 'The operating system of the host.'}),

                    ('os:name', ('it:prod:softname', {}), {
                        'doc': 'A software product name for the host operating system. Used for entity resolution.'}),

                    ('hardware', ('it:prod:hardware', {}), {
                        'doc': 'The hardware specification for this host.'}),

                    ('manu', ('str', {}), {
                        'deprecated': True,
                        'doc': 'Please use :hardware:make.'}),

                    ('model', ('str', {}), {
                        'deprecated': True,
                        'doc': 'Please use :hardware:model.'}),

                    ('serial', ('str', {}), {
                        'doc': 'The serial number of the host.'}),

                    ('operator', ('ps:contact', {}), {
                        'doc': 'The operator of the host.'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The org that operates the given host.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An external identifier for the host.'}),

                    ('keyboard:layout', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The primary keyboard layout configured on the host.'}),

                    ('keyboard:language', ('lang:language', {}), {
                        'doc': 'The primary keyboard input language configured on the host.'}),
                )),
                ('it:log:event:type:taxonomy', {}, ()),
                ('it:log:event', {}, (

                    ('mesg', ('str', {}), {
                        'doc': 'The log message text.'}),

                    ('type', ('it:log:event:type:taxonomy', {}), {
                        'ex': 'windows.eventlog.securitylog',
                        'doc': 'A taxonometric type for the log event.'}),

                    ('severity', ('int', {'enums': loglevels}), {
                        'doc': 'A log level integer that increases with severity.'}),

                    ('data', ('data', {}), {
                        'doc': 'A raw JSON record of the log event.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An external id that uniquely identifies this log entry.'}),

                    ('product', ('it:prod:softver', {}), {
                        'doc': 'The software which produced the log entry.'}),

                )),
                ('it:domain', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the domain.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A brief description of the domain.',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The org that operates the given domain.',
                    }),
                )),
                ('it:network', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the network.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A brief description of the network.',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The org that owns/operates the network.',
                    }),
                    ('net4', ('inet:net4', {}), {
                        'doc': 'The optional contiguous IPv4 address range of this network.',
                    }),
                    ('net6', ('inet:net6', {}), {
                        'doc': 'The optional contiguous IPv6 address range of this network.',
                    }),
                )),
                ('it:account', {}, (
                    ('user', ('inet:user', {}), {
                        'doc': 'The username associated with the account',
                    }),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'Additional contact information associated with this account.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host where the account is registered.',
                    }),
                    ('domain', ('it:domain', {}), {
                        'doc': 'The authentication domain where the account is registered.',
                    }),
                    ('posix:uid', ('int', {}), {
                        'doc': 'The user ID of the account.',
                        'ex': '1001',
                    }),
                    ('posix:gid', ('int', {}), {
                        'doc': 'The primary group ID of the account.',
                        'ex': '1001',
                    }),
                    ('posix:gecos', ('int', {}), {
                        'doc': 'The GECOS field for the POSIX account.',
                    }),
                    ('posix:home', ('file:path', {}), {
                        'doc': "The path to the POSIX account's home directory.",
                        'ex': '/home/visi',
                    }),
                    ('posix:shell', ('file:path', {}), {
                        'doc': "The path to the POSIX account's default shell.",
                        'ex': '/bin/bash',
                    }),
                    ('windows:sid', ('it:os:windows:sid', {}), {
                        'doc': 'The Microsoft Windows Security Identifier of the account.',
                    }),
                    ('groups', ('array', {'type': 'it:group', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of groups that the account is a member of.',
                    }),
                )),
                ('it:group', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the group.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A brief description of the group.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host where the group is registered.',
                    }),
                    ('domain', ('it:domain', {}), {
                        'doc': 'The authentication domain where the group is registered.',
                    }),
                    ('groups', ('array', {'type': 'it:group', 'uniq': True, 'sorted': True}), {
                        'doc': 'Groups that are a member of this group.',
                    }),
                    ('posix:gid', ('int', {}), {
                        'doc': 'The primary group ID of the account.',
                        'ex': '1001',
                    }),
                    ('windows:sid', ('it:os:windows:sid', {}), {
                        'doc': 'The Microsoft Windows Security Identifier of the group.',
                    }),
                )),
                ('it:logon', {}, (
                    ('time', ('time', {}), {
                        'doc': 'The time the logon occurred.',
                    }),
                    ('success', ('bool', {}), {
                        'doc': 'Set to false to indicate an unsuccessful logon attempt.',
                    }),
                    ('logoff:time', ('time', {}), {
                        'doc': 'The time the logon session ended.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host that the account logged in to.',
                    }),
                    ('account', ('it:account', {}), {
                        'doc': 'The account that logged in.',
                    }),
                    ('creds', ('auth:creds', {}), {
                        'doc': 'The credentials that were used for the logon.',
                    }),
                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the logon session.',
                    }),
                    ('client:host', ('it:host', {}), {
                        'doc': 'The host where the logon originated.',
                    }),
                    ('client:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 where the logon originated.',
                    }),
                    ('client:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 where the logon originated.',
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
                ('it:screenshot', {}, (
                    ('image', ('file:bytes', {}), {
                        'doc': 'The image file.'}),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A brief description of the screenshot.'})
                )),
                ('it:dev:str', {}, (
                    ('norm', ('str', {'lower': True}), {
                        'doc': 'Lower case normalized version of the it:dev:str.',
                    }),
                )),
                ('it:sec:cve', {}, (

                    ('desc', ('str', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use risk:vuln:cve:desc.'}),

                    ('url', ('inet:url', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use risk:vuln:cve:url.'}),

                    ('references', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use risk:vuln:cve:references.'}),

                )),
                ('it:sec:cpe', {}, (
                    ('v2_2', ('it:sec:cpe:v2_2', {}), {
                        'doc': 'The CPE 2.2 string which is equivalent to the primary property.',
                    }),
                    ('part', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "part" field from the CPE 2.3 string.'}),
                    ('vendor', ('ou:name', {}), {
                        'ro': True,
                        'doc': 'The "vendor" field from the CPE 2.3 string.'}),
                    ('product', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "product" field from the CPE 2.3 string.'}),
                    ('version', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "version" field from the CPE 2.3 string.'}),
                    ('update', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "update" field from the CPE 2.3 string.'}),
                    ('edition', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "edition" field from the CPE 2.3 string.'}),
                    ('language', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "language" field from the CPE 2.3 string.'}),
                    ('sw_edition', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "sw_edition" field from the CPE 2.3 string.'}),
                    ('target_sw', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "target_sw" field from the CPE 2.3 string.'}),
                    ('target_hw', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "target_hw" field from the CPE 2.3 string.'}),
                    ('other', ('str', {'lower': True, 'strip': True}), {
                        'ro': True,
                        'doc': 'The "other" field from the CPE 2.3 string.'}),
                )),
                ('it:sec:cwe', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The CWE description field.',
                        'ex': 'Buffer Copy without Checking Size of Input (Classic Buffer Overflow)',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'The CWE description field.',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'A URL linking this CWE to a full description.',
                    }),
                    ('parents', ('array', {'type': 'it:sec:cwe',
                                           'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of ChildOf CWE Relationships.'
                    }),
                )),

                ('it:sec:metrics', {}, (

                    ('org', ('ou:org', {}), {
                        'doc': 'The organization whose security program is being measured.'}),

                    ('org:name', ('ou:name', {}), {
                        'doc': 'The organization name. Used for entity resolution.'}),

                    ('org:fqdn', ('inet:fqdn', {}), {
                        'doc': 'The organization FQDN. Used for entity resolution.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The time period used to compute the metrics.'}),

                    ('alerts:meantime:triage', ('duration', {}), {
                        'doc': 'The mean time to triage alerts generated within the time period.'}),

                    ('alerts:count', ('int', {}), {
                        'doc': 'The total number of alerts generated within the time period.'}),

                    ('alerts:falsepos', ('int', {}), {
                        'doc': 'The number of alerts generated within the time period that were determined to be false positives.'}),

                    ('assets:hosts', ('int', {}), {
                        'doc': 'The total number of hosts within scope for the information security program.'}),

                    ('assets:users', ('int', {}), {
                        'doc': 'The total number of users within scope for the information security program.'}),

                    ('assets:vulns:count', ('int', {}), {
                        'doc': 'The number of asset vulnerabilities being tracked at the end of the time period.'}),

                    ('assets:vulns:preexisting', ('int', {}), {
                        'doc': 'The number of asset vulnerabilities being tracked at the beginning of the time period.'}),

                    ('assets:vulns:discovered', ('int', {}), {
                        'doc': 'The number of asset vulnerabilities discovered during the time period.'}),

                    ('assets:vulns:mitigated', ('int', {}), {
                        'doc': 'The number of asset vulnerabilities mitigated during the time period.'}),

                    ('assets:vulns:meantime:mitigate', ('duration', {}), {
                        'doc': 'The mean time to mitigate for vulnerable assets mitigated during the time period.'}),

                )),

                ('it:sec:vuln:scan', {}, (

                    ('time', ('time', {}), {
                        'doc': 'The time that the scan was started.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'Description of the scan and scope.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An externally generated ID for the scan.'}),

                    ('ext:url', ('inet:url', {}), {
                        'doc': 'An external URL which documents the scan.'}),

                    ('software', ('it:prod:softver', {}), {
                        'doc': 'The scanning software used.'}),

                    ('software:name', ('it:prod:softname', {}), {
                        'doc': 'The name of the scanner software.'}),

                    ('operator', ('ps:contact', {}), {
                        'doc': 'Contact information for the scan operator.'}),

                )),

                ('it:sec:vuln:scan:result', {}, (

                    ('scan', ('it:sec:vuln:scan', {}), {
                        'doc': 'The scan that discovered the vulnerability in the asset.'}),

                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The vulnerability detected in the asset.'}),

                    ('asset', ('ndef', {}), {
                        'doc': 'The node which is vulnerable.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A description of the vulnerability and how it was detected in the asset.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the scan result was produced.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An externally generated ID for the scan result.'}),

                    ('ext:url', ('inet:url', {}), {
                        'doc': 'An external URL which documents the scan result.'}),

                    ('mitigation', ('risk:mitigation', {}), {
                        'doc': 'The mitigation used to address this asset vulnerability.'}),

                    ('mitigated', ('time', {}), {
                        'doc': 'The time that the vulnerability in the asset was mitigated.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The priority of mitigating the vulnerability.'}),

                    ('severity', ('meta:severity', {}), {
                        'doc': 'The severity of the vulnerability in the asset. Use "none" for no vulnerability discovered.'}),
                )),

                ('it:mitre:attack:group', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'Used to map an ATT&CK group to a synapse ou:org.',
                    }),
                    ('name', ('ou:name', {}), {
                        'doc': 'The primary name for the ATT&CK group.',
                    }),
                    ('names', ('array', {'type': 'ou:name', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the ATT&CK group.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the ATT&CK group.',
                        'disp': {'hint': 'text'},
                    }),
                    ('isnow', ('it:mitre:attack:group', {}), {
                        'doc': 'If deprecated, this field may contain the current value for the group.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that documents the ATT&CK group.',
                    }),
                    ('tag', ('syn:tag', {}), {
                        'doc': 'The synapse tag used to annotate nodes included in this ATT&CK group ID.',
                        'ex': 'cno.mitre.g0100',
                    }),
                    ('references', ('array', {'type': 'inet:url', 'uniq': True}), {
                        'doc': 'An array of URLs that document the ATT&CK group.',
                    }),
                    ('techniques', ('array', {'type': 'it:mitre:attack:technique',
                                              'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of ATT&CK technique IDs used by the group.',
                    }),
                    ('software', ('array', {'type': 'it:mitre:attack:software',
                                            'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of ATT&CK software IDs used by the group.',
                    }),
                )),
                ('it:mitre:attack:tactic', {}, (
                    ('name', ('str', {'strip': True}), {
                        'doc': 'The primary name for the ATT&CK tactic.',
                    }),
                    ('matrix', ('it:mitre:attack:matrix', {}), {
                        'doc': 'The ATT&CK matrix which defines the tactic.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the ATT&CK tactic.',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that documents the ATT&CK tactic.',
                    }),
                    ('tag', ('syn:tag', {}), {
                        'doc': 'The synapse tag used to annotate nodes included in this ATT&CK tactic.',
                        'ex': 'cno.mitre.ta0100',
                    }),
                    ('references', ('array', {'type': 'inet:url', 'uniq': True}), {
                        'doc': 'An array of URLs that document the ATT&CK tactic.',
                    }),
                )),
                ('it:mitre:attack:technique', {}, (
                    ('name', ('str', {'strip': True}), {
                        'doc': 'The primary name for the ATT&CK technique.',
                    }),
                    ('matrix', ('it:mitre:attack:matrix', {}), {
                        'doc': 'The ATT&CK matrix which defines the technique.',
                    }),
                    ('status', ('it:mitre:attack:status', {}), {
                        'doc': 'The status of this ATT&CK technique.',
                    }),
                    ('isnow', ('it:mitre:attack:technique', {}), {
                        'doc': 'If deprecated, this field may contain the current value for the technique.',
                    }),
                    ('desc', ('str', {'strip': True}), {
                        'doc': 'A description of the ATT&CK technique.',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that documents the ATT&CK technique.',
                    }),
                    ('tag', ('syn:tag', {}), {
                        'doc': 'The synapse tag used to annotate nodes included in this ATT&CK technique.',
                        'ex': 'cno.mitre.t0100',
                    }),
                    ('references', ('array', {'type': 'inet:url', 'uniq': True}), {
                        'doc': 'An array of URLs that document the ATT&CK technique.',
                    }),
                    ('parent', ('it:mitre:attack:technique', {}), {
                        'doc': 'The parent ATT&CK technique on this sub-technique.',
                    }),
                    ('tactics', ('array', {'type': 'it:mitre:attack:tactic',
                                           'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of ATT&CK tactics that include this technique.',
                    }),
                )),
                ('it:mitre:attack:software', {}, (
                    ('software', ('it:prod:soft', {}), {
                        'doc': 'Used to map an ATT&CK software to a synapse it:prod:soft.',
                    }),
                    ('name', ('it:prod:softname', {}), {
                        'doc': 'The primary name for the ATT&CK software.',
                    }),
                    ('names', ('array', {'type': 'it:prod:softname', 'uniq': True, 'sorted': True}), {
                        'doc': 'Associated names for the ATT&CK software.',
                    }),
                    ('desc', ('str', {'strip': True}), {
                        'doc': 'A description of the ATT&CK software.',
                        'disp': {'hint': 'text'},
                    }),
                    ('isnow', ('it:mitre:attack:software', {}), {
                        'doc': 'If deprecated, this field may contain the current value for the software.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that documents the ATT&CK software.',
                    }),
                    ('tag', ('syn:tag', {}), {
                        'doc': 'The synapse tag used to annotate nodes included in this ATT&CK software.',
                        'ex': 'cno.mitre.s0100',
                    }),
                    ('references', ('array', {'type': 'inet:url', 'uniq': True}), {
                        'doc': 'An array of URLs that document the ATT&CK software.',
                    }),
                    ('techniques', ('array', {'type': 'it:mitre:attack:technique',
                                              'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of techniques used by the software.',
                    }),
                )),
                ('it:mitre:attack:mitigation', {}, (
                    # TODO map to an eventual risk:mitigation
                    ('name', ('str', {'strip': True}), {
                        'doc': 'The primary name for the ATT&CK mitigation.',
                    }),
                    ('matrix', ('it:mitre:attack:matrix', {}), {
                        'doc': 'The ATT&CK matrix which defines the mitigation.',
                    }),
                    ('desc', ('str', {'strip': True}), {
                        'doc': 'A description of the ATT&CK mitigation.',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL that documents the ATT&CK mitigation.',
                    }),
                    ('tag', ('syn:tag', {}), {
                        'doc': 'The synapse tag used to annotate nodes included in this ATT&CK mitigation.',
                        'ex': 'cno.mitre.m0100',
                    }),
                    ('references', ('array', {'type': 'inet:url', 'uniq': True}), {
                        'doc': 'An array of URLs that document the ATT&CK mitigation.',
                    }),
                    ('addresses', ('array', {'type': 'it:mitre:attack:technique',
                                             'uniq': True, 'sorted': True, 'split': ','}), {
                        'doc': 'An array of ATT&CK technique IDs addressed by the mitigation.',
                    }),
                )),
                ('it:mitre:attack:flow', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The name of the attack-flow diagram.'}),
                    ('data', ('data', {'schema': attack_flow_schema_2_0_0}), {
                        'doc': 'The ATT&CK Flow diagram. Schema version 2.0.0 enforced.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time that the diagram was created.'}),
                    ('updated', ('time', {}), {
                        'doc': 'The time that the diagram was last updated.'}),
                    ('author:user', ('syn:user', {}), {
                        'doc': 'The Synapse user that created the node.'}),
                    ('author:contact', ('ps:contact', {}), {
                        'doc': 'The contact information for the author of the ATT&CK Flow diagram.'}),
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

                # TODO: all of the `id:dev:repo` forms need to be tied to the TBD inet:service model
                ('it:dev:repo:type:taxonomy', {}, ()),
                ('it:dev:repo', {}, (
                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The name of the repository.',
                    }),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A free-form description of the repository.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'When the repository was created.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'A URL where the repository is hosted.',
                    }),
                    ('type', ('it:dev:repo:type:taxonomy', {}), {
                        'doc': 'The type of the version control system used.',
                        'ex': 'svn'
                    }),
                    ('submodules', ('array', {'type': 'it:dev:repo:commit'}), {
                        'doc': "An array of other repos that this repo has as submodules, pinned at specific commits.",
                    }),
                )),

                ('it:dev:repo:remote', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name the repo is using for the remote repo.',
                        'ex': 'origin'
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL the repo is using to access the remote repo.',
                    }),
                    ('repo', ('it:dev:repo', {}), {
                        'doc': 'The repo that is tracking the remote repo.',
                    }),
                    ('remote', ('it:dev:repo', {}), {
                        'doc': 'The instance of the remote repo.',
                    }),
                )),

                ('it:dev:repo:branch', {}, (
                    ('parent', ('it:dev:repo:branch', {}), {
                        'doc': 'The branch this branch was branched from.',
                    }),
                    ('start', ('it:dev:repo:commit', {}), {
                        'doc': 'The commit in the parent branch this branch was created at.'
                    }),
                    ('name', ('str', {'strip': True}), {
                        'doc': 'The name of the branch.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the branch is hosted.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time this branch was created',
                    }),
                    ('merged', ('time', {}), {
                        'doc': 'The time this branch was merged back into its parent.',
                    }),
                    ('deleted', ('time', {}), {
                        'doc': 'The time this branch was deleted.',
                    }),
                )),

                ('it:dev:repo:commit', {}, (
                    ('repo', ('it:dev:repo', {}), {
                        'doc': 'The repository the commit lives in.',
                    }),
                    ('parents', ('array', {'type': 'it:dev:repo:commit'}), {
                        'doc': 'The commit or commits this commit is immediately based on.',
                    }),
                    ('branch', ('it:dev:repo:branch', {}), {
                        'doc': 'The name of the branch the commit was made to.',
                    }),
                    ('mesg', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The commit message describing the changes in the commit.',
                    }),
                    ('id', ('str', {}), {
                        'doc': 'The version control system specific commit identifier.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the commit was made.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the commit is hosted.',
                    }),
                )),

                ('it:dev:repo:diff', {}, (
                    ('commit', ('it:dev:repo:commit', {}), {
                        'doc': 'The commit that produced this diff.',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file after the commit has been applied',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path to the file in the repo that the diff is being applied to.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the diff is hosted.',
                    }),
                )),

                ('it:dev:repo:issue', {}, (
                    ('repo', ('it:dev:repo', {}), {
                        'doc': 'The repo where the issue was logged.',
                    }),
                    ('title', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The title of the issue.'
                    }),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The text describing the issue.'
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the issue was created.',
                    }),
                    ('updated', ('time', {}), {
                        'doc': 'The time the issue was updated.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the issue is hosted.',
                    }),
                    ('id', ('str', {'strip': True}), {
                        'doc': 'The ID of the issue in the repository system.',
                    }),
                )),

                ('it:dev:repo:label', {}, (
                    ('id', ('str', {'strip': True}), {
                        'doc': 'The ID of the label.',
                    }),
                    ('title', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The human friendly name of the label.',
                    }),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The description of the label.',
                    }),
                )),

                ('it:dev:repo:issue:label', {}, (
                    ('issue', ('it:dev:repo:issue', {}), {
                        'doc': 'The issue the label was applied to.',
                    }),
                    ('label', ('it:dev:repo:label', {}), {
                        'doc': 'The label that was applied to the issue.',
                    }),
                    ('applied', ('time', {}), {
                        'doc': 'The time the label was applied.',
                    }),
                    ('removed', ('time', {}), {
                        'doc': 'The time the label was removed.',
                    }),
                )),

                ('it:dev:repo:issue:comment', {}, (
                    ('issue', ('it:dev:repo:issue', {}), {
                        'doc': 'The issue thread that the comment was made in.',
                    }),
                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The body of the comment.',
                    }),
                    ('replyto', ('it:dev:repo:issue:comment', {}), {
                        'doc': 'The comment that this comment is replying to.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the comment is hosted.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the comment was created.',
                    }),
                    ('updated', ('time', {}), {
                        'doc': 'The time the comment was updated.',
                    }),
                )),

                ('it:dev:repo:diff:comment', {}, (
                    ('diff', ('it:dev:repo:diff', {}), {
                        'doc': 'The diff the comment is being added to.',
                    }),
                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The body of the comment.',
                    }),
                    ('replyto', ('it:dev:repo:diff:comment', {}), {
                        'doc': 'The comment that this comment is replying to.',
                    }),
                    ('line', ('int', {}), {
                        'doc': 'The line in the file that is being commented on.',
                    }),
                    ('offset', ('int', {}), {
                        'doc': 'The offset in the line in the file that is being commented on.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the comment is hosted.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the comment was created.',
                    }),
                    ('updated', ('time', {}), {
                        'doc': 'The time the comment was updated.',
                    }),
                )),

                ('it:prod:hardwaretype', {}, ()),
                ('it:prod:hardware', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The display name for this hardware specification.'}),
                    ('type', ('it:prod:hardwaretype', {}), {
                        'doc': 'The type of hardware.'}),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A brief description of the hardware.'}),
                    ('cpe', ('it:sec:cpe', {}), {
                        'doc': 'The NIST CPE 2.3 string specifying this hardware.'}),
                    ('make', ('ou:name', {}), {
                        'doc': 'The name of the organization which manufactures this hardware.'}),
                    ('model', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The model name or number for this hardware specification.'}),
                    ('version', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'Version string associated with this hardware specification.'}),
                    ('released', ('time', {}), {
                        'doc': 'The initial release date for this hardware.'}),
                    ('parts', ('array', {'type': 'it:prod:hardware', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of it:prod:hardware parts included in this hardware specification.'}),
                )),
                ('it:prod:component', {}, (
                    ('hardware', ('it:prod:hardware', {}), {
                        'doc': 'The hardware specification of this component.'}),
                    ('serial', ('str', {}), {
                        'doc': 'The serial number of this component.'}),
                    ('host', ('it:host', {}), {
                        'doc': 'The it:host which has this component installed.'}),
                )),
                ('it:prod:soft:taxonomy', {}, ()),
                ('it:prod:soft', {}, (
                    ('name', ('it:prod:softname', {}), {
                        'doc': 'Name of the software.',
                    }),
                    ('type', ('it:prod:soft:taxonomy', {}), {
                        'doc': 'The software type.'}),
                    ('names', ('array', {'type': 'it:prod:softname', 'uniq': True, 'sorted': True}), {
                        'doc': 'Observed/variant names for this software.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the software.',
                        'disp': {'hint': 'text'},
                    }),
                    ('desc:short', ('str', {'lower': True}), {
                        'doc': 'A short description of the software.',
                    }),
                    ('cpe', ('it:sec:cpe', {}), {
                        'doc': 'The NIST CPE 2.3 string specifying this software.',
                    }),
                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact information of the org or person who authored the software.',
                    }),
                    ('author:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :author to link to a ps:contact.',
                    }),
                    ('author:acct', ('inet:web:acct', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :author to link to a ps:contact.',
                    }),
                    ('author:email', ('inet:email', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :author to link to a ps:contact.',
                    }),

                    ('author:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :author to link to a ps:contact.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'URL relevant for the software.',
                    }),

                    ('isos', ('bool', {}), {
                        'doc': 'Set to True if the software is an operating system.'}),

                    ('islib', ('bool', {}), {
                        'doc': 'Set to True if the software is a library.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),
                )),

                ('it:prod:softname', {}, ()),
                ('it:prod:softid', {}, (

                    ('id', ('str', {}), {
                        'doc': 'The ID issued by the software to the host.'}),

                    ('host', ('it:host', {}), {
                        'doc': 'The host which was issued the ID by the software.'}),

                    ('soft', ('it:prod:softver', {}), {
                        'doc': 'The software which issued the ID to the host.'}),

                    ('soft:name', ('it:prod:softname', {}), {
                        'doc': 'The name of the software which issued the ID to the host.'}),
                )),

                ('it:adid', {}, ()),
                ('it:os:ios:idfa', {}, ()),
                ('it:os:android:aaid', {}, ()),
                ('it:os:android:perm', {}, ()),
                ('it:os:android:intent', {}, ()),

                ('it:os:android:reqperm', {}, (

                    ('app', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The android app which requests the permission.'}),

                    ('perm', ('it:os:android:perm', {}), {'ro': True,
                        'doc': 'The android permission requested by the app.'}),
                )),

                ('it:prod:softos', {}, (

                    ('soft', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The software which can run on the operating system.'}),

                    ('os', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The operating system which the software can run on.'}),
                )),

                ('it:os:android:ilisten', {}, (

                    ('app', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The app software which listens for the android intent.'}),

                    ('intent', ('it:os:android:intent', {}), {'ro': True,
                        'doc': 'The android intent which is listened for by the app.'}),
                )),

                ('it:os:android:ibroadcast', {}, (

                    ('app', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The app software which broadcasts the android intent.'}),

                    ('intent', ('it:os:android:intent', {}), {'ro': True,
                        'doc': 'The android intent which is broadcast by the app.'}),

                )),

                ('it:prod:softver', {}, (

                    ('software', ('it:prod:soft', {}), {
                        'doc': 'Software associated with this version instance.',
                    }),
                    ('software:name', ('str', {'lower': True, 'strip': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use it:prod:softver:name.',
                    }),
                    ('name', ('it:prod:softname', {}), {
                        'doc': 'Name of the software version.',
                    }),
                    ('names', ('array', {'type': 'it:prod:softname', 'uniq': True, 'sorted': True}), {
                        'doc': 'Observed/variant names for this software version.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the software.',
                        'disp': {'hint': 'text'},
                    }),
                    ('cpe', ('it:sec:cpe', {}), {
                        'doc': 'The NIST CPE 2.3 string specifying this software version',
                    }),
                    ('cves', ('array', {'type': 'it:sec:cve', 'uniq': True, 'sorted': True}), {
                        'doc': 'A list of CVEs that apply to this software version.',
                    }),
                    ('vers', ('it:dev:str', {}), {
                        'doc': 'Version string associated with this version instance.',
                    }),
                    ('vers:norm', ('str', {'lower': True}), {
                        'doc': 'Normalized version of the version string.',
                    }),
                    ('arch', ('it:dev:str', {}), {
                        'doc': 'Software architecture.',
                    }),
                    ('released', ('time', {}), {
                        'doc': 'Timestamp for when this version of the software was released.',
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

                ('it:prod:softlib', {}, (

                    ('soft', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The software version that contains the library.'}),

                    ('lib', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The library software version.'}),
                )),

                ('it:prod:softfile', {}, (

                    ('soft', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The software which distributes the file.'}),

                    ('file', ('file:bytes', {}), {'ro': True,
                        'doc': 'The file distributed by the software.'}),
                    ('path', ('file:path', {}), {
                        'doc': 'The default installation path of the file.'}),
                )),

                ('it:prod:softreg', {}, (

                    ('softver', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'The software which creates the registry entry.'}),

                    ('regval', ('it:dev:regval', {}), {'ro': True,
                        'doc': 'The registry entry created by the software.'}),
                )),

                ('it:hostsoft', {}, (

                    ('host', ('it:host', {}), {'ro': True,
                        'doc': 'Host with the software.'}),

                    ('softver', ('it:prod:softver', {}), {'ro': True,
                        'doc': 'Software on the host.'})

                )),
                ('it:av:sig', {}, (
                    ('soft', ('it:prod:soft', {}), {
                        'ro': True,
                        'doc': 'The anti-virus product which contains the signature.',
                    }),
                    ('name', ('it:av:signame', {}), {
                        'ro': True,
                        'doc': 'The signature name.'
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the signature.',
                        'disp': {'hint': 'text'},
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'A reference URL for information about the signature.',
                    })
                )),
                ('it:av:signame', {}, ()),

                ('it:av:filehit', {}, (
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file that triggered the signature hit.',
                    }),
                    ('sig', ('it:av:sig', {}), {
                        'ro': True,
                        'doc': 'The signature that the file triggered on.'
                    }),
                    ('sig:name', ('it:av:signame', {}), {
                        'ro': True,
                        'doc': 'The signature name.',
                    }),
                    ('sig:soft', ('it:prod:soft', {}), {
                        'ro': True,
                        'doc': 'The anti-virus product which contains the signature.',
                    }),

                )),
                ('it:av:prochit', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The file that triggered the signature hit.',
                    }),
                    ('sig', ('it:av:sig', {}), {
                        'doc': 'The signature that the file triggered on.'
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time that the AV engine detected the signature.'
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
                ('it:cmd', {}, ()),
                ('it:exec:proc', {}, (
                    ('host', ('it:host', {}), {
                        'doc': 'The host that executed the process. May be an actual or a virtual / notional host.',
                    }),
                    ('exe', ('file:bytes', {}), {
                        'doc': 'The file considered the "main" executable for the process. For example, rundll32.exe may be considered the "main" executable for DLLs loaded by that program.',
                    }),
                    ('cmd', ('it:cmd', {}), {
                        'doc': 'The command string used to launch the process, including any command line parameters.',
                        'disp': {'hint': 'text'},
                    }),
                    ('pid', ('int', {}), {
                        'doc': 'The process ID.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The start time for the process.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'The display name specified by the process.',
                    }),
                    ('exited', ('time', {}), {
                        'doc': 'The time the process exited.',
                    }),
                    ('exitcode', ('int', {}), {
                        'doc': 'The exit code for the process.',
                    }),
                    ('user', ('inet:user', {}), {
                        'deprecated': True,
                        'doc': 'The user name of the process owner.',
                    }),
                    ('account', ('it:account', {}), {
                        'doc': 'The account of the process owner.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path to the executable of the process.',
                    }),
                    ('path:base', ('file:base', {}), {
                        'doc': 'The file basename of the executable of the process.',
                    }),
                    ('src:exe', ('file:path', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Create :src:proc and set :path.',
                    }),
                    ('src:proc', ('it:exec:proc', {}), {
                        'doc': 'The process which created the process.'
                    }),
                    ('killedby', ('it:exec:proc', {}), {
                        'doc': 'The process which killed this process.',
                    }),
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
                    }),
                )),
                ('it:query', {}, ()),
                ('it:exec:query', {}, (
                    ('text', ('it:query', {}), {
                        'doc': 'The query string that was executed.'}),
                    ('opts', ('data', {}), {
                        'doc': 'An opaque JSON object containing query parameters and options.'}),
                    ('api:url', ('inet:url', {}), {
                        'doc': 'The URL of the API endpoint the query was sent to.'}),
                    ('language', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the language that the query is expressed in.'}),
                )),
                ('it:exec:thread', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process which contains the thread.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the thread was created.',
                    }),
                    ('exited', ('time', {}), {
                        'doc': 'The time the thread exited.',
                    }),
                    ('exitcode', ('int', {}), {
                        'doc': 'The exit code or return value for the thread.',
                    }),
                    ('src:proc', ('it:exec:proc', {}), {
                        'doc': 'An external process which created the thread.',
                    }),
                    ('src:thread', ('it:exec:thread', {}), {
                        'doc': 'The thread which created this thread.',
                    }),
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
                    }),
                )),
                ('it:exec:loadlib', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process where the library was loaded.',
                    }),
                    ('va', ('int', {}), {
                        'doc': 'The base memory address where the library was loaded in the process.',
                    }),
                    ('loaded', ('time', {}), {
                        'doc': 'The time the library was loaded.',
                    }),
                    ('unloaded', ('time', {}), {
                        'doc': 'The time the library was unloaded.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The path that the library was loaded from.',
                    }),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The library file that was loaded.',
                    }),
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
                    }),
                )),
                ('it:exec:mmap', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process where the memory was mapped.',
                    }),
                    ('va', ('int', {}), {
                        'doc': 'The base memory address where the map was created in the process.',
                    }),
                    ('size', ('int', {}), {
                        'doc': 'The size of the memory map in bytes.',
                    }),
                    ('perms:read', ('bool', {}), {
                        'doc': 'True if the mmap is mapped with read permissions.',
                    }),
                    ('perms:write', ('bool', {}), {
                        'doc': 'True if the mmap is mapped with write permissions.',
                    }),
                    ('perms:execute', ('bool', {}), {
                        'doc': 'True if the mmap is mapped with execute permissions.',
                    }),
                    ('created', ('time', {}), {
                        'doc': 'The time the memory map was created.',
                    }),
                    ('deleted', ('time', {}), {
                        'doc': 'The time the memory map was deleted.',
                    }),
                    ('path', ('file:path', {}), {
                        'doc': 'The file path if the mmap is a mapped view of a file.',
                    }),
                    ('hash:sha256', ('hash:sha256', {}), {
                        'doc': 'A SHA256 hash of the memory map. Bytes may optionally be present in the axon.',
                    }),
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
                    }),
                )),
                ('it:exec:url', {}, (
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The main process executing code that requested the URL.',
                    }),
                    ('browser', ('it:prod:softver', {}), {
                        'doc': 'The software version of the browser.',
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
                    ('page:pdf', ('file:bytes', {}), {
                        'doc': 'The rendered DOM saved as a PDF file.',
                    }),
                    ('page:html', ('file:bytes', {}), {
                        'doc': 'The rendered DOM saved as an HTML file.',
                    }),
                    ('page:image', ('file:bytes', {}), {
                        'doc': 'The rendered DOM saved as an image.',
                    }),
                    ('http:request', ('inet:http:request', {}), {
                        'doc': 'The HTTP request made to retrieve the initial URL contents.',
                    }),
                    ('client', ('inet:client', {}), {
                        'doc': 'The address of the client during the URL retrieval.'
                    }),
                    ('client:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The IPv4 of the client during the URL retrieval.'
                    }),
                    ('client:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The IPv6 of the client during the URL retrieval.'
                    }),
                    ('client:port', ('inet:port', {}), {
                        'doc': 'The client port during the URL retrieval.'
                    }),
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
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
                    ('sandbox:file', ('file:bytes', {}), {
                        'doc': 'The initial sample given to a sandbox environment to analyze.'
                    }),
                )),

                ('it:app:snort:rule', {}, (

                    ('id', ('str', {}), {
                        'doc': 'The snort rule id.'}),

                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The snort rule text.'}),

                    ('name', ('str', {}), {
                        'doc': 'The name of the snort rule.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A brief description of the snort rule.'}),

                    ('engine', ('int', {}), {
                        'doc': 'The snort engine ID which can parse and evaluate the rule text.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The current version of the rule.'}),

                    ('author', ('ps:contact', {}), {
                        'doc': 'Contact info for the author of the rule.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the rule was initially created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the rule was most recently modified.'}),

                    ('enabled', ('bool', {}), {
                        'doc': 'The rule enabled status to be used for snort evaluation engines.'}),

                    ('family', ('it:prod:softname', {}), {
                        'doc': 'The name of the software family the rule is designed to detect.'}),
                )),

                ('it:app:snort:hit', {}, (
                    ('rule', ('it:app:snort:rule', {}), {
                        'doc': 'The snort rule that matched the file.'}),
                    ('flow', ('inet:flow', {}), {
                        'doc': 'The inet:flow that matched the snort rule.'}),
                    ('src', ('inet:addr', {}), {
                        'doc': 'The source address of flow that caused the hit.'}),
                    ('src:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The source IPv4 address of the flow that caused the hit.'}),
                    ('src:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The source IPv6 address of the flow that caused the hit.'}),
                    ('src:port', ('inet:port', {}), {
                        'doc': 'The source port of the flow that caused the hit.'}),
                    ('dst', ('inet:addr', {}), {
                        'doc': 'The destination address of the trigger.'}),
                    ('dst:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The destination IPv4 address of the flow that caused the hit.'}),
                    ('dst:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The destination IPv4 address of the flow that caused the hit.'}),
                    ('dst:port', ('inet:port', {}), {
                        'doc': 'The destination port of the flow that caused the hit.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time of the network flow that caused the hit.'}),
                    ('sensor', ('it:host', {}), {
                        'doc': 'The sensor host node that produced the hit.'}),
                    ('version', ('it:semver', {}), {
                        'doc': 'The version of the rule at the time of match.'}),
                )),

                ('it:sec:stix:bundle', {}, (
                    ('id', ('str', {}), {
                        'doc': 'The id field from the STIX bundle.'}),
                )),

                ('it:sec:stix:indicator', {}, (
                    ('id', ('str', {}), {
                        'doc': 'The STIX id field from the indicator pattern.'}),
                    ('name', ('str', {}), {
                        'doc': 'The name of the STIX indicator pattern.'}),
                    ('pattern', ('str', {}), {
                        'doc': 'The STIX indicator pattern text.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time that the indicator pattern was first created.'}),
                    ('updated', ('time', {}), {
                        'doc': 'The time that the indicator pattern was last modified.'}),
                    ('labels', ('array', {'type': 'str', 'uniq': True, 'sorted': True}), {
                        'doc': 'The label strings embedded in the STIX indicator pattern.'}),
                )),

                ('it:app:yara:rule', {}, (

                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The YARA rule text.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'The YARA rule ID from an external system.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the YARA rule.'}),

                    ('name', ('str', {}), {
                        'doc': 'The name of the YARA rule.'}),

                    ('author', ('ps:contact', {}), {
                        'doc': 'Contact info for the author of the YARA rule.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The current version of the rule.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the YARA rule was initially created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the YARA rule was most recently modified.'}),

                    ('enabled', ('bool', {}), {
                        'doc': 'The rule enabled status to be used for YARA evaluation engines.'}),

                    ('family', ('it:prod:softname', {}), {
                        'doc': 'The name of the software family the rule is designed to detect.'}),
                )),

                ('it:app:yara:match', {}, (
                    ('rule', ('it:app:yara:rule', {}), {
                        'ro': True,
                        'doc': 'The YARA rule that matched the file.'}),
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file that matched the YARA rule.'}),
                    ('version', ('it:semver', {}), {
                        'doc': 'The most recent version of the rule evaluated as a match.'}),
                )),

                ('it:app:yara:procmatch', {}, (
                    ('rule', ('it:app:yara:rule', {}), {
                        'doc': 'The YARA rule that matched the file.'}),
                    ('proc', ('it:exec:proc', {}), {
                        'doc': 'The process that matched the YARA rule.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time that the YARA engine matched the process to the rule.'}),
                    ('version', ('it:semver', {}), {
                        'doc': 'The most recent version of the rule evaluated as a match.'}),
                )),

                ('it:reveng:function', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The name of the function.'}),
                    ('description', ('str', {}), {
                        'doc': 'Notes concerning the function.'}),
                    ('impcalls', ('array', {'type': 'it:reveng:impfunc', 'uniq': True, 'sorted': True}), {
                        'doc': 'Calls to imported library functions within the scope of the function.',
                    }),
                    ('strings', ('array', {'type': 'it:dev:str', 'uniq': True}), {
                        'doc': 'An array of strings referenced within the function.',
                    }),
                )),

                ('it:reveng:filefunc', {}, (
                    ('function', ('it:reveng:function', {}), {
                        'ro': True,
                        'doc': 'The guid matching the function.'}),
                    ('file', ('file:bytes', {}), {
                        'ro': True,
                        'doc': 'The file that contains the function.'}),
                    ('va', ('int', {}), {
                        'doc': 'The virtual address of the first codeblock of the function.'}),
                    ('rank', ('int', {}), {
                        'doc': 'The function rank score used to evaluate if it exhibits interesting behavior.'}),
                    ('complexity', ('int', {}), {
                        'doc': 'The complexity of the function.'}),
                    ('funccalls', ('array', {'type': 'it:reveng:filefunc', 'uniq': True, 'sorted': True}), {
                        'doc': 'Other function calls within the scope of the function.',
                    }),
                )),

                ('it:reveng:funcstr', {}, (
                    ('function', ('it:reveng:function', {}), {
                        'ro': True,
                        'doc': 'The guid matching the function.'}),
                    ('string', ('str', {}), {
                        'ro': True,
                        'doc': 'The string that the function references.'}),
                )),

                ('it:reveng:impfunc', {}, ()),

                ('it:sec:c2:config', {}, (
                    ('family', ('it:prod:softname', {}), {
                        'doc': 'The name of the software family which uses the config.'}),
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file that the C2 config was extracted from.'}),
                    ('decoys', ('array', {'type': 'inet:url'}), {
                        'doc': 'An array of URLs used as decoy connections to obfuscate the C2 servers.'}),
                    ('servers', ('array', {'type': 'inet:url'}), {
                        'doc': 'An array of connection URLs built from host/port/passwd combinations.'}),
                    ('proxies', ('array', {'type': 'inet:url'}), {
                        'doc': 'An array of proxy URLs used to communicate with the C2 server.'}),
                    ('listens', ('array', {'type': 'inet:url'}), {
                        'doc': 'An array of listen URLs that the software should bind.'}),
                    ('dns:resolvers', ('array', {'type': 'inet:server'}), {
                        'doc': 'An array of inet:servers to use when resolving DNS names.'}),
                    ('mutex', ('it:dev:mutex', {}), {
                        'doc': 'The mutex that the software uses to prevent multiple-installations.'}),
                    ('campaigncode', ('it:dev:str', {}), {
                        'doc': 'The operator selected string used to identify the campaign or group of targets.'}),
                    ('crypto:key', ('crypto:key', {}), {
                        'doc': 'Static key material used to encrypt C2 communications.'}),
                    ('connect:delay', ('duration', {}), {
                        'doc': 'The time delay from first execution to connecting to the C2 server.'}),
                    ('connect:interval', ('duration', {}), {
                        'doc': 'The configured duration to sleep between connections to the C2 server.'}),
                    ('raw', ('data', {}), {
                        'doc': 'A JSON blob containing the raw config extracted from the binary.'}),
                    ('http:headers', ('array', {'type': 'inet:http:header'}), {
                        'doc': 'An array of HTTP headers that the sample should transmit to the C2 server.'}),
                )),
            ),
        }
        name = 'it'
        return ((name, modl), )
