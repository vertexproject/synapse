import synapse.lib.tufo as s_tufo

from synapse.tests.common import *

class OrgTest(SynTest, ModelSeenMixin):

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

    def test_model_org_has_file(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = 32 * 'f'

            node = core.formTufoByProp('ou:hasfile', (oval, fval))
            self.eq(node[1].get('ou:hasfile'), '9b7f777eee4e7d5d652a900c286148f1')
            self.eq(node[1].get('ou:hasfile:org'), oval)
            self.eq(node[1].get('ou:hasfile:file'), fval)
            self.check_seen(core, node)

    def test_model_org_has_fqdn(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = 'vertex.link'

            node = core.formTufoByProp('ou:hasfqdn', (oval, fval))
            self.eq(node[1].get('ou:hasfqdn'), 'a03c5c146283036868f196088982145a')
            self.eq(node[1].get('ou:hasfqdn:org'), oval)
            self.eq(node[1].get('ou:hasfqdn:fqdn'), fval)
            self.check_seen(core, node)

    def test_model_org_has_ipv4(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = '1.2.3.4'

            node = core.formTufoByProp('ou:hasipv4', (oval, fval))
            self.eq(node[1].get('ou:hasipv4'), '7c17a8170d0dc9bb2ec2a9ebb76edf29')
            self.eq(node[1].get('ou:hasipv4:org'), oval)
            self.eq(node[1].get('ou:hasipv4:ipv4'), 0x01020304)
            self.check_seen(core, node)

    def test_model_org_has_host(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = 32 * 'A'

            node = core.formTufoByProp('ou:hashost', (oval, fval))
            self.eq(node[1].get('ou:hashost'), '9a79fb0e6d2270076483e72cf572e514')
            self.eq(node[1].get('ou:hashost:org'), oval)
            self.eq(node[1].get('ou:hashost:host'), fval.lower())
            self.check_seen(core, node)

    def test_model_org_has_email(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = 'CONTACT@vertex.link'

            node = core.formTufoByProp('ou:hasemail', (oval, fval))
            self.eq(node[1].get('ou:hasemail'), 'c99e129a497cfbfd2dcce5ec89423276')
            self.eq(node[1].get('ou:hasemail:org'), oval)
            self.eq(node[1].get('ou:hasemail:email'), fval.lower())
            self.check_seen(core, node)

    def test_model_org_has_phone(self):
        with self.getRamCore() as core:
            oval = 32 * '0'
            fval = '1234567890'

            node = core.formTufoByProp('ou:hasphone', (oval, fval))
            self.eq(node[1].get('ou:hasphone'), 'b7fdb3ca07543cd42c0faf478628d8d7')
            self.eq(node[1].get('ou:hasphone:org'), oval)
            self.eq(node[1].get('ou:hasphone:phone'), int(fval))
            self.check_seen(core, node)

    def test_model_org_has_webacct(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ou:haswebacct', (iden, 'ROOTKIT.com/visi'))

            self.eq(node[1].get('ou:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ou:haswebacct:org'), iden)

            self.check_seen(core, node)

            self.nn(core.getTufoByProp('ou:org', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/visi'))

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
