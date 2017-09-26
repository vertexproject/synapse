from synapse.lib.module import CoreModule, modelrev

class SynMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {

            'types': (
                ('syn:splice', {'subof': 'guid'}),
                ('syn:auth:user', {'subof': 'str'}),
                ('syn:auth:role', {'subof': 'str'}),
                ('syn:auth:userrole', {'subof': 'comp', 'fields': 'user=syn:auth:user,role=syn:auth:role'}),
            ),

            'forms': (

                ('syn:splice', {'local': 1}, (
                    ('act', {'ptype': 'str:lwr'}),
                    ('time', {'ptype': 'time'}),
                    ('node', {'ptype': 'guid'}),
                    ('user', {'ptype': 'str:lwr'}),

                    ('tag', {'ptype': 'str:lwr'}),
                    ('form', {'ptype': 'str:lwr'}),
                    ('valu', {'ptype': 'str:lwr'}),
                )),

                ('syn:auth:user', {'local': 1}, (
                    ('storm:limit:lift', {'ptype': 'int', 'defval': 10000, 'doc': 'The storm query lift limit for the user'}),
                    ('storm:limit:time', {'ptype': 'int', 'defval': 120, 'doc': 'The storm query time limit for the user'}),
                )),

                ('syn:auth:role', {'local': 1}, (
                    ('desc', {'ptype': 'str'}),
                )),

                ('syn:auth:userrole', {'local': 1}, (
                    ('user', {'ptype': 'syn:auth:user'}),
                    ('role', {'ptype': 'syn:auth:role'}),
                )),

                ('syn:trigger', {'ptype': 'guid', 'local': 1}, (
                    ('en', {'ptype': 'bool', 'defval': 0, 'doc': 'Is the trigger currently enabled'}),
                    ('on', {'ptype': 'syn:perm'}),
                    ('run', {'ptype': 'syn:storm'}),
                    ('user', {'ptype': 'syn:auth:user'}),
                )),

            ),
        }

        name = 'syn'
        return ((name, modl), )

    @modelrev('syn', 201709051630)
    def _delOldModelNodes(self):

        types = self.core.getRowsByProp('syn:type')
        forms = self.core.getRowsByProp('syn:form')
        props = self.core.getRowsByProp('syn:prop')
        syncore = self.core.getRowsByProp('.:modl:vers:syn:core')

        with self.core.getCoreXact():
            [self.core.delRowsById(r[0]) for r in types]
            [self.core.delRowsById(r[0]) for r in forms]
            [self.core.delRowsById(r[0]) for r in props]
            [self.core.delRowsById(r[0]) for r in syncore]
