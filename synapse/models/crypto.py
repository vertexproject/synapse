
# Matching N number of occurrences in regex is easy. Matching a specific list of numbers of
# occurrences... maybe not so much. This helper method builds that regex for you.
def n_time_regex(base_re, times):
    r = '^'
    times.sort()
    sum = 0
    base_re = '(?:%s)' % base_re
    for n in times:
        r += '(?:%s{%d}' % (base_re, n - sum)
        sum = n
    r += ')?' * (len(times) - 1)
    r += ')$'
    return r

ex_md5    = 'd41d8cd98f00b204e9800998ecf8427e'
ex_sha1   = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
ex_sha256 = 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c'
ex_sha384 = 'd425f1394e418ce01ed1579069a8bfaa1da8f32cf823982113ccbef531fa36bda9987f389c5af05b5e28035242efab6c'
ex_sha512 = 'ca74fe2ff2d03b29339ad7d08ba21d192077fece1715291c7b43c20c9136cd132788239189f3441a87eb23ce2660aa243f334295902c904b5520f6e80ab91f11'

def getDataModel():
    return {

        'version':201701181223,

        'types':(
            ('hash:md5',    {'subof':'str','regex':'^[0-9a-f]{32}$', 'lower':1, 'doc':'An MD5 hash', 'ex':ex_md5 }),
            ('hash:sha1',   {'subof':'str','regex':'^[0-9a-f]{40}$', 'lower':1, 'doc':'A SHA1 hash', 'ex':ex_sha1 }),
            ('hash:sha256', {'subof':'str','regex':'^[0-9a-f]{64}$', 'lower':1, 'doc':'A SHA256 hash', 'ex':ex_sha256 }),
            ('hash:sha384', {'subof':'str','regex':'^[0-9a-f]{96}$', 'lower':1, 'doc':'A SHA384 hash', 'ex':ex_sha384 }),
            ('hash:sha512', {'subof':'str','regex':'^[0-9a-f]{128}$', 'lower':1, 'doc':'A SHA512 hash', 'ex':ex_sha512 }),
            ('pgp:userid',  {'subof': 'sepr', 'sep': '/', 'fields': 'name,str|email,inet:email', 'doc': 'A UserID packet.'}),
            ('crypto:asym',  {'subof': 'str:hex', 'doc': 'An asymmetric cryptokey, such as an RSA key.'}),
            ('crypto:sig',  {'subof': 'str:hex', 'doc': 'A SHA512 hash of a signature\'s crypto material', 'ex': ex_sha512}),
            ('crypto:sig:digest', {'subof': 'str:hex', 'doc': 'Message digest contained in a cryptographic signature. Usually the output of a hashing function.', 'ex': ex_sha512}),
            ('crypto:sig:rsa',  {'subof': 'str:hex', 'doc': 'Cryptographic material representing the RSA signature of a document.'}),
            ('crypto:sig:dsa:r',  {'subof': 'str:hex', 'doc': 'DSA cryptographic signature value R'}),
            ('crypto:sig:dsa:s',  {'subof': 'str:hex', 'doc': 'DSA cryptographic signature value S'}),

            # https://tools.ietf.org/html/rfc4880#section-12.2
            ('crypto:asym:finger',         {'subof': 'str:hex', 'regex': '^[0-9a-f]{40}$', 'lower': 1, 'doc': ''}),
            ('crypto:asym:id',             {'subof': 'str:hex', 'regex': '^[0-9a-f]{16}$', 'lower': 1, 'doc': ''}),

            # RSA key of bitlen N will have a shared modulus of len N and will have constants some size smaller, so we can't do strict size checking.
            # https://crypto.stackexchange.com/questions/16417/is-rsa-key-size-the-size-of-private-key-exponent
            ('crypto:asym:rsa:pub:mod',    {'subof': 'str:hex', 'regex': '^[0-9a-f]{128,1024}$', 'lower': 1, 'doc': 'RSA public modulus.'}),
            ('crypto:asym:rsa:pub:exp',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'lower': 1, 'doc': 'RSA public exponent. (Creates public key combined with modulus)'}),
            ('crypto:asym:rsa:priv:exp',   {'subof': 'str:hex', 'regex': '^[0-9a-f]{128,1024}$', 'lower': 1, 'doc': 'RSA private exponent (Creates private key combined with modulus)'}),
            ('crypto:asym:rsa:priv:p',     {'subof': 'str:hex', 'regex': '^[0-9a-f]{128,1024}$', 'lower': 1, 'doc': 'RSA system prime p.'}),
            ('crypto:asym:rsa:priv:q',     {'subof': 'str:hex', 'regex': '^[0-9a-f]{128,1024}$', 'lower': 1, 'doc': 'RSA system prime q.'}),

            # http://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf,  page 24
            ('crypto:asym:dsa:pub:p',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'DSA system prime modulus (length L).'}),
            ('crypto:asym:dsa:pub:q',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'DSA system prime divisor of (p - 1) (length N). Defines the modular subgroup that DSA operates in.'}),
            ('crypto:asym:dsa:pub:g',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'DSA system multiplicative group generator of order q.'}),
            ('crypto:asym:dsa:pub:y',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'DSA system public key (y = g^x mod p)'}),
            ('crypto:asym:dsa:priv:x',   {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'DSA system private exponent(key) used to generate y'}),

            # TODO: ECDSA modeling.

            ('crypto:asym:elg:pub:p',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'ElGamal system prime modulus (length L)'}),
            ('crypto:asym:elg:pub:y',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'ElGamal public key such that (y = g^x mod p)'}),
            ('crypto:asym:elg:pub:g',    {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'The ElGamal generator of the multiplicative group of integers mod p.'}),
            ('crypto:asym:elg:priv:x',   {'subof': 'str:hex', 'regex': '^[0-9a-f]+$', 'doc': 'The ElGamal private exponent(key).'}),

            ('crypto:sym:rc4',   {'subof': 'str:hex', 'regex': '^[0-9a-f]{10,512}$',                  'doc': 'Key to an RC4 cipher'}),
            ('crypto:sym:aes',   {'subof': 'str:hex', 'regex': n_time_regex('[0-9a-f]', [16, 32, 64]), 'doc': 'Key to an AES cipher'}),
            ('crypto:sym:des',   {'subof': 'str:hex', 'regex': '^[0-9a-f]{14}$',                       'doc': '56 bit key to a DES cipher'}),
            ('crypto:sym:3des',  {'subof': 'str:hex', 'regex': '^[0-9a-f]{42}$',                       'doc': '168 bit key to a triple DES cipher.'}),
            ('crypto:sym:bfish', {'subof': 'str:hex', 'regex': '^[0-9a-f]{8,112}',                     'doc': 'Key to a blowfish cipher. Contains between 32 and 448 bits.'}),
            ('crypto:sym:2fish', {'subof': 'str:hex', 'regex': n_time_regex('[0-9a-f]', [32, 48, 64]), 'doc': 'Key to a twofish cipher. Has 128, 192 or 256 bits'}),
        ),

        'forms':(
            ('hash:md5', {'ptype':'hash:md5'},[]),
            ('hash:sha1', {'ptype':'hash:sha1'},[]),
            ('hash:sha256', {'ptype':'hash:sha256'},[]),
            ('hash:sha384', {'ptype':'hash:sha384'},[]),
            ('hash:sha512', {'ptype':'hash:sha512'},[]),

            ('crypto:sym:rc4',   {'ptype': 'crypto:sym:rc4'}, []),
            ('crypto:sym:aes',   {'ptype': 'crypto:sym:aes'}, []),
            ('crypto:sym:des',   {'ptype': 'crypto:sym:des'}, []),
            ('crypto:sym:3des',  {'ptype': 'crypto:sym:3des'}, []),
            ('crypto:sym:bfish', {'ptype': 'crypto:sym:bfish'}, []),
            ('crypto:sym:2fish', {'ptype': 'crypto:sym:2fish'}, []),

            ('crypto:asym', {'ptype': 'crypto:asym'}, [
                ('finger',       {'ptype': 'crypto:asym:finger'}),
                ('id',           {'ptype': 'crypto:asym:id'}),
                ('created_at',   {'ptype': 'time:epoch'}),
                ('expiration',   {'ptype': 'time:epoch'}),
                ('subkey_of',    {'ptype': 'crypto:asym'}),
                ('type',         {'ptype': 'str'}),
                ('sys',          {'ptype': 'str:hex'}),
                ('size',         {'ptype': 'int'}),
                ('rsa:pub:mod',  {'ptype': 'crypto:asym:rsa:pub:mod'}),
                ('rsa:pub:exp',  {'ptype': 'crypto:asym:rsa:pub:exp'}),
                ('rsa:priv:exp', {'ptype': 'crypto:asym:rsa:priv:exp'}),
                ('rsa:priv:p',   {'ptype': 'crypto:asym:rsa:priv:p'}),
                ('rsa:priv:q',   {'ptype': 'crypto:asym:rsa:priv:q'}),
                ('dsa:pub:p',    {'ptype': 'crypto:asym:dsa:pub:p'}),
                ('dsa:pub:q',    {'ptype': 'crypto:asym:dsa:pub:q'}),
                ('dsa:pub:g',    {'ptype': 'crypto:asym:dsa:pub:g'}),
                ('dsa:pub:y',    {'ptype': 'crypto:asym:dsa:pub:y'}),
                ('dsa:priv:x',   {'ptype': 'crypto:asym:dsa:priv:x'}),
                ('elg:pub:p',    {'ptype': 'crypto:asym:elg:pub:p'}),
                ('elg:pub:y',    {'ptype': 'crypto:asym:elg:pub:y'}),
                ('elg:pub:g',    {'ptype': 'crypto:asym:elg:pub:g'}),
                ('elg:priv:x',   {'ptype': 'crypto:asym:elg:priv:x'}),
            ]),
            ('crypto:sig', {'ptype': 'crypto:sig'}, [
                ('created_at',     {'ptype': 'time:epoch'}),
                ('expiration',     {'ptype': 'time:epoch'}),
                ('hash_alg', {'ptype': 'str'}),
                ('pub_alg',  {'ptype': 'str'}),
                ('sig_type', {'ptype': 'str'}),
                ('digest',         {'ptype': 'crypto:sig:digest'}),
                ('dsa:r',          {'ptype': 'crypto:sig:dsa:r'}),
                ('dsa:s',          {'ptype': 'crypto:sig:dsa:s'}),
                ('rsa',            {'ptype': 'crypto:sig:rsa'}),
                ('key:id',         {'ptype': 'crypto:asym:id'}),
                ('src',            {'ptype': 'crypto:asym'}),

                # More thought needs to be done wrt how to model things that can be
                # cryptographically signed by a given key. Theoretically any information
                # at all can be signed, so it's difficult to model in any specific sense.
                ('tgt_type',    {'ptype': 'str'}),
                ('tgt',         {'ptype': 'str'}),
            ]),
        ),
    }
