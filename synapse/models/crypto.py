ex_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
ex_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
ex_sha256 = 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c'
ex_sha384 = 'd425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c'
ex_sha512 = 'ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11'

x509vers = (
    (0, 'v1'),
    (2, 'v3'),
)

modeldefs = (
    ('crypto', {
        'types': (

            ('crypto:currency:transaction', ('guid', {}), {
                'doc': 'An individual crypto currency transaction recorded on the blockchain.'}),

            ('crypto:currency:block', ('comp', {'fields': (
                                                    ('coin', 'econ:currency'),
                                                    ('offset', 'int'),
                                               ), 'sepr': '/'}), {
                'doc': 'An individual crypto currency block record on the blockchain.'}),

            ('crypto:smart:contract', ('guid', {}), {
                'doc': 'A smart contract.'}),

            ('crypto:smart:effect:transfertoken', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which transfers ownership of a non-fungible token.'}),

            ('crypto:smart:effect:transfertokens', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which transfers fungible tokens.'}),

            ('crypto:smart:effect:edittokensupply', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which increases or decreases the supply of a fungible token.'}),

            ('crypto:smart:effect:minttoken', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which creates a new non-fungible token.'}),

            ('crypto:smart:effect:burntoken', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which destroys a non-fungible token.'}),

            ('crypto:smart:effect:proxytoken', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which grants a non-owner address the ability to manipulate a specific non-fungible token.'}),

            ('crypto:smart:effect:proxytokenall', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which grants a non-owner address the ability to manipulate all non-fungible tokens of the owner.'}),

            ('crypto:smart:effect:proxytokens', ('guid', {}), {
                'interfaces': (
                    ('crypto:smart:effect', {}),
                ),
                'doc': 'A smart contract effect which grants a non-owner address the ability to manipulate fungible tokens.'}),

            # TODO crypto:smart:effect:call - call another smart contract
            # TODO crypto:smart:effect:giveproxy - grant your proxy for a token based vote
            ('crypto:payment:input', ('guid', {}), {
                'doc': 'A payment made into a transaction.'}),

            ('crypto:payment:output', ('guid', {}), {
                'doc': 'A payment received from a transaction.'}),

            ('crypto:smart:token', ('comp', {'fields': (('contract', 'crypto:smart:contract'), ('tokenid', 'hugenum'))}), {
                'doc': 'A token managed by a smart contract.'}),

            ('crypto:currency:address', ('comp', {'fields': (('coin', 'econ:currency'), ('iden', 'str')), 'sepr': '/'}), {

                'interfaces': (
                    ('econ:pay:instrument', {'template': {'instrument': 'crypto currency address'}}),
                    ('meta:observable', {'template': {'title': 'crypto currency address'}}),
                ),
                'ex': 'btc/1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
                'doc': 'An individual crypto currency address.'}),

            ('crypto:currency:client', ('comp', {'fields': (
                                                    ('inetaddr', 'inet:client'),
                                                    ('coinaddr', 'crypto:currency:address')
                                                )}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'crypto currency address and Internet client'}}),
                ),
                'ex': '(1.2.3.4, (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2))',
                'doc': 'A fused node representing a crypto currency address used by an Internet client.'}),

            ('crypto:hash', ('ndef', {'interface': 'crypto:hash'}), {
                'doc': 'A cryptographic hash.'}),

            ('crypto:hashable', ('ndef', {'interface': 'crypto:hashable'}), {
                'doc': 'A node which can be cryptographically hashed.'}),

            ('crypto:pki:key', ('ndef', {'forms': ('crypto:key:rsa', 'crypto:key:dsa')}), {
                'doc': 'A node which is a public key.'}),

            ('crypto:hash:md5', ('hex', {'size': 32}), {
                'ex': ex_md5,
                'interfaces': (
                    ('crypto:hash', {}),
                    ('meta:observable', {'template': {'title': 'MD5'}}),
                ),
                'doc': 'A hex encoded MD5 hash.'}),

            ('crypto:hash:sha1', ('hex', {'size': 40}), {
                'ex': ex_sha1,
                'interfaces': (
                    ('crypto:hash', {}),
                    ('meta:observable', {'template': {'title': 'SHA1'}}),
                ),
                'doc': 'A hex encoded SHA1 hash.'}),

            ('crypto:hash:sha256', ('hex', {'size': 64}), {
                'ex': ex_sha256,
                'interfaces': (
                    ('crypto:hash', {}),
                    ('meta:observable', {'template': {'title': 'SHA256'}}),
                ),
                'doc': 'A hex encoded SHA256 hash.'}),

            ('crypto:hash:sha384', ('hex', {'size': 96}), {
                'ex': ex_sha384,
                'interfaces': (
                    ('crypto:hash', {}),
                    ('meta:observable', {'template': {'title': 'SHA384'}}),
                ),
                'doc': 'A hex encoded SHA384 hash.'}),

            ('crypto:hash:sha512', ('hex', {'size': 128}), {
                'ex': ex_sha512,
                'interfaces': (
                    ('crypto:hash', {}),
                    ('meta:observable', {'template': {'title': 'SHA512'}}),
                ),
                'doc': 'A hex encoded SHA512 hash.'}),

            ('crypto:salthash', ('guid', {}), {
                'interfaces': (
                    ('auth:credential', {}),
                    ('meta:observable', {'template': {'title': 'salted hash'}}),
                ),
                'doc': 'A salted hash computed for a value.'}),

            ('crypto:key', ('ndef', {'interface': 'crypto:key'}), {
                'doc': 'A cryptographic key and algorithm.'}),

            # TODO DH / ECDH / ECDHE
            ('crypto:key:rsa', ('guid', {}), {
                'interfaces': (
                    ('crypto:key', {}),
                    ('meta:observable', {'template': {'title': 'RSA key pair'}}),
                ),
                'doc': 'An RSA public/private key pair.'}),

            ('crypto:key:rsa:prime', ('guid', {}), {
                'doc': 'A prime value and exponent used to generate an RSA key.'}),

            ('crypto:key:dsa', ('guid', {}), {
                'interfaces': (
                    ('crypto:key', {}),
                    ('meta:observable', {'template': {'title': 'DSA key pair'}}),
                ),
                'doc': 'A DSA public/private key pair.'}),

            ('crypto:key:secret', ('guid', {}), {
                'interfaces': (
                    ('crypto:key', {}),
                    ('meta:observable', {'template': {'title': 'secret key'}}),
                ),
                'doc': 'A secret key with an optional initialiation vector.'}),

            ('crypto:algorithm', ('str', {'lower': True, 'onespace': True}), {
                'ex': 'aes256',
                'doc': 'A cryptographic algorithm name.'}),

            ('crypto:x509:cert', ('guid', {}), {
                'doc': 'A unique X.509 certificate.'}),

            ('crypto:x509:san', ('comp', {'fields': (('type', 'str'), ('value', 'str'))}), {
                'doc': 'An X.509 Subject Alternative Name (SAN).'}),

            ('crypto:x509:crl', ('guid', {}), {
                'doc': 'A unique X.509 Certificate Revocation List.'}),

            ('crypto:x509:revoked', ('comp', {'fields': (('crl', 'crypto:x509:crl'), ('cert', 'crypto:x509:cert'))}), {
                'doc': 'A revocation relationship between a CRL and an X.509 certificate.'}),

            ('crypto:x509:signedfile', ('comp', {'fields': (('cert', 'crypto:x509:cert'), ('file', 'file:bytes'))}), {
                'doc': 'A digital signature relationship between an X.509 certificate and a file.'}),
        ),

        'interfaces': (

            ('crypto:key', {
                'props': (
                    ('bits', ('int', {'min': 1}), {
                        'doc': 'The number of bits of key material.'}),

                    ('algorithm', ('crypto:algorithm', {}), {
                        'ex': 'aes256',
                        'doc': 'The cryptographic algorithm which uses the key material.'}),
                ),
                'doc': 'An interface inherited by all cryptographic keys.'}),

            ('crypto:hash', {
                'doc': 'An interface inherited by all cryptographic hashes.'}),

            ('crypto:hashable', {
                'doc': 'An interface inherited by types which are frequently hashed.'}),

            ('crypto:smart:effect', {
                'doc': 'Properties common to the effects of a crypto smart contract transaction.',
                'props': (
                    ('index', ('int', {}), {
                        'doc': 'The order of the effect within the effects of one transaction.'}),
                    ('transaction', ('crypto:currency:transaction', {}), {
                        'doc': 'The transaction where the smart contract was called.'}),
                ),
            }),
        ),

        'forms': (

            ('crypto:payment:input', {}, (
                ('transaction', ('crypto:currency:transaction', {}), {
                    'doc': 'The transaction the payment was input to.'}),
                ('address', ('crypto:currency:address', {}), {
                    'doc': 'The address which paid into the transaction.'}),
                ('value', ('econ:price', {}), {
                    'doc': 'The value of the currency paid into the transaction.'}),
            )),
            ('crypto:payment:output', {}, (
                ('transaction', ('crypto:currency:transaction', {}), {
                    'doc': 'The transaction the payment was output from.'}),
                ('address', ('crypto:currency:address', {}), {
                    'doc': 'The address which received payment from the transaction.'}),
                ('value', ('econ:price', {}), {
                    'doc': 'The value of the currency received from the transaction.'}),
            )),
            ('crypto:currency:transaction', {}, (
                ('hash', ('hex', {}), {
                    'doc': 'The unique transaction hash for the transaction.'}),
                ('desc', ('str', {}), {
                    'doc': 'An analyst specified description of the transaction.'}),
                ('block', ('crypto:currency:block', {}), {
                    'doc': 'The block which records the transaction.'}),
                ('block:coin', ('econ:currency', {}), {
                    'doc': 'The coin/blockchain of the block which records this transaction.'}),
                ('block:offset', ('int', {}), {
                    'doc': 'The offset of the block which records this transaction.'}),

                ('success', ('bool', {}), {
                    'doc': 'Set to true if the transaction was successfully executed and recorded.'}),
                ('status:code', ('int', {}), {
                    'doc': 'A coin specific status code which may represent an error reason.'}),
                ('status:message', ('str', {}), {
                    'doc': 'A coin specific status message which may contain an error reason.'}),

                ('to', ('crypto:currency:address', {}), {
                    'doc': 'The destination address of the transaction.'}),
                ('from', ('crypto:currency:address', {}), {
                    'doc': 'The source address of the transaction.'}),
                ('fee', ('econ:price', {}), {
                    'doc': 'The total fee paid to execute the transaction.'}),
                ('value', ('econ:price', {}), {
                    'doc': 'The total value of the transaction.'}),
                ('time', ('time', {}), {
                    'doc': 'The time this transaction was initiated.'}),

                ('eth:gasused', ('int', {}), {
                    'doc': 'The amount of gas used to execute this transaction.'}),
                ('eth:gaslimit', ('int', {}), {
                    'doc': 'The ETH gas limit specified for this transaction.'}),
                ('eth:gasprice', ('econ:price', {}), {
                    'doc': 'The gas price (in ETH) specified for this transaction.'}),

                ('contract:input', ('file:bytes', {}), {
                    'doc': 'Input value to a smart contract call.'}),
                ('contract:output', ('file:bytes', {}), {
                    'doc': 'Output value of a smart contract call.'}),
                # TODO break out args/retvals and maybe make humon repr?
            )),

            ('crypto:currency:block', {}, (
                ('coin', ('econ:currency', {}), {
                    'doc': 'The coin/blockchain this block resides on.', 'ro': True, }),
                ('offset', ('int', {}), {
                    'doc': 'The index of this block.', 'ro': True, }),
                ('hash', ('hex', {}), {
                    'doc': 'The unique hash for the block.'}),
                ('minedby', ('crypto:currency:address', {}), {
                    'doc': 'The address which mined the block.'}),
                ('time', ('time', {}), {
                    'doc': 'Time timestamp embedded in the block by the miner.'}),
            )),

            ('crypto:smart:contract', {}, (
                ('transaction', ('crypto:currency:transaction', {}), {
                    'doc': 'The transaction which created the contract.'}),
                ('address', ('crypto:currency:address', {}), {
                    'doc': 'The address of the contract.'}),
                ('bytecode', ('file:bytes', {}), {
                    'doc': 'The bytecode which implements the contract.'}),
                ('token:name', ('str', {}), {
                    'doc': 'The ERC-20 token name.'}),
                ('token:symbol', ('str', {}), {
                    'doc': 'The ERC-20 token symbol.'}),
                ('token:totalsupply', ('hugenum', {}), {
                    'doc': 'The ERC-20 totalSupply value.'}),
                # TODO methods, ABI conventions, source/disassembly
            )),
            ('crypto:smart:token', {}, (

                ('contract', ('crypto:smart:contract', {}), {
                    'ro': True,
                    'doc': 'The smart contract which defines and manages the token.'}),

                ('tokenid', ('hugenum', {}), {
                    'ro': True,
                    'doc': 'The token ID.'}),

                ('owner', ('crypto:currency:address', {}), {
                    'doc': 'The address which currently owns the token.'}),

                ('nft:url', ('inet:url', {}), {
                    'doc': 'The URL which hosts the NFT metadata.'}),

                ('nft:meta', ('data', {}), {
                    'doc': 'The raw NFT metadata.'}),

                ('nft:meta:name', ('base:name', {}), {
                    'doc': 'The name field from the NFT metadata.'}),

                ('nft:meta:description', ('text', {}), {
                    'doc': 'The description field from the NFT metadata.'}),

                ('nft:meta:image', ('inet:url', {}), {
                    'doc': 'The image URL from the NFT metadata.'}),
            )),

            ('crypto:smart:effect:transfertoken', {}, (

                ('token', ('crypto:smart:token', {}), {
                    'doc': 'The non-fungible token that was transferred.'}),

                ('from', ('crypto:currency:address', {}), {
                    'doc': 'The address the NFT was transferred from.'}),

                ('to', ('crypto:currency:address', {}), {
                    'doc': 'The address the NFT was transferred to.'}),
            )),

            ('crypto:smart:effect:transfertokens', {}, (

                ('contract', ('crypto:smart:contract', {}), {
                    'doc': 'The contract which defines the tokens.'}),

                ('from', ('crypto:currency:address', {}), {
                    'doc': 'The address the tokens were transferred from.'}),

                ('to', ('crypto:currency:address', {}), {
                    'doc': 'The address the tokens were transferred to.'}),

                ('amount', ('hugenum', {}), {
                    'doc': 'The number of tokens transferred.'}),
            )),

            ('crypto:smart:effect:edittokensupply', {}, (

                ('contract', ('crypto:smart:contract', {}), {
                    'doc': 'The contract which defines the tokens.'}),

                ('amount', ('hugenum', {}), {
                    'doc': 'The number of tokens added or removed if negative.'}),

                ('totalsupply', ('hugenum', {}), {
                    'doc': 'The total supply of tokens after this modification.'}),
            )),

            ('crypto:smart:effect:minttoken', {}, (
                ('token', ('crypto:smart:token', {}), {
                    'doc': 'The non-fungible token that was created.'}),
            )),

            ('crypto:smart:effect:burntoken', {}, (
                ('token', ('crypto:smart:token', {}), {
                    'doc': 'The non-fungible token that was destroyed.'}),
            )),

            ('crypto:smart:effect:proxytoken', {}, (

                ('owner', ('crypto:currency:address', {}), {
                    'doc': 'The address granting proxy authority to manipulate non-fungible tokens.'}),

                ('proxy', ('crypto:currency:address', {}), {
                    'doc': 'The address granted proxy authority to manipulate non-fungible tokens.'}),

                ('token', ('crypto:smart:token', {}), {
                    'doc': 'The specific token being granted access to.'}),
            )),

            ('crypto:smart:effect:proxytokenall', {}, (

                ('contract', ('crypto:smart:contract', {}), {
                    'doc': 'The contract which defines the tokens.'}),

                ('owner', ('crypto:currency:address', {}), {
                    'doc': 'The address granting/denying proxy authority to manipulate all non-fungible tokens of the owner.'}),

                ('proxy', ('crypto:currency:address', {}), {
                    'doc': 'The address granted/denied proxy authority to manipulate all non-fungible tokens of the owner.'}),

                ('approval', ('bool', {}), {
                    'doc': 'The approval status.'}),
            )),

            ('crypto:smart:effect:proxytokens', {}, (

                ('contract', ('crypto:smart:contract', {}), {
                    'doc': 'The contract which defines the tokens.'}),

                ('owner', ('crypto:currency:address', {}), {
                    'doc': 'The address granting proxy authority to manipulate fungible tokens.'}),

                ('proxy', ('crypto:currency:address', {}), {
                    'doc': 'The address granted proxy authority to manipulate fungible tokens.'}),

                ('amount', ('hex', {}), {
                    'doc': 'The hex encoded amount of tokens the proxy is allowed to manipulate.'}),
            )),

            ('crypto:currency:address', {}, (

                ('coin', ('econ:currency', {}), {
                    'doc': 'The crypto coin to which the address belongs.', 'ro': True, }),

                ('seed', ('crypto:key', {}), {
                    'doc': 'The cryptographic key and or password used to generate the address.'}),

                ('iden', ('str', {}), {
                    'doc': 'The coin specific address identifier.', 'ro': True, }),

                ('desc', ('str', {}), {
                    'doc': 'A free-form description of the address.'}),

                ('contact', ('entity:contactable', {}), {
                    'doc': 'The primary contact information associated with the crypto currency address.'}),
            )),

            ('crypto:algorithm', {}, ()),

            ('crypto:key:rsa:prime', {}, (

                ('value', ('hex', {}), {
                    'doc': 'The hex encoded prime number.'}),

                ('exponent', ('hex', {}), {
                    'doc': 'The hex encoded exponent.'}),
            )),

            ('crypto:key:rsa', {}, (

                ('public:modulus', ('hex', {}), {
                    'doc': 'The public modulus of the RSA key.'}),

                ('public:exponent', ('hex', {}), {
                    'doc': 'The public exponent of the RSA key.'}),

                ('private:exponent', ('hex', {}), {
                    'doc': 'The private exponent of the RSA key.'}),

                ('private:primes', ('array', {'type': 'crypto:key:rsa:prime', 'sorted': True, 'uniq': True}), {
                    'doc': 'The prime number and exponent combinations used to generate the RSA key.'}),

                ('private:coefficient', ('hex', {}), {
                    'doc': 'The private coefficient of the RSA key.'}),
            )),

            ('crypto:key:dsa', {}, (

                ('public', ('hex', {}), {
                    'doc': 'The HEX encoded public portion of the DSA key.'}),

                ('public:p', ('hex', {}), {
                    'doc': 'The HEX encoded public modulus or "P" component of the DSA key.'}),

                ('public:q', ('hex', {}), {
                    'doc': 'The HEX encoded subgroup order or "Q" component of the DSA key.'}),

                ('public:g', ('hex', {}), {
                    'doc': 'The HEX encoded generator or "G" component of the DSA key.'}),

                ('private', ('hex', {}), {
                    'doc': 'The HEX encoded private portion of the DSA key.'}),
            )),

            ('crypto:key:secret', {}, (

                ('iv', ('hex', {}), {
                    'doc': 'The hex encoded initialization vector.'}),

                ('mode', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The algorithm specific mode in use.'}),

                ('value', ('hex', {}), {
                    'doc': 'The hex encoded secret key.'}),

                ('seed:passwd', ('auth:passwd', {}), {
                    'doc': 'The seed password used to generate the key material.'}),

                ('seed:algorithm', ('crypto:algorithm', {}), {
                    'ex': 'pbkdf2',
                    'doc': 'The algorithm used to generate the key from the seed password.'})
            )),

            ('crypto:currency:client', {}, (

                ('inetaddr', ('inet:client', {}), {
                    'doc': 'The Internet client address observed using the crypto currency address.', 'ro': True, }),

                ('coinaddr', ('crypto:currency:address', {}), {
                    'doc': 'The crypto currency address observed in use by the Internet client.', 'ro': True, }),
            )),

            ('crypto:hash:md5', {}, ()),
            ('crypto:hash:sha1', {}, ()),
            ('crypto:hash:sha256', {}, ()),
            ('crypto:hash:sha384', {}, ()),
            ('crypto:hash:sha512', {}, ()),

            ('crypto:salthash', {}, (

                ('salt', ('hex', {}), {
                    'doc': 'The salt value encoded as a hexadecimal string.'}),

                ('hash', ('crypto:hash', {}), {
                    'doc': 'The hash value.'}),

                ('value', ('crypto:hashable', {}), {
                    'doc': 'The value that was used to compute the salted hash.'}),
            )),

            ('crypto:x509:signedfile', {}, (
                ('cert', ('crypto:x509:cert', {}), {
                    'doc': 'The certificate for the key which signed the file.', 'ro': True, }),
                ('file', ('file:bytes', {}), {
                    'doc': 'The file which was signed by the certificates key.', 'ro': True, }),
            )),

            ('crypto:x509:crl', {}, (
                ('file', ('file:bytes', {}), {
                    'doc': 'The file containing the CRL.'}),
                ('url', ('inet:url', {}), {
                    'doc': 'The URL where the CRL was published.'}),
            )),

            ('crypto:x509:revoked', {}, (
                ('crl', ('crypto:x509:crl', {}), {
                    'doc': 'The CRL which revoked the certificate.', 'ro': True, }),
                ('cert', ('crypto:x509:cert', {}), {
                    'doc': 'The certificate revoked by the CRL.', 'ro': True, }),
            )),

            ('crypto:x509:cert', {}, (

                ('key', ('crypto:pki:key', {}), {
                    'doc': 'The public key embedded in the certificate.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The file that the certificate metadata was parsed from.',
                }),

                ('subject', ('str', {}), {
                    'doc': 'The subject identifier, commonly in X.500/LDAP format, to which the certificate was issued.',
                }),

                ('issuer', ('str', {}), {
                    'doc': 'The Distinguished Name (DN) of the Certificate Authority (CA) which issued the certificate.',
                }),

                ('issuer:cert', ('crypto:x509:cert', {}), {
                    'doc': 'The certificate used by the issuer to sign this certificate.',
                }),

                ('serial', ('hex', {'zeropad': 40}), {
                    'doc': 'The certificate serial number as a big endian hex value.',
                }),

                ('version', ('int', {'enums': x509vers}), {
                    'doc': 'The version integer in the certificate. (ex. 2 == v3 ).',
                }),

                ('subject:cn', ('str', {'strip': True}), {
                    'doc': 'The Common Name (CN) attribute of the x509 Subject.',
                }),

                ('validity:notbefore', ('time', {}), {
                    'doc': 'The timestamp for the beginning of the certificate validity period.',
                }),

                ('validity:notafter', ('time', {}), {
                    'doc': 'The timestamp for the end of the certificate validity period.',
                }),

                ('md5', ('crypto:hash:md5', {}), {
                    'doc': 'The MD5 fingerprint for the certificate.',
                }),

                ('sha1', ('crypto:hash:sha1', {}), {
                    'doc': 'The SHA1 fingerprint for the certificate.',
                }),

                ('sha256', ('crypto:hash:sha256', {}), {
                    'doc': 'The SHA256 fingerprint for the certificate.',
                }),

                ('algo', ('iso:oid', {}), {
                    'doc': 'The X.509 signature algorithm OID.',
                }),

                ('signature', ('hex', {}), {
                    'doc': 'The hexadecimal representation of the digital signature.',
                }),

                ('ext:sans', ('array', {'type': 'crypto:x509:san', 'uniq': True, 'sorted': True}), {
                    'doc': 'The Subject Alternate Names (SANs) listed in the certificate.',
                }),

                ('ext:crls', ('array', {'type': 'crypto:x509:san', 'uniq': True, 'sorted': True}), {
                    'doc': 'A list of Subject Alternate Names (SANs) for Distribution Points.',
                }),

                ('identities:fqdns', ('array', {'type': 'inet:fqdn', 'uniq': True, 'sorted': True}), {
                    'doc': 'The fused list of FQDNs identified by the cert CN and SANs.',
                }),

                ('identities:emails', ('array', {'type': 'inet:email', 'uniq': True, 'sorted': True}), {
                    'doc': 'The fused list of email addresses identified by the cert CN and SANs.',
                }),

                ('identities:ips', ('array', {'type': 'inet:ip', 'uniq': True, 'sorted': True}), {
                    'doc': 'The fused list of IP addresses identified by the cert CN and SANs.',
                    'prevnames': ('identities:ipv4s', 'identities:ipv6s')}),

                ('identities:urls', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                    'doc': 'The fused list of URLs identified by the cert CN and SANs.',
                }),

                ('crl:urls', ('array', {'type': 'inet:url', 'uniq': True, 'sorted': True}), {
                    'doc': 'The extracted URL values from the CRLs extension.',
                }),

                ('selfsigned', ('bool', {}), {
                    'doc': 'Whether this is a self-signed certificate.',
                }),

            )),
        )
    }),
)
