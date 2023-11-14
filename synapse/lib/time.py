'''
Time related utilities for synapse "epoch millis" time values.
'''
import logging
import datetime
import calendar

from dateutil.relativedelta import relativedelta

import pytz
import regex

import synapse.exc as s_exc

import synapse.lookup.timezones as s_l_timezones

logger = logging.getLogger(__name__)

EPOCH = datetime.datetime(1970, 1, 1)

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

tzcat = '|'.join(sorted(s_l_timezones.getTzNames(), key=lambda x: len(x), reverse=True))
unitcat = '|'.join(sorted(timeunits.keys(), key=lambda x: len(x), reverse=True))
tz_re = regex.compile(
    r'\d(?P<tzstr>\s?(?:'
    r'(?P<tzname>%s)|'
    r'(?:(?P<tzrel>\-|\+)(?P<tzhr>\d{1,2}):?(?P<tzmin>\d{2})))'
    r')(?:[\-|\+]\d+(?:%s))?$' % (tzcat, unitcat),
    flags=regex.IGNORECASE
)

daycat = '|'.join(calendar.day_abbr[i].lower() for i in range(7))
monthcat = '|'.join(calendar.month_abbr[i].lower() for i in range(1, 13))
rfc822_re = regex.compile(r'((?:%s),)?\d{1,2}(?:%s)\d{4}\d{2}:\d{2}:\d{2}' % (daycat, monthcat))
rfc822_fmt = '%d%b%Y%H:%M:%S'

def _rawparse(text, base=None, chop=False):
    otext = text
    text = text.strip().lower().replace(' ', '')

    parsed_tz = False
    if base is None:
        text, base = parsetz(text)
        if base != 0:
            parsed_tz = True

    # regex match is ~10x faster than strptime, so optimize
    # for the case that *most* datetimes will not be RFC822
    rfc822_match = rfc822_re.match(text)
    if rfc822_match is not None:

        # remove leading day since it is not used in strptime
        if grp := rfc822_match.groups()[0]:
            text = text.replace(grp, '', 1)

        try:
            dt = datetime.datetime.strptime(text, rfc822_fmt)
            return dt, base, len(text)
        except ValueError as e:
            raise s_exc.BadTypeValu(mesg=f'Error parsing time as RFC822 "{otext}"; {str(e)}', valu=otext)

    text = (''.join([c for c in text if c.isdigit()]))

    if chop:
        text = text[:17]

    tlen = len(text)

    try:
        if tlen == 4:
            if parsed_tz:
                raise s_exc.BadTypeValu(mesg=f'Not enough information to parse timezone properly for {otext}.',
                                        valu=otext)
            dt = datetime.datetime.strptime(text, '%Y')

        elif tlen == 6:
            if parsed_tz:
                raise s_exc.BadTypeValu(mesg=f'Not enough information to parse timezone properly for {otext}.',
                                        valu=otext)
            dt = datetime.datetime.strptime(text, '%Y%m')

        elif tlen == 8:
            if parsed_tz:
                raise s_exc.BadTypeValu(mesg=f'Not enough information to parse timezone properly for {otext}.',
                                        valu=otext)
            dt = datetime.datetime.strptime(text, '%Y%m%d')

        elif tlen == 10:
            if parsed_tz:
                raise s_exc.BadTypeValu(mesg=f'Not enough information to parse timezone properly for {otext}.',
                                        valu=otext)
            dt = datetime.datetime.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S')

        elif 15 <= tlen <= 20:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S%f')

        else:
            raise s_exc.BadTypeValu(valu=otext, name='time',
                                    mesg=f'Unknown time format for {otext}')
    except ValueError as e:
        raise s_exc.BadTypeValu(mesg=f'Error parsing time "{otext}"; {str(e)}', valu=otext)

    return dt, base, tlen

