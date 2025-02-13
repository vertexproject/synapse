import os
import json
import asyncio
import logging
import weakref
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.const as s_const
import synapse.lib.scope as s_scope

logger = logging.getLogger(__name__)

logtodo = []
logbase = None
logevnt = asyncio.Event()
logwindows = weakref.WeakSet()

logfifo = collections.deque(maxlen=1000)

def _addLogInfo(info):
    logfifo.append(info)
    if logbase is not None:
        logtodo.append(info)
        logevnt.set()

async def _feedLogInfo():

    while not logbase.isfini:

        await logevnt.wait()

        if logbase.isfini:
            return

        todo = list(logtodo)

        logevnt.clear()
        logtodo.clear()

        for wind in logwindows:
            await wind.puts(todo)

async def _initLogBase():

    global logbase

    # FIXME: resolve circurlar deps
    import synapse.lib.base as s_base

    logbase = await s_base.Base.anit()
    logbase._fini_at_exit = True
    logbase.schedCoro(_feedLogInfo())

async def getLogInfo(wait=False, last=None):

    if not wait:
        for loginfo in list(logfifo)[last:]:
            yield loginfo
        return

    global logbase

    if logbase is None:
        await _initLogBase()

    # FIXME: resolve circurlar deps
    import synapse.lib.queue as s_queue

    async with await s_queue.Window.anit(maxsize=2000) as window:

        await window.puts(list(logfifo)[last:])

        logwindows.add(window)

        async for loginfo in window:
            yield loginfo

logextra = {}
def setLogExtra(name, valu):
    '''
    Configure global extra values which should be added to every log.
    '''
    logextra[name] = valu

def getLogExtra(**kwargs):

    extra = {'synapse': kwargs}
    extra.update(logextra)

    user = s_scope.get('user')  # type: s_auth.User
    if user is not None:
        extra['user'] = user.iden
        extra['username'] = user.name

    else:
        sess = s_scope.get('sess')  # type: s_daemon.Sess
        if sess is not None and sess.user is not None:
            extra['user'] = sess.user.iden
            extra['username'] = sess.user.name

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

        if record.exc_info:
            loginfo['err'] = s_common.err(record.exc_info[1], fulltb=True)

        if not hasattr(record, 'synapse'):
            record.synapse = {}

        loginfo['synapse'] = record.synapse

        _addLogInfo(loginfo)

        return loginfo

    def format(self, record):
        loginfo = self.genLogInfo(record)
        return json.dumps(loginfo, default=str)

class TextFormatter(Formatter):

    def __init__(self, *args, **kwargs):
        kwargs['fmt'] = s_const.LOG_FORMAT
        return super().__init__(*args, **kwargs)

    def format(self, record):
        loginfo = self.genLogInfo(record)
        return logging.Formatter.format(self, record)

def setup(level=logging.WARNING, structlog=False):
    '''
    Configure synapse logging.
    '''
    conf = getLogConfFromEnv()
    conf.setdefault('level', level)
    conf.setdefault('structlog', structlog)

    fmtclass = Formatter
    if not conf.get('structlog'):
        fmtclass = TextFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(fmtclass(datefmt=conf.get('datefmt')))

    logging.basicConfig(level=conf.get('level'), handlers=(handler,))

    logger.info('log level set to %s', s_const.LOG_LEVEL_INVERSE_CHOICES.get(level))

    return conf

def getLogConfFromEnv():

    conf = {}

    if level := os.getenv('SYN_LOG_LEVEL') is not None:
        conf['level'] = normLogLevel(level)

    if datefmt := os.getenv('SYN_LOG_DATEFORMAT') is not None:
        conf['datefmt'] = datefmt

    if structlog := os.getenv('SYN_LOG_STRUCT') is not None:
        conf['structlog'] = structlog.lower() in ('1', 'true')

    return conf

def normLogLevel(valu):
    '''
    Norm a log level value to a integer.

    Args:
        valu: The value to norm ( a string or integer ).

    Returns:
        int: A valid log level.
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
