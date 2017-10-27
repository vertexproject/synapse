
from synapse.tests.common import *

class GeoTest(SynTest):

    def test_model_geospace_types(self):

        with self.getRamCore() as core:

            #self.eq(core.getTypeNorm('geo:lat', '88.12345678')[0], 8812345678)
            #self.eq(core.getTypeNorm('geo:lat', '-88.12345678')[0], -8812345678)

            #self.eq(core.getTypeRepr('geo:lat', 8812345678), '88.12345678')
            #self.eq(core.getTypeRepr('geo:lat', -8812345678), '-88.12345678')

            #self.raises(BadTypeValu, core.getTypeNorm, 'geo:lat', '800')
            #self.raises(BadTypeValu, core.getTypeNorm, 'geo:lat', '-800')

            #self.eq(core.getTypeNorm('geo:long', '100.12345678')[0], 10012345678)
            #self.eq(core.getTypeNorm('geo:long', '-100.12345678')[0], -10012345678)

            #self.eq(core.getTypeRepr('geo:long', 10012345678), '100.12345678')
            #self.eq(core.getTypeRepr('geo:long', -10012345678), '-100.12345678')

            #self.raises(BadTypeValu, core.getTypeNorm, 'geo:long', '800')
            #self.raises(BadTypeValu, core.getTypeNorm, 'geo:long', '-800')

            valu, subs = core.getTypeNorm('geo:latlong', '-88.12345678,101.12345678')
            self.eq(valu, '-88.12345678,101.12345678')
            #self.eq(subs.get('lat'), -8812345678)
            #self.eq(subs.get('long'), 10112345678)

            valu, subs = core.getTypeNorm('geo:latlong', '-88.02000000,101.1100000000')
            self.eq(valu, '-88.02,101.11')

            valu, subs = core.getTypeNorm('geo:dist', '11.2 km')
            self.eq(valu, 11200000)
