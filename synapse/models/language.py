modeldefs = (
    ('lang', {

        'types': (

            ('lang:phrase', ('str', {'lower': True, 'onespace': True}), {
                'doc': 'A small group of words which stand together as a concept.'}),

            ('lang:code', ('str', {'lower': True, 'regex': '^[a-z]{2}(.[a-z]{2})?$'}), {
                'ex': 'pt.br',
                'doc': 'An optionally 2 part language code.'}),

            ('lang:translation', ('guid', {}), {
                'doc': 'A translation of text from one language to another.'}),

            ('lang:language', ('guid', {}), {
                'doc': 'A specific written or spoken language.'}),
        ),
        'forms': (

            ('lang:phrase', {}, ()),

            ('lang:translation', {}, (

                ('input', ('lang:phrase', {}), {
                    'ex': 'hola',
                    'doc': 'The input text.'}),

                ('input:lang', ('lang:code', {}), {
                    'doc': 'The input language code.'}),

                ('output', ('lang:phrase', {}), {
                    'ex': 'hi',
                    'doc': 'The output text.'}),

                ('output:lang', ('lang:code', {}), {
                    'doc': 'The output language code.'}),

                ('desc', ('text', {}), {
                    'ex': 'A standard greeting',
                    'doc': 'A description of the meaning of the output.'}),

                ('engine', ('it:software', {}), {
                    'doc': 'The translation engine version used.'}),
            )),

            ('lang:language', {}, (

                ('code', ('lang:code', {}), {
                    'doc': 'The language code for this language.'}),

                ('name', ('meta:name', {}), {
                    'alts': ('names',),
                    'doc': 'The primary name of the language.'}),

                ('names', ('array', {'type': 'meta:name', 'sorted': True, 'uniq': True}), {
                    'doc': 'An array of alternative names for the language.'}),

                ('skill', ('ps:skill', {}), {
                    'doc': 'The skill used to annotate proficiency in the language.'}),
            )),

        ),

    }),
)
