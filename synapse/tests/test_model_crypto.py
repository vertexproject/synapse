import hashlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils


BITS = 2048
HEXSTR_MODULUS = 'abbd407f417fe8d6632aae1c6d09b271416bef9244e61f7c7c2856ddfde3ecf93cd50b3eaea5c9b8cb9bfb5a317bf50925a' \
                 'b500a06247ec2f3294891a8e62c317ee648f933ec1bf760a9d7e9a5ea4706b2a2c3f6376079114ddcc7a15d3fecf001458f' \
                 '22f0551802a25ef95cf464aabeb0514ea3849583bc09022730c44a2ff5f893fc6885add69c103d75114dd2f11436f617fbf' \
                 'b0af2978802aabf35483bbfcc470d50d6afb4283c1d06d2bf27efe9d7c09f226895633a46c3d77173bf0db8634299462b5f' \
                 '29629ad3b0470c76ddfd331ed0207d4dbd5fd44a2f66ca5f802ac0130e4a4bb2c149b5baa7a373188823ee21fe2950a76c8' \
                 '18586919f7914453d'
HEXSTR_PUBLIC_EXPONENT = 0x10001
HEXSTR_PRIVATE_EXPONENT = '9db58a80120f3b2b7d1f998a231b8f916fa985f4456f2a24f0033f5a56a7b35b61e0a695e65dfab3c7ceb2f0ad' \
                          '968e7bdaeac9f29a97730ce5add8a5627c14c3532c7880d88c8f56099f8ed65275a4c9e2cb93b70c3d7c904677' \
                          '639fac7962c537f5bfaf2f12859d0dacb7c403ee59da0922715bba0a6f5202d7c653833e39715f04664c2396c4' \
                          '7bdf3f09f5486d8f6aea767ba011f1a5a10c8b57f079aea58abfd5e50ef20aa5e09b1082f6af98e806c9aeeb89' \
                          '4148a7d82cd6e1443c6115eb567fba0eacf5b7178518b8ba312da6ace22238d1ed19f3e703652576a6152ba60d' \
                          '4d4c6bc75b3ee7c8efeadee0c5ed7c14bf2930a6c4f13137becf38912f49c5'
HEXSTR_PRIVATE_PRIME_P = 'dee90ee63c12729a3fe7d38c581abf7e1c784ec0bd4bfdd1282286ea9996673942a24c7c98b31c6cd12db8ba96d' \
                         'a785c4392569d7bfc2be9d9907c3b7fbf40d31891642952a0e5a23dfbe721a746588df9a246ea4936a1958f66fd' \
                         '3a32c08008a0f6ed9b516fa869fb08a57ef31c0ec217f173e489a2f8f111e25c25c961c2b7'
HEXSTR_PRIVATE_PRIME_Q = 'c53b9c8dfb3dda04d16c7f779a02b3b8c7b44bf876dc88ad562778eafaded9ade882ccfb887761515a251c22476' \
                         '1bef7207fa489e398041787cfbd155f1034a207d517f06bc76a044262484f82f0c6a887f776b1dce837408999d8' \
                         '8dd33a96c7f80e23719e77a11075d337bf9cc47d7dbf98e341b81c23f165dd15ccfd2973ab'

TEST_MD5 = hashlib.md5(b'test', usedforsecurity=False).hexdigest()
TEST_SHA1 = hashlib.sha1(b'test', usedforsecurity=False).hexdigest()
TEST_SHA256 = hashlib.sha256(b'test').hexdigest()
TEST_SHA384 = hashlib.sha384(b'test').hexdigest()
TEST_SHA512 = hashlib.sha512(b'test').hexdigest()

