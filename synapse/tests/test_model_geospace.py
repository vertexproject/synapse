
from synapse.tests.common import *

class GeoTest(SynTest):

    def test_model_geospace_types(self):

        with self.getRamCore() as core:

            self.raises(BadTypeValu(core.getTypeNorm, 'geo:latlong', '91,100'))
            self.raises(BadTypeValu(core.getTypeNorm, 'geo:latlong', '-91,100'))
            self.raises(BadTypeValu(core.getTypeNorm, 'geo:latlong', '80,181'))
            self.raises(BadTypeValu(core.getTypeNorm, 'geo:latlong', '80,-181'))

            valu, subs = core.getTypeNorm('geo:latlong', '-88.12345678,101.12345678')
            self.eq(valu, '-88.12345678,101.12345678')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.02000000,101.1100000000')
            self.eq(valu, '-88.02,101.11')

            valu, subs = core.getTypeNorm('geo:dist', '11.2 km')
            self.eq(valu, 11200000)
