import synapse.lib.module as s_module

class LangModule(s_module.CoreModule):

    def getModelDefs(self):

        modldef = ('lang', {

            "types": (

                ('lang:idiom', ('str', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use lang:translation.'}),

                ('lang:phrase', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A small group of words which stand together as a concept.'}),

                ('lang:trans', ('str', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use lang:translation.'}),

                ('lang:code', ('str', {'lower': True, 'regex': '^[a-z]{2}(.[a-z]{2})?$'}), {
                    'ex': 'pt.br',
                    'doc': 'An optionally 2 part language code.'}),

                ('lang:translation', ('guid', {}), {
                    'doc': 'A translation of text from one language to another.'}),

                ('lang:name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'A name used to refer to a language.'}),

                ('lang:language', ('guid', {}), {
                    'doc': 'A specific written or spoken language.'}),
            ),
            'forms': (

                ('lang:phrase', {}, ()),
                ('lang:idiom', {}, (

                    ('url', ('inet:url', {}), {
                        'doc': 'Authoritative URL for the idiom.'}),

                    ('desc:en', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'English description.'}),
                )),

                ('lang:trans', {}, (

                    ('text:en', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'English translation.'}),

                    ('desc:en', ('str', {}), {
                        'doc': 'English description.',
                        'disp': {'hint': 'text'}}),
                )),

                ('lang:translation', {}, (

                    ('input', ('str', {}), {
                        'ex': 'hola',
                        'doc': 'The input text.'}),

                    ('input:lang', ('lang:code', {}), {
                        'doc': 'The input language code.'}),

                    ('output', ('str', {}), {
                        'ex': 'hi',
                        'doc': 'The output text.'}),

                    ('output:lang', ('lang:code', {}), {
                        'doc': 'The output language code.'}),

                    ('desc', ('str', {}), {
                        'ex': 'A standard greeting',
                        'doc': 'A description of the meaning of the output.'}),

                    ('engine', ('it:prod:softver', {}), {
                        'doc': 'The translation engine version used.'}),
                )),

                ('lang:name', {}, ()),

                ('lang:language', {}, (

                    ('code', ('lang:code', {}), {
                        'doc': 'The language code for this language.'}),

                    ('name', ('lang:name', {}), {
                        'doc': 'The primary name of the language.'}),

                    ('names', ('array', {'type': 'lang:name', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of alternative names for the language.'}),

                    ('skill', ('ps:skill', {}), {
                        'doc': 'The skill used to annotate proficiency in the language.'}),
                )),

            ),

        })

        return (modldef, )
