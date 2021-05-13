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
            'logger': {
                'name': record.name,
                'process': record.processName,
                'filename': record.filename,
                'func': record.funcName,
            },
            'level': record.levelname,
            'time': self.formatTime(record, self.datefmt),
        }

        if record.exc_info:
            name, info = s_common.err(record.exc_info[1], fulltb=True)
            # This is the actual exception name. The ename key is the function name.
            info['errname'] = name
            ret['err'] = info

        # stuffing our extra into a single dictionary avoids a loop
        # over record.__dict__ extracting fields which are not known
        # attributes for each log record.
        extras = record.__dict__.get('synapse')
        if extras:
            ret.update({k: v for k, v in extras.items() if k not in ret})

        return json.dumps(ret, default=str)
