from synapse.tests.utils import SynTest

class IntlGovTest(SynTest):

    async def test_models_intl(self):

        async with self.getTestCore() as core:
            q = 'return( $lib.trycast(gov:intl:un:m49, $valu) )'

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 1}})
            self.true(isok)
            self.eq(valu, 1)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 0}})
            self.false(isok)
            self.none(valu)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': '999'}})
            self.true(isok)
            self.eq(valu, 999)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 1000}})
            self.false(isok)
            self.none(valu)
