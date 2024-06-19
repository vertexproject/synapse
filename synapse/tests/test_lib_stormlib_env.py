import os
import synapse.exc as s_exc
import synapse.tests.utils as s_test

class StormLibEnvTest(s_test.SynTest):

    async def test_stormlib_env(self):

        with self.setTstEnvars(SYN_STORM_ENV_WOOT='woot'):

            async with self.getTestCore() as core:

                self.eq('woot', await core.callStorm('return($lib.env.get(SYN_STORM_ENV_WOOT))'))
                self.eq('hehe', await core.callStorm('return($lib.env.get(SYN_STORM_ENV_HEHE, default=hehe))'))

                self.none(await core.callStorm('return($lib.env.get(SYN_STORM_ENV_HEHE))'))

                visi = await core.auth.addUser('visi')

                with self.raises(s_exc.AuthDeny):
                    opts = {'user': visi.iden}
                    await core.callStorm('return($lib.env.get(SYN_STORM_ENV_WOOT))', opts=opts)

                with self.raises(s_exc.BadArg):
                    await core.callStorm('return($lib.env.get(USER))')
