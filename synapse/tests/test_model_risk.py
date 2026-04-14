import logging

import synapse.exc as s_exc
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
                    :prev=*
                    :actor = {[ entity:contact=* ]}
                    :sophistication=high
                    :url=https://vertex.link/attacks/CASE-2022-03
                    :id=CASE-2022-03
            ]''')
            self.eq(nodes[0].ndef, ('risk:attack', '17eb16247855525d6f9cb1585a59877f'))
            self.propeq(nodes[0], 'time', 1580601600000000)
            self.propeq(nodes[0], 'detected', 1612310400000000)
            self.propeq(nodes[0], 'desc', 'wootwoot')
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'success', True)
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'sophistication', 40)
            self.propeq(nodes[0], 'severity', 10)
            self.propeq(nodes[0], 'url', 'https://vertex.link/attacks/CASE-2022-03')
            self.propeq(nodes[0], 'id', 'CASE-2022-03')
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, await core.nodes('risk:attack -> risk:attack:type:taxonomy'))
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

            self.propeq(nodes[0], 'severity', 40)
            self.propeq(nodes[0], 'priority', 40)
            self.propeq(nodes[0], 'tag', 'cno.vuln.woot')
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

            self.propeq(nodes[0], 'cvss:v2', s_chop.cvss2_normalize(cvssv2))
            self.propeq(nodes[0], 'cvss:v3', s_chop.cvss3x_normalize(cvssv3))

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
                    :discoverer={[ entity:contact=({"name": "visi"}) ]}
                    :vendor:notified=2020-01-14
                    :vendor:fixed=2020-01-14
                    :seen=(20200101, 20200601)

                    :id = CVE-2013-0000
                    :ids = (VISI-B-0000,)

                    :cvss:v2 = AV:A/AC:M/Au:S/C:P/I:P/A:P/E:U/RL:OF/RC:UR/CDP:L/TD:L/CR:M/IR:M/AR:M
                    :cvss:v2_0:score=1.0

                    :cvss:v3 = AV:A/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:L/E:P/RL:T/RC:R/CR:L/IR:M/AR:L/MAV:A/MAC:L/MPR:N/MUI:X/MS:C/MC:N/MI:N/MA:N

                    :cvss:v3_0:score=2.0

                    :cvss:v3_1:score=3.0
            ]''')
            self.propeq(nodes[0], 'name', 'my vuln is cool')
            self.propeq(nodes[0], 'names', ('haha', 'hehe'))
            self.propeq(nodes[0], 'type', 'mytype.')
            self.propeq(nodes[0], 'desc', 'mydesc')

            self.propeq(nodes[0], 'mitigated', False)

            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'exploited', 1578960000000000)
            self.propeq(nodes[0], 'discovered', 1578960000000000)
            self.propeq(nodes[0], 'vendor:notified', 1578960000000000)
            self.propeq(nodes[0], 'vendor:fixed', 1578960000000000)
            self.propeq(nodes[0], 'published', 1578960000000000)
            self.nn(nodes[0].get('seen'))

            self.propeq(nodes[0], 'id', 'CVE-2013-0000', form='it:sec:cve')
            self.propeq(nodes[0], 'ids', ('VISI-B-0000',))

            self.propeq(nodes[0], 'cvss:v2', 'AV:A/AC:M/Au:S/C:P/I:P/A:P/E:U/RL:OF/RC:UR/CDP:L/TD:L/CR:M/IR:M/AR:M')
            cvssv3 = 'AV:A/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:L/E:P/RL:T/RC:R/CR:L/IR:M/AR:L/MAV:A/MAC:L/MPR:N/MS:C/MC:N/MI:N/MA:N'
            self.propeq(nodes[0], 'cvss:v3', cvssv3)

            self.propeq(nodes[0], 'cvss:v2_0:score', 1.0)

            self.propeq(nodes[0], 'cvss:v3_0:score', 2.0)

            self.propeq(nodes[0], 'cvss:v3_1:score', 3.0)

            self.len(1, await core.nodes('risk:vuln:id=CVE-2013-0000 -> it:sec:cve'))
            self.len(1, await core.nodes('risk:vuln:id=CVE-2013-0000 :id -> it:sec:cve'))
            self.len(1, await core.nodes('risk:vuln:id=CVE-2013-0000 :discoverer -> entity:contact'))

            self.len(1, await core.nodes('risk:attack :actor -> entity:contact'))

            self.eq(nodes[0].ndef, (await core.nodes('[ risk:vuln=({"name": "hehe"}) ]'))[0].ndef)
            self.eq(nodes[0].ndef[1], await core.callStorm('return({[risk:vuln=({"id": "VISI-B-0000"})]})'))

            nodes = await core.nodes('''
                [ risk:alert=*
                    :type=BazFaz
                    :name=FooBar
                    :desc=BlahBlah
                    :created=20501217
                    :status=todo
                    :assignee={[ syn:user=root ]}
                    :url=https://vertex.link/alerts/WOOT-20
                    :id=WOOT-20
                    :engine={[ it:software=* :name=visiware ]}
                    :host=*
                    :priority=high
                    :severity=highest
                    :platform=*
                    :account={[ inet:service:account=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'status', 20)
            self.propeq(nodes[0], 'priority', 40)
            self.propeq(nodes[0], 'severity', 50)
            self.propeq(nodes[0], 'type', 'bazfaz.')
            self.propeq(nodes[0], 'name', 'foobar')
            self.propeq(nodes[0], 'desc', 'BlahBlah')
            self.propeq(nodes[0], 'created', 2554848000000000)
            self.propeq(nodes[0], 'id', 'WOOT-20')
            self.propeq(nodes[0], 'url', 'https://vertex.link/alerts/WOOT-20')
            self.propeq(nodes[0], 'assignee', core.auth.rootuser.iden, form='syn:user')
            self.nn(nodes[0].get('host'))
            self.len(1, await core.nodes('risk:alert -> it:host'))
            self.len(1, await core.nodes('risk:alert :engine -> it:software'))
            self.len(1, await core.nodes('risk:alert :account -> inet:service:account'))
            self.len(1, await core.nodes('risk:alert :platform -> inet:service:platform'))

            opts = {'vars': {'ndef': nodes[0].ndef[1]}}
            nodes = await core.nodes('risk:alert=$ndef [ :updated=20251003 ]', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'updated', s_time.parse('20251003'))

            self.len(1, await core.nodes('[ risk:alert=({"name": "bazfaz"}) +(about)> {[ file:bytes=* :name=alert.txt]} ]'))
            self.len(1, fnode := await core.nodes('risk:alert=({"name": "bazfaz"}) -(about)> file:bytes'))
            self.propeq(fnode[0], 'name', 'alert.txt')

            self.len(1, await core.nodes('[ meta:rule=({"name": "bar"}) +(generated)> {[ risk:alert=({"name": "foo"}) ]} ]'))
            self.len(1, nodes := await core.nodes('meta:rule=({"name": "bar"}) -(generated)> risk:alert'))
            self.propeq(nodes[0], 'name', 'foo')

            self.len(1, await core.nodes('[ meta:rule=({"name": "baz"}) +(generated)> {[ it:log:event=({"mesg": "faz"}) ]} ]'))
            self.len(1, nodes := await core.nodes('meta:rule=({"name": "baz"}) -(generated)> it:log:event'))
            self.propeq(nodes[0], 'mesg', 'faz')

            nodes = await core.nodes('''[
                    risk:compromise=*
                    :vector=*
                    :tag=foo.bar
                    :name = "Visi Wants Pizza"
                    :desc = "Visi wants a pepperoni and mushroom pizza"
                    :type = when.noms.attack
                    :url=https://vertex.link/pwned
                    :id=PWN-00
                    :reporter = {[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name = vertex
                    :severity = 10
                    :victim = {[ entity:contact=* :name=ledo ]}
                    :actor = {[ entity:contact=* :name=visi ]}
                    :period = (20210202, 20210204)
                    :loss:pii = 400
                    :cost = 1337
                    :loss:life = 0
                    :loss:bytes = 1024
            ]''')

            self.propeq(nodes[0], 'tag', 'foo.bar')
            self.propeq(nodes[0], 'name', 'visi wants pizza')
            self.propeq(nodes[0], 'desc', 'Visi wants a pepperoni and mushroom pizza')
            self.propeq(nodes[0], 'type', 'when.noms.attack.')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'id', 'PWN-00')
            self.propeq(nodes[0], 'url', 'https://vertex.link/pwned')
            self.nn(nodes[0].get('victim'))
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'period', (1612224000000000, 1612396800000000, 172800000000))
            self.propeq(nodes[0], 'loss:pii', 400)
            self.propeq(nodes[0], 'cost', '1337')
            self.propeq(nodes[0], 'loss:life', 0)
            self.propeq(nodes[0], 'loss:bytes', 1024)
            self.propeq(nodes[0], 'severity', 10)
            self.len(1, await core.nodes('risk:compromise -> syn:tag'))
            self.len(1, await core.nodes('risk:compromise -> risk:compromise:type:taxonomy'))
            self.len(1, await core.nodes('risk:compromise :vector -> risk:attack'))
            self.len(1, await core.nodes('risk:compromise :victim -> entity:contact +:name=ledo'))
            self.len(1, await core.nodes('risk:compromise :actor -> entity:contact +:name=visi'))

            nodes = await core.nodes('''
                [ risk:threat=*
                    :id=VTX-APT1
                    :name=apt1
                    :names=(comment crew,)
                    :desc=VTX-APT1
                    :resolved={[ risk:threat=(foo, bar) :name="foo bar"]}
                    :tag=cno.threat.apt1
                    :active=(2012,2023)
                    :activity=high
                    :reporter={[ ou:org=({"name": "mandiant"}) ]}
                    :reporter:name=mandiant
                    :discovered=202202
                    :published=202302
                    :sophistication=high
                    :superseded = 20230111
                    :place:loc=cn.shanghai
                    :place:country={gen.pol.country cn}
                    :place:country:code=cn
                ]
                $threat = $node
                $_ = {[ risk:threat=* :name=apt1next :supersedes=($threat,) ]}
                $_ = {[ doc:reference=({"source": $threat, "doc:url": "https://vtx.lk"}) ]}
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(nodes[0], 'id', 'VTX-APT1')
            self.propeq(nodes[0], 'name', 'apt1')
            self.propeq(nodes[0], 'names', ('comment crew',))
            self.propeq(nodes[0], 'desc', 'VTX-APT1')
            self.propeq(nodes[0], 'activity', 40)
            self.propeq(nodes[0], 'place:country:code', 'cn')
            self.propeq(nodes[0], 'place:loc', 'cn.shanghai')
            self.propeq(nodes[0], 'tag', 'cno.threat.apt1')
            self.propeq(nodes[0], 'reporter:name', 'mandiant')
            self.propeq(nodes[0], 'sophistication', 40)
            self.nn(nodes[0].get('reporter'))
            self.nn(nodes[0].get('place:country'))
            self.propeq(nodes[0], 'active', (1325376000000000, 1672531200000000, 347155200000000))
            self.propeq(nodes[0], 'superseded', 1673395200000000)
            self.propeq(nodes[0], 'discovered', 1643673600000000)
            self.propeq(nodes[0], 'published', 1675209600000000)
            self.nn(nodes[0].get('resolved'))

            self.len(1, await core.nodes('risk:threat:name=apt1 :resolved -> risk:threat'))
            self.len(1, await core.nodes('risk:threat:name=apt1 -> doc:reference'))

            await core.nodes('risk:threat:name=apt1 [ +(targeted)> {[ meta:topic=cybersecurity ]} ]')
            self.len(1, await core.nodes('risk:threat:name=apt1 -(targeted)> meta:topic'))

            nodes = await core.nodes('risk:threat:name=apt1 -> risk:threat:supersedes')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'apt1next')

            self.len(1, nodes := await core.nodes('[ risk:threat=({"name": "comment crew"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''[ risk:leak=*
                :name="WikiLeaks ACME      Leak"
                :desc="WikiLeaks leaked ACME stuff."
                :time=20231102
                :victim={ gen.ou.org acme }
                :actor={ gen.ou.org wikileaks }
                :recipient={ gen.ou.org everyone }
                :type=public
                :public=(true)
                :urls=(https://wikileaks.org/acme,)
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :size:bytes=99
                :size:count=33
                :size:percent=12
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'wikileaks acme leak')
            self.propeq(nodes[0], 'desc', 'WikiLeaks leaked ACME stuff.')
            self.propeq(nodes[0], 'time', 1698883200000000)
            self.propeq(nodes[0], 'type', 'public.')
            self.propeq(nodes[0], 'public', 1)
            self.propeq(nodes[0], 'size:bytes', 99)
            self.propeq(nodes[0], 'size:count', 33)
            self.propeq(nodes[0], 'size:percent', 12)
            self.propeq(nodes[0], 'urls', ('https://wikileaks.org/acme',))
            self.propeq(nodes[0], 'reporter:name', 'vertex')

            self.len(1, await core.nodes('risk:leak -> risk:leak:type:taxonomy'))
            self.len(1, await core.nodes('risk:leak :victim -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:leak :actor -> ou:org +:name=wikileaks'))
            self.len(1, await core.nodes('risk:leak :recipient -> ou:org +:name=everyone'))
            self.len(1, await core.nodes('risk:leak :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''[ risk:extortion=*
                :name="APT99 Extorted     ACME"
                :desc="APT99 extorted ACME for a zillion vertex coins."
                :type=fingain
                :actor={[ entity:contact=* :name=agent99 ]}
                :victim={ gen.ou.org acme }
                :target={ gen.ou.org acme }
                :success=(true)
                :enacted=(true)
                :public=(true)
                :public:url=https://apt99.com/acme
                :compromise={[ risk:compromise=* :victim={ gen.ou.org acme } ]}
                :reporter={ gen.ou.org vertex }
                :reporter:name=vertex
                :paid:price=12345
            ]''')

            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'apt99 extorted acme')
            self.propeq(nodes[0], 'desc', 'APT99 extorted ACME for a zillion vertex coins.')
            self.propeq(nodes[0], 'type', 'fingain.')
            self.propeq(nodes[0], 'public', 1)
            self.propeq(nodes[0], 'success', 1)
            self.propeq(nodes[0], 'enacted', 1)
            self.propeq(nodes[0], 'public:url', 'https://apt99.com/acme')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'paid:price', '12345')

            self.len(1, await core.nodes('risk:extortion :victim -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:extortion :target -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:extortion :actor -> entity:contact +:name=agent99'))
            self.len(1, await core.nodes('risk:extortion -> risk:compromise :victim -> ou:org +:name=acme'))
            self.len(1, await core.nodes('risk:extortion :reporter -> ou:org +:name=vertex'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :period=(2022, ?)
                    :to={[ risk:vuln=* :name=redtree ]}
                    :mitigated=true
                    :mitigations={[
                        ( risk:mitigation=* :name=patchstuff )
                        ( meta:technique=* :name=dothing )
                    ]}
                    <(shows)+ {[ inet:flow=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('to'))
            self.propeq(nodes[0], 'mitigated', True)
            self.propeq(nodes[0], 'period', (1640995200000000, 9223372036854775807, 0xffffffffffffffff))
            self.len(1, await core.nodes('risk:vulnerable -> risk:vuln'))
            self.len(1, await core.nodes('risk:vulnerable <(shows)- inet:flow'))

            nodes = await core.nodes('risk:vulnerable :mitigations -> *')
            self.sorteq(['meta:technique', 'risk:mitigation'], [n.ndef[0] for n in nodes])

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ it:software=* :name=vulnsoft ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('node'))
            self.len(1, await core.nodes('risk:vulnerable :node -> it:software +:name=vulnsoft'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ inet:server=tcp://1.2.3.4:80 ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> inet:server'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ ou:asset=* :name=myasset ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> ou:asset +:name=myasset'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ it:host=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> it:host'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ inet:client=tcp://5.6.7.8:12345 ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> inet:client'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ inet:service:platform=* :name=myplatform ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> inet:service:platform +:name=myplatform'))

            nodes = await core.nodes('''
                [ risk:vulnerable=*
                    :node={[ it:hardware=* :name=myhardware ]}
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('risk:vulnerable :node -> it:hardware +:name=myhardware'))

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
            self.propeq(nodes[0], 'name', 'the big one')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'provider:name', 'desert power')
            self.propeq(nodes[0], 'type', 'service.power.')
            self.propeq(nodes[0], 'cause', 'nature.earthquake.')
            self.propeq(nodes[0], 'period', (1672531200000000, 1704067200000000, 31536000000000))

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
                    +(uses)> {[ meta:rule=* it:hardware=* ]}
            ]''')
            self.propeq(nodes[0], 'name', 'foobar')
            self.propeq(nodes[0], 'names', ('bar', 'foo'))
            self.propeq(nodes[0], 'desc', 'BazFaz')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'id', 'IDa123')
            self.nn(nodes[0].get('reporter'))

            self.len(2, await core.nodes('risk:mitigation -(addresses)> *'))
            self.len(2, await core.nodes('risk:mitigation -(uses)> *'))
            self.len(1, await core.nodes('risk:mitigation -> meta:technique:type:taxonomy'))

            nodes = await core.nodes('meta:technique:type:taxonomy=foo.bar [ :desc="foo that bars"]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'desc', 'foo that bars')

    async def test_model_risk_theft(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                risk:theft=*
                    :actor={[ entity:contact=* :name=thief ]}
                    :victim={[ entity:contact=* :name=target ]}
                    :victim:name=target
                    :time=20230101
                    :value=9999.99
                    :reporter={ gen.ou.org vertex }
                    :reporter:name=vertex
                    +(stole)> {[ file:bytes=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('victim'))
            self.propeq(nodes[0], 'victim:name', 'target')
            self.propeq(nodes[0], 'value', '9999.99')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'time', 1672531200000000)

            self.len(1, await core.nodes('risk:theft :actor -> entity:contact +:name=thief'))
            self.len(1, await core.nodes('risk:theft :victim -> entity:contact +:name=target'))
            self.len(1, await core.nodes('risk:theft -(stole)> file:bytes'))
            self.len(1, await core.nodes('risk:theft :reporter -> ou:org +:name=vertex'))

    async def test_model_risk_vuln_technique(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:vuln=* :name=foo <(uses)+ { [ meta:technique=* :name=bar ] } ]
            ''')
            self.len(1, await core.nodes('risk:vuln:name=foo <(uses)- meta:technique:name=bar'))
