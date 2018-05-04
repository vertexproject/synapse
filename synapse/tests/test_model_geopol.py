import synapse.exc as s_exc
import synapse.tests.common as s_t_common


class GeoPolModelTest(s_t_common.SynTest):

    def test_forms_country(self):
        with self.getTestCore() as core:
            formname = 'pol:country'
            guid = 32 * '0'
            flag_valu = 64 * 'f'

            input_props = {'flag': flag_valu, 'founded': 456, 'iso2': 'VI', 'iso3': 'VIS', 'isonum': 31337,
                'name': 'Republic of Visi', 'tld': 'visi', 'pop': 123}
            expected_props = {'flag': flag_valu, 'founded': 456, 'iso2': 'vi', 'iso3': 'vis', 'isonum': 31337,
                'name': 'republic of visi', 'tld': 'visi', 'pop': 123}
            expected_ndef = (formname, guid)

            with core.xact(write=True) as xact:
                node = xact.addNode(formname, guid, props=input_props)

            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

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
            self.nn(core.model.type('pol:country'))  # guid
            self.nn(core.model.type('pol:isonum'))  # int
