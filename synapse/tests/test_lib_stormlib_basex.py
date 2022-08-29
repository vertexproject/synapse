import synapse.exc as s_exc

import synapse.tests.utils as s_test

b64alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
b58alpha = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

class StormLibBaseXTest(s_test.SynTest):

    async def test_stormlib_basex(self):

        async with self.getTestCore() as core:
            self.len(64, b64alpha)

            opts = {'vars': {'valu': b'\xbe+"', 'alpha': b64alpha}}
            self.eq('visi', await core.callStorm('return($lib.basex.encode($valu, $alpha))', opts=opts))

            opts = {'vars': {'valu': b'\x00', 'alpha': b64alpha}}
            self.eq('A', await core.callStorm('return($lib.basex.encode($valu, $alpha))', opts=opts))

            opts = {'vars': {'valu': 'visi', 'alpha': b64alpha}}
            self.eq(b'\xbe+"', await core.callStorm('return($lib.basex.decode($valu, $alpha))', opts=opts))

            opts = {'vars': {'valu': '282749fae7dcb58db8fe7311b12e21036cd18885ca4cd835a325b106cb98c44d', 'alpha': b58alpha}}
            retn = await core.callStorm('return($lib.basex.encode($lib.hex.decode($valu), $alpha))', opts=opts)
            self.eq('3hk4CzJbCuZfWFHEyQWHC5y3KJCShQDjiz4sUu3dJKzt', retn)

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'valu': 'derp', 'alpha': 'visi'}}
                retn = await core.callStorm('return($lib.basex.encode($valu, $alpha))', opts=opts)

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'valu': 'derp', 'alpha': 'visi'}}
                retn = await core.callStorm('return($lib.basex.decode($valu, $alpha))', opts=opts)

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'valu': 10, 'alpha': 'visi'}}
                retn = await core.callStorm('return($lib.basex.encode($valu, $alpha))', opts=opts)

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'valu': 10, 'alpha': 'visi'}}
                retn = await core.callStorm('return($lib.basex.encode($valu, $alpha))', opts=opts)
