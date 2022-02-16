import logging

import synapse.exc as s_exc

import synapse.lib.stormlib.json as s_json

import synapse.tests.utils as s_test

logname = 'synapse.storm.log'

import contextlib

class LogTest(s_test.SynTest):
    #
    # def setUp(self):
    #     self.stormlogger = logging.getLogger(logname)
    #     self.oldlevel = self.stormlogger.getEffectiveLevel()
    #     self.stormlogger.setLevel(logging.DEBUG)
    #
    # def tearDown(self) -> None:
    #     self.stormlogger.setLevel(self.oldlevel)

    @contextlib.contextmanager
    def setLoggerLevel(self, name, level):
        logger = logging.getLogger(name)
        oldlevel = logger.getEffectiveLevel()
        logger.setLevel(level)
        try:
            yield logger
        finally:
            logger.setLevel(oldlevel)

    async def test_stormlib_log(self):

        async with self.getTestCore() as core:
            # with self.setLoggerLevel(logname, logging.DEBUG):
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
