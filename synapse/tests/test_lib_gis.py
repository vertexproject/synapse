from synapse.tests.common import *

import synapse.lib.gis as s_gis

# earth mean radius in mm
r = 6371008800

ratios = {
    'cm': 10.0,
    'm': 1000.0,
    'km': 1000000.0,
}

km = 1000000.0 # using mm as base units
gchq = (51.8994, -2.0783)

class GisTest(SynTest):

    def test_lib_gis_haversine(self):
        px = (36.12, -86.67)
        py = (33.94, -118.40)
        self.eq(s_gis.haversine(px, py), 2886448429.7648544)

    def test_lib_gis_dms2dec(self):
        self.eq(s_gis.dms2dec(45, 46, 52), 45.78111111111111)

    def test_lib_gis_bbox(self):
        lbox = s_gis.bbox(gchq[0], gchq[1], 1 * km)
        self.eq(lbox, (51.890406796362754,
                       51.908393203637246,
                       -2.0928746526154747,
                       -2.0637253473845254))
