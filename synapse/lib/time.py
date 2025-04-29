'''
Time related utilities for synapse "epoch micros" time values.
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
EPOCHUTC = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)

onesec = 1000000
onemin = 60000000
onehour = 3600000000
oneday = 86400000000

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

PREC_YEAR = 4
PREC_MONTH = 8
PREC_DAY = 12
PREC_HOUR = 16
PREC_MINUTE = 20
PREC_SECOND = 24
PREC_MILLI = 27
PREC_MICRO = 30

MAX_TIME = 253402300799999999

def total_microseconds(delta):
    return (delta.days * oneday) + (delta.seconds * onesec) + delta.microseconds

def timestamp(dt):
    '''
    Convert a naive or aware datetime object to an epoch micros timestamp.
    '''
    if dt.tzinfo is not None:
        return total_microseconds(dt.astimezone(pytz.UTC) - EPOCHUTC)
    return total_microseconds(dt - EPOCH)

def yearprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)
    if maxfill:
        try:
            return total_microseconds(datetime.datetime(dtime.year + 1, 1, 1) - EPOCH) - 1
        except (ValueError, OverflowError):
            return MAX_TIME
    return total_microseconds(datetime.datetime(dtime.year, 1, 1) - EPOCH)

def monthprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(months=1)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    newdt = datetime.datetime(dtime.year, dtime.month, 1)
    return total_microseconds(newdt - EPOCH) - subv

def dayprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(days=1)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    newdt = datetime.datetime(dtime.year, dtime.month, dtime.day)
    return total_microseconds(newdt - EPOCH) - subv

def hourprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(hours=1)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    newdt = datetime.datetime(dtime.year, dtime.month, dtime.day, dtime.hour)
    return total_microseconds(newdt - EPOCH) - subv

def minuteprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(minutes=1)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    newdt = datetime.datetime(dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute)
    return total_microseconds(newdt - EPOCH) - subv

def secprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(seconds=1)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    newdt = datetime.datetime(dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute, dtime.second)
    return total_microseconds(newdt - EPOCH) - subv

def milliprec(ts, maxfill=False):
    dtime = EPOCH + datetime.timedelta(microseconds=ts)

    subv = 0
    if maxfill:
        try:
            dtime += relativedelta(microseconds=1000)
        except (ValueError, OverflowError):
            return MAX_TIME
        subv = 1

    millis = (dtime.microsecond // 1000) * 1000
    newdt = datetime.datetime(dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute, dtime.second, millis)
    return total_microseconds(newdt - EPOCH) - subv

precfuncs = {
    PREC_YEAR: yearprec,
    PREC_MONTH: monthprec,
    PREC_DAY: dayprec,
    PREC_HOUR: hourprec,
    PREC_MINUTE: minuteprec,
    PREC_SECOND: secprec,
    PREC_MILLI: milliprec,
    PREC_MICRO: lambda x, maxfill=False: x
}

precisions = {
    'year': PREC_YEAR,
    'month': PREC_MONTH,
    'day': PREC_DAY,
    'hour': PREC_HOUR,
    'minute': PREC_MINUTE,
    'second': PREC_SECOND,
    'millisecond': PREC_MILLI,
    'microsecond': PREC_MICRO,
}

preclookup = {valu: vstr for vstr, valu in precisions.items()}
preclen = {
    4: PREC_YEAR,
    6: PREC_MONTH,
    8: PREC_DAY,
    10: PREC_HOUR,
    12: PREC_MINUTE,
    14: PREC_SECOND,
    15: PREC_MILLI,
    16: PREC_MILLI,
    17: PREC_MILLI,
    18: PREC_MICRO,
    19: PREC_MICRO,
    20: PREC_MICRO,
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
        text = text[:20]

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
    Parse a time string into an epoch micros value.

    Args:
        text (str): Time string to parse
        base (int or None): Microseconds to offset the time from
        chop (bool): Whether to chop the digit-only string to 20 chars

    Returns:
        int: Epoch microseconds
    '''
    dtraw, base, tlen = _rawparse(text, base=base, chop=chop)
    return total_microseconds(dtraw - EPOCH) + base

def parseprec(text, base=None, chop=False):
    '''
    Parse a time string (which may have an implicit precision) into an epoch micros value and precision tuple.

    Args:
        text (str): Time string to parse
        base (int or None): Microseconds to offset the time from
        chop (bool): Whether to chop the digit-only string to 20 chars

    Returns:
        tuple: Epoch microseconds timestamp and precision enum value if present.
    '''
    dtraw, base, tlen = _rawparse(text, base=base, chop=chop)
    if text.endswith('?'):
        return (total_microseconds(dtraw - EPOCH) + base, preclen[tlen])
    return (total_microseconds(dtraw - EPOCH) + base, None)

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

    tick = total_microseconds(dttick - EPOCH) + base
    tock = total_microseconds(dttock - EPOCH) + base
    return (tick, tock)

def parsetz(text):
    '''
    Parse timezone from time string, with UTC as the default.

    Args:
        text (str): Time string

    Returns:
        tuple: A tuple of text with tz chars removed and base microseconds to offset time.
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
    Return a date string for an epoch-micros timestamp.

    Args:
        tick (int): The timestamp in microseconds since the epoch.

    Returns:
        (str):  A date time string
    '''
    if tick == 0x7fffffffffffffff:
        return '?'

    dt = EPOCH + datetime.timedelta(microseconds=tick)

    mstr = ''
    micros = dt.microsecond

    if pack:
        if micros > 0:
            mstr = f'{micros:06d}'.rstrip('0')
        return f'{dt.year:04d}{dt.month:02d}{dt.day:02d}{dt.hour:02d}{dt.minute:02d}{dt.second:02d}{mstr}'

    if micros > 0:
        mstr = f'.{micros:06d}'.rstrip('0')
    return f'{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}{mstr}Z'

def day(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).day

def year(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).year

def month(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).month

def hour(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).hour

def minute(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).minute

def second(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).second

def dayofmonth(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).day - 1

def dayofweek(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).weekday()

def dayofyear(tick):
    return (EPOCH + datetime.timedelta(microseconds=tick)).timetuple().tm_yday - 1

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

    base = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=tick)
    try:
        localized = tz.localize(base, is_dst=None)
    except pytz.exceptions.AmbiguousTimeError as e:
        mesg = f'Ambiguous time: {base} {fromzone}'
        raise s_exc.BadArg(mesg=mesg) from e

    return total_microseconds(localized.astimezone(pytz.UTC) - EPOCHUTC)
