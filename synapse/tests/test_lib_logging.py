import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.logging as s_logging

import synapse.tests.utils as s_test

class LoggingTest(s_test.SynTest):

    async def test_lib_logging(self):

        s_logging.setup(structlog=True)
        logger = logging.getLogger(__name__)

        self.eq(10, s_logging.normLogLevel(' 10 '))
        self.eq(10, s_logging.normLogLevel(10))
        self.eq(20, s_logging.normLogLevel(' inFo\n'))

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel(100)

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel('BEEP')

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel('12')

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel({'key': 'newp'})

        s_logging.setLogExtra('woot', 'hehe')
        extra = s_logging.getLogExtra()

        self.eq(extra['woot'], 'hehe')

        event = asyncio.Event()
        async def logtask():
            await asyncio.sleep(1)
            print('LOG TASK')
            logger.warning('OMG WARNING', s_logging.getLogExtra(hehe='haha'))
            logger.warning('OMG WARNING', s_logging.getLogExtra(hehe='haha'))
            print('DONE')

        async with await s_base.Base.anit() as base:
            s_logging.logfifo.clear()
            base.schedCoro(logtask())
            async for loginfo in s_logging.getLogInfo(wait=True):
                print(loginfo)
                self.eq(loginfo['loglevel'], 'WARNING')
                break
