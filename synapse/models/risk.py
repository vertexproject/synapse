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
                ('risk:attack', ('guid', {}), {
                    'doc': 'An instance of an actor attacking a target.'
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
            ),
            'forms': (
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
                        'doc': 'A user specified name for the vulnerability.',
                    }),
                    ('type', ('str', {}), {
                        'doc': 'A user specified type for the vulnerability.',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the vulnerability.',
                        'disp': {'hint': 'text'},
                    }),
                    ('cve', ('it:sec:cve', {}), {
                        'doc': 'The CVE ID of the vulnerability.',
                    }),
                    ('cvss:av', ('str', {'enums': 'N,A,V,L'}), {
                        'doc': 'The CVSS Attack Vector (AV) value.',
                    }),
                    ('cvss:ac', ('str', {'enums': 'L,H'}), {
                        'doc': 'The CVSS Attack Complexity (AC) value.',
                        'disp': {'enums': (('Low', 'L'), ('High', 'H'))},
                    }),
                    ('cvss:pr', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Privileges Required (PR) value.',
                        'disp': {'enums': (
                            {'title': 'None', 'value': 'N', 'doc': 'FIXME privs stuff'},
                            {'title': 'Low', 'value': 'L', 'doc': 'FIXME privs stuff'},
                            {'title': 'High', 'value': 'H', 'doc': 'FIXME privs stuff'},
                        )},
                    }),
                    ('cvss:ui', ('str', {'enums': 'N,R'}), {
                        'doc': 'The CVSS User Interaction (UI) value.',
                    }),
                    ('cvss:s', ('str', {'enums': 'U,C'}), {
                        'doc': 'The CVSS Scope (S) value.',
                    }),
                    ('cvss:c', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Confidentiality Impact (C) value.',
                    }),
                    ('cvss:i', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Integrity Impact (I) value.',
                    }),
                    ('cvss:a', ('str', {'enums': 'N,L,H'}), {
                        'doc': 'The CVSS Availability Impact (A) value.',
                    }),
                    ('cvss:e', ('str', {'enums': 'X,U,P,F,H'}), {
                        'doc': 'The CVSS Exploit Code Maturity (E) value.',
                    }),
                    ('cvss:rl', ('str', {'enums': 'X,O,T,W,U'}), {
                        'doc': 'The CVSS Remediation Level (RL) value.',
                    }),
                    ('cvss:rc', ('str', {'enums': 'X,U,R,C'}), {
                        'doc': 'The CVSS Report Confidence (AV) value.',
                    }),
                    ('cvss:mav', ('str', {'enums': 'X,N,A,L,P'}), {
                        'doc': 'The CVSS Environmental Attack Vector (MAV) value.',
                    }),
                    ('cvss:mac', ('str', {'enums': 'X,L,H'}), {
                        'doc': 'The CVSS Environmental Attack Complexity (MAC) value.',
                    }),
                    ('cvss:mpr', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Privileges Required (MPR) value.',
                    }),
                    ('cvss:mui', ('str', {'enums': 'X,N,R'}), {
                        'doc': 'The CVSS Environmental User Interaction (MUI) value.',
                    }),
                    ('cvss:ms', ('str', {'enums': 'X,U,C'}), {
                        'doc': 'The CVSS Environmental Scope (MS) value.',
                    }),
                    ('cvss:mc', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Confidentiality Impact (MC) value.',
                    }),
                    ('cvss:mi', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Integrity Impact (MI) value.',
                    }),
                    ('cvss:ma', ('str', {'enums': 'X,N,L,H'}), {
                        'doc': 'The CVSS Environmental Accessibility Impact (MA) value.',
                    }),
                    ('cvss:cr', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Confidentiality Requirement (CR) value.',
                    }),
                    ('cvss:ir', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Integrity Requirement (IR) value.',
                    }),
                    ('cvss:ar', ('str', {'enums': 'X,L,M,H'}), {
                        'doc': 'The CVSS Environmental Availability Requirement (AR) value.',
                    }),
                    ('cvss:score', ('float', {}), {
                        'doc': 'The Overall CVSS Score value.',
                    }),
                    ('cvss:score:base', ('float', {}), {
                        'doc': 'The CVSS Base Score value.',
                    }),
                    ('cvss:score:temporal', ('float', {}), {
                        'doc': 'The CVSS Temporal Score value.',
                    }),
                    ('cvss:score:environmental', ('float', {}), {
                        'doc': 'The CVSS Environmental Score value.',
                    }),
                    ('cwes', ('array', {'type': 'it:sec:cwe', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of MITRE CWE values that apply to the vulnerability.',
                    }),
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

                ('risk:alert', {}, (
                    ('type', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'An alert type.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'The alert name.',
                    }),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A free-form description / overview of the alert.',
                    }),
                    ('detected', ('time', {}), {
                        'doc': 'The time the alerted condition was detected.',
                    }),
                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The optional vulnerability that the alert indicates.',
                    }),
                    ('attack', ('risk:attack', {}), {
                        'doc': 'A confirmed attack that this alert indicates.',
                    }),
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
                        'doc': 'Contact information associated with the target.',
                    }),
                    ('target:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :target to allow entity resolution.',
                    }),
                    ('target:host', ('it:host', {}), {
                        'doc': 'The host was the target of the attack.',
                    }),
                    ('target:person', ('ps:person', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :target to allow entity resolution.',
                    }),
                    ('target:place', ('geo:place', {}), {
                        'doc': 'The place that was the target of the attack.',
                    }),
                    ('via:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The target host was contacted via the IPv4 address.',
                    }),
                    ('via:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The target host was contacted via the IPv6 address.',
                    }),
                    ('via:email', ('inet:email', {}), {
                        'doc': 'The target person/org was contacted via the email address.',
                    }),
                    ('via:phone', ('tel:phone', {}), {
                        'doc': 'The target person/org was contacted via the phone number.',
                    }),
                    ('used:vuln', ('risk:vuln', {}), {
                        'doc': 'The actor used the vuln in the attack.',
                    }),
                    ('used:url', ('inet:url', {}), {
                        'doc': 'The actor used the url in the attack.',
                    }),
                    ('used:host', ('it:host', {}), {
                        'doc': 'The actor used the host in the attack.',
                    }),
                    ('used:email', ('inet:email', {}), {
                        'doc': 'The actor used the email in the attack.',
                    }),
                    ('used:file', ('file:bytes', {}), {
                        'doc': 'The actor used the file in the attack.',
                    }),
                    ('used:server', ('inet:server', {}), {
                        'doc': 'The actor used the server in the attack.',
                    }),
                    ('used:software', ('it:prod:softver', {}), {
                        'doc': 'The actor used the software in the attack.',
                    }),
                )),
            ),
        }
        name = 'risk'
        return ((name, modl), )
