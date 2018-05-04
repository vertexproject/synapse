
import synapse.exc as s_exc
import synapse.lib.module as s_module

from synapse.tests.common import SynTest

testmodel = {

    'types': (
        ('fakem49', ('gov:intl:un:m49', {}), {'doc': 'A fake int type.'}),
    ),

    'forms': (
        ('fakem49', {}, ()),
    ),

}

class TestModule(s_module.CoreModule):

    def initCoreModule(self):
        pass

    def getModelDefs(self):
        return (
            ('test', testmodel),
        )

class IntlGovTest(SynTest):

    def test_models_intl(self):

        with self.getTestCore() as core:

            core.addCoreMods(['synapse.tests.test_model_gov_intl.TestModule'])

            formname = 'fakem49'
            expected_ndef = (formname, 17)
            with core.xact(write=True) as xact:
                self.raises(s_exc.BadTypeValu, xact.addNode, formname, 3417)
                self.raises(s_exc.BadTypeValu, xact.addNode, formname, 0)
                n0 = xact.addNode(formname, 17)

            self.eq(n0.ndef, expected_ndef)
