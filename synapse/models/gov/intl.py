import synapse.lib.module as s_module

class GovIntlModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('iso:oid', ('str', {'regex': '^([0-2])((\\.0)|(\\.[1-9][0-9]*))*$'}), {
                    'doc': 'An ISO Object Identifier string.'}),

                ('iso:3166:cc', ('str', {'lower': True, 'regex': '^[a-z]{2}$'}), {
                    'doc': 'An ISO 3166 2 digit country code.'}),

                ('gov:intl:un:m49', ('int', {'min': 1, 'max': 999}), {
                    'doc': 'UN M49 Numeric Country Code.'}),
            ),

            'forms': (
                ('iso:oid', {}, (
                    ('descr', ('str', {}), {
                        'doc': 'A description of the value or meaning of the OID.'}),
                    ('identifier', ('str', {}), {
                        'doc': 'The string identifier for the deepest tree element.'}),
                )),
            ),
        }
        name = 'gov:intl'
        return ((name, modl), )
