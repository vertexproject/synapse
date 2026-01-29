import math
import synapse.tests.utils as s_t_utils

import synapse.lib.gis as s_gis

# earth mean radius in mm
r = 6371008800

ratios = {
    'cm': 10.0,
    'm': 1000.0,
    'km': 1000000.0,
}

km = 1000000.0  # using mm as base units
gchq = (51.8994, -2.0783)

class GisTest(s_t_utils.SynTest):

    def test_lib_gis_haversine(self):
        px = (36.12, -86.67)
        py = (33.94, -118.40)
        self.eqish(s_gis.haversine(px, py), 2886448429.7648544)

        # Test haversinve value from rosetta code
        r = s_gis.haversine((36.12, -86.67), (33.94, -118.40), 6372.8)
        e = 2887.2599506071106
        self.eqish(r, e)

        # Test against 1/4th of a unit sphere
        r = s_gis.haversine((45, 45), (-45, 45), 1.0)
        e = math.pi / 2
        # We are typically within the machine-epsilon range for this test
        self.assertAlmostEqual(r, e)

        # Test against the haversine package
        lyon = (45.7597, 4.8422)
        paris = (48.8567, 2.3508)
        r = s_gis.haversine(lyon, paris, r=6371)
        e = 392.21671780659625
        self.assertAlmostEqual(r, e)

    def test_lib_gis_latlong(self):
        self.assertRaises(ValueError, s_gis.latlong, 'hehe')
        self.assertRaises(ValueError, s_gis.latlong, 'hehe,hoho')

        self.eq(s_gis.latlong(' 0,0 '), (0.0, 0.0))
        self.eq(s_gis.latlong('-0,0 '), (0.0, 0.0))
        self.eq(s_gis.latlong('50,100 '), (50.0, 100.0))
        self.eq(s_gis.latlong('-50,100 '), (-50.0, 100.0))
        self.eq(s_gis.latlong('-50,-100 '), (-50.0, -100.0))
        self.eq(s_gis.latlong('50,-100 '), (50.0, -100.0))

        self.eq(s_gis.latlong(' 0.12345678901234567890,-0.12345678901234567890 '), (0.12345678901234568, -0.12345678901234568))  # Note precision

        self.eq(s_gis.latlong('123.456,-987.654 '), (123.456, -987.654))  # Note Invalid coords

    def test_lib_gis_near(self):
        point = (0.0, 0.0)
        dist = 0
        points = []
        self.false(s_gis.near(point, dist, points))  # no points

        point = (0.0, 0.0)
        dist = 0
        points = [(0.0, 0.0)]
        self.true(s_gis.near(point, dist, points))  # same point

        point = (0.0, 0.0)
        dist = 0
        points = [(50.0, 50.0), (0.0, 0.0)]
        self.true(s_gis.near(point, dist, points))  # far point and same point

        point = (45.7597, 4.8422)  # lyon
        dist = 400000000  # actual haversine distance between lyon/paris is ~392217259mm
        points = [(0.0, 0.0), (48.8567, 2.3508)]  # 0,0 and paris
        self.true(s_gis.near(point, dist, points))

        point = (45.7597, 4.8422)  # lyon
        dist = 391000000  # actual haversine distance between lyon/paris is ~392217259mm
        points = [(0.0, 0.0), (48.8567, 2.3508)]  # 0,0 and paris
        self.false(s_gis.near(point, dist, points))

    def test_lib_gis_dms2dec(self):
        self.eqish(s_gis.dms2dec(45, 46, 52), 45.78111111111111)

    def test_lib_gis_bbox(self):
        lbox = s_gis.bbox(gchq[0], gchq[1], 1 * km)
        self.eq(lbox, (51.890406796362754,
                       51.908393203637246,
                       -2.0928746526154747,
                       -2.0637253473845254))
