from synapse.lib.module import CoreModule, modelrev

class SynMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('syn:splice', {'subof': 'guid'}),
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
