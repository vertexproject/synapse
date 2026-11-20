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

durprecisions = {
    'microsecond': 1,
    'millisecond': 1000,
    'second': onesec,
    'minute': onemin,
    'hour': onehour,
    'day': oneday,
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
    # go style numeric offset followed by a redundant abbreviation ( -0500 EST ); the offset wins
    r'(?:(?P<tzrel>\-|\+)(?P<tzhr>\d{2})(?P<tzmin>\d{2})\s?(?:%s))|'
    # utc / gmt prefixed offsets ( GMT+5, UTC-05:30 )
    r'(?:(?:utc|gmt|ut)(?P<tzrel>\-|\+)(?P<tzhr>\d{1,2})(?::?(?P<tzmin>\d{2}))?)|'
    # parenthesized timezone names ( (EST) )
    r'(?:\((?P<tzname>%s)\))|'
    r'(?P<tzname>%s)|'
    r'(?:(?P<tzrel>\-|\+)(?P<tzhr>\d{1,2}):?(?P<tzmin>\d{2})))'
    r')(?:[\-|\+]\d+(?:%s))?$' % (tzcat, tzcat, tzcat, unitcat),
    flags=regex.IGNORECASE
)

# a bare ISO 8601 +/-hh offset is only unambiguous following a full seconds precision time
tzhour_re = regex.compile(
    r'(?:\d{2}:\d{2}:\d{2}(?:[\.,]\d+)?|^\d{14,})'
    r'(?P<tzstr>\s?(?P<tzrel>\-|\+)(?P<tzhr>\d{2}))'
    r'(?:[\-|\+]\d+(?:%s))?$' % (unitcat,),
)

# after timezone removal, only digits and separators may remain, and every separator must fall on a
# year, month, day, hour, minute or second boundary. only a trailing fraction may follow the seconds.
timefields_re = regex.compile(r'''
    \d{15,}                             # separator free digits beyond seconds precision
    |
    \d{4}                               # year
    (?:
        (?:%(s)s?\d{2}){5}              # month, day, hour, minute and second
        (?:[\.,]\d+)?                   # only a full seconds time may carry a fraction
        |
        (?:%(s)s?\d{2}){0,4}            # a partial time, from year up to minutes
    )
''' % {'s': r'[\-/\._:t@]'}, flags=regex.VERBOSE)

# clean ISO 8601 style values, which _rawparse reads without the general path. an offset may only follow a time.
isotime_tail = (
    r'(?:[tT ](?P<hour>[0-9]{2}):(?P<minute>[0-9]{2})(?::(?P<second>[0-9]{2})(?:\.(?P<frac>[0-9]+))?)?'
    r'(?:[ ]?(?P<tz>[zZ]|(?P<tzrel>[\-+])(?P<tzhr>[0-9]{2}):?(?P<tzmin>[0-9]{2})))?)?'
)
isotime_re = regex.compile(
    r'(?P<year>[0-9]{4})[\-/](?P<month>[0-9]{2})(?:[\-/](?P<day>[0-9]{2})' + isotime_tail + r')?'
)

# colon separated dates ( 2008:04:19 11:49:11 ) must use colons for both separators and include the day
colontime_re = regex.compile(r'(?P<year>[0-9]{4}):(?P<month>[0-9]{2}):(?P<day>[0-9]{2})' + isotime_tail)

daycat = '|'.join(calendar.day_abbr[i].lower() for i in range(7))
monthcat = '|'.join(calendar.month_abbr[i].lower() for i in range(1, 13))
rfc822_re = regex.compile(r'((?:%s),)?\d{1,2}(?:%s)\d{4}\d{2}:\d{2}:\d{2}' % (daycat, monthcat))
rfc822_fmt = '%d%b%Y%H:%M:%S'

def _getTimeDigits(text, otext):
    '''
    Validate the structure of a timezone stripped time string and return its digits.
    '''
    # a trailing precision marker ( 2021-06-07? )
    if text.endswith(('?', '*')):
        text = text[:-1]

    # a trailing separator, which reprmax() emits and a wildcard lift leaves behind ( 2021-06-07T02:* )
    if text.endswith(('-', '/', '.', '_', ':', 't', '@')):
        text = text[:-1]

    # text without any digits falls through to the unknown time format error
    if not any(c.isdigit() for c in text):
        return ''

    if timefields_re.fullmatch(text) is None:
        mesg = f'Error parsing time "{otext}"; unexpected text in time value'
        raise s_exc.BadTypeValu(mesg=mesg, valu=otext, name='time')

    return ''.join([c for c in text if c.isdigit()])

