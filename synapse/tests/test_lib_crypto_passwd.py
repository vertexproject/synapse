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

    async def test_checkShadowV2_cache(self):
        passwd = 'password'
        wrong = 'newp'
        shadow = await s_passwd.getShadowV2(passwd)

        s_passwd._shadowCache.clear()

        # First call populates cache; subsequent calls return cached result.
        self.true(await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow))
        self.len(1, s_passwd._shadowCache)
        self.true(await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow))
        self.true(await s_passwd.checkShadowV2(passwd=passwd, shadow=shadow))
        self.len(1, s_passwd._shadowCache)

        # Wrong password gets its own cache entry.
        self.false(await s_passwd.checkShadowV2(passwd=wrong, shadow=shadow))
        self.len(2, s_passwd._shadowCache)
        self.false(await s_passwd.checkShadowV2(passwd=wrong, shadow=shadow))
        self.len(2, s_passwd._shadowCache)

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
        # TODO: remove this version check once CI Python is >= 3.14.4 (SYN-10581)
        if s_common.version >= (3, 14, 4):
            self.eq(valu, 'Only base64 data is allowed')
        else:
            self.eq(valu, 'Excess data after padding')

        badkey = key1 + 'newp'
        isok, valu = s_passwd.parseApiKey(badkey)
        self.false(isok)
        self.eq(valu, 'Excess data after padding')

        badkey = base64.b64encode(b'newp', altchars=b'-_').decode('-utf-8')
        isok, valu = s_passwd.parseApiKey(badkey)
        self.false(isok)
        self.eq(valu, 'Incorrect length, got 8')

        # An otherwise valid key, but with standard base64 chars instead
        # of the altchars we specified. This covers CVE-2025-12781 behavior.
        badkeys_invalid_alts = (
            'bcr_T1bNJURuN4+7CY5CqSuuK_Uvqg5Uv47W5YQ58RA=',
            'bcr/T1bNJURuN4-7CY5CqSuuK/Uvqg5Uv47W5YQ58RA=',
            'bcr/T1bNJURuN4+7CY5CqSuuK/Uvqg5Uv47W5YQ58RA=',
        )
        for badkey in badkeys_invalid_alts:
            isok, valu = s_passwd.parseApiKey(badkey)
            self.false(isok)
            self.isin('Invalid character in API key.', valu)

    async def test_apikey_generation_prefix(self):
        # every generated key now carries a fixed prefix, so it can never begin with
        # '-' regardless of which iden bytes s_common.guid() happens to produce.
        iden, key, shadow = await s_passwd.generateApiKey()
        self.true(key.startswith(s_passwd.APIKEY_PREFIX))
        self.false(key.startswith('-'))

        isok, (iden2, secv) = s_passwd.parseApiKey(key)
        self.true(isok)
        self.eq(iden, iden2)
        self.true(await s_passwd.checkShadowV2(secv, shadow))

        # a key issued before the prefix existed carries none, and must still parse --
        # this is the shape of every key issued before this change, including one whose
        # iden happens to produce a leading '-' (an iden's first byte of 0xf8-0xfb does).
        dash_iden = 'f8' + s_common.guid()[2:]
        legacy_secv = s_common.guid()
        legacy_key = base64.b64encode(s_common.uhex(dash_iden) + s_common.uhex(legacy_secv),
                                       altchars=b'-_').decode('utf-8')
        self.true(legacy_key.startswith('-'))

        isok0, (iden0, secv0) = s_passwd.parseApiKey(legacy_key)
        self.true(isok0)
        self.eq(dash_iden, iden0)
        self.eq(legacy_secv, secv0)

        legacy_shadow = await s_passwd.getShadowV2(legacy_secv)
        self.true(await s_passwd.checkShadowV2(secv0, legacy_shadow))

        # a legacy (unprefixed) key can itself begin with the literal prefix -- 's', 'y',
        # 'n' and '-' are all valid '-_' altchars -- so parseApiKey must not strip it
        # unconditionally. An iden starting with the bytes b3:29:fe encodes to exactly
        # that.
        prefixlike_iden = 'b329fe' + s_common.guid()[6:]
        prefixlike_secv = s_common.guid()
        prefixlike_key = base64.b64encode(s_common.uhex(prefixlike_iden) + s_common.uhex(prefixlike_secv),
                                           altchars=b'-_').decode('utf-8')
        self.true(prefixlike_key.startswith(s_passwd.APIKEY_PREFIX))

        isok1, (iden1, secv1) = s_passwd.parseApiKey(prefixlike_key)
        self.true(isok1)
        self.eq(prefixlike_iden, iden1)
        self.eq(prefixlike_secv, secv1)

        # a value that begins with the prefix but whose remainder does not parse falls
        # back cleanly rather than raising, and is still rejected
        isok2, _ = s_passwd.parseApiKey(s_passwd.APIKEY_PREFIX + 'newp')
        self.false(isok2)
