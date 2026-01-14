import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.lib.time as s_time
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class RiskModelTest(s_t_utils.SynTest):

    async def test_model_risk(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                risk:attack=17eb16247855525d6f9cb1585a59877f
                    :reporter={[ entity:contact=* ]}
                    :reporter:name=vertex
                    :time=20200202
                    :detected = 20210203
                    :success=true
                    :type=foo.bar
                    :severity=10
                    :desc=wootwoot
                    :campaign=*
                    :prev=*
                    :actor = {[ entity:contact=* ]}
                    :sophistication=high
                    :url=https://vertex.link/attacks/CASE-2022-03
                    :id=CASE-2022-03
                    +(had)> {[ entity:goal=* ]}
            ]''')
            self.eq(nodes[0].ndef, ('risk:attack', '17eb16247855525d6f9cb1585a59877f'))
            self.eq(nodes[0].get('time'), 1580601600000000)
            self.eq(nodes[0].get('detected'), 1612310400000000)
            self.eq(nodes[0].get('desc'), 'wootwoot')
            self.eq(nodes[0].get('type'), 'foo.bar.')
            self.eq(nodes[0].get('success'), True)
            self.eq(nodes[0].get('reporter:name'), 'vertex')
            self.eq(nodes[0].get('sophistication'), 40)
            self.eq(nodes[0].get('severity'), 10)
            self.eq(nodes[0].get('url'), 'https://vertex.link/attacks/CASE-2022-03')
            self.eq(nodes[0].get('id'), 'CASE-2022-03')
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, await core.nodes('risk:attack -(had)> entity:goal'))
            self.len(1, await core.nodes('risk:attack -> risk:attack:type:taxonomy'))
            self.len(1, await core.nodes('risk:attack=17eb16247855525d6f9cb1585a59877f -> entity:campaign'))
            self.len(1, await core.nodes('risk:attack=17eb16247855525d6f9cb1585a59877f :prev -> risk:attack'))
            self.len(1, await core.nodes('risk:attack=17eb16247855525d6f9cb1585a59877f :actor -> entity:contact'))

            nodes = await core.nodes('''[
                risk:vuln=17eb16247855525d6f9cb1585a59877f
                    :cvss:v2 ?= "newp2"
                    :cvss:v3 ?= "newp3.1"
                    :priority=high
                    :severity=high
                    :tag=cno.vuln.woot
            ]''')

            self.eq(nodes[0].get('severity'), 40)
            self.eq(nodes[0].get('priority'), 40)
            self.eq(nodes[0].get('tag'), 'cno.vuln.woot')
            self.none(nodes[0].get('cvss:v2'))
            self.none(nodes[0].get('cvss:v3'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[risk:vuln=17eb16247855525d6f9cb1585a59877f :cvss:v2=newp2 ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[risk:vuln=17eb16247855525d6f9cb1585a59877f :cvss:v3=newp3.1 ]')

            cvssv2 = '(AV:N/AC:L/Au:N/C:C/I:N/A:N/E:POC/RL:ND/RC:ND)'
            cvssv3 = 'CVSS:3.1/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X'

            opts = {'vars': {'v2': cvssv2, 'v3': cvssv3}}
            nodes = await core.nodes('[ risk:vuln=17eb16247855525d6f9cb1585a59877f :cvss:v2=$v2 :cvss:v3=$v3 ]', opts=opts)

            self.eq(nodes[0].get('cvss:v2'), s_chop.cvss2_normalize(cvssv2))
            self.eq(nodes[0].get('cvss:v3'), s_chop.cvss3x_normalize(cvssv3))

            nodes = await core.nodes('''[
                risk:vuln=*
                    :name="My Vuln   is Cool"
                    :names=(hehe, haha, haha)
                    :type=mytype
                    :desc=mydesc

                    :mitigated=(false)

                    :reporter={[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name=vertex

                    :published=2020-01-14
                    :exploited=2020-01-14
                    :discovered=2020-01-14
                    :vendor:notified=2020-01-14
                    :vendor:fixed=2020-01-14

                    :id = VISI-0000
                    :ids = (VISI-B-0000,)
                    :cve = CVE-2013-0000

                    :cvss:v2 = AV:A/AC:M/Au:S/C:P/I:P/A:P/E:U/RL:OF/RC:UR/CDP:L/TD:L/CR:M/IR:M/AR:M
                    :cvss:v2_0:score=1.0
                    :cvss:v2_0:score:base=1.1
                    :cvss:v2_0:score:temporal=1.2
                    :cvss:v2_0:score:environmental=1.3

                    :cvss:v3 = AV:A/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:L/E:P/RL:T/RC:R/CR:L/IR:M/AR:L/MAV:A/MAC:L/MPR:N/MUI:X/MS:C/MC:N/MI:N/MA:N

                    :cvss:v3_0:score=2.0
                    :cvss:v3_0:score:base=2.1
                    :cvss:v3_0:score:temporal=2.2
                    :cvss:v3_0:score:environmental=2.3

                    :cvss:v3_1:score=3.0
                    :cvss:v3_1:score:base=3.1
                    :cvss:v3_1:score:temporal=3.2
                    :cvss:v3_1:score:environmental=3.3
            ]''')
            self.eq(nodes[0].get('name'), 'my vuln is cool')
            self.eq(nodes[0].get('names'), ('haha', 'hehe'))
            self.eq(nodes[0].get('type'), 'mytype.')
            self.eq(nodes[0].get('desc'), 'mydesc')

            self.eq(nodes[0].get('mitigated'), False)

            self.nn(nodes[0].get('reporter'))
            self.eq(nodes[0].get('reporter:name'), 'vertex')
            self.eq(nodes[0].get('exploited'), 1578960000000000)
            self.eq(nodes[0].get('discovered'), 1578960000000000)
            self.eq(nodes[0].get('vendor:notified'), 1578960000000000)
            self.eq(nodes[0].get('vendor:fixed'), 1578960000000000)
            self.eq(nodes[0].get('published'), 1578960000000000)

            self.eq(nodes[0].get('id'), 'VISI-0000')
            self.eq(nodes[0].get('ids'), ('VISI-B-0000',))

            self.eq(nodes[0].get('cvss:v2'), 'AV:A/AC:M/Au:S/C:P/I:P/A:P/E:U/RL:OF/RC:UR/CDP:L/TD:L/CR:M/IR:M/AR:M')
            cvssv3 = 'AV:A/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:L/E:P/RL:T/RC:R/CR:L/IR:M/AR:L/MAV:A/MAC:L/MPR:N/MS:C/MC:N/MI:N/MA:N'
            self.eq(nodes[0].get('cvss:v3'), cvssv3)

            self.eq(nodes[0].get('cvss:v2_0:score'), 1.0)
            self.eq(nodes[0].get('cvss:v2_0:score:base'), 1.1)
            self.eq(nodes[0].get('cvss:v2_0:score:temporal'), 1.2)
            self.eq(nodes[0].get('cvss:v2_0:score:environmental'), 1.3)

            self.eq(nodes[0].get('cvss:v3_0:score'), 2.0)
            self.eq(nodes[0].get('cvss:v3_0:score:base'), 2.1)
            self.eq(nodes[0].get('cvss:v3_0:score:temporal'), 2.2)
            self.eq(nodes[0].get('cvss:v3_0:score:environmental'), 2.3)

            self.eq(nodes[0].get('cvss:v3_1:score'), 3.0)
            self.eq(nodes[0].get('cvss:v3_1:score:base'), 3.1)
            self.eq(nodes[0].get('cvss:v3_1:score:temporal'), 3.2)
            self.eq(nodes[0].get('cvss:v3_1:score:environmental'), 3.3)

            self.len(2, await core.nodes('risk:vuln:id=VISI-0000 -> meta:id'))
            self.len(1, await core.nodes('risk:vuln:cve=CVE-2013-0000 -> it:sec:cve'))
            self.len(1, await core.nodes('risk:vuln:cve=CVE-2013-0000 :cve -> it:sec:cve'))

            self.len(1, await core.nodes('risk:attack :actor -> entity:contact'))

            self.eq(nodes[0].ndef, (await core.nodes('[ risk:vuln=({"name": "hehe"}) ]'))[0].ndef)
            self.eq(nodes[0].ndef[1], await core.callStorm('return({[risk:vuln=({"id": "VISI-B-0000"})]})'))

            nodes = await core.nodes('''
                [ risk:alert=*
                    :type=BazFaz
                    :name=FooBar
                    :desc=BlahBlah
                    :detected=20501217
                    :vuln=*
                    :status=todo
                    :assignee=$lib.user.iden
                    :ext:assignee = {[ entity:contact=* :email=visi@vertex.link ]}
                    :url=https://vertex.link/alerts/WOOT-20
                    :id=WOOT-20
                    :engine={[ it:software=* :name=visiware ]}
                    :host=*
                    :priority=high
                    :severity=highest
                    :service:platform=*
                    :service:account=*
                ]
            ''')
            self.len(1, nodes)
            self.eq(20, nodes[0].get('status'))
            self.eq(40, nodes[0].get('priority'))
            self.eq(50, nodes[0].get('severity'))
            self.eq('bazfaz.', nodes[0].get('type'))
            self.eq('foobar', nodes[0].get('name'))
            self.eq('BlahBlah', nodes[0].get('desc'))
            self.eq(2554848000000000, nodes[0].get('detected'))
            self.eq('WOOT-20', nodes[0].get('id'))
            self.eq('https://vertex.link/alerts/WOOT-20', nodes[0].get('url'))
            self.eq(core.auth.rootuser.iden, nodes[0].get('assignee'))
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('ext:assignee'))
            self.len(1, await core.nodes('risk:alert -> it:host'))
            self.len(1, await core.nodes('risk:alert -> risk:vuln'))
            self.len(1, await core.nodes('risk:alert :engine -> it:software'))
            self.len(1, await core.nodes('risk:alert :service:account -> inet:service:account'))
            self.len(1, await core.nodes('risk:alert :service:platform -> inet:service:platform'))

            opts = {'vars': {'ndef': nodes[0].ndef[1]}}
            nodes = await core.nodes('risk:alert=$ndef [ :updated=20251003 ]', opts=opts)
            self.len(1, nodes)
            self.eq(s_time.parse('20251003'), nodes[0].get('updated'))

            self.len(1, await core.nodes('[ risk:alert=({"name": "bazfaz"}) +(about)> {[ file:bytes=* :name=alert.txt]} ]'))
            self.len(1, fnode := await core.nodes('risk:alert=({"name": "bazfaz"}) -(about)> file:bytes'))
            self.eq(fnode[0].get('name'), 'alert.txt')

            nodes = await core.nodes('''[
                    risk:compromise=*
                    :vector=*
                    :name = "Visi Wants Pizza"
                    :desc = "Visi wants a pepperoni and mushroom pizza"
                    :type = when.noms.attack
                    :url=https://vertex.link/pwned
                    :id=PWN-00
                    :reporter = {[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name = vertex
                    :severity = 10
                    :target = {[ entity:contact=* :name=ledo ]}
                    :actor = {[ entity:contact=* :name=visi ]}
                    :campaign = *
                    :period = (20210202, 20210204)
                    :detected = 20210203
                    :loss:pii = 400
                    :loss:econ = 1337
                    :loss:life = 0
                    :loss:bytes = 1024
                    :theft:price = 919
                    :ransom:paid = 1
                    :ransom:price = 99
                    :response:cost = 1010
                    :econ:currency = usd
            ]''')

            self.eq('visi wants pizza', nodes[0].get('name'))
            self.eq('Visi wants a pepperoni and mushroom pizza', nodes[0].get('desc'))
            self.eq('when.noms.attack.', nodes[0].get('type'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('PWN-00', nodes[0].get('id'))
            self.eq('https://vertex.link/pwned', nodes[0].get('url'))
            self.nn(nodes[0].get('target'))
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('campaign'))
            self.nn(nodes[0].get('reporter'))
            self.eq(nodes[0].get('period'), (1612224000000000, 1612396800000000, 172800000000))
            self.eq(1612310400000000, nodes[0].get('detected'))
            self.eq(400, nodes[0].get('loss:pii'))
            self.eq('1337', nodes[0].get('loss:econ'))
            self.eq(0, nodes[0].get('loss:life'))
            self.eq(1024, nodes[0].get('loss:bytes'))
            self.eq('919', nodes[0].get('theft:price'))
            self.eq('1', nodes[0].get('ransom:paid'))
            self.eq('99', nodes[0].get('ransom:price'))
            self.eq('1010', nodes[0].get('response:cost'))
            self.eq('usd', nodes[0].get('econ:currency'))
            self.eq(10, nodes[0].get('severity'))
            self.len(1, await core.nodes('risk:compromise -> entity:campaign'))
            self.len(1, await core.nodes('risk:compromise -> risk:compromise:type:taxonomy'))
            self.len(1, await core.nodes('risk:compromise :vector -> risk:attack'))
            self.len(1, await core.nodes('risk:compromise :target -> entity:contact +:name=ledo'))
            self.len(1, await core.nodes('risk:compromise :actor -> entity:contact +:name=visi'))

            nodes = await core.nodes('''
                [ risk:threat=*
                    :id=VTX-APT1
                    :name=apt1
                    :names=(comment crew,)
                    :desc=VTX-APT1
                    :tag=cno.threat.apt1
                    :active=(2012,2023)
                    :activity=high
                    :reporter={[ ou:org=({"name": "mandiant"}) ]}
                    :reporter:name=mandiant
                    :reporter:discovered=202202
                    :reporter:published=202302
                    :sophistication=high
                    :merged:time = 20230111
                    :merged:isnow = {[ risk:threat=* ]}
                    :place:loc=cn.shanghai
                    :place:country={gen.pol.country cn}
                    :place:country:code=cn
                    +(had)> {[ entity:goal=* ]}
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq('VTX-APT1', nodes[0].get('id'))
            self.eq('apt1', nodes[0].get('name'))
            self.eq(('comment crew',), nodes[0].get('names'))
            self.eq('VTX-APT1', nodes[0].get('desc'))
            self.eq(40, nodes[0].get('activity'))
            self.eq('cn', nodes[0].get('place:country:code'))
            self.eq('cn.shanghai', nodes[0].get('place:loc'))
            self.eq('cno.threat.apt1', nodes[0].get('tag'))
            self.eq('mandiant', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.nn(nodes[0].get('reporter'))
            self.nn(nodes[0].get('place:country'))
            self.nn(nodes[0].get('merged:isnow'))
            self.eq((1325376000000000, 1672531200000000, 347155200000000), nodes[0].get('active'))
            self.eq(1673395200000000, nodes[0].get('merged:time'))
            self.eq(1643673600000000, nodes[0].get('reporter:discovered'))
            self.eq(1675209600000000, nodes[0].get('reporter:published'))

            self.len(1, await core.nodes('risk:threat -(had)> entity:goal'))
            self.len(1, await core.nodes('risk:threat:merged:isnow -> risk:threat'))

            self.len(1, nodes := await core.nodes('[ risk:threat=({"name": "comment crew"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''[ risk:leak=*
                :name="WikiLeaks ACME      Leak"
                :desc="WikiLeaks leaked ACME stuff."
                :disclosed=20231102
                :owner={ gen.ou.org acme }
                :actor={ gen.ou.org wikileaks }
                :recipient={ gen.ou.org everyone }
                :type=public
                :compromise={[ risk:compromise=* :target={ gen.ou.org acme } ]}
                :public=(true)
                :public:urls=(https://wikileaks.org/acme,)
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :size:bytes=99
                :size:count=33
                :size:percent=12
                :extortion=*
                +(had)> {[ entity:goal=({"name": "publicity"}) ]}
            ]''')
            self.len(1, nodes)
            self.eq('wikileaks acme leak', nodes[0].get('name'))
            self.eq('WikiLeaks leaked ACME stuff.', nodes[0].get('desc'))
            self.eq(1698883200000000, nodes[0].get('disclosed'))
            self.eq('public.', nodes[0].get('type'))
            self.eq(1, nodes[0].get('public'))
            self.eq(99, nodes[0].get('size:bytes'))
            self.eq(33, nodes[0].get('size:count'))
            self.eq(12, nodes[0].get('size:percent'))
            self.eq(('https://wikileaks.org/acme',), nodes[0].get('public:urls'))
            self.eq('vertex', nodes[0].get('reporter:name'))

            self.len(1, await core.nodes('risk:leak -> risk:extortion'))
            self.len(1, await core.nodes('risk:leak -> risk:leak:type:taxonomy'))
            self.len(1, await core.nodes('risk:leak :owner -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:leak :actor -> ou:org +:name=wikileaks'))
            self.len(1, await core.nodes('risk:leak :recipient -> ou:org +:name=everyone'))
            self.len(1, await core.nodes('risk:leak -(had)> entity:goal +:name=publicity'))
            self.len(1, await core.nodes('risk:leak -> risk:compromise :target -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:leak :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''[ risk:extortion=*
                :demanded=20231102
                :deadline=20240329
                :name="APT99 Extorted     ACME"
                :desc="APT99 extorted ACME for a zillion vertex coins."
                :type=fingain
                :actor={[ entity:contact=* :name=agent99 ]}
                :target={ gen.ou.org acme }
                :success=(true)
                :enacted=(true)
                :public=(true)
                :public:url=https://apt99.com/acme
                :compromise={[ risk:compromise=* :target={ gen.ou.org acme } ]}
                :demanded:payment:price=99.99
                :demanded:payment:currency=VTC
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :paid:price=12345
                :payments={[ econ:payment=* ]}
            ]''')

            self.len(1, nodes)
            self.eq('apt99 extorted acme', nodes[0].get('name'))
            self.eq('APT99 extorted ACME for a zillion vertex coins.', nodes[0].get('desc'))
            self.eq(1698883200000000, nodes[0].get('demanded'))
            self.eq(1711670400000000, nodes[0].get('deadline'))
            self.eq('fingain.', nodes[0].get('type'))
            self.eq(1, nodes[0].get('public'))
            self.eq(1, nodes[0].get('success'))
            self.eq(1, nodes[0].get('enacted'))
            self.eq('https://apt99.com/acme', nodes[0].get('public:url'))
            self.eq('99.99', nodes[0].get('demanded:payment:price'))
            self.eq('vtc', nodes[0].get('demanded:payment:currency'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('12345', nodes[0].get('paid:price'))

            self.len(1, await core.nodes('risk:extortion -> econ:payment'))
            self.len(1, await core.nodes('risk:extortion :target -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:extortion :actor -> entity:contact +:name=agent99'))
            self.len(1, await core.nodes('risk:extortion -> risk:compromise :target -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:extortion :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :period=(2022, ?)
                    :node=(inet:fqdn, vertex.link)
                    :vuln={[ risk:vuln=* :name=redtree ]}
                    :technique={[ meta:technique=* :name=foo ]}
                    :mitigated=true
                    :mitigations={[ risk:mitigation=* :name=patchstuff ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('vuln'))
            self.eq(True, nodes[0].get('mitigated'))
            self.eq((1640995200000000, 9223372036854775807, 0xffffffffffffffff), nodes[0].get('period'))
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0].get('node'))
            self.len(1, await core.nodes('risk:vulnerable -> risk:vuln'))
            self.len(1, await core.nodes('risk:vuln:name=redtree -> risk:vulnerable :node -> *'))
            self.len(1, await core.nodes('risk:vulnerable -> risk:mitigation'))
            self.len(1, await core.nodes('risk:vulnerable -> meta:technique'))

            nodes = await core.nodes('''
                [ risk:outage=*
                    :name="The Big One"
                    :period=(2023, 2024)
                    :type=service.power
                    :cause=nature.earthquake
                    :provider={[ ou:org=* :name="desert power" ]}
                    :provider:name="desert power"
                    :attack={[ risk:attack=* ]}
                    :reporter={ ou:org:name=vertex }
                    :reporter:name=vertex
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('attack'))
            self.nn(nodes[0].get('reporter'))
            self.eq('the big one', nodes[0].get('name'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('desert power', nodes[0].get('provider:name'))
            self.eq('service.power.', nodes[0].get('type'))
            self.eq('nature.earthquake.', nodes[0].get('cause'))
            self.eq((1672531200000000, 1704067200000000, 31536000000000), nodes[0].get('period'))

            self.len(1, await core.nodes('risk:outage -> risk:attack'))
            self.len(1, await core.nodes('risk:outage -> risk:outage:cause:taxonomy'))
            self.len(1, await core.nodes('risk:outage :reporter -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('risk:outage :provider -> ou:org +:name="desert power"'))

    async def test_model_risk_mitigation(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                risk:mitigation=*
                    :name="  FooBar  "
                    :names = (Foo, Bar)
                    :id="  IDa123  "
                    :type=foo.bar
                    :desc=BazFaz
                    :reporter:name=vertex
                    :reporter = { gen.ou.org vertex }
                    +(addresses)> {[ risk:vuln=* meta:technique=* ]}
            ]''')
            self.eq('foobar', nodes[0].get('name'))
            self.eq(('bar', 'foo'), nodes[0].get('names'))
            self.eq('BazFaz', nodes[0].get('desc'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq('IDa123', nodes[0].get('id'))
            self.nn(nodes[0].get('reporter'))

            self.len(2, await core.nodes('risk:mitigation -(addresses)> *'))
            self.len(1, await core.nodes('risk:mitigation -> risk:mitigation:type:taxonomy'))

            nodes = await core.nodes('risk:mitigation:type:taxonomy=foo.bar [ :desc="foo that bars"]')
            self.len(1, nodes)
            self.eq('foo that bars', nodes[0].get('desc'))

    async def test_model_risk_tool_software(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:tool:software=*
                    :software=*
                    :used=(2012,?)
                    :software:name=cobaltstrike
                    :software:names=(beacon,)
                    :reporter={[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name=vertex
                    :reporter:discovered=202202
                    :reporter:published=202302
                    :tag=cno.mal.cobaltstrike
                    :id=" AAAbbb123  "

                    :sophistication=high
                    :availability=public
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(nodes[0].get('software'))

            self.nn(nodes[0].get('reporter'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('public.', nodes[0].get('availability'))
            self.eq((1325376000000000, 9223372036854775807, 0xffffffffffffffff), nodes[0].get('used'))
            self.eq(1643673600000000, nodes[0].get('reporter:discovered'))
            self.eq(1675209600000000, nodes[0].get('reporter:published'))
            self.eq('AAAbbb123', nodes[0].get('id'))

            self.eq('cobaltstrike', nodes[0].get('software:name'))
            self.eq(('beacon',), nodes[0].get('software:names'))

            self.len(1, await core.nodes('risk:tool:software -> ou:org'))
            self.len(1, await core.nodes('risk:tool:software -> syn:tag'))
            self.len(1, await core.nodes('risk:tool:software -> it:software'))

            self.len(1, nodes := await core.nodes('[ risk:tool:software=({"software:name": "beacon"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

    async def test_model_risk_vuln_technique(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:vuln=* :name=foo <(uses)+ { [ meta:technique=* :name=bar ] } ]
            ''')
            self.len(1, await core.nodes('risk:vuln:name=foo <(uses)- meta:technique:name=bar'))