def _tzoffs(tzrel, tzhr, tzmin):
    '''
    Return the base offset for a numeric timezone offset, where tzmin may be None.
    '''
    base = onehour * int(tzhr)
    if tzmin is not None:
        base += onemin * int(tzmin)

    if tzrel == '+':
        base *= -1

    return base

def _fastparse(text, base, chop):
    '''
    Parse a clean ISO 8601 style or separator free digits time value, or return None for the general path.
    '''
    text = text.strip()
    if text.isdigit() and text.isascii():

        if chop:
            text = text[:20]

        tlen = len(text)
        if tlen not in preclen:
            return None

        year, month, day, hour, minute, second, frac = (text[:4], text[4:6], text[6:8], text[8:10],
                                                        text[10:12], text[12:14], text[14:])

    else:
        match = isotime_re.fullmatch(text)
        if match is None and text[4:5] == ':':
            match = colontime_re.fullmatch(text)

        if match is None:
            return None

        year, month, day, hour, minute, second, frac, tz, tzrel, tzhr, tzmin = match.groups()

        if frac is not None:
            if chop:
                frac = frac[:6]

            elif len(frac) > 6:
                return None

            tlen = 14 + len(frac)

        elif second is not None:
            tlen = 14

        elif hour is not None:
            tlen = 12

        elif day is not None:
            tlen = 8

        else:
            tlen = 6

        if tz is not None:
            if base is not None:
                return None

            # the general path strips the first copy of the offset text, which may be the day and hour
            if tzhr == day and tzmin == hour:
                return None

            base = 0
            if tzrel is not None:
                base = _tzoffs(tzrel, tzhr, tzmin)
                if abs(base) >= oneday:
                    return None

    if base is None:
        base = 0

    try:
        dt = datetime.datetime(int(year), int(month or 1), int(day or 1), int(hour or 0), int(minute or 0),
                               int(second or 0), int(frac.ljust(6, '0')) if frac else 0)
    except ValueError:
        return None

    return dt, base, tlen

def parsefast(text, chop=False):
    '''
    Parse a clean ISO 8601 style or separator free digits time value into epoch micros, or return None.
    '''
    if (info := _fastparse(text, None, chop)) is None:
        return None

    dt, base, tlen = info
    return total_microseconds(dt - EPOCH) + base

def _rawparse(text, base=None, chop=False):

    if (info := _fastparse(text, base, chop)) is not None:
        return info

    return _textparse(text, base, chop)

def _textparse(text, base, chop):
    '''
    Parse a time value with the general path, which handles timezones, separators and RFC822.
    '''
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

    text = _getTimeDigits(text, otext)

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
    return _parseprec(text, base, chop, True)

def _parseprec(text, base, chop, fast):
    '''
    Parse a time string into an epoch micros value and precision, only trying the fast path if fast is set.
    '''
    if fast:
        dtraw, base, tlen = _rawparse(text, base, chop)
    else:
        dtraw, base, tlen = _textparse(text, base, chop)

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
        match = tzhour_re.search(text)

    if match is None:
        return text, 0

    tzrel = match['tzrel']
    if tzrel is not None:

        base = _tzoffs(tzrel, match['tzhr'], match.groupdict().get('tzmin'))
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

def reprmax(tick):
    '''
    Return a date string for a max-fill epoch-micros timestamp, collapsing the
    trailing time fields which were filled up to their maximum into a `*`.

    A max-fill timestamp is produced when a partial time expression is normed
    up to the maximum of its precision window (e.g. `2025-12-31` -> the last
    microsecond of that day). Rather than displaying the filled maximum (e.g.
    `2025-12-31T23:59:59.999999Z`), this collapses the filled tail into a
    `*` (e.g. `2025-12-31*`). The fill boundary is determined dynamically
    from the value itself.
    '''
    if tick == 0x7fffffffffffffff:
        return '?'

    if tick == 0x7ffffffffffffffe:
        return '*'

    dt = EPOCH + datetime.timedelta(microseconds=tick)

    datestr = f'{dt.year:04d}-{dt.month:02d}-{dt.day:02d}'

    micro = dt.microsecond

    if micro == 999999:

        if dt.second != 59:
            return f'{datestr}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.*'

        if dt.minute != 59:
            return f'{datestr}T{dt.hour:02d}:{dt.minute:02d}:*'

        if dt.hour != 23:
            return f'{datestr}T{dt.hour:02d}:*'

        return f'{datestr}*'

    if micro % 1000 == 999:
        return f'{datestr}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{micro // 1000:03d}*'

    # not a detectable max-fill boundary; render the full timestamp
    return repr(tick)

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
