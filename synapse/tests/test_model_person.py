from synapse.tests.common import *

class PersonTest(SynTest):

    def _check_seen(self, core, node):
        form = node[1]['tufo:form']
        minp = form + ':seen:min'
        maxp = form + ':seen:max'

        self.none(node[1].get(minp))
        self.none(node[1].get(maxp))

        core.setTufoProps(node, **{'seen:min': 100, 'seen:max': 100})
        self.eq(node[1].get(minp), 100)
        self.eq(node[1].get(maxp), 100)

        core.setTufoProps(node, **{'seen:min': 0, 'seen:max': 0})
        self.eq(node[1].get(minp), 0)
        self.eq(node[1].get(maxp), 100)

        core.setTufoProps(node, **{'seen:min': 1000, 'seen:max': 1000})
        self.eq(node[1].get(minp), 0)
        self.eq(node[1].get(maxp), 1000)

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

    def test_model_person_has_user(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasuser', '%s/visi' % iden)

            self.eq(node[1].get('ps:hasuser:user'), 'visi')
            self.eq(node[1].get('ps:hasuser:person'), iden)
            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))

            self._check_seen(core, node)

    def test_model_person_has_alias(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasalias', '%s/Kenshoto,Invisigoth' % iden)

            self.eq(node[1].get('ps:hasalias:alias'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:hasalias:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('ps:name', 'kenshoto,invisigoth'))

            self._check_seen(core, node)

    def test_model_person_has_phone(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasphone', '%s/17035551212' % iden)

            self.eq(node[1].get('ps:hasphone:phone'), 17035551212)
            self.eq(node[1].get('ps:hasphone:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('tel:phone', 17035551212))

            self._check_seen(core, node)

    def test_model_person_has_email(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasemail', '%s/visi@VERTEX.link' % iden)

            self.eq(node[1].get('ps:hasemail:email'), 'visi@vertex.link')
            self.eq(node[1].get('ps:hasemail:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))

            self._check_seen(core, node)

    def test_model_person_has_webacct(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:haswebacct', '%s/ROOTKIT.com/visi' % iden)

            self.eq(node[1].get('ps:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ps:haswebacct:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/visi'))

            self._check_seen(core, node)

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
