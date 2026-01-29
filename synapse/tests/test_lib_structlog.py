import io
import time
import logging

import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.structlog as s_structlog

import synapse.tests.utils as s_test
import synapse.exc as s_exc
logger = logging.getLogger(__name__)


class ZDE(s_exc.SynErr): pass


class StructLogTest(s_test.SynTest):

    def test_structlog_base(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream=stream)
        formatter = s_structlog.JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.warning('Test message 1')
        logger.error('Test message 2')
        iden = s_common.guid()
        logger.error('Extra test', extra={'synapse': {'foo': 'bar', 'iden': iden, 'time': 0}})

        def foo():
            _ = 1 / 0
        def bar():
            try:
                foo()
            except ZeroDivisionError as e:
                raise ZDE(mesg='ZDE test', args=(1, 0), buffer='vertex'.encode()) from e
        try:
            bar()
        except s_exc.SynErr:
            logger.exception('Exception handling')

        logger.warning('Unicode is cool for 程序员!')

        data = stream.getvalue()

        # There is a trailing \n on the stream
        raw_mesgs = [m for m in data.split('\n') if m]
        mesgs = [s_json.loads(m) for m in raw_mesgs]
        self.len(5, mesgs)

        mesg = mesgs[0]
        self.eq(set(mesg.keys()), {'message', 'logger', 'level', 'time'})
        lnfo = mesg.get('logger')
        self.eq(set(lnfo.keys()), {'name', 'process', 'filename', 'func'})
        self.eq(mesg.get('message'), 'Test message 1')
        self.eq(mesg.get('level'), 'WARNING')

        mesg = mesgs[1]
        self.eq(mesg.get('message'), 'Test message 2')
        self.eq(mesg.get('level'), 'ERROR')

        mesg = mesgs[2]
        self.eq(mesg.get('message'), 'Extra test')
        self.eq(mesg.get('level'), 'ERROR')
        self.eq(mesg.get('foo'), 'bar')
        self.eq(mesg.get('iden'), iden)
        self.ne(mesg.get('time'), 0)  # time was not overwritten by the extra

        mesg = mesgs[3]
        self.eq(mesg.get('message'), 'Exception handling')
        self.eq(mesg.get('level'), 'ERROR')
        erfo = mesg.get('err')

        etb = erfo.get('etb')
        self.isin('Traceback', etb)
        self.isin('_ = 1 / 0', etb)
        self.isin('The above exception was the direct cause of the following exception:', etb)
        self.isin('ZeroDivisionError: division by zero', etb)
        self.isin("""test_lib_structlog.ZDE: ZDE: args=(1, 0) buffer=b'vertex' mesg='ZDE test'""", etb)
        self.eq(erfo.get('errname'), 'ZDE')
        self.eq(erfo.get('mesg'), 'ZDE test')
        self.eq(erfo.get('args'), (1, 0))
        self.eq(erfo.get('buffer'), "b'vertex'")

        rawm = raw_mesgs[4]
        self.isin('"message":"Unicode is cool for 程序员!"', rawm)

        logger.removeHandler(handler)

    def test_structlog_datefmt(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream=stream)
        datefmt = '%m-%Y-%d'  # MMYYYYYDD
        formatter = s_structlog.JsonFormatter(datefmt=datefmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        now = time.gmtime()
        logger.error('Time test', extra={'synapse': {'foo': 'bar'}})

        data = stream.getvalue()

        # There is a trailing \n on the stream
        raw_mesgs = [m for m in data.split('\n') if m]
        mesgs = [s_json.loads(m) for m in raw_mesgs]
        self.len(1, mesgs)
        ptime = time.strptime(mesgs[0].get('time'), datefmt)
        self.eq(now.tm_year, ptime.tm_year)
        self.eq(now.tm_mon, ptime.tm_mon)
        self.eq(now.tm_mday, ptime.tm_mday)
        self.eq(0, ptime.tm_hour)
        self.eq(0, ptime.tm_min)
        self.eq(0, ptime.tm_sec)

        logger.removeHandler(handler)
