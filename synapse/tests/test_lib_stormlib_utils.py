import synapse.exc as s_exc
import synapse.tests.utils as s_test

class UtilsTest(s_test.SynTest):

    async def test_lib_stormlib_utils_todo(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('return($lib.utils.todo(foo))')
            self.eq(valu, ('foo', (), {}))

            valu = await core.callStorm('return($lib.utils.todo(fooName, arg1, arg2, keyword=bar, anotherkeyword=hehe))')
            self.eq(valu, ('fooName', ('arg1', 'arg2'), {'keyword': 'bar', 'anotherkeyword': 'hehe'}))
