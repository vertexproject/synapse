import logging

import synapse.common as s_common

from synapse.lib.module import CoreModule, modelrev

logger = logging.getLogger(__name__)

ex_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
ex_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
ex_sha256 = 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c'
ex_sha384 = 'd425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c'
ex_sha512 = 'ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11'

class CryptoMod(CoreModule):

    @modelrev('crypto', 201708231712)
    def _revModl201708231712(self):
        pass # here from legacy for backward compat

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('hash:md5', {'subof': 'str', 'regex': '^[0-9a-f]{32}$', 'lower': 1,
                    'doc': 'A hex encoded MD5 hash', 'ex': ex_md5}),

                ('hash:sha1', {'subof': 'str', 'regex': '^[0-9a-f]{40}$', 'lower': 1,
                    'doc': 'A hex encoded SHA1 hash', 'ex': ex_sha1}),

                ('hash:sha256', {'subof': 'str', 'regex': '^[0-9a-f]{64}$', 'lower': 1,
                    'doc': 'A hex encoded SHA256 hash', 'ex': ex_sha256}),

                ('hash:sha384', {'subof': 'str', 'regex': '^[0-9a-f]{96}$', 'lower': 1,
                    'doc': 'A hex encoded SHA384 hash', 'ex': ex_sha384}),

                ('hash:sha512', {'subof': 'str', 'regex': '^[0-9a-f]{128}$', 'lower': 1,
                    'doc': 'A hex encoded SHA512 hash', 'ex': ex_sha512}),

                ('hash:lm', {'subof': 'str', 'regex': '^[0-9a-f]{32}$', 'lower': 1,
                    'doc': 'A hex encoded Microsoft Windows LM password hash', 'ex': ex_md5}),

                ('hash:ntlm', {'subof': 'str', 'regex': '^[0-9a-f]{32}$', 'lower': 1,
                    'doc': 'A hex encoded Microsoft Windows NTLM password hash', 'ex': ex_md5}),

                ('rsa:key', {'subof': 'sepr', 'sep': '/', 'fields': 'mod,str:hex|pub:exp,str:hex',
                             'doc': 'An RSA keypair modulus and public exponent'}),

            ),

            'forms': (
                ('hash:md5', {'ptype': 'hash:md5'}, []),
                ('hash:sha1', {'ptype': 'hash:sha1'}, []),
                ('hash:sha256', {'ptype': 'hash:sha256'}, []),
                ('hash:sha384', {'ptype': 'hash:sha384'}, []),
                ('hash:sha512', {'ptype': 'hash:sha512'}, []),
                ('rsa:key', {'ptype': 'rsa:key'}, [
                    ('mod', {'ptype': 'str:hex', 'doc': 'The RSA key modulus'}),
                    ('bits', {'ptype': 'int', 'doc': 'The length of the modulus in bits'}),
                    ('pub:exp', {'ptype': 'str:hex', 'doc': 'The public exponent'}),
                    ('priv:exp', {'ptype': 'str:hex', 'doc': 'The private exponent'}),
                    ('priv:p', {'ptype': 'str:hex', 'doc': 'One of the two private primes'}),
                    ('priv:q', {'ptype': 'str:hex', 'doc': 'One of the two private primes'}),
                ]),
            ),
        }
        name = 'crypto'
        return ((name, modl), )
