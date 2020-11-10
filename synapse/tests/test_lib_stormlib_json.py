import synapse.exc as s_exc

import synapse.tests.utils as s_test

class JsonTest(s_test.SynTest):

    async def test_stormlib_json(self):

        async with self.getTestCore() as core:

            self.eq(((1, 2, 3)), await core.callStorm('return($lib.json.load("[1, 2, 3]"))'))
            self.eq(('["foo", "bar", "baz"]'), await core.callStorm('return($lib.json.save((foo, bar, baz)))'))

            with self.raises(s_exc.BadJsonText):
                await core.callStorm('return($lib.json.load(foo))')

            with self.raises(s_exc.MustBeJsonSafe):
                await core.callStorm('return($lib.json.save($lib.print))')
