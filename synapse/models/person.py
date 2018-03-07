import synapse.lib.tufo as s_tufo
import synapse.lib.module as s_module
from synapse.lib.types import DataType

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
        self.core.addSeedCtor('ps:persona:guidname', self.seedPersonaGuidName)

    def seedPersonGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:person:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:person', None, guidname=valu, **props)
        return node

    def seedPersonaGuidName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ps:persona:guidname', valu)
        if node is None:
            # trigger GUID auto-creation
            node = self.core.formTufoByProp('ps:persona', None, guidname=valu, **props)
        return node

    @s_module.modelrev('ps', 201802281621)
    def _revModl201802281621(self):
        '''
        Combine ps:has* into ps:person:has
        - Forms a new ps:person:has node for all of the old ps:has* nodes
        - Applies the old node's tags to the new node
        - Deletes the old node
        - Deletes the syn:tagform nodes for the old form
        - Adds dark row for each node, signifying that they were added by migration
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
                sminkey = oldform + ':seen:min'
                smaxkey = oldform + ':seen:max'

                for tufo in self.core.getTufosByProp(oldform):
                    perval = tufo[1].get(personkey)
                    newval = tufo[1].get(newvalkey)

                    kwargs = {}
                    smin = tufo[1].get(sminkey)
                    if smin is not None:
                        kwargs['seen:min'] = smin
                    smax = tufo[1].get(smaxkey)
                    if smax is not None:
                        kwargs['seen:max'] = smax

                    newfo = self.core.formTufoByProp('ps:person:has', (perval, (ptype, newval)), **kwargs)

                    tags = s_tufo.tags(tufo, leaf=True)
                    self.core.addTufoTags(newfo, tags)

                    self.core.delTufo(tufo)

                self.core.delTufosByProp('syn:tagform:form', oldform)

            # Add dark rows to the ps:person:has
            # It is safe to operate on all ps:person:has nodes as this point as none should exist
            dvalu = 'ps:201802281621'
            dprop = '_:dark:syn:modl:rev'
            darks = [(i[::-1], dprop, dvalu, t) for (i, p, v, t) in self.core.getRowsByProp('ps:person:has')]
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
                 {'subof': 'guid', 'alias': 'ps:person:guidname', 'doc': 'A GUID for a person'}),
                ('ps:persona',
                 {'subof': 'guid', 'alias': 'ps:persona:guidname', 'doc': 'A GUID for a suspected person'}),

                ('ps:contact', {'subof': 'guid', 'doc': 'A GUID for a contact info record'}),

                ('ps:person:has', {
                    'subof': 'xref',
                    'source': 'person,ps:person',
                    'doc': 'A person owns, controls, or has exclusive use of an object or resource,'
                        'potentially during a specific period of time.'}),

                ('ps:persona:has', {
                    'subof': 'xref',
                    'source': 'persona,ps:persona',
                    'doc': 'A persona owns, controls, or has exclusive use of an object or resource,'
                        'potentially during a specific period of time.'}),

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

                ('ps:persona', {'ptype': 'ps:persona'}, [
                    ('guidname', {'ptype': 'str:lwr', 'doc': 'The GUID resolver alias for this suspected person'}),
                    ('dob', {'ptype': 'time', 'doc': 'The Date of Birth (DOB) if known'}),
                    ('img', {'ptype': 'file:bytes', 'doc': 'The "primary" image of a suspected person'}),
                    ('nick', {'ptype': 'inet:user'}),
                    ('name', {'ptype': 'ps:name',
                        'doc': 'The localized name for the suspected person'}),
                    ('name:sur', {'ptype': 'ps:tokn', }),
                    ('name:middle', {'ptype': 'ps:tokn'}),
                    ('name:given', {'ptype': 'ps:tokn'}),
                    ('name:en', {'ptype': 'ps:name',
                        'doc': 'The English version of the name for the suspected person'}),
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

                ('ps:person:has', {}, [
                    ('person', {'ptype': 'ps:person', 'ro': 1, 'req': 1,
                        'doc': 'The person who owns or controls the object or resource.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The object or resource (prop=valu) that is owned or controlled by the person.'}),
                    ('xref:node', {'ptype': 'ndef', 'ro': 1, 'req': 1,
                        'doc': 'The ndef of the node that is owned or controlled by the person.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the object or resource that is owned or controlled by the person.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time when the person owned or controlled the resource.'
                    }),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known time when the person owned or controlled the resource.'
                    }),
                ]),

                ('ps:persona:has', {}, [
                    ('persona', {'ptype': 'ps:persona', 'ro': 1, 'req': 1,
                        'doc': 'The persona who owns or controls the object or resource.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The object or resource (prop=valu) that is owned or controlled by the persona.'}),
                    ('xref:node', {'ptype': 'ndef', 'ro': 1, 'req': 1,
                        'doc': 'The ndef of the node that is owned or controlled by the persona.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the object or resource that is owned or controlled by the persona.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time when the persona owned or controlled the resource.'
                    }),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known time when the persona owned or controlled the resource.'
                    }),
                ]),

            ),
        }
        name = 'ps'
        return ((name, modl), )
