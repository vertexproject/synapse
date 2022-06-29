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

TEST_MD5 = hashlib.md5(b'test').hexdigest()
TEST_SHA1 = hashlib.sha1(b'test').hexdigest()
TEST_SHA256 = hashlib.sha256(b'test').hexdigest()
TEST_SHA384 = hashlib.sha384(b'test').hexdigest()
TEST_SHA512 = hashlib.sha512(b'test').hexdigest()

class CryptoModelTest(s_t_utils.SynTest):

    async def test_model_crypto_currency(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ crypto:currency:client=(1.2.3.4, (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)) ]')
            self.len(1, nodes)

            nodes = await core.nodes('''
                crypto:currency:address=btc/1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
                [ :seed={
                    [ crypto:key=* :algorithm=aes256 :private=00000000 :public=ffffffff :seed:passwd=s3cret :seed:algorithm=pbkdf2 ]
                }]
            ''')

            self.len(1, await core.nodes('crypto:algorithm=aes256'))
            self.len(1, await core.nodes('crypto:key:algorithm=aes256 +:private=00000000 +:public=ffffffff +:seed:algorithm=pbkdf2 +:seed:passwd=s3cret'))
            self.len(1, await core.nodes('inet:passwd=s3cret -> crypto:key -> crypto:currency:address'))

            nodes = await core.nodes('inet:client=1.2.3.4 -> crypto:currency:client -> crypto:currency:address')
            self.eq(nodes[0].get('coin'), 'btc')
            self.eq(nodes[0].get('iden'), '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')

            nodes = await core.nodes('''
                [
                    econ:acct:payment="*"
                        :from:coinaddr=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :to:coinaddr=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                ]
            ''')

            # these would explode if the model was wrong
            self.len(1, await core.nodes('crypto:currency:address [ :desc="woot woot" :contact="*" ] -> ps:contact'))
            self.len(1, await core.nodes('crypto:currency:address:iden=1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.len(1, await core.nodes('crypto:currency:address:coin=btc'))
            self.len(1, await core.nodes('crypto:currency:client:inetaddr=1.2.3.4'))

            opts = {'vars': {
                'input': hashlib.sha256(b'asdf').hexdigest(),
                'output': hashlib.sha256(b'qwer').hexdigest(),
            }}

            payors = await core.nodes('[ crypto:payment:input=* :transaction=(t1,) :address=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2) :value=30 ]')
            self.eq(payors[0].get('value'), '30')
            self.eq(payors[0].get('address'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))

            payees = await core.nodes('[ crypto:payment:output=* :transaction=(t1,) :address=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2) :value=30 ]')
            self.eq(payees[0].get('value'), '30')
            self.eq(payees[0].get('address'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))

            payor = payors[0].ndef[1]
            payee = payees[0].ndef[1]

            nodes = await core.nodes(f'''
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
                        :contract:input = $input
                        :contract:output = $output
                ]
            ''', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('hash'), '01020304')
            self.eq(node.get('desc'), 'Woot Woot')
            self.eq(node.get('block'), ('btc', 998877))
            self.eq(node.get('block:coin'), 'btc')
            self.eq(node.get('block:offset'), 998877)
            self.eq(node.get('success'), True)
            self.eq(node.get('status:code'), 10)
            self.eq(node.get('status:message'), 'success')
            self.eq(node.get('to'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.eq(node.get('from'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.eq(node.get('fee'), '0.0001')
            self.eq(node.get('value'), '30')
            self.eq(node.get('time'), 1635638400000)
            self.eq(node.get('eth:gasused'), 10)
            self.eq(node.get('eth:gaslimit'), 20)
            self.eq(node.get('eth:gasprice'), '0.001')
            self.eq(node.get('contract:input'), 'sha256:f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b')
            self.eq(node.get('contract:output'), 'sha256:f6f2ea8f45d8a057c9566a33f99474da2e5c6a6604d736121650e2730c6fb0a3')

            with self.raises(s_exc.IsDeprLocked):
                await node.set('inputs', (payor,))
            with self.raises(s_exc.IsDeprLocked):
                await node.set('outputs', (payee,))

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
            self.eq(node.get('coin'), 'btc')
            self.eq(node.get('offset'), 12345)
            self.eq(node.get('hash'), '01020304')
            self.eq(node.get('time'), 1638230400000)

            nodes = await core.nodes('''
                [
                    crypto:smart:contract=*
                        :transaction=*
                        :bytecode=$input
                        :address = (btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)
                        :token:name=Foo
                        :token:symbol=Bar
                        :token:totalsupply=300
                ]''', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('transaction'))
            self.eq(node.get('bytecode'), 'sha256:f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b')
            self.eq(node.get('address'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
            self.eq(node.get('token:name'), 'Foo')
            self.eq(node.get('token:symbol'), 'Bar')
            self.eq(node.get('token:totalsupply'), '300')

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
            self.eq(node.get('to'), ('eth', 'bbbb'))
            self.eq(node.get('from'), ('eth', 'aaaa'))
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
            self.eq(node.get('to'), ('eth', 'bbbb'))
            self.eq(node.get('from'), ('eth', 'aaaa'))
            self.eq(node.get('amount'), '20')
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
            self.eq(node.get('amount'), '20')
            self.eq(node.get('totalsupply'), '1020')
            self.len(1, await core.nodes('crypto:smart:effect:edittokensupply -> crypto:smart:contract'))
            self.len(1, await core.nodes('crypto:smart:effect:edittokensupply -> crypto:currency:transaction'))

            nodes = await core.nodes('''
                [
                    crypto:smart:token=(2bdea834252a220b61aadf592cc0de66, 30)
                        :owner=eth/aaaa
                        :nft:url = https://coin.vertex.link/nfts/30
                        :nft:meta = $lib.dict(name=WootWoot)
                        :nft:meta:name = WootWoot
                        :nft:meta:description = LoLoL
                        :nft:meta:image = https://vertex.link/favicon.ico
                ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('2bdea834252a220b61aadf592cc0de66', '30'), node.ndef[1])
            self.eq('2bdea834252a220b61aadf592cc0de66', node.get('contract'))
            self.eq('30', node.get('tokenid'))
            self.eq(('eth', 'aaaa'), node.get('owner'))
            self.eq('https://coin.vertex.link/nfts/30', node.get('nft:url'))
            self.eq({'name': 'WootWoot'}, node.get('nft:meta'))
            self.eq('WootWoot', node.get('nft:meta:name'))
            self.eq('LoLoL', node.get('nft:meta:description'))
            self.eq('https://vertex.link/favicon.ico', node.get('nft:meta:image'))

            nodes = await core.nodes('''
                [ crypto:currency:transaction=*
                    :value = '1e-24'
                ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('value'), '0.000000000000000000000001')

            nodes = await core.nodes('''
                [ crypto:currency:transaction=*
                    :value = 0.000000000000000000000002
                ]''')
            self.len(1, await core.nodes('crypto:currency:transaction:value=1e-24'))
            self.len(1, await core.nodes('crypto:currency:transaction:value=0.000000000000000000000001'))

            huge = '730750818665451459101841.00000000000000000002'
            huge2 = '730750818665451459101841.000000000000000000015'

            self.len(1, await core.nodes(f'[ crypto:currency:transaction=* :value={huge} ]'))
            self.len(1, await core.nodes(f'[ crypto:currency:transaction=* :value={huge2} ]'))
            self.len(2, await core.nodes(f'crypto:currency:transaction:value={huge}'))

    async def test_norm_lm_ntlm(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex
            lm = core.model.type('hash:lm')
            valu, subs = lm.norm(TEST_MD5.upper())
            self.eq(valu, TEST_MD5)
            self.eq(subs, {})
            self.raises(s_exc.BadTypeValu, lm.norm, TEST_SHA256)

            ntlm = core.model.type('hash:ntlm')
            valu, subs = lm.norm(TEST_MD5.upper())
            self.eq(valu, TEST_MD5)
            self.eq(subs, {})
            self.raises(s_exc.BadTypeValu, ntlm.norm, TEST_SHA256)

    async def test_forms_crypto_simple(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex
            async with await core.snap() as snap:
                # md5
                node = await snap.addNode('hash:md5', TEST_MD5.upper())
                self.eq(node.ndef, ('hash:md5', TEST_MD5))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('hash:md5', TEST_SHA1))
                # sha1
                node = await snap.addNode('hash:sha1', TEST_SHA1.upper())
                self.eq(node.ndef, ('hash:sha1', TEST_SHA1))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('hash:sha1', TEST_SHA256))
                # sha256
                node = await snap.addNode('hash:sha256', TEST_SHA256.upper())
                self.eq(node.ndef, ('hash:sha256', TEST_SHA256))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('hash:sha256', TEST_SHA384))
                # sha384
                node = await snap.addNode('hash:sha384', TEST_SHA384.upper())
                self.eq(node.ndef, ('hash:sha384', TEST_SHA384))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('hash:sha384', TEST_SHA512))
                # sha512
                node = await snap.addNode('hash:sha512', TEST_SHA512.upper())
                self.eq(node.ndef, ('hash:sha512', TEST_SHA512))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('hash:sha512', TEST_MD5))

    async def test_form_rsakey(self):
        prop = 'rsa:key'
        props = {
            'bits': BITS,
            'priv:exp': HEXSTR_PRIVATE_EXPONENT,
            'priv:p': HEXSTR_PRIVATE_PRIME_P,
            'priv:q': HEXSTR_PRIVATE_PRIME_Q,
        }
        valu = (HEXSTR_MODULUS, HEXSTR_PUBLIC_EXPONENT)

        async with self.getTestCore() as core:  # type: s_cortex.Cortex

            async with await core.snap() as snap:

                node = await snap.addNode(prop, valu, props)

                self.eq(node.ndef[1], (HEXSTR_MODULUS, HEXSTR_PUBLIC_EXPONENT))

                self.eq(node.get('mod'), HEXSTR_MODULUS)
                self.eq(node.get('bits'), BITS)
                self.eq(node.get('pub:exp'), HEXSTR_PUBLIC_EXPONENT)
                self.eq(node.get('priv:exp'), HEXSTR_PRIVATE_EXPONENT)
                self.eq(node.get('priv:p'), HEXSTR_PRIVATE_PRIME_P)
                self.eq(node.get('priv:q'), HEXSTR_PRIVATE_PRIME_Q)

    async def test_model_x509(self):

        async with self.getTestCore() as core:

            crl = s_common.guid()
            cert = s_common.guid()
            icert = s_common.guid()
            fileguid = 'guid:' + s_common.guid()

            nodes = await core.nodes('''
                [ crypto:x509:cert=$icert
                    :subject="CN=issuer.link"
                    :issuer:cert=$icert
                    :selfsigned=$lib.true
                ]
            ''', opts={'vars': {'icert': icert}})
            self.eq(nodes[0].ndef, ('crypto:x509:cert', icert))
            self.eq(nodes[0].get('subject'), "CN=issuer.link")
            self.eq(nodes[0].get('issuer:cert'), icert)
            self.eq(nodes[0].get('selfsigned'), True)

            nodes = await core.nodes('''
                [ crypto:x509:cert=$cert

                    :subject="CN=vertex.link"
                    :issuer="DN FOO THING"
                    :issuer:cert=$icert

                    :serial=12345
                    :version=v3

                    :validity:notafter=2019
                    :validity:notbefore=2015

                    :md5=$md5
                    :sha1=$sha1
                    :sha256=$sha256

                    :algo=1.2.840.113549.1.1.11
                    :rsa:key=(ff00ff00, 100)
                    :signature=ff00ff00

                    :ext:sans=((dns, vertex.link), (dns, "*.vertex.link"))
                    :ext:crls = ((dns, http://vertex.link/crls),)
                    :crl:urls = ("http://vertex.link/crls",)

                    :identities:urls=(http://woot.com/1, http://woot.com/2)
                    :identities:fqdns=(vertex.link, woot.com)
                    :identities:ipv4s=(1.2.3.4, 5.5.5.5)
                    :identities:ipv6s=(ff::11, ff::aa)
                    :identities:emails=(visi@vertex.link, v@vtx.lk)
                ]
            ''', opts={'vars': {'icert': icert, 'cert': cert, 'md5': TEST_MD5, 'sha1': TEST_SHA1, 'sha256': TEST_SHA256}})

            self.eq(nodes[0].ndef, ('crypto:x509:cert', cert))
            self.eq(nodes[0].get('subject'), "CN=vertex.link")
            self.eq(nodes[0].get('issuer'), "DN FOO THING")
            self.eq(nodes[0].get('issuer:cert'), icert)
            self.eq(nodes[0].get('serial'), "12345")
            self.eq(nodes[0].get('version'), 2)

            self.eq(nodes[0].get('validity:notafter'), 1546300800000)
            self.eq(nodes[0].get('validity:notbefore'), 1420070400000)

            self.eq(nodes[0].get('md5'), TEST_MD5)
            self.eq(nodes[0].get('sha1'), TEST_SHA1)
            self.eq(nodes[0].get('sha256'), TEST_SHA256)

            self.eq(nodes[0].get('algo'), '1.2.840.113549.1.1.11')
            self.eq(nodes[0].get('rsa:key'), ('ff00ff00', 100))
            self.eq(nodes[0].get('signature'), 'ff00ff00')
            self.eq(nodes[0].get('ext:crls'), (('dns', 'http://vertex.link/crls'),))
            self.eq(nodes[0].get('crl:urls'), ('http://vertex.link/crls',))
            self.eq(nodes[0].get('ext:sans'), (('dns', '*.vertex.link'), ('dns', 'vertex.link')))
            self.eq(nodes[0].get('identities:urls'), ('http://woot.com/1', 'http://woot.com/2'))
            self.eq(nodes[0].get('identities:fqdns'), ('vertex.link', 'woot.com'))
            self.eq(nodes[0].get('identities:ipv4s'), (0x01020304, 0x05050505))
            self.eq(nodes[0].get('identities:ipv6s'), ('ff::11', 'ff::aa'))

            nodes = await core.nodes('''
                [
                    crypto:x509:crl=$crl
                        :url=http://vertex.link/crls
                        :file="*"
                ]
            ''', opts={'vars': {'crl': crl}})

            self.eq(nodes[0].ndef, ('crypto:x509:crl', crl))
            self.nn(nodes[0].get('file'))
            self.eq(nodes[0].get('url'), 'http://vertex.link/crls')

            opts = {'vars': {'cert': cert, 'file': fileguid}}
            nodes = await core.nodes('[ crypto:x509:signedfile = ($cert, $file) ]', opts=opts)

            self.eq(nodes[0].ndef, ('crypto:x509:signedfile', (cert, fileguid)))
            self.eq(nodes[0].get('cert'), cert)
            self.nn(nodes[0].get('file'), fileguid)

            opts = {'vars': {'cert': cert, 'crl': crl}}
            nodes = await core.nodes('[ crypto:x509:revoked = ($crl, $cert) ]', opts=opts)

            self.eq(nodes[0].ndef, ('crypto:x509:revoked', (crl, cert)))
            self.eq(nodes[0].get('crl'), crl)
            self.nn(nodes[0].get('cert'), cert)
