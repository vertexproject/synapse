import synapse.tests.common as s_test

import unittest
raise unittest.SkipTest('FILE MODEL')

class GeoTest(s_test.SynTest):

    def test_model_geospace_types_latlong(self):

        with self.getRamCore() as core:

            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '91,100')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '-91,100')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '80,181')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '80,-181')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', 'hehe,hoho')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.12345678,101.12345678')
            self.eq(valu, '-88.12345678,101.12345678')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.02000000,101.1100000000')
            self.eq(valu, '-88.02,101.11')

            valu, subs = core.getTypeNorm('geo:latlong', '??')
            self.eq(valu, '??')

    def test_model_geospace_types_dist(self):

        with self.getRamCore() as core:

            valu, subs = core.getTypeNorm('geo:dist', '11.2 km')
            self.eq(valu, 11200000)

            valu, subs = core.getTypeNorm('geo:dist', 11200000)
            self.eq(valu, 11200000)

            self.raises(BadTypeValu, core.getTypeNorm, 'geo:dist', '1.3 pc')

    def test_model_geospace_nloc(self):

        with self.getRamCore() as core:

            item = core.formTufoByProp('mat:item', '7ea768402eae63c9378f4e3805f4d0d3')

            valu = ('mat:item:latlong', item[1].get('node:ndef'), '44.0429075,4.8828757', '20160403')

            node = core.formTufoByProp('geo:nloc', valu)
            self.eq(node[1].get('geo:nloc:time'), 1459641600000)
            self.eq(node[1].get('geo:nloc:prop'), 'mat:item:latlong')
            self.eq(node[1].get('geo:nloc:ndef'), '15533769b23efcb12d126a53f9b804ee')
            self.eq(node[1].get('geo:nloc:latlong'), '44.0429075,4.8828757')
