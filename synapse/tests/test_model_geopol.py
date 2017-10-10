import synapse.cortex as s_cortex

from synapse.tests.common import *

class GeopolModelTest(SynTest):

    def test_model_geopol_iso2(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeNorm('pol:iso2', 'FO'), ('fo', {}))
            self.eq(core.getTypeParse('pol:iso2', 'FO'), ('fo', {}))
            self.raises(BadTypeValu, core.getTypeNorm, 'pol:iso2', 'asdf')
            self.raises(BadTypeValu, core.getTypeParse, 'pol:iso2', 'asdf')

    def test_model_geopol_iso3(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeNorm('pol:iso3', 'FOO'), ('foo', {}))
            self.eq(core.getTypeParse('pol:iso3', 'FOO'), ('foo', {}))
            self.raises(BadTypeValu, core.getTypeNorm, 'pol:iso3', 'asdf')
            self.raises(BadTypeValu, core.getTypeParse, 'pol:iso3', 'asdf')

    def test_model_geopol_isonum(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeNorm('pol:isonum', 10), (10, {}))
            self.eq(core.getTypeParse('pol:isonum', '10')[0], 10)
            self.raises(BadTypeValu, core.getTypeNorm, 'pol:isonum', 'asdf')
            self.raises(BadTypeValu, core.getTypeParse, 'pol:isonum', 'asdf')

    def test_model_geopol_country(self):
        with self.getRamCore() as core:
            props = {'iso2': 'VI', 'iso3': 'VIS', 'isonum': 31337}
            t0 = core.formTufoByProp('pol:country', guid(), name='Republic of Visi', **props)
            self.eq(t0[1].get('pol:country:name'), 'republic of visi')
            self.eq(t0[1].get('pol:country:iso2'), 'vi')
            self.eq(t0[1].get('pol:country:iso3'), 'vis')
            self.eq(t0[1].get('pol:country:isonum'), 31337)
