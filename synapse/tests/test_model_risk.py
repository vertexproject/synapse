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
                    :campaign={camp}
                    :prev={attk}
                    :actor:org={org0}
                    :actor:person={pers}
                    :target:org={org0}
                    :target:host={host}
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
            self.eq(node.get('success'), True)
            self.eq(node.get('targeted'), True)
            self.eq(node.get('campaign'), camp)
            self.eq(node.get('prev'), attk)
            self.eq(node.get('actor:org'), org0)
            self.eq(node.get('actor:person'), pers)
            self.eq(node.get('target:org'), org0)
            self.eq(node.get('target:host'), host)
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

            node = await addNode(f'''[
                risk:hasvuln={hasv}
                :vuln={vuln}
                :person={pers}
                :org={org0}
                :place={plac}
                :software={soft}
                :spec={spec}
                :item={item}
            ]''')
            self.eq(node.ndef, ('risk:hasvuln', hasv))
            self.eq(node.get('vuln'), vuln)
            self.eq(node.get('person'), pers)
            self.eq(node.get('org'), org0)
            self.eq(node.get('place'), plac)
            self.eq(node.get('software'), soft)
            self.eq(node.get('spec'), spec)
            self.eq(node.get('item'), item)
