import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types

from synapse.tests.common import *

class PersonTest(SynTest, ModelSeenMixin):

    def test_model_ps_has(self):
        with self.getRamCore() as core:
            person_guid = 32 * '0'
            person_tufo = core.formTufoByProp('ps:person', person_guid, name='Kenshoto,Invisigoth')
            personval = person_tufo[1].get('ps:person')

            node = core.formTufoByProp('ps:person:has', (personval, ('inet:fqdn', 'vertex.link')))
            self.ge(node[1].get('node:created'), 1519852535218)
            self.eq(node[1].get('ps:person:has'), '03870dc800bc21c7c594a900ae65f5cb')
            self.eq(node[1].get('ps:person:has:person'), personval)
            self.eq(node[1].get('ps:person:has:xref'), 'inet:fqdn=vertex.link')
            self.eq(node[1].get('ps:person:has:xref:prop'), 'inet:fqdn')
            self.eq(node[1].get('ps:person:has:xref:node'), '42366d896b947b97e7f3b1afeb9433a3')

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

            node = core.formTufoByProp('ps:person:guidname', 'person123', name='cool')
            person = node[1].get('ps:person')

            node = core.getTufoByProp('ps:person', person)
            self.eq(node[1].get('ps:person'), person)
            self.eq(node[1].get('ps:person:guidname'), 'person123')
            self.eq(node[1].get('ps:person:name'), 'cool')

    def test_model_persona(self):

        with self.getRamCore() as core:
            dob = core.getTypeParse('time', '19700101000000001')
            node = core.formTufoByProp('ps:persona', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth')
            self.eq(node[1].get('ps:persona:dob'), 1)
            self.eq(node[1].get('ps:persona:name'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:persona:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:persona:name:given'), 'invisigoth')
            self.none(node[1].get('ps:persona:name:middle'))

            node = core.formTufoByProp('ps:persona', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth,Ninja')
            self.eq(node[1].get('ps:persona:name'), 'kenshoto,invisigoth,ninja')
            self.eq(node[1].get('ps:persona:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:persona:name:given'), 'invisigoth')
            self.eq(node[1].get('ps:persona:name:middle'), 'ninja')

            node = core.formTufoByProp('ps:persona', guid(), dob=dob[0],
                                       name='Kenshoto,Invisigoth,Ninja,Gray')
            self.eq(node[1].get('ps:persona:name'), 'kenshoto,invisigoth,ninja,gray')
            self.eq(node[1].get('ps:persona:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:persona:name:given'), 'invisigoth')
            self.eq(node[1].get('ps:persona:name:middle'), 'ninja')

            node = core.formTufoByProp('ps:persona', guid(),
                                       **{'name': 'Гольдштейн, Эммануэль, брат',
                                          'name:en': 'Goldstein, Emmanuel, Brother',
                                          })
            self.eq(node[1].get('ps:persona:name'), 'гольдштейн,эммануэль,брат')
            self.eq(node[1].get('ps:persona:name:sur'), 'гольдштейн')
            self.eq(node[1].get('ps:persona:name:given'), 'эммануэль')
            self.eq(node[1].get('ps:persona:name:middle'), 'брат')
            self.eq(node[1].get('ps:persona:name:en'), 'goldstein,emmanuel,brother')
            self.eq(node[1].get('ps:persona:name:en:sur'), 'goldstein')
            self.eq(node[1].get('ps:persona:name:en:given'), 'emmanuel')
            self.eq(node[1].get('ps:persona:name:en:middle'), 'brother')

            node = core.formTufoByProp('ps:persona:guidname', 'persona456', name='cool')
            persona = node[1].get('ps:persona')

            node = core.getTufoByProp('ps:persona', persona)
            self.eq(node[1].get('ps:persona'), persona)
            self.eq(node[1].get('ps:persona:guidname'), 'persona456')
            self.eq(node[1].get('ps:persona:name'), 'cool')

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
        FORMS = ('ps:hasuser', 'ps:hashost', 'ps:hasalias', 'ps:hasphone', 'ps:hasemail', 'ps:haswebacct')
        NODECOUNT = N * len(FORMS)
        TAGS = ['hehe', 'hehe.hoho']

        def _check_no_old_data_remains(core, oldname):
            tufos = core.getTufosByProp(oldname)
            self.len(0, tufos)
            rows = core.getJoinByProp(oldname)
            self.len(0, rows)

        def _check_tags(core, tufo, tags):
            self.sorteq(tags, s_tufo.tags(tufo))

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
            self.true(any([p == '_:dark:syn:modl:rev' and v == 'ps:201802281621' for (i, p, v, t) in dark_rows]))

        def run_assertions(core, oldname, reftype, tufo_check):
            # assert that the correct number of items was migrated
            tufos = core.getTufosByProp('ps:person:has:xref:prop', reftype)
            self.len(N, tufos)

            # check that properties were correctly migrated and tags were not damaged
            tufo = tufo_check(core)

            # check that tags were correctly migrated
            _check_tags(core, tufo, TAGS)
            _check_tagforms(core, oldname, 'ps:person:has')
            _check_tagdarks(core, oldname, 'ps:person:has', NODECOUNT)
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

        for i in range(N):
            user = 'inet:user%d' % i
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

        hostcompguids = ['05a67fe71d3f2ad5e7c9db1aa0eabb35', '0b579d971767ad8391baed2382bef53e']
        for i in range(N):
            host = 32 * str(i)
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ps:hashost', tick),
                (iden, 'ps:hashost:host', host, tick),
                (iden, 'ps:hashost:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:hashost', hostcompguids[i], tick),
                (iden, 'ps:hashost:seen:min', 0, tick),
                (iden, 'ps:hashost:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:hashost#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:hashost#hehe', tick, tick),
            ])

        for i in range(N):
            alias = 'ps:name%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ps:hasalias', tick),
                (iden, 'ps:hasalias:alias', alias, tick),
                (iden, 'ps:hasalias:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:hasalias', '2f6d1248de48f451e1f349cff33f336c/' + alias, tick),
                (iden, 'ps:hasalias:seen:min', 0, tick),
                (iden, 'ps:hasalias:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:hasalias#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:hasalias#hehe', tick, tick),
            ])

        for i in range(N):
            phone = (123456789 * 10) + i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ps:hasphone', tick),
                (iden, 'ps:hasphone:phone', phone, tick),
                (iden, 'ps:hasphone:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:hasphone', '2f6d1248de48f451e1f349cff33f336c/' + str(phone), tick),
                (iden, 'ps:hasphone:seen:min', 0, tick),
                (iden, 'ps:hasphone:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:hasphone#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:hasphone#hehe', tick, tick),
            ])

        for i in range(N):
            email = 'email%d@vertex.link' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ps:hasemail', tick),
                (iden, 'ps:hasemail:email', email, tick),
                (iden, 'ps:hasemail:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:hasemail', '2f6d1248de48f451e1f349cff33f336c/' + email, tick),
                (iden, 'ps:hasemail:seen:min', 0, tick),
                (iden, 'ps:hasemail:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:hasemail#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:hasemail#hehe', tick, tick),
            ])

        for i in range(N):
            acct = 'vertex.link/user%d' % i
            iden = guid()
            dark_iden = iden[::-1]
            tick = now()
            adds.extend([
                (iden, 'tufo:form', 'ps:haswebacct', tick),
                (iden, 'ps:haswebacct:web:acct', acct, tick),
                (iden, 'ps:haswebacct:person', '2f6d1248de48f451e1f349cff33f336c', tick),
                (iden, 'ps:haswebacct', '2f6d1248de48f451e1f349cff33f336c/' + acct, tick),
                (iden, 'ps:haswebacct:seen:min', 0, tick),
                (iden, 'ps:haswebacct:seen:max', 1, tick),
                (iden, '#hehe.hoho', tick, tick),
                (iden, '#hehe', tick, tick),
                (dark_iden, '_:*ps:haswebacct#hehe.hoho', tick, tick),
                (dark_iden, '_:*ps:haswebacct#hehe', tick, tick),
            ])

        for form in FORMS:
            adds.extend(_addTag('hehe.hoho', form))
            adds.extend(_addTag('hehe', form))

        # Spin up a core with the old rows, then run the migration and check the results
        with s_cortex.openstore('ram:///') as stor:
            stor.setModlVers('ps', 0)
            def addrows(mesg):
                stor.addRows(adds)
            stor.on('modl:vers:rev', addrows, name='ps', vers=201802281621)

            with s_cortex.fromstore(stor) as core:

                # ps:hasuser ======================================================================
                oldname = 'ps:hasuser'
                reftype = 'inet:user'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'inet:user=inet:user0')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], '1d69ccd1948c985d9467fb4d3caab4f1')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'inet:user=inet:user0')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], 'bec8693bb5b38ffe62b97b0d2b7cdbb5')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, 'inet:user0')
                    userfo = core.getTufoByProp('node:ndef', 'bec8693bb5b38ffe62b97b0d2b7cdbb5')
                    self.eq(userfo[1].get(reftype), 'inet:user0')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ps:hashost ======================================================================
                oldname = 'ps:hashost'
                reftype = 'it:host'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'it:host=00000000000000000000000000000000')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], '4b4e7d417c84e75fbd30332bde6d9614')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'it:host=00000000000000000000000000000000')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], '09cd1fbc8b183f18c38ae034713af5e3')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, 32 * '0')
                    userfo = core.getTufoByProp('node:ndef', '09cd1fbc8b183f18c38ae034713af5e3')
                    self.eq(userfo[1].get(reftype), 32 * '0')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ps:hasalias =====================================================================
                oldname = 'ps:hasalias'
                reftype = 'ps:name'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'ps:name=ps:name0')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], '5225cebcede28ca91fae6d9dcf0442f0')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'ps:name=ps:name0')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], '06359585e4d66e7ab081aaafdedabe39')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, 'ps:name0')
                    namefo = core.getTufoByProp('node:ndef', '06359585e4d66e7ab081aaafdedabe39')
                    self.eq(namefo[1].get(reftype), 'ps:name0')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ps:hasphone =====================================================================
                oldname = 'ps:hasphone'
                reftype = 'tel:phone'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'tel:phone=+1 (234) 567-890')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], 'e7cdfaba2a1cb739bdf5afd56795dbd3')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'tel:phone=+1 (234) 567-890')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], '0068a540030a8de1d3f3817e52d50b7c')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, '1234567890')
                    phonefo = core.getTufoByProp('node:ndef', '0068a540030a8de1d3f3817e52d50b7c')
                    self.eq(phonefo[1].get(reftype), 1234567890)

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ps:hasemail =====================================================================
                oldname = 'ps:hasemail'
                reftype = 'inet:email'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'inet:email=email0@vertex.link')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], 'f1459cf885d792f2a98ae89d36ee9227')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'inet:email=email0@vertex.link')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], '79249f2582baef41cbed45f609e2ea89')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, 'email0@vertex.link')
                    namefo = core.getTufoByProp('node:ndef', '79249f2582baef41cbed45f609e2ea89')
                    self.eq(namefo[1].get(reftype), 'email0@vertex.link')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)

                # ps:haswebacct ===================================================================
                oldname = 'ps:haswebacct'
                reftype = 'inet:web:acct'
                def tufo_check(core):
                    tufo = core.getTufoByProp('ps:person:has:xref', 'inet:web:acct=vertex.link/user0')
                    self.eq(tufo[1]['tufo:form'], 'ps:person:has')
                    self.eq(tufo[1]['ps:person:has'], '9f2179b7a428d4ca233b96acd9b0c8fc')
                    self.eq(tufo[1]['ps:person:has:seen:min'], 0)
                    self.eq(tufo[1]['ps:person:has:seen:max'], 1)
                    self.eq(tufo[1]['ps:person:has:xref'], 'inet:web:acct=vertex.link/user0')
                    self.eq(tufo[1]['ps:person:has:xref:prop'], reftype)
                    self.eq(tufo[1]['ps:person:has:xref:node'], '0cd705305c7f4573a38b7e7c8f4ddef9')
                    self.eq(tufo[1]['ps:person:has:person'], '2f6d1248de48f451e1f349cff33f336c')

                    # Demonstrate that node:ndef works (We have to form this node as adding the xref will not)
                    core.formTufoByProp(reftype, 'vertex.link/user0')
                    namefo = core.getTufoByProp('node:ndef', '0cd705305c7f4573a38b7e7c8f4ddef9')
                    self.eq(namefo[1].get(reftype), 'vertex.link/user0')

                    return tufo
                run_assertions(core, oldname, reftype, tufo_check)
