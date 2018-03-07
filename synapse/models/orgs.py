from synapse.common import guid

import synapse.lib.tufo as s_tufo
import synapse.lib.module as s_module

class OuMod(s_module.CoreModule):

    def initCoreModule(self):
        self.core.addSeedCtor('ou:org:name', self.seedOrgName)
        self.core.addSeedCtor('ou:org:alias', self.seedOrgAlias)

    def seedOrgName(self, prop, valu, **props):
        node = self.core.getTufoByProp('ou:org:name', valu)
        if node is None:
            node = self.core.formTufoByProp('ou:org', guid(), name=valu, **props)
        return node

    def seedOrgAlias(self, prop, valu, **props):
        node = self.core.getTufoByProp('ou:org:alias', valu)
        if node is None:
            node = self.core.formTufoByProp('ou:org', guid(), alias=valu, **props)
        return node

    @s_module.modelrev('ou', 201802281621)
    def _revModl201802281621(self):
        '''
        Combine ou:has* into ou:org:has
        - Forms a new ou:org:has node for all of the old ou:has* nodes
        - Applies the old node's tags to the new node
        - Deletes the old node
        - Deletes the syn:tagform nodes for the old form
        - Adds dark row for each node, signifying that they were added by migration
        - NOTE: does not migrate ou:hasalias
        '''
        data = (
            ('ou:hasfile', 'file', 'file:bytes'),
            ('ou:hasfqdn', 'fqdn', 'inet:fqdn'),
            ('ou:hasipv4', 'ipv4', 'inet:ipv4'),
            ('ou:hashost', 'host', 'it:host'),
            ('ou:hasemail', 'email', 'inet:email'),
            ('ou:hasphone', 'phone', 'tel:phone'),
            ('ou:haswebacct', 'web:acct', 'inet:web:acct'),
        )
        with self.core.getCoreXact() as xact:

            for oldform, pname, ptype in data:
                orgkey = oldform + ':org'
                newvalkey = oldform + ':' + pname
                sminkey = oldform + ':seen:min'
                smaxkey = oldform + ':seen:max'

                for tufo in self.core.getTufosByProp(oldform):
                    orgval = tufo[1].get(orgkey)
                    newval = tufo[1].get(newvalkey)

                    kwargs = {}
                    smin = tufo[1].get(sminkey)
                    if smin is not None:
                        kwargs['seen:min'] = smin
                    smax = tufo[1].get(smaxkey)
                    if smax is not None:
                        kwargs['seen:max'] = smax

                    newfo = self.core.formTufoByProp('ou:org:has', (orgval, (ptype, newval)), **kwargs)

                    tags = s_tufo.tags(tufo, leaf=True)
                    self.core.addTufoTags(newfo, tags)

                    self.core.delTufo(tufo)

                self.core.delTufosByProp('syn:tagform:form', oldform)

            # Add dark rows to the ou:org:has
            # It is safe to operate on all ou:org:has nodes as this point as none should exist
            dvalu = 'ou:201802281621'
            dprop = '_:dark:syn:modl:rev'
            darks = [(i[::-1], dprop, dvalu, t) for (i, p, v, t) in self.core.getRowsByProp('ou:org:has')]
            self.core.addRows(darks)

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('ou:org', {'subof': 'guid', 'alias': 'ou:org:alias',
                            'doc': 'A GUID for a human organization such as a company or military unit'}),
                ('ou:user', {'subof': 'sepr', 'sep': '/', 'fields': 'org,ou:org|user,inet:user',
                             'doc': 'A user name within an organization'}),
                ('ou:alias',
                 {'subof': 'str:lwr', 'regex': '^[0-9a-z]+$', 'doc': 'An alias for the org GUID', 'ex': 'vertexproj'}),

                ('ou:name', {'subof': 'str:lwr'}),
                ('ou:sic', {'subof': 'int', 'doc': 'Standard Industrial Classification Code'}),
                ('ou:naics', {'subof': 'int', 'doc': 'North American Industry Classification System'}),

                ('ou:suborg',
                 {'subof': 'comp', 'fields': 'org,ou:org|sub,ou:org', 'doc': 'An org which owns a sub org'}),
                ('ou:member', {'subof': 'comp', 'fields': 'org,ou:org|person,ps:person',
                               'doc': 'A person who is (or was) a member of an organization.'}),

                ('ou:hasalias', {'subof': 'comp', 'fields': 'org=ou:org,alias=ou:alias'}),
                ('ou:org:has', {
                    'subof': 'xref',
                    'source': 'org,ou:org',
                    'doc': 'An org owns, controls, or has exclusive use of an object or resource,'
                        'potentially during a specific period of time.'}),

            ),

            'forms': (

                ('ou:org', {'ptype': 'ou:org'}, [
                    ('cc', {'ptype': 'pol:iso2'}),
                    ('name', {'ptype': 'ou:name'}),
                    ('name:en', {'ptype': 'ou:name'}),
                    ('alias', {'ptype': 'ou:alias'}),
                    ('phone', {'ptype': 'tel:phone', 'doc': 'The primary phone number for the organization'}),
                    ('sic', {'ptype': 'ou:sic'}),
                    ('naics', {'ptype': 'ou:naics'}),
                    ('us:cage', {'ptype': 'gov:us:cage'}),
                    ('url', {'ptype': 'inet:url'}),
                ]),

                ('ou:suborg', {}, [
                    ('org', {'ptype': 'ou:org', 'doc': 'The org which owns sub'}),
                    ('sub', {'ptype': 'ou:org', 'doc': 'The the sub which is owned by org'}),
                    ('perc', {'ptype': 'int', 'doc': 'The optional percentage of sub which is owned by org'}),
                    ('current', {'ptype': 'bool', 'defval': 1, 'doc': 'Is the suborg relationship still current'}),
                    ('seen:min', {'ptype': 'time:min', 'doc': 'The optional time the suborg relationship began'}),
                    ('seen:max', {'ptype': 'time:max', 'doc': 'The optional time the suborg relationship ended'}),
                ]),

                ('ou:user', {}, [
                    ('org', {'ptype': 'ou:org'}),
                    ('user', {'ptype': 'inet:user'}),
                ]),

                ('ou:member', {}, [
                    ('org', {'ptype': 'ou:org', 'ro': 1}),
                    ('person', {'ptype': 'ps:person', 'ro': 1}),
                    ('start', {'ptype': 'time:min'}),
                    ('end', {'ptype': 'time:max'}),
                    ('title', {'ptype': 'str:lwr', 'defval': '??'}),
                ]),

                ('ou:owns', {'ptype': 'sepr', 'sep': '/', 'fields': 'owner,ou:org|owned,ou:org'}, [
                ]),  # FIXME does this become an ou:org:has?

                ('ou:hasalias', {'ptype': 'ou:hasalias'}, (
                    ('org', {'ptype': 'ou:org'}),
                    ('alias', {'ptype': 'ou:alias'}),
                    ('seen:min', {'ptype': 'time:min'}),
                    ('seen:max', {'ptype': 'time:max'}),
                )),
                ('ou:org:has', {}, [
                    ('org', {'ptype': 'ou:org', 'ro': 1, 'req': 1,
                        'doc': 'The org who owns or controls the object or resource.'}),
                    ('xref', {'ptype': 'propvalu', 'ro': 1, 'req': 1,
                        'doc': 'The object or resource (prop=valu) that is owned or controlled by the org.'}),
                    ('xref:node', {'ptype': 'ndef', 'ro': 1, 'req': 1,
                        'doc': 'The ndef of the node that is owned or controlled by the org.'}),
                    ('xref:prop', {'ptype': 'str', 'ro': 1,
                        'doc': 'The property (form) of the object or resource that is owned or controlled by the org.'}),
                    ('seen:min', {'ptype': 'time:min',
                        'doc': 'The earliest known time when the org owned or controlled the resource.'}),
                    ('seen:max', {'ptype': 'time:max',
                        'doc': 'The most recent known time when the org owned or controlled the resource.'}),
                ]),

            ),
        }
        name = 'ou'
        return ((name, modl), )
