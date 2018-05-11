import synapse.exc as s_exc
import synapse.tests.common as s_t_common

class GeoPolModelTest(s_t_common.SynTest):

    def test_country(self):
        formname = 'pol:country'
        self.nn(core.model.type(formname))
        with self.getTestCore() as core:
            self.perform_basic_form_assertions(core, formname)

    def test_types_iso2(self):
        with self.getTestCore() as core:
            t = core.model.type('pol:iso2')

            self.eq(t.norm('Fo'), ('fo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'A')
            self.raises(s_exc.BadTypeValu, t.norm, 'asD')

    def test_types_iso3(self):
        with self.getTestCore() as core:
            t = core.model.type('pol:iso3')

            self.eq(t.norm('Foo'), ('foo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'As')
            self.raises(s_exc.BadTypeValu, t.norm, 'asdF')

    def test_types_unextended(self):
        # The following types are subtypes that do not extend their base type
        with self.getTestCore() as core:
            self.nn(core.model.type('pol:isonum'))  # int
