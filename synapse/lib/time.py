'''
Time related utilities for synapse "epoch millis" time values.
'''

import datetime

import synapse.exc as s_exc

EPOCH = datetime.datetime(1970, 1, 1)

def parse(text, base=None, chop=False):
    '''
    Parse a time string into an epoch millis value.
    '''
    # TODO: use base to facilitate relative time offsets
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

    elif 15 <= tlen <= 20:
        dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S%f')

    else:
        raise s_exc.BadTypeValu(valu=text, name='time',
                                mesg='Unknown time format')

    return int((dt - EPOCH).total_seconds() * 1000)

def repr(tick, pack=False):
    '''
    Return a date string for an epoch-millis timestamp.

    Args:
        tick (int): The timestamp in milliseconds since the epoch.

    Returns:
        (str):  A date time string
    '''
    if tick == 0x7fffffffffffffff:
        return '?'

    dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=tick)
    millis = dt.microsecond / 1000
    if pack:
        return '%d%.2d%.2d%.2d%.2d%.2d%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)
    return '%d/%.2d/%.2d %.2d:%.2d:%.2d.%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)

def ival(*times):

    times = [t for t in times if t is not None]

    minv = min(times)
    maxv = max(times)

    if minv == maxv:
        maxv += 1

    return (minv, maxv)

onesec = 1000
onemin = 60000
onehour = 3600000
oneday = 86400000

timeunits = {
    'sec': onesec,
    'secs': onesec,
    'seconds': onesec,

    'min': onemin,
    'mins': onemin,
    'minute': onemin,
    'minutes': onemin,

    'hour': onehour,
    'hours': onehour,

    'day': oneday,
    'days': oneday,
}

# TODO: use synapse.lib.syntax once it gets cleaned up
def _noms(text, offs, cset):
    begin = offs
    while len(text) > offs and text[offs] in cset:
        offs += 1
    return text[begin:offs], offs

def delta(text):
    '''
    Parse a simple time delta string and return the delta.
    '''
    text = text.strip().lower()

    _, offs = _noms(text, 0, ' \t\r\n')

    sign = '+'
    if text and text[0] in ('+', '-'):
        sign = text[0]
        offs += 1

    _, offs = _noms(text, offs, ' \t\r\n')

    sizetext, offs = _noms(text, offs, '0123456789')

    _, offs = _noms(text, offs, ' \t\r\n')

    unittext = text[offs:]

    size = int(sizetext, 0)

    if sign == '-':
        size = -size

    base = timeunits.get(unittext)
    if base is None:
        mesg = f'unknown time delta units: {unittext}'
        raise s_exc.BadTypeValu(name='time', valu=text, mesg=mesg)

    return size * base
