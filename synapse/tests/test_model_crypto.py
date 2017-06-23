import synapse.cortex as s_cortex

from synapse.tests.common import *


HEXSTR_FINGER = '4ea54f9cfc338ded2f58ecbd907e6432a329cebc'
FINGER= 0x4ea54f9cfc338ded2f58ecbd907e6432a329cebc

HEXSTR_KEYID = '907e6432a329cebc'
KEYID = 0x907e6432a329cebc

BITS = 2048
MODULUS = 21680073759901560171209957725353947845838657877489390985629011146485484841613254787012016412199394070769311374208089618561220933596407338770180192384317562523491504421019673615789668662137487867201848792175221628030748903758659512346089900598997888270904750957373405614508524979486643166681109379345160580296332322836921704829624843374764439692279358554558941230025781198901328474879152567953389671112502837567613909993840129753441530321638514598444958171485518879137004811038656035936398122093390552808567871935626042277760893618056402149399121098975363621174280972619512060731453783290243406423030552375052230477117
HEXSTR_MODULUS = 'abbd407f417fe8d6632aae1c6d09b271416bef9244e61f7c7c2856ddfde3ecf93cd50b3eaea5c9b8cb9bfb5a317bf50925ab500a06247ec2f3294891a8e62c317ee648f933ec1bf760a9d7e9a5ea4706b2a2c3f6376079114ddcc7a15d3fecf001458f22f0551802a25ef95cf464aabeb0514ea3849583bc09022730c44a2ff5f893fc6885add69c103d75114dd2f11436f617fbfb0af2978802aabf35483bbfcc470d50d6afb4283c1d06d2bf27efe9d7c09f226895633a46c3d77173bf0db8634299462b5f29629ad3b0470c76ddfd331ed0207d4dbd5fd44a2f66ca5f802ac0130e4a4bb2c149b5baa7a373188823ee21fe2950a76c818586919f7914453d'
PUBLIC_EXPONENT = 65537
HEXSTR_PUBLIC_EXPONENT = '10001'
PRIVATE_EXPONENT = 19908935091507935910766878035079064394252223126492576982286506520422599969830943022212554491896121784047323899994895364662251238943384391552951073718134547894338911005542319868457049133976538936963987760493787680848597910720774607191734874769206553699556901092018305233653761369004450092319898771337256804613522317422533116544949192149922930004965904101153270320899927630023151519164234033080401056920737409312210208519608126904153045420378101666974043300846024202376639976827675424610873439010403494045110511125497106688005087420608633713569510808521791875704919516380552984253009872506805233489422334428748712987077
HEXSTR_PRIVATE_EXPONENT = '9db58a80120f3b2b7d1f998a231b8f916fa985f4456f2a24f0033f5a56a7b35b61e0a695e65dfab3c7ceb2f0ad968e7bdaeac9f29a97730ce5add8a5627c14c3532c7880d88c8f56099f8ed65275a4c9e2cb93b70c3d7c904677639fac7962c537f5bfaf2f12859d0dacb7c403ee59da0922715bba0a6f5202d7c653833e39715f04664c2396c47bdf3f09f5486d8f6aea767ba011f1a5a10c8b57f079aea58abfd5e50ef20aa5e09b1082f6af98e806c9aeeb894148a7d82cd6e1443c6115eb567fba0eacf5b7178518b8ba312da6ace22238d1ed19f3e703652576a6152ba60d4d4c6bc75b3ee7c8efeadee0c5ed7c14bf2930a6c4f13137becf38912f49c5'
PRIVATE_PRIME_P = 156532994640717807361608570611796319305663234740664421762070081027284552113924902465098803666443018989500889191221784106739853246716130351638754811952418505918520952533734611708019313476414762006641033262124920543558854778066147079325885899480329140950654918462245144305556866163678471146913922858422171189943
HEXSTR_PRIVATE_PRIME_P = 'dee90ee63c12729a3fe7d38c581abf7e1c784ec0bd4bfdd1282286ea9996673942a24c7c98b31c6cd12db8ba96da785c4392569d7bfc2be9d9907c3b7fbf40d31891642952a0e5a23dfbe721a746588df9a246ea4936a1958f66fd3a32c08008a0f6ed9b516fa869fb08a57ef31c0ec217f173e489a2f8f111e25c25c961c2b7'
PRIVATE_PRIME_Q = 138501622674904590241979533901923672469392492154619678828180202352596319430957093632613282955184195992095035063297311252977898969555093667265836880501714630547665618115519694458795827169975578296162626726079027770594551438491027253477102905357276738700715758142905702644770884617741935638407118002466518037419
HEXSTR_PRIVATE_PRIME_Q = 'c53b9c8dfb3dda04d16c7f779a02b3b8c7b44bf876dc88ad562778eafaded9ade882ccfb887761515a251c224761bef7207fa489e398041787cfbd155f1034a207d517f06bc76a044262484f82f0c6a887f776b1dce837408999d88dd33a96c7f80e23719e77a11075d337bf9cc47d7dbf98e341b81c23f165dd15ccfd2973ab'
HEXSTR_RSA_KEY = 'abbd407f417fe8d6632aae1c6d09b271416bef9244e61f7c7c2856ddfde3ecf93cd50b3eaea5c9b8cb9bfb5a317bf50925ab500a06247ec2f3294891a8e62c317ee648f933ec1bf760a9d7e9a5ea4706b2a2c3f6376079114ddcc7a15d3fecf001458f22f0551802a25ef95cf464aabeb0514ea3849583bc09022730c44a2ff5f893fc6885add69c103d75114dd2f11436f617fbfb0af2978802aabf35483bbfcc470d50d6afb4283c1d06d2bf27efe9d7c09f226895633a46c3d77173bf0db8634299462b5f29629ad3b0470c76ddfd331ed0207d4dbd5fd44a2f66ca5f802ac0130e4a4bb2c149b5baa7a373188823ee21fe2950a76c818586919f7914453d/10001'
HEXSTR_RSA_SIG = '4eca252cd49dadef2ea3a84a20df7a8bcb97092305dd6ffdd94b092fa91a820e88613672e887ff276672bf5b2eb686121832a92c4c07d409d12e4e82128b3f93d6c5bb2c850e5cde9a1a161ffa832acd98e3e9a02de8368dda9f2f4e9592abaa89c86459081dcc8b1dbdafe501bcbce663491c43e275330f52f671e927f3c8e4'
RSA_SIG=0x4eca252cd49dadef2ea3a84a20df7a8bcb97092305dd6ffdd94b092fa91a820e88613672e887ff276672bf5b2eb686121832a92c4c07d409d12e4e82128b3f93d6c5bb2c850e5cde9a1a161ffa832acd98e3e9a02de8368dda9f2f4e9592abaa89c86459081dcc8b1dbdafe501bcbce663491c43e275330f52f671e927f3c8e4
CREATION_TS = 1488863050
STR_CREATION_TS = '2017-03-07 05:04:10'
EXPIRATION_TS = 1588863050
STR_EXPIRATION_TS = '2020-05-07 14:50:50'

