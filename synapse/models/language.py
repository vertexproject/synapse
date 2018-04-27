import synapse.lib.module as s_module

class LangModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('lang', {

                'types': (

                    ('lang:idiom',
                        ('str', {}),  # TODO migrate to token-searchable type
                        {'doc': 'A subcultural idiom.'}
                    ),

                    ('lang:trans',
                        ('str', {}),  # TODO migrate to token-searchable type
                        {'doc': 'Raw text with a documented translation.'}
                    ),

                ),

                'forms': (

                    ('lang:idiom', {}, (
                        ('url', ('inet:url', {}), {'doc': 'Authoritative URL for the idiom.'}),  # FIXME implement inet:url
                        ('desc:en', ('str', {}), {'doc': 'English description.'}),  # TODO migrate to token-searchable type
                    )),

                    ('lang:trans', {}, (
                        ('text:en', ('str', {}), {'doc': 'English translation.'}),  # TODO migrate to token-searchable type
                        ('desc:en', ('str', {}), {'doc': 'English description.'}),  # TODO migrate to token-searchable type
                    )),

                ),

            }),
        )
