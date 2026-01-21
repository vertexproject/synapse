import os
import sys
import asyncio
import logging
import weakref
import traceback
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

logtodo = []
logbase = None
loglock = asyncio.Lock()
logevnt = asyncio.Event()
logwindows = weakref.WeakSet()

logfifo = collections.deque(maxlen=1000)

def excinfo(e, _seen=None):

    if _seen is None:
        _seen = set()

    _seen.add(e)

    tb = []
    for path, line, func, sorc in traceback.extract_tb(e.__traceback__):
        tb.append((path, line, func, sorc))

    ret = {
        'code': e.__class__.__name__,
        'traceback': tb,
    }

    if notes := getattr(e, '__notes__', None):
        ret['notes'] = tuple(notes)

    if (cause := getattr(e, '__cause__', None)) is not None:
        if isinstance(cause, Exception) and cause not in _seen:
            ret['cause'] = excinfo(cause, _seen=_seen)

    if (context := getattr(e, '__context__', None)) is not None:
        if isinstance(context, Exception) and context not in _seen:
            ret['context'] = excinfo(context, _seen=_seen)

    if isinstance(e, s_exc.SynErr):
        ret['mesg'] = e.errinfo.pop('mesg', None)
        ret['info'] = e.errinfo

    if ret.get('mesg') is None:
        ret['mesg'] = str(e)

    return ret

def _addLogInfo(info):
    logfifo.append(info)
    if logbase is not None:
        logtodo.append(info)
        logevnt.set()

async def _feedLogTask():

    while not logbase.isfini:

        await logevnt.wait()

        if logbase.isfini:
            return

        todo = list(logtodo)

        logevnt.clear()
        logtodo.clear()

        for wind in logwindows:
            await wind.puts(todo)

_glob_loginfo = {}
def setLogInfo(name, valu):
    '''
    Configure global values which should be added to every log.
    '''
    _glob_loginfo[name] = valu

def getLogExtra(**kwargs):
    '''
    Construct a properly enveloped log extra dictionary.

    NOTE: If the key "exc" is specified, it will be used as
          an exception to generate standardized error info.
    '''
    extra = {'params': kwargs, 'loginfo': {}}
    return extra

class Formatter(logging.Formatter):

    def genLogInfo(self, record):

        record.message = record.getMessage()

        loginfo = {
            'message': record.message,
            'logger': {
                'name': record.name,
                'func': record.funcName,
            },
            'level': record.levelname,
            'time': self.formatTime(record, self.datefmt),
        }

        loginfo.update(_glob_loginfo)

        if hasattr(record, 'loginfo'):
            loginfo.update(record.loginfo)

        if (user := s_scope.get('user')) is not None:
            loginfo['user'] = user.iden
            loginfo['username'] = user.name

        elif (sess := s_scope.get('sess')) is not None:
            if sess.user is not None:
                loginfo['user'] = sess.user.iden
                loginfo['username'] = sess.user.name

        if record.exc_info:
            loginfo['error'] = excinfo(record.exc_info[1])

        if not hasattr(record, 'params'):
            record.params = {}

        loginfo['params'] = record.params

        _addLogInfo(loginfo)

        return loginfo

    def format(self, record):
        loginfo = self.genLogInfo(record)
        return s_json.dumps(loginfo, default=str).decode()

class TextFormatter(Formatter):

    def __init__(self, *args, **kwargs):
        kwargs['fmt'] = s_const.LOG_FORMAT
        return super().__init__(*args, **kwargs)

    def format(self, record):
        loginfo = self.genLogInfo(record)
        return logging.Formatter.format(self, record)

class StreamHandler(logging.StreamHandler):

    _pump_task = None
    _pump_event = None
    _pump_fifo = collections.deque(maxlen=10000)

    def emit(self, record):

        if self._pump_task is None:
            return logging.StreamHandler.emit(self, record)

        try:
            text = self.format(record)
            self._pump_fifo.append(text)
            self._pump_event.set()

        # emulating behavior of parent class
        except RecursionError:
            raise

        except Exception as e:
            self.handleError(record)

