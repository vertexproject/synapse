import synapse.common as s_common

import synapse.lib.tufo as s_tufo
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

    def test_model_ou_201802281621(self):
        # NOTE: a lot of this code can be combined with the ps:has migration
        N = 2
        FORMS = ('ou:hasfile', 'ou:hasfqdn', 'ou:hasipv4', 'ou:hashost', 'ou:hasemail', 'ou:hasphone', 'ou:haswebacct')
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
            tufos = core.getTufosByProp('ou:org:has:xref:prop', reftype)
            self.len(N, tufos)

            # check that properties were correctly migrated and tags were not damaged
            tufo = tufo_check(core)

            # check that tags were correctly migrated
            _check_tags(core, tufo, TAGS)
            _check_tagforms(core, oldname, 'ou:org:has')
            _check_tagdarks(core, oldname, 'ou:org:has', NODECOUNT)
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

        ipv4compguids = ['d146d3e5d63fc05baa25532b7cbac96e', '424079c0c7e3132073c90747ba5f59bd']
        for i in range(N):
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hasipv4', tick),
                (iden, 'ou:hasipv4:ipv4', i, tick),
                (iden, 'ou:hasipv4:org', 32 * 'a', tick),
                (iden, 'ou:hasipv4', ipv4compguids[i], tick),
                (iden, 'ou:hasipv4:seen:min', 0, tick),
                (iden, 'ou:hasipv4:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hasipv4#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hasipv4#hehe', tick, tick),
            ])

        hostcompguids = ['d146d3e5d63fc05baa25532b7cbac96e', '424079c0c7e3132073c90747ba5f59bd']
        for i in range(N):
            hval = 32 * str(i)
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hashost', tick),
                (iden, 'ou:hashost:host', hval, tick),
                (iden, 'ou:hashost:org', 32 * 'a', tick),
                (iden, 'ou:hashost', hostcompguids[i], tick),
                (iden, 'ou:hashost:seen:min', 0, tick),
                (iden, 'ou:hashost:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hashost#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hashost#hehe', tick, tick),
            ])

        emailcompguids = ['32d2112204c514b5195d3f03f537b687', '3b4194eeac4f7d197287ff247a61753c']
        emails = ['example@vertex.link', 'visi@vertex.link']
        for i in range(N):
            email = emails[i]
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hasemail', tick),
                (iden, 'ou:hasemail:email', email, tick),
                (iden, 'ou:hasemail:org', 32 * 'a', tick),
                (iden, 'ou:hasemail', fqdncompguids[i], tick),
                (iden, 'ou:hasemail:seen:min', 0, tick),
                (iden, 'ou:hasemail:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hasemail#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hasemail#hehe', tick, tick),
            ])

        telcompguids = ['a20cf139c699973c05c959898b04f3ef', 'd1f1e18dd11375c32f83f053a318e37a']
        for i in range(N):
            phone = int('123456789' + str(i))
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:hasphone', tick),
                (iden, 'ou:hasphone:phone', phone, tick),
                (iden, 'ou:hasphone:org', 32 * 'a', tick),
                (iden, 'ou:hasphone', telcompguids[i], tick),
                (iden, 'ou:hasphone:seen:min', 0, tick),
                (iden, 'ou:hasphone:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:hasphone#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:hasphone#hehe', tick, tick),
            ])

        acctcompguids = ['d146d3e5d63fc05baa25532b7cbac96e', '424079c0c7e3132073c90747ba5f59bd']
        for i in range(N):
            acct = 'vertex.link/user%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ou:haswebacct', tick),
                (iden, 'ou:haswebacct:web:acct', acct, tick),
                (iden, 'ou:haswebacct:org', 32 * 'a', tick),
                (iden, 'ou:haswebacct', acctcompguids[i], tick),
                (iden, 'ou:haswebacct:seen:min', 0, tick),
                (iden, 'ou:haswebacct:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ou:haswebacct#hehe.hoho', tick, tick),
                (dark_iden, '_:*ou:haswebacct#hehe', tick, tick),
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
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

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
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:hasipv4 ======================================================================
                oldname = 'ou:hasipv4'
                reftype = 'inet:ipv4'
                refval = '0.0.0.0'
                xrval = '%s=%s' % (reftype, refval)
                hasval = '69339004f2dcb7d06454357d8809c764'
                ndefval = 'ac544a8fffd9636664df2254371aea5a'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), 0)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:hashost ======================================================================
                oldname = 'ou:hashost'
                reftype = 'it:host'
                refval = 32 * '0'
                xrval = '%s=%s' % (reftype, refval)
                hasval = '2b43700d635b1f9840d1bf83e4181830'
                ndefval = '09cd1fbc8b183f18c38ae034713af5e3'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:hasemail =====================================================================
                oldname = 'ou:hasemail'
                reftype = 'inet:email'
                refval = 'example@vertex.link'
                xrval = '%s=%s' % (reftype, refval)
                hasval = '56883ea61acc8bf4443dc3b9a60638cf'
                ndefval = 'e1b961ba74520aa06f5f4bb526f4ad1e'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:hasphone =====================================================================
                oldname = 'ou:hasphone'
                reftype = 'tel:phone'
                refval = 1234567890
                xrval = 'tel:phone=+1 (234) 567-890'
                hasval = '5650ba4dca5ef636817228cffc718dd3'
                ndefval = '0068a540030a8de1d3f3817e52d50b7c'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ou:haswebacct ===================================================================
                oldname = 'ou:haswebacct'
                reftype = 'inet:web:acct'
                refval = 'vertex.link/user0'
                xrval = '%s=%s' % (reftype, refval)
                hasval = '8001ce943435e274f1d83a6f17f61e44'
                ndefval = '0cd705305c7f4573a38b7e7c8f4ddef9'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ou:org:has:xref', xrval)
                    self.eq(tufo[1]['tufo:form'], 'ou:org:has')
                    self.eq(tufo[1]['ou:org:has'], hasval)
                    self.eq(tufo[1]['ou:org:has:seen:min'], 0)
                    self.eq(tufo[1]['ou:org:has:seen:max'], 1)
                    self.eq(tufo[1]['ou:org:has:xref'], xrval)
                    self.eq(tufo[1]['ou:org:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ou:org:has:xref:node'], ndefval)
                    self.eq(tufo[1]['ou:org:has:org'], orgval)

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, refval)
                    userfo = core.getTufoByProp('node:ndef', ndefval)
                    self.eq(userfo[1].get(reftype), refval)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

    def test_model_org_meeting(self):

        with self.getRamCore() as core:

            plac = s_common.guid()
            pers = s_common.guid()

            props = {
                'name': 'woot woot',
                'place': plac,
                'time:start': '2016 12 17 14:30',
                'time:end': '2016 12 17 15:00',
            }

            meet = core.formTufoByProp('ou:meet', '*', **props)

            self.eq(meet[1].get('ou:meet:name'), 'woot woot')
            self.eq(meet[1].get('ou:meet:time:start'), 1481985000000)
            self.eq(meet[1].get('ou:meet:time:end'), 1481986800000)
            self.eq(meet[1].get('ou:meet:place'), plac)

            iden = meet[1].get('ou:meet')

            props = {
                'arrive': '2016 12 17 14:33',
                'depart': '2016 12 17 15:13',
            }
            atnd = core.formTufoByProp('ou:meet:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:meet:attendee:meet'), iden)
            self.eq(atnd[1].get('ou:meet:attendee:person'), pers)
            self.eq(atnd[1].get('ou:meet:attendee:arrive'), 1481985180000)
            self.eq(atnd[1].get('ou:meet:attendee:depart'), 1481987580000)

            props = {
                'name': 'woot woot',
                'place': plac,
                'time:start': '2016 12 17 14:30',
                'time:end': '2016 12 17 15:00',
            }
            conf = core.formTufoByProp('ou:conference', '*', **props)

            iden = conf[1].get('ou:conference')

            self.eq(conf[1].get('ou:conference:name'), 'woot woot')
            self.eq(conf[1].get('ou:conference:place'), plac)
            self.eq(conf[1].get('ou:conference:time:start'), 1481985000000)
            self.eq(conf[1].get('ou:conference:time:end'), 1481986800000)

            props = {
                'arrive': '2016 12 17 14:33',
                'depart': '2016 12 17 15:13',
            }
            atnd = core.formTufoByProp('ou:conference:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:conference:attendee:conference'), iden)
            self.eq(atnd[1].get('ou:conference:attendee:person'), pers)
            self.eq(atnd[1].get('ou:conference:attendee:arrive'), 1481985180000)
            self.eq(atnd[1].get('ou:conference:attendee:depart'), 1481987580000)