class CryptoModelTest(s_t_utils.SynTest):

    async def test_model_crypto_keys(self):

        async with self.getTestCore() as core:
            opts = {
                'vars': {
                    'sha1': TEST_SHA1,
                    'sha256': TEST_SHA256,
                }
            }
            nodes = await core.nodes('''
                [ crypto:key:base=*
                    :bits=2048
                    :algorithm=rsa
                    :public:hashes=(
                        {[crypto:hash:sha1=$sha1]},
                        {[crypto:hash:sha256=$sha256]},
                        {[crypto:hash:sha1=$sha1]},
                    )
                    :private:hashes=(
                        {[crypto:hash:sha1=$sha1]},
                    )
                    :seen=2022
                ]
            ''', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'bits', 2048)
            self.propeq(nodes[0], 'algorithm', 'rsa')
            self.len(2, nodes[0].get('public:hashes'))
            self.len(1, nodes[0].get('private:hashes'))
            self.nn(nodes[0].get('seen'))

            self.len(1, await core.nodes('crypto:key:base -> crypto:algorithm'))
            self.len(1, await core.nodes('crypto:key:base :public:hashes -> crypto:hash:sha1'))
            self.len(1, await core.nodes('crypto:key:base :public:hashes -> crypto:hash:sha256'))
            self.len(1, await core.nodes('crypto:key:base :private:hashes -> crypto:hash:sha1'))

            nodes = await core.nodes('''
                [ crypto:key:secret=*
                    :mode=CBC
                    :iv=AAAA
                    :value=BBBB
                    :algorithm=aes256
                    :seed:passwd=s3cret
                    :seed:algorithm=pbkdf2
                    +(decrypts)> {[ file:bytes=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'mode', 'cbc')
            self.propeq(nodes[0], 'algorithm', 'aes256')
            self.propeq(nodes[0], 'seed:passwd', 's3cret')
            self.propeq(nodes[0], 'seed:algorithm', 'pbkdf2')
            self.propeq(nodes[0], 'iv', 'aaaa')
            self.propeq(nodes[0], 'value', 'bbbb')

            self.len(2, await core.nodes('crypto:key:secret -> crypto:algorithm'))
            self.len(1, await core.nodes('crypto:key:secret -(decrypts)> file:bytes'))

            nodes = await core.nodes('''
                [ crypto:key:rsa=*
                    :bits=2048
                    :algorithm=rsa
                    :public:modulus=AAAA
                    :public:exponent=CCCC
                    :private:exponent=BB:BB
                    :private:coefficient=DDDD
                    :private:primes = {[ crypto:key:rsa:prime=({"value": "aaaa", "exponent": "bbbb"}) ]}
                    :public:hashes = { crypto:hash:sha1=$sha1 }
                    :private:hashes = { crypto:hash:sha256=$sha256 }
                ]
            ''', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'bits', 2048)
            self.propeq(nodes[0], 'algorithm', 'rsa')
            self.propeq(nodes[0], 'public:modulus', 'aaaa')
            self.propeq(nodes[0], 'public:exponent', 'cccc')
            self.propeq(nodes[0], 'private:exponent', 'bbbb')
            self.propeq(nodes[0], 'private:coefficient', 'dddd')
            self.propeq(nodes[0], 'public:hashes', [('crypto:hash:sha1', TEST_SHA1)])
            self.propeq(nodes[0], 'private:hashes', [('crypto:hash:sha256', TEST_SHA256)])

            self.len(1, await core.nodes('crypto:key:rsa -> crypto:algorithm'))
            self.len(1, await core.nodes('crypto:key:rsa -> crypto:key:rsa:prime'))

            nodes = await core.nodes('''
                [ crypto:key:dsa=*
                    :algorithm=dsa
                    :public=aaaa
                    :private=bbbb

                    :public:p=cccc
                    :public:q=dddd
                    :public:g=eeee

                    :public:hashes = { crypto:hash:sha1=$sha1 }
                    :private:hashes = { crypto:hash:sha256=$sha256 }
                ]
            ''', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'algorithm', 'dsa')
            self.propeq(nodes[0], 'public', 'aaaa')
            self.propeq(nodes[0], 'private', 'bbbb')
            self.propeq(nodes[0], 'public:p', 'cccc')
            self.propeq(nodes[0], 'public:q', 'dddd')
            self.propeq(nodes[0], 'public:g', 'eeee')
            self.propeq(nodes[0], 'public:hashes', [('crypto:hash:sha1', TEST_SHA1)])
            self.propeq(nodes[0], 'private:hashes', [('crypto:hash:sha256', TEST_SHA256)])

            self.len(1, await core.nodes('crypto:key:dsa -> crypto:algorithm'))

            nodes = await core.nodes('''
                [ crypto:key:ecdsa=*
                    :algorithm=ecdsa
                    :curve=p-256
                    :private=ffff
                    :public=aaaa
                    :public:p=aaab
                    :public:a=aaac
                    :public:b=aaad
                    :public:gx=aaae
                    :public:gy=aaaf
                    :public:n=aaba
                    :public:h=aaca
                    :public:x=aada
                    :public:y=aaea
                    :public:hashes={crypto:hash:sha1=$sha1}
                    :private:hashes={ crypto:hash:sha256=$sha256}
                ]
            ''', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'algorithm', 'ecdsa')
            self.propeq(nodes[0], 'private', 'ffff')
            self.propeq(nodes[0], 'public', 'aaaa')
            self.propeq(nodes[0], 'public:p', 'aaab')
            self.propeq(nodes[0], 'public:a', 'aaac')
            self.propeq(nodes[0], 'public:b', 'aaad')
            self.propeq(nodes[0], 'public:gx', 'aaae')
            self.propeq(nodes[0], 'public:gy', 'aaaf')
            self.propeq(nodes[0], 'public:n', 'aaba')
            self.propeq(nodes[0], 'public:h', 'aaca')
            self.propeq(nodes[0], 'public:x', 'aada')
            self.propeq(nodes[0], 'public:y', 'aaea')
            self.propeq(nodes[0], 'public:hashes', [('crypto:hash:sha1', TEST_SHA1)])
            self.propeq(nodes[0], 'private:hashes', [('crypto:hash:sha256', TEST_SHA256)])

    async def test_model_crypto_currency(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ crypto:currency:client=(1.2.3.4, (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)) ]')
            self.len(1, nodes)

            nodes = await core.nodes('''
                crypto:currency:address=btc/1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
                [ :seed={[ crypto:key:secret=(asdf,) ]} ]
            ''')
            self.propeq(nodes[0], 'seed', ('crypto:key:secret', '91a14b40da052cb388bf6b6d7723adee'))

            nodes = await core.nodes('inet:client=1.2.3.4 -> crypto:currency:client -> crypto:currency:address')
            self.propeq(nodes[0], 'coin', 'btc')
            self.propeq(nodes[0], 'iden', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')

            # these would explode if the model was wrong
            self.len(1, await core.nodes('crypto:currency:address [ :desc="woot woot" :contact=(entity:contact, *) ] -> entity:contact'))
            self.len(1, await core.nodes('crypto:currency:address:iden=1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.len(1, await core.nodes('crypto:currency:address:coin=btc'))
            self.len(1, await core.nodes('crypto:currency:client:inetaddr=1.2.3.4'))

            opts = {'vars': {
                'input': hashlib.sha256(b'asdf').hexdigest(),
                'output': hashlib.sha256(b'qwer').hexdigest(),
            }}

            payors = await core.nodes('[ crypto:payment:input=* :transaction=(t1,) :address=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2) :value=30 ]')
            self.propeq(payors[0], 'value', '30')
            self.propeq(payors[0], 'address', ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))

            payees = await core.nodes('[ crypto:payment:output=* :transaction=(t1,) :address=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2) :value=30 ]')
            self.propeq(payees[0], 'value', '30')
            self.propeq(payees[0], 'address', ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))

            payor = payors[0].ndef[1]
            payee = payees[0].ndef[1]

            nodes = await core.nodes('''
                [
                    crypto:currency:transaction=(t1,)
                        :hash=0x01020304
                        :desc="Woot Woot"
                        :block=(BTC, 998877)
                        :success=1
                        :status:code=10
                        :status:message=success
                        :to = (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :from = (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :fee = 0.0001
                        :value = 30
                        :time = 20211031
                        :eth:gasused = 10
                        :eth:gaslimit = 20
                        :eth:gasprice = 0.001
                        :contract:input = {[ file:bytes=({"sha256": $input}) ]}
                        :contract:output = {[ file:bytes=({"sha256": $output}) ]}
                ]
            ''', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'hash', '01020304')
            self.propeq(node, 'desc', 'Woot Woot')
            self.propeq(node, 'block', ('btc', 998877))
            self.propeq(node, 'block:coin', 'btc')
            self.propeq(node, 'block:offset', 998877)
            self.propeq(node, 'success', True)
            self.propeq(node, 'status:code', 10)
            self.propeq(node, 'status:message', 'success')
            self.propeq(node, 'to', ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.propeq(node, 'from', ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.propeq(node, 'fee', '0.0001')
            self.propeq(node, 'value', '30')
            self.propeq(node, 'time', 1635638400000000)
            self.propeq(node, 'eth:gasused', 10)
            self.propeq(node, 'eth:gaslimit', 20)
            self.propeq(node, 'eth:gasprice', '0.001')
            self.propeq(node, 'contract:input', 'c7b0fb6229283d0f30a360f8b81d63e5')
            self.propeq(node, 'contract:output', '074ce17fabf0f083843f83246533deb3')

            q = 'crypto:currency:transaction=(t1,) | tee { -> crypto:payment:input } { -> crypto:payment:output }'
            nodes = await core.nodes(q)
            self.eq({n.ndef[1] for n in nodes}, {payor, payee})

            nodes = await core.nodes('''
                [
                    crypto:currency:block=(btc, 12345)
                        :hash=0x01020304
                        :minedby = (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :time=20211130
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'coin', 'btc')
            self.propeq(node, 'offset', 12345)
            self.propeq(node, 'hash', '01020304')
            self.propeq(node, 'time', 1638230400000000)

            nodes = await core.nodes('''
                [
                    crypto:smart:contract=*
                        :transaction=*
                        :bytecode={[ file:bytes=({"sha256": $input}) ]}
                        :address = (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :token:name=Foo
                        :token:symbol=Bar
                        :token:totalsupply=300
                ]''', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('transaction'))
            self.propeq(node, 'bytecode', 'c7b0fb6229283d0f30a360f8b81d63e5')
            self.propeq(node, 'address', ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.propeq(node, 'token:name', 'Foo')
            self.propeq(node, 'token:symbol', 'Bar')
            self.propeq(node, 'token:totalsupply', '300')

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:transfertoken=*
                        :token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :to=eth/bbbb
                        :from=eth/aaaa
                        :transaction=*
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('token'))
            self.nn(node.get('transaction'))
            self.propeq(node, 'to', ('eth', 'bbbb'))
            self.propeq(node, 'from', ('eth', 'aaaa'))
            self.len(1, await core.nodes('crypto:smart:effect:transfertoken -> crypto:smart:token'))
            self.len(1, await core.nodes('crypto:smart:effect:transfertoken -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:transfertokens=*
                        :to=eth/bbbb
                        :from=eth/aaaa
                        :amount=20
                        :transaction=*
                        :contract=*
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('transaction'))
            self.nn(node.get('contract'))
            self.propeq(node, 'to', ('eth', 'bbbb'))
            self.propeq(node, 'from', ('eth', 'aaaa'))
            self.propeq(node, 'amount', '20')
            self.len(1, await core.nodes('crypto:smart:effect:transfertokens -> crypto:smart:contract'))
            self.len(1, await core.nodes('crypto:smart:effect:transfertokens -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:edittokensupply=*
                        :amount=20
                        :contract=*
                        :transaction=*
                        :totalsupply=1020
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('contract'))
            self.nn(node.get('transaction'))
            self.propeq(node, 'amount', '20')
            self.propeq(node, 'totalsupply', '1020')
            self.len(1, await core.nodes('crypto:smart:effect:edittokensupply -> crypto:smart:contract'))
            self.len(1, await core.nodes('crypto:smart:effect:edittokensupply -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:minttoken=*
                        :index=0
                        :token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :transaction=*
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'index', 0)
            self.nn(node.get('token'))
            self.nn(node.get('transaction'))
            self.len(1, await core.nodes('crypto:smart:effect:minttoken -> crypto:smart:token'))
            self.len(1, await core.nodes('crypto:smart:effect:minttoken -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:burntoken=*
                        :index=0
                        :token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :transaction=*
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'index', 0)
            self.nn(node.get('token'))
            self.nn(node.get('transaction'))
            self.len(1, await core.nodes('crypto:smart:effect:burntoken -> crypto:smart:token'))
            self.len(1, await core.nodes('crypto:smart:effect:burntoken -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:proxytoken=*
                        :index=0
                        :token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :transaction=*
                        :owner=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :proxy=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'index', 0)
            self.nn(node.get('token'))
            self.nn(node.get('owner'))
            self.nn(node.get('proxy'))
            self.len(1, await core.nodes('crypto:smart:effect:minttoken -> crypto:smart:token'))
            self.len(1, await core.nodes('crypto:smart:effect:minttoken -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:proxytokenall=*
                        :index=0
                        :transaction=*
                        :contract=*
                        :owner=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :proxy=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :approval=$lib.true
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'index', 0)
            self.nn(node.get('owner'))
            self.nn(node.get('proxy'))
            self.nn(node.get('contract'))
            self.true(node.get('approval'))
            self.len(2, await core.nodes('crypto:smart:effect:proxytokenall -> crypto:currency:address'))
            self.len(1, await core.nodes('crypto:smart:effect:proxytokenall -> crypto:currency:transaction'))
            self.len(1, await core.nodes('crypto:smart:effect:proxytokenall -> crypto:smart:contract'))

            nodes = await core.nodes('''
                [
                    crypto:smart:effect:proxytokens=*
                        :index=0
                        :transaction=*
                        :contract=*
                        :owner=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :proxy=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :amount=0xff
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'index', 0)
            self.nn(node.get('owner'))
            self.nn(node.get('proxy'))
            self.nn(node.get('contract'))
            self.propeq(node, 'amount', 'ff')
            self.len(2, await core.nodes('crypto:smart:effect:proxytokens -> crypto:currency:address'))
            self.len(1, await core.nodes('crypto:smart:effect:proxytokens -> crypto:currency:transaction'))
            self.len(1, await core.nodes('crypto:smart:effect:proxytokens -> crypto:smart:contract'))

            nodes = await core.nodes('''
                [
                    crypto:smart:token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :owner=eth/aaaa
                        :nft:url = https://coin.vertex.link/nfts/30
                        :nft:meta = ({'name':'WootWoot'})
                        :nft:meta:name = WootWoot
                        :nft:meta:description = LoLoL
                        :nft:meta:image = https://vertex.link/favicon.ico
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('2bdea834252a220b61aadf592cc0de66', '30'), node.ndef[1])
            self.propeq(node, 'contract', '2bdea834252a220b61aadf592cc0de66')
            self.propeq(node, 'tokenid', '30')
            self.propeq(node, 'owner', ('eth', 'aaaa'))
            self.propeq(node, 'nft:url', 'https://coin.vertex.link/nfts/30')
            self.propeq(node, 'nft:meta', {'name': 'WootWoot'})
            self.propeq(node, 'nft:meta:name', 'wootwoot')
            self.propeq(node, 'nft:meta:description', 'LoLoL')
            self.propeq(node, 'nft:meta:image', 'https://vertex.link/favicon.ico')

            nodes = await core.nodes('''
                [ crypto:currency:transaction=*
                    :value = '1e-24'
                ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'value', '0.000000000000000000000001')

            nodes = await core.nodes('''
                [ crypto:currency:transaction=*
                    :value = 0.000000000000000000000002
                ]''')
            self.len(1, await core.nodes('crypto:currency:transaction:value=1e-24'))
            self.len(1, await core.nodes('crypto:currency:transaction:value=0.000000000000000000000001'))

            huge = '730750818665451459101841.000000000000000000000002'
            huge2 = '730750818665451459101841.0000000000000000000000015'
            huge3 = '730750818665451459101841.000000000000000000000001'

            self.len(1, await core.nodes(f'[ crypto:currency:transaction=* :value={huge} ]'))
            self.len(1, await core.nodes(f'[ crypto:currency:transaction=* :value={huge2} ]'))
            self.len(2, await core.nodes(f'crypto:currency:transaction:value={huge}'))

            self.len(1, await core.nodes(f'[ crypto:currency:transaction=* :value={huge3} ]'))
            self.len(2, await core.nodes(f'crypto:currency:transaction:value={huge}'))
            self.len(2, await core.nodes(f'crypto:currency:transaction:value={huge2}'))
            self.len(1, await core.nodes(f'crypto:currency:transaction:value={huge3}'))

    async def test_forms_crypto_simple(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex

            nodes = await core.nodes('[crypto:hash:md5=$valu]', opts={'vars': {'valu': TEST_MD5.upper()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('crypto:hash:md5', TEST_MD5))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[crypto:hash:md5=$valu]', opts={'vars': {'valu': TEST_SHA1}})

            nodes = await core.nodes('[crypto:hash:sha1=$valu]', opts={'vars': {'valu': TEST_SHA1.upper()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('crypto:hash:sha1', TEST_SHA1))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[crypto:hash:sha1=$valu]', opts={'vars': {'valu': TEST_SHA256}})

            nodes = await core.nodes('[crypto:hash:sha256=$valu]', opts={'vars': {'valu': TEST_SHA256.upper()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('crypto:hash:sha256', TEST_SHA256))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[crypto:hash:sha256=$valu]', opts={'vars': {'valu': TEST_SHA384}})

            nodes = await core.nodes('[crypto:hash:sha384=$valu]', opts={'vars': {'valu': TEST_SHA384.upper()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('crypto:hash:sha384', TEST_SHA384))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[crypto:hash:sha384=$valu]', opts={'vars': {'valu': TEST_SHA512}})

            nodes = await core.nodes('[crypto:hash:sha512=$valu]', opts={'vars': {'valu': TEST_SHA512.upper()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('crypto:hash:sha512', TEST_SHA512))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[crypto:hash:sha512=$valu]', opts={'vars': {'valu': TEST_MD5}})

    async def test_model_x509(self):

        async with self.getTestCore() as core:

            crl = s_common.guid()
            cert = s_common.guid()
            icert = s_common.guid()
            fileguid = s_common.guid()

            nodes = await core.nodes('''
                [ crypto:x509:cert=$icert
                    :subject="CN=issuer.link"
                    :subject:cn="  Issuer.Link  "
                    :issuer:cert=$icert
                    :selfsigned=$lib.true
                    :seen=(2022, 2023)
                ]
            ''', opts={'vars': {'icert': icert}})
            self.eq(nodes[0].ndef, ('crypto:x509:cert', icert))
            self.propeq(nodes[0], 'subject', "CN=issuer.link")
            self.propeq(nodes[0], 'subject:cn', "Issuer.Link")
            self.propeq(nodes[0], 'issuer:cert', icert)
            self.propeq(nodes[0], 'selfsigned', True)
            self.eq(('2022-01-01T00:00:00Z', '2023-01-01T00:00:00Z'), nodes[0].repr('seen'))

            nodes = await core.nodes('''
                [ crypto:x509:cert=$cert

                    :subject="CN=vertex.link"
                    :issuer="DN FOO THING"
                    :issuer:cert=$icert

                    :serial=0000000000000000000000000000000000003039
                    :version=v3

                    :validity:notafter=2019
                    :validity:notbefore=2015

                    :md5=$md5
                    :sha1=$sha1
                    :sha256=$sha256

                    :algo=1.2.840.113549.1.1.11
                    :signature=ff00ff00

                    :ext:sans=((dns, vertex.link), (dns, "*.vertex.link"))
                    :ext:crls = ((dns, http://vertex.link/crls),)
                    :crl:urls = ("http://vertex.link/crls",)

                    :identities:urls=(http://woot.com/1, http://woot.com/2)
                    :identities:fqdns=(vertex.link, woot.com)
                    :identities:ips=(1.2.3.4, 5.5.5.5, ff::11, ff::aa)
                    :identities:emails=(visi@vertex.link, v@vtx.lk)
                ]
            ''', opts={'vars': {'icert': icert, 'cert': cert, 'md5': TEST_MD5, 'sha1': TEST_SHA1, 'sha256': TEST_SHA256}})

            self.eq(nodes[0].ndef, ('crypto:x509:cert', cert))
            self.propeq(nodes[0], 'subject', "CN=vertex.link")
            self.propeq(nodes[0], 'issuer', "DN FOO THING")
            self.propeq(nodes[0], 'issuer:cert', icert)
            self.propeq(nodes[0], 'serial', "0000000000000000000000000000000000003039")
            self.propeq(nodes[0], 'version', 2)

            self.propeq(nodes[0], 'validity:notafter', 1546300800000000)
            self.propeq(nodes[0], 'validity:notbefore', 1420070400000000)

            self.propeq(nodes[0], 'md5', TEST_MD5)
            self.propeq(nodes[0], 'sha1', TEST_SHA1)
            self.propeq(nodes[0], 'sha256', TEST_SHA256)

            self.propeq(nodes[0], 'algo', '1.2.840.113549.1.1.11')
            self.propeq(nodes[0], 'signature', 'ff00ff00')
            self.propeq(nodes[0], 'ext:crls', (('dns', 'http://vertex.link/crls'),))
            self.propeq(nodes[0], 'crl:urls', ('http://vertex.link/crls',))
            self.propeq(nodes[0], 'ext:sans', (('dns', '*.vertex.link'), ('dns', 'vertex.link')))
            self.propeq(nodes[0], 'identities:urls', ('http://woot.com/1', 'http://woot.com/2'))
            self.propeq(nodes[0], 'identities:fqdns', ('vertex.link', 'woot.com'))

            ip3 = (6, 0xff0000000000000000000000000011)
            ip4 = (6, 0xff00000000000000000000000000aa)
            self.propeq(nodes[0], 'identities:ips', ((4, 0x01020304), (4, 0x05050505), ip3, ip4))

            nodes = await core.nodes('[ crypto:x509:cert=* :serial=(1234) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'serial', '00000000000000000000000000000000000004d2')

            nodes = await core.nodes('[ crypto:x509:cert=* :serial=(-1234) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'serial', 'fffffffffffffffffffffffffffffffffffffb2e')

            nodes = await core.nodes('''
                [
                    crypto:x509:crl=$crl
                        :url=http://vertex.link/crls
                        :file=*
                ]
            ''', opts={'vars': {'crl': crl}})

            self.eq(nodes[0].ndef, ('crypto:x509:crl', crl))
            self.nn(nodes[0].get('file'))
            self.propeq(nodes[0], 'url', 'http://vertex.link/crls')

            opts = {'vars': {'cert': cert, 'file': fileguid}}
            nodes = await core.nodes('[ crypto:x509:signedfile = ($cert, $file) ]', opts=opts)

            self.eq(nodes[0].ndef, ('crypto:x509:signedfile', (cert, fileguid)))
            self.propeq(nodes[0], 'cert', cert)
            self.nn(nodes[0].get('file'), fileguid)

            opts = {'vars': {'cert': cert, 'crl': crl}}
            nodes = await core.nodes('[ crypto:x509:revoked = ($crl, $cert) ]', opts=opts)

            self.eq(nodes[0].ndef, ('crypto:x509:revoked', (crl, cert)))
            self.propeq(nodes[0], 'crl', crl)
            self.nn(nodes[0].get('cert'), cert)

            # odd-length serials
            serials = [
                '1' * 7,
                '2' * 9,
                '3' * 15,
                '4' * 17,
                '5' * 31,
                '6' * 33,
                '7' * 39,
            ]

            for serial in serials:
                msgs = await core.stormlist(f'[crypto:x509:cert=* :serial={serial}]')
                self.stormHasNoErr(msgs)

    async def test_crypto_salthash(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'md5': TEST_MD5}}
            nodes = await core.nodes('''
                [ crypto:salthash=*
                    :salt=4141
                    :hash={[ crypto:hash:md5=$md5 ]}
                    :value=(auth:passwd, woot)
                ]
            ''', opts=opts)

            self.len(1, nodes)
            self.propeq(nodes[0], 'salt', '4141')
            self.propeq(nodes[0], 'hash', ('crypto:hash:md5', '098f6bcd4621d373cade4e832627b4f6'))
            self.propeq(nodes[0], 'value', ('auth:passwd', 'woot'))

            self.len(1, await core.nodes('crypto:salthash -> auth:passwd'))
            self.len(1, await core.nodes('crypto:salthash -> crypto:hash:md5'))
