from synapse.lib.types import DataType

from synapse.lib.module import CoreModule, modelrev

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

class PsMod(CoreModule):

    def initCoreModule(self):
        self.core.addSeedCtor('ps:person:guidname', self.seedPersonGuidName)

    def seedPersonGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:person:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:person', None, guidname=valu, **props)
        return node

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

                ('ps:hasuser', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|user,inet:user'}),
                ('ps:hashost', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|host,it:host'}),
                ('ps:hasalias', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|alias,ps:name'}),
                ('ps:hasphone', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|phone,tel:phone'}),
                ('ps:hasemail', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|email,inet:email'}),
                ('ps:haswebacct', {'subof': 'sepr', 'sep': '/', 'fields': 'person,ps:person|web:acct,inet:web:acct'}),

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

                ('ps:hasuser', {'ptype': 'ps:hasuser'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('user', {'ptype': 'inet:user'}),
                )),

                ('ps:hasalias', {'ptype': 'ps:hasalias'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('alias', {'ptype': 'ps:name'}),
                )),

                ('ps:hasphone', {'ptype': 'ps:hasphone'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('phone', {'ptype': 'tel:phone'}),
                )),

                ('ps:hasemail', {'ptype': 'ps:hasemail'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('email', {'ptype': 'inet:email'}),
                )),

                ('ps:haswebacct', {'ptype': 'ps:haswebacct'}, (
                    ('person', {'ptype': 'ps:person'}),
                    ('web:acct', {'ptype': 'inet:web:acct'}),
                )),
            ),
        }
        name = 'ps'
        return ((name, modl), )
