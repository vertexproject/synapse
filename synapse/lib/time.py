'''
Time related utilities for synapse "epoch millis" time values.
'''

import datetime

from synapse.exc import BadTypeValu

def parse(text, base=None):
    '''
    Parse a time string into an epoch millis value.
    '''
    text = text.strip().lower()
    text = (''.join([ c for c in text if c.isdigit() ]))

    # TODO: support relative time offsets here...

    tlen = len(text)
    if tlen == 4:
        dt = datetime.datetime.strptime(text, '%Y')

    elif tlen == 6:
        dt = datetime.datetime.strptime(text, '%Y%m')

    elif tlen == 8:
        dt = datetime.datetime.strptime(text, '%Y%m%d')

    elif tlen == 10:
        dt = datetime.datetime.strptime(text, '%Y%m%d%H')

    elif tlen == 12:
        dt = datetime.datetime.strptime(text, '%Y%m%d%H%M')

    elif tlen == 14:
        dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S')

    elif tlen in (15,16,17):
        dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S%f')

    else:
        raise BadTypeValu(mesg='Unknown time format')

    epoch = datetime.datetime(1970,1,1)
    return int((dt - epoch).total_seconds() * 1000)
