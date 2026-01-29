import copy
import base64
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.lib.crypto.passwd as s_passwd

class PasswdTest(s_t_utils.SynTest):
    async def test_shadow_passwords(self):
        passwd = 'the quick brown fox jumps over the lazy dog.'
        shadow = await s_passwd.getShadowV2(passwd)
        self.eq(shadow.get('type'), 'pbkdf2')
        self.len(32, shadow.get('hashed'))
        # PBKDF2 defaults
        func_params = shadow.get('func_params')
        self.eq(func_params.get('hash_name'), 'sha256')
        self.len(32, func_params.get('salt'))
        self.eq(310_000, func_params.get('iterations'))

        self.true(await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow))
        self.false(await s_passwd.checkShadowV2(passwd='newp', shadow=shadow))
        shadow['func_params']['hash_name'] = 'sha1'
        self.false(await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow))

        # Blobs constructed with valid parameters can be validated.
        # This is to future proof that in the event of modifying parameters,
        # stored values which have values which differ from our defaults will
        # still be able to be verified.
        with mock.patch('synapse.lib.crypto.passwd.PBKDF2_HASH', 'sha512'):
            with mock.patch('synapse.lib.crypto.passwd.PBKDF2_ITERATIONS', 100_000):
                mock_shadow = await s_passwd.getShadowV2('manual')
        self.true(await s_passwd.checkShadowV2('manual', mock_shadow))

        # Ensure we have all our expected parameters when validating the shadow
        bad_shadow = copy.deepcopy(mock_shadow)
        bad_shadow['func_params'].pop('salt')
        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('manual', bad_shadow)

        bad_shadow = copy.deepcopy(mock_shadow)
        bad_shadow['func_params'].pop('iterations')
        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('manual', bad_shadow)

        bad_shadow = copy.deepcopy(mock_shadow)
        bad_shadow['func_params'].pop('hash_name')
        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('manual', bad_shadow)

        bad_shadow = copy.deepcopy(mock_shadow)
        bad_shadow.pop('func_params')
        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('manual', bad_shadow)

        bad_shadow = copy.deepcopy(mock_shadow)
        bad_shadow.pop('hashed')
        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('manual', bad_shadow)

        # Bad inputs
        with mock.patch('synapse.lib.crypto.passwd.DEFAULT_PTYP', 'newp'):
            with self.raises(s_exc.CryptoErr):
                await s_passwd.getShadowV2('newp')

        with self.raises(s_exc.CryptoErr):
            await s_passwd.checkShadowV2('newp', {'type': 'newp'})

        tvs = (None,
               1234,
               b'1234',
               (1, 2, 3, 4),
               [1, 2, 3, 4],
               {1: 2, 3: 4},
               {1, 2, 3, 4},
               )
        for vec in tvs:
            with self.raises(AttributeError):
                await s_passwd.getShadowV2(vec)

    async def test_apikey_generation(self):
        iden, key, shadow = await s_passwd.generateApiKey()
        self.true(s_common.isguid(iden))
        self.isinstance(key, str)
        self.isinstance(shadow, dict)

        isok, (iden2, secv) = s_passwd.parseApiKey(key)
        self.true(isok)
        self.eq(iden, iden2)

        result = await s_passwd.checkShadowV2(secv, shadow)
        self.true(result)

        some_iden = s_common.guid()

        iden0, key0, shadow0 = await s_passwd.generateApiKey(some_iden)
        iden1, key1, shadow1 = await s_passwd.generateApiKey(some_iden)
        self.eq(some_iden, iden0)
        self.eq(iden0, iden1)
        self.ne(key0, key1)
        self.ne(shadow0, shadow1)

        isok0, (cidn0, secv0) = s_passwd.parseApiKey(key0)
        isok1, (cidn1, secv1) = s_passwd.parseApiKey(key1)
        self.true(isok0)
        self.true(isok1)
        self.eq(some_iden, cidn0)
        self.eq(some_iden, cidn1)
        self.ne(secv0, secv1)

        self.true(await s_passwd.checkShadowV2(secv0, shadow0))
        self.false(await s_passwd.checkShadowV2(secv1, shadow0))
        self.false(await s_passwd.checkShadowV2(secv0, shadow1))
        self.true(await s_passwd.checkShadowV2(secv1, shadow1))

        with self.raises(s_exc.CryptoErr):
            await s_passwd.generateApiKey(iden=iden[:16])

        badkey = key1 + ' '
        isok, valu = s_passwd.parseApiKey(badkey)
        self.false(isok)
        self.eq(valu, 'Excess data after padding')

        badkey = key1 + 'newp'
        isok, valu = s_passwd.parseApiKey(badkey)
        self.false(isok)
        self.eq(valu, 'Excess data after padding')

        badkey = base64.b64encode(b'newp', altchars=b'-_').decode('-utf-8')
        isok, valu = s_passwd.parseApiKey(badkey)
        self.false(isok)
        self.eq(valu, 'Incorrect length, got 8')
