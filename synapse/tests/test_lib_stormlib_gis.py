import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibGisTest(s_test.SynTest):

    async def test_stormlib_gis_bbox(self):

        async with self.getTestCore() as core:

            gchq = (51.8994, -2.0783)
            km = 1000000.0  # using mm as base units
            lbox = await core.callStorm('return($lib.gis.bbox(51.8994, -2.0783, $lib.cast(geo:dist, 1km)))')
            self.eq(lbox, (51.890406796362754,
                           51.908393203637246,
                           -2.0928746526154747,
                           -2.0637253473845254))
