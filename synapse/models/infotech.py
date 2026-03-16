import logging

import synapse.data as s_data

import synapse.lib.chop as s_chop

logger = logging.getLogger(__name__)

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

suslevels = (
    (10, 'benign'),
    (20, 'unknown'),
    (30, 'suspicious'),
    (40, 'malicious'),
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

modeldefs = (
    ('it', {
        'ctors': (
            ('it:semver', 'synapse.lib.types.SemVer', {}, {
                'doc': 'Semantic Version type.'}),

            ('it:version', 'synapse.lib.types.ItVersion', {}, {
                'virts': (
                    ('semver', ('it:semver', {}), {
                        'computed': True,
                        'doc': 'The semver value if the version string is compatible.'}),
                ),
                'doc': 'A version string.'}),

            ('it:sec:cpe', 'synapse.lib.types.Cpe23Str', {}, {
                'doc': 'A NIST CPE 2.3 Formatted String.'}),

            ('it:sec:cpe:v2_2', 'synapse.lib.types.Cpe22Str', {}, {
                'doc': 'A NIST CPE 2.2 Formatted String.'}),
        ),
        'types': (

            ('it:hostname', ('str', {'lower': True}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'hostname'}}),
                ),
                'doc': 'The name of a host or system.'}),

            ('it:host', ('guid', {}), {
                'template': {'title': 'host'},
                'interfaces': (
                    ('phys:object', {}),
                    ('inet:service:object', {}),
                ),
                'doc': 'A GUID that represents a host or system.'}),

            ('it:log:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of log event types.'}),

            ('it:log:event', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A GUID representing an individual log event.'}),

            ('it:network', ('guid', {}), {
                'doc': 'A GUID that represents a logical network.'}),

            ('it:network:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of network types.'}),

            ('it:host:account', ('guid', {}), {
                'prevnames': ('it:account',),
                'doc': 'A local account on a host.'}),

            ('it:host:group', ('guid', {}), {
                'prevnames': ('it:group',),
                'doc': 'A local group on a host.'}),

            ('it:host:login', ('guid', {}), {
                'prevnames': ('it:logon',),
                'interfaces': (
                    ('inet:proto:link', {'template': {'link': 'login'}}),
                ),
                'doc': 'A host specific login session.'}),

            ('it:host:hosted:url', ('comp', {'fields': (('host', 'it:host'), ('url', 'inet:url'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'host at this URL'}}),
                ),
                'doc': 'A URL hosted on or served by a specific host.'}),

            ('it:host:installed', ('guid', {}), {
                'doc': 'Software installed on a specific host.'}),

            ('it:exec:screenshot', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A screenshot of a host.'}),

           ('it:sec:cve', ('base:id', {'upper': True, 'replace': s_chop.unicode_dashes_replace,
                                   'regex': r'(?i)^CVE-[0-9]{4}-[0-9]{4,}$'}), {
               'ex': 'CVE-2012-0158',
               'doc': 'A vulnerability as designated by a Common Vulnerabilities and Exposures (CVE) number.'}),


            ('it:sec:cwe', ('str', {'regex': r'^CWE-[0-9]{1,8}$'}), {
                'ex': 'CWE-120',
                'doc': 'NIST NVD Common Weaknesses Enumeration Specification.'}),

            ('it:sec:tlp', ('int', {'enums': tlplevels}), {
                'doc': 'The US CISA Traffic-Light-Protocol used to designate information sharing boundaries.',
                'ex': 'green'}),

            ('it:sec:metrics', ('guid', {}), {
                'doc': "A node used to track metrics of an organization's infosec program."}),

            ('it:sec:vuln:scan', ('guid', {}), {
                'doc': "An instance of running a vulnerability scan."}),

            ('it:sec:vuln:scan:result', ('guid', {}), {
                'doc': "A vulnerability scan result for an asset."}),

            ('it:mitre:attack:group:id', ('meta:id', {'regex': r'^G[0-9]{4}$'}), {
                'doc': 'A MITRE ATT&CK Group ID.',
                'ex': 'G0100',
            }),

            ('it:mitre:attack:tactic:id', ('meta:id', {'regex': r'^TA[0-9]{4}$'}), {
                'doc': 'A MITRE ATT&CK Tactic ID.',
                'ex': 'TA0040',
            }),

            ('it:mitre:attack:technique:id', ('meta:id', {'regex': r'^T[0-9]{4}(.[0-9]{3})?$'}), {
                'doc': 'A MITRE ATT&CK Technique ID.',
                'ex': 'T1548',
            }),

            ('it:mitre:attack:mitigation:id', ('meta:id', {'regex': r'^M[0-9]{4}$'}), {
                'doc': 'A MITRE ATT&CK Mitigation ID.',
                'ex': 'M1036',
            }),

            ('it:mitre:attack:software:id', ('meta:id', {'regex': r'^S[0-9]{4}$'}), {
                'doc': 'A MITRE ATT&CK Software ID.',
                'ex': 'S0154',
            }),

            ('it:mitre:attack:campaign:id', ('meta:id', {'regex': r'^C[0-9]{4}$'}), {
                'doc': 'A MITRE ATT&CK Campaign ID.',
                'ex': 'C0028',
            }),

            ('it:dev:function', ('guid', {}), {
                'props': (
                    ('id', ('meta:id', {}), {
                        'doc': 'An identifier for the function.'}),

                    ('name', ('it:dev:str', {}), {
                        'doc': 'The name of the function.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the function.'}),

                    ('impcalls', ('array', {'type': 'it:dev:str', 'typeopts': {'lower': True}}), {
                        'doc': 'Calls to imported library functions within the scope of the function.'}),

                    ('strings', ('array', {'type': 'it:dev:str'}), {
                        'doc': 'An array of strings referenced within the function.'}),
                ),
                'doc': 'A function defined by code.'}),

            ('it:dev:function:sample', ('guid', {}), {
                'interfaces': (
                    ('file:mime:meta', {'template': {'metadata': 'function'}}),
                ),
                'props': (
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file which contains the function.'}),

                    ('function', ('it:dev:function', {}), {
                        'doc': 'The function contained within the file.'}),

                    ('va', ('int', {}), {
                        'doc': 'The virtual address of the first codeblock of the function.'}),

                    ('complexity', ('meta:score', {}), {
                        'doc': 'The complexity of the function.'}),

                    ('calls', ('array', {'type': 'it:dev:function:sample'}), {
                        'doc': 'Other function calls within the scope of the function.'}),
                ),
                'doc': 'An instance of a function in an executable.'}),

            ('it:dev:str', ('str', {'strip': False}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'string'}}),
                ),
                'doc': 'A developer selected string.'}),

            ('it:dev:int', ('int', {}), {
                'doc': 'A developer selected integer constant.'}),

            ('it:os:windows:registry:key', ('str', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'registry key'}}),
                ),
                'prevnames': ('it:dev:regkey',),
                'ex': 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run',
                'doc': 'A Windows registry key.'}),

            ('it:os:windows:registry:entry', ('guid', {}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'registry entry'}}),
                ),
                'prevnames': ('it:dev:regval',),
                'doc': 'A Windows registry key, name, and value.'}),

            ('it:dev:repo:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of repository types.'}),

            ('it:dev:repo:label', ('guid', {}), {
                'doc': 'A developer selected label.'}),

            ('it:dev:repo', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository'}}),
                ),
                'doc': 'A version control system instance.'}),

            ('it:dev:repo:remote', ('guid', {}), {
                'doc': 'A remote repo that is tracked for changes/branches/etc.'}),

            ('it:dev:repo:branch', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository branch'}}),
                ),
                'doc': 'A branch in a version control system instance.'}),

            ('it:dev:repo:commit', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository commit'}}),
                ),
                'doc': 'A commit to a repository.'}),

            ('it:dev:repo:diff', ('guid', {}), {
                'doc': 'A diff of a file being applied in a single commit.'}),

            ('it:dev:repo:entry', ('guid', {}), {
                'doc': 'A file included in a repository.'}),

            ('it:dev:repo:issue:label', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository issue label'}}),
                ),
                'doc': 'A label applied to a repository issue.'}),

            ('it:dev:repo:issue', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository issue'}}),
                ),
                'doc': 'An issue raised in a repository.'}),

            ('it:dev:repo:issue:comment', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository issue comment'}}),
                ),
                'doc': 'A comment on an issue in a repository.'}),

            ('it:dev:repo:diff:comment', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'repository diff comment'}}),
                ),
                'doc': 'A comment on a diff in a repository.'}),

            ('it:software', ('guid', {}), {
                'prevnames': ('it:prod:soft', 'it:prod:softver', 'risk:tool:software'),
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                    ('doc:authorable', {'template': {'title': 'software'}}),
                ),
                'doc': 'A software product, tool, or script.'}),

            ('it:softwarename', ('base:name', {}), {
                'prevnames': ('it:prod:softname',),
                'doc': 'The name of a software product or tool.'}),

            ('it:software:type:taxonomy', ('taxonomy', {}), {
                'prevnames': ('it:prod:soft:taxonomy',),
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of software types.'}),

            ('it:softid', ('guid', {}), {
                'template': {'title': 'software identifier'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'doc': 'An identifier issued to a given host by a specific software application.'}),

            ('it:hardware', ('guid', {}), {
                'prevnames': ('it:prod:hardware',),
                'interfaces': (
                    ('meta:usable', {}),
                ),
                'doc': 'A specification for a piece of IT hardware.'}),

            ('it:host:component', ('guid', {}), {
                'doc': 'Hardware components which are part of a host.'}),

            ('it:hardware:type:taxonomy', ('taxonomy', {}), {
                'prevnames': ('it:prod:hardwaretype',),
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of IT hardware types.'}),

            ('it:adid', ('meta:id', {}), {
                'interfaces': (
                    ('entity:identifier', {}),
                    ('meta:observable', {'template': {'title': 'advertising ID'}}),
                ),
                'doc': 'An advertising identification string.'}),

            # https://learn.microsoft.com/en-us/windows-hardware/drivers/install/hklm-system-currentcontrolset-services-registry-tree
            ('it:os:windows:service', ('guid', {}), {
                'doc': 'A Microsoft Windows service configuration on a host.'}),

            # TODO
            # ('it:os:windows:task', ('guid', {}), {
            #     'doc': 'A Microsoft Windows scheduled task configuration.'}),

            # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/c92a27b1-c772-4fa7-a432-15df5f1b66a1
            ('it:os:windows:sid', ('str', {'regex': r'^S-1-(?:\d{1,10}|0x[0-9a-fA-F]{12})(?:-(?:\d+|0x[0-9a-fA-F]{2,}))*$'}), {
                'ex': 'S-1-5-21-1220945662-1202665555-839525555-5555',
                'doc': 'A Microsoft Windows Security Identifier.'}),

            ('it:os:android:perm', ('str', {}), {
                'doc': 'An android permission string.'}),

            ('it:os:android:intent', ('str', {}), {
                'doc': 'An android intent string.'}),

            ('it:os:android:reqperm', ('comp', {'fields': (
                                                    ('app', 'it:software'),
                                                    ('perm', 'it:os:android:perm'))}), {
                'doc': 'The given software requests the android permission.'}),

            ('it:os:android:ilisten', ('comp', {'fields': (
                                                    ('app', 'it:software'),
                                                    ('intent', 'it:os:android:intent'))}), {
                'doc': 'The given software listens for an android intent.'}),

            ('it:os:android:ibroadcast', ('comp', {'fields': (
                                                    ('app', 'it:software'),
                                                    ('intent', 'it:os:android:intent')
                                          )}), {
                'doc': 'The given software broadcasts the given Android intent.'}),

            ('it:av:signame', ('base:name', {}), {
                'doc': 'An antivirus signature name.'}),

            ('it:av:scan:result', ('guid', {}), {
                'doc': 'The result of running an antivirus scanner.'}),

            ('it:exec:proc', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A process executing on a host. May be an actual (e.g., endpoint) or virtual (e.g., malware sandbox) host.'}),

            ('it:exec:thread', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A thread executing in a process.'}),

            ('it:exec:loadlib', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A library load event in a process.'}),

            ('it:exec:mmap', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A memory mapped segment located in a process.'}),

            ('it:cmd', ('str', {}), {
                'doc': 'A unique command-line string.',
                'ex': 'foo.exe --dostuff bar'}),

            ('it:cmd:session', ('guid', {}), {
                'doc': 'A command line session with multiple commands run over time.'}),

            ('it:cmd:history', ('guid', {}), {
                'doc': 'A single command executed within a session.'}),

            ('it:query', ('str', {}), {
                'doc': 'A unique query string.'}),

            ('it:exec:query', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of an executed query.'}),

            ('it:exec:mutex', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A mutex created by a process at runtime.'}),

            ('it:exec:pipe', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'A named pipe created by a process at runtime.'}),

            ('it:exec:fetch', ('guid', {}), {
                'prevnames': ('it:hosturl',),
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host requesting a URL using any protocol scheme.'}),

            ('it:exec:bind', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host binding a listening port.'}),

            ('it:exec:file:add', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host adding a file to a filesystem.'}),

            ('it:exec:file:del', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host deleting a file from a filesystem.'}),

            ('it:exec:file:read', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host reading a file from a filesystem.'}),

            ('it:exec:file:write', ('guid', {}), {
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host writing a file to a filesystem.'}),

            ('it:exec:windows:registry:get', ('guid', {}), {
                'prevnames': ('it:exec:reg:get',),
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host getting a registry key.', }),

            ('it:exec:windows:registry:set', ('guid', {}), {
                'prevnames': ('it:exec:reg:set',),
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host creating or setting a registry key.', }),

            ('it:exec:windows:registry:del', ('guid', {}), {
                'prevnames': ('it:exec:reg:del',),
                'interfaces': (
                    ('it:host:activity', {}),
                ),
                'doc': 'An instance of a host deleting a registry key.', }),

            ('it:app:yara:rule', ('meta:rule', {}), {

                'interfaces': (
                    ('doc:authorable', {'template': {
                        'title': 'YARA rule', 'syntax': 'yara'}}),
                ),
                'doc': 'A YARA rule unique identifier.'}),

            ('it:app:yara:target', ('ndef', {'forms': ('file:bytes', 'it:exec:proc',
                                                          'inet:ip', 'inet:fqdn', 'inet:url')}), {
                'doc': 'An ndef type which is limited to forms which YARA rules can match.'}),

            ('it:app:yara:match', ('guid', {}), {
                'interfaces': (
                    ('meta:matchish', {'template': {'rule': 'YARA rule',
                                                    'rule:type': 'it:app:yara:rule',
                                                    'match:type': 'it:app:yara:target'}}),
                ),
                'doc': 'A YARA rule which can match files, processes, or network traffic.'}),

            ('it:sec:stix:bundle', ('guid', {}), {
                'doc': 'A STIX bundle.'}),

            ('it:sec:stix:indicator', ('guid', {}), {
                'doc': 'A STIX indicator pattern.'}),

            ('it:app:snort:rule', ('meta:rule', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'title': 'snort rule'}}),
                ),
                'doc': 'A snort rule.'}),

            ('it:app:snort:match', ('guid', {}), {
                'prevnames': ('it:app:snort:hit',),
                'interfaces': (
                    ('meta:matchish', {'template': {'rule': 'Snort rule',
                                       'rule:type': 'it:app:snort:rule',
                                       'target:type': 'it:app:snort:target'}}),
                ),
                'doc': 'An instance of a snort rule hit.'}),

            ('it:app:snort:target', ('ndef', {'forms': ('inet:flow',)}), {
                'doc': 'An ndef type which is limited to forms which snort rules can match.'}),

            ('it:sec:c2:config', ('guid', {}), {
                'doc': 'An extracted C2 config from an executable.'}),

            ('it:host:tenancy', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'host tenancy'}}),
                ),
                'doc': 'A time window where a host was a tenant run by another host.'}),

            ('it:software:image:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of software image types.'}),

            ('it:software:image', ('guid', {}), {
                'interfaces': (
                    ('inet:service:object', {
                        'template': {'service:base': 'software image'}}),
                ),
                'doc': 'The base image used to create a container or OS.'}),

            ('it:storage:mount', ('guid', {}), {
                'doc': 'A storage volume that has been attached to an image.'}),

            ('it:storage:volume', ('guid', {}), {
                'doc': 'A physical or logical storage volume that can be attached to a physical/virtual machine or container.'}),

            ('it:storage:volume:type:taxonomy', ('taxonomy', {}), {
                'ex': 'network.smb',
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of storage volume types.'}),
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

            (('it:sec:stix:indicator', 'detects', 'entity:campaign'), {
                'doc': 'The STIX indicator detects the campaign.'}),

            (('it:sec:stix:indicator', 'detects', 'entity:contact'), {
                'doc': 'The STIX indicator detects the entity.'}),

            (('it:sec:stix:indicator', 'detects', 'it:software'), {
                'doc': 'The STIX indicator detects the software.'}),

            (('it:sec:stix:indicator', 'detects', 'meta:technique'), {
                'doc': 'The STIX indicator detects the technique.'}),

            (('it:sec:stix:indicator', 'detects', 'ou:org'), {
                'doc': 'The STIX indicator detects the organization.'}),

            (('it:software', 'runson', 'it:software'), {
                'doc': 'The source software can be run within the target software.'}),

            (('it:software', 'runson', 'it:hardware'), {
                'doc': 'The source software can be run on the target hardware.'}),

            (('it:software', 'uses', 'meta:technique'), {
                'doc': 'The software uses the technique.'}),

            (('it:software', 'uses', 'risk:vuln'), {
                'doc': 'The software uses the vulnerability.'}),

            (('it:software', 'creates', 'file:exemplar:entry'), {
                'doc': 'The software creates the file entry.'}),

            (('it:software', 'creates', 'it:os:windows:registry:entry'), {
                'doc': 'The software creates the Microsoft Windows registry entry.'}),

            (('it:software', 'creates', 'it:os:windows:service'), {
                'doc': 'The software creates the Microsoft Windows service.'}),

            (('it:exec:query', 'found', None), {
                'doc': 'The target node was returned as a result of running the query.'}),

            (('it:app:snort:rule', 'detects', 'risk:vuln'), {
                'doc': 'The snort rule detects use of the vulnerability.'}),

            (('it:app:snort:rule', 'detects', 'it:software'), {
                'doc': 'The snort rule detects use of the software.'}),

            (('it:app:snort:rule', 'detects', 'risk:tool:software'), {
                'doc': 'The snort rule detects use of the tool.'}),

            (('it:app:snort:rule', 'detects', 'meta:technique'), {
                'doc': 'The snort rule detects use of the technique.'}),

            (('it:app:snort:rule', 'detects', 'it:softwarename'), {
                'doc': 'The snort rule detects the named software.'}),

            (('it:app:yara:rule', 'detects', 'it:software'), {
                'doc': 'The YARA rule detects the software.'}),

            (('it:app:yara:rule', 'detects', 'risk:tool:software'), {
                'doc': 'The YARA rule detects the tool.'}),

            (('it:app:yara:rule', 'detects', 'meta:technique'), {
                'doc': 'The YARA rule detects the technique.'}),

            (('it:app:yara:rule', 'detects', 'risk:vuln'), {
                'doc': 'The YARA rule detects the vulnerability.'}),

            (('it:app:yara:rule', 'detects', 'it:softwarename'), {
                'doc': 'The YARA rule detects the named software.'}),

            (('it:dev:repo', 'has', 'inet:url'), {
                'doc': 'The repo has content hosted at the URL.'}),

            (('it:dev:repo:commit', 'has', 'it:dev:repo:entry'), {
                'doc': 'The file entry is present in the commit version of the repository.'}),

            (('it:log:event', 'about', None), {
                'doc': 'The it:log:event is about the target node.'}),

            (('it:software', 'uses', 'it:software'), {
                'doc': 'The source software uses the target software.'}),

            (('it:software', 'has', 'it:software'), {
                'doc': 'The source software directly includes the target software.'}),

            (('it:sec:stix:indicator', 'detects', None), {
                'doc': 'The STIX indicator can detect evidence of the target node.'}),
        ),
        'forms': (
            ('it:hostname', {}, ()),

            ('it:host', {}, (

                ('name', ('it:hostname', {}), {
                    'doc': 'The name of the host or system.'}),

                ('desc', ('str', {}), {
                    'doc': 'A free-form description of the host.'}),

                ('ip', ('inet:ip', {}), {
                    'doc': 'The last known IP address for the host.',
                    'prevnames': ('ipv4',)}),

                ('os', ('it:software', {}), {
                    'doc': 'The operating system of the host.'}),

                ('os:name', ('it:softwarename', {}), {
                    'doc': 'A software product name for the host operating system. Used for entity resolution.'}),

                ('hardware', ('it:hardware', {}), {
                    'doc': 'The hardware specification for this host.'}),

                ('serial', ('base:id', {}), {
                    'doc': 'The serial number of the host.'}),

                ('operator', ('entity:contact', {}), {
                    'doc': 'The operator of the host.'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The org that operates the given host.'}),

                ('id', ('str', {}), {
                    'doc': 'An external identifier for the host.'}),

                ('keyboard:layout', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The primary keyboard layout configured on the host.'}),

                ('keyboard:language', ('lang:language', {}), {
                    'doc': 'The primary keyboard input language configured on the host.'}),

                ('image', ('it:software:image', {}), {
                    'doc': 'The container image or OS image running on the host.'}),
            )),

            ('it:host:tenancy', {}, (

                ('lessor', ('it:host', {}), {
                    'doc': 'The host which provides runtime resources to the tenant host.'}),

                ('tenant', ('it:host', {}), {
                    'doc': 'The host which is run within the resources provided by the lessor.'}),

            )),

            ('it:software:image:type:taxonomy', {}, ()),
            ('it:software:image', {}, (

                ('name', ('it:softwarename', {}), {
                    'doc': 'The name of the image.'}),

                ('type', ('it:software:image:type:taxonomy', {}), {
                    'doc': 'The type of software image.'}),

                ('published', ('time', {}), {
                    'doc': 'The time the image was published.'}),

                ('publisher', ('entity:contact', {}), {
                    'doc': 'The contact information of the org or person who published the image.'}),

                ('parents', ('array', {'type': 'it:software:image', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of parent images in precedence order.'}),
            )),

            ('it:storage:volume:type:taxonomy', {}, ()),
            ('it:storage:volume', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The unique volume ID.'}),

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the volume.'}),

                ('type', ('it:storage:volume:type:taxonomy', {}), {
                    'doc': 'The type of storage volume.'}),

                ('size', ('int', {'min': 0}), {
                    'doc': 'The size of the volume in bytes.'}),
            )),

            ('it:storage:mount', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host that has mounted the volume.'}),

                ('volume', ('it:storage:volume', {}), {
                    'doc': 'The volume that the host has mounted.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path where the volume is mounted in the host filesystem.'}),
            )),

            ('it:log:event:type:taxonomy', {}, ()),
            ('it:log:event', {}, (

                ('mesg', ('str', {}), {
                    'doc': 'The log message text.'}),

                ('type', ('it:log:event:type:taxonomy', {}), {
                    'ex': 'windows.eventlog.securitylog',
                    'doc': 'The type of log event.'}),

                ('severity', ('int', {'enums': loglevels}), {
                    'doc': 'A log level integer that increases with severity.'}),

                ('data', ('data', {}), {
                    'doc': 'A raw JSON record of the log event.'}),

                ('id', ('str', {}), {
                    'doc': 'An external id that uniquely identifies this log entry.'}),

                ('product', ('it:software', {}), {
                    'doc': 'The software which produced the log entry.'}),

                ('service:platform', ('inet:service:platform', {}), {
                    'doc': 'The service platform which generated the log event.'}),

                ('service:account', ('inet:service:account', {}), {
                    'doc': 'The service account which generated the log event.'}),

            )),

            ('it:network:type:taxonomy', {}, ()),
            ('it:network', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the network.'}),

                ('desc', ('text', {}), {
                    'doc': 'A brief description of the network.'}),

                ('type', ('it:network:type:taxonomy', {}), {
                    'doc': 'The type of network.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period when the network existed.'}),

                # FIXME ownable / owner / operatable?
                ('org', ('ou:org', {}), {
                    'doc': 'The org that owns/operates the network.'}),

                ('net', ('inet:net', {}), {
                    'doc': 'The optional contiguous IP address range of this network.',
                    'prevnames': ('net4', 'net6')}),

                ('dns:resolvers', ('array', {'type': 'inet:server', 'sorted': False, 'uniq': False,
                                             'typeopts': {'defport': 53, 'defproto': 'udp'}}), {
                    'doc': 'An array of DNS servers configured to resolve requests for hosts on the network.'})

            )),

            ('it:host:account', {}, (

                ('user', ('inet:user', {}), {
                    'doc': 'The username associated with the account.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period where the account existed.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'Additional contact information associated with this account.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host where the account is registered.'}),

                ('posix:uid', ('int', {}), {
                    'ex': '1001',
                    'doc': 'The user ID of the account.'}),

                ('posix:gid', ('int', {}), {
                    'ex': '1001',
                    'doc': 'The primary group ID of the account.'}),

                ('posix:gecos', ('int', {}), {
                    'doc': 'The GECOS field for the POSIX account.'}),

                ('posix:home', ('file:path', {}), {
                    'ex': '/home/visi',
                    'doc': "The path to the POSIX account's home directory."}),

                ('posix:shell', ('file:path', {}), {
                    'ex': '/bin/bash',
                    'doc': "The path to the POSIX account's default shell."}),

                ('windows:sid', ('it:os:windows:sid', {}), {
                    'doc': 'The Microsoft Windows Security Identifier of the account.'}),

                ('service:account', ('inet:service:account', {}), {
                    'doc': 'The optional service account which the local account maps to.'}),

                ('groups', ('array', {'type': 'it:host:group'}), {
                    'doc': 'Groups that the account is a member of.'}),
            )),
            ('it:host:group', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the group.'}),

                ('desc', ('text', {}), {
                    'doc': 'A brief description of the group.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host where the group was created.'}),

                ('posix:gid', ('int', {}), {
                    'ex': '1001',
                    'doc': 'The primary group ID of the account.'}),

                ('windows:sid', ('it:os:windows:sid', {}), {
                    'doc': 'The Microsoft Windows Security Identifier of the group.'}),

                ('service:role', ('inet:service:role', {}), {
                    'doc': 'The optional service role which the local group maps to.'}),

                ('groups', ('array', {'type': 'it:host:group'}), {
                    'doc': 'Groups that are a member of this group.'}),
            )),
            ('it:host:login', {}, (

                ('server:host', ('it:host', {}), {
                    'prevnames': ('host',),
                    'doc': 'The server host which received the login.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period when the login session was active.'}),

                ('success', ('bool', {}), {
                    'doc': 'Set to false to indicate an unsuccessful logon attempt.'}),

                ('account', ('it:host:account', {}), {
                    'doc': 'The account that logged in.'}),

                ('creds', ('array', {'type': 'auth:credential'}), {
                    'doc': 'The credentials that were used to login.'}),
            )),
            ('it:host:hosted:url', {}, (

                ('host', ('it:host', {}), {
                    'computed': True,
                    'doc': 'Host serving a url.'}),

                ('url', ('inet:url', {}), {
                    'computed': True,
                    'doc': 'URL available on the host.'}),
            )),
            ('it:exec:screenshot', {}, (

                ('image', ('file:bytes', {}), {
                    'doc': 'The image file.'}),

                ('desc', ('text', {}), {
                    'doc': 'A brief description of the screenshot.'})
            )),
            ('it:dev:str', {'on': {'add': {'q': '[ :norm=$node ]'}}}, (

                ('norm', ('str', {'lower': True}), {
                    'doc': 'Lower case normalized version of the it:dev:str.'}),

            )),
            ('it:sec:cve', {}, ()),
            ('it:sec:cpe', {}, (

                ('v2_2', ('it:sec:cpe:v2_2', {}), {
                    'doc': 'The CPE 2.2 string which is equivalent to the primary property.'}),

                ('part', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "part" field from the CPE 2.3 string.'}),

                ('vendor', ('meta:name', {}), {
                    'computed': True,
                    'doc': 'The "vendor" field from the CPE 2.3 string.'}),

                ('product', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "product" field from the CPE 2.3 string.'}),

                ('version', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "version" field from the CPE 2.3 string.'}),

                ('update', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "update" field from the CPE 2.3 string.'}),

                ('edition', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "edition" field from the CPE 2.3 string.'}),

                ('language', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "language" field from the CPE 2.3 string.'}),

                ('sw_edition', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "sw_edition" field from the CPE 2.3 string.'}),

                ('target_sw', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "target_sw" field from the CPE 2.3 string.'}),

                ('target_hw', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "target_hw" field from the CPE 2.3 string.'}),

                ('other', ('str', {'lower': True}), {
                    'computed': True,
                    'doc': 'The "other" field from the CPE 2.3 string.'}),
            )),
            ('it:sec:cwe', {}, (

                ('name', ('str', {}), {
                    'doc': 'The CWE description field.',
                    'ex': 'Buffer Copy without Checking Size of Input (Classic Buffer Overflow)'}),

                ('desc', ('text', {}), {
                    'doc': 'The CWE description field.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL linking this CWE to a full description.'}),

                ('parents', ('array', {'type': 'it:sec:cwe', 'split': ','}), {
                    'doc': 'An array of ChildOf CWE Relationships.'}),
            )),

            ('it:sec:metrics', {}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The organization whose security program is being measured.'}),

                ('org:name', ('entity:name', {}), {
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

                ('desc', ('text', {}), {
                    'doc': 'Description of the scan and scope.'}),

                ('id', ('str', {}), {
                    'doc': 'An externally generated ID for the scan.'}),

                ('ext:url', ('inet:url', {}), {
                    'doc': 'An external URL which documents the scan.'}),

                ('software', ('it:software', {}), {
                    'doc': 'The scanning software used.'}),

                ('software:name', ('it:softwarename', {}), {
                    'doc': 'The name of the scanner software.'}),

                ('operator', ('entity:contact', {}), {
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

                ('id', ('str', {}), {
                    'doc': 'An externally generated ID for the scan result.'}),

                ('ext:url', ('inet:url', {}), {
                    'doc': 'An external URL which documents the scan result.'}),

                ('mitigation', ('meta:technique', {}), {
                    'doc': 'The mitigation used to address this asset vulnerability.'}),

                ('mitigated', ('time', {}), {
                    'doc': 'The time that the vulnerability in the asset was mitigated.'}),

                ('priority', ('meta:score', {}), {
                    'doc': 'The priority of mitigating the vulnerability.'}),

                ('severity', ('meta:score', {}), {
                    'doc': 'The severity of the vulnerability in the asset. Use "none" for no vulnerability discovered.'}),
            )),

            ('it:mitre:attack:group:id', {}, ()),
            ('it:mitre:attack:tactic:id', {}, ()),
            ('it:mitre:attack:technique:id', {}, ()),
            ('it:mitre:attack:mitigation:id', {}, ()),
            ('it:mitre:attack:software:id', {}, ()),
            ('it:mitre:attack:campaign:id', {}, ()),

            ('it:dev:int', {}, ()),
            ('it:os:windows:registry:key', {}, (
                ('parent', ('it:os:windows:registry:key', {}), {
                    'doc': 'The parent key.'}),
            )),
            ('it:os:windows:registry:entry', {}, (

                ('key', ('it:os:windows:registry:key', {}), {
                    'doc': 'The Windows registry key.'}),

                ('name', ('it:dev:str', {}), {
                    'doc': 'The name of the registry value within the key.'}),

                ('value', ('ndef', {'forms': ('file:bytes', 'it:dev:int', 'it:dev:str')}), {
                    'prevnames': ('str', 'int', 'bytes'),
                    'doc': 'The value assigned to the name within the key.'}),
            )),

            ('it:dev:repo:type:taxonomy', {}, ()),
            ('it:dev:repo', {}, (

                ('name', ('str', {'lower': True}), {
                    'doc': 'The name of the repository.'}),

                ('desc', ('text', {}), {
                    'doc': 'A free-form description of the repository.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the repository is hosted.'}),

                ('type', ('it:dev:repo:type:taxonomy', {}), {
                    'doc': 'The type of the version control system used.',
                    'ex': 'svn'}),

                ('submodules', ('array', {'type': 'it:dev:repo:commit'}), {
                    'doc': "An array of other repos that this repo has as submodules, pinned at specific commits."}),
            )),

            ('it:dev:repo:remote', {}, (

                ('name', ('meta:name', {}), {
                    'ex': 'origin',
                    'doc': 'The name the repo is using for the remote repo.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL the repo is using to access the remote repo.'}),

                ('repo', ('it:dev:repo', {}), {
                    'doc': 'The repo that is tracking the remote repo.'}),

                ('remote', ('it:dev:repo', {}), {
                    'doc': 'The instance of the remote repo.'}),
            )),

            ('it:dev:repo:branch', {}, (

                ('parent', ('it:dev:repo:branch', {}), {
                    'doc': 'The branch this branch was branched from.'}),

                ('start', ('it:dev:repo:commit', {}), {
                    'doc': 'The commit in the parent branch this branch was created at.'}),

                ('name', ('str', {}), {
                    'doc': 'The name of the branch.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the branch is hosted.'}),

                ('merged', ('time', {}), {
                    'doc': 'The time this branch was merged back into its parent.'}),
            )),

            ('it:dev:repo:commit', {}, (

                ('repo', ('it:dev:repo', {}), {
                    'doc': 'The repository the commit lives in.'}),

                ('parents', ('array', {'type': 'it:dev:repo:commit', 'sorted': False}), {
                    'doc': 'The commit or commits this commit is immediately based on.'}),

                ('branch', ('it:dev:repo:branch', {}), {
                    'doc': 'The name of the branch the commit was made to.'}),

                ('mesg', ('text', {}), {
                    'doc': 'The commit message describing the changes in the commit.'}),

                ('id', ('meta:id', {}), {
                    'doc': 'The version control system specific commit identifier.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the commit is hosted.'}),
            )),

            ('it:dev:repo:diff', {}, (

                ('commit', ('it:dev:repo:commit', {}), {
                    'doc': 'The commit that produced this diff.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file after the commit has been applied.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path to the file in the repo that the diff is being applied to.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the diff is hosted.'}),
            )),

            ('it:dev:repo:entry', {}, (

                ('repo', ('it:dev:repo', {}), {
                    'doc': 'The repository which contains the file.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file which the repository contains.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path to the file in the repository.'}),
            )),

            ('it:dev:repo:issue', {}, (

                ('repo', ('it:dev:repo', {}), {
                    'doc': 'The repo where the issue was logged.'}),

                ('title', ('str', {'lower': True}), {
                    'doc': 'The title of the issue.'}),

                ('desc', ('text', {}), {
                    'doc': 'The text describing the issue.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the issue was updated.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the issue is hosted.'}),

                ('id', ('meta:id', {}), {
                    'doc': 'The ID of the issue in the repository system.'}),
            )),

            ('it:dev:repo:label', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The ID of the label.'}),

                ('title', ('str', {'lower': True}), {
                    'doc': 'The human friendly name of the label.'}),

                ('desc', ('text', {}), {
                    'doc': 'The description of the label.'}),

            )),

            ('it:dev:repo:issue:label', {}, (

                ('issue', ('it:dev:repo:issue', {}), {
                    'doc': 'The issue the label was applied to.'}),

                ('label', ('it:dev:repo:label', {}), {
                    'doc': 'The label that was applied to the issue.'}),
            )),

            ('it:dev:repo:issue:comment', {}, (
                ('issue', ('it:dev:repo:issue', {}), {
                    'doc': 'The issue thread that the comment was made in.',
                }),
                ('text', ('text', {}), {
                    'doc': 'The body of the comment.',
                }),
                ('replyto', ('it:dev:repo:issue:comment', {}), {
                    'doc': 'The comment that this comment is replying to.',
                }),
                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the comment is hosted.',
                }),
                ('updated', ('time', {}), {
                    'doc': 'The time the comment was updated.',
                }),
            )),

            ('it:dev:repo:diff:comment', {}, (

                ('diff', ('it:dev:repo:diff', {}), {
                    'doc': 'The diff the comment is being added to.'}),

                ('text', ('text', {}), {
                    'doc': 'The body of the comment.'}),

                ('replyto', ('it:dev:repo:diff:comment', {}), {
                    'doc': 'The comment that this comment is replying to.'}),

                ('line', ('int', {}), {
                    'doc': 'The line in the file that is being commented on.'}),

                ('offset', ('int', {}), {
                    'doc': 'The offset in the line in the file that is being commented on.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the comment is hosted.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the comment was updated.'}),

            )),

            ('it:hardware:type:taxonomy', {
                'prevnames': ('it:hardwaretype',)}, ()),

            ('it:hardware', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of this hardware specification.'}),

                ('type', ('it:hardware:type:taxonomy', {}), {
                    'doc': 'The type of hardware.'}),

                ('desc', ('text', {}), {
                    'doc': 'A brief description of the hardware.'}),

                ('cpe', ('it:sec:cpe', {}), {
                    'doc': 'The NIST CPE 2.3 string specifying this hardware.'}),

                ('manufacturer', ('entity:actor', {}), {
                    'doc': 'The organization that manufactures this hardware.'}),

                ('manufacturer:name', ('entity:name', {}), {
                    'doc': 'The name of the organization that manufactures this hardware.'}),

                ('model', ('base:name', {}), {
                    'doc': 'The model name or number for this hardware specification.'}),

                ('version', ('it:version', {}), {
                    'doc': 'Version string associated with this hardware specification.'}),

                ('released', ('time', {}), {
                    'doc': 'The initial release date for this hardware.'}),

                ('parts', ('array', {'type': 'it:hardware'}), {
                    'doc': 'An array of it:hardware parts included in this hardware specification.'}),
            )),
            ('it:host:component', {}, (

                ('hardware', ('it:hardware', {}), {
                    'doc': 'The hardware specification of this component.'}),

                ('serial', ('meta:id', {}), {
                    'doc': 'The serial number of this component.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The it:host which has this component installed.'}),
            )),

            ('it:softid', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The ID issued by the software to the host.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host which was issued the ID by the software.'}),

                ('software', ('it:software', {}), {
                    'prevnames': ('soft',),
                    'doc': 'The software which issued the ID to the host.'}),

                ('software:name', ('it:softwarename', {}), {
                    'prevnames': ('soft:name',),
                    'doc': 'The name of the software which issued the ID to the host.'}),
            )),

            ('it:adid', {}, ()),
            ('it:os:android:perm', {}, ()),
            ('it:os:android:intent', {}, ()),

            ('it:os:android:reqperm', {}, (

                ('app', ('it:software', {}), {'computed': True,
                    'doc': 'The android app which requests the permission.'}),

                ('perm', ('it:os:android:perm', {}), {'computed': True,
                    'doc': 'The android permission requested by the app.'}),
            )),

            ('it:os:android:ilisten', {}, (

                ('app', ('it:software', {}), {'computed': True,
                    'doc': 'The app software which listens for the android intent.'}),

                ('intent', ('it:os:android:intent', {}), {'computed': True,
                    'doc': 'The android intent which is listened for by the app.'}),
            )),

            ('it:os:android:ibroadcast', {}, (

                ('app', ('it:software', {}), {'computed': True,
                    'doc': 'The app software which broadcasts the android intent.'}),

                ('intent', ('it:os:android:intent', {}), {'computed': True,
                    'doc': 'The android intent which is broadcast by the app.'}),

            )),

            ('it:softwarename', {}, ()),
            ('it:software:type:taxonomy', {}, ()),
            ('it:software', {}, (

                ('type', ('it:software:type:taxonomy', {}), {
                    'doc': 'The type of software.'}),

                ('parent', ('it:software', {}), {
                    'doc': 'The parent software version or family.'}),

                ('name', ('it:softwarename', {}), {
                    'alts': ('names',),
                    'doc': 'The name of the software.'}),

                ('names', ('array', {'type': 'it:softwarename'}), {
                    'doc': 'Observed/variant names for this software version.'}),

                ('released', ('time', {}), {
                    'doc': 'Timestamp for when the software was released.'}),

                ('cpe', ('it:sec:cpe', {}), {
                    'doc': 'The NIST CPE 2.3 string specifying this software version.'}),

                ('risk:score', ('meta:score', {}), {
                    'doc': 'The risk posed by the software.'}),

            )),

            ('it:host:installed', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host which the software was installed on.'}),

                ('software', ('it:software', {}), {
                    'doc': 'The software installed on the host.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period when the software was installed on the host.'}),
            )),

            ('it:av:signame', {}, ()),

            ('it:av:scan:result', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time the scan was run.'}),

                ('verdict', ('int', {'enums': suslevels}), {
                    'doc': 'The scanner provided verdict for the scan.'}),

                ('scanner', ('it:software', {}), {
                    'doc': 'The scanner software used to produce the result.'}),

                ('scanner:name', ('it:softwarename', {}), {
                    'doc': 'The name of the scanner software.'}),

                ('signame', ('it:av:signame', {}), {
                    'doc': 'The name of the signature returned by the scanner.'}),

                ('categories', ('array', {'type': 'str',
                                          'typeopts': {'lower': True, 'onespace': True}}), {
                    'doc': 'A list of categories for the result returned by the scanner.'}),

                ('target', ('ndef', {'forms': ('file:bytes', 'it:exec:proc', 'it:host',
                                               'inet:fqdn', 'inet:url', 'inet:ip')}), {
                    'doc': 'The target of the scan.'}),

                ('multi:scan', ('it:av:scan:result', {}), {
                    'doc': 'Set if this result was part of running multiple scanners.'}),

                ('multi:count', ('int', {'min': 0}), {
                    'doc': 'The total number of scanners which were run by a multi-scanner.'}),

                ('multi:count:benign', ('int', {'min': 0}), {
                    'doc': 'The number of scanners which returned a benign verdict.'}),

                ('multi:count:unknown', ('int', {'min': 0}), {
                    'doc': 'The number of scanners which returned a unknown/unsupported verdict.'}),

                ('multi:count:suspicious', ('int', {'min': 0}), {
                    'doc': 'The number of scanners which returned a suspicious verdict.'}),

                ('multi:count:malicious', ('int', {'min': 0}), {
                    'doc': 'The number of scanners which returned a malicious verdict.'}),
            )),

            ('it:cmd', {}, ()),
            ('it:cmd:session', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host where the command line session was executed.'}),

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The process which was interpreting this command line session.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period over which the command line session was running.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file containing the command history such as a .bash_history file.'}),

                ('account', ('ndef', {'forms': ('it:host:account', 'inet:service:account')}), {
                    'doc': 'The account which executed the commands in the session.'}),
            )),
            ('it:cmd:history', {}, (

                ('cmd', ('it:cmd', {}), {
                    'doc': 'The command that was executed.'}),

                ('session', ('it:cmd:session', {}), {
                    'doc': 'The session that contains this history entry.'}),

                ('time', ('time', {}), {
                    'doc': 'The time that the command was executed.'}),

                ('index', ('int', {}), {
                    'doc': 'Used to order the commands when times are not available.'}),
            )),
            ('it:exec:proc', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host that executed the process. May be an actual or a virtual / notional host.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The file considered the "main" executable for the process. For example, rundll32.exe may be considered the "main" executable for DLLs loaded by that program.'}),

                ('cmd', ('it:cmd', {}), {
                    'doc': 'The command string used to launch the process, including any command line parameters.'}),

                ('cmd:history', ('it:cmd:history', {}), {
                    'doc': 'The command history entry which caused this process to be run.'}),

                ('pid', ('int', {}), {
                    'doc': 'The process ID.'}),

                ('time', ('time', {}), {
                    'doc': 'The start time for the process.'}),

                ('name', ('str', {}), {
                    'doc': 'The display name specified by the process.'}),

                ('exited', ('time', {}), {
                    'doc': 'The time the process exited.'}),

                ('exitcode', ('int', {}), {
                    'doc': 'The exit code for the process.'}),

                ('account', ('it:host:account', {}), {
                    'doc': 'The account of the process owner.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path to the executable of the process.'}),

                ('src:proc', ('it:exec:proc', {}), {
                    'doc': 'The process which created the process.'}),

                ('killedby', ('it:exec:proc', {}), {
                    'doc': 'The process which killed this process.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),

                # TODO
                # ('windows:task', ('it:os:windows:task', {}), {
                #     'doc': 'The Microsoft Windows scheduled task responsible for starting the process.'}),

                ('windows:service', ('it:os:windows:service', {}), {
                    'doc': 'The Microsoft Windows service responsible for starting the process.'}),
            )),

            ('it:os:windows:service', {}, (

                ('host', ('it:host', {}), {
                    'doc': 'The host that the service was configured on.'}),

                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The name of the service from the registry key within Services.'}),

                # TODO flags...
                ('type', ('int', {'min': 0}), {
                    'doc': 'The type of service from the Type registry key.'}),

                ('start', ('int', {'min': 0}), {
                    'doc': 'The start configuration of the service from the Start registry key.'}),

                ('errorcontrol', ('int', {'min': 0}), {
                    'doc': 'The service error handling behavior from the ErrorControl registry key.'}),

                ('displayname', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The friendly name of the service from the DisplayName registry key.'}),

                ('description', ('text', {}), {
                    'doc': 'The description of the service from the Description registry key.'}),

                ('imagepath', ('file:path', {}), {
                    'doc': 'The path to the service binary from the ImagePath registry key.'}),
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

                ('offset', ('int', {}), {
                    'doc': 'The offset of the last record consumed from the query.'}),

                ('account', ('ndef', {'forms': ('syn:user', 'it:host:account', 'inet:service:account')}), {
                    'doc': 'The account which executed the query.'}),

                ('platform', ('inet:service:platform', {}), {
                    'doc': 'The service platform which was queried.'}),
            )),
            ('it:exec:thread', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The process which contains the thread.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the thread was created.'}),

                ('exited', ('time', {}), {
                    'doc': 'The time the thread exited.'}),

                ('exitcode', ('int', {}), {
                    'doc': 'The exit code or return value for the thread.'}),

                ('src:proc', ('it:exec:proc', {}), {
                    'doc': 'An external process which created the thread.'}),

                ('src:thread', ('it:exec:thread', {}), {
                    'doc': 'The thread which created this thread.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:loadlib', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The process where the library was loaded.'}),

                ('va', ('int', {}), {
                    'doc': 'The base memory address where the library was loaded in the process.'}),

                ('loaded', ('time', {}), {
                    'doc': 'The time the library was loaded.'}),

                ('unloaded', ('time', {}), {
                    'doc': 'The time the library was unloaded.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path that the library was loaded from.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The library file that was loaded.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:mmap', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The process where the memory was mapped.'}),

                ('va', ('int', {}), {
                    'doc': 'The base memory address where the map was created in the process.'}),

                ('size', ('int', {}), {
                    'doc': 'The size of the memory map in bytes.'}),

                ('perms:read', ('bool', {}), {
                    'doc': 'True if the mmap is mapped with read permissions.'}),

                ('perms:write', ('bool', {}), {
                    'doc': 'True if the mmap is mapped with write permissions.'}),

                ('perms:execute', ('bool', {}), {
                    'doc': 'True if the mmap is mapped with execute permissions.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the memory map was created.'}),

                ('deleted', ('time', {}), {
                    'doc': 'The time the memory map was deleted.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The file path if the mmap is a mapped view of a file.'}),

                ('hash:sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'A SHA256 hash of the memory map.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:mutex', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that created the mutex.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that created the mutex.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that created the mutex.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the mutex was created.'}),

                ('name', ('it:dev:str', {}), {
                    'doc': 'The mutex string.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:pipe', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that created the named pipe.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that created the named pipe.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that created the named pipe.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the named pipe was created.'}),

                ('name', ('it:dev:str', {}), {
                    'doc': 'The named pipe string.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:fetch', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that requested the URL.'}),

                ('browser', ('it:software', {}), {
                    'doc': 'The software version of the browser.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that requested the URL.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that requested the URL.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the URL was requested.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL that was requested.'}),

                ('page:pdf', ('file:bytes', {}), {
                    'doc': 'The rendered DOM saved as a PDF file.'}),

                ('page:html', ('file:bytes', {}), {
                    'doc': 'The rendered DOM saved as an HTML file.'}),

                ('page:image', ('file:bytes', {}), {
                    'doc': 'The rendered DOM saved as an image.'}),

                ('http:request', ('inet:http:request', {}), {
                    'doc': 'The HTTP request made to retrieve the initial URL contents.'}),

                ('client', ('inet:client', {}), {
                    'doc': 'The address of the client during the URL retrieval.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:bind', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that bound the listening port.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that bound the listening port.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that bound the listening port.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the port was bound.'}),

                ('server', ('inet:server', {}), {
                    'doc': 'The socket address of the server when binding the port.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),

            ('it:exec:file:add', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that created the new file.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that created the new file.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that created the new file.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the file was created.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path where the file was created.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that was created.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:file:del', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that deleted the file.', }),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that deleted the file.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that deleted the file.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the file was deleted.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path where the file was deleted.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that was deleted.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:file:read', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that read the file.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that read the file.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that read the file.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the file was read.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path where the file was read.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that was read.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:file:write', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that wrote to / modified the existing file.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that wrote to the file.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that wrote to the file.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the file was written to/modified.'}),

                ('path', ('file:path', {}), {
                    'doc': 'The path where the file was written to/modified.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that was modified.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:windows:registry:get', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that read the registry.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that read the registry.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that read the registry.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the registry was read.'}),

                ('entry', ('it:os:windows:registry:entry', {}), {
                    'prevnames': ('reg',),
                    'doc': 'The registry key or value that was read.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:windows:registry:set', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that wrote to the registry.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that wrote to the registry.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that wrote to the registry.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the registry was written to.'}),

                ('entry', ('it:os:windows:registry:entry', {}), {
                    'prevnames': ('reg',),
                    'doc': 'The registry key or value that was written to.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),
            ('it:exec:windows:registry:del', {}, (

                ('proc', ('it:exec:proc', {}), {
                    'doc': 'The main process executing code that deleted data from the registry.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host running the process that deleted data from the registry.'}),

                ('exe', ('file:bytes', {}), {
                    'doc': 'The specific file containing code that deleted data from the registry.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the data from the registry was deleted.'}),

                ('entry', ('it:os:windows:registry:entry', {}), {
                    'prevnames': ('reg',),
                    'doc': 'The registry entry that was deleted.'}),

                ('sandbox:file', ('file:bytes', {}), {
                    'doc': 'The initial sample given to a sandbox environment to analyze.'}),
            )),

            ('it:app:snort:rule', {}, (
                ('engine', ('int', {}), {
                    'doc': 'The snort engine ID which can parse and evaluate the rule text.'}),
            )),

            ('it:app:snort:match', {}, (

                ('target', ('ndef', {'forms': ('inet:flow',)}), {
                    'doc': 'The node which matched the snort rule.'}),

                ('sensor', ('it:host', {}), {
                    'doc': 'The sensor host node that produced the match.'}),

                ('dropped', ('bool', {}), {
                    'doc': 'Set to true if the network traffic was dropped due to the match.'}),
            )),

            ('it:sec:stix:bundle', {}, (
                ('id', ('meta:id', {}), {
                    'doc': 'The id field from the STIX bundle.'}),
            )),

            ('it:sec:stix:indicator', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The STIX id field from the indicator pattern.'}),

                ('name', ('str', {}), {
                    'doc': 'The name of the STIX indicator pattern.'}),

                ('confidence', ('int', {'min': 0, 'max': 100}), {
                    'doc': 'The confidence field from the STIX indicator.'}),

                ('revoked', ('bool', {}), {
                    'doc': 'The revoked field from the STIX indicator.'}),

                ('desc', ('str', {}), {
                    'doc': 'The description field from the STIX indicator.'}),

                ('pattern', ('str', {}), {
                    'doc': 'The STIX indicator pattern text.'}),

                ('pattern_type', ('str', {'lower': True, 'enums': 'stix,pcre,sigma,snort,suricata,yara'}), {
                    'doc': 'The STIX indicator pattern type.'}),

                ('created', ('time', {}), {
                    'doc': 'The time that the indicator pattern was first created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time that the indicator pattern was last modified.'}),

                ('labels', ('array', {'type': 'str'}), {
                    'doc': 'The label strings embedded in the STIX indicator pattern.'}),

                ('valid_from', ('time', {}), {
                    'doc': 'The valid_from field from the STIX indicator.'}),

                ('valid_until', ('time', {}), {
                    'doc': 'The valid_until field from the STIX indicator.'}),
            )),

            ('it:app:yara:rule', {}, ()),
            ('it:app:yara:match', {}, (
                ('target', ('ndef', {'forms': ('file:bytes', 'it:host:proc', 'inet:ip',
                                               'inet:fqdn', 'inet:url')}), {
                    'doc': 'The node which matched the YARA rule.'}),
            )),

            ('it:sec:c2:config', {}, (

                ('family', ('it:softwarename', {}), {
                    'doc': 'The name of the software family which uses the config.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that the C2 config was extracted from.'}),

                ('decoys', ('array', {'type': 'inet:url', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of URLs used as decoy connections to obfuscate the C2 servers.'}),

                ('servers', ('array', {'type': 'inet:url', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of connection URLs built from host/port/passwd combinations.'}),

                ('proxies', ('array', {'type': 'inet:url', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of proxy URLs used to communicate with the C2 server.'}),

                ('listens', ('array', {'type': 'inet:url', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of listen URLs that the software should bind.'}),

                ('dns:resolvers', ('array', {'type': 'inet:server', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of inet:servers to use when resolving DNS names.'}),

                ('mutex', ('it:dev:str', {}), {
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

                ('http:headers', ('array', {'type': 'inet:http:header', 'uniq': False, 'sorted': False}), {
                    'doc': 'An array of HTTP headers that the sample should transmit to the C2 server.'}),
            )),
        ),
    }),
)
