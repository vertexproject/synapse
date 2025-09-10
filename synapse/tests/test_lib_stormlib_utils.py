import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class UtilsTest(s_test.SynTest):

    async def test_lib_stormlib_utils_buid(self):
        async with self.getTestCore() as core:
            obj = ('meta:source', '0123456789abcdef0123456789abcdef')
            self.eq(
                await core.callStorm('return($lib.utils.buid($obj))', opts={'vars': {'obj': obj}}),
                s_common.buid(obj)
            )

    async def test_lib_stormlib_utils_todo(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('return($lib.utils.todo(foo))')
            self.eq(valu, ('foo', (), {}))

            valu = await core.callStorm('return($lib.utils.todo(fooName, arg1, arg2, keyword=bar, anotherkeyword=hehe))')
            self.eq(valu, ('fooName', ('arg1', 'arg2'), {'keyword': 'bar', 'anotherkeyword': 'hehe'}))
