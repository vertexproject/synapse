import gc
import asyncio
import logging

import unittest.mock as mock

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.logging as s_logging

import synapse.tests.utils as s_test

logger = logging.getLogger(__name__)

class LoggingTest(s_test.SynTest):

    async def test_lib_logging_norm(self):

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

    async def test_lib_logging_base(self):

        # Ensure we're starting the test from a clean slate
        self.none(s_logging.StreamHandler._pump_task)

        # Installs the logginghandlers
        s_logging.setup()
        self.nn(s_logging.StreamHandler._pump_task)

        # Enwusre that while we have a running logging task, that windowing of live log events to a consumer works.

        msgs = []
        # Indicates that the function has started
        evnt0 = asyncio.Event()
        # Indicates the function has entered the window
        evnt1 = asyncio.Event()
        # Indicates the function has left Window.__aiter__ - this will start the teardown the Window object,
        # which will eventually cause __aiter__ to exit and leave the ioloop.
        evnt2 = asyncio.Event()
        async def collector():
            evnt0.set()
            async for m in s_logging.watch(last=0):
                evnt1.set()
                msgs.append(m)
                if m.get('params').get('fini'):
                    break
            evnt2.set()
            return True

        self.len(0, s_logging._log_wins)

        task = s_coro.create_task(collector())
        await asyncio.wait_for(evnt0.wait(), timeout=12)

        logger.error('window0')

        await asyncio.wait_for(evnt1.wait(), timeout=12)
        self.len(1, s_logging._log_wins)

        logger.error('window1', extra=s_logging.getLogExtra(fini=True))

        await asyncio.wait_for(evnt2.wait(), timeout=12)
        self.true(await task)

        self.len(2, msgs)
        self.eq([m.get('message') for m in msgs], ['window0', 'window1'])

        # Ensure that the ioloop can remove the empty Window.__aiter__ task,
        # which will release the Window ref and allow it to be GC'd.
        # Test runs gc.collect() as a safety for test stability.
        await asyncio.sleep(0)
        gc.collect()
        self.len(0, s_logging._log_wins)

        s_logging.reset()
        self.none(s_logging.StreamHandler._pump_task)
        self.none(s_logging.StreamHandler._pump_event)
        self.len(0, s_logging.StreamHandler._logs_fifo)
        self.len(0, s_logging.StreamHandler._text_todo)
        self.len(0, s_logging.StreamHandler._logs_todo)

        # Ensure various log messages are properly captured a structured data in the FIFO and logs() works
        s_logging.setLogInfo('someglobal', 'testvalu')
        with self.getLoggerStream('synapse.tests.test_lib_logging') as stream:
            # Log a few messages
            logger.error('test0', extra=s_logging.getLogExtra(foo='bar'))
            s_logging.popLogInfo('someglobal')
            logger.warning('test1', extra=s_logging.getLogExtra(foo='baz'))
            logger.info('test2')
            logger.debug('test3')
            await stream.expect('test3')

            msgs = s_logging.logs()
            self.isinstance(msgs, tuple)
            self.len(4, msgs)

        msg0 = msgs[0]
        self.eq(msg0.get('message'), 'test0')
        self.eq(msg0.get('level'), 'ERROR')
        self.eq(msg0.get('someglobal'), 'testvalu')
        self.eq(msg0.get('params'), {'foo': 'bar'})
        self.isin('time', msg0)
        lnfo = msg0.get('logger')
        self.eq(lnfo.get('name'), 'synapse.tests.test_lib_logging')
        self.eq(lnfo.get('func'), 'test_lib_logging_base')
        self.isin('process', lnfo)
        self.isin('thread', lnfo)

        msg1 = msgs[1]
        self.eq(msg1.get('message'), 'test1')
        self.eq(msg1.get('level'), 'WARNING')
        self.notin('someglobal', msg1)
        self.eq(msg1.get('params'), {'foo': 'baz'})
        self.isin('time', msg0)

        msg2 = msgs[2]
        self.eq(msg2.get('message'), 'test2')
        self.eq(msg2.get('level'), 'INFO')
        self.eq(msg2.get('params'), {})

        msg3 = msgs[3]
        self.eq(msg3.get('message'), 'test3')
        self.eq(msg3.get('level'), 'DEBUG')
        self.eq(msg3.get('params'), {})

        s_logging.reset()

        msgs = s_logging.logs()
        self.len(0, msgs)
        self.isinstance(msgs, tuple)
        self.none(s_logging.StreamHandler._pump_task)

    async def test_lib_logging_shutdown(self):
        # Test the _shutdown_task functionality used in s_logging.shutdown() to ensure it drains the logs
        # and exits cleanly

        # Installs the logginghandlers
        s_logging.setup(structlog=True)
        self.nn(s_logging.StreamHandler._pump_task)

        # Let the task startup
        await asyncio.sleep(0)

        msgs = []
        nlines = 3
        evnt = asyncio.Event()

        def writemock(text):
            lines = text.split('\n')
            for line in lines:
                if line:
                    msgs.append(s_json.loads(line))
            if len(msgs) == nlines:
                evnt.set()

        # shutdown with a pending log event
        with mock.patch('synapse.lib.logging._writestderr', writemock) as patch:
            logger.error('message0')
            logger.error('message1')
            await asyncio.sleep(0)
            logger.error('message2')
            # Shutdown before nlines have been accounted for
            await s_logging._shutdown_task()
            self.true(await asyncio.wait_for(evnt.wait(), timeout=12))

        self.true(s_logging.StreamHandler._pump_task.done())
        self.eq([m.get('message') for m in msgs], ['message0', 'message1', 'message2'])

        s_logging.reset()

        evnt.clear()
        msgs.clear()

        s_logging.setup(structlog=True)
        await asyncio.sleep(0)
        self.false(s_logging.StreamHandler._pump_task.done())

        # shutdown without a pending log event
        with mock.patch('synapse.lib.logging._writestderr', writemock) as patch:
            logger.error('message0')
            logger.error('message1')
            logger.error('message2')
            await asyncio.sleep(0)
            # Shutdown after nlines have been accounted for
            self.true(await asyncio.wait_for(evnt.wait(), timeout=12))
            await s_logging._shutdown_task()

        self.true(s_logging.StreamHandler._pump_task.done())
        self.eq([m.get('message') for m in msgs], ['message0', 'message1', 'message2'])

    async def test_lib_logging_pump_error(self):
        # Ensure that exceptions are captured and printed to stderr directly
        s_logging.setup(structlog=True)
        self.nn(s_logging.StreamHandler._pump_task)

        evnt = asyncio.Event()

        data = []
        def writemock(text):
            data.append(text)
            evnt.set()

        with mock.patch('synapse.lib.logging._writestderr', writemock):
            s_logging.StreamHandler._text_todo.append('hehe')
            s_logging.StreamHandler._logs_todo.append('hehe')

            s_logging.StreamHandler._text_todo.append(1234)
            s_logging.StreamHandler._logs_todo.append('newp')

            # This will cause a type error trying to join hehe and 1234 together
            # when the task wakes up and and tries to process the queue

            s_logging.StreamHandler._pump_event.set()

            self.true(await asyncio.wait_for(evnt.wait(), timeout=12))

        text = '\n'.join(data)
        self.isin('Error during log handling', text)
        self.isin('Traceback', text)

        s_logging.reset()

    async def test_lib_logging_exception(self):

        # Ensure that various exception information is captured

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
