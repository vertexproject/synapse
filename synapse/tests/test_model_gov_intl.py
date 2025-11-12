import synapse.tests.utils as s_t_utils

class IntlGovTest(s_t_utils.SynTest):

    async def test_models_intl(self):

        async with self.getTestCore() as core:
            q = 'return( $lib.trycast(gov:intl:un:m49, $valu) )'

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 1}})
            self.true(isok)
            self.eq(valu, 1)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 0}})
            self.false(isok)
            self.eq(valu, {
                'valu': 0,
                'type': 'gov:intl:un:m49',
                'errinfo': {
                    'valu': '0',
                    'name': 'gov:intl:un:m49',
                    'mesg': 'value is below min=1',
                },
            })

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': '999'}})
            self.true(isok)
            self.eq(valu, 999)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 1000}})
            self.false(isok)
            self.eq(valu, {
                'valu': 1000,
                'type': 'gov:intl:un:m49',
                'errinfo': {
                    'valu': '1000',
                    'name': 'gov:intl:un:m49',
                    'mesg': 'value is above max=999',
                },
            })
