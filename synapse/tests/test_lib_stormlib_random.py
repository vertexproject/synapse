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

    async def test_stormlib_random_seed(self):
        async with self.getTestCore() as core:
            q = '''$r=$lib.random.seed(myCoolTestSeed)
            return(($r.int(10), $r.int(10), $r.int(10)))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 9, 1))

            new_valu = await core.callStorm(q)
            self.eq(valu, new_valu)

            q = '''$r=$lib.random.seed(myCoolTestSeed)
            $r2 = $lib.random.seed($r.seed)
            return(($r.int(10), $r2.int(10)))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 5))

            q = '''return($lib.vars.type($lib.random.seed(x)))'''
            valu = await core.callStorm(q)
            self.eq(valu, 'random')

            # Seeds are stringified
            q = '''$r=$lib.random.seed(1234567890)
            $r2 = $lib.random.seed((1234567890))
            return(($r.int(10), $r2.int(10), $r.seed, $r2.seed))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 5, '1234567890', '1234567890'))

            # Empty string value is still a str
            q = '''$r=$lib.random.seed('') return ($r.int(10))'''
            valu = await core.callStorm(q)
            self.eq(valu, 7)
