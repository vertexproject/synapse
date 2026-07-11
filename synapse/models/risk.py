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

modeldefs = (
    {
        'types': (
            # TODO: implement type specific cmprs and virts for CVSS types
            ('it:sec:cvss:v2', (None, {'ctor': 'synapse.models.risk.CvssV2'}), {
                'ex': '(AV:L/AC:L/Au:M/C:P/I:C/A:N)',
                'doc': 'A CVSS v2 vector string.'}),

            ('it:sec:cvss:v3', (None, {'ctor': 'synapse.models.risk.CvssV3'}), {
                'ex': 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
                'doc': 'A CVSS v3.x vector string.'}),

            ('risk:vuln', ('guid', {}), {
                'template': {'title': 'vulnerability'},
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                    ('meta:observable', {}),
                    ('risk:targetable', {}),
                    ('risk:mitigatable', {}),
                    ('meta:discoverable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'id'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'props': (

                    ('id', ('risk:vuln:id', {}), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the vulnerability.'}),

                    ('ids', ('risk:vuln:id', {}), {
                        'array': {},
                        'doc': 'An array of alternate IDs given to the vulnerability.'}),

                    ('type', ('risk:vuln:type:taxonomy', {}), {
                        'doc': 'A taxonomy type entry for the vulnerability.'}),

                    ('severity', ('meta:score', {}), {
                        'doc': 'The severity of the vulnerability.'}),

                    ('priority', ('meta:score', {}), {
                        'doc': 'The priority of the vulnerability.'}),

                    ('mitigated', ('time', {}), {
                        'doc': 'The earliest known time when a mitigation/fix became available for the vulnerability.'}),

                    ('published', ('time', {}), {
                        'prevnames': ('timeline:published',),
                        'doc': 'The earliest known time the vulnerability was published.'}),

                    ('vendor', ('entity:actor', {}), {
                        'doc': 'The vendor whose product contains the vulnerability.'}),

                    ('vendor:name', ('entity:name', {}), {
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

                    ('cvss:v2', ('it:sec:cvss:v2', {}), {
                        'doc': 'The CVSS v2 vector for the vulnerability.'}),

                    ('cvss:v2_0:score', ('float', {}), {
                        'doc': 'The CVSS v2.0 overall score for the vulnerability.'}),

                    ('cvss:v3', ('it:sec:cvss:v3', {}), {
                        'doc': 'The CVSS v3 vector for the vulnerability.'}),

                    ('cvss:v3_0:score', ('float', {}), {
                        'doc': 'The CVSS v3.0 overall score for the vulnerability.'}),

                    ('cvss:v3_1:score', ('float', {}), {
                        'doc': 'The CVSS v3.1 overall score for the vulnerability.'}),

                    ('cwes', ('it:sec:cwe', {}), {
                        'array': {},
                        'doc': 'MITRE CWE values that apply to the vulnerability.'}),
                ),
                'doc': 'A unique vulnerability.'}),

            ('risk:vuln:id', (
                    ('it:sec:cve', {}),
                    ('base:id', {})
                ), {
                'doc': 'A unique ID given to a vulnerability.'}),

            ('risk:vuln:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of vulnerability types.'}),

            ('risk:vulnerable', ('guid', {}), {
                'template': {'title': 'mitigation task'},
                'interfaces': (
                    ('meta:task', {}),
                ),
                'props': (

                    ('to', ('risk:mitigatable', {}), {
                        'doc': 'The thing which the node is vulnerable to.'}),

                    ('period', None, {
                        'doc': 'The time window where the node was vulnerable.'}),

                    ('node', ('risk:exploitable', {}), {
                        'doc': 'The node which is vulnerable.'}),

                    ('mitigations', ('meta:technique', {}), {
                        'array': {},
                        'doc': 'The mitigations which were used to address the vulnerable node.'}),
                ),
                'doc': 'Indicates that a node is susceptible to a vulnerability.'}),

            ('risk:threat', ('guid', {}), {
                'template': {'title': 'threat'},
                'interfaces': (
                    # entity:resolvable must precede meta:reported so :resolved
                    # resolves to ou:org/ps:person rather than meta:reported's {$self}.
                    ('entity:resolvable', {}),
                    ('meta:reported', {}),
                    ('meta:discoverable', {}),
                    ('entity:actor', {}),
                    ('entity:contactable', {}),
                ),
                'props': (

                    ('id', (
                        ('it:mitre:attack:group:id', {}),
                        ('base:id', {}),
                    ), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the threat.'}),

                    ('ids', (('it:mitre:attack:group:id', {}), ('base:id', {})), {
                        'array': {},
                        'doc': 'An array of alternate IDs given to the threat.'}),

                    ('name', ('entity:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the threat according to the source.'}),

                    ('names', ('entity:name', {}), {
                        'array': {},
                        'doc': 'A list of alternate names for the threat according to the source.'}),

                    ('type', ('risk:threat:type:taxonomy', {}), {
                        'doc': 'A type for the threat, as a taxonomy entry.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are associated with the threat cluster.'}),

                    ('activity', ('meta:score', {}), {
                        'doc': 'The most recently assessed activity level of the threat cluster.'}),

                    ('sophistication', ('meta:score', {}), {
                        'doc': "The sources's assessed sophistication of the threat cluster."}),

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
                    ('meta:reported', {}),
                    ('entity:activity', {}),
                    ('risk:victimized', {}),
                    ('meta:discoverable', {}),
                ),
                'props': (

                    ('type', ('risk:attack:type:taxonomy', {}), {
                        'ex': 'cno.phishing',
                        'doc': 'A type for the attack, as a taxonomy entry.'}),

                    ('detected', ('time', {}), {
                        'doc': 'The first confirmed detection time of the attack.'}),

                    ('success', ('bool', {}), {
                        'doc': 'Set if the attack was known to have succeeded or not.'}),

                    ('compromise', ('risk:compromise', {}), {
                        'doc': 'A compromise that this attack contributed to.'}),

                    ('severity', ('meta:score', {}), {
                        'doc': 'A severity rank for the attack.'}),

                    ('sophistication', ('meta:score', {}), {
                        'doc': 'The assessed sophistication of the attack.'}),

                    ('previous', ('risk:attack', {}), {
                        'doc': 'The previous/parent attack in a list or hierarchy.'}),

                ),
                'doc': 'An instance of an actor attacking a target.'}),

            ('risk:alert:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('risk:alert:taxonomy',),
                'props': (),
                'doc': 'A hierarchical taxonomy of alert types.'}),

            ('risk:alert', ('guid', {}), {
                'template': {'title': 'alert'},
                'interfaces': (
                    ('meta:task', {}),
                ),
                'props': (

                    ('type', ('risk:alert:type:taxonomy', {}), {
                        'doc': 'A type for the alert, as a taxonomy entry.'}),

                    ('name', ('base:name', {}), {
                        'doc': 'A brief name for the alert.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A free-form description / overview of the alert.'}),

                    ('benign', ('bool', {}), {
                        'doc': 'Set to true if the alert has been confirmed benign. Set to false if malicious.'}),

                    ('severity', ('meta:score', {}), {
                        'doc': 'A severity rank for the alert.'}),

                    ('verdict', ('risk:alert:verdict:taxonomy', {}), {
                        'ex': 'benign.false_positive',
                        'doc': 'A verdict about why the alert is malicious or benign, as a taxonomy entry.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the alert.'}),

                    ('host', ('it:host', {}), {
                        'doc': 'The host which generated the alert.'}),

                    ('engine', ('it:software', {}), {
                        'doc': 'The software that generated the alert.'}),

                    ('platform', ('inet:service:platform', {}), {
                        'doc': 'The service platform which generated the alert.'}),

                    ('account', (('it:host:account', {}),
                                 ('inet:service:account', {})), {
                        'doc': 'The account which generated the alert.'}),
                ),
                'doc': 'An alert which indicates the presence of a risk.'}),

            ('risk:compromise', ('guid', {}), {
                'template': {'title': 'compromise'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:activity', {}),
                    ('risk:victimized', {}),
                    ('meta:discoverable', {}),
                ),
                'display': {
                    'columns': (
                        # TODO allow columns to use virtual props
                        # {'type': 'prop', 'opts': {'name': 'period.min'}},
                        # {'type': 'prop', 'opts': {'name': 'period.max'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'victim::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'props': (

                    ('type', ('risk:compromise:type:taxonomy', {}), {
                        'ex': 'cno.breach',
                        'doc': 'A type for the compromise, as a taxonomy entry.'}),

                    ('vector', ('risk:attack', {}), {
                        'doc': 'The attack assessed to be the initial compromise vector.'}),

                    ('cost', ('econ:price', {}), {
                        'doc': 'The total cost of the compromise, response, and mitigation efforts.'}),

                    ('severity', ('meta:score', {}), {
                        'doc': 'A severity rank for the compromise.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'A tag used to associate nodes with the compromise.'}),
                ),
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
                'props': (

                    ('id', (
                        ('it:mitre:attack:mitigation:id', {}),
                        ('base:id', {}),
                    ), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the mitigation.'}),

                    ('ids', (('it:mitre:attack:mitigation:id', {}), ('base:id', {})), {
                        'array': {},
                        'doc': 'An array of alternate IDs given to the mitigation.'}),
                ),
                'doc': 'A mitigation for a specific vulnerability or technique.'}),

            ('risk:attack:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('risk:attacktype',),
                'props': (),
                'doc': 'A hierarchical taxonomy of attack types.'}),

            ('risk:compromise:type:taxonomy', ('taxonomy', {}), {
                'ex': 'cno.breach',
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('risk:compromisetype',),
                'props': (),
                'doc': 'A hierarchical taxonomy of compromise types.'}),

            ('risk:alert:verdict:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of alert verdicts.'}),

            ('risk:threat:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of threat types.'}),

            ('risk:leak', ('guid', {}), {
                'template': {'title': 'leak'},
                'interfaces': (
                    ('entity:event', {}),
                    ('meta:reported', {}),
                    ('risk:victimized', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'time'}},
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'victim::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'props': (

                    ('recipient', ('entity:actor', {}), {
                        'doc': 'The identity which received the leaked information.'}),

                    ('type', ('risk:leak:type:taxonomy', {}), {
                        'doc': 'A type taxonomy for the leak.'}),

                    ('public', ('bool', {}), {
                        'doc': 'Set to true if the leaked information was made publicly available.'}),

                    ('urls', ('inet:url', {}), {
                        'array': {},
                        'prevnames': ('public:url',),
                        'doc': 'URLs where the leaked information was made available.'}),

                    ('size:bytes', ('size', {}), {
                        'doc': 'The total size of the leaked data in bytes.'}),

                    ('size:count', ('size', {}), {
                        'doc': 'The number of files included in the leaked data.'}),

                    ('size:percent', ('percent', {}), {
                        'doc': 'The total percent of the data leaked.'}),
                ),
                'doc': 'An event where information was disclosed without permission.'}),

            ('risk:leak:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of leak event types.'}),

            ('risk:extortion', ('guid', {}), {
                'template': {'title': 'extortion'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('entity:activity', {}),
                    ('risk:victimized', {}),
                    ('meta:negotiable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'victim::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        # TODO: period.min / period.max
                    ),
                },
                'props': (

                    ('type', ('risk:extortion:type:taxonomy', {}), {
                        'doc': 'A type taxonomy for the extortion event.'}),

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

                    ('paid:price', ('econ:price', {}), {
                        'doc': 'The total price paid by the target of the extortion.'}),
                ),
                'doc': 'Activity where an attacker attempted to extort a victim.'}),

            ('risk:theft', ('guid', {}), {
                'template': {'title': 'theft'},
                'interfaces': (
                    ('entity:event', {}),
                    ('meta:reported', {}),
                    ('risk:victimized', {}),
                ),
                'props': (
                    ('value', ('econ:price', {}), {
                        'doc': 'The total value of the stolen items.'}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'time'}},
                        {'type': 'prop', 'opts': {'name': 'value'}},
                        {'type': 'prop', 'opts': {'name': 'actor::name'}},
                        {'type': 'prop', 'opts': {'name': 'victim::name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'doc': 'An event where an actor stole from a victim.'}),

            ('risk:loss:life', ('guid', {}), {
                'template': {'title': 'loss of life'},
                'interfaces': (
                    ('risk:loss', {}),
                ),
                'props': (
                    ('count', ('size', {}), {
                        'doc': 'The number of lives lost.'}),
                ),
                'doc': 'An aggregate loss of life.'}),

            ('risk:loss:data', ('guid', {}), {
                'template': {'title': 'data loss'},
                'interfaces': (
                    ('risk:loss', {}),
                ),
                'props': (
                    ('size', ('size', {}), {
                        'doc': 'The total size of the data which was lost.'}),
                ),
                'doc': 'An aggregate loss of data which is no longer available. This is not used to record data theft.'}),

            ('risk:loss:funds', ('guid', {}), {
                'template': {'title': 'loss of funds'},
                'interfaces': (
                    ('risk:loss', {}),
                ),
                'props': (
                    ('value', ('econ:price', {}), {
                        'doc': 'The total value of the funds which were lost.'}),
                ),
                'doc': 'An aggregate loss of funds.'}),

            ('risk:outage:cause:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'An outage cause taxonomy.'}),

            ('risk:outage:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'An outage type taxonomy.'}),

            ('risk:outage', ('guid', {}), {
                'template': {'title': 'outage'},
                'interfaces': (
                    ('base:activity', {}),
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
                'props': (

                    ('period', None, {
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

                    ('provider:name', ('entity:name', {}), {
                        'doc': 'The name of the organization which experienced the outage event.'}),
                ),
                'doc': 'An outage event which affected resource availability.'}),

            ('risk:extortion:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of extortion event types.'}),
        ),
        'interfaces': (

            ('risk:exploitable', {
                'doc': 'An interface implemented by forms which may be exploited by an actor.'}),

            ('risk:loss', {
                'template': {'title': 'loss'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'doc': 'An interface for aggregate losses which occur over a period.'}),

            ('risk:mitigatable', {
                'doc': 'A common interface for risks which may be mitigated.'}),

            ('risk:targetable', {
                'doc': 'An interface implemented by forms which are targets of threats.'}),

            ('risk:victimized', {
                'template': {'title': 'event'},
                'props': (
                    ('victim', ('entity:actor', {}), {
                        'doc': 'The victim of the {title}.'}),

                    ('victim:name', ('entity:name', {}), {
                        'doc': 'The name of the victim of the {title}.'}),
                ),
                'doc': 'An interface for malicious acts which directly impact a victim.'}),
        ),
        'edges': (
            # some explicit examples...

            (('entity:actor', 'targeted', 'risk:targetable'), {
                'doc': 'The actor targets based on the target node.'}),

            (('entity:action', 'targeted', 'risk:targetable'), {
                'doc': 'The action represents the actor targeting based on the target node.'}),

            (('risk:theft', 'stole', 'meta:observable'), {
                'doc': 'The target node was stolen during the theft.'}),

            (('risk:theft', 'stole', 'phys:object'), {
                'doc': 'The target node was stolen during the theft.'}),

            (('risk:leak', 'leaked', 'meta:observable'), {
                'doc': 'The leak included the disclosure of the target node.'}),

            (('risk:loss:funds', 'had', 'econ:payment'), {
                'doc': 'The loss of funds included the payment.'}),

            (('risk:loss:data', 'had', 'file:attachment'), {
                'doc': 'The loss of data included the file.'}),

            (('risk:loss:life', 'had', 'entity:singular'), {
                'doc': 'The loss of life included the entity.'}),

            (('risk:extortion', 'leveraged', 'meta:observable'), {
                'doc': 'The extortion event was based on attacker access to the target node.'}),

            (('risk:outage', 'impacted', None), {
                'doc': 'The outage event impacted the availability of the target node.'}),

            (('risk:alert', 'about', None), {
                'doc': 'The alert is about the target node.'}),

            (('meta:observable', 'resembles', 'meta:observable'), {
                'doc': 'The source node resembles the target node.'}),

            # TODO we will need more of these...
            (('inet:proto:link', 'shows', 'risk:vulnerable'), {
                'doc': 'The network activity shows that the vulnerability was present.'}),

            # A few explicit -(ledto)> edges to reinforce the use case
            (('risk:attack', 'ledto', 'risk:outage'), {
                'doc': 'The attack led to the outage.'}),

            (('risk:extortion', 'ledto', 'econ:payment'), {
                'doc': 'The extortion led to the payment.'}),
        ),
    },
)
