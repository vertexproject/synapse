import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class PackTest(s_test.SynTest):

    async def test_stormlib_pack(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.en((10), "asdf"))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.un((10), "asdf"))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.un(">HI", "asdfqwer"))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.en(">D", ([10])))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.un("<D", $lib.hex.decode(0000)))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.un("HI", $lib.hex.decode(00010000000a)))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.pack.en("HI", ([1, 10])))')

            self.eq(b'\x00\x01\x00\x00\x00\x0a', await core.callStorm('return($lib.pack.en(">HI", ([1, 10])))'))
            self.eq((1, 10), await core.callStorm('return($lib.pack.un(">HI", $lib.hex.decode(00010000000a)))'))

            self.eq((1,), await core.callStorm('return($lib.pack.un(">H", $lib.hex.decode(00010000000a)))'))
            self.eq((10,), await core.callStorm('return($lib.pack.un(">H", $lib.hex.decode(00010000000a), offs=4))'))
