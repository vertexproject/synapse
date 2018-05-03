import synapse.common as s_common

import unittest
raise unittest.SkipTest()

import synapse.lib.types as s_types

from synapse.tests.common import *

class OrgTest(SynTest, ModelSeenMixin):

    def test_model_ou_has(self):
        with self.getRamCore() as core:
            org_guid = 32 * '0'
            org_tufo = core.formTufoByProp('ou:org', org_guid, name='The Vertex Project')
            orgval = org_tufo[1].get('ou:org')

            node = core.formTufoByProp('ou:org:has', (orgval, ('inet:fqdn', 'vertex.link')))
            self.ge(node[1].get('node:created'), 1519852535218)
            self.eq(node[1].get('ou:org:has'), '03870dc800bc21c7c594a900ae65f5cb')
            self.eq(node[1].get('ou:org:has:org'), orgval)
            self.eq(node[1].get('ou:org:has:xref'), 'inet:fqdn=vertex.link')
            self.eq(node[1].get('ou:org:has:xref:prop'), 'inet:fqdn')
            self.eq(node[1].get('ou:org:has:xref:node'), '42366d896b947b97e7f3b1afeb9433a3')

            self.none(core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3'))  # Not automatically formed
            core.formTufoByProp('inet:fqdn', 'vertex.link')
            fqdnfo = core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3')
            self.eq(fqdnfo[1].get('inet:fqdn'), 'vertex.link')

    def test_model_org_has_alias(self):
        with self.getRamCore() as core:
            iden = 32 * '0'

            node = core.formTufoByProp('ou:hasalias', (iden, 'cools'))
            self.eq(node[1].get('ou:hasalias'), '77ff3cd31931a67b658af31260ade638')
            self.eq(node[1].get('ou:hasalias:org'), iden)
            self.eq(node[1].get('ou:hasalias:alias'), 'cools')

            node = core.formTufoByProp('ou:hasalias', (iden, 'b4dZ'))
            self.eq(node[1].get('ou:hasalias'), '4be15b22e4081e102d6c8201ca26f28f')
            self.eq(node[1].get('ou:hasalias:org'), iden)
            self.eq(node[1].get('ou:hasalias:alias'), 'b4dz')

            self.check_seen(core, node)

            self.len(2, core.getTufosByProp('ou:hasalias:org', iden))

            self.raises(BadTypeValu, core.formTufoByProp, 'ou:hasalias', (iden, 'wee!!!'))

    def test_model_orgs_seed_alias(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:alias', 'wewtcorp', name='The Woot Corp')

            self.eq(node0[1].get('ou:org:alias'), 'wewtcorp')
            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            node1 = core.formTufoByProp('ou:org:alias', 'wewtcorp')

            self.eq(node0[0], node1[0])

    def test_model_orgs_seed_name(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:name', 'The Woot Corp')
            node1 = core.formTufoByProp('ou:org:name', 'the woot corp')

            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            self.eq(node0[0], node1[0])

    def test_model_orgs_oumember(self):
        with self.getRamCore() as core:
            pnode = core.formTufoByProp('ps:person', '*', name='grey, robert')
            _, pprop = s_tufo.ndef(pnode)

            onode = core.formTufoByProp('ou:org:name', 'derry sanitation corp')
            _, oprop = s_tufo.ndef(onode)

            mnode = core.formTufoByProp('ou:member',
                                        {'org': oprop, 'person': pprop},
                                        **{'start': '2017',
                                           'end': '2018',
                                           'title': 'Dancing Clown'})
            self.nn(mnode)
            _, mpprop = s_tufo.ndef(mnode)
            props = s_tufo.props(mnode)
            self.eq(props.get('org'), oprop)
            self.eq(props.get('person'), pprop)
            self.eq(props.get('end'), core.getTypeNorm('time', '2018')[0])
            self.eq(props.get('start'), core.getTypeNorm('time', '2017')[0])
            self.eq(props.get('title'), 'dancing clown')

            # We can traverse across the ou:member node
            nodes = core.eval('ps:person=%s -> ou:member:person :org -> ou:org' % pprop)
            self.len(1, nodes)
            self.eq(oprop, nodes[0][1].get('ou:org'))

            nodes = core.eval('ou:org=%s -> ou:member:org :person -> ps:person' % oprop)
            self.len(1, nodes)
            self.eq(pprop, nodes[0][1].get('ps:person'))

    def test_model_org_meeting(self):

        with self.getRamCore() as core:

            plac = s_common.guid()
            pers = s_common.guid()

            props = {
                'name': 'woot woot',
                'place': plac,
                'start': '2016 12 17 14:30',
                'end': '2016 12 17 15:00',
            }

            meet = core.formTufoByProp('ou:meet', '*', **props)

            self.eq(meet[1].get('ou:meet:name'), 'woot woot')
            self.eq(meet[1].get('ou:meet:start'), 1481985000000)
            self.eq(meet[1].get('ou:meet:end'), 1481986800000)
            self.eq(meet[1].get('ou:meet:place'), plac)

            iden = meet[1].get('ou:meet')

            props = {
                'arrived': '2016 12 17 14:33',
                'departed': '2016 12 17 15:13',
            }
            atnd = core.formTufoByProp('ou:meet:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:meet:attendee:meet'), iden)
            self.eq(atnd[1].get('ou:meet:attendee:person'), pers)
            self.eq(atnd[1].get('ou:meet:attendee:arrived'), 1481985180000)
            self.eq(atnd[1].get('ou:meet:attendee:departed'), 1481987580000)

            props = {
                'base': 'woot',
                'name': 'woot 2016',
                'place': plac,
                'start': '2016 12 17 14:30',
                'end': '2016 12 17 15:00',
            }
            conf = core.formTufoByProp('ou:conference', '*', **props)

            iden = conf[1].get('ou:conference')

            self.eq(conf[1].get('ou:conference:base'), 'woot')
            self.eq(conf[1].get('ou:conference:name'), 'woot 2016')
            self.eq(conf[1].get('ou:conference:place'), plac)
            self.eq(conf[1].get('ou:conference:start'), 1481985000000)
            self.eq(conf[1].get('ou:conference:end'), 1481986800000)

            props = {
                'arrived': '2016 12 17 14:33',
                'departed': '2016 12 17 15:13',
                'role:staff': 1,
                'role:speaker': 0,
            }
            atnd = core.formTufoByProp('ou:conference:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:conference:attendee:conference'), iden)
            self.eq(atnd[1].get('ou:conference:attendee:person'), pers)
            self.eq(atnd[1].get('ou:conference:attendee:arrived'), 1481985180000)
            self.eq(atnd[1].get('ou:conference:attendee:departed'), 1481987580000)
            self.eq(atnd[1].get('ou:conference:attendee:role:staff'), 1)
            self.eq(atnd[1].get('ou:conference:attendee:role:speaker'), 0)
