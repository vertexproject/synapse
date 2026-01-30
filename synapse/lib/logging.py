import os
import sys
import asyncio
import logging
import weakref
import traceback
import collections

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.scope as s_scope

logger = logging.getLogger(__name__)

_log_wins = weakref.WeakSet()

LOG_PUMP_TASK_TIMEOUT = int(os.environ.get('SYNDEV_LOG_TASK_SHUTDOWN_TIMEOUT', 1))

# TODO - Handle exception groups
def excinfo(e, _seen=None):

    if _seen is None:
        _seen = set()

    _seen.add(e)

    tb = []
    for path, line, func, sorc in traceback.extract_tb(e.__traceback__):
        # sorc may not be available; enusre that all output is a str
        if sorc is None:
            sorc = '<none>'
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
        ret['info'] = e.errinfo.copy()
        ret['mesg'] = ret['info'].pop('mesg', None)

    if ret.get('mesg') is None:
        ret['mesg'] = str(e)

    return ret

_glob_loginfo = {}
def setLogInfo(name, valu):
    '''
    Configure global values which should be added to every log.
    '''
    _glob_loginfo[name] = valu

def getLogExtra(**kwargs):
    '''
    Construct a properly enveloped log extra dictionary.
    '''
    extra = {'params': kwargs, 'loginfo': {}}
    return extra

class JsonFormatter(logging.Formatter):

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
            # loginfo['sess'] = sess.iden
            if sess.user is not None:
                loginfo['user'] = sess.user.iden
                loginfo['username'] = sess.user.name

        if record.exc_info:
            loginfo['error'] = excinfo(record.exc_info[1])

        if not hasattr(record, 'params'):
            record.params = {}

        loginfo['params'] = record.params

        # the subsequent emit() will set the event
        StreamHandler._logs_fifo.append(loginfo)
        StreamHandler._logs_todo.append(loginfo)

        return loginfo

    def format(self, record):
        loginfo = self.genLogInfo(record)
        return s_json.dumps(loginfo, default=str).decode()

class TextFormatter(JsonFormatter):

    def __init__(self, *args, **kwargs):
        kwargs['fmt'] = s_const.LOG_FORMAT
        return super().__init__(*args, **kwargs)

    def format(self, record):
        # this is required to send the structured data
        loginfo = self.genLogInfo(record)
        return logging.Formatter.format(self, record)

class StreamHandler(logging.StreamHandler):

    _pump_task = None
    _pump_event = None
    _pump_exit_flag = False
    _glob_handler = None

    _logs_fifo = collections.deque(maxlen=1000)
    _logs_todo = collections.deque(maxlen=1000)
    _text_todo = collections.deque(maxlen=1000)

    def emit(self, record):

        if self._pump_task is None:
            return logging.StreamHandler.emit(self, record)

        try:
            text = self.format(record)
            self._text_todo.append(text)
            self._pump_event.set()

        # emulating behavior of parent class
        except RecursionError: # pragma: no cover
            raise

        except Exception as e: # pragma: no cover
            self.handleError(record)

def _writestderr(text):
    sys.stderr.write(text)
    sys.stderr.flush()

async def _pumpLogStream():

    while True:

        try:
            await StreamHandler._pump_event.wait()

            logstodo = tuple(StreamHandler._logs_todo)
            texttodo = tuple(StreamHandler._text_todo)

            if not logstodo and not texttodo:
                StreamHandler._pump_event.clear()
                if StreamHandler._pump_exit_flag is True:
                    return
                continue

            StreamHandler._logs_todo.clear()
            StreamHandler._text_todo.clear()
            StreamHandler._pump_event.clear()

            fulltext = '\n'.join(texttodo) + '\n'

            for wind in _log_wins:
                await wind.puts(logstodo)

            await s_coro.executor(_writestderr, fulltext)

            if StreamHandler._pump_exit_flag is True:
                return

        except Exception as e:
            traceback.print_exc()

def logs(last=100):
    return tuple(StreamHandler._logs_fifo)[-last:]

async def watch(last=100):
    # avoid a circular import...
    import synapse.lib.queue as s_queue
    async with await s_queue.Window.anit(maxsize=10000) as window:
        await window.puts(logs(last=last))
        _log_wins.add(window)
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
        conf['structlog'] = False

    fmtclass = JsonFormatter
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

    _glob_logconf.clear()
    _glob_logconf.update(conf)

    rootlogger = logging.getLogger()

    level = normLogLevel(conf.get('level'))
    rootlogger.setLevel(level)

    if StreamHandler._glob_handler is None:
        handler = StreamHandler()
        handler.setFormatter(fmtclass(datefmt=conf.get('datefmt')))
        StreamHandler._glob_handler = handler
        rootlogger.handlers.append(handler)

    return conf

def reset(clear_globconf=True):
    # This may be called by tests to cleanup loop specific objects
    # ( it does not need to be called by in general by service fini )

    if StreamHandler._glob_handler is not None:
        rootlogger = logging.getLogger()
        rootlogger.handlers.remove(StreamHandler._glob_handler)

    if StreamHandler._pump_task is not None:
        StreamHandler._pump_task.cancel()

    StreamHandler._pump_task = None
    StreamHandler._pump_event = None
    StreamHandler._pump_exit_flag = False
    StreamHandler._glob_handler = None
    StreamHandler._text_todo.clear()
    StreamHandler._logs_fifo.clear()
    StreamHandler._logs_todo.clear()

    if clear_globconf:
        _glob_logconf.clear()
        _glob_loginfo.clear()

async def shutdown():
    '''
    Inverse of setup. Gives the pump task the opportunity to exit
    before removing it and resetting log attributes. A StreamHandler
    is then re-installed on the root logger to allow for messages
    from sources like atexit handlers to be logged.
    '''
    # Give the pump task a small opportunity to drain its
    # queue of items and exit cleanly.
    if StreamHandler._pump_task is not None:
        StreamHandler._pump_exit_flag = True  # Set the task to exit
        StreamHandler._pump_event.set()  # Wake the task
        try:
            await asyncio.wait_for(StreamHandler._pump_task, timeout=LOG_PUMP_TASK_TIMEOUT)
        except asyncio.TimeoutError:
            pass

    # Reset all logging configs except globals since we may need those.
    reset(clear_globconf=False)

    fmtclass = JsonFormatter
    if not _glob_logconf.get('structlog'):
        fmtclass = TextFormatter

    # Reinstall a StreamHandler and the formatter on the root logger
    rootlogger = logging.getLogger()
    stream = logging.StreamHandler()
    stream.setFormatter(fmtclass(datefmt=_glob_logconf.get('datefmt')))
    rootlogger.addHandler(stream)

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
