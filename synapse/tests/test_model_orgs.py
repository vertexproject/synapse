import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types

from synapse.tests.common import *

class OrgTest(SynTest, ModelSeenMixin):

    def test_model_ou_has(self):
        with self.getRamCore() as core:
            org_guid = 32 * '0'
            org_tufo = core.formTufoByProp('ou:org', org_guid, name='The Vertex Project')
            orgval = org_tufo[1].get('ou:org')

            node = core.formTufoByProp('ou:has', (orgval, ('inet:fqdn', 'vertex.link')))
            self.ge(node[1].get('node:created'), 1519852535218)
            self.eq(node[1].get('ou:has'), '03870dc800bc21c7c594a900ae65f5cb')
            self.eq(node[1].get('ou:has:org'), orgval)
            self.eq(node[1].get('ou:has:xref'), 'inet:fqdn=vertex.link')
            self.eq(node[1].get('ou:has:xref:prop'), 'inet:fqdn')
            self.eq(node[1].get('ou:has:xref:node'), '42366d896b947b97e7f3b1afeb9433a3')

            self.none(core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3'))  # Not automatically formed
            core.formTufoByProp('inet:fqdn', 'vertex.link')
            fqdnfo = core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3')
            self.eq(fqdnfo[1].get('inet:fqdn'), 'vertex.link')

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

    def test_model_ou_201802281621(self):
        # FIXME a lot of this code can be combined with the ps:has migration
        N = 2
        # FORMS = ('ps:hasuser', 'ps:hashost', 'ps:hasalias', 'ps:hasphone', 'ps:hasemail', 'ps:haswebacct')
        FORMS = ('ou:hasfile', 'ou:hasfqdn')
        NODECOUNT = N * len(FORMS)
        TAGS = ['hehe', 'hehe.hoho']

        def _check_no_old_data_remains(core, oldname):
            tufos = core.getTufosByProp(oldname)
            self.len(0, tufos)
            rows = core.getJoinByProp(oldname)
            self.len(0, rows)

        def _check_tags(core, tufo, tags):
            self.eq(sorted(tags), sorted(s_tufo.tags(tufo)))

        def _check_tagforms(core, oldname, newname):
            self.len(0, core.getRowsByProp('syn:tagform:form', oldname))
            self.len(0, core.getJoinByProp(oldname))
            self.len(len(TAGS), core.getRowsByProp('syn:tagform:form', newname))

        def _check_tagdarks(core, oldname, newname, count):
            self.len(0, core.getRowsByProp('_:*' + oldname + '#hehe.hoho'))
            self.len(0, core.getRowsByProp('_:*' + oldname + '#hehe'))
            self.len(count, core.getRowsByProp('_:*' + newname + '#hehe.hoho'))
            self.len(count, core.getRowsByProp('_:*' + newname + '#hehe'))

        def _check_darkmodlrev(core, tufo):
            dark_rows = core.getRowsById(tufo[0][::-1])
            self.true(any([p == '_:dark:syn:modl:rev' and v == 'ou:201802281621' for (i, p, v, t) in dark_rows]))

        def run_assertions(core, oldname, reftype, tufo_check):
            # assert that the correct number of items was migrated
            tufos = core.getTufosByProp('ou:has:xref:prop', reftype)
            self.len(N, tufos)

            # check that properties were correctly migrated and tags were not damaged
            tufo = tufo_check(core)

            # check that tags were correctly migrated
            _check_tags(core, tufo, TAGS)
            _check_tagforms(core, oldname, 'ou:has')
            _check_tagdarks(core, oldname, 'ou:has', NODECOUNT)
            _check_darkmodlrev(core, tufo)

            # assert that no old data remains
            _check_no_old_data_remains(core, oldname)

        def _addTag(tag, form):
            tick = now()
            iden = guid()
            tlib = s_types.TypeLib()
            form_valu, _ = tlib.getTypeNorm('syn:tagform', (tag, form))
            return [
                (iden, 'syn:tagform:title', '??', tick),
                (iden, 'syn:tagform', form_valu, tick),
                (iden, 'tufo:form', 'syn:tagform', tick),
                (iden, 'syn:tagform:tag', tag, tick),
                (iden, 'syn:tagform:form', form, tick),
                (iden, 'syn:tagform:doc', '??', tick),
            ]

        # Add rows to the storage layer so we have something to migrate
        adds = []

        # NOTE: Not migrating ou:hasalias, see below

        filecompguids = ['d146d3e5d63fc05baa25532b7cbac96e', '424079c0c7e3132073c90747ba5f59bd']
        for i in range(N):
            fval = 32 * str(i)
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hasfile', tick),
                (iden, 'ou:hasfile:file', fval, tick),
                (iden, 'ou:hasfile:org', 32 * 'a', tick),
                (iden, 'ou:hasfile', filecompguids[i], tick),
                (iden, 'ou:hasfile:seen:min', 0, tick),
                (iden, 'ou:hasfile:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hasfile#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hasfile#hehe', tick, tick),
            ])

        fqdncompguids = ['32d2112204c514b5195d3f03f537b687', '3b4194eeac4f7d197287ff247a61753c']
        fqdns = ['vertex.link', 'example.com']
        for i in range(N):
            fval = fqdns[i]
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hasfqdn', tick),
                (iden, 'ou:hasfqdn:fqdn', fval, tick),
                (iden, 'ou:hasfqdn:org', 32 * 'a', tick),
                (iden, 'ou:hasfqdn', fqdncompguids[i], tick),
                (iden, 'ou:hasfqdn:seen:min', 0, tick),
                (iden, 'ou:hasfqdn:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hasfqdn#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hasfqdn#hehe', tick, tick),
            ])

        for form in FORMS:
            adds.extend(_addTag('hehe.hoho', form))
            adds.extend(_addTag('hehe', form))

        # Spin up a core with the old rows, then run the migration and check the results
        with s_cortex.openstore('ram:///') as stor:
            stor.setModlVers('ou', 0)
            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='ou', vers=201802281621)

            with s_cortex.fromstore(stor) as core:

                orgval = 32 * 'a'

                # ou:hasalias =====================================================================
                # NOTE: This form is not being migrated as it is not possible to form them correctly
                # This can be migrated *IF* we make ou:alias a form

                # ou:hasfile ======================================================================
                oldname = 'ou:hasfile'
                reftype = 'file:bytes'
                refval = 32 * '0'
                xrval = '%s=%s' % (reftype, refval)
                hasval = '9c9eceba074787316af6750f307b8118'
                ndefval = '8c313cbd0f67bd15eb2bf3adea46a9dd'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:has')
                    self.eq(tufo[1]['ou:has'], hasval)
                    self.eq(tufo[1]['ou:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:has:xref'], xrval)
                    self.eq(tufo[1]['ou:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:hasfqdn ======================================================================
                oldname = 'ou:hasfqdn'
                reftype = 'inet:fqdn'
                refval = 'vertex.link'
                xrval = '%s=%s' % (reftype, refval)
                hasval = 'bb3df3b5ddbbd7c80b9dcbee28135668'
                ndefval = '42366d896b947b97e7f3b1afeb9433a3'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:has')
                    self.eq(tufo[1]['ou:has'], hasval)
                    self.eq(tufo[1]['ou:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:has:xref'], xrval)
                    self.eq(tufo[1]['ou:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ou:hasipv4 ======================================================================
                # ou:hashost ======================================================================
                # ou:hasemail =====================================================================
                # ou:hasphone =====================================================================
                # ou:haswebacct ===================================================================
