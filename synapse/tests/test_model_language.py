import synapse.tests.utils as s_t_utils

class LangModuleTest(s_t_utils.SynTest):

    async def test_forms_idiom(self):
        async with self.getTestCore() as core:
            formname = 'lang:idiom'
            valu = 'arbitrary text 123'

            input_props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_ndef = (formname, valu)

            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)

            self.eq(node.ndef, expected_ndef)
            for prop, valu in expected_props.items():
                self.eq(node.get(prop), valu)

    async def test_forms_trans(self):
        async with self.getTestCore() as core:
            formname = 'lang:trans'
            valu = 'arbitrary text 123'

            input_props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_ndef = (formname, valu)

            async with await core.snap() as snap:
                node = await snap.addNode(formname, valu, props=input_props)

            self.eq(node.ndef, expected_ndef)
            for prop, valu in expected_props.items():
                self.eq(node.get(prop), valu)

    async def test_types_unextended(self):
        # The following types are subtypes that do not extend their base type
        async with self.getTestCore() as core:
            self.nn(core.model.type('lang:idiom'))  # str
            self.nn(core.model.type('lang:trans'))  # str
