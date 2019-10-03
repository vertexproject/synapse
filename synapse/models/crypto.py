import logging

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

ex_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
ex_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
ex_sha256 = 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c'
ex_sha384 = 'd425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c'
ex_sha512 = 'ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11'

class CryptoModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {

            'types': (

                ('crypto:currency:coin', ('str', {'lower': True}), {
                    'doc': 'An individual crypto currency type.',
                    'ex': 'btc',
                }),
                ('crypto:currency:address', ('comp', {'fields': (('coin', 'crypto:currency:coin'), ('iden', 'str'))}), {
                    'doc': 'An individual crypto currency address.',
                    'ex': '(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)',
                }),

                ('crypto:currency:client', ('comp', {'fields': (
                                                        ('inetaddr', 'inet:client'),
                                                        ('coinaddr', 'crypto:currency:address')
                                                    )}), {
                    'doc': 'A fused node representing a crypto currency address used by an Internet client.',
                    'ex': '(1.2.3.4, (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2))',
                }),

                ('hash:md5', ('hex', {'size': 32}), {
                    'doc': 'A hex encodeded MD5 hash',
                    'ex': ex_md5
                }),
                ('hash:sha1', ('hex', {'size': 40}), {
                    'doc': 'A hex encoded SHA1 hash',
                    'ex': ex_sha1
                }),
                ('hash:sha256', ('hex', {'size': 64}), {
                    'doc': 'A hex encoded SHA256 hash',
                    'ex': ex_sha256
                }),
                ('hash:sha384', ('hex', {'size': 96}), {
                    'doc': 'A hex encoded SHA384 hash',
                    'ex': ex_sha384
                }),
                ('hash:sha512', ('hex', {'size': 128}), {
                    'doc': 'A hex encoded SHA512 hash',
                    'ex': ex_sha512
                }),
                ('hash:lm', ('hex', {'size': 32}), {
                    'doc': 'A hex encoded Microsoft Windows LM password hash',
                    'ex': ex_md5
                }),
                ('hash:ntlm', ('hex', {'size': 32}), {
                    'doc': 'A hex encoded Microsoft Windows NTLM password hash',
                    'ex': ex_md5
                }),
                ('rsa:key', ('comp', {'fields': (('mod', 'hex'), ('pub:exp', 'int')), }), {
                    'doc': 'An RSA keypair modulus and public exponent.'
                }),
            ),

            'forms': (

                ('crypto:currency:coin', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The full name of the crypto coin.'}),
                )),

                ('crypto:currency:address', {}, (
                    ('coin', ('str', {}), {
                        'doc': 'The crypto coin to which the address belongs.'}),
                    ('desc', ('str', {}), {
                        'doc': 'A free-form description of the address.'}),
                    ('iden', ('str', {}), {
                        'doc': 'The coin specific address identifier.'}),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'Contact information associated with the address.'}),
                )),

                ('crypto:currency:client', {}, (
                    ('inetaddr', ('inet:client', {}), {
                        'doc': 'The Internet client address observed using the crypto currency address.'}),
                    ('coinaddr', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address observed in use the the Internet client.'}),
                )),

                ('hash:md5', {}, ()),
                ('hash:sha1', {}, ()),
                ('hash:sha256', {}, ()),
                ('hash:sha384', {}, ()),
                ('hash:sha512', {}, ()),
                ('rsa:key', {}, (
                    ('mod', ('hex', {}), {'ro': 1,
                       'doc': 'The RSA key modulus.'}),
                    ('pub:exp', ('int', {}), {'ro': 1,
                       'doc': 'The public exponent'}),
                    ('bits', ('int', {}),
                     {'doc': 'The length of the modulus in bits'}),
                    ('priv:exp', ('hex', {}),
                     {'doc': 'The private exponent'}),
                    ('priv:p', ('hex', {}),
                     {'doc': 'One of the two private primes.'}),
                    ('priv:q', ('hex', {}),
                     {'doc': 'One of the two private primes.'}),
                ))
            )
        }
        name = 'crypto'
        return ((name, modl),)
