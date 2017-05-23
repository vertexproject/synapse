
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
            ('crypto:key',  {'subof': 'str:hex', 'doc': 'An asymmetric cryptokey, such as an RSA key.'}),
            ('crypto:signature', {'subof': 'hash:sha512', 'doc': 'A SHA512 hash of a signature\'s crypto material', 'ex': ex_sha512}),
        ),

        'forms':(
            ('hash:md5', {'ptype':'hash:md5'},[]),
            ('hash:sha1', {'ptype':'hash:sha1'},[]),
            ('hash:sha256', {'ptype':'hash:sha256'},[]),
            ('hash:sha384', {'ptype':'hash:sha384'},[]),
            ('hash:sha512', {'ptype':'hash:sha512'},[]),
            ('crypto:key', {'ptype': 'crypto:key'}, [
                ('fingerprint',       {'ptype': 'str:hex'}),
                ('id',                {'ptype': 'str:hex'}),
                ('created_at',        {'ptype': 'time:epoch'}),
                ('expiration',        {'ptype': 'time:epoch'}),
                ('subkey_of',         {'ptype': 'crypto:key'}),
                ('type',              {'ptype': 'str'}),
                ('rsa:pub:mod',       {'ptype': 'str:hex'}),
                ('rsa:bits',          {'ptype': 'int'}),
                ('rsa:pub:exp',       {'ptype': 'str:hex'}),
                ('rsa:priv:exp',      {'ptype': 'str:hex'}),
                ('rsa:priv:p',        {'ptype': 'str:hex'}),
                ('rsa:priv:q',        {'ptype': 'str:hex'}),
                ('dsa:pub:prime',     {'ptype': 'str:hex'}),
                ('dsa:pub:key',       {'ptype': 'str:hex'}),
                ('dsa:pub:generator', {'ptype': 'str:hex'}),
                ('dsa:pub:order',     {'ptype': 'str:hex'}),
                ('dsa:priv:exponent', {'ptype': 'str:hex'}),
                ('elg:pub:prime',     {'ptype': 'str:hex'}),
                ('elg:pub:key',       {'ptype': 'str:hex'}),
                ('elg:pub:generator', {'ptype': 'str:hex'}),
                ('elg:priv:exponent', {'ptype': 'str:hex'}),
            ]),
            ('crypto:signature', {'ptype': 'crypto:signature'}, [
                ('created_at',     {'ptype': 'time:epoch'}),
                ('expiration',     {'ptype': 'time:epoch'}),
                ('hash_algorithm', {'ptype': 'str'}),
                ('pub_algorithm',  {'ptype': 'str'}),
                ('signature_type', {'ptype': 'str'}),
                ('hash_digest',    {'ptype': 'str:hex'}),
                ('dsa_r',          {'ptype': 'str:hex'}),
                ('dsa_s',          {'ptype': 'str:hex'}),
                ('rsa_signature',  {'ptype': 'str:hex'}),
                ('key_id',         {'ptype': 'str:hex'}),
                ('target_type',    {'ptype': 'str'}),
                ('source',         {'ptype': 'str:hex'}),
                ('target',         {'ptype': 'str'}),
            ]),
        ),
    }
