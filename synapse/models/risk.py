import synapse.exc as s_exc

import synapse.lib.chop as s_chop
import synapse.lib.types as s_types
import synapse.lib.module as s_module


class CvssV2(s_types.Str):

    def _normPyStr(self, text):
        try:
            return s_chop.cvss2_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None

class CvssV3(s_types.Str):

    def _normPyStr(self, text):
        try:
            return s_chop.cvss3x_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None

class RiskModule(s_module.CoreModule):

    def getModelDefs(self):

        modl = {
            'ctors': (
                ('cvss:v2', 'synapse.models.risk.CvssV2', {}, {
                    'doc': 'A CVSS v2 vector string.', 'ex': '(AV:L/AC:L/Au:M/C:P/I:C/A:N)'
                }),
                ('cvss:v3', 'synapse.models.risk.CvssV3', {}, {
                    'doc': 'A CVSS v3.x vector string.', 'ex': 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L'
                }),
            ),
            'types': (
                ('risk:vuln', ('guid', {}), {
                    'doc': 'A unique vulnerability.'}),

                ('risk:vulnname', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A vulnerability name such as log4j or rowhammer.'}),

                ('risk:vuln:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of vulnerability types.'}),

                ('risk:vuln:soft:range', ('guid', {}), {
                    'doc': 'A contiguous range of software versions which contain a vulnerability.'}),

                ('risk:hasvuln', ('guid', {}), {
                    'doc': 'An instance of a vulnerability present in a target.',
                }),
                ('risk:threat', ('guid', {}), {
                    'doc': 'A threat cluster or subgraph of threat activity, as reported by a specific organization.',
                }),
                ('risk:attack', ('guid', {}), {
                    'doc': 'An instance of an actor attacking a target.',
                }),
                ('risk:alert:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of alert types.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('risk:alert', ('guid', {}), {
                    'doc': 'An instance of an alert which indicates the presence of a risk.',
                }),
                ('risk:compromise', ('guid', {}), {
                    'doc': 'An instance of a compromise and its aggregate impact.',
                }),
                ('risk:mitigation', ('guid', {}), {
                    'doc': 'A mitigation for a specific risk:vuln.',
                }),
                ('risk:attacktype', ('taxonomy', {}), {
                    'doc': 'A taxonomy of attack types.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('risk:compromisetype', ('taxonomy', {}), {
                    'doc': 'A taxonomy of compromise types.',
                    'ex': 'cno.breach',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('risk:tool:software:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of software / tool types.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('risk:availability', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of availability status values.',
                }),
                ('risk:tool:software', ('guid', {}), {
                    'doc': 'A software tool used in threat activity, as reported by a specific organization.',
                }),

                ('risk:alert:verdict:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of verdicts for the origin and validity of the alert.',
                    'interfaces': ('meta:taxonomy',),
                }),

                ('risk:threat:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of threat types.'}),

                ('risk:leak', ('guid', {}), {
                    'doc': 'An event where information was disclosed without permission.'}),

                ('risk:leak:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of leak event types.'}),

                ('risk:extortion', ('guid', {}), {
                    'doc': 'An event where an attacker attempted to extort a victim.'}),

                ('risk:extortion:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of extortion event types.'}),
                ('risk:technique:masquerade', ('guid', {}), {
                    'doc': 'Represents the assessment that a node is designed to resemble another in order to mislead.'}),
            ),
            'edges': (
                # some explicit examples...
                (('risk:attack', 'uses', 'ou:technique'), {
                    'doc': 'The attackers used the technique in the attack.'}),
                (('risk:threat', 'uses', 'ou:technique'), {
                    'doc': 'The threat cluster uses the technique.'}),
                (('risk:tool:software', 'uses', 'ou:technique'), {
                    'doc': 'The tool uses the technique.'}),
                (('risk:compromise', 'uses', 'ou:technique'), {
                    'doc': 'The attackers used the technique in the compromise.'}),

                (('risk:attack', 'uses', 'risk:vuln'), {
                    'doc': 'The attack used the vulnerability.'}),
                (('risk:threat', 'uses', 'risk:vuln'), {
                    'doc': 'The threat cluster uses the vulnerability.'}),
                (('risk:tool:software', 'uses', 'risk:vuln'), {
                    'doc': 'The tool uses the vulnerability.'}),

                (('risk:attack', 'targets', 'ou:industry'), {
                    'doc': 'The attack targeted the industry.'}),
                (('risk:threat', 'targets', 'ou:industry'), {
                    'doc': 'The threat cluster targets the industry.'}),

                (('risk:threat', 'targets', None), {
                    'doc': 'The threat cluster targeted the target node.'}),
                (('risk:threat', 'uses', None), {
                    'doc': 'The threat cluster uses the target node.'}),
                (('risk:attack', 'targets', None), {
                    'doc': 'The attack targeted the target node.'}),
                (('risk:attack', 'uses', None), {
                    'doc': 'The attack used the target node to facilitate the attack.'}),
                (('risk:tool:software', 'uses', None), {
                    'doc': 'The tool uses the target node.'}),
                (('risk:compromise', 'stole', None), {
                    'doc': 'The target node was stolen or copied as a result of the compromise.'}),
                (('risk:mitigation', 'addresses', 'ou:technique'), {
                    'doc': 'The mitigation addresses the technique.'}),

                (('risk:leak', 'leaked', None), {
                    'doc': 'The leak included the disclosure of the target node.'}),

                (('risk:extortion', 'leveraged', None), {
                    'doc': 'The extortion event was based on attacker access to the target node.'}),
            ),
            'forms': (

                ('risk:threat:type:taxonomy', {}, ()),

                ('risk:threat', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': "apt1 (mandiant)",
                        'doc': 'A brief descriptive name for the threat cluster.'}),

                    ('type', ('risk:threat:type:taxonomy', {}), {
                        'doc': 'A type for the threat, as a taxonomy entry.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A description of the threat cluster.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are associated with the threat cluster.'}),

                    ('active', ('ival', {}), {
                        'doc': 'An interval for when the threat cluster is assessed to have been active.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the threat cluster.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the threat cluster.'}),

                    ('reporter:discovered', ('time', {}), {
                        'doc': 'The time that the reporting organization first discovered the threat cluster.'}),

                    ('reporter:published', ('time', {}), {
                        'doc': 'The time that the reporting organization first publicly disclosed the threat cluster.'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The authoritative organization for the threat cluster.'}),

                    ('org:loc', ('loc', {}), {
                        'doc': "The reporting organization's assessed location of the threat cluster."}),

                    ('org:name', ('ou:name', {}), {
                        'ex': 'apt1',
                        'doc': "The reporting organization's name for the threat cluster."}),

                    ('org:names', ('array', {'type': 'ou:name', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the threat cluster, according to the reporting organization.'}),

                    ('country', ('pol:country', {}), {
                        'doc': "The reporting organization's assessed country of origin of the threat cluster."}),

                    ('country:code', ('pol:iso2', {}), {
                        'doc': "The 2 digit ISO 3166 country code for the threat cluster's assessed country of origin."}),

                    ('goals', ('array', {'type': 'ou:goal', 'sorted': True, 'uniq': True}), {
                        'doc': "The reporting organization's assessed goals of the threat cluster."}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': "The reporting organization's assessed sophistication of the threat cluster."}),

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),

                    ('merged:time', ('time', {}), {
                        'doc': 'The time that the reporting organization merged this threat cluster into another.'}),

                    ('merged:isnow', ('risk:threat', {}), {
                        'doc': 'The threat cluster that the reporting organization merged this cluster into.'}),
                )),
                ('risk:availability', {}, {}),
                ('risk:tool:software:taxonomy', {}, ()),
                ('risk:tool:software', {}, (

                    ('tag', ('syn:tag', {}), {
                        'ex': 'rep.mandiant.tabcteng',
                        'doc': 'The tag used to annotate nodes that are associated with the tool.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A description of the tool.'}),

                    ('type', ('risk:tool:software:taxonomy', {}), {
                        'doc': 'A type for the tool, as a taxonomy entry.'}),

                    ('used', ('ival', {}), {
                        'doc': 'An interval for when the tool is assessed to have been deployed.'}),

                    ('availability', ('risk:availability', {}), {
                        'doc': 'The reporting organization\'s assessed availability of the tool.'}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The reporting organization\'s assessed sophistication of the tool.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the tool.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the tool.'}),

                    ('reporter:discovered', ('time', {}), {
                        'doc': 'The time that the reporting organization first discovered the tool.'}),

                    ('reporter:published', ('time', {}), {
                        'doc': 'The time that the reporting organization first publicly disclosed the tool.'}),

                    ('soft', ('it:prod:soft', {}), {
                        'doc': 'The authoritative software family for the tool.'}),

                    ('soft:name', ('it:prod:softname', {}), {
                        'doc': 'The reporting organization\'s name for the tool.'}),

                    ('soft:names', ('array', {'type': 'it:prod:softname', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of alternate names for the tool, according to the reporting organization.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'uniq': True, 'sorted': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),

                )),
                ('risk:mitigation', {}, (
                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The vulnerability that this mitigation addresses.'}),
                    ('name', ('str', {}), {
                        'doc': 'A brief name for this risk mitigation.'}),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the mitigation approach for the vulnerability.'}),
                    ('software', ('it:prod:softver', {}), {
                        'doc': 'A software version which implements a fix for the vulnerability.'}),
                    ('hardware', ('it:prod:hardware', {}), {
                        'doc': 'A hardware version which implements a fix for the vulnerability.'}),
                )),
                ('risk:vulnname', {}, ()),
                ('risk:vuln:type:taxonomy', {}, ()),

                ('risk:vuln', {}, (

                    ('name', ('risk:vulnname', {}), {
                        'doc': 'A user specified name for the vulnerability.'}),

                    ('names', ('array', {'type': 'risk:vulnname', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the vulnerability.'}),

                    ('type', ('risk:vuln:type:taxonomy', {}), {
                        'doc': 'A taxonomy type entry for the vulnerability.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the vulnerability.'}),

                    ('severity', ('meta:severity', {}), {
                        'doc': 'The severity of the vulnerability.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The priority of the vulnerability.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the vulnerability.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the vulnerability.'}),

                    ('mitigated', ('bool', {}), {
                        'doc': 'Set to true if a mitigation/fix is available for the vulnerability.'}),

                    ('exploited', ('bool', {}), {
                        'doc': 'Set to true if the vulnerability has been exploited in the wild.'}),

                    ('timeline:discovered', ('time', {"ismin": True}), {
                        'doc': 'The earliest known discovery time for the vulnerability.'}),

                    ('timeline:published', ('time', {"ismin": True}), {
                        'doc': 'The earliest known time the vulnerability was published.'}),

                    ('timeline:vendor:notified', ('time', {"ismin": True}), {
                        'doc': 'The earliest known vendor notification time for the vulnerability.'}),

                    ('timeline:vendor:fixed', ('time', {"ismin": True}), {
                        'doc': 'The earliest known time the vendor issued a fix for the vulnerability.'}),

                    ('timeline:exploited', ('time', {"ismin": True}), {
                        'doc': 'The earliest known time when the vulnerability was exploited in the wild.'}),

                    ('id', ('str', {'strip': True}), {
                        'doc': 'An identifier for the vulnerability.'}),

                    ('cve', ('it:sec:cve', {}), {
                        'doc': 'The CVE ID of the vulnerability.'}),

                    ('cve:desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The description of the vulnerability according to the CVE database.'}),

                    ('cve:url', ('inet:url', {}), {
                        'doc': 'A URL linking this vulnerability to the CVE description.'}),

                    ('cve:references', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of documentation URLs provided by the CVE database.'}),

                    ('nist:nvd:source', ('ou:name', {}), {
                        'doc': 'The name of the organization which reported the vulnerability to NIST.'}),

                    ('nist:nvd:published', ('time', {}), {
                        'doc': 'The date the vulnerability was first published in the NVD.'}),

                    ('nist:nvd:modified', ('time', {"ismax": True}), {
                        'doc': 'The date the vulnerability was last modified in the NVD.'}),

                    ('cisa:kev:name', ('str', {}), {
                        'doc': 'The name of the vulnerability according to the CISA KEV database.'}),

                    ('cisa:kev:desc', ('str', {}), {
                        'doc': 'The description of the vulnerability according to the CISA KEV database.'}),

                    ('cisa:kev:action', ('str', {}), {
                        'doc': 'The action to mitigate the vulnerability according to the CISA KEV database.'}),

                    ('cisa:kev:vendor', ('ou:name', {}), {
                        'doc': 'The vendor name listed in the CISA KEV database.'}),

                    ('cisa:kev:product', ('it:prod:softname', {}), {
                        'doc': 'The product name listed in the CISA KEV database.'}),

                    ('cisa:kev:added', ('time', {}), {
                        'doc': 'The date the vulnerability was added to the CISA KEV database.'}),

                    ('cisa:kev:duedate', ('time', {}), {
                        'doc': 'The date the action is due according to the CISA KEV database.'}),

                    ('cvss:v2', ('cvss:v2', {}), {
                        'doc': 'The CVSS v2 vector for the vulnerability.'}),

                    ('cvss:v2_0:score', ('float', {}), {
                        'doc': 'The CVSS v2.0 overall score for the vulnerability.'}),

                    ('cvss:v2_0:score:base', ('float', {}), {
                        'doc': 'The CVSS v2.0 base score for the vulnerability.'}),

                    ('cvss:v2_0:score:temporal', ('float', {}), {
                        'doc': 'The CVSS v2.0 temporal score for the vulnerability.'}),

                    ('cvss:v2_0:score:environmental', ('float', {}), {
                        'doc': 'The CVSS v2.0 environmental score for the vulnerability.'}),

                    ('cvss:v3', ('cvss:v3', {}), {
                        'doc': 'The CVSS v3 vector for the vulnerability.'}),

                    ('cvss:v3_0:score', ('float', {}), {
                        'doc': 'The CVSS v3.0 overall score for the vulnerability.'}),

                    ('cvss:v3_0:score:base', ('float', {}), {
                        'doc': 'The CVSS v3.0 base score for the vulnerability.'}),

                    ('cvss:v3_0:score:temporal', ('float', {}), {
                        'doc': 'The CVSS v3.0 temporal score for the vulnerability.'}),

                    ('cvss:v3_0:score:environmental', ('float', {}), {
                        'doc': 'The CVSS v3.0 environmental score for the vulnerability.'}),

                    ('cvss:v3_1:score', ('float', {}), {
                        'doc': 'The CVSS v3.1 overall score for the vulnerability.'}),

                    ('cvss:v3_1:score:base', ('float', {}), {
                        'doc': 'The CVSS v3.1 base score for the vulnerability.'}),

                    ('cvss:v3_1:score:temporal', ('float', {}), {
                        'doc': 'The CVSS v3.1 temporal score for the vulnerability.'}),

                    ('cvss:v3_1:score:environmental', ('float', {}), {
                        'doc': 'The CVSS v3.1 environmental score for the vulnerability.'}),

                    ('cvss:av', ('str', {'enums': 'N,A,P,L'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ac', ('str', {'enums': 'L,H'}), {
                        'disp': {'enums': (('Low', 'L'), ('High', 'H'))},
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:pr', ('str', {'enums': 'N,L,H'}), {
                        'disp': {'enums': (
                            {'title': 'None', 'value': 'N', 'doc': 'FIXME privs stuff'},
                            {'title': 'Low', 'value': 'L', 'doc': 'FIXME privs stuff'},
                            {'title': 'High', 'value': 'H', 'doc': 'FIXME privs stuff'},
                        )},
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ui', ('str', {'enums': 'N,R'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:s', ('str', {'enums': 'U,C'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:c', ('str', {'enums': 'N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:i', ('str', {'enums': 'N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:a', ('str', {'enums': 'N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:e', ('str', {'enums': 'X,U,P,F,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:rl', ('str', {'enums': 'X,O,T,W,U'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:rc', ('str', {'enums': 'X,U,R,C'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mav', ('str', {'enums': 'X,N,A,L,P'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mac', ('str', {'enums': 'X,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mpr', ('str', {'enums': 'X,N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mui', ('str', {'enums': 'X,N,R'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ms', ('str', {'enums': 'X,U,C'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mc', ('str', {'enums': 'X,N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:mi', ('str', {'enums': 'X,N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ma', ('str', {'enums': 'X,N,L,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:cr', ('str', {'enums': 'X,L,M,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ir', ('str', {'enums': 'X,L,M,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:ar', ('str', {'enums': 'X,L,M,H'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :cvss:v3.'}),

                    ('cvss:score', ('float', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use version specific score properties.'}),

                    ('cvss:score:base', ('float', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use version specific score properties.'}),

                    ('cvss:score:temporal', ('float', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use version specific score properties.'}),

                    ('cvss:score:environmental', ('float', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use version specific score properties.'}),

                    ('cwes', ('array', {'type': 'it:sec:cwe', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of MITRE CWE values that apply to the vulnerability.'}),
                )),

                ('risk:vuln:soft:range', {}, (
                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The vulnerability present in this software version range.'}),
                    ('version:min', ('it:prod:softver', {}), {
                        'doc': 'The minimum version which is vulnerable in this range.'}),
                    ('version:max', ('it:prod:softver', {}), {
                        'doc': 'The maximum version which is vulnerable in this range.'}),
                )),

                ('risk:hasvuln', {}, (
                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The vulnerability present in the target.'
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': 'The vulnerable person.',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The vulnerable org.',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The vulnerable place.',
                    }),
                    ('software', ('it:prod:softver', {}), {
                        'doc': 'The vulnerable software.',
                    }),
                    ('hardware', ('it:prod:hardware', {}), {
                        'doc': 'The vulnerable hardware.',
                    }),
                    ('spec', ('mat:spec', {}), {
                        'doc': 'The vulnerable material specification.',
                    }),
                    ('item', ('mat:item', {}), {
                        'doc': 'The vulnerable material item.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The vulnerable host.'
                    })
                )),

                ('risk:alert:taxonomy', {}, {}),
                ('risk:alert:verdict:taxonomy', {}, {}),
                ('risk:alert', {}, (
                    ('type', ('risk:alert:taxonomy', {}), {
                        'doc': 'A type for the alert, as a taxonomy entry.'}),

                    ('name', ('str', {}), {
                        'doc': 'A brief name for the alert.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A free-form description / overview of the alert.'}),

                    ('benign', ('bool', {}), {
                        'doc': 'Set to true if the alert has been confirmed benign. Set to false if malicious.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'A priority rank for the alert.'}),

                    ('severity', ('meta:severity', {}), {
                        'doc': 'A severity rank for the alert.'}),

                    ('verdict', ('risk:alert:verdict:taxonomy', {}), {
                        'ex': 'benign.false_positive',
                        'doc': 'A verdict about why the alert is malicious or benign, as a taxonomy entry.'}),

                    ('engine', ('it:prod:softver', {}), {
                        'doc': 'The software that generated the alert.'}),

                    ('detected', ('time', {}), {
                        'doc': 'The time the alerted condition was detected.'}),

                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The optional vulnerability that the alert indicates.'}),

                    ('attack', ('risk:attack', {}), {
                        'doc': 'A confirmed attack that this alert indicates.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the alert.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An external identifier for the alert.'}),

                    ('host', ('it:host', {}), {
                        'doc': 'The host which generated the alert.'}),
                )),
                ('risk:compromisetype', {}, ()),
                ('risk:compromise', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A brief name for the compromise event.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A prose description of the compromise event.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the compromise.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the compromise.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An external unique ID for the compromise.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the compromise.'}),

                    ('type', ('risk:compromisetype', {}), {
                        'ex': 'cno.breach',
                        'doc': 'A type for the compromise, as a taxonomy entry.'}),

                    ('vector', ('risk:attack', {}), {
                        'doc': 'The attack assessed to be the initial compromise vector.'}),

                    ('target', ('ps:contact', {}), {
                        'doc': 'Contact information representing the target.'}),

                    ('attacker', ('ps:contact', {}), {
                        'doc': 'Contact information representing the attacker.'}),

                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'The campaign that this compromise is part of.'}),

                    ('time', ('time', {}), {
                        'doc': 'Earliest known evidence of compromise.'}),

                    ('lasttime', ('time', {}), {
                        'doc': 'Last known evidence of compromise.'}),

                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the compromise.'}),

                    ('detected', ('time', {}), {
                        'doc': 'The first confirmed detection time of the compromise.'}),

                    ('loss:pii', ('int', {}), {
                        'doc': 'The number of records compromised which contain PII.'}),

                    ('loss:econ', ('econ:price', {}), {
                        'doc': 'The total economic cost of the compromise.'}),

                    ('loss:life', ('int', {}), {
                        'doc': 'The total loss of life due to the compromise.'}),

                    ('loss:bytes', ('int', {}), {
                        'doc': 'An estimate of the volume of data compromised.'}),

                    ('ransom:paid', ('econ:price', {}), {
                        'doc': 'The value of the ransom paid by the target.'}),

                    ('ransom:price', ('econ:price', {}), {
                        'doc': 'The value of the ransom demanded by the attacker.'}),

                    ('response:cost', ('econ:price', {}), {
                        'doc': 'The economic cost of the response and mitigation efforts.'}),

                    ('theft:price', ('econ:price', {}), {
                        'doc': 'The total value of the theft of assets.'}),

                    ('econ:currency', ('econ:currency', {}), {
                        'doc': 'The currency type for the econ:price fields.'}),

                    ('severity', ('meta:severity', {}), {
                        'doc': 'A severity rank for the compromise.'}),

                    ('goal', ('ou:goal', {}), {
                        'doc': 'The assessed primary goal of the attacker for the compromise.'}),

                    ('goals', ('array', {'type': 'ou:goal', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of assessed attacker goals for the compromise.'}),

                    # -(stole)> file:bytes ps:contact file:bytes
                    # -(compromised)> geo:place it:account it:host

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),
                )),
                ('risk:attacktype', {}, ()),
                ('risk:attack', {}, (
                    ('desc', ('str', {}), {
                        'doc': 'A description of the attack.',
                        'disp': {'hint': 'text'},
                    }),
                    ('type', ('risk:attacktype', {}), {
                        'ex': 'cno.phishing',
                        'doc': 'A type for the attack, as a taxonomy entry.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the attack.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the attack.'}),

                    ('time', ('time', {}), {
                        'doc': 'Set if the time of the attack is known.'}),

                    ('detected', ('time', {}), {
                        'doc': 'The first confirmed detection time of the attack.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Set if the attack was known to have succeeded or not.'}),

                    ('targeted', ('bool', {}), {
                        'doc': 'Set if the attack was assessed to be targeted or not.'}),

                    ('goal', ('ou:goal', {}), {
                        'doc': 'The tactical goal of this specific attack.'}),

                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'Set if the attack was part of a larger campaign.'}),

                    ('compromise', ('risk:compromise', {}), {
                        'doc': 'A compromise that this attack contributed to.'}),

                    ('severity', ('meta:severity', {}), {
                        'doc': 'A severity rank for the attack.'}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the attack.'}),

                    ('prev', ('risk:attack', {}), {
                        'doc': 'The previous/parent attack in a list or hierarchy.'}),

                    ('actor:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :attacker to allow entity resolution.'}),

                    ('actor:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :attacker to allow entity resolution.'}),

                    ('attacker', ('ps:contact', {}), {
                        'doc': 'Contact information representing the attacker.'}),

                    ('target', ('ps:contact', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.'}),

                    ('target:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.'}),

                    ('target:host', ('it:host', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.'}),

                    ('target:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.'}),

                    ('target:place', ('geo:place', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.'}),

                    ('via:ipv4', ('inet:ipv4', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('via:ipv6', ('inet:ipv6', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('via:email', ('inet:email', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('via:phone', ('tel:phone', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:vuln', ('risk:vuln', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:url', ('inet:url', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:host', ('it:host', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:email', ('inet:email', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:file', ('file:bytes', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:server', ('inet:server', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('used:software', ('it:prod:softver', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the attack.'}),

                    ('ext:id', ('str', {}), {
                        'doc': 'An external unique ID for the attack.'}),

                )),

                ('risk:leak:type:taxonomy', {}, ()),
                ('risk:leak', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A simple name for the leak event.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the leak event.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the leak event.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the leak event.'}),

                    ('disclosed', ('time', {}), {
                        'doc': 'The time the leaked information was disclosed.'}),

                    ('owner', ('ps:contact', {}), {
                        'doc': 'The owner of the leaked information.'}),

                    ('leaker', ('ps:contact', {}), {
                        'doc': 'The identity which leaked the information.'}),

                    ('type', ('risk:leak:type:taxonomy', {}), {
                        'doc': 'A type taxonomy for the leak.'}),

                    ('goal', ('ou:goal', {}), {
                        'doc': 'The goal of the leaker in disclosing the information.'}),

                    ('compromise', ('risk:compromise', {}), {
                        'doc': 'The compromise which allowed the leaker access to the information.'}),

                    ('public', ('bool', {}), {
                        'doc': 'Set to true if the leaked information was made publicly available.'}),

                    ('public:url', ('inet:url', {}), {
                        'doc': 'The URL where the leaked information was made publicly available.'}),

                )),

                ('risk:extortion:type:taxonomy', {}, ()),
                ('risk:extortion', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the extortion event.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the extortion event.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization reporting on the extortion event.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization reporting on the extortion event.'}),

                    ('demanded', ('time', {}), {
                        'doc': 'The time that the attacker made their demands.'}),

                    ('goal', ('ou:goal', {}), {
                        'doc': 'The goal of the attacker in extorting the victim.'}),

                    ('type', ('risk:extortion:type:taxonomy', {}), {
                        'doc': 'A type taxonomy for the extortion event.'}),

                    ('attacker', ('ps:contact', {}), {
                        'doc': 'The extortion attacker identity.'}),

                    ('target', ('ps:contact', {}), {
                        'doc': 'The extortion target identity.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Set to true if the victim met the attackers demands.'}),

                    ('enacted', ('bool', {}), {
                        'doc': 'Set to true if attacker carried out the threat.'}),

                    ('public', ('bool', {}), {
                        'doc': 'Set to true if the attacker publicly announced the extortion.'}),

                    ('public:url', ('inet:url', {}), {
                        'doc': 'The URL where the attacker publicly announced the extortion.'}),

                    ('compromise', ('risk:compromise', {}), {
                        'doc': 'The compromise which allowed the attacker to extort the target.'}),

                    ('demanded:payment:price', ('econ:price', {}), {
                        'doc': 'The payment price which was demanded.'}),

                    ('demanded:payment:currency', ('econ:currency', {}), {
                        'doc': 'The currency in which payment was demanded.'}),

                )),
                ('risk:technique:masquerade', {}, (
                    ('node', ('ndef', {}), {
                        'doc': 'The node masquerading as another.'}),
                    ('period', ('ival', {}), {
                        'doc': 'The time period when the masquerading was active.'}),
                    ('target', ('ndef', {}), {
                        'doc': 'The being masqueraded as.'}),
                    ('technique', ('ou:technique', {}), {
                        'doc': 'The specific technique which describes the type of masquerading.'}),
                )),
            ),
        }
        name = 'risk'
        return ((name, modl), )
