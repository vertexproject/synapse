import io
import json
import logging

import synapse.common as s_common
import synapse.lib.structlog as s_structlog

import synapse.tests.utils as s_test

logger = logging.getLogger(__name__)

class StructLogTest(s_test.SynTest):

    def test_structlog(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream=stream)
        formatter = s_structlog.JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.warning('Test message 1')
        logger.error('Test message 2')
        iden = s_common.guid()
        logger.error('Extra test', extra={'synapse': {'foo': 'bar', 'iden': iden}})

        try:
            _ = 1 / 0
        except ZeroDivisionError:
            logger.exception('Exception handling')

        data = stream.getvalue()

        # There is a trailing \n on the stream
        mesgs = [json.loads(m) for m in data.split('\n') if m]
        self.len(4, mesgs)

        mesg = mesgs[0]
        self.eq(set(mesg.keys()),
                {'mesg', 'logger', 'thread', 'process', 'thread',
                 'filename', 'level', 'func', 'time'})
        self.eq(mesg.get('mesg'), 'Test message 1')
        self.eq(mesg.get('level'), 'WARNING')

        mesg = mesgs[1]
        self.eq(mesg.get('mesg'), 'Test message 2')
        self.eq(mesg.get('level'), 'ERROR')

        mesg = mesgs[2]
        self.eq(mesg.get('mesg'), 'Extra test')
        self.eq(mesg.get('level'), 'ERROR')
        self.eq(mesg.get('foo'), 'bar')
        self.eq(mesg.get('iden'), iden)

        mesg = mesgs[3]
        self.eq(mesg.get('mesg'), 'Exception handling')
        self.eq(mesg.get('level'), 'ERROR')
        exc_info = mesg.get('exc_info')
        self.isin('Traceback', exc_info)
        self.isin('_ = 1 / 0', exc_info)
        self.isin('ZeroDivisionError: division by zero', exc_info)
