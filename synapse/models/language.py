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

            ('lang:translation', {}, (
                ('input', ('str', {}), {
                    'ex': 'hola',
                    'doc': 'The input text.',
                }),
                ('input:lang', ('lang:code', {}), {
                    'doc': 'The input language code.'
                }),
                ('output', ('str', {}), {
                    'ex': 'hi',
                    'doc': 'The output text.',
                }),
                ('output:lang', ('lang:code', {}), {
                    'doc': 'The output language code.'
                }),
                ('desc', ('str', {}), {
                    'doc': 'A description of the meaning of the output.',
                    'ex': 'A standard greeting',
                }),
                ('engine', ('it:prod:softver', {}), {
                    'doc': 'The translation engine version used.',
                }),
            ))
        )

        types = (
            ('lang:idiom', ('str', {}), {
                'deprecated': True,
                'doc': 'Deprecated. Please use lang:translation.'
            }),

            ('lang:trans', ('str', {}), {
                'deprecated': True,
                'doc': 'Deprecated. Please use lang:translation.'
            }),

            ('lang:code', ('str', {'lower': True, 'regex': '^[a-z]{2}(.[a-z]{2})?$'}), {
                'ex': 'pt.br',
                'doc': 'An optionally 2 part language code.',
            }),
            ('lang:translation', ('guid', {}), {
                'doc': 'A translation of text from one language to another.',
            }),
        )

        modldef = (name, {
            'ctors': ctors,
            'forms': forms,
            'types': types,
        })
        return (modldef, )
