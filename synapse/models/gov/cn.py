import synapse.lib.module as s_module

class GovCnModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('gov:cn:icp',
                    ('int', {}),
                    {'doc': 'A Chinese Internet Content Provider ID'},
                 ),
                ('gov:cn:mucd',
                    ('int', {}),
                    {'doc': 'A Chinese PLA MUCD'},
                 ),
            ),
            'forms': (
                ('gov:cn:icp', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org with the Internet Content Provider ID.',
                    }),
                )),
                # TODO - Add 'org' as a secondary property to mcud?
                ('gov:cn:mucd', {}, ()),
            )
        }
        name = 'gov:cn'
        return ((name, modl), )