# DSA/ELG test values taken from the following valid pgp key.
# Take heart, it has never been used to sign anything!

# -----BEGIN PGP PRIVATE KEY BLOCK-----
#
# lQNTBFi+P0oRCADEyeX4aoXa9ZmSiwPmZreobSzQ1vqmS88o9U9hg6UODU6sWRJz
# A1muxYiXX+xdmr+MSKYwuSzj47X4hSJEPCHupJF8atuPufN3XrenVQlz0eqxMbIA
# B1xV/lHkuK5TxQRhS0baThjc2GzcquMh0vyUuyFdgkSynRoCd6Z1uSKW8BXRrZZ2
# b0LaAbG0/bVbEbKVjzhXLlJ3+l3zYlEOzpzhZlJEmfSrQT5KJ+q7zEK+LXKS1vT/
# mxtut5BQPz9I1TJmROwie31Uqc5hanfOWuCGFaHy3yNGtQ7wXh0e3UFbvQKlUIlS
# j1tE3W54n3jIlihyCi9Ycp40WW7MLcZaknA/AQDrcZ3mGQdUrmKgItp/aL7+KDJ8
# vQKmh4y2eHafARGVRQgAohffJL1gcucDAzifDNTFKzvLvmWHN1QiIRST7U3q5uEH
# 13J+re9nhZY/UVijh+uvtzF5cEYlNirBD9Nt4+di0A2m8wEpJ5UqNgnhTovLvFmw
# s0ufNgRmZcq7KVmMvd2Kw2/lnLHIOTLgatgaWr5/6nSWs85wadW42dibOdNL1Kqz
# bzfoO+fAclsW8Lpg/RCF9563MukAkpXyroZ/ytBBWeBQXnG+kR5bsqO8sN6XDeuM
# MIsZWh3AmYjccRHe9JUNHn3zW3aNkJxlAdM+oQo6OEEXBpwTaYWlGRbOkTt6uojb
# TXwdFZ40d4Jwj3suv/CD2Xo1T7Fop4qHFG9hFWp67wf/c3oWnQW6u6V7kQXxet9n
# 0yv2E5VhlpiQ689ashvzjVPFA6FQBg9FSAeGhkFruVjVFuP0LkmWhTpd9Z7H/oAj
# rcSJkrxirvHgvXXx6H/CIKkqTVFmkmTYaK5zpSwbvqTancOAGQc3CgWXGts10+2S
# 14EXJgSfADOVZAcKSpwaLTtPPuVJXwTXfKy6MNfSMsIg0Usjdh6+djqiYMy2WIbO
# aqxAEKwV6rQQdLyI9o1tvcq3lhtkoqXoULGucbp4/nQqNMtQG8Rxmu6fRkG3Q2sn
# 7eVERCIc8sJxWtnzJxdR0wRor36vEzQmbclny/7dOHC3Ga/QxRKAL5cGSgVekWAp
# zQABAMBT9ogA3xUzSM21pd13uqRbjFiU6ivaCjCjlKITgcmHEJO0H3Rlc3R5ICh0
# ZXNldCkgPHRlc3R5QHRlc3QudGVzdD6IeQQTEQoAIQUCWL4/SgIbAwULCQgHAwUV
# CgkICwUWAgMBAAIeAQIXgAAKCRCQfmQyoynOvHiYAP9Takp+stXYeKDRslZqY2ET
# 3ApqwHz7F4Y6J3kQvybGhQEAlhwG3TL0rj0OoCctRQtltyDA78kiyB+PfJ97L5Br
# wjWdAj0EWL4/ShAIAJT0ThDecIqMl29tgAyVT5Ug5bLJ83z/erKF4rcXD7Q0yfQR
# 0eH1FwBV6nATggkztCZIXveeLcDMDX5SNA+qF14SS9RH6kDEHAFQTDbSSRnvPYew
# /ApsW+5/8lT6F1Jx/t0Zc89JzdQm9OypMSzYDvwFdgyzJ0OpdjzwlYfg73y9iANn
# q1At74QkBUt18Tqx6Ndg+P2e872rrvYiAQoEcB6n/jY7GN/TAM3jl6zQ/PKb0qIp
# 2CshGcBXah2BGCZhIARW7F3H0lnHyPv3NIxYFwi43rHQYmJhmQpVP3NEhiG+XN3M
# J4CirXg1mDIb1/4nkZ3QGXMngA0NHrnznXWINVsAAwYH/Asu4bZ1zGrgfEKKK+vH
# epGyfCniIM5+nRHSNe9B2sVyAkVvBKL9nhX62IafFmROdx4GqdG+jJejSVlUrLF1
# J6P8SjTl0LAoQde/ffel3kuRCWWlMTZeDWtxyeuQieOEUh6UUU0Ejvu9Jb+GI21m
# jA6z7k/EhT0eHhlMo2xWr8DxlLkOPEbPwQfAtOwc8c4aJ+shnKONLf3jRE5Jwe/P
# ypwIXe9JyTnvYZQovD3bBRVn9XUULayOqXQV0cTNtFmLL0CUufBV75FCwkh9UYcj
# vlFyGCJ16eorDnDOhqHpFiP/BNMKxq3MbCyAtV328IYUdNMFmAqkw1B2KyXO1DT9
# 1RAAAVQNp/hpesyXW26Vpa/Ib9hRQfoVvISpZAMRzRlJlV9/2LYCUNFT0O2In8Vh
# FrqIYQQYEQoACQUCWL4/SgIbDAAKCRCQfmQyoynOvJovAQCV7TUxQKnOpw91qaPR
# tWmhPRWFDfWP2uInpWLsfsgijgD9GtPK7VKrlluj0Z7YVc7QaOrQ/ykhaOQaJEEB
# 6aFfyKQ=
# =IQfy
# -----END PGP PRIVATE KEY BLOCK-----
#

