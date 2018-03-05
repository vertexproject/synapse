import synapse.lib.module as s_module

class GovIntlMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('gov:intl:un:m49', {'subof': 'int', 'doc': 'UN M4 Numeric Country Code'}),
            ),
        }
        name = 'gov:intl'
        return ((name, modl), )
