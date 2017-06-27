from synapse.lib.module import CoreModule, modelrev

class GovUsMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('gov:us:ssn', {'subof': 'int', 'doc': 'A US Social Security Number (SSN)'}),
                ('gov:us:zip', {'subof': 'int', 'doc': 'A US Zip Code'}),
                ('gov:us:cage', {'subof': 'str', 'lower': 1, 'doc': 'A Commercial and Government Entity (CAGE) code'}),
            ),

            'forms': (
                ('gov:us:cage', {}, (
                    ('name0', {'ptype': 'ou:name', 'doc': 'The name of the organization'}),
                    ('name1', {'ptype': 'str:lwr', 'doc': 'Name Part 1'}),
                    ('street', {'ptype': 'str:lwr'}),
                    ('city', {'ptype': 'str:lwr'}),
                    ('state', {'ptype': 'str:lwr'}),
                    ('zip', {'ptype': 'gov:us:zip'}),
                    ('cc', {'ptype': 'pol:iso2'}),
                    ('country', {'ptype': 'str:lwr'}),
                    ('phone0', {'ptype': 'tel:phone'}),
                    ('phone1', {'ptype': 'tel:phone'}),
                )),

                ('gov:us:ssn', {}, []),
                ('gov:us:zip', {}, []),
            ),
        }
        name = 'gov:us'
        return ((name, modl), )
