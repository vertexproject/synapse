import synapse.exc as s_exc

import synapse.tests.utils as s_test

class TestLibStormRandom(s_test.SynTest):

    async def test_stormlib_random_int(self):
        async with self.getTestCore() as core:
            valu = await core.callStorm('return($lib.random.int(30))')
            self.true(valu >= 0 and valu <= 30)

            valu = await core.callStorm('return($lib.random.int(30, minval=10))')
            self.true(valu >= 10 and valu <= 30)

            valu = await core.callStorm('return($lib.random.int(0))')
            self.eq(valu, 0)

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.random.int(-1))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.random.int(maxval=0, minval=1))')
