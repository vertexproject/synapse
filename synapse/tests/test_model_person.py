import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.common as s_test

class PsModelTest(s_test.SynTest):
    def test_ps_simple(self):

        person0 = s_common.guid()
        persona0 = s_common.guid()

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                node = snap.addNode('ps:tokn', ' BOB ')
                self.eq(node.ndef[1], 'bob')

                node = snap.addNode('ps:name', ' robert GREY  the\t3rd  ')
                self.eq(node.ndef[1], 'robert grey the 3rd')

                person_props = {
                    'dob': '1971',
                    'nick': 'pennywise',
                    'name': 'robert clown grey',
                    # 'img': ''  # fixme file:bytes
                    # 'guidname': '', # fixme guid aliases
                    'name:sur': 'grey',
                    'name:middle': 'clown',
                    'name:given': 'robert',
                    'name:en:sur': 'grey',
                    'name:en:middle': 'clown',
                    'name:en:given': 'robert',
                }
                node = snap.addNode('ps:person', person0, person_props)
                self.eq(node.ndef[1], person0)
                self.eq(node.get('dob'), 31536000000)
                self.eq(node.get('nick'), 'pennywise')
                self.eq(node.get('name'), 'robert clown grey')
                self.eq(node.get('name:sur'), 'grey')
                self.eq(node.get('name:middle'), 'clown')
                self.eq(node.get('name:given'), 'robert')
                self.eq(node.get('name:en:sur'), 'grey')
                self.eq(node.get('name:en:middle'), 'clown')
                self.eq(node.get('name:en:given'), 'robert')
                # self.eq(node.get('img'), '')  # fixme file:bytes
                # self.eq(node.get('guidname'), '')  # fixme guid aliases

                persona_props = {
                    'dob': '2000',
                    'nick': 'acid burn',
                    'name': 'Эммануэль брат Гольдштейн',
                    # 'img': ''  # fixme file:bytes
                    # 'guidname': '', # fixme guid aliases
                    'name:sur': 'Гольдштейн',
                    'name:middle': 'брат',
                    'name:given': 'эммануэль',
                    'name:en': 'emmanuel brother goldstein',
                    'name:en:sur': 'goldstein',
                    'name:en:middle': 'brother',
                    'name:en:given': 'emmanuel',
                }
                node = snap.addNode('ps:persona', persona0, persona_props)
                self.eq(node.ndef[1], persona0)
                self.eq(node.get('dob'), 946684800000)
                self.eq(node.get('nick'), 'acid burn')
                self.eq(node.get('name'), 'эммануэль брат гольдштейн')
                self.eq(node.get('name:sur'), 'гольдштейн')
                self.eq(node.get('name:middle'), 'брат')
                self.eq(node.get('name:given'), 'эммануэль')
                self.eq(node.get('name:en'), 'emmanuel brother goldstein')
                self.eq(node.get('name:en:sur'), 'goldstein')
                self.eq(node.get('name:en:middle'), 'brother')
                self.eq(node.get('name:en:given'), 'emmanuel')
                # self.eq(node.get('img'), '')  # fixme file:bytes
                # self.eq(node.get('guidname'), '')  # fixme guid aliases

                node = snap.addNode('ps:person:has', (person0, ('teststr', 'sewer map')))
                self.eq(node.ndef[1], (person0, ('teststr', 'sewer map')))
                self.eq(node.get('person'), person0)
                self.eq(node.get('node'), ('teststr', 'sewer map'))
                self.eq(node.get('node:form'), 'teststr')

                node = snap.addNode('ps:persona:has', (persona0, ('teststr', 'the gibson')))
                self.eq(node.ndef[1], (persona0, ('teststr', 'the gibson')))
                self.eq(node.get('persona'), persona0)
                self.eq(node.get('node'), ('teststr', 'the gibson'))
                self.eq(node.get('node:form'), 'teststr')

                org0 = s_common.guid()
                con0 = s_common.guid()
                cprops = {
                    'org': org0,
                    'asof': '20080414',
                    'person': person0,
                    'name': 'Tony  Stark',
                    'title': 'CEO',
                    'orgname': 'Stark Industries, INC',
                    # 'img': '',  # fixme file:bytes
                    'user': 'ironman',
                    'web:acct': ('twitter.com', 'ironman'),
                    'dob': '1976-12-17',
                    'url': 'https://starkindustries.com/',
                    'email': 'tony.stark@gmail.com',
                    'email:work': 'tstark@starkindustries.com',
                    'phone': '12345678910',
                    'phone:fax': '12345678910',
                    'phone:work': '12345678910',
                    'address': '1 Iron Suit Drive, San Francisco, CA, 22222, USA',
                }

                node = snap.addNode('ps:contact', con0, cprops)
                self.eq(node.ndef[1], con0)
                self.eq(node.get('org'), org0)
                self.eq(node.get('asof'), 1208131200000)
                self.eq(node.get('person'), person0)
                self.eq(node.get('name'), 'tony stark')
                self.eq(node.get('title'), 'ceo')
                self.eq(node.get('orgname'), 'stark industries, inc')
                self.eq(node.get('user'), 'ironman')
                self.eq(node.get('web:acct'), ('twitter.com', 'ironman'))
                self.eq(node.get('dob'), 219628800000)
                self.eq(node.get('url'), 'https://starkindustries.com/')
                self.eq(node.get('email'), 'tony.stark@gmail.com')
                self.eq(node.get('email:work'), 'tstark@starkindustries.com')
                self.eq(node.get('phone'), '12345678910')
                self.eq(node.get('phone:fax'), '12345678910')
                self.eq(node.get('phone:work'), '12345678910')
                self.eq(node.get('address'), '1 iron suit drive, san francisco, ca, 22222, usa')

class Fixme():

    def test_model_person(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('ps:person:guidname', 'person123', name='cool')
            person = node[1].get('ps:person')

            node = core.getTufoByProp('ps:person', person)
            self.eq(node[1].get('ps:person'), person)
            self.eq(node[1].get('ps:person:guidname'), 'person123')
            self.eq(node[1].get('ps:person:name'), 'cool')

    def test_model_persona(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('ps:persona:guidname', 'persona456', name='cool')
            persona = node[1].get('ps:persona')

            node = core.getTufoByProp('ps:persona', persona)
            self.eq(node[1].get('ps:persona'), persona)
            self.eq(node[1].get('ps:persona:guidname'), 'persona456')
            self.eq(node[1].get('ps:persona:name'), 'cool')
