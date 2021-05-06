import json

import logging

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
            ret['exc_info'] = self.formatException(record.exc_info)
        if record.exc_text:
            ret['exc_text'] = record.exc_text
        if record.stack_info:
            ret['stack_info'] = record.stack_info

        # stuffing our extra into a single dictionary avoids a loop
        # over record.__dict__ extracting fields which are not known
        # attributes for each log record.
        extras = record.__dict__.get('synapse')
        if extras:
            ret.update({k: v for k, v in extras.items() if k not in ret})

        return json.dumps(ret)
