import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils

import synapse.lib.crypto.passwd as s_passwd

class PasswdTest(s_t_utils.SynTest):
    async def test_shadow_passwords(self):
        passwd = 'the quick brown fox jumps over the lazy dog.'
        info = await s_passwd.getShadowV2(passwd)
        self.eq(info.get('type'), 'pbkdf2')
        self.eq(info.get('hash_name'), 'sha256')

        self.true(await s_passwd.checkShadowV2(passwd=passwd, params=info))
        self.false(await s_passwd.checkShadowV2(passwd='newp', params=info))
        info['hash_name'] = 'sha1'
        self.false(await s_passwd.checkShadowV2(passwd=passwd, params=info))

        # Scrypt supported on the backend as well.
        info = await s_passwd.getShadowV2(passwd, ptyp='scrypt')
        self.eq(info.get('type'), 'scrypt')
        self.true(await s_passwd.checkShadowV2(passwd=passwd, params=info))
        self.false(await s_passwd.checkShadowV2(passwd='newp', params=info))
        info['n'] = 2 ** 15
        self.false(await s_passwd.checkShadowV2(passwd=passwd, params=info))

        # Bad inputs
        with self.raises(s_exc.BadArg):
            await s_passwd.getShadowV2('newp', ptyp='newp')

        with self.raises(s_exc.BadArg):
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
