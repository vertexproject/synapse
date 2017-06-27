from synapse.lib.module import CoreModule, modelrev

class GovIntlMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('gov:intl:un:m49', {'subof': 'int', 'doc': 'UN M4 Numeric Country Code'}),
            ),
        }
        name = 'gov:intl'
        return ((name, modl), )
