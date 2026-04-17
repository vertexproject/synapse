import math

import synapse.exc as s_exc

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

    def test_lib_gis_parseDMS(self):
        deg = '°'

        # Standard symbol-based DMS
        self.eqish(s_gis.parseDMS(f'45{deg}46\'52"N'), 45.78111111111111)
        self.eqish(s_gis.parseDMS(f'45{deg}46\'52"S'), -45.78111111111111)
        self.eqish(s_gis.parseDMS(f'13{deg}30\'45"E'), 13.5125)
        self.eqish(s_gis.parseDMS(f'13{deg}30\'45"W'), -13.5125)

        # Letter-based separators (d for degrees, m for minutes)
        self.eqish(s_gis.parseDMS('45d46m52N'), 45.78111111111111)
        self.eqish(s_gis.parseDMS('13d30m45E'), 13.5125)

        # Space-separated
        self.eqish(s_gis.parseDMS('45 46 52 N'), 45.78111111111111)
        self.eqish(s_gis.parseDMS('13 30 45 E'), 13.5125)

        # No seconds
        self.eqish(s_gis.parseDMS(f'45{deg}46\'N'), 45.766666666666666)

        # Negative sign (no direction letter)
        self.eqish(s_gis.parseDMS(f'-45{deg}46\'52"'), -45.78111111111111)

        # Direction prefix
        self.eqish(s_gis.parseDMS(f'N45{deg}46\'52"'), 45.78111111111111)
        self.eqish(s_gis.parseDMS(f'S45{deg}46\'52"'), -45.78111111111111)

        # Zero
        self.eqish(s_gis.parseDMS(f'0{deg}0\'0"N'), 0.0)

        # Fractional seconds
        self.eqish(s_gis.parseDMS(f'45{deg}46\'52.5"N'), 45.78125)

        # Error: unparseable
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, 'not a coordinate')

        # Error: conflicting negative sign and S/W direction
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, f'-45{deg}46\'52"S')

        # Error: minutes >= 60
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, f'45{deg}60\'0"N')

        # Error: seconds >= 60
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, f'45{deg}46\'60"N')

        # Error: conflicting prefix and suffix directions
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, f'N45{deg}46\'52"S')
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, f'E13{deg}30\'45"W')
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, 'N 1 2 3 S')
        self.raises(s_exc.BadTypeValu, s_gis.parseDMS, 'E 3 4 5 W')

    def test_lib_gis_parseLatLong(self):
        deg = '°'

        # Comma-separated
        lat, lon = s_gis.parseLatLong(f'45{deg}46\'52"N, 13{deg}30\'45"E')
        self.eqish(lat, 45.78111111111111)
        self.eqish(lon, 13.5125)

        # Comma-separated with S/W directions
        lat, lon = s_gis.parseLatLong(f'45{deg}46\'52"S, 13{deg}30\'45"W')
        self.eqish(lat, -45.78111111111111)
        self.eqish(lon, -13.5125)

        # No comma - split on N/S boundary
        lat, lon = s_gis.parseLatLong(f'45{deg}46\'52"N 13{deg}30\'45"E')
        self.eqish(lat, 45.78111111111111)
        self.eqish(lon, 13.5125)

        # Semicolon separator
        lat, lon = s_gis.parseLatLong(f'45{deg}46\'52"N; 13{deg}30\'45"E')
        self.eqish(lat, 45.78111111111111)
        self.eqish(lon, 13.5125)

        # Error: same direction class in both parts (N/S in lon, or E/W in lat)
        self.raises(s_exc.BadTypeValu, s_gis.parseLatLong, '1 2 3N, 4 5 6N')
        self.raises(s_exc.BadTypeValu, s_gis.parseLatLong, '1 2 3E, 4 5 6E')

        # Error: conflicting prefix and suffix in a single part (propagates from parseDMS)
        self.raises(s_exc.BadTypeValu, s_gis.parseLatLong, 'N 1 2 3S, E 3 4 5W')

        # Error: unparseable
        self.raises(s_exc.BadTypeValu, s_gis.parseLatLong, 'not a lat long')

    def test_lib_gis_bbox(self):
        lbox = s_gis.bbox(gchq[0], gchq[1], 1 * km)
        self.eq(lbox, (51.890406796362754,
                       51.908393203637246,
                       -2.0928746526154747,
                       -2.0637253473845254))
