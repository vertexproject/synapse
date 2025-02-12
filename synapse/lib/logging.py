import os
import json
import logging
import collections

import synapse.common as s_common
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

logfifo = collections.deque()

def _addLogInfo(info):
    logfifo.append(info)
    # TODO notify waiters...

# TODO: getLogInfo(wait=True)

def getLogExtra(**kwargs):
    return {'synapse': kwargs}

class Formatter(logging.Formatter):

    def genLogInfo(self, record):

        record.message = record.getMessage()

        loginfo = {
            'message': record.message,
            'logger': {
                'name': record.name,
                'filename': record.filename,
                'func': record.funcName,
            },
            'level': record.levelname,
            'time': self.formatTime(record, self.datefmt),
        }

        if record.exc_info:
            loginfo['err'] = s_common.err(record.exc_info[1], fulltb=True)

        loginfo['synapse'] = record.__dict__.get('synapse')

        _addLogInfo(loginfo)

        return loginfo

    def format(self, record: logging.LogRecord):
        loginfo = self.genLogInfo(record)
        return json.dumps(loginfo, default=str)

class TextFormatter(Formatter):

    def format(self, record):

        loginfo = self.genLogInfo(record)
        mesg = loginfo.get('message')

        syns = loginfo.get('synapse')
        if syns:
            mesg += ' ({json.dumps(syns, default=str)})'

        return mesg

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
        int: A valid Logging log level.
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
