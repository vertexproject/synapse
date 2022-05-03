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
                    :cve=cve-2013-0000
            ]''')
            self.eq(node.ndef, ('risk:vuln', vuln))
            self.eq(node.get('name'), 'myvuln')
            self.eq(node.get('type'), 'mytype')
            self.eq(node.get('desc'), 'mydesc')
            self.eq(node.get('cve'), 'cve-2013-0000')
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
                ]
            ''')
            self.len(1, nodes)
            self.eq('bazfaz', nodes[0].get('type'))
            self.eq('FooBar', nodes[0].get('name'))
            self.eq('BlahBlah', nodes[0].get('desc'))
            self.eq(2554848000000, nodes[0].get('detected'))
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
