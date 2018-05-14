
import synapse.exc as s_exc

from synapse.tests.common import SynTest

testmodel = (
    (
        'test',
        {
            'types': (
                ('fakem49', ('gov:intl:un:m49', {}), {'doc': 'A fake int type.'}),
            ),

            'forms': (
                ('fakem49', {}, ()),
            ),
        }
    ),
)

class IntlGovTest(SynTest):

    def test_models_intl(self):

        with self.getTestCore() as core:

            core.model.addDataModels(testmodel)

            formname = 'fakem49'
            expected_ndef = (formname, 17)
            with core.snap(write=True) as snap:
                self.raises(s_exc.BadTypeValu, snap.addNode, formname, 3417)
                self.raises(s_exc.BadTypeValu, snap.addNode, formname, 0)
                n0 = snap.addNode(formname, 17)

            self.eq(n0.ndef, expected_ndef)
