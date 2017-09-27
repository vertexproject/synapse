from synapse.tests.common import *

class LangTest(SynTest):

    def test_model_language_trans(self):
        with self.getRamCore() as core:

            self.nn(core.getTufoByProp('syn:type', 'lang:trans'))
            self.nn(core.getTufoByProp('syn:form', 'lang:trans'))

            props = {'text:en': 'Some English Text', 'desc:en': 'Some English Desc'}

            node = core.formTufoByProp('lang:trans', 'Some Non English Text', **props)
            self.eq(node[1].get('lang:trans:text:en'), 'Some English Text')
            self.eq(node[1].get('lang:trans:desc:en'), 'Some English Desc')

    def test_model_language_idiom(self):
        with self.getRamCore() as core:

            self.nn(core.getTufoByProp('syn:type', 'lang:idiom'))
            self.nn(core.getTufoByProp('syn:form', 'lang:idiom'))

            props = {'desc:en': 'Bawk Bawk', 'url': 'http://test.com/'}

            node = core.formTufoByProp('lang:idiom', 'meat chicken', **props)
            self.eq(node[1].get('lang:idiom:url'), 'http://test.com/')
            self.eq(node[1].get('lang:idiom:desc:en'), 'Bawk Bawk')

    #def test_model_language_tags(self):
