import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.common as s_t_common

class GeoTest(s_t_common.SynTest):

    def test_types_forms(self):
        formlat = 'geo:latitude'
        formlon = 'geo:longitude'
        formlatlon = 'geo:latlong'

        with self.getTestCore() as core:

            # Latitude Type Tests =====================================================================================
            t = core.model.type(formlat)
            self.raises(s_exc.BadTypeValu, t.norm, '-90.1')
            self.eq(t.norm('-90')[0], -90.0)
            self.eq(t.norm('-12.345678901234567890')[0], -12.3456789)
            self.eq(t.norm('-0')[0], 0.0)
            self.eq(t.norm('0')[0], 0.0)
            self.eq(t.norm('12.345678901234567890')[0], 12.3456789)
            self.eq(t.norm('90')[0], 90.0)
            self.raises(s_exc.BadTypeValu, t.norm, '90.1')
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')

            self.eq(t.indx(-90), b'\x00\x00\x00\x00\x00')  # index starts at 0 and goes to 9000000000
            self.eq(t.indx(-12.34567890123456789), b'\x01\xce\xdb\x17-')
            self.eq(t.indx(0), b'\x02\x18q\x1a\x00')
            self.eq(t.indx(12.34567890123456789), b'\x02b\x07\x1c\xd2')
            self.eq(t.indx(90), b'\x040\xe24\x00')

            # Longitude Type Tests =====================================================================================
            t = core.model.type(formlon)
            self.raises(s_exc.BadTypeValu, t.norm, '-180.1')
            self.eq(t.norm('-180')[0], -180.0)
            self.eq(t.norm('-12.345678901234567890')[0], -12.3456789)
            self.eq(t.norm('-0')[0], 0.0)
            self.eq(t.norm('0')[0], 0.0)
            self.eq(t.norm('12.345678901234567890')[0], 12.3456789)
            self.eq(t.norm('180')[0], 180.0)
            self.raises(s_exc.BadTypeValu, t.norm, '180.1')
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')

            self.eq(t.indx(-180), b'\x00\x00\x00\x00\x00')  # index starts at 0 and goes to 18000000000
            self.eq(t.indx(-12.34567890123456789), b'\x03\xe7L1-')
            self.eq(t.indx(0), b'\x040\xe24\x00')
            self.eq(t.indx(12.34567890123456789), b'\x04zx6\xd2')
            self.eq(t.indx(180), b'\x08a\xc4h\x00')

            # Latlong Type Tests =====================================================================================
            t = core.model.type(formlatlon)
            self.eq(t.norm('0,-0'), ((0.0, 0.0), {'subs': {'lat': 0.0, 'lon': 0.0}}))
            self.eq(t.norm('89.999,179.999'), ((89.999, 179.999), {'subs': {'lat': 89.999, 'lon': 179.999}}))
            self.eq(t.norm('-89.999,-179.999'), ((-89.999, -179.999), {'subs': {'lat': -89.999, 'lon': -179.999}}))

            self.eq(t.norm([89.999, 179.999]), ((89.999, 179.999), {'subs': {'lat': 89.999, 'lon': 179.999}}))
            self.eq(t.norm((89.999, 179.999)), ((89.999, 179.999), {'subs': {'lat': 89.999, 'lon': 179.999}}))

            self.raises(s_exc.BadTypeValu, t.norm, '-91,0')
            self.raises(s_exc.BadTypeValu, t.norm, '91,0')
            self.raises(s_exc.BadTypeValu, t.norm, '0,-181')
            self.raises(s_exc.BadTypeValu, t.norm, '0,181')
            self.raises(s_exc.BadTypeValu, t.norm, ('newp', 'newp', 'still newp'))

            # Demonstrate precision
            self.eq(t.norm('12.345678,-12.345678'),
                ((12.345678, -12.345678), {'subs': {'lat': 12.345678, 'lon': -12.345678}}))
            self.eq(t.norm('12.3456789,-12.3456789'),
                ((12.3456789, -12.3456789), {'subs': {'lat': 12.3456789, 'lon': -12.3456789}}))
            self.eq(t.norm('12.34567890,-12.34567890'),
                ((12.3456789, -12.3456789), {'subs': {'lat': 12.3456789, 'lon': -12.3456789}}))

            self.eq(t.indx((-90, -180)), b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            self.eq(t.indx((90, 180)), b'\x040\xe24\x00\x08a\xc4h\x00')

            self.eq(t.indx((0, 0)), b'\x02\x18q\x1a\x00\x040\xe24\x00')
            self.eq(t.indx((0, -0)), b'\x02\x18q\x1a\x00\x040\xe24\x00')
            self.eq(t.indx((0, 1)), b'\x02\x18q\x1a\x00\x046\xd8\x15\x00')
            self.eq(t.indx((0, -1)), b'\x02\x18q\x1a\x00\x04*\xecS\x00')
            self.eq(t.indx((-90, 180)), b'\x00\x00\x00\x00\x00\x08a\xc4h\x00')
            self.eq(t.indx((90, -180)), b'\x040\xe24\x00\x00\x00\x00\x00\x00')
            self.eq(t.indx((12.3456789, -12.3456789)), b'\x02b\x07\x1c\xd2\x03\xe7L1.')
            self.eq(t.indx((12.34567890, -12.34567890)), b'\x02b\x07\x1c\xd2\x03\xe7L1.')

            self.eq(t.repr((0, 0)), '0,0')
            self.eq(t.repr((0, -0)), '0,0')
            self.eq(t.repr((12.345678, -12.345678)), '12.345678,-12.345678')

            # Geo-dist tests
            formname = 'geo:dist'
            t = core.model.type(formname)

            self.eq(t.norm('100km')[0], 100000000)
            self.eq(t.norm('100     km')[0], 100000000)
            self.eq(t.norm('837.33 m')[0], 837330)
            self.eq(t.norm('11.2 km'), (11200000, {}))
            self.eq(t.norm(11200000), (11200000, {}))

            self.eq(t.repr(5), '5 mm')
            self.eq(t.repr(500), '50.0 cm')
            self.eq(t.repr(1000), '1.0 m')
            self.eq(t.repr(10000), '10.0 m')
            self.eq(t.repr(1000000), '1.0 km')

            self.raises(s_exc.BadTypeValu, t.norm, '1.3 pc')

            # geo:nloc
            formname = 'geo:nloc'
            t = core.model.type(formname)

            ndef = ('inet:ipv4', '0.0.0.0')
            latlong = ('0.000000000', '0')
            stamp = -0

            with core.snap() as snap:
                node = snap.addNode('geo:nloc', (ndef, latlong, stamp))
                self.eq(node.ndef[1], (('inet:ipv4', 0), (0.0, 0.0), stamp))
                self.eq(node.get('ndef'), ('inet:ipv4', 0))
                self.eq(node.get('ndef:form'), 'inet:ipv4')
                self.eq(node.get('latlong'), (0.0, 0.0))
                self.eq(node.get('time'), 0)
                self.nn(snap.getNodeByNdef(('inet:ipv4', 0)))

            # geo:place

            # test inline tuple/float with negative syntax...
            node = list(core.eval('[ geo:place="*" :latlong=(-30.0,20.22) ]'))[0]
            self.eq(node.get('latlong'), (-30.0, 20.22))

            with core.snap() as snap:
                guid = s_common.guid()
                props = {'name': 'Vertex  HQ',
                         'desc': ' The place where Vertex Project hangs out        at! ',
                         'loc': 'us.hehe.haha',
                         'latlong': '34.1341, -118.3215',
                         'radius': '1.337km'}
                node = snap.addNode('geo:place', guid, props)
                self.eq(node.ndef[1], guid)
                self.eq(node.get('name'), 'vertex hq')
                self.eq(node.get('loc'), 'us.hehe.haha')
                self.eq(node.get('latlong'), (34.13409999, -118.3215))
                self.eq(node.get('radius'), 1337000)
                self.eq(node.get('desc'), 'the place where vertex project hangs out at!')
