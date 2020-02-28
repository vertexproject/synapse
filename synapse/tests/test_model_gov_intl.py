import synapse.exc as s_exc

from synapse.tests.utils import SynTest

testmodel = (
    (
        'test',
        {
            'types': (
                ('fake:m49', ('gov:intl:un:m49', {}), {'doc': 'A fake int type.'}),
            ),

            'forms': (
                ('fake:m49', {}, ()),
            ),
        }
    ),
)

class IntlGovTest(SynTest):

    async def test_models_intl(self):

        async with self.getTestCore() as core:

            core.model.addDataModels(testmodel)

            formname = 'fake:m49'
            expected_ndef = (formname, 17)
            async with await core.snap() as snap:
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode(formname, 3417))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode(formname, 0))
                n0 = await snap.addNode(formname, 17)

            self.eq(n0.ndef, expected_ndef)
