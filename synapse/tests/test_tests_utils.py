import synapse.exc as s_exc
import synapse.tests.utils as s_test

class TestTestsTest(s_test.SynTest):

    async def test_tests_storm(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('foo.bar')

            with self.raises(s_exc.SynErr):
                self.stormHasNoErr(msgs)

            with self.raises(s_exc.SynErr):
                self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('$lib.warn(woot)')

            with self.raises(s_exc.SynErr):
                self.stormHasNoWarnErr(msgs)
