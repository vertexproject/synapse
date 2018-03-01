import synapse.lib.tufo as s_tufo
from synapse.lib.types import DataType

import synapse.lib.module as s_module

# FIXME identify/handle possibly as seeds
# tony stark
# tony logan stark
# stark,tony logan
# stark,tony l.

class Name(DataType):
    subprops = (
        ('sur', {'ptype': 'ps:tokn'}),
        ('given', {'ptype': 'ps:tokn'}),
        ('middle', {'ptype': 'ps:tokn'}),
        ('parts', {'ptype': 'int', 'doc': 'Number of ps:tokn elements in ps:name'}),
    )

    def norm(self, valu, oldval=None):
        subs = {}

        valu = valu.lower().strip()
        if not valu:
            self._raiseBadValu(valu)

        parts = [v.strip().strip('.').lower() for v in valu.split(',')]
        if len(parts) >= 2:
            subs['sur'] = parts[0]
            subs['given'] = parts[1]
            if len(parts) >= 3:
                subs['middle'] = parts[2]

        subs['parts'] = len(parts)
        valu = ','.join(parts)
        return valu, subs

class PsMod(s_module.CoreModule):

    def initCoreModule(self):
        self.core.addSeedCtor('ps:person:guidname', self.seedPersonGuidName)

    def seedPersonGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:person:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:person', None, guidname=valu, **props)
        return node

    @modelrev('ps', 201802281621)
    def _revModl201802281621(self):
        '''
        Combine ps:has* into ps:has
        - Forms a new ps:has node for all of the old ps:has* nodes
        - Applies the old node's tags to the new node
        - Deletes the old node
        - Deletes the syn:tagform nodes for the old form
        - FIXME do we need to do anything with dark rows?
        '''
        data = (
            ('ps:hasuser', 'user', 'inet:user'),
            ('ps:hashost', 'host', 'it:host'),
            ('ps:hasalias', 'alias', 'ps:name'),
            ('ps:hasphone', 'phone', 'tel:phone'),
            ('ps:hasemail', 'email', 'inet:email'),
            ('ps:haswebacct', 'web:acct', 'inet:web:acct'),
        )
        with self.core.getCoreXact() as xact:

            for oldform, pname, ptype in data:
                personkey = oldform + ':person'
                newvalkey = oldform + ':' + pname

                for tufo in self.core.getTufosByProp(oldform):
                    perval = tufo[1].get(personkey)
                    newval = tufo[1].get(newvalkey)
                    newfo = self.core.formTufoByProp('ps:has', (perval, (ptype, newval)))

                    tags = s_tufo.tags(tufo, leaf=True)
                    self.core.addTufoTags(newfo, tags)

                    self.core.delTufo(tufo)

                self.core.delTufosByProp('syn:tagform:form', oldform)

            # Add dark rows to the ps:has
            # It is safe to operate on all ps:has nodes as this point as none should exist
            dvalu = 'ps:201802281621'
            dprop = '_:dark:syn:modl:rev'
            darks = [(i[::-1], dprop, dvalu, t) for (i, p, v, t) in self.core.getRowsByProp('ps:has')]
            self.core.addRows(darks)

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (

                ('ps:tokn',
                 {'subof': 'str:lwr', 'doc': 'A single name element (potentially given or sur)', 'ex': 'mike'}),
                ('ps:name',
                 {'ctor': 'synapse.models.person.Name', 'ex': 'smith,bob', 'doc': 'A last,first person full name'}),
                ('ps:person',
                 {'subof': 'guid', 'alias': 'ps:person:guidname', 'doc': 'A GUID for a person or suspected person'}),

                ('ps:contact', {'subof': 'guid', 'doc': 'A GUID for a contact info record'}),

                ('ps:hashost', {'subof': 'comp', 'fields': 'person=ps:person,host=it:host'}),
                ('ps:hasalias', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|alias,ps:name'}),
                ('ps:hasphone', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|phone,tel:phone'}),
                ('ps:hasemail', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|email,inet:email'}),
                ('ps:haswebacct', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|web:acct,inet:web:acct'}),

                ('ps:has', {
                    'subof': 'xref',
                    'source': 'person,ps:person',
                    'doc': 'A person that has a thing. FIXME reword'}),

                ('ps:image', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|file,file:bytes'}),

                # FIXME add wireless elemements like NMEI and IMEI once modeled
            ),

            'forms': (

                ('ps:tokn', {'ptype': 'ps:tokn'}, []),

                ('ps:name', {'ptype': 'ps:name'}, [
                    ('sur', {'ptype': 'ps:tokn', 'doc': 'The "surname" part of ps:name', 'ex': 'stark'}),
                    ('given', {'ptype': 'ps:tokn', 'doc': 'The "given name" part of ps:name', 'ex': 'tony'}),
                    ('middle', {'ptype': 'ps:tokn', 'doc': 'The "middle name" part of ps:name', 'ex': 'alex'}),
                ]),

                ('ps:person', {'ptype': 'ps:person'}, [
                    ('guidname', {'ptype': 'str:lwr', 'doc': 'The GUID resolver alias for this person'}),
                    ('dob', {'ptype': 'time', 'doc': 'The Date of Birth (DOB) if known'}),
                    ('img', {'ptype': 'file:bytes', 'doc': 'The "primary" image of a person'}),
                    ('nick', {'ptype': 'inet:user'}),
                    ('name', {'ptype': 'ps:name',
                        'doc': 'The localized name for the person'}),
                    ('name:sur', {'ptype': 'ps:tokn', }),
                    ('name:middle', {'ptype': 'ps:tokn'}),
                    ('name:given', {'ptype': 'ps:tokn'}),
                    ('name:en', {'ptype': 'ps:name',
                        'doc': 'The English version of the name for the person'}),
                    ('name:en:sur', {'ptype': 'ps:tokn'}),
                    ('name:en:middle', {'ptype': 'ps:tokn'}),
                    ('name:en:given', {'ptype': 'ps:tokn'}),
                ]),

                ('ps:contact', {'ptype': 'guid', 'doc': 'A collection of contact information in a single record'}, [

                    ('org', {'ptype': 'ou:org', 'doc': 'The ou:org GUID which owns this contact'}),
                    ('asof', {'ptype': 'time', 'doc': 'The time this contact was created or modified'}),
                    ('person', {'ptype': 'ps:person', 'doc': 'The ps:person GUID which owns this contact'}),

                    ('name', {'ptype': 'ps:name', 'doc': 'The person name listed for the contact'}),
                    ('title', {'ptype': 'str:lwr', 'doc': 'The job/org title listed for this contact'}),
                    ('photo', {'ptype': 'file:bytes', 'doc': 'The photo listed for this contact'}),

                    ('orgname', {'ptype': 'str:lwr', 'doc': 'The listed org/company name for this contact'}),

                    ('user', {'ptype': 'inet:user', 'doc': 'The username or handle for the contact'}),

                    ('web:acct', {'ptype': 'inet:web:acct', 'doc': 'The social media account for this contact'}),

                    ('dob', {'ptype': 'time', 'doc': 'The Date of Birth (DOB) for the contact'}),

                    ('url', {'ptype': 'inet:url', 'doc': 'The home/main site for this contact'}),

                    ('email', {'ptype': 'inet:email', 'doc': 'The main email address for this contact'}),
                    ('email:work', {'ptype': 'inet:email', 'doc': 'The contact work email address'}),

                    ('address', {'ptype': 'str:lwr', 'doc': 'The free-form address listed for the contact'}),

                    ('phone', {'ptype': 'tel:phone', 'doc': 'The "main" phone number for this contact'}),

                    # TODO: figure out a reasonable way to do multi-valu fields?
                    ('phone:fax', {'ptype': 'tel:phone', 'doc': 'The contact fax phone number'}),
                    ('phone:work', {'ptype': 'tel:phone', 'doc': 'The contact work phone number'}),
                ]),

                ('ps:image', {}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('file', {'ptype': 'file:bytes'}),
                    # FIXME add an optional bounding box
                )),

                ('ps:hasalias', {'ptype': 'ps:hasalias'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('alias', {'ptype': 'ps:name'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),

                ('ps:hashost', {'ptype': 'ps:hashost'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('host', {'ptype': 'it:host'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),

                ('ps:hasphone', {'ptype': 'ps:hasphone'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('phone', {'ptype': 'tel:phone'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),

                ('ps:hasemail', {'ptype': 'ps:hasemail'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('email', {'ptype': 'inet:email'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),

                ('ps:haswebacct', {'ptype': 'ps:haswebacct'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('web:acct', {'ptype': 'inet:web:acct'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),

                ('ps:has', {}, [
                    ('person', {'ptype': 'ps:person', 'ro': 1, 'req': 1,
                        'doc': 'The person that has the given node.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The prop=valu that is referenced as part of the FIXME.'}),
                    ('xref:node', {'ptype': 'ndef', 'ro': 1, 'req': 1,
                        'doc': 'FIXME.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the referenced object, as specified by the propvalu.'}),
                    ('xref:intval', {'ptype': 'int', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is an integer.'}),
                    ('xref:strval', {'ptype': 'str', 'ro': 1,
                        'doc': 'The normed value of the form that was referenced, if the value is a string.'}),
                ]),

            ),
        }
        name = 'ps'
        return ((name, modl), )
