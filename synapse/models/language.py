modeldefs = (
    ('lang', {

        'interfaces': (
            ('lang:transcript', {
                'doc': 'An interface which applies to forms containing speech.',
            }),
        ),

        'types': (

            ('lang:phrase', ('text', {}), {
                'doc': 'A small group of words which stand together as a concept.'}),

            ('lang:code', ('str', {'lower': True, 'regex': '^[a-z]{2}(.[a-z]{2})?$'}), {
                'ex': 'pt.br',
                'doc': 'An optionally 2 part language code.'}),

            ('lang:idiom', ('guid', {}), {
                'doc': 'An idiomatic use of a phrase.'}),

            ('lang:translation', ('guid', {}), {
                'doc': 'A translation of text from one language to another.'}),

            ('lang:language', ('guid', {}), {
                'interfaces': (
                    ('edu:learnable', {}),
                ),
                'doc': 'A specific written or spoken language.'}),

            ('lang:transcript', ('ndef', {'interface': 'lang:transcript'}), {
                'doc': 'A node which implements the lang:transcript interface.'}),

            ('lang:statement', ('guid', {}), {
                'doc': 'A single statement which is part of a transcript.'}),

        ),
        'forms': (

            ('lang:phrase', {}, ()),

            ('lang:translation', {}, (

                ('input', ('nodeprop', {}), {
                    'ex': 'hola',
                    'doc': 'The input text.'}),

                ('input:lang', ('lang:language', {}), {
                    'doc': 'The input language.'}),

                ('output', ('text', {}), {
                    'ex': 'hi',
                    'doc': 'The output text.'}),

                ('output:lang', ('lang:language', {}), {
                    'doc': 'The output language.'}),

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
            )),

            ('lang:statement', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time that the speaker made the statement.'}),

                ('transcript', ('lang:transcript', {}), {
                    'doc': 'The transcript where the statement was recorded.'}),

                ('transcript:offset', ('duration', {}), {
                    'doc': 'The time offset of the statement within the transcript.'}),

                ('speaker', ('entity:actor', {}), {
                    'doc': 'The entity making the statement.'}),

                ('text', ('str', {}), {
                    'doc': 'The transcribed text of the statement.'}),
            )),

            ('lang:statement', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time that the speaker made the statement.'}),

                ('transcript', ('lang:transcript', {}), {
                    'doc': 'The transcript where the statement was recorded.'}),

                ('transcript:offset', ('duration', {}), {
                    'doc': 'The time offset of the statement within the transcript.'}),

                ('speaker', ('entity:actor', {}), {
                    'doc': 'The entity making the statement.'}),

                ('text', ('str', {}), {
                    'doc': 'The transcribed text of the statement.'}),
            )),

        ),

    }),
)
