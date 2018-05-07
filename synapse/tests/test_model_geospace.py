import synapse.exc as s_exc
import synapse.tests.common as s_t_common

class GeoTest(s_t_common.SynTest):

    def test_latlong(self):
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

    def test_dist(self):

        formname = 'geo:dist'
        with self.getTestCore() as core:
            t = core.model.type(formname)

            self.eq(t.norm('11.2 km'), (11200000.0, {}))
            self.eq(t.norm(11200000), (11200000.0, {}))

            self.raises(s_exc.BadTypeValu, t.norm, '1.3 pc')

    def test_nloc(self):
        pass  # FIXME can't test until syn:prop is done
        '''
        with self.getRamCore() as core:

            item = core.formTufoByProp('mat:item', '7ea768402eae63c9378f4e3805f4d0d3')

            valu = ('mat:item:latlong', item[1].get('node:ndef'), '44.0429075,4.8828757', '20160403')

            node = core.formTufoByProp('geo:nloc', valu)
            self.eq(node[1].get('geo:nloc:time'), 1459641600000)
            self.eq(node[1].get('geo:nloc:prop'), 'mat:item:latlong')
            self.eq(node[1].get('geo:nloc:ndef'), '15533769b23efcb12d126a53f9b804ee')
            self.eq(node[1].get('geo:nloc:latlong'), '44.0429075,4.8828757')
        '''
