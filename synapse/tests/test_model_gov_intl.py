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
            self.eq(valu['err'], 'BadTypeValu')
            self.true(valu['errfile'].endswith('synapse/lib/types.py'))
            self.eq(valu['errinfo'], {
                'mesg': 'value is below min=1',
                'name': 'gov:intl:un:m49',
                'valu': '0',
            })
            self.gt(valu['errline'], 0)
            self.eq(valu['errmsg'], "BadTypeValu: mesg='value is below min=1' name='gov:intl:un:m49' valu='0'")

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': '999'}})
            self.true(isok)
            self.eq(valu, 999)

            isok, valu = await core.callStorm(q, opts={'vars': {'valu': 1000}})
            self.false(isok)
            self.eq(valu['err'], 'BadTypeValu')
            self.true(valu['errfile'].endswith('synapse/lib/types.py'))
            self.eq(valu['errinfo'], {
                'mesg': 'value is above max=999',
                'name': 'gov:intl:un:m49',
                'valu': '1000',
            })
            self.gt(valu['errline'], 0)
            self.eq(valu['errmsg'], "BadTypeValu: mesg='value is above max=999' name='gov:intl:un:m49' valu='1000'")
