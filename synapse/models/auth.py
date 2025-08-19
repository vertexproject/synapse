import hashlib

import synapse.lib.types as s_types

class Passwd(s_types.Str):

    async def norm(self, valu, view=None):
        retn = await s_types.Str.norm(self, valu)
        retn[1].setdefault('subs', {})
        byts = retn[0].encode('utf8')
        retn[1]['subs'].update({
            'md5': hashlib.md5(byts, usedforsecurity=False).hexdigest(),
            'sha1': hashlib.sha1(byts, usedforsecurity=False).hexdigest(),
            'sha256': hashlib.sha256(byts).hexdigest(),
        })
        return retn

modeldefs = (

    ('auth', {

        'ctors': (
            ('auth:passwd', 'synapse.models.auth.Passwd', {'strip': False}, {
                'interfaces': (
                    ('auth:credential', {}),
                    ('crypto:hashable', {}),
                    ('meta:observable', {'template': {'title': 'password'}}),
                ),
                'doc': 'A password string.'}),
        ),

        'types': (

            ('auth:credential', ('ndef', {'interface': 'auth:credential'}), {
                'doc': 'A node which inherits the auth:credential interface.'}),
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
        ),

    }),
)
