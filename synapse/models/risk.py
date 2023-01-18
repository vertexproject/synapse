import synapse.lib.module as s_module

class RiskModule(s_module.CoreModule):

    def getModelDefs(self):

        modl = {
            'types': (
                ('risk:vuln', ('guid', {}), {
                    'doc': 'A unique vulnerability.',
                }),
                ('risk:hasvuln', ('guid', {}), {
                    'doc': 'An instance of a vulnerability present in a target.',
                }),
                ('risk:threat', ('guid', {}), {
                    'doc': 'A threat cluster or subgraph of threat activity.',
                }),
                ('risk:attack', ('guid', {}), {
                    'doc': 'An instance of an actor attacking a target.',
                }),
                ('risk:alert:taxonomy', ('taxonomy', {}), {
                    'doc': 'A taxonomy of alert types.'
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
                    'doc': 'An attack type taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
                ('risk:compromisetype', ('taxonomy', {}), {
                    'doc': 'A compromise type taxonomy.',
                    'ex': 'cno.breach',
                    'interfaces': ('taxonomy',),
                }),
                ('risk:tool:software:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                }),
                ('risk:availability', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                    'doc': 'A taxonomy of availability status values.',
                }),
                ('risk:tool:software', ('guid', {}), {
                    'doc': 'A software tool used in threat activity.',
                }),
                ('risk:alert:verdict:taxonomy', ('taxonomy', {}), {
                    'doc': 'An assessment of the origin and validity of the alert.'}),
            ),
            'edges': (
                # some explicit examples...
                (('risk:attack', 'uses', 'ou:technique'), {
                    'doc': 'The attack used the technique.'}),
                (('risk:threat', 'uses', 'ou:technique'), {
                    'doc': 'The threat cluster uses the technique.'}),
                (('risk:tool:software', 'uses', 'ou:technique'), {
                    'doc': 'The tool uses the technique.'}),

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
                    'doc': 'The attack used the target nodes to facilitate the attack.'}),
                (('risk:tool:software', 'uses', None), {
                    'doc': 'The tool uses the target node.'}),
                (('risk:compromise', 'stole', None), {
                    'doc': 'The target node was stolen or copied as a result of the compromise.'}),
            ),
            'forms': (
                ('risk:threat', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': "apt1 (mandiant)",
                        'doc': 'The name of the threat cluster.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A description of the threat cluster.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are members of the cluster.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization who published the threat cluster.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization who published the threat cluster.'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The organization that the threat cluster is attributed to.'}),

                    ('org:loc', ('loc', {}), {
                        'doc': 'The assessed location of the organization that the threat cluster is attributed to.'}),

                    ('org:name', ('ou:name', {}), {
                        'ex': 'apt1',
                        'doc': 'The name of the organization that the threat cluster is attributed to.'}),

                    ('org:names', ('array', {'type': 'ou:name', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternate names for the organization that the threat cluster is attributed to.'}),

                    ('goals', ('array', {'type': 'ou:goal', 'sorted': True, 'uniq': True}), {
                        'doc': 'The assessed goals of the threat cluster activity.'}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the threat cluster.'}),

                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated for scalability. Please use -(uses)> ou:technique.'}),

                    ('merged:time', ('time', {}), {
                        'doc': 'The time that this threat cluster was merged into another.'}),

                    ('merged:isnow', ('risk:threat', {}), {
                        'doc': 'The threat cluster that this cluster has been merged into.'}),
                )),
                ('risk:availability', {}, {}),
                ('risk:tool:software:taxonomy', {}, ()),
                ('risk:tool:software', {}, (

                    ('tag', ('syn:tag', {}), {
                        'ex': 'rep.mandiant.tabcteng',
                        'doc': 'The tag used to annotate nodes that are part of the tool subgraph.'}),

                    ('desc', ('str', {}), {
                        'doc': "A description of the tool's use in threat activity."}),

                    ('type', ('risk:tool:software:taxonomy', {}), {
                        'doc': 'An analyst specified taxonomy of software tool types.'}),

                    ('availability', ('risk:availability', {}), {
                        'doc': 'The assessed availability of the tool.'}),

                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the tool.'}),

                    ('reporter', ('ou:org', {}), {
                        'doc': 'The organization which reported the tool.'}),

                    ('reporter:name', ('ou:name', {}), {
                        'doc': 'The name of the organization which reported the tool.'}),

                    ('soft', ('it:prod:soft', {}), {
                        'doc': 'The authoritative software family of the tool.'}),

                    ('soft:name', ('it:prod:softname', {}), {
                        'doc': 'The reported primary name of the tool.'}),

                    ('soft:names', ('array', {'type': 'it:prod:softname', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of reported alterate names for the tool.'}),

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
                ('risk:vuln', {}, (
                    ('name', ('str', {}), {
                        'doc': 'A user specified name for the vulnerability.'}),

                    ('type', ('str', {}), {
                        'doc': 'A user specified type for the vulnerability.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the vulnerability.'}),

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

                    ('cvss:av', ('str', {'enums': 'N,A,V,L'}), {
                        'doc': 'The CVSS Attack Vector (AV) value.'}),

                    ('cvss:ac', ('str', {'enums': 'L,H'}), {
                        'disp': {'enums': (('Low', 'L'), ('High', 'H'))},
                        'doc': 'The CVSS Attack Complexity (AC) value.'}),

                    ('cvss:pr', ('str', {'enums': 'N,L,H'}), {
                        'disp': {'enums': (
                            {'title': 'None', 'value': 'N', 'doc': 'FIXME privs stuff'},
                            {'title': 'Low', 'value': 'L', 'doc': 'FIXME privs stuff'},
                            {'title': 'High', 'value': 'H', 'doc': 'FIXME privs stuff'},
                        )},
                        'doc': 'The CVSS Privileges Required (PR) value.'}),

                    ('cvss:ui', ('str', {'enums': 'N,R'}), {
                        'doc': 'The CVSS User Interaction (UI) value.'}),

                    ('cvss:s', ('str', {'enums': 'U,C'}), {
                        'doc': 'The CVSS Scope (S) value.'}),

                    ('cvss:c', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Confidentiality Impact (C) value.'}),

                    ('cvss:i', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Integrity Impact (I) value.'}),

                    ('cvss:a', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Availability Impact (A) value.'}),

                    ('cvss:e', ('str', {'enums': 'X,U,P,F,H'}), {
                        'doc': 'The CVSS Exploit Code Maturity (E) value.'}),

                    ('cvss:rl', ('str', {'enums': 'X,O,T,W,U'}), {
                        'doc': 'The CVSS Remediation Level (RL) value.'}),

                    ('cvss:rc', ('str', {'enums': 'X,U,R,C'}), {
                        'doc': 'The CVSS Report Confidence (AV) value.'}),

                    ('cvss:mav', ('str', {'enums': 'X,N,A,L,P'}), {
                        'doc': 'The CVSS Environmental Attack Vector (MAV) value.'}),

                    ('cvss:mac', ('str', {'enums': 'X,L,H'}), {
                        'doc': 'The CVSS Environmental Attack Complexity (MAC) value.'}),

                    ('cvss:mpr', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Privileges Required (MPR) value.'}),

                    ('cvss:mui', ('str', {'enums': 'X,N,R'}), {
                        'doc': 'The CVSS Environmental User Interaction (MUI) value.'}),

                    ('cvss:ms', ('str', {'enums': 'X,U,C'}), {
                        'doc': 'The CVSS Environmental Scope (MS) value.'}),

                    ('cvss:mc', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Confidentiality Impact (MC) value.'}),

                    ('cvss:mi', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Integrity Impact (MI) value.'}),

                    ('cvss:ma', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Accessibility Impact (MA) value.'}),

                    ('cvss:cr', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Confidentiality Requirement (CR) value.'}),

                    ('cvss:ir', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Integrity Requirement (IR) value.'}),

                    ('cvss:ar', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Availability Requirement (AR) value.'}),

                    ('cvss:score', ('float', {}), {
                        'doc': 'The Overall CVSS Score value.'}),

                    ('cvss:score:base', ('float', {}), {
                        'doc': 'The CVSS Base Score value.'}),

                    ('cvss:score:temporal', ('float', {}), {
                        'doc': 'The CVSS Temporal Score value.'}),

                    ('cvss:score:environmental', ('float', {}), {
                        'doc': 'The CVSS Environmental Score value.'}),

                    ('cwes', ('array', {'type': 'it:sec:cwe', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of MITRE CWE values that apply to the vulnerability.'}),
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
                        'doc': 'An alert type.'}),

                    ('name', ('str', {}), {
                        'doc': 'The alert name.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A free-form description / overview of the alert.'}),

                    ('benign', ('bool', {}), {
                        'doc': 'Set to true if the alert has been confirmed benign. Set to false if malicious.'}),

                    ('verdict', ('risk:alert:verdict:taxonomy', {}), {
                        'ex': 'benign.false_positive',
                        'doc': 'Analyst specified verdict taxonomy about why the alert is malicious or benign.'}),

                    ('engine', ('it:prod:softver', {}), {
                        'doc': 'The software which generated the alert.'}),

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
                )),
                ('risk:compromisetype', {}, ()),
                ('risk:compromise', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A brief name for the compromise event.',
                    }),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A prose description of the compromise event.',
                    }),
                    ('type', ('risk:compromisetype', {}), {
                        'ex': 'cno.breach',
                        'doc': 'The compromise type.',
                    }),
                    ('target', ('ps:contact', {}), {
                        'doc': 'Contact information of the target.',
                    }),
                    ('attacker', ('ps:contact', {}), {
                        'doc': 'Contact information of the attacker.',
                    }),
                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'The campaign that this compromise is part of.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'Earliest known evidence of compromise.',
                    }),
                    ('lasttime', ('time', {}), {
                        'doc': 'Last known evidence of compromise.',
                    }),
                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the compromise.',
                    }),
                    ('loss:pii', ('int', {}), {
                        'doc': 'The number of records compromised which contain PII.',
                    }),
                    ('loss:econ', ('econ:price', {}), {
                        'doc': 'The total economic cost of the compromise.',
                    }),
                    ('loss:life', ('int', {}), {
                        'doc': 'The total loss of life due to the compromise.',
                    }),
                    ('loss:bytes', ('int', {}), {
                        'doc': 'An estimate of the volume of data compromised.',
                    }),
                    ('ransom:paid', ('econ:price', {}), {
                        'doc': 'The value of the ransom paid by the target.',
                    }),
                    ('ransom:price', ('econ:price', {}), {
                        'doc': 'The value of the ransom demanded by the attacker.',
                    }),
                    ('response:cost', ('econ:price', {}), {
                        'doc': 'The economic cost of the response and mitigation efforts.',
                    }),
                    ('theft:price', ('econ:price', {}), {
                        'doc': 'The total value of the theft of assets.',
                    }),
                    ('econ:currency', ('econ:currency', {}), {
                        'doc': 'The currency type for the econ:price fields.',
                    }),
                    # -(stole)> file:bytes ps:contact file:bytes
                    # -(compromised)> geo:place it:account it:host
                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'doc': 'A list of techniques employed during the compromise.',
                    }),
                )),
                ('risk:attacktype', {}, ()),
                ('risk:attack', {}, (
                    ('desc', ('str', {}), {
                        'doc': 'A description of the attack.',
                        'disp': {'hint': 'text'},
                    }),
                    ('type', ('risk:attacktype', {}), {
                        'ex': 'cno.phishing',
                        'doc': 'The attack type.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'Set if the time of the attack is known.',
                    }),
                    ('success', ('bool', {}), {
                        'doc': 'Set if the attack was known to have succeeded or not.',
                    }),
                    ('targeted', ('bool', {}), {
                        'doc': 'Set if the attack was assessed to be targeted or not.',
                    }),
                    ('goal', ('ou:goal', {}), {
                        'doc': 'The tactical goal of this specific attack.',
                    }),
                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'Set if the attack was part of a larger campaign.',
                    }),
                    ('compromise', ('risk:compromise', {}), {
                        'doc': 'A compromise that this attack contributed to.',
                    }),
                    ('sophistication', ('meta:sophistication', {}), {
                        'doc': 'The assessed sophistication of the attack.',
                    }),
                    ('prev', ('risk:attack', {}), {
                        'doc': 'The previous/parent attack in a list or hierarchy.',
                    }),
                    ('actor:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :attacker to allow entity resolution.',
                    }),
                    ('actor:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :attacker to allow entity resolution.',
                    }),
                    ('attacker', ('ps:contact', {}), {
                        'doc': 'Contact information associated with the attacker.',
                    }),
                    ('target', ('ps:contact', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.',
                    }),
                    ('target:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.',
                    }),
                    ('target:host', ('it:host', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.',
                    }),
                    ('target:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.',
                    }),
                    ('target:place', ('geo:place', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(targets)> light weight edges.',
                    }),
                    ('via:ipv4', ('inet:ipv4', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('via:ipv6', ('inet:ipv6', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('via:email', ('inet:email', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('via:phone', ('tel:phone', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:vuln', ('risk:vuln', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:url', ('inet:url', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:host', ('it:host', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:email', ('inet:email', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:file', ('file:bytes', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:server', ('inet:server', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('used:software', ('it:prod:softver', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use -(uses)> light weight edges.',
                    }),
                    ('techniques', ('array', {'type': 'ou:technique', 'sorted': True, 'uniq': True}), {
                        'doc': 'A list of techniques employed during the attack.',
                    }),
                )),
            ),
        }
        name = 'risk'
        return ((name, modl), )
