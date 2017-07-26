'''
Time related utilities for synapse "epoch millis" time values.
'''

import datetime

import synapse.common as s_common

def parse(text, base=None, chop=False):
    '''
    Parse a time string into an epoch millis value.
    '''
    #TODO: use base to facilitate relative time offsets
    text = text.strip().lower()
    text = (''.join([c for c in text if c.isdigit()]))

    if chop:
        text = text[:17]

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

    elif tlen in (15, 16, 17):
        dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S%f')

    else:
        raise s_common.BadTypeValu(mesg='Unknown time format')

    epoch = datetime.datetime(1970, 1, 1)
    return int((dt - epoch).total_seconds() * 1000)

def repr(tick, pack=False):
    '''
    Return a date string for an epoch-millis timestamp.

    Args:
        tick (int): The timestamp in milliseconds since the epoch.

    Returns:
        (str):  A date time string
    '''
    dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=tick)
    millis = dt.microsecond / 1000
    if pack:
        return '%d%.2d%.2d%.2d%.2d%.2d%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)
    return '%d/%.2d/%.2d %.2d:%.2d:%.2d.%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)
