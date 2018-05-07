import synapse.lib.module as s_module

class GovIntlModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('gov:intl:un:m49', ('int', {'min': 1, 'max': 999}), {'doc': 'UN M49 Numeric Country Code'}),
            ),
        }
        name = 'gov:intl'
        return ((name, modl), )