HEXSTR_DSA_P = 'c4c9e5f86a85daf599928b03e666b7a86d2cd0d6faa64bcf28f54f6183a50e0d4eac5912730359aec588975fec5d9abf8c48a630b92ce3e3b5f88522443c21eea4917c6adb8fb9f3775eb7a7550973d1eab131b200075c55fe51e4b8ae53c504614b46da4e18dcd86cdcaae321d2fc94bb215d8244b29d1a0277a675b92296f015d1ad96766f42da01b1b4fdb55b11b2958f38572e5277fa5df362510ece9ce166524499f4ab413e4a27eabbcc42be2d7292d6f4ff9b1b6eb790503f3f48d5326644ec227b7d54a9ce616a77ce5ae08615a1f2df2346b50ef05e1d1edd415bbd02a55089528f5b44dd6e789f78c89628720a2f58729e34596ecc2dc65a92703f'
DSA_P = 0xc4c9e5f86a85daf599928b03e666b7a86d2cd0d6faa64bcf28f54f6183a50e0d4eac5912730359aec588975fec5d9abf8c48a630b92ce3e3b5f88522443c21eea4917c6adb8fb9f3775eb7a7550973d1eab131b200075c55fe51e4b8ae53c504614b46da4e18dcd86cdcaae321d2fc94bb215d8244b29d1a0277a675b92296f015d1ad96766f42da01b1b4fdb55b11b2958f38572e5277fa5df362510ece9ce166524499f4ab413e4a27eabbcc42be2d7292d6f4ff9b1b6eb790503f3f48d5326644ec227b7d54a9ce616a77ce5ae08615a1f2df2346b50ef05e1d1edd415bbd02a55089528f5b44dd6e789f78c89628720a2f58729e34596ecc2dc65a92703f
HEXSTR_DSA_Q = 'eb719de6190754ae62a022da7f68befe28327cbd02a6878cb678769f01119545'
DSA_Q = 0xeb719de6190754ae62a022da7f68befe28327cbd02a6878cb678769f01119545
HEXSTR_DSA_G = 'a217df24bd6072e70303389f0cd4c52b3bcbbe6587375422211493ed4deae6e107d7727eadef6785963f5158a387ebafb73179704625362ac10fd36de3e762d00da6f3012927952a3609e14e8bcbbc59b0b34b9f36046665cabb29598cbddd8ac36fe59cb1c83932e06ad81a5abe7fea7496b3ce7069d5b8d9d89b39d34bd4aab36f37e83be7c0725b16f0ba60fd1085f79eb732e9009295f2ae867fcad04159e0505e71be911e5bb2a3bcb0de970deb8c308b195a1dc09988dc7111def4950d1e7df35b768d909c6501d33ea10a3a384117069c136985a51916ce913b7aba88db4d7c1d159e347782708f7b2ebff083d97a354fb168a78a87146f61156a7aef'
DSA_G = 0xa217df24bd6072e70303389f0cd4c52b3bcbbe6587375422211493ed4deae6e107d7727eadef6785963f5158a387ebafb73179704625362ac10fd36de3e762d00da6f3012927952a3609e14e8bcbbc59b0b34b9f36046665cabb29598cbddd8ac36fe59cb1c83932e06ad81a5abe7fea7496b3ce7069d5b8d9d89b39d34bd4aab36f37e83be7c0725b16f0ba60fd1085f79eb732e9009295f2ae867fcad04159e0505e71be911e5bb2a3bcb0de970deb8c308b195a1dc09988dc7111def4950d1e7df35b768d909c6501d33ea10a3a384117069c136985a51916ce913b7aba88db4d7c1d159e347782708f7b2ebff083d97a354fb168a78a87146f61156a7aef
HEXSTR_DSA_Y = '737a169d05babba57b9105f17adf67d32bf6139561969890ebcf5ab21bf38d53c503a150060f4548078686416bb958d516e3f42e4996853a5df59ec7fe8023adc48992bc62aef1e0bd75f1e87fc220a92a4d51669264d868ae73a52c1bbea4da9dc3801907370a05971adb35d3ed92d7811726049f00339564070a4a9c1a2d3b4f3ee5495f04d77cacba30d7d232c220d14b23761ebe763aa260ccb65886ce6aac4010ac15eab41074bc88f68d6dbdcab7961b64a2a5e850b1ae71ba78fe742a34cb501bc4719aee9f4641b7436b27ede54444221cf2c2715ad9f3271751d30468af7eaf1334266dc967cbfedd3870b719afd0c512802f97064a055e916029cd'
DSA_Y = 0x737a169d05babba57b9105f17adf67d32bf6139561969890ebcf5ab21bf38d53c503a150060f4548078686416bb958d516e3f42e4996853a5df59ec7fe8023adc48992bc62aef1e0bd75f1e87fc220a92a4d51669264d868ae73a52c1bbea4da9dc3801907370a05971adb35d3ed92d7811726049f00339564070a4a9c1a2d3b4f3ee5495f04d77cacba30d7d232c220d14b23761ebe763aa260ccb65886ce6aac4010ac15eab41074bc88f68d6dbdcab7961b64a2a5e850b1ae71ba78fe742a34cb501bc4719aee9f4641b7436b27ede54444221cf2c2715ad9f3271751d30468af7eaf1334266dc967cbfedd3870b719afd0c512802f97064a055e916029cd
HEXSTR_DSA_X = 'c053f68800df153348cdb5a5dd77baa45b8c5894ea2bda0a30a394a21381c987'
DSA_X = 0xc053f68800df153348cdb5a5dd77baa45b8c5894ea2bda0a30a394a21381c987
HEXSTR_DSA_R = '95ed353140a9cea70f75a9a3d1b569a13d15850df58fdae227a562ec7ec8228e'
DSA_R=0x95ed353140a9cea70f75a9a3d1b569a13d15850df58fdae227a562ec7ec8228e
HEXSTR_DSA_S = '1ad3caed52ab965ba3d19ed855ced068ead0ff292168e41a244101e9a15fc8a4'
DSA_S=0x1ad3caed52ab965ba3d19ed855ced068ead0ff292168e41a244101e9a15fc8a4