def parse(text, base=None, chop=False):
    '''
    Parse a time string into an epoch millis value.

    Args:
        text (str): Time string to parse
        base (int or None): Milliseconds to offset the time from
        chop (bool): Whether to chop the digit-only string to 17 chars

    Returns:
        int: Epoch milliseconds
    '''
    dtraw, base, tlen = _rawparse(text, base=base, chop=chop)
    return int((dtraw - EPOCH).total_seconds() * 1000 + base)

def wildrange(text):
    '''
    Parse an interval from a wild card time stamp: 2021/10/31*
    '''
    dttick, base, tlen = _rawparse(text)
    if tlen not in (4, 6, 8, 10, 12, 14):
        mesg = f'Time wild card position not supported for {text}'
        raise s_exc.BadTypeValu(mesg=mesg, valu=text)

    if tlen == 4:
        dttock = dttick + relativedelta(years=1)
    elif tlen == 6:
        dttock = dttick + relativedelta(months=1)
    elif tlen == 8:
        dttock = dttick + relativedelta(days=1)
    elif tlen == 10:
        dttock = dttick + relativedelta(hours=1)
    elif tlen == 12:
        dttock = dttick + relativedelta(minutes=1)
    else:  # tlen = 14
        dttock = dttick + relativedelta(seconds=1)

    tick = int((dttick - EPOCH).total_seconds() * 1000 + base)
    tock = int((dttock - EPOCH).total_seconds() * 1000 + base)
    return (tick, tock)

def parsetz(text):
    '''
    Parse timezone from time string, with UTC as the default.

    Args:
        text (str): Time string

    Returns:
        tuple: A tuple of text with tz chars removed and base milliseconds to offset time.
    '''

    match = tz_re.search(text)
    if match is None:
        return text, 0

    tzrel = match['tzrel']
    if tzrel is not None:

        base = onehour * int(match['tzhr']) + onemin * int(match['tzmin'])
        if tzrel == '+':
            base *= -1

        if abs(base) >= oneday:
            raise s_exc.BadTypeValu(mesg=f'Timezone offset must be between +/- 24 hours for {text}',
                                    valu=text, name='time')

        return text.replace(match['tzstr'], '', 1), base

    offset, _ = s_l_timezones.getTzOffset(match['tzname'])
    if offset is None:  # pragma: no cover
        raise s_exc.BadTypeValu(mesg=f'Unknown timezone for {text}', valu=text, name='time') from None

    base = offset * -1

    return text.replace(match['tzstr'], '', 1), base

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

    dt = EPOCH + datetime.timedelta(milliseconds=tick)
    millis = dt.microsecond / 1000
    if pack:
        return '%d%.2d%.2d%.2d%.2d%.2d%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)
    return '%d/%.2d/%.2d %.2d:%.2d:%.2d.%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, millis)

def day(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).day

def year(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).year

def month(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).month

def hour(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).hour

def minute(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).minute

def second(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).second

def dayofmonth(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).day - 1

def dayofweek(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).weekday()

def dayofyear(tick):
    return (EPOCH + datetime.timedelta(milliseconds=tick)).timetuple().tm_yday - 1

def ival(*times):

    times = [t for t in times if t is not None]

    minv = min(times)
    maxv = max(times)

    if minv == maxv:
        maxv += 1

    return (minv, maxv)

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
    otext = text
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
        mesg = f'unknown time delta units: {unittext} for {otext}'
        raise s_exc.BadTypeValu(name='time', valu=otext, mesg=mesg)

    return size * base

def toUTC(tick, fromzone):
    try:
        tz = pytz.timezone(fromzone)
    except pytz.exceptions.UnknownTimeZoneError as e:
        mesg = f'Unknown timezone: {fromzone}'
        raise s_exc.BadArg(mesg=mesg) from e

    base = datetime.datetime(1970, 1, 1, tzinfo=tz) + datetime.timedelta(milliseconds=tick)
    return int(base.astimezone(pytz.UTC).timestamp() * 1000)
