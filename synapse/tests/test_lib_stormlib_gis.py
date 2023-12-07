import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibGisTest(s_test.SynTest):

    async def test_stormlib_gis_bbox(self):

        async with self.getTestCore() as core:

            lbox = await core.callStorm('return($lib.gis.bbox(-2.0783, 51.8994, $lib.cast(geo:dist, 1km)))')
            self.eq(lbox, (-2.0928746526154747,
                           -2.0637253473845254,
                           51.890406796362754,
                           51.908393203637246))

            with self.raises(s_exc.BadArg):
                lbox = await core.callStorm('return($lib.gis.bbox(newp, -2.0783, 1))')

            with self.raises(s_exc.BadArg):
                lbox = await core.callStorm('return($lib.gis.bbox(51.2, -2.0783, newp))')
