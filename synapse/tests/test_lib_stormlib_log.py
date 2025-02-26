import synapse.exc as s_exc

import synapse.tests.utils as s_test

logname = 'synapse.storm.log'


class LogTest(s_test.SynTest):

    async def test_stormlib_log(self):

        async with self.getTestCore() as core:
            # Raw message
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.debug("debug message")')
                self.true(await stream.expect('debug message'))
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.info("info message")')
                self.true(await stream.expect('info message'))
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.warning("warn message")')
                self.true(await stream.expect('warn message'))
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.error("error message")')
                self.true(await stream.expect('error message'))

            # Extra without structlog handler in place has no change in results
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.debug("debug message", extra=({"key": "valu"}))')
                self.true(await stream.expect('debug message'))
                self.eq('valu', stream.jsonlines()[0]['params']['key'])

            # Extra can be empty too
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.debug("debug message", extra=({}))')
                self.true(await stream.expect('debug message'))

            # Extra must be a dict after toprim is called on him.
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.log.debug("debug message", extra=(foo, bar, baz))')

            # structlog test
            with self.getLoggerStream(logname) as stream:
                await core.callStorm('$lib.log.debug("struct1 message")')
                await core.callStorm('$lib.log.debug("struct2 message", extra=({"key": "valu"}))')

            msgs = stream.jsonlines()
            self.len(2, msgs)
            mesg = msgs[0]
            self.eq(mesg.get('logger').get('name'), 'synapse.storm.log')
            self.eq(mesg.get('message'), 'struct1 message')
            self.none(mesg.get('key'))

            mesg = msgs[1]
            self.eq(mesg.get('logger').get('name'), 'synapse.storm.log')
            self.eq(mesg.get('message'), 'struct2 message')
            self.eq(mesg['params'].get('key'), 'valu')
