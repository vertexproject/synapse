import synapse.lib.module as s_module

class GovUsModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('gov:us:ssn', ('int', {}), {'doc': 'A US Social Security Number (SSN).'}),
                ('gov:us:zip', ('int', {}), {'doc': 'A US Postal Zip Code.'}),
                ('gov:us:cage', ('str', {'lower': True}), {'doc': 'A Commercial and Government Entity (CAGE) code.'}),
            ),

            'forms': (
                ('gov:us:cage', {}, (
                    ('name0', ('ou:name', {}), {'doc': 'The name of the organization.'}),
                    ('name1', ('str', {'lower': True}), {'doc': 'Name Part 1.'}),
                    ('street', ('str', {'lower': True}), {}),
                    ('city', ('str', {'lower': True}), {}),
                    ('state', ('str', {'lower': True}), {}),
                    ('zip', ('gov:us:zip', {}), {}),
                    ('cc', ('pol:iso2', {}), {}),
                    ('country', ('str', {'lower': True}), {}),
                    ('phone0', ('tel:phone', {}), {}),
                    ('phone1', ('tel:phone', {}), {}),
                )),

                ('gov:us:ssn', {}, []),
                ('gov:us:zip', {}, []),
            ),
        }
        name = 'gov:us'
        return ((name, modl), )
