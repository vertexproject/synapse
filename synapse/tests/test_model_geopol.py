import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class GeoPolModelTest(s_t_utils.SynTest):

    async def test_forms_country(self):

        async with self.getTestCore() as core:

            flag = s_common.guid()
            country = s_common.guid()

            input_props = {'flag': flag, 'founded': 456, 'iso2': 'VI', 'iso3': 'VIS', 'isonum': 31337,
                           'name': 'Republic of Visi', 'tld': 'visi', 'pop': 123}
            expected_props = {'flag': flag, 'founded': 456, 'iso2': 'vi', 'iso3': 'vis', 'isonum': 31337,
                              'name': 'republic of visi', 'tld': 'visi', 'pop': 123}

            async with await core.snap() as snap:
                node = await snap.addNode('pol:country', country, props=input_props)

            for prop, valu in expected_props.items():
                self.eq(node.get(prop), valu)

    async def test_types_iso2(self):
        async with self.getTestCore() as core:
            t = core.model.type('pol:iso2')

            self.eq(t.norm('Fo'), ('fo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'A')
            self.raises(s_exc.BadTypeValu, t.norm, 'asD')

    async def test_types_iso3(self):
        async with self.getTestCore() as core:
            t = core.model.type('pol:iso3')

            self.eq(t.norm('Foo'), ('foo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'As')
            self.raises(s_exc.BadTypeValu, t.norm, 'asdF')
