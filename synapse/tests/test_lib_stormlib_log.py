import synapse.exc as s_exc

import synapse.tests.utils as s_test

logname = 'synapse.storm.log'


class LogTest(s_test.SynTest):

    async def test_stormlib_log(self):

        async with self.getTestCore() as core:
            # Raw message
            with self.getAsyncLoggerStream(logname, 'debug message') as stream:
                await core.callStorm('$lib.log.debug("debug message")')
                self.true(await stream.wait(6))
            with self.getAsyncLoggerStream(logname, 'info message') as stream:
                await core.callStorm('$lib.log.info("info message")')
                self.true(await stream.wait(6))
            with self.getAsyncLoggerStream(logname, 'warn message') as stream:
                await core.callStorm('$lib.log.warning("warn message")')
                self.true(await stream.wait(6))
            with self.getAsyncLoggerStream(logname, 'error message') as stream:
                await core.callStorm('$lib.log.error("error message")')
                self.true(await stream.wait(6))

            # Extra without structlog handler in place has no change in results
            with self.getAsyncLoggerStream(logname, 'debug message') as stream:
                await core.callStorm('$lib.log.debug("debug message", extra=({"key": "valu"}))')
                self.true(await stream.wait(6))
            stream.seek(0)
            self.eq(stream.read(), 'debug message\n')

            # Extra can be empty too
            with self.getAsyncLoggerStream(logname, 'debug message') as stream:
                await core.callStorm('$lib.log.debug("debug message", extra=({}))')
                self.true(await stream.wait(6))
            stream.seek(0)
            self.eq(stream.read(), 'debug message\n')

            # Extra must be a dict after toprim is called on him.
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.log.debug("debug message", extra=(foo, bar, baz))')

            # structlog test
            with self.getStructuredAsyncLoggerStream(logname, '"key":"valu"') as stream:
                await core.callStorm('$lib.log.debug("struct1 message")')
                await core.callStorm('$lib.log.debug("struct2 message", extra=({"key": "valu"}))')
                self.true(await stream.wait(6))
            msgs = stream.jsonlines()
            self.len(2, msgs)
            mesg = msgs[0]
            self.eq(mesg.get('logger').get('name'), 'synapse.storm.log')
            self.eq(mesg.get('message'), 'struct1 message')
            self.none(mesg.get('key'))

            mesg = msgs[1]
            self.eq(mesg.get('logger').get('name'), 'synapse.storm.log')
            self.eq(mesg.get('message'), 'struct2 message')
            self.eq(mesg.get('key'), 'valu')
