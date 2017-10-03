
from synapse.tests.common import *

class PersonTest(SynTest):

    def test_model_person(self):

        with self.getRamCore() as core:
            dob = core.getTypeParse('time', '19700101000000001')
            node = core.formTufoByProp('ps:person', guid(), dob=dob[0], name='Kenshoto,Invisigoth')
            self.eq(node[1].get('ps:person:dob'), 1)
            self.eq(node[1].get('ps:person:name'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:person:name:sur'), 'kenshoto')
            self.eq(node[1].get('ps:person:name:given'), 'invisigoth')

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

    def test_model_person_has_alias(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasalias', '%s/Kenshoto,Invisigoth' % iden)

            self.eq(node[1].get('ps:hasalias:alias'), 'kenshoto,invisigoth')
            self.eq(node[1].get('ps:hasalias:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('ps:name', 'kenshoto,invisigoth'))

    def test_model_person_has_phone(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasphone', '%s/17035551212' % iden)

            self.eq(node[1].get('ps:hasphone:phone'), 17035551212)
            self.eq(node[1].get('ps:hasphone:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('tel:phone', 17035551212))

    def test_model_person_has_email(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:hasemail', '%s/visi@VERTEX.link' % iden)

            self.eq(node[1].get('ps:hasemail:email'), 'visi@vertex.link')
            self.eq(node[1].get('ps:hasemail:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))

    def test_model_person_has_webacct(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ps:haswebacct', '%s/ROOTKIT.com/visi' % iden)

            self.eq(node[1].get('ps:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ps:haswebacct:person'), iden)

            self.nn(core.getTufoByProp('ps:person', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/visi'))

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