# Taken from the elg secret subkey of the above.
HEXSTR_ELG_P = '4f44e10de708a8c976f6d800c954f9520e5b2c9f37cff7ab285e2b7170fb434c9f411d1e1f5170055ea7013820933b426485ef79e2dc0cc0d7e52340faa175e124bd447ea40c41c01504c36d24919ef3d87b0fc0a6c5bee7ff254fa175271fedd1973cf49cdd426f4eca9312cd80efc05760cb32743a9763cf09587e0ef7cbd880367ab502def8424054b75f13ab1e8d760f8fd9ef3bdabaef622010a04701ea7fe363b18dfd300cde397acd0fcf29bd2a229d82b2119c0576a1d81182661200456ec5dc7d259c7c8fbf7348c581708b8deb1d0626261990a553f73448621be5cddcc2780a2ad783598321bd7fe27919dd0197327800d0d1eb9f39d7588355b'
ELG_P = 0x4f44e10de708a8c976f6d800c954f9520e5b2c9f37cff7ab285e2b7170fb434c9f411d1e1f5170055ea7013820933b426485ef79e2dc0cc0d7e52340faa175e124bd447ea40c41c01504c36d24919ef3d87b0fc0a6c5bee7ff254fa175271fedd1973cf49cdd426f4eca9312cd80efc05760cb32743a9763cf09587e0ef7cbd880367ab502def8424054b75f13ab1e8d760f8fd9ef3bdabaef622010a04701ea7fe363b18dfd300cde397acd0fcf29bd2a229d82b2119c0576a1d81182661200456ec5dc7d259c7c8fbf7348c581708b8deb1d0626261990a553f73448621be5cddcc2780a2ad783598321bd7fe27919dd0197327800d0d1eb9f39d7588355b
HEXSTR_ELG_G = '6'
ELG_G = 0x06
HEXSTR_ELG_Y = 'b2ee1b675cc6ae07c428a2bebc77a91b27c29e220ce7e9d11d235ef41dac57202456f04a2fd9e15fad8869f16644e771e06a9d1be8c97a3495954acb17527a3fc4a34e5d0b02841d7bf7df7a5de4b910965a531365e0d6b71c9eb9089e384521e94514d048efbbd25bf86236d668c0eb3ee4fc4853d1e1e194ca36c56afc0f194b90e3c46cfc107c0b4ec1cf1ce1a27eb219ca38d2dfde3444e49c1efcfca9c085def49c939ef619428bc3ddb051567f575142dac8ea97415d1c4cdb4598b2f4094b9f055ef9142c2487d518723be5172182275e9ea2b0e70ce86a1e91623ff04d30ac6adcc6c2c80b55df6f0861474d305980aa4c350762b25ced434fdd510'
ELG_Y = 0x0b2ee1b675cc6ae07c428a2bebc77a91b27c29e220ce7e9d11d235ef41dac57202456f04a2fd9e15fad8869f16644e771e06a9d1be8c97a3495954acb17527a3fc4a34e5d0b02841d7bf7df7a5de4b910965a531365e0d6b71c9eb9089e384521e94514d048efbbd25bf86236d668c0eb3ee4fc4853d1e1e194ca36c56afc0f194b90e3c46cfc107c0b4ec1cf1ce1a27eb219ca38d2dfde3444e49c1efcfca9c085def49c939ef619428bc3ddb051567f575142dac8ea97415d1c4cdb4598b2f4094b9f055ef9142c2487d518723be5172182275e9ea2b0e70ce86a1e91623ff04d30ac6adcc6c2c80b55df6f0861474d305980aa4c350762b25ced434fdd510
HEXSTR_ELG_X = 'da7f8697acc975b6e95a5afc86fd85141fa15bc84a9640311cd1949955f7fd8b60250d153d0ed889fc561'
ELG_X = 0x0da7f8697acc975b6e95a5afc86fd85141fa15bc84a9640311cd1949955f7fd8b60250d153d0ed889fc561

