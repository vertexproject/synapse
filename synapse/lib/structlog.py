import json

import logging

import synapse.common as s_common

class JsonFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord):

        record.message = record.getMessage()
        mesg = self.formatMessage(record)
        ret = {
            'message': mesg,
            'logger': record.name,
            'thread': record.threadName,
            'process': record.processName,
            'filename': record.filename,
            'level': record.levelname,
            'func': record.funcName,
            'time': self.formatTime(record, self.datefmt),
        }

        if record.exc_info:
            name, info = s_common.err(record.exc_info[1], fulltb=True)
            ret.update({k: v for k, v in info.items() if k not in ret})
            # This is the actual exception name. The ename key is the function name.
            ret['errname'] = name

        # stuffing our extra into a single dictionary avoids a loop
        # over record.__dict__ extracting fields which are not known
        # attributes for each log record.
        extras = record.__dict__.get('synapse')
        if extras:
            ret.update({k: v for k, v in extras.items() if k not in ret})

        return json.dumps(ret)
