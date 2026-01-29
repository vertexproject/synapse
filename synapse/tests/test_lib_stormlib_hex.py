import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibHexTest(s_test.SynTest):

    async def test_stormlib_hex(self):

        async with self.getTestCore() as core:
            self.eq((1, 2, 3), await core.callStorm('''
                return($lib.hex.decode(010002000300).unpack("<HHH"))
            '''))

            self.eq(b'\x03\x00', await core.callStorm('''
                return($lib.hex.decode(010002000300).slice(4,6))
            '''))

            self.eq(b'\x03\x00', await core.callStorm('''
                return($lib.hex.decode(010002000300).slice(4))
            '''))

            self.eq('010002000300', await core.callStorm('''
                return($lib.hex.encode($lib.hex.decode(010002000300)))
            '''))

            self.eq(255, await core.callStorm('''
                return($lib.hex.toint(ff))
            '''))

            self.eq(-1, await core.callStorm('''
                return($lib.hex.toint(ff, signed=$lib.true))
            '''))

            self.eq('ffff', await core.callStorm('''
                return($lib.hex.fromint(65535, 2))
            '''))

            with self.raises(s_exc.BadArg):
                self.eq('00ff', await core.callStorm('''
                    return($lib.hex.fromint(65535, 2, signed=$lib.true))
                '''))

            self.eq('ffff', await core.callStorm('''
                return($lib.hex.fromint(-1, 2, signed=$lib.true))
            '''))

            with self.raises(s_exc.BadArg):
                self.eq('ffff', await core.callStorm('''
                    return($lib.hex.fromint(-1, 2))
                '''))

            self.eq('ee2b3debd421de14a862ac04f3ddc401', await core.callStorm('''
                return($lib.hex.trimext(ffffffffee2b3debd421de14a862ac04f3ddc401))
            '''))

            self.eq('03e8', await core.callStorm('''
                return($lib.hex.trimext(00000000000000000000000000000000000003e8))
            '''))

            self.eq('80', await core.callStorm('''
                return($lib.hex.trimext(ff80))
            '''))

            self.eq('00ff', await core.callStorm('''
                return($lib.hex.trimext(00ff))
            '''))

            self.eq('00000000ff', await core.callStorm('''
                return($lib.hex.signext(00ff, 10))
            '''))

            self.eq('ffffffffff', await core.callStorm('''
                return($lib.hex.signext(ff, 10))
            '''))

            self.eq('ffffaf2ff3de000035cb', await core.callStorm('''
                return($lib.hex.signext(faf2ff3de000035cb, 20))
            '''))

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.decode(asdf))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.encode(asdf))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.decode(010002000300).unpack("<ZZ"))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.toint(asdf))')

            with self.raises(s_exc.BadCast):
                await core.callStorm('return($lib.hex.fromint(foo, 20))')

            with self.raises(s_exc.BadCast):
                await core.callStorm('return($lib.hex.fromint(20, foo))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.trimext(foo))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.hex.signext(oo, 20))')

            with self.raises(s_exc.BadCast):
                await core.callStorm('return($lib.hex.signext(ff, foo))')
