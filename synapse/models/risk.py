import synapse.exc as s_exc

import synapse.lib.chop as s_chop
import synapse.lib.types as s_types


class CvssV2(s_types.Str):

    async def _normPyStr(self, text, view=None):
        try:
            return s_chop.cvss2_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None

class CvssV3(s_types.Str):

    async def _normPyStr(self, text, view=None):
        try:
            return s_chop.cvss3x_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None

alertstatus = (
    (0, 'new'),
    (10, 'enrichment'),
    (20, 'todo'),
    (30, 'analysis'),
    (40, 'remediation'),
    (50, 'done'),
)

modeldefs = (
    ('risk', {
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
                'template': {'title': 'vulnerability'},
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                    ('risk:targetable', {}),
                    ('risk:mitigatable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'id'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'cvss:v3_1:score'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'doc': 'A unique vulnerability.'}),

            ('risk:vuln:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of vulnerability types.'}),

            ('risk:vulnerable', ('guid', {}), {
                'doc': 'Indicates that a node is susceptible to a vulnerability.'}),

            ('risk:threat', ('guid', {}), {
                'template': {'title': 'threat'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:actor', {}),
                    ('entity:abstract', {}),
                    ('entity:contactable', {}),
                ),
                'doc': 'A threat cluster or subgraph of threat activity, as defined by a specific source.',
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'names'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                },
            }),
            ('risk:attack', ('guid', {}), {
                'template': {'title': 'attack'},
                'interfaces': (
                    ('entity:action', {}),
                    ('meta:reported', {}),
                ),
                'doc': 'An instance of an actor attacking a target.'}),

            ('risk:alert:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of alert types.'}),

            ('risk:alert', ('guid', {}), {
                'doc': 'An alert which indicates the presence of a risk.'}),

            ('risk:compromise', ('guid', {}), {
                'template': {'title': 'compromise'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:action', {}),
                ),
                'display': {
                    'columns': (
                        # TODO allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period.min'}},
                        # {'type': 'prop', 'opts': {'name': 'period.max'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'doc': 'A compromise and its aggregate impact. The compromise is the result of a successful attack.'}),

            ('risk:mitigation', ('meta:technique', {}), {
                'template': {'title': 'mitigation'},
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                },
                'doc': 'A mitigation for a specific vulnerability or technique.'}),

            ('risk:attack:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of attack types.'}),

            ('risk:compromise:type:taxonomy', ('taxonomy', {}), {
                'ex': 'cno.breach',
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of compromise types.'}),

            ('risk:tool:software:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of software tool types.'}),

            ('risk:availability', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of availability status values.'}),

            ('risk:tool:software', ('guid', {}), {
                'template': {'title': 'tool'},
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'names'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                },
                'doc': 'A software tool used in threat activity, as defined by a specific source.'}),

            ('risk:alert:verdict:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of alert verdicts.'}),

            ('risk:threat:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of threat types.'}),

            ('risk:leak', ('guid', {}), {
                'template': {'title': 'leak'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:action', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'disclosed'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'owner::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'doc': 'An event where information was disclosed without permission.'}),

            ('risk:leak:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of leak event types.'}),

            ('risk:extortion', ('guid', {}), {
                'template': {'title': 'extortion'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:action', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'demanded'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'target::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'deadline'}},
                    ),
                },
                'doc': 'An event where an attacker attempted to extort a victim.'}),

            ('risk:outage:cause:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'An outage cause taxonomy.'}),

            ('risk:outage:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'An outage type taxonomy.'}),

            ('risk:outage', ('guid', {}), {
                'template': {'title': 'outage'},
                'interfaces': (
                    ('meta:reported', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'period'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'provider:name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'cause'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'doc': 'An outage event which affected resource availability.'}),

            ('risk:extortion:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of extortion event types.'}),

            ('risk:mitigatable', ('ndef', {'interface': 'risk:mitigatable'}), {
                'doc': 'A node whose effect may be reduced by a mitigation.'}),
        ),
        'interfaces': (

            ('risk:mitigatable', {
                'doc': 'A common interface for risks which may be mitigated.',
            }),

            ('risk:targetable', {
                'doc': 'A common interface for nodes which may target selection criteria for threats.',
            }),
        ),
        'edges': (
            # some explicit examples...

            (('entity:actor', 'targeted', 'risk:targetable'), {
                'doc': 'The actor targets based on the target node.'}),

            (('entity:action', 'targeted', 'risk:targetable'), {
                'doc': 'The action represents the actor targeting based on the target node.'}),

            (('risk:compromise', 'stole', 'meta:observable'), {
                'doc': 'The target node was stolen or copied as a result of the compromise.'}),

            (('risk:compromise', 'stole', 'phys:object'), {
                'doc': 'The target node was stolen as a result of the compromise.'}),

            (('risk:leak', 'leaked', 'meta:observable'), {
                'doc': 'The leak included the disclosure of the target node.'}),

            (('risk:leak', 'enabled', 'risk:leak'), {
                'doc': 'The source leak enabled the target leak to occur.'}),

            (('risk:extortion', 'leveraged', 'meta:observable'), {
                'doc': 'The extortion event was based on attacker access to the target node.'}),

            (('meta:event', 'caused', 'risk:outage'), {
                'doc': 'The event caused the outage.'}),

            (('risk:attack', 'caused', 'risk:alert'), {
                'doc': 'The attack caused the alert.'}),

            (('risk:attack', 'caused', 'risk:outage'), {
                'doc': 'The attack caused the outage.'}),

            (('risk:outage', 'impacted', None), {
                'doc': 'The outage event impacted the availability of the target node.'}),

            (('risk:alert', 'about', None), {
                'doc': 'The alert is about the target node.'}),

            (('meta:observable', 'resembles', 'meta:observable'), {
                'doc': 'The source node resembles the target node.'}),

            # TODO we will need more of these...
            (('inet:proto:link', 'shows', 'risk:vulnerable'), {
                'doc': 'The network activity shows that the vulnerability was present.'}),
        ),
        'forms': (

            ('risk:threat:type:taxonomy', {}, ()),

            ('risk:threat', {}, (

                ('type', ('risk:threat:type:taxonomy', {}), {
                    'doc': 'A type for the threat, as a taxonomy entry.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes that are associated with the threat cluster.'}),

                ('active', ('ival', {}), {
                    'doc': 'An interval for when the threat cluster is assessed to have been active.'}),

                ('activity', ('meta:activity', {}), {
                    'doc': 'The most recently assessed activity level of the threat cluster.'}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': "The sources's assessed sophistication of the threat cluster."}),

                ('merged:time', ('time', {}), {
                    'doc': 'The time that the source merged this threat cluster into another.'}),

                ('merged:isnow', ('risk:threat', {}), {
                    'doc': 'The threat cluster that the source merged this cluster into.'}),

            )),
            ('risk:availability', {}, {}),
            ('risk:tool:software:type:taxonomy', {
                'prevnames': ('risk:tool:software:taxonomy',)}, ()),

            # FIXME extend it:software form?
            ('risk:tool:software', {}, (

                ('name', ('it:softwarename', {}), {
                    'alts': ('names',),
                    'doc': 'The primary name of the tool according to the source.'}),

                ('names', ('array', {'type': 'it:softwarename'}), {
                    'doc': 'A list of alternate names for the tool according to the source.'}),

                ('tag', ('syn:tag', {}), {
                    'ex': 'rep.mandiant.tabcteng',
                    'doc': 'The tag used to annotate nodes that are associated with the tool.'}),

                ('type', ('risk:tool:software:type:taxonomy', {}), {
                    'doc': 'A type for the tool, as a taxonomy entry.'}),

                ('used', ('ival', {}), {
                    'doc': "The source's assessed interval for when the tool has been deployed."}),

                ('availability', ('risk:availability', {}), {
                    'doc': "The source's assessed availability of the tool."}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': "The source's assessed sophistication of the tool."}),

                ('software', ('it:software', {}), {
                    'prevnames': ('soft',),
                    'doc': 'The authoritative software family for the tool.'}),
            )),
            ('risk:mitigation', {}, ()),

            ('risk:vuln:type:taxonomy', {}, ()),

            ('risk:vuln', {}, (

                ('cve', ('it:sec:cve', {}), {
                    'doc': 'The CVE ID assigned to the vulnerability.'}),

                ('type', ('risk:vuln:type:taxonomy', {}), {
                    'doc': 'A taxonomy type entry for the vulnerability.'}),

                ('severity', ('meta:severity', {}), {
                    'doc': 'The severity of the vulnerability.'}),

                ('priority', ('meta:priority', {}), {
                    'doc': 'The priority of the vulnerability.'}),

                ('mitigated', ('bool', {}), {
                    'doc': 'Set to true if a mitigation/fix is available for the vulnerability.'}),

                ('exploited', ('bool', {}), {
                    'doc': 'Set to true if the vulnerability has been exploited in the wild.'}),

                ('discovered', ('time', {}), {
                    'prevnames': ('timeline:discovered',),
                    'doc': 'The earliest known discovery time for the vulnerability.'}),

                ('published', ('time', {}), {
                    'prevnames': ('timeline:published',),
                    'doc': 'The earliest known time the vulnerability was published.'}),

                ('vendor', ('entity:actor', {}), {
                    'doc': 'The vendor whose product contains the vulnerability.'}),

                ('vendor:name', ('meta:name', {}), {
                    'doc': 'The name of the vendor whose product contains the vulnerability.'}),

                ('vendor:fixed', ('time', {}), {
                    'prevnames': ('timeline:vendor:fixed',),
                    'doc': 'The earliest known time the vendor issued a fix for the vulnerability.'}),

                ('vendor:notified', ('time', {}), {
                    'prevnames': ('timeline:vendor:notified',),
                    'doc': 'The earliest known vendor notification time for the vulnerability.'}),

                ('exploited', ('time', {}), {
                    'prevnames': ('timeline:exploited',),
                    'doc': 'The earliest known time when the vulnerability was exploited in the wild.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'A tag used to annotate the presence or use of the vulnerability.'}),

                # FIXME cvss / vuln scoring
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

                ('cwes', ('array', {'type': 'it:sec:cwe'}), {
                    'doc': 'MITRE CWE values that apply to the vulnerability.'}),
            )),

            ('risk:vulnerable', {}, (

                # FIXME either/or prop?
                ('vuln', ('risk:vuln', {}), {
                    'doc': 'The vulnerability that the node is susceptible to.'}),

                ('technique', ('meta:technique', {}), {
                    'doc': 'The technique that the node is susceptible to.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time window where the node was vulnerable.'}),

                # TODO - interface for things which can be vulnerable?
                ('node', ('ndef', {}), {
                    'doc': 'The node which is vulnerable.'}),

                ('mitigated', ('bool', {}), {
                    'doc': 'Set to true if the vulnerable node has been mitigated.'}),

                ('mitigations', ('array', {'type': 'meta:technique'}), {
                    'doc': 'The mitigations which were used to address the vulnerable node.'}),
            )),

            ('risk:alert:type:taxonomy', {
                'prevnames': ('risk:alert:taxonomy',)}, {}),

            ('risk:alert:verdict:taxonomy', {}, {}),
            ('risk:alert', {}, (
                # FIXME - This is REALLY close to meta:reported
                # FIXME - This is also REALLY close to proj:doable

                ('type', ('risk:alert:type:taxonomy', {}), {
                    'doc': 'A type for the alert, as a taxonomy entry.'}),

                ('name', ('base:name', {}), {
                    'doc': 'A brief name for the alert.'}),

                ('desc', ('text', {}), {
                    'doc': 'A free-form description / overview of the alert.'}),

                ('status', ('int', {'enums': alertstatus}), {
                    'doc': 'The status of the alert.'}),

                ('benign', ('bool', {}), {
                    'doc': 'Set to true if the alert has been confirmed benign. Set to false if malicious.'}),

                ('priority', ('meta:priority', {}), {
                    'doc': 'A priority rank for the alert.'}),

                ('severity', ('meta:severity', {}), {
                    'doc': 'A severity rank for the alert.'}),

                ('verdict', ('risk:alert:verdict:taxonomy', {}), {
                    'ex': 'benign.false_positive',
                    'doc': 'A verdict about why the alert is malicious or benign, as a taxonomy entry.'}),

                ('assignee', ('syn:user', {}), {
                    'doc': 'The Synapse user who is assigned to investigate the alert.'}),

                ('ext:assignee', ('entity:contact', {}), {
                    'doc': 'The alert assignee contact information from an external system.'}),

                ('engine', ('it:software', {}), {
                    'doc': 'The software that generated the alert.'}),

                ('detected', ('time', {}), {
                    'doc': 'The time the alerted condition was detected.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the alert was most recently modified.'}),

                ('vuln', ('risk:vuln', {}), {
                    'doc': 'The optional vulnerability that the alert indicates.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the alert.'}),

                ('id', ('base:id', {}), {
                    'doc': 'An external identifier for the alert.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host which generated the alert.'}),

                ('service:platform', ('inet:service:platform', {}), {
                    'doc': 'The service platform which generated the alert.'}),

                ('service:account', ('inet:service:account', {}), {
                    'doc': 'The service account which generated the alert.'}),
            )),

            ('risk:compromise:type:taxonomy', {
                'prevnames': ('risk:compromisetype',)}, ()),

            ('risk:compromise', {}, (

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the compromise.'}),

                ('type', ('risk:compromise:type:taxonomy', {}), {
                    'ex': 'cno.breach',
                    'doc': 'A type for the compromise, as a taxonomy entry.'}),

                ('vector', ('risk:attack', {}), {
                    'doc': 'The attack assessed to be the initial compromise vector.'}),

                ('target', ('entity:actor', {}), {
                    'doc': 'Contact information representing the target.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period over which the target was compromised.'}),

                # FIXME - is this overfit being one-to-one?
                ('campaign', ('entity:campaign', {}), {
                    'doc': 'The campaign that this compromise is part of.'}),

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
            )),
            ('risk:attack:type:taxonomy', {
                'prevnames': ('risk:attacktype',)}, ()),

            ('risk:attack', {}, (

                ('type', ('risk:attack:type:taxonomy', {}), {
                    'ex': 'cno.phishing',
                    'doc': 'A type for the attack, as a taxonomy entry.'}),

                ('time', ('time', {}), {
                    'doc': 'Set if the time of the attack is known.'}),

                ('detected', ('time', {}), {
                    'doc': 'The first confirmed detection time of the attack.'}),

                ('success', ('bool', {}), {
                    'doc': 'Set if the attack was known to have succeeded or not.'}),

                # FIXME overfit
                ('campaign', ('entity:campaign', {}), {
                    'doc': 'Set if the attack was part of a larger campaign.'}),

                ('compromise', ('risk:compromise', {}), {
                    'doc': 'A compromise that this attack contributed to.'}),

                ('severity', ('meta:severity', {}), {
                    'doc': 'A severity rank for the attack.'}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': 'The assessed sophistication of the attack.'}),

                ('prev', ('risk:attack', {}), {
                    'doc': 'The previous/parent attack in a list or hierarchy.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the attack.'}),
            )),

            ('risk:leak:type:taxonomy', {}, ()),
            ('risk:leak', {}, (

                ('disclosed', ('time', {}), {
                    'doc': 'The time the leaked information was disclosed.'}),

                ('owner', ('entity:actor', {}), {
                    'doc': 'The owner of the leaked information.'}),

                ('recipient', ('entity:actor', {}), {
                    'doc': 'The identity which received the leaked information.'}),

                ('type', ('risk:leak:type:taxonomy', {}), {
                    'doc': 'A type taxonomy for the leak.'}),

                ('compromise', ('risk:compromise', {}), {
                    'doc': 'The compromise which allowed the leaker access to the information.'}),

                ('extortion', ('risk:extortion', {}), {
                    'doc': 'The extortion event which used the threat of the leak as leverage.'}),

                ('public', ('bool', {}), {
                    'doc': 'Set to true if the leaked information was made publicly available.'}),

                ('public:urls', ('array', {'type': 'inet:url'}), {
                    'prevnames': ('public:url',),
                    'doc': 'The URL where the leaked information was made publicly available.'}),

                ('size:bytes', ('int', {'min': 0}), {
                    'doc': 'The total size of the leaked data in bytes.'}),

                ('size:count', ('int', {'min': 0}), {
                    'doc': 'The number of files included in the leaked data.'}),

                ('size:percent', ('int', {'min': 0, 'max': 100}), {
                    'doc': 'The total percent of the data leaked.'}),

            )),

            ('risk:outage:type:taxonomy', {}, ()),
            ('risk:outage:cause:taxonomy', {}, ()),
            ('risk:outage', {}, (

                ('period', ('ival', {}), {
                    'doc': 'The time period where the outage impacted availability.'}),

                ('type', ('risk:outage:type:taxonomy', {}), {
                    'ex': 'service.power',
                    'doc': 'The type of outage.'}),

                ('cause', ('risk:outage:cause:taxonomy', {}), {
                    'ex': 'nature.earthquake',
                    'doc': 'The outage cause type.'}),

                ('attack', ('risk:attack', {}), {
                    'doc': 'An attack which caused the outage.'}),

                ('provider', ('ou:org', {}), {
                    'doc': 'The organization which experienced the outage event.'}),

                ('provider:name', ('meta:name', {}), {
                    'doc': 'The name of the organization which experienced the outage event.'}),
            )),

            ('risk:extortion:type:taxonomy', {}, ()),
            ('risk:extortion', {}, (

                ('demanded', ('time', {}), {
                    'doc': 'The time that the attacker made their demands.'}),

                ('deadline', ('time', {}), {
                    'doc': 'The time that the demand must be met.'}),

                ('type', ('risk:extortion:type:taxonomy', {}), {
                    'doc': 'A type taxonomy for the extortion event.'}),

                ('target', ('entity:actor', {}), {
                    'doc': 'The extortion target identity.'}),

                ('success', ('bool', {}), {
                    'doc': "Set to true if the victim met the attacker's demands."}),

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

                ('paid:price', ('econ:price', {}), {
                    'doc': 'The total price paid by the target of the extortion.'}),

                ('payments', ('array', {'type': 'econ:payment'}), {
                    'doc': 'Payments made from the target to the attacker.'}),
            )),
        ),
    }),
)
