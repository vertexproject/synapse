import logging

import synapse.common as s_common
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

                    :time=20200202
                    :success=true
                    :targeted=true
                    :goal=*
                    :type=foo.bar
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
            ]''')
            self.eq(node.ndef, ('risk:attack', attk))
            self.eq(node.get('time'), 1580601600000)
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
            self.nn(node.get('used:file'))
            self.nn(node.get('goal'))
            self.nn(node.get('target'))
            self.nn(node.get('attacker'))

            self.len(1, await core.nodes('risk:attack -> risk:attacktype'))

            node = await addNode(f'''[
                    risk:vuln={vuln}
                    :name=myvuln
                    :type=mytype
                    :desc=mydesc

                    :exploited=$lib.true
                    :mitigated=$lib.false

                    :timeline:exploited=2020-01-14
                    :timeline:discovered=2020-01-14
                    :timeline:vendor:notified=2020-01-14
                    :timeline:vendor:fixed=2020-01-14
                    :timeline:published=2020-01-14

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
            ]''')
            self.eq(node.ndef, ('risk:vuln', vuln))
            self.eq(node.get('name'), 'myvuln')
            self.eq(node.get('type'), 'mytype')
            self.eq(node.get('desc'), 'mydesc')

            self.eq(node.get('exploited'), True)
            self.eq(node.get('mitigated'), False)

            self.eq(node.get('timeline:exploited'), 1578960000000)
            self.eq(node.get('timeline:discovered'), 1578960000000)
            self.eq(node.get('timeline:vendor:notified'), 1578960000000)
            self.eq(node.get('timeline:vendor:fixed'), 1578960000000)
            self.eq(node.get('timeline:published'), 1578960000000)

            self.eq(node.get('cve'), 'cve-2013-0000')
            self.eq(node.get('cve:desc'), 'Woot Woot')
            self.eq(node.get('cve:references'), ('http://vertex.link',))

            self.eq(node.get('nist:nvd:source'), 'nistsource')
            self.eq(node.get('nist:nvd:published'), 1633910400000)
            self.eq(node.get('nist:nvd:modified'), 1633910400000)

            self.eq(node.get('cisa:kev:name'), 'KevName')
            self.eq(node.get('cisa:kev:desc'), 'KevDesc')
            self.eq(node.get('cisa:kev:action'), 'KevAction')
            self.eq(node.get('cisa:kev:vendor'), 'kevvendor')
            self.eq(node.get('cisa:kev:product'), 'kevproduct')
            self.eq(node.get('cisa:kev:added'), 1641081600000)
            self.eq(node.get('cisa:kev:duedate'), 1641081600000)
            self.len(1, await core.nodes('risk:attack :target -> ps:contact'))
            self.len(1, await core.nodes('risk:attack :attacker -> ps:contact'))

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
                    :url=https://vertex.link/alerts/WOOT-20
                    :ext:id=WOOT-20
                ]
            ''')
            self.len(1, nodes)
            self.eq('bazfaz.', nodes[0].get('type'))
            self.eq('FooBar', nodes[0].get('name'))
            self.eq('BlahBlah', nodes[0].get('desc'))
            self.eq(2554848000000, nodes[0].get('detected'))
            self.eq('WOOT-20', nodes[0].get('ext:id'))
            self.eq('https://vertex.link/alerts/WOOT-20', nodes[0].get('url'))
            self.len(1, await core.nodes('risk:alert -> risk:vuln'))
            self.len(1, await core.nodes('risk:alert -> risk:attack'))

            nodes = await core.nodes('''[
                    risk:compromise=*
                    :name = "Visi Wants Pizza"
                    :desc = "Visi wants a pepperoni and mushroom pizza"
                    :type = when.noms.attack
                    :target = {[ ps:contact=* :name=ledo ]}
                    :attacker = {[ ps:contact=* :name=visi ]}
                    :campaign = *
                    :time = 20210202
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
            self.nn(nodes[0].get('target'))
            self.nn(nodes[0].get('attacker'))
            self.nn(nodes[0].get('campaign'))
            self.eq(1612224000000, nodes[0].get('time'))
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
            self.len(1, await core.nodes('risk:compromise -> ou:campaign'))
            self.len(1, await core.nodes('risk:compromise -> risk:compromisetype'))
            self.len(1, await core.nodes('risk:compromise :target -> ps:contact +:name=ledo'))
            self.len(1, await core.nodes('risk:compromise :attacker -> ps:contact +:name=visi'))

            nodes = await core.nodes('''
                [ risk:threat=*
                    :name=VTX-APT1
                    :desc=VTX-APT1
                    :tag=cno.threat.apt1
                    :reporter=*
                    :reporter:name=mandiant
                    :org=*
                    :org:loc=cn.shanghai
                    :org:name=apt1
                    :org:names=(comment crew,)
                    :goals=(*,)
                    :techniques=(*,)
                    :sophistication=high
                ]
            ''')
            self.len(1, nodes)
            self.eq('vtx-apt1', nodes[0].get('name'))
            self.eq('VTX-APT1', nodes[0].get('desc'))
            self.eq('apt1', nodes[0].get('org:name'))
            self.eq('cn.shanghai', nodes[0].get('org:loc'))
            self.eq(('comment crew',), nodes[0].get('org:names'))
            self.eq('cno.threat.apt1', nodes[0].get('tag'))
            self.eq('mandiant', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('reporter'))
            self.len(1, nodes[0].get('goals'))
            self.len(1, nodes[0].get('techniques'))

    async def test_model_risk_mitigation(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                risk:mitigation=*
                    :vuln=*
                    :name=FooBar
                    :desc=BazFaz
                    :hardware=*
                    :software=*
            ]''')
            self.eq('FooBar', nodes[0].props['name'])
            self.eq('BazFaz', nodes[0].props['desc'])
            self.len(1, await core.nodes('risk:mitigation -> risk:vuln'))
            self.len(1, await core.nodes('risk:mitigation -> it:prod:softver'))
            self.len(1, await core.nodes('risk:mitigation -> it:prod:hardware'))

    async def test_model_risk_tool_software(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ risk:tool:software=*
                    :soft=*
                    :soft:name=cobaltstrike
                    :soft:names=(beacon,)
                    :reporter=*
                    :reporter:name=vertex
                    :techniques=(*,)
                    :tag=cno.mal.cobaltstrike

                    :sophistication=high
                    :availability=public
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('soft'))

            self.nn(nodes[0].get('reporter'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('public.', nodes[0].get('availability'))

            self.eq('cobaltstrike', nodes[0].get('soft:name'))
            self.eq(('beacon',), nodes[0].get('soft:names'))

            self.len(1, nodes[0].get('techniques'))
            self.len(1, await core.nodes('risk:tool:software -> ou:org'))
            self.len(1, await core.nodes('risk:tool:software -> it:prod:soft'))
            self.len(1, await core.nodes('risk:tool:software -> ou:technique'))
            self.len(1, await core.nodes('risk:tool:software -> syn:tag'))
