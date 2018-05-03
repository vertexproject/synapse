import synapse.lib.types as s_types

import unittest
raise unittest.SkipTest()

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
