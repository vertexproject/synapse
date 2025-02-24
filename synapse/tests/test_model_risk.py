import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.chop as s_chop
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class RiskModelTest(s_t_utils.SynTest):

    async def test_model_risk(self):

        async with self.getTestCore() as core:

            attk = s_common.guid()
            camp = s_common.guid()
            org0 = s_common.guid()
            pers = s_common.guid()
            host = s_common.guid()
            vuln = s_common.guid()
            soft = s_common.guid()
            hasv = s_common.guid()
            plac = s_common.guid()
            spec = s_common.guid()
            item = s_common.guid()

            async def addNode(text):
                nodes = await core.nodes(text)
                return nodes[0]

            node = await addNode(f'''[
                    risk:attack={attk}

                    :reporter=*
                    :reporter:name=vertex
                    :time=20200202
                    :detected = 20210203
                    :success=true
                    :targeted=true
                    :goal=*
                    :type=foo.bar
                    :severity=10
                    :desc=wootwoot
                    :campaign={camp}
                    :prev={attk}
                    :actor:org={org0}
                    :actor:person={pers}
                    :target = *
                    :attacker = *
                    :target:org={org0}
                    :target:host={host}
                    :target:place={plac}
                    :target:person={pers}
                    :via:ipv4=1.2.3.4
                    :via:ipv6=ff::01
                    :via:email=visi@vertex.link
                    :via:phone=1234567890
                    :used:vuln={vuln}
                    :used:url=https://attacker.com/
                    :used:host={host}
                    :used:email=visi@vertex.link
                    :used:file="*"
                    :used:server=tcp://1.2.3.4/
                    :used:software={soft}
                    :sophistication=high
                    :url=https://vertex.link/attacks/CASE-2022-03
                    :ext:id=CASE-2022-03
            ]''')
            self.eq(node.ndef, ('risk:attack', attk))
            self.eq(node.get('time'), 1580601600000)
            self.eq(node.get('detected'), 1612310400000)
            self.eq(node.get('desc'), 'wootwoot')
            self.eq(node.get('type'), 'foo.bar.')
            self.eq(node.get('success'), True)
            self.eq(node.get('targeted'), True)
            self.eq(node.get('campaign'), camp)
            self.eq(node.get('prev'), attk)
            self.eq(node.get('actor:org'), org0)
            self.eq(node.get('actor:person'), pers)
            self.eq(node.get('target:org'), org0)
            self.eq(node.get('target:host'), host)
            self.eq(node.get('target:place'), plac)
            self.eq(node.get('target:person'), pers)
            self.eq(node.get('reporter:name'), 'vertex')
            self.eq(node.get('via:ipv4'), 0x01020304)
            self.eq(node.get('via:ipv6'), 'ff::1')
            self.eq(node.get('via:email'), 'visi@vertex.link')
            self.eq(node.get('via:phone'), '1234567890')
            self.eq(node.get('used:vuln'), vuln)
            self.eq(node.get('used:url'), 'https://attacker.com/')
            self.eq(node.get('used:host'), host)
            self.eq(node.get('used:email'), 'visi@vertex.link')
            self.eq(node.get('used:server'), 'tcp://1.2.3.4')
            self.eq(node.get('used:software'), soft)
            self.eq(node.get('sophistication'), 40)
            self.eq(node.get('severity'), 10)
            self.eq(node.get('url'), 'https://vertex.link/attacks/CASE-2022-03')
            self.eq(node.get('ext:id'), 'CASE-2022-03')
            self.nn(node.get('used:file'))
            self.nn(node.get('goal'))
            self.nn(node.get('target'))
            self.nn(node.get('attacker'))
            self.nn(node.get('reporter'))

            self.len(1, await core.nodes('risk:attack -> risk:attacktype'))

            node = await addNode(f'''[
                risk:vuln={vuln}
                :cvss:v2 ?= "newp2"
                :cvss:v3 ?= "newp3.1"
                :priority=high
                :severity=high
                :tag=cno.vuln.woot
            ]''')

            self.none(node.get('cvss:v2'))
            self.none(node.get('cvss:v3'))
            self.eq(40, node.get('severity'))
            self.eq(40, node.get('priority'))
            self.eq('cno.vuln.woot', node.get('tag'))

            with self.raises(s_exc.BadTypeValu):
                node = await addNode(f'''[
                    risk:vuln={vuln}
                    :cvss:v2 = "newp2"
                ]''')

            with self.raises(s_exc.BadTypeValu):
                node = await addNode(f'''[
                    risk:vuln={vuln}
                    :cvss:v3 = "newp3.1"
                ]''')

            cvssv2 = '(AV:N/AC:L/Au:N/C:C/I:N/A:N/E:POC/RL:ND/RC:ND)'
            cvssv3 = 'CVSS:3.1/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X'

            node = await addNode(f'''[
                risk:vuln={vuln}
                :cvss:v2 = "{cvssv2}"
                :cvss:v3 = "{cvssv3}"
            ]''')

            self.eq(node.get('cvss:v2'), s_chop.cvss2_normalize(cvssv2))
            self.eq(node.get('cvss:v3'), s_chop.cvss3x_normalize(cvssv3))

            node = await addNode(f'''[
                    risk:vuln={vuln}
                    :name="My Vuln   is Cool"
                    :names=(hehe, haha, haha)
                    :type=mytype
                    :desc=mydesc

                    :exploited=$lib.true
                    :mitigated=$lib.false

                    :reporter=*
                    :reporter:name=vertex

                    :timeline:exploited=2020-01-14
                    :timeline:discovered=2020-01-14
                    :timeline:vendor:notified=2020-01-14
                    :timeline:vendor:fixed=2020-01-14
                    :timeline:published=2020-01-14

                    :id=" Vtx-000-1234 "

                    :cve=cve-2013-0000
                    :cve:desc="Woot Woot"
                    :cve:references=(http://vertex.link,)

                    :nist:nvd:source=NistSource
                    :nist:nvd:published=2021-10-11
                    :nist:nvd:modified=2021-10-11

                    :cisa:kev:name=KevName
                    :cisa:kev:desc=KevDesc
                    :cisa:kev:action=KevAction
                    :cisa:kev:vendor=KevVendor
                    :cisa:kev:product=KevProduct
                    :cisa:kev:added=2022-01-02
                    :cisa:kev:duedate=2022-01-02

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
            self.eq(node.ndef, ('risk:vuln', vuln))
            self.eq(node.get('name'), 'my vuln is cool')
            self.eq(node.get('names'), ('haha', 'hehe'))
            self.eq(node.get('type'), 'mytype.')
            self.eq(node.get('desc'), 'mydesc')

            self.eq(node.get('exploited'), True)
            self.eq(node.get('mitigated'), False)

            self.nn(node.get('reporter'))
            self.eq(node.get('reporter:name'), 'vertex')
            self.eq(node.get('timeline:exploited'), 1578960000000)
            self.eq(node.get('timeline:discovered'), 1578960000000)
            self.eq(node.get('timeline:vendor:notified'), 1578960000000)
            self.eq(node.get('timeline:vendor:fixed'), 1578960000000)
            self.eq(node.get('timeline:published'), 1578960000000)

            self.eq(node.get('id'), 'Vtx-000-1234')

            self.eq(node.get('cve'), 'cve-2013-0000')
            self.eq(node.get('cve:desc'), 'Woot Woot')
            self.eq(node.get('cve:references'), ('http://vertex.link',))

            self.eq(node.get('nist:nvd:source'), 'nistsource')
            self.eq(node.get('nist:nvd:published'), 1633910400000)
            self.eq(node.get('nist:nvd:modified'), 1633910400000)

            self.eq(node.get('cvss:v2'), 'AV:A/AC:M/Au:S/C:P/I:P/A:P/E:U/RL:OF/RC:UR/CDP:L/TD:L/CR:M/IR:M/AR:M')
            cvssv3 = 'AV:A/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:L/E:P/RL:T/RC:R/CR:L/IR:M/AR:L/MAV:A/MAC:L/MPR:N/MS:C/MC:N/MI:N/MA:N'
            self.eq(node.get('cvss:v3'), cvssv3)

            self.eq(node.get('cvss:v2_0:score'), 1.0)
            self.eq(node.get('cvss:v2_0:score:base'), 1.1)
            self.eq(node.get('cvss:v2_0:score:temporal'), 1.2)
            self.eq(node.get('cvss:v2_0:score:environmental'), 1.3)

            self.eq(node.get('cvss:v3_0:score'), 2.0)
            self.eq(node.get('cvss:v3_0:score:base'), 2.1)
            self.eq(node.get('cvss:v3_0:score:temporal'), 2.2)
            self.eq(node.get('cvss:v3_0:score:environmental'), 2.3)

            self.eq(node.get('cvss:v3_1:score'), 3.0)
            self.eq(node.get('cvss:v3_1:score:base'), 3.1)
            self.eq(node.get('cvss:v3_1:score:temporal'), 3.2)
            self.eq(node.get('cvss:v3_1:score:environmental'), 3.3)

            self.eq(node.get('cisa:kev:name'), 'KevName')
            self.eq(node.get('cisa:kev:desc'), 'KevDesc')
            self.eq(node.get('cisa:kev:action'), 'KevAction')
            self.eq(node.get('cisa:kev:vendor'), 'kevvendor')
            self.eq(node.get('cisa:kev:product'), 'kevproduct')
            self.eq(node.get('cisa:kev:added'), 1641081600000)
            self.eq(node.get('cisa:kev:duedate'), 1641081600000)
            self.len(1, await core.nodes('risk:attack :target -> ps:contact'))
            self.len(1, await core.nodes('risk:attack :attacker -> ps:contact'))

            self.len(1, nodes := await core.nodes('[ risk:vuln=({"name": "hehe"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            node = await addNode(f'''[
                risk:hasvuln={hasv}
                :vuln={vuln}
                :person={pers}
                :org={org0}
                :place={plac}
                :software={soft}
                :hardware=*
                :spec={spec}
                :item={item}
                :host={host}
            ]''')
            self.eq(node.ndef, ('risk:hasvuln', hasv))
            self.eq(node.get('vuln'), vuln)
            self.eq(node.get('person'), pers)
            self.eq(node.get('org'), org0)
            self.eq(node.get('place'), plac)
            self.eq(node.get('software'), soft)
            self.eq(node.get('spec'), spec)
            self.eq(node.get('item'), item)
            self.eq(node.get('host'), host)
            self.nn(node.get('hardware'))
            self.len(1, await core.nodes('risk:hasvuln -> it:prod:hardware'))

            nodes = await core.nodes('''
                [ risk:alert=*
                    :type=BazFaz
                    :name=FooBar
                    :desc=BlahBlah
                    :detected=20501217
                    :attack=*
                    :vuln=*
                    :status=todo
                    :assignee=$lib.user.iden
                    :ext:assignee = {[ ps:contact=* :email=visi@vertex.link ]}
                    :url=https://vertex.link/alerts/WOOT-20
                    :ext:id=WOOT-20
                    :engine={[ it:prod:softver=* :name=visiware ]}
                    :host=*
                    :priority=high
                    :severity=highest
                    :service:platform=*
                    :service:instance=*
                    :service:account=*
                ]
            ''')
            self.len(1, nodes)
            self.eq(20, nodes[0].get('status'))
            self.eq(40, nodes[0].get('priority'))
            self.eq(50, nodes[0].get('severity'))
            self.eq('bazfaz.', nodes[0].get('type'))
            self.eq('FooBar', nodes[0].get('name'))
            self.eq('BlahBlah', nodes[0].get('desc'))
            self.eq(2554848000000, nodes[0].get('detected'))
            self.eq('WOOT-20', nodes[0].get('ext:id'))
            self.eq('https://vertex.link/alerts/WOOT-20', nodes[0].get('url'))
            self.eq(core.auth.rootuser.iden, nodes[0].get('assignee'))
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('ext:assignee'))
            self.len(1, await core.nodes('risk:alert -> it:host'))
            self.len(1, await core.nodes('risk:alert -> risk:vuln'))
            self.len(1, await core.nodes('risk:alert -> risk:attack'))
            self.len(1, await core.nodes('risk:alert :engine -> it:prod:softver'))
            self.len(1, await core.nodes('risk:alert :service:account -> inet:service:account'))
            self.len(1, await core.nodes('risk:alert :service:platform -> inet:service:platform'))
            self.len(1, await core.nodes('risk:alert :service:instance -> inet:service:instance'))

            nodes = await core.nodes('''[
                    risk:compromise=*
                    :vector=*
                    :name = "Visi Wants Pizza"
                    :desc = "Visi wants a pepperoni and mushroom pizza"
                    :type = when.noms.attack
                    :url=https://vertex.link/pwned
                    :ext:id=PWN-00
                    :reporter = *
                    :reporter:name = vertex
                    :severity = 10
                    :target = {[ ps:contact=* :name=ledo ]}
                    :attacker = {[ ps:contact=* :name=visi ]}
                    :campaign = *
                    :time = 20210202
                    :detected = 20210203
                    :lasttime = 20210204
                    :duration = 2D
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
            self.eq('PWN-00', nodes[0].get('ext:id'))
            self.eq('https://vertex.link/pwned', nodes[0].get('url'))
            self.nn(nodes[0].get('target'))
            self.nn(nodes[0].get('attacker'))
            self.nn(nodes[0].get('campaign'))
            self.nn(nodes[0].get('reporter'))
            self.eq(1612224000000, nodes[0].get('time'))
            self.eq(1612310400000, nodes[0].get('detected'))
            self.eq(1612396800000, nodes[0].get('lasttime'))
            self.eq(172800000, nodes[0].get('duration'))
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
            self.len(1, await core.nodes('risk:compromise -> ou:campaign'))
            self.len(1, await core.nodes('risk:compromise -> risk:compromisetype'))
            self.len(1, await core.nodes('risk:compromise :vector -> risk:attack'))
            self.len(1, await core.nodes('risk:compromise :target -> ps:contact +:name=ledo'))
            self.len(1, await core.nodes('risk:compromise :attacker -> ps:contact +:name=visi'))

            nodes = await core.nodes('''
                [ risk:threat=*
                    :name=VTX-APT1
                    :desc=VTX-APT1
                    :tag=cno.threat.apt1
                    :active=(2012,2023)
                    :activity=high
                    :reporter=*
                    :reporter:name=mandiant
                    :reporter:discovered=202202
                    :reporter:published=202302
                    :org=*
                    :org:loc=cn.shanghai
                    :org:name=apt1
                    :org:names=(comment crew,)
                    :country={gen.pol.country ua}
                    :country:code=ua
                    :goals=(*,)
                    :techniques=(*,)
                    :sophistication=high
                    :merged:time = 20230111
                    :merged:isnow = {[ risk:threat=* ]}
                    :mitre:attack:group=G0001
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq('vtx-apt1', nodes[0].get('name'))
            self.eq('VTX-APT1', nodes[0].get('desc'))
            self.eq(40, nodes[0].get('activity'))
            self.eq('apt1', nodes[0].get('org:name'))
            self.eq('ua', nodes[0].get('country:code'))
            self.eq('cn.shanghai', nodes[0].get('org:loc'))
            self.eq(('comment crew',), nodes[0].get('org:names'))
            self.eq('cno.threat.apt1', nodes[0].get('tag'))
            self.eq('mandiant', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('country'))
            self.nn(nodes[0].get('reporter'))
            self.nn(nodes[0].get('merged:isnow'))
            self.eq((1325376000000, 1672531200000), nodes[0].get('active'))
            self.eq(1673395200000, nodes[0].get('merged:time'))
            self.eq(1643673600000, nodes[0].get('reporter:discovered'))
            self.eq(1675209600000, nodes[0].get('reporter:published'))
            self.eq('G0001', nodes[0].get('mitre:attack:group'))

            self.len(1, nodes[0].get('goals'))
            self.len(1, nodes[0].get('techniques'))
            self.len(1, await core.nodes('risk:threat:merged:isnow -> risk:threat'))
            self.len(1, await core.nodes('risk:threat -> it:mitre:attack:group'))

            self.len(1, nodes := await core.nodes('[ risk:threat=({"org:name": "comment crew"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''[ risk:leak=*
                :name="WikiLeaks ACME      Leak"
                :desc="WikiLeaks leaked ACME stuff."
                :disclosed=20231102
                :owner={ gen.ou.org.hq acme }
                :leaker={ gen.ou.org.hq wikileaks }
                :recipient={ gen.ou.org.hq everyone }
                :type=public
                :goal={[ ou:goal=* :name=publicity ]}
                :compromise={[ risk:compromise=* :target={ gen.ou.org.hq acme } ]}
                :public=(true)
                :public:url=https://wikileaks.org/acme
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :size:bytes=99
                :size:count=33
                :size:percent=12
                :extortion=*
            ]''')
            self.len(1, nodes)
            self.eq('wikileaks acme leak', nodes[0].get('name'))
            self.eq('WikiLeaks leaked ACME stuff.', nodes[0].get('desc'))
            self.eq(1698883200000, nodes[0].get('disclosed'))
            self.eq('public.', nodes[0].get('type'))
            self.eq(1, nodes[0].get('public'))
            self.eq(99, nodes[0].get('size:bytes'))
            self.eq(33, nodes[0].get('size:count'))
            self.eq(12, nodes[0].get('size:percent'))
            self.eq('https://wikileaks.org/acme', nodes[0].get('public:url'))
            self.eq('vertex', nodes[0].get('reporter:name'))

            self.len(1, await core.nodes('risk:leak -> risk:extortion'))
            self.len(1, await core.nodes('risk:leak -> risk:leak:type:taxonomy'))
            self.len(1, await core.nodes('risk:leak :owner -> ps:contact +:orgname=acme'))
            self.len(1, await core.nodes('risk:leak :leaker -> ps:contact +:orgname=wikileaks'))
            self.len(1, await core.nodes('risk:leak :recipient -> ps:contact +:orgname=everyone'))
            self.len(1, await core.nodes('risk:leak -> ou:goal +:name=publicity'))
            self.len(1, await core.nodes('risk:leak -> risk:compromise :target -> ps:contact +:orgname=acme'))
            self.len(1, await core.nodes('risk:leak :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''[ risk:extortion=*
                :demanded=20231102
                :deadline=20240329
                :name="APT99 Extorted     ACME"
                :desc="APT99 extorted ACME for a zillion vertex coins."
                :type=fingain
                :attacker={[ ps:contact=* :name=agent99 ]}
                :target={ gen.ou.org.hq acme }
                :success=(true)
                :enacted=(true)
                :public=(true)
                :public:url=https://apt99.com/acme
                :compromise={[ risk:compromise=* :target={ gen.ou.org.hq acme } ]}
                :demanded:payment:price=99.99
                :demanded:payment:currency=VTC
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :paid:price=12345
                :payments={[ econ:acct:payment=* ]}
            ]''')

            self.len(1, nodes)
            self.eq('apt99 extorted acme', nodes[0].get('name'))
            self.eq('APT99 extorted ACME for a zillion vertex coins.', nodes[0].get('desc'))
            self.eq(1698883200000, nodes[0].get('demanded'))
            self.eq(1711670400000, nodes[0].get('deadline'))
            self.eq('fingain.', nodes[0].get('type'))
            self.eq(1, nodes[0].get('public'))
            self.eq(1, nodes[0].get('success'))
            self.eq(1, nodes[0].get('enacted'))
            self.eq('https://apt99.com/acme', nodes[0].get('public:url'))
            self.eq('99.99', nodes[0].get('demanded:payment:price'))
            self.eq('vtc', nodes[0].get('demanded:payment:currency'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('12345', nodes[0].get('paid:price'))

            self.len(1, await core.nodes('risk:extortion -> econ:acct:payment'))
            self.len(1, await core.nodes('risk:extortion :target -> ps:contact +:orgname=acme'))
            self.len(1, await core.nodes('risk:extortion :attacker -> ps:contact +:name=agent99'))
            self.len(1, await core.nodes('risk:extortion -> risk:compromise :target -> ps:contact +:orgname=acme'))
            self.len(1, await core.nodes('risk:extortion :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''[
                risk:technique:masquerade=*
                    :node=(inet:fqdn, microsoft-verify.com)
                    :target=(inet:fqdn, microsoft.com)
                    :technique={[ ou:technique=* :name=masq ]}
                    :period=(2021, 2022)
            ]''')
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'microsoft.com'), nodes[0].get('target'))
            self.eq(('inet:fqdn', 'microsoft-verify.com'), nodes[0].get('node'))
            self.eq((1609459200000, 1640995200000), nodes[0].get('period'))
            self.nn(nodes[0].get('technique'))
            self.len(1, await core.nodes('risk:technique:masquerade -> ou:technique'))
            self.len(1, await core.nodes('risk:technique:masquerade :node -> * +inet:fqdn=microsoft-verify.com'))
            self.len(1, await core.nodes('risk:technique:masquerade :target -> * +inet:fqdn=microsoft.com'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :period=(2022, ?)
                    :node=(inet:fqdn, vertex.link)
                    :vuln={[ risk:vuln=* :name=redtree ]}
                    :technique={[ ou:technique=* :name=foo ]}
                    :mitigated=true
                    :mitigations={[ risk:mitigation=* :name=patchstuff ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('vuln'))
            self.eq(True, nodes[0].get('mitigated'))
            self.eq((1640995200000, 9223372036854775807), nodes[0].get('period'))
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0].get('node'))
            self.len(1, await core.nodes('risk:vulnerable -> risk:vuln'))
            self.len(1, await core.nodes('risk:vuln:name=redtree -> risk:vulnerable :node -> *'))
            self.len(1, await core.nodes('risk:vulnerable -> risk:mitigation'))
            self.len(1, await core.nodes('risk:vulnerable -> ou:technique'))

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
            self.eq((1672531200000, 1704067200000), nodes[0].get('period'))

            self.len(1, await core.nodes('risk:outage -> risk:attack'))
            self.len(1, await core.nodes('risk:outage -> risk:outage:cause:taxonomy'))
            self.len(1, await core.nodes('risk:outage :reporter -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('risk:outage :provider -> ou:org +:name="desert power"'))

    async def test_model_risk_mitigation(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                risk:mitigation=*
                    :vuln=*
                    :name="  FooBar  "
                    :type=foo.bar
                    :desc=BazFaz
                    :hardware=*
                    :software=*
                    :reporter:name=vertex
                    :reporter = { gen.ou.org vertex }
                    :mitre:attack:mitigation=M1036
            ]''')
            self.eq('foobar', nodes[0].props['name'])
            self.eq('BazFaz', nodes[0].props['desc'])
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.nn(nodes[0].get('reporter'))
            self.len(1, await core.nodes('risk:mitigation -> risk:vuln'))
            self.len(1, await core.nodes('risk:mitigation -> it:prod:softver'))
            self.len(1, await core.nodes('risk:mitigation -> it:prod:hardware'))
            self.len(1, await core.nodes('risk:mitigation -> it:mitre:attack:mitigation'))
            self.len(1, await core.nodes('risk:mitigation -> risk:mitigation:type:taxonomy'))

            nodes = await core.nodes('risk:mitigation:type:taxonomy=foo.bar [ :desc="foo that bars"]')
            self.len(1, nodes)
            self.eq('foo that bars', nodes[0].get('desc'))

    async def test_model_risk_tool_software(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:tool:software=*
                    :soft=*
                    :used=(2012,?)
                    :soft:name=cobaltstrike
                    :soft:names=(beacon,)
                    :reporter=*
                    :reporter:name=vertex
                    :reporter:discovered=202202
                    :reporter:published=202302
                    :techniques=(*,)
                    :tag=cno.mal.cobaltstrike
                    :mitre:attack:software=S0001
                    :id=" AAAbbb123  "

                    :sophistication=high
                    :availability=public
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(nodes[0].get('soft'))

            self.nn(nodes[0].get('reporter'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('public.', nodes[0].get('availability'))
            self.eq((1325376000000, 9223372036854775807), nodes[0].get('used'))
            self.eq(1643673600000, nodes[0].get('reporter:discovered'))
            self.eq(1675209600000, nodes[0].get('reporter:published'))
            self.eq('S0001', nodes[0].get('mitre:attack:software'))
            self.eq('AAAbbb123', nodes[0].get('id'))

            self.eq('cobaltstrike', nodes[0].get('soft:name'))
            self.eq(('beacon',), nodes[0].get('soft:names'))

            self.len(1, nodes[0].get('techniques'))
            self.len(1, await core.nodes('risk:tool:software -> ou:org'))
            self.len(1, await core.nodes('risk:tool:software -> it:prod:soft'))
            self.len(1, await core.nodes('risk:tool:software -> ou:technique'))
            self.len(1, await core.nodes('risk:tool:software -> syn:tag'))
            self.len(1, await core.nodes('risk:tool:software -> it:mitre:attack:software'))

            self.len(1, nodes := await core.nodes('[ risk:tool:software=({"soft:name": "beacon"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''
                [ risk:vuln:soft:range=*
                    :vuln={[ risk:vuln=* :name=woot ]}
                    :version:min={[ it:prod:softver=* :name=visisoft :vers=1.2.3 ]}
                    :version:max={[ it:prod:softver=* :name=visisoft :vers=1.3.0 ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('vuln'))
            self.nn(nodes[0].get('version:min'))
            self.nn(nodes[0].get('version:max'))
            self.len(2, await core.nodes('risk:vuln:name=woot -> risk:vuln:soft:range -> it:prod:softver'))

    async def test_model_risk_vuln_technique(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:vuln=* :name=foo <(uses)+ { [ ou:technique=* :name=bar ] } ]
            ''')
            self.len(1, await core.nodes('risk:vuln:name=foo <(uses)- ou:technique:name=bar'))
