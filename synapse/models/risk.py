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
            ),
            'forms': (
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
                    ('cwes', ('array', {'type': 'it:sec:cwe'}), {
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
                    ('spec', ('mat:spec', {}), {
                        'doc': 'The vulnerable material specification.',
                    }),
                    ('item', ('mat:item', {}), {
                        'doc': 'The vulnerable material item.',
                    }),
                )),

                ('risk:alert', {}, (
                    ('type', ('str', {'lower': True, 'onespace': True, 'strip': True}), {
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

                ('risk:attack', {}, (
                    ('time', ('time', {}), {
                        'doc': 'Set if the time of the attack is known.',
                    }),
                    ('success', ('bool', {}), {
                        'doc': 'Set if the attack was known to have succeeded or not.',
                    }),
                    ('targeted', ('bool', {}), {
                        'doc': 'Set if the attack was assessed to be targeted or not.',
                    }),
                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'Set if the attack was part of a larger campaign.',
                    }),
                    ('prev', ('risk:attack', {}), {
                        'doc': 'The previous/parent attack in a list or hierarchy.',
                    }),
                    ('actor:org', ('ou:org', {}), {
                        'doc': 'The org that carried out the attack.',
                    }),
                    ('actor:person', ('ps:person', {}), {
                        'doc': 'The person that carried out the attack.',
                    }),
                    ('target:org', ('ou:org', {}), {
                        'doc': 'The org was the target of the attack.',
                    }),
                    ('target:host', ('it:host', {}), {
                        'doc': 'The host was the target of the attack.',
                    }),
                    ('target:person', ('ps:person', {}), {
                        'doc': 'The person was the target of the attack.',
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
