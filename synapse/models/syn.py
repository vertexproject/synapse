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
