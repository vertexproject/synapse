import os
import synapse.exc as s_exc
import synapse.tests.utils as s_test

class StormLibEnvTest(s_test.SynTest):

    async def test_stormlib_env(self):

        with self.setTstEnvars(SYN_STORM_ENV_WOOT='woot', USER='bar'):

            async with self.getTestCore() as core:

                self.eq('woot', await core.callStorm('return($lib.env.SYN_STORM_ENV_WOOT)'))
                self.none(await core.callStorm('return($lib.env.SYN_STORM_ENV_HEHE)'))

                retn = await core.callStorm('$vars = () for $v in $lib.env { $vars.append($v) } return($vars)')
                self.eq([('SYN_STORM_ENV_WOOT', 'woot')], retn)

                msgs = await core.stormlist('$lib.print($lib.env)')
                self.stormIsInPrint("{'SYN_STORM_ENV_WOOT': 'woot'}", msgs)

                visi = await core.auth.addUser('visi')

                opts = {'user': visi.iden}
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm('return($lib.env.SYN_STORM_ENV_WOOT)', opts=opts)

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm('for $v in $lib.env { }', opts=opts)

                with self.raises(s_exc.BadArg):
                    await core.callStorm('return($lib.env.USER)')
