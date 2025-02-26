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
loglock = asyncio.Lock()
logevnt = asyncio.Event()
logwindows = weakref.WeakSet()

logfifo = collections.deque(maxlen=1000)

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
def setLogGlobal(name, valu):
    '''
    Configure global values which should be added to every log.
    '''
    _glob_loginfo[name] = valu

def getLogExtra(**kwargs):
    return {'params': kwargs, 'loginfo': {}}

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

        try:

            if (user := s_scope.get('user')) is not None:
                loginfo['user'] = user.iden
                loginfo['username'] = user.name

            elif (sess := s_scope.get('sess')) is not None:
                if sess.user is not None:
                    loginfo['user'] = sess.user.iden
                    loginfo['username'] = sess.user.name

        except RuntimeError:
            # if there is no running loop, there can be no scope vars...
            pass

        if record.exc_info:
            loginfo['err'] = s_common.err(record.exc_info[1], fulltb=True)

        if not hasattr(record, 'params'):
            record.params = {}

        loginfo['params'] = record.params

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

_glob_logconf = {}
def setup(**conf):
    '''
    Configure synapse logging.
    '''
    conf.update(getLogConfFromEnv())

    if conf.get('level') is None:
        conf['level'] = logging.WARNING

    if conf.get('structlog') is None:
        conf['structlog'] = False

    fmtclass = Formatter
    if not conf.get('structlog'):
        fmtclass = TextFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(fmtclass(datefmt=conf.get('datefmt')))

    level = normLogLevel(conf.get('level'))

    logging.basicConfig(level=level, handlers=(handler,))

    logger.info('log level set to %s', s_const.LOG_LEVEL_INVERSE_CHOICES.get(level))

    _glob_logconf.clear()
    _glob_logconf.update(conf)

    return conf

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
