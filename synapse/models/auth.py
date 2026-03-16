modeldefs = (

    ('auth', {

        'ctors': (
            ('auth:passwd', 'synapse.lib.types.Passwd', {'strip': False}, {
                'interfaces': (
                    ('auth:credential', {}),
                    ('crypto:hashable', {}),
                    ('meta:observable', {'template': {'title': 'password'}}),
                ),
                'doc': 'A password string.'}),
        ),

        'types': (),

        'interfaces': (
            ('auth:credential', {
                'doc': 'An interface inherited by authentication credential forms.',
            }),
        ),

        'forms': (
            ('auth:passwd', {}, (
                ('md5', ('crypto:hash:md5', {}), {
                    'computed': True,
                    'doc': 'The MD5 hash of the password.'}),

                ('sha1', ('crypto:hash:sha1', {}), {
                    'computed': True,
                    'doc': 'The SHA1 hash of the password.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'computed': True,
                    'doc': 'The SHA256 hash of the password.'}),
            )),
        ),

    }),
)
