import synapse.lib.module as s_module

class LangModule(s_module.CoreModule):

    def getModelDefs(self):
        name = 'lang'

        ctors = ()

        forms = (
            ('lang:idiom', {}, (
                ('url', ('inet:url', {}), {
                    'doc': 'Authoritative URL for the idiom.'
                }),
                ('desc:en', ('str', {}), {
                    'doc': 'English description.',
                    'disp': {'hint': 'text'},
                }),
            )),

            ('lang:trans', {}, (
                ('text:en', ('str', {}), {
                    'doc': 'English translation.',
                    'disp': {'hint': 'text'},
                }),
                ('desc:en', ('str', {}), {
                    'doc': 'English description.',
                    'disp': {'hint': 'text'},
                }),
            )),
        )

        types = (
            ('lang:idiom', ('str', {}), {
                'doc': 'A subcultural idiom.'
            }),

            ('lang:trans', ('str', {}), {
                'doc': 'Raw text with a documented translation.'
            }),
        )

        modldef = (name, {
            'ctors': ctors,
            'forms': forms,
            'types': types,
        })
        return (modldef, )
