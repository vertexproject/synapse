
from synapse.tests.common import *

class GeoTest(SynTest):

    def test_model_geospace_types(self):

        with self.getRamCore() as core:

            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '91,100')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '-91,100')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '80,181')
            self.raises(BadTypeValu, core.getTypeNorm, 'geo:latlong', '80,-181')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.12345678,101.12345678')
            self.eq(valu, '-88.12345678,101.12345678')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.02000000,101.1100000000')
            self.eq(valu, '-88.02,101.11')

            valu, subs = core.getTypeNorm('geo:dist', '11.2 km')
            self.eq(valu, 11200000)

    #def test_model_geospace_place(self):
        #with self.getRamCore() as core:

    def test_model_geospace_nloc(self):

        with self.getRamCore() as core:

            item = core.formTufoByProp('mat:item', '7ea768402eae63c9378f4e3805f4d0d3')

            valu = ('mat:item', item[1].get('node:ndef'), '44.0429075,4.8828757', '20160403')

            node = core.formTufoByProp('geo:nloc', valu)
            self.eq(node[1].get('geo:nloc:prop'), 'mat:item')
            self.eq(node[1].get('geo:nloc:ndef'), '15533769b23efcb12d126a53f9b804ee')
            self.eq(node[1].get('geo:nloc:locn'), '44.0429075,4.8828757')
            self.eq(node[1].get('geo:nloc:time'), 1459641600000)
