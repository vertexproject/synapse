import copy
import unittest.mock as mock

import synapse.exc as s_exc

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
