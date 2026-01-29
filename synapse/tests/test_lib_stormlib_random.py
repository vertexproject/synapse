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

    async def test_stormlib_random_generator(self):
        async with self.getTestCore() as core:

            # Seedless generators
            q = '''$r=$lib.random.generator()
            return(($r.int(10), $r.int(10), $r.int(10)))
            '''
            valu = await core.callStorm(q)
            for v in valu:
                self.true(v >= 0 and v <= 10)

            # There is no seed on the generator
            q = '''$r=$lib.random.generator() return ( $r.seed )'''
            valu = await core.callStorm(q)
            self.none(valu)

            # Generators can be made and seeds set
            q = '''$r=$lib.random.generator() $r.seed=myCoolTestSeed
            return ( (($r.int(10), $r.int(10), $r.int(10)), $r.seed) )'''
            valu = await core.callStorm(q)
            self.eq(valu, ((5, 9, 1), 'myCoolTestSeed'))

            # Setting a seed resets the generator
            q = '''$r=$lib.random.generator(seed=myCoolTestSeed) $ret=()
            $ret.append($r.int(10)) $ret.append($r.int(10)) $ret.append($r.int(10))
            $r.seed=myCoolTestSeed
            $ret.append($r.int(10)) $ret.append($r.int(10)) $ret.append($r.int(10))
            return ($ret)'''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 9, 1, 5, 9, 1))

            # Clearing the seed makes the generator random.
            q = '''$r=$lib.random.generator(seed=myCoolTestSeed) $ret=()
            $ret.append($r.int(10)) $ret.append($r.int(10)) $ret.append($r.int(10))
            $r.seed=(null)
            $ret.append($r.int(10)) $ret.append($r.int(10)) $ret.append($r.int(10))
            return ($ret)'''
            valu = await core.callStorm(q)
            self.len(6, valu)
            self.eq(valu[:3], (5, 9, 1))
            self.ne(valu[3:], (5, 9, 1))
            for v in valu[3:]:
                self.true(v >= 0 and v <= 10)

            # Seeded generators are consistent
            q = '''$r=$lib.random.generator(seed=myCoolTestSeed)
            return(($r.int(10), $r.int(10), $r.int(10)))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 9, 1))

            new_valu = await core.callStorm(q)
            self.eq(valu, new_valu)

            q = '''$r=$lib.random.generator(seed=myCoolTestSeed)
            $r2 = $lib.random.generator(seed=$r.seed)
            return(($r.int(10), $r2.int(10)))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 5))

            q = '''return($lib.vars.type($lib.random.generator(x)))'''
            valu = await core.callStorm(q)
            self.eq(valu, 'random')

            # Seeds are stringified
            q = '''$r=$lib.random.generator(seed=1234567890)
            $r2 = $lib.random.generator(seed=(1234567890))
            return(($r.int(10), $r2.int(10), $r.seed, $r2.seed))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (5, 5, '1234567890', '1234567890'))

            # Empty string value is still a str
            q = '''$r=$lib.random.generator(seed='') return ($r.int(10))'''
            valu = await core.callStorm(q)
            self.eq(valu, 7)

            # Sad path
            with self.raises(s_exc.BadArg):
                await core.callStorm('$r=$lib.random.generator(seed="") return($r.int(maxval=0, minval=1))')

            # Printing objects
            msgs = await core.stormlist('$lib.print($lib.random.generator())')
            self.stormIsInPrint('random', msgs)
            self.stormNotInPrint('seed=', msgs)

            msgs = await core.stormlist('$lib.print($lib.random.generator(seed=""))')
            self.stormIsInPrint('random seed=', msgs)

            msgs = await core.stormlist('$lib.print($lib.random.generator(seed=haha))')
            self.stormIsInPrint('random seed=haha', msgs)
