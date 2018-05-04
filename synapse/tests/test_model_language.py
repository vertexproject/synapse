import synapse.exc as s_exc
import synapse.tests.common as s_t_common

class LangModuleTest(s_t_common.SynTest):

    def test_forms_idiom(self):
        with self.getTestCore() as core:
            formname = 'lang:idiom'
            valu = 'arbitrary text 123'

            input_props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_props = {'url': 'https://vertex.link/', 'desc:en': 'Some English Desc'}
            expected_ndef = (formname, valu)

            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu, props=input_props)

            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

    def test_forms_trans(self):
        with self.getTestCore() as core:
            formname = 'lang:trans'
            valu = 'arbitrary text 123'

            input_props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}
            expected_ndef = (formname, valu)

            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu, props=input_props)

            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

    def test_types_unextended(self):
        # The following types are subtypes that do not extend their base type
        with self.getTestCore() as core:
            self.nn(core.model.type('lang:idiom'))  # str
            self.nn(core.model.type('lang:trans'))  # str
