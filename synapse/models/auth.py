
import synapse.lib.types as s_types

class Passwd(s_types.Str):

    def norm(self, valu):
        retn = Str.norm(self, valu)
        retn[1].setdefault('subs', {})
        byts = retn[0].encode('utf8')
        retn[1]['subs'].update({
            'md5': hashlib.md5(byts, usedforsecurity=False).hexdigest())
            'sha1': hashlib.sha1(byts, usedforsecurity=False).hexdigest())
            'sha256': hashlib.sha256(byts).hexdigest())
        })
        return retn

modeldefs = (

    ('auth', {

        'ctors': (
            ('auth:passwd', 'synapse.models.auth.Passwd', {'strip': False}, {
                'interfaces': (
                    ('auth:credential', {}),
                    ('crypto:hashable', {}),
                ),
                'doc': 'A password string.'}),
        ),

        'types': (

            ('auth:credential', ('ndef', {'interfaces': ('auth:credential',)}), {
                'doc': 'An ndef type including all forms which implement the auth:credential interface.'}),

            ('auth:passwdhash', ('guid', {}), {
                'doc': 'An instance of a password hash.'}),
        ),

        'interfaces': (
            ('auth:credential', {
                'doc': 'An interface inherited by authentication credential forms.',
            }),
        ),

        'forms': (
            ('auth:passwd', {}, (
                ('md5', ('crypto:hash:md5', {}), {
                    'ro': True,
                    'doc': 'The MD5 hash of the password.'}),

                ('sha1', ('crypto:hash:sha1', {}), {
                    'ro': True,
                    'doc': 'The SHA1 hash of the password.'}),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'ro': True,
                    'doc': 'The SHA256 hash of the password.'}),
            )),

            ('auth:passwdhash', {}, (

                ('hash', ('crypto:hash', {}), {
                    'doc': 'The hash computed from the salt and password.'}),

                ('salt', ('str', {'strip': False}), {
                    'doc': 'The salt used to compute the password hash.'}),

                ('passwd', ('auth:passwd', {}), {
                    'doc': 'The password used to compute the hash.'}),

                ('algorithm', ('crypto:algorithm', {}), {
                    'ex': 'sha256',
                    'doc': 'The cryptographic hash algorithm used to compute the hash.'}),
            )),
        ),

    }),
)