class CryptoModelTest(SynTest):

    def test_form_rsakey(self):
        prop = 'crypto:asym'
        props = {
            'id': KEYID,
            'finger': FINGER,
            'created_at': STR_CREATION_TS,
            'expiration': STR_EXPIRATION_TS,
            'type': 'rsa',
            'size': BITS,
            'rsa:pub:mod': MODULUS,
            'rsa:pub:exp': PUBLIC_EXPONENT,
            'rsa:priv:exp': PRIVATE_EXPONENT,
            'rsa:priv:p': PRIVATE_PRIME_P,
            'rsa:priv:q': PRIVATE_PRIME_Q,
        }
        valu = HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT
        tufo = ('', {})
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:asym')
        self.eq(tufo[1].get('crypto:asym'), HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT)
        self.eq(tufo[1].get('crypto:asym:size'), BITS)
        self.eq(tufo[1].get('crypto:asym:rsa:pub:mod'), HEXSTR_MODULUS)
        self.eq(tufo[1].get('crypto:asym:rsa:pub:exp'), HEXSTR_PUBLIC_EXPONENT)
        self.eq(tufo[1].get('crypto:asym:rsa:priv:exp'), HEXSTR_PRIVATE_EXPONENT)
        self.eq(tufo[1].get('crypto:asym:rsa:priv:p'), HEXSTR_PRIVATE_PRIME_P)
        self.eq(tufo[1].get('crypto:asym:rsa:priv:q'), HEXSTR_PRIVATE_PRIME_Q)
        self.eq(tufo[1].get('crypto:asym:created_at'), CREATION_TS)
        self.eq(tufo[1].get('crypto:asym:expiration'), EXPIRATION_TS)



    def test_form_dsakey(self):
        prop = 'crypto:asym'
        props = {
            'id': KEYID,
            'finger': FINGER,
            'created_at': STR_CREATION_TS,
            'expiration': STR_EXPIRATION_TS,
            'type': 'dsa',
            'size': BITS,
            'dsa:pub:g': DSA_G,
            'dsa:pub:y': DSA_Y,
            'dsa:pub:p': DSA_P,
            'dsa:pub:q': DSA_Q,
            'dsa:priv:x' : DSA_X,
        }
        valu = HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT
        tufo = ('', {})
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:asym')
        self.eq(tufo[1].get('crypto:asym'), HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT)
        self.eq(tufo[1].get('crypto:asym:size'), BITS)
        self.eq(tufo[1].get('crypto:asym:dsa:pub:g'), HEXSTR_DSA_G)
        self.eq(tufo[1].get('crypto:asym:dsa:pub:y'), HEXSTR_DSA_Y)
        self.eq(tufo[1].get('crypto:asym:dsa:pub:p'), HEXSTR_DSA_P)
        self.eq(tufo[1].get('crypto:asym:dsa:pub:q'), HEXSTR_DSA_Q)
        self.eq(tufo[1].get('crypto:asym:dsa:priv:x'), HEXSTR_DSA_X)
        self.eq(tufo[1].get('crypto:asym:created_at'), CREATION_TS)
        self.eq(tufo[1].get('crypto:asym:expiration'), EXPIRATION_TS)

    def test_form_elgkey(self):
        prop = 'crypto:asym'
        props = {
            'id': KEYID,
            'finger': FINGER,
            'created_at': STR_CREATION_TS,
            'expiration': STR_EXPIRATION_TS,
            'type': 'elg',
            'size': BITS,
            'elg:pub:g': ELG_G,
            'elg:pub:y': ELG_Y,
            'elg:pub:p': ELG_P,
            'elg:priv:x' : ELG_X,
        }
        valu = HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT
        tufo = ('', {})
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:asym')
        self.eq(tufo[1].get('crypto:asym'), HEXSTR_MODULUS + HEXSTR_PRIVATE_EXPONENT)
        self.eq(tufo[1].get('crypto:asym:size'), BITS)
        self.eq(tufo[1].get('crypto:asym:elg:pub:g'), HEXSTR_ELG_G)
        self.eq(tufo[1].get('crypto:asym:elg:pub:y'), HEXSTR_ELG_Y)
        self.eq(tufo[1].get('crypto:asym:elg:pub:p'), HEXSTR_ELG_P)
        self.eq(tufo[1].get('crypto:asym:elg:priv:x'), HEXSTR_ELG_X)
        self.eq(tufo[1].get('crypto:asym:created_at'), CREATION_TS)
        self.eq(tufo[1].get('crypto:asym:expiration'), EXPIRATION_TS)

    def test_form_rsa_sig(self):
        prop = 'crypto:sig'
        props = {
            'created_at': STR_CREATION_TS,
            'expiration': STR_EXPIRATION_TS,
            'hash_alg': 'SHA1',
            'pub_alg': 'RSA Encrypt or Sign',
            'sig_type': 'Generic certification of a User ID and Public Key packet',
            'digest': 0x7eb4,
            'rsa': RSA_SIG,
            'src': MODULUS,
            'tgt_type': 'subpacket',
            'tgt': 'some other key hex'
        }

        valu = HEXSTR_RSA_SIG
        tufo = ('', {})
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sig')
        self.eq(tufo[1].get('crypto:sig'), HEXSTR_RSA_SIG)
        self.eq(tufo[1].get('crypto:sig:created_at'), CREATION_TS)
        self.eq(tufo[1].get('crypto:sig:expiration'), EXPIRATION_TS)
        self.eq(tufo[1].get('crypto:sig:rsa'), HEXSTR_RSA_SIG)
        self.eq(tufo[1].get('crypto:sig:src'), HEXSTR_MODULUS)
        self.eq(tufo[1].get('crypto:sig:digest'), '7eb4')
        self.eq(tufo[1].get('crypto:sig:hash_alg'), 'SHA1')
        self.eq(tufo[1].get('crypto:sig:pub_alg'), 'RSA Encrypt or Sign')
        self.eq(tufo[1].get('crypto:sig:sig_type'), 'Generic certification of a User ID and Public Key packet')
        self.eq(tufo[1].get('crypto:sig:tgt_type'), 'subpacket')
        self.eq(tufo[1].get('crypto:sig:tgt'), 'some other key hex')

    def test_form_dsa_sig(self):
        prop = 'crypto:sig'
        dsa_crypto_system = HEXSTR_DSA_P + HEXSTR_DSA_Q + HEXSTR_DSA_G + HEXSTR_DSA_Y
        props = {
            'created_at': STR_CREATION_TS,
            'expiration': STR_EXPIRATION_TS,
            'hash_alg': 'SHA1',
            'pub_alg': 'DSA Digital Signature Algorithm',
            'sig_type': 'Generic certification of a User ID and Public Key packet',
            'digest': 0x7eb4,
            'dsa:r': DSA_R,
            'dsa:s': DSA_S,
            'src': dsa_crypto_system,
            'tgt_type': 'subpacket',
            'tgt': 'some other key hex'
        }

        valu = HEXSTR_RSA_SIG
        tufo = ('', {})
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sig')
        self.eq(tufo[1].get('crypto:sig'), HEXSTR_RSA_SIG)
        self.eq(tufo[1].get('crypto:sig:created_at'), CREATION_TS)
        self.eq(tufo[1].get('crypto:sig:expiration'), EXPIRATION_TS)
        self.eq(tufo[1].get('crypto:sig:dsa:r'), HEXSTR_DSA_R)
        self.eq(tufo[1].get('crypto:sig:dsa:s'), HEXSTR_DSA_S)
        self.eq(tufo[1].get('crypto:sig:src'), dsa_crypto_system)
        self.eq(tufo[1].get('crypto:sig:digest'), '7eb4')
        self.eq(tufo[1].get('crypto:sig:hash_alg'), 'SHA1')
        self.eq(tufo[1].get('crypto:sig:pub_alg'), 'DSA Digital Signature Algorithm')
        self.eq(tufo[1].get('crypto:sig:sig_type'), 'Generic certification of a User ID and Public Key packet')
        self.eq(tufo[1].get('crypto:sig:tgt_type'), 'subpacket')
        self.eq(tufo[1].get('crypto:sig:tgt'), 'some other key hex')

    def test_prop_rc4(self):
        prop = 'crypto:sym:rc4'
        props = {}
        valu = 0xB204A082F9
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:rc4')
        self.eq(tufo[1].get('crypto:sym:rc4'), 'b204a082f9')


    def test_prop_aes(self):
        prop = 'crypto:sym:aes'
        props = {}
        valu = 0xD148488164B1684829398003FDA2E5F922109E22C64E0B3967A3E087B6607FF6
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:aes')
        self.eq(tufo[1].get('crypto:sym:aes'), 'd148488164b1684829398003fda2e5f922109e22c64e0b3967a3e087b6607ff6')

    def test_prop_des(self):
        prop = 'crypto:sym:des'
        props = {}
        valu = 0xEB2C6093861362
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:des')
        self.eq(tufo[1].get('crypto:sym:des'), 'eb2c6093861362')

    def test_prop_3des(self):
        prop = 'crypto:sym:3des'
        props = {}
        valu = 0xEB2C60938613625E46BEBD61B87537BB8F3DABC615
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:3des')
        self.eq(tufo[1].get('crypto:sym:3des'), 'eb2c60938613625e46bebd61b87537bb8f3dabc615')

    def test_prop_bfish(self):
        prop = 'crypto:sym:bfish'
        props = {}
        valu = 0xDCE47A5C776F64A7DDD0F199F8AFDD99800BFA6D684B3976677217A9D7EAD27E
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:bfish')
        self.eq(tufo[1].get('crypto:sym:bfish'), 'dce47a5c776f64a7ddd0f199f8afdd99800bfa6d684b3976677217a9d7ead27e')

    def test_prop_2fish(self):
        prop = 'crypto:sym:2fish'
        props = {}
        valu = 0xDCE47A5C776F64A7DDD0F199F8AFDD99800BFA6D684B3976677217A9D7EAD27E
        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp(prop, valu, **props)
        self.eq(tufo[1].get('tufo:form'), 'crypto:sym:2fish')
        self.eq(tufo[1].get('crypto:sym:2fish'), 'dce47a5c776f64a7ddd0f199f8afdd99800bfa6d684b3976677217a9d7ead27e')
        pass
