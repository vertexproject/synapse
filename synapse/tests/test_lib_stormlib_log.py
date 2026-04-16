import synapse.exc as s_exc

import synapse.tests.utils as s_test

logname = 'synapse.storm.log'


class LogTest(s_test.SynTest):

    async def test_stormlib_log(self):

        async with self.getTestCore() as core:
            # Raw message
            with self.getLoggerStream(logname, 'debug message') as stream:

                await core.callStorm('$lib.log.debug("debug message")')
                await stream.expect('debug message', timeout=6)

                await core.callStorm('$lib.log.info("info message")')
                await stream.expect('info message', timeout=6)

                await core.callStorm('$lib.log.warning("warn message")')
                await stream.expect('warn message', timeout=6)

                await core.callStorm('$lib.log.error("error message")')
                await stream.expect('error message', timeout=6)

                await core.callStorm('$lib.log.debug("debug message", extra=({"key": "valu"}))')
                await stream.expect('debug message', timeout=6)
                await stream.expect('"key":"valu"', timeout=6)

            # Extra must be a dict after toprim is called on him.
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.log.debug("debug message", extra=(foo, bar, baz))')

            mesg = stream.jsonlines()[-1]

            self.eq(mesg.get('logger').get('name'), 'synapse.storm.log')
            self.eq(mesg.get('message'), 'debug message')
            self.eq(mesg['params'].get('key'), 'valu')
