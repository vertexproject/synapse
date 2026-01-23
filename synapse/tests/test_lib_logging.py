import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.logging as s_logging

import synapse.tests.utils as s_test

logger = logging.getLogger(__name__)

class LoggingTest(s_test.SynTest):

    async def test_lib_logging(self):

        s_logging.setup()

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

        s_logging.reset()

        self.none(s_logging.StreamHandler._pump_task)
        self.none(s_logging.StreamHandler._pump_event)
        self.len(0, s_logging.StreamHandler._logs_fifo)
        self.len(0, s_logging.StreamHandler._text_todo)
        self.len(0, s_logging.StreamHandler._logs_todo)

        with self.getLoggerStream('synapse.tests.test_lib_logging') as stream:

            try:
                try:
                    raise s_exc.SynErr(mesg='omg')
                except Exception as e1:
                    e1.add_note('inner note')
                    raise s_exc.NoSuchType(mesg='woot') from e1
            except Exception as e0:
                e0.add_note('outer note')
                logger.exception(e0)

            mesg = stream.jsonlines()[0]
            self.eq(mesg['error']['code'], 'NoSuchType')
            self.eq(mesg['error']['notes'], ('outer note',))
            self.eq(mesg['error']['cause']['code'], 'SynErr')
            self.eq(mesg['error']['cause']['notes'], ('inner note',))

            self.none(mesg['error'].get('context'))

            stream.clear()

            try:
                try:
                    raise s_exc.SynErr(mesg='omg')
                except Exception as e1:
                    e1.add_note('inner note')
                    raise s_exc.NoSuchType(mesg='woot')
            except Exception as e0:
                e0.add_note('outer note')
                logger.exception(e0)

            mesg = stream.jsonlines()[0]
            self.eq(mesg['error']['code'], 'NoSuchType')
            self.eq(mesg['error']['notes'], ('outer note',))
            self.eq(mesg['error']['context']['code'], 'SynErr')
            self.eq(mesg['error']['context']['notes'], ('inner note',))
