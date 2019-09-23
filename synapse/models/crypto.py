import logging

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

ex_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
ex_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
ex_sha256 = 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c'
ex_sha384 = 'd425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c'
ex_sha512 = 'ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11'

sigalgos = {
#1.2.840.113549.1.1.1 - RSA encryption
#1.2.840.113549.1.1.2 - MD2 with RSA encryption
    '1.2.840.113549.1.1.3': 'md4WithRSAEncryption',
#1.2.840.113549.1.1.4 - MD5 with RSA encryption
    '1.2.840.113549.1.1.5': 'sha1-with-rsa-signature',
#1.2.840.113549.1.1.6 - rsaOAEPEncryptionSET
#1.2.840.113549.1.1.7 - id-RSAES-OAEP
#1.2.840.113549.1.1.10 - RSASSA-PSS
#1.2.840.113549.1.1.11 - sha256WithRSAEncryption
}

class CryptoModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (

                ('crypto:x509:cert', ('guid', {}), {
                    'doc': 'A unique X.509 certificate.',
                }),

                ('crypto:x509:san', (???), {
                    'doc': 'An X.509 Subject Alternative Name (SAN) value.',
                }),

                ('crypto:x509:crl', ('guid', {}), {
                    'doc': 'A unique X.509 Certificate Revocation List.',
                }),

                ('crypto:x509:revoked', ('comp', 'fields': (('crl', 'crypto:x509:crl'), ('cert', 'crypto:x509:cert'))), {
                    'doc': 'A revokation relationship between a CRL and an X.509 certificate.',
                }),

                ('crypto:x509:signedfile', ???
                }),

                ('crypto:x509:chain', ('array', {'type': 'crypto:x509:cert'}), {
                })

                #('iso:oid', ('str', {'regex':
                #('iso:oid', ('str', {'regex': '^([1-9][0-9]{0,3}|0)(\.([1-9][0-9]{0,3}|0)){5,13}$'}), {

                #('crypto:x509:keytype', ('str', {'regex': '^([1-9][0-9]{0,3}|0)(\.([1-9][0-9]{0,3}|0)){5,13}$'}), {
                #}),

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
                )),

                ('crypto:x509:signed', {}, (
                    ('cert', ('crypto:x509:cert', {}), {
                        'doc': 'The certificate for the key which signed the file.'}),
                    ('file': ('file:bytes', {}), {
                        'doc': 'The file which was signed by the certificates key.'}),
                ),
                ('crypto:x509:crl', {},
                    ('file', ('file:bytes', {}), {
                        'doc': 'The file containing the CRL.'}),
                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the CRL was published.'}),
                ),

                ('crypto:x509:revoked', {}, (
                    ('crl', ('crypto:x509:crl', {}), {
                        'doc': 'The CRL which revoked the certificate.'})
                    ('cert', ('crypto:x509:cert', {}), {
                        'doc': 'The certificate revoked by the CRL.'}),
                ),

                ('crypto:x509:cert', {}, (

                    ('subject', ('str', {}), {
                        'doc': 'The subject identifier, commonly in X.500/LDAP format, to which the certificate was issued.',
                    }),

                    ('subject:fqdn', ('inet:fqdn', {}), {
                        'doc': 'The optional inet:fqdn from within the subject Common Name.',
                    })

                    ('subject:email', ('inet:email', {}), {
                        'doc': 'The optional inet:email from within the subject Common Name.',
                    })

                    ('issuer', ('str', {}), {
                        'doc': 'The Distinguished Name (DN) of the Certificate Authority (CA) which issued the certificate.',
                    }),

                    ('serial', ('str', {}), {
                        'doc': 'The serial number string in the certificate.',
                    }),

                    ('validity:notbefore', ('time', {}), {
                    }),

                    ('validity:notafter', ('time', {}), {
                    }),

                    ('md5', ('hash:md5', {}) {
                        'doc': 'The MD5 fingerprint for the certificate.',
                    }),

                    ('sha1', ('hash:sha1', {}) {
                        'doc': 'The SHA1 fingerprint for the certificate.',
                    }),

                    ('sha256', ('hash:sha256', {}) {
                        'doc': 'The SHA256 fingerprint for the certificate.',
                    }),

                    ('keytype', ('oid', {'names': keytypes}), {
                        'doc': 'The X.509 key type OID.',
                    }),

                    ('rsa:key', ('rsa:key', {}), {
                        'doc': 'The optional RSA public key associated with the certificate.',
                    }),

                    ('algo', ('oid', {'names': sigalgos}), {
                        'doc': 'The X.509 signature algorithm OID.',
                    })

                    ('signature', ('hex', {}), {
                        'doc': 'The hexidecimal representation of the digital signature.',
                    }),

                    ('ext:sans', ('array', {'type': 'crypto:x509:san'}), {
                        'doc': 'The Subject Alternate Names (SANs) listed in the certficate.',
                    }),

                    ('ext:crls', ('array', {'type': 'inet:url'}), {
                        'doc': 'A list of the CRL Distribution Point URLs.',
                    }),

                    #('ext:auth:keyid',
                    #('ext:subj:keyid',
                    #('ext:usage',
                    #('ext:keyusage',
                    #('ext:crl:paths',
                    # TODO more of these
                    #('ext:cons:isca',
                )),
            )
        }
        name='crypto'
        return ((name, modl),)
