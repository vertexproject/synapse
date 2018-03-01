import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types

from synapse.tests.common import *

class PersonTest(SynTest, ModelSeenMixin):

    def test_model_ps_has(self):
        with self.getRamCore() as core:
            person_guid = 32 * '0'
            person_tufo = core.formTufoByProp('ps:person', person_guid, name='Kenshoto,Invisigoth')
            personval = person_tufo[1].get('ps:person')

            node = core.formTufoByProp('ps:has', (personval, ('inet:fqdn', 'vertex.link')))
            self.ge(node[1].get('node:created'), 1519852535218)
            self.eq(node[1].get('ps:has'), '03870dc800bc21c7c594a900ae65f5cb')
            self.eq(node[1].get('ps:has:person'), personval)
            self.eq(node[1].get('ps:has:xref'), 'inet:fqdn=vertex.link')
            self.eq(node[1].get('ps:has:xref:prop'), 'inet:fqdn')
            self.eq(node[1].get('ps:has:xref:node'), '42366d896b947b97e7f3b1afeb9433a3')

            self.none(core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3'))  # Not automatically formed
            core.formTufoByProp('inet:fqdn', 'vertex.link')
            fqdnfo = core.getTufoByProp('node:ndef', '42366d896b947b97e7f3b1afeb9433a3')
            self.eq(fqdnfo[1].get('inet:fqdn'), 'vertex.link')

    def test_model_person(self):

        with self.getRamCore() as core:
            dob = core.getTypeParse('time', '19700101000000001')
            node = core.formTufoByProp('ps:person', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth')
            self.eq(node[1].get('ps:person:dob'), 1)
            self.eq(node[1].get('ps:person:name'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:person:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:person:name:given'), 'invisigoth')
            self.none(node[1].get('ps:person:name:middle'))

            node = core.formTufoByProp('ps:person', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth,Ninja')
            self.eq(node[1].get('ps:person:name'), 'kenshoto,invisigoth,ninja')
            self.eq(node[1].get('ps:person:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:person:name:given'), 'invisigoth')
            self.eq(node[1].get('ps:person:name:middle'), 'ninja')

            node = core.formTufoByProp('ps:person', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth,Ninja,Gray')
            self.eq(node[1].get('ps:person:name'), 'kenshoto,invisigoth,ninja,gray')
            self.eq(node[1].get('ps:person:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:person:name:given'), 'invisigoth')
            self.eq(node[1].get('ps:person:name:middle'), 'ninja')

            node = core.formTufoByProp('ps:person', guid(),
                                       **{'name': 'Гольдштейн, Эммануэль, брат',
                                          'name:en': 'Goldstein, Emmanuel, Brother',
                                          })
            self.eq(node[1].get('ps:person:name'), 'гольдштейн,эммануэль,брат')
            self.eq(node[1].get('ps:person:name:sur'), 'гольдштейн')
            self.eq(node[1].get('ps:person:name:given'), 'эммануэль')
            self.eq(node[1].get('ps:person:name:middle'), 'брат')
            self.eq(node[1].get('ps:person:name:en'), 'goldstein,emmanuel,brother')
            self.eq(node[1].get('ps:person:name:en:sur'), 'goldstein')
            self.eq(node[1].get('ps:person:name:en:given'), 'emmanuel')
            self.eq(node[1].get('ps:person:name:en:middle'), 'brother')

    def test_model_person_tokn(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('ps:tokn', 'Invisigoth')
            self.eq(node[1].get('ps:tokn'), 'invisigoth')

    def test_model_person_name(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('ps:name', 'Kenshoto,Invisigoth')

            self.eq(node[1].get('ps:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:name:given'), 'invisigoth')

            self.nn(core.getTufoByProp('ps:tokn', 'kenshoto'))
            self.nn(core.getTufoByProp('ps:tokn', 'invisigoth'))

    def test_model_person_2(self):

        with self.getRamCore() as core:
            node = core.formTufoByProp('ps:name', 'Kenshoto,Invisigoth')

            self.eq(node[1].get('ps:name'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:name:given'), 'invisigoth')

            self.nn(core.getTufoByProp('ps:tokn', 'kenshoto'))
            self.nn(core.getTufoByProp('ps:tokn', 'invisigoth'))

    def test_model_person_has_alias(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasalias', '%s/Kenshoto,Invisigoth' % iden)

            self.eq(node[1].get('ps:hasalias:alias'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:hasalias:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('ps:name', 'kenshoto,invisigoth'))

            self.check_seen(core, node)

    def test_model_person_has_host(self):
        with self.getRamCore() as core:
            pval = 32 * 'a'
            hval = 32 * 'b'

            node = core.formTufoByProp('ps:hashost', (pval, hval))

            self.eq(node[1]['ps:hashost'], '20ffcd864aeb7f4f6e23d95680eeed47')
            self.eq(node[1].get('ps:hashost:host'), hval)
            self.eq(node[1].get('ps:hashost:person'), pval)

            self.nn(core.getTufoByProp('ps:person', pval))
            self.nn(core.getTufoByProp('it:host', hval))

            self.check_seen(core, node)

    def test_model_person_has_email(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasemail', '%s/visi@VERTEX.link' % iden)

            self.eq(node[1].get('ps:hasemail:email'), 'visi@vertex.link')
            self.eq(node[1].get('ps:hasemail:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))

            self.check_seen(core, node)

    def test_model_person_has_phone(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasphone', '%s/17035551212' % iden)

            self.eq(node[1].get('ps:hasphone:phone'), 17035551212)
            self.eq(node[1].get('ps:hasphone:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('tel:phone', 17035551212))

            self.check_seen(core, node)

    def test_model_person_has_webacct(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:haswebacct', '%s/ROOTKIT.com/visi' % iden)

            self.eq(node[1].get('ps:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ps:haswebacct:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/visi'))

            self.check_seen(core, node)

    def test_model_person_guidname(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('ps:person:guidname', 'visi')
            self.eq(node[1].get('ps:person:guidname'), 'visi')

            iden = node[1].get('ps:person')

            node = core.formTufoByProp('ps:haswebacct', '$visi/rootkit.com/visi')

            self.eq(node[1].get('ps:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ps:haswebacct:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))

            self.eq(len(core.eval('ps:person=$visi')), 1)

    def test_model_person_contact(self):

        with self.getRamCore() as core:

            info = {
                'org': '*',
                'person': '*',

                'name': 'Stark,Tony',

                'title': 'CEO',
                'orgname': 'Stark Industries, INC',

                'user': 'ironman',
                'web:acct': 'twitter.com/ironman',

                'dob': '1976-12-17',
                'url': 'https://starkindustries.com/',

                'email': 'tony.stark@gmail.com',
                'email:work': 'tstark@starkindustries.com',

                'phone': '12345678910',
                'phone:fax': '12345678910',
                'phone:work': '12345678910',

                'address': '1 Iron Suit Drive, San Francisco, CA, 22222, USA',
            }

            node = core.formTufoByProp('ps:contact', info)

            self.nn(core.getTufoByProp('ou:org', node[1].get('ps:contact:org')))
            self.nn(core.getTufoByProp('ps:person', node[1].get('ps:contact:person')))
            self.nn(core.getTufoByProp('inet:url', node[1].get('ps:contact:url')))
            self.nn(core.getTufoByProp('inet:user', node[1].get('ps:contact:user')))
            self.nn(core.getTufoByProp('inet:email', node[1].get('ps:contact:email')))
            self.nn(core.getTufoByProp('inet:email', node[1].get('ps:contact:email:work')))
            self.nn(core.getTufoByProp('inet:web:acct', node[1].get('ps:contact:web:acct')))
            self.nn(core.getTufoByProp('tel:phone', node[1].get('ps:contact:phone')))
            self.nn(core.getTufoByProp('tel:phone', node[1].get('ps:contact:phone:fax')))
            self.nn(core.getTufoByProp('tel:phone', node[1].get('ps:contact:phone:work')))

            self.eq(node[1].get('ps:contact:address'), '1 iron suit drive, san francisco, ca, 22222, usa')

    def test_model_ps_201802281621(self):
        N = 2
        FORMS = ('ps:hasuser', )
        NODECOUNT = N * len(FORMS)
        TAGS = ['hehe', 'hehe.hoho']

        def _check_no_old_data_remains(core, oldname):
            tufos = core.getTufosByProp(oldname)
            self.len(0, tufos)
            rows = core.getJoinByProp(oldname)
            self.len(0, rows)

        def _check_tags(core, tufo, tags):
            self.eq(sorted(tags), sorted(s_tufo.tags(tufo)))

        def _check_tagforms(core, oldname, newname, count):
            self.len(0, core.getRowsByProp('syn:tagform:form', oldname))
            self.len(0, core.getJoinByProp(oldname))
            self.len(count, core.getRowsByProp('syn:tagform:form', newname))

        def _check_tagdarks(core, oldname, newname, count):
            self.len(0, core.getRowsByProp('_:*' + oldname + '#hehe.hoho'))
            self.len(0, core.getRowsByProp('_:*' + oldname + '#hehe'))
            self.len(count, core.getRowsByProp('_:*' + newname + '#hehe.hoho'))
            self.len(count, core.getRowsByProp('_:*' + newname + '#hehe'))

        def _check_darkmodlrev(core, tufo):
            dark_rows = core.getRowsById(tufo[0][::-1])
            self.true(any([p == '_:dark:syn:modl:rev' and v == 'ps:201802281621' for (i, p, v, t) in dark_rows]))

        def run_assertions(core, oldname, reftype, tufo_check):
            # assert that the correct number of items was migrated
            tufos = core.getTufosByProp('ps:has:xref:prop', 'inet:user')
            self.len(N, tufos)

            # check that properties were correctly migrated and tags were not damaged
            tufo = tufo_check(core)

            # check that tags were correctly migrated
            _check_tags(core, tufo, TAGS)
            _check_tagforms(core, oldname, 'ps:has', NODECOUNT)
            _check_tagdarks(core, oldname, 'ps:has', NODECOUNT)
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
        for form in FORMS:
            adds.extend(_addTag('hehe.hoho', form))
            adds.extend(_addTag('hehe', form))

        for i in range(N):
            user = 'pennywise%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()

            adds.extend([
                (iden, 'tufo:form', 'ps:hasuser', tick),
                (iden, 'ps:hasuser:user', user, tick),
                (iden, 'ps:hasuser:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:hasuser', '2f6d1248de48f451e1f349cff33f336c/' + user, tick),
                (iden, 'ps:hasuser:seen:min', 0, tick),
                (iden, 'ps:hasuser:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:hasuser#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:hasuser#hehe', tick, tick),
            ])

        # Spin up a core with the old rows, then run the migration and check the results
        with s_cortex.openstore('ram:///') as stor:
            stor.setModlVers('ps', 0)
            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='ps', vers=201802281621)

            with s_cortex.fromstore(stor) as core:
                # FIXME seen/min/max. hashost is a comp

                # ps:hasuser ======================================================================
                oldname = 'ps:hasuser'
                reftype = 'inet:user'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:has:xref', 'inet:user=pennywise0')
                    self.eq(tufo[1]['tufo:form'], 'ps:has')
                    self.eq(tufo[1]['ps:has'], 'f8cb39f7e4d8f1b82a5263c14655df68')
                    self.eq(tufo[1]['ps:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:has:xref'], 'inet:user=pennywise0')
                    self.eq(tufo[1]['ps:has:xref:prop'], 'inet:user')
                    self.eq(tufo[1]['ps:has:xref:node'], '707d5a722ceaa4101d19d7ce3b1a60bb')
                    self.eq(tufo[1]['ps:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp('inet:user', 'pennywise0')
                    userfo = core.getTufoByProp('node:ndef', '707d5a722ceaa4101d19d7ce3b1a60bb')
                    self.eq(userfo[1].get('inet:user'), 'pennywise0')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ps:hashost ======================================================================
                oldname = 'ps:hashost'
                reftype = 'it:host'
                tufo_check = None  # FIXME
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ps:hasalias =====================================================================
                oldname = 'ps:hasalias'
                reftype = 'ps:name'
                tufo_check = None  # FIXME
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ps:hasphone =====================================================================
                oldname = 'ps:hasphone'
                reftype = 'tel:phone'
                tufo_check = None  # FIXME
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ps:hasemail =====================================================================
                oldname = 'ps:hasemail'
                reftype = 'inet:email'
                tufo_check = None  # FIXME
                run_assertions(core, oldname, reftype, tufo_check)
                return

                # ps:haswebacct ===================================================================
                oldname = 'ps:haswebacct'
                reftype = 'inet:web:acct'
                tufo_check = None  # FIXME
                run_assertions(core, oldname, reftype, tufo_check)
                return