def _writestderr(text):
    sys.stderr.write(text)
    sys.stderr.flush()

async def _pumpLogStream():

    while True:

        await StreamHandler._pump_event.wait()

        StreamHandler._pump_event.clear()

        if not StreamHandler._pump_fifo:
            continue

        todo = list(StreamHandler._pump_fifo)
        text = '\n'.join(todo) + '\n'

        StreamHandler._pump_fifo.clear()
        await s_coro.executor(_writestderr, text)

def logs(last=100):
    return logfifo[-last:]

async def watch(last=100):
    async with await s_queue.Window.anit(maxsize=10000) as window:
        window.puts(logs(last=last))
        logwindows.add(window)
        async for item in window:
            yield item

_glob_logconf = {}
def setup(**conf):
    '''
    Configure synapse logging.

    NOTE: If this API is invoked while there is a running
          asyncio loop, it will automatically enter async
          mode and fire a task to pump log events without
          blocking.
    '''
    conf.update(getLogConfFromEnv())

    if conf.get('level') is None:
        conf['level'] = logging.INFO

    if conf.get('structlog') is None:
        conf['structlog'] = s_version.version >= (3, 0, 0)

    fmtclass = Formatter
    if not conf.get('structlog'):
        fmtclass = TextFormatter

    if s_coro.has_running_loop() and StreamHandler._pump_task is None:
        StreamHandler._pump_event = asyncio.Event()
        StreamHandler._pump_task = s_coro.create_task(_pumpLogStream())

    # this is used to pass things like service name
    # to child processes and forked workers...
    loginfo = conf.pop('loginfo', None)
    if loginfo is not None:
        _glob_loginfo.update(loginfo)

    handler = StreamHandler()
    handler.setFormatter(fmtclass(datefmt=conf.get('datefmt')))

    level = normLogLevel(conf.get('level'))

    _glob_logconf.clear()
    _glob_logconf.update(conf)

    logging.basicConfig(level=level, handlers=(handler,))

    logger.info('log level set to %s', s_const.LOG_LEVEL_INVERSE_CHOICES.get(level))

    return conf

def reset():
    # This may be called by tests to cleanup loop specific objects
    # ( it does not need to be called by in general by service fini )
    if StreamHandler._pump_task is not None:
        StreamHandler._pump_task.cancel()

    StreamHandler._pump_event = None
    StreamHandler._pump_task = None
    StreamHandler._pump_fifo.clear()

    _glob_logconf.clear()
    _glob_loginfo.clear()

def getLogConf():
    logconf = _glob_logconf.copy()
    logconf['loginfo'] = _glob_loginfo.copy()
    return logconf

def getLogConfFromEnv():

    conf = {}

    if (level := os.getenv('SYN_LOG_LEVEL')) is not None:
        conf['level'] = normLogLevel(level)

    if (datefmt := os.getenv('SYN_LOG_DATEFORMAT')) is not None:
        conf['datefmt'] = datefmt

    if (structlog := os.getenv('SYN_LOG_STRUCT')) is not None:
        conf['structlog'] = structlog.lower() in ('1', 'true')

    return conf

def normLogLevel(valu):
    '''
    Normalize a log level value to an integer.

    Args:
        valu: The value to norm ( a string or integer ).

    Returns:
        int: A valid log level integer.
    '''
    if isinstance(valu, str):

        valu = valu.strip()
        level = s_const.LOG_LEVEL_CHOICES.get(valu.upper())
        if level is not None:
            return level

        try:
            valu = int(valu)
        except ValueError:
            raise s_exc.BadArg(mesg=f'Invalid log level provided: {valu}', valu=valu) from None

    if isinstance(valu, int):

        if valu not in s_const.LOG_LEVEL_INVERSE_CHOICES:
            raise s_exc.BadArg(mesg=f'Invalid log level provided: {valu}', valu=valu)

        return valu

    raise s_exc.BadArg(mesg=f'Unknown log level type: {type(valu)} {valu}', valu=valu)
