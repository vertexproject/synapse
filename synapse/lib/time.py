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
# a space separated offset ( -05 00 ) may not start right after the year and month, where it is the end of a
# date ( 2021-06-07 02 )
tzspaced = r'(?<!^\d{4}[\-/\._:]?\d{2}\s?[\-\+]\d{2}\s\d{2})'
tz_re = regex.compile(
    r'\d(?P<tzstr>\s?(?:'
    # go style numeric offset followed by a redundant abbreviation ( -0500 EST ); the offset wins
    r'(?:(?P<tzrel>\-|\+)(?:(?P<tzhr>\d{2})(?P<tzmin>\d{2})|(?P<tzhr>\d{2})\s(?P<tzmin>\d{2})%s)\s?(?:%s))|'
    # utc / gmt prefixed offsets ( GMT+5, UTC-05:30 )
    r'(?:(?:utc|gmt|ut)(?P<tzrel>\-|\+)(?P<tzhr>\d{1,2})(?:[:\s]?(?P<tzmin>\d{2}))?)|'
    # parenthesized timezone names ( (EST) )
    r'(?:\((?P<tzname>%s)\))|'
    r'(?P<tzname>%s)|'
    r'(?:(?P<tzrel>\-|\+)(?:(?P<tzhr>\d{1,2}):?(?P<tzmin>\d{2})|(?P<tzhr>\d{2})\s(?P<tzmin>\d{2})%s)))'
    r')(?:[\-|\+]\d+(?:%s))?$' % (tzspaced, tzcat, tzcat, tzcat, tzspaced, unitcat),
    flags=regex.IGNORECASE
)

# a bare ISO 8601 +/-hh offset is only unambiguous following a time of at least minutes precision, either
# extended ( 05:55 ) or basic after a full date and a t or space ( 20151102t0555, 2015.11.02 0555 ). the search
# runs in reverse so the end anchor fails fast.
tzhour = r'(?P<tzstr>\s?(?P<tzrel>\-|\+)(?P<tzhr>\d{2}))(?:[\-|\+]\d+(?:%s))?$' % (unitcat,)
tzhour_re = regex.compile(
    r'(?:\d{1,2}:\d{2}(?::\d{2}(?:[\.,]\d+)?)?|'
    r'\d{4}[\-/\._:]?\d{2}[\-/\._:]?\d{2}[tT ]\d{4}(?:\d{2}(?:[\.,]\d+)?)?)' + tzhour,
    flags=regex.REVERSE
)

# ... or following separator free digits of at least seconds precision. matched forward from the start and
# possessively, since an offset never starts with a digit and backtracking over them is quadratic.
tzdigits_re = regex.compile(r'^\d(?:\s?\d){13}(?:\s?\d)*+' + tzhour)

# an RFC 2822 style comment after a numeric offset ( -0700 (PDT) )
tzcomment_re = regex.compile(r'\s?\([^()]*\)$')

# after timezone removal, only digits and separators may remain, and every separator must fall on a
# year, month, day, hour, minute or second boundary. a space separates the seconds only when one also
# separates the minutes, so a bare number after hh:mm is not read as seconds. only the day and hour may
# be a single digit: the day only when a separator comes before it and a t, @ or space then a time follow
# it, and the hour only when a separator comes before it and a colon follows it. only a trailing fraction
# may follow the seconds.
timefields = r'''
    \d{15,}                                   # separator free digits beyond seconds precision
    |
    \d{8}t\d{7,}                             # a basic format time with an undotted fraction
    |
    \d{4}(?:%(s)s?\d{2}){0,2}                 # a date, from year up to day
    |
    \d{4}%(s)s?\d{2}                          # year and month
    (?:%(s)s?(?P<day>\d{2})|%(s)s(?P<day>\d)(?=[t@ ]))  # a single digit day must be followed by t, @ or a space
    (?:%(s)s?(?P<hour>\d{2})|%(s)s(?P<hour>\d)(?=%(h)s))  # a single digit hour must be followed by a colon
    (?:
        (?:[ ]\d{2}[ ]\d{2}|%(s)s?\d{2}%(n)s?\d{2})  # minute and second
        (?:[\.,]\d+(?:[ ]\d+)*)?              # only a full seconds time may carry a fraction
        |
        (?:%(s)s?\d{2})?                      # minute
    )
'''
timeseps = {'s': r'[\-/\._:t@ ]', 'n': r'[\-/\._:t@]'}
timefields_re = regex.compile(timefields % {**timeseps, 'h': ':'}, flags=regex.VERBOSE)

# a single digit hour may also end a value whose trailing colon was stripped ( 2015/11/02 5:* )
timefields_colon_re = regex.compile(timefields % {**timeseps, 'h': r':|\Z'}, flags=regex.VERBOSE)

# clean ISO 8601 style values, which _rawparse reads without the general path. an offset may only follow a time.
isotime_tail = (
    r'(?:[tT ](?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{2})(?::(?P<second>[0-9]{2})(?:\.(?P<frac>[0-9]+))?)?'
    r'(?:[ ]?(?P<tz>[zZ]|(?P<tzrel>[\-+])(?P<tzhr>[0-9]{2}):?(?P<tzmin>[0-9]{2})))?)?'
)
isotime_re = regex.compile(
    r'(?P<year>[0-9]{4})[\-/](?P<month>[0-9]{2})(?:[\-/](?P<day>[0-9]{1,2})' + isotime_tail + r')?'
)

# colon separated dates ( 2008:04:19 11:49:11 ) must use colons for both separators and include the day
colontime_re = regex.compile(r'(?P<year>[0-9]{4}):(?P<month>[0-9]{2}):(?P<day>[0-9]{1,2})' + isotime_tail)

daycat = '|'.join(calendar.day_abbr[i].lower() for i in range(7))
monthcat = '|'.join(calendar.month_abbr[i].lower() for i in range(1, 13))
rfc822_re = regex.compile(r'((?:%s),)?\d{1,2}(?:%s)\d{4} ?\d{2}:\d{2}:\d{2}' % (daycat, monthcat))
rfc822_fmt = '%d%b%Y%H:%M:%S'

def _getTimeDigits(text, otext):
    '''
    Validate the structure of a timezone stripped time string and return its digits.
    '''
    # a trailing precision marker ( 2021-06-07? )
    if text.endswith(('?', '*')):
        text = text[:-1]

    # a trailing separator, which reprmax() emits and a wildcard lift leaves behind ( 2021-06-07T02:* )
    fieldsre = timefields_re
    if text.endswith(('-', '/', '.', '_', ':', 't', '@')):
        if text[-1] == ':':
            fieldsre = timefields_colon_re

        text = text[:-1]

    # text without any digits falls through to the unknown time format error
    if not any(c.isdigit() for c in text):
        return ''

    match = fieldsre.fullmatch(text)
    if match is None and ' ' in text:
        # spaces that split separator free digits are not field boundaries
        text = text.replace(' ', '')
        if text.isdigit():
            match = timefields_re.fullmatch(text)

    if match is None:
        mesg = f'Error parsing time "{otext}"; unexpected text in time value'
        raise s_exc.BadTypeValu(mesg=mesg, valu=otext, name='time')

    # pad the hour before the day so the day offset still holds
    day, hour = match.groups()
    if hour is not None and len(hour) == 1:
        offs = match.start('hour')
        text = text[:offs] + '0' + text[offs:]

    if day is not None and len(day) == 1:
        offs = match.start('day')
        text = text[:offs] + '0' + text[offs:]

    return ''.join([c for c in text if c.isdigit()])

def _fastparse(text, base, chop):
    '''
    Parse a clean ISO 8601 style or separator free digits time value, or return None for the general path.
    '''
    text = text.strip()
    if text.isdigit() and text.isascii():

        if chop:
            text = text[:17]

        tlen = len(text)
        if tlen not in (4, 6, 8, 10, 12, 14) and not 15 <= tlen <= 20:
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

        # a single digit day must be followed by a time
        if day is not None and len(day) == 1 and hour is None:
            return None

        if frac is not None:
            if chop:
                frac = frac[:3]

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

            base = 0
            if tzrel is not None:
                base = onehour * int(tzhr) + onemin * int(tzmin)
                if abs(base) >= oneday:
                    return None

                if tzrel == '+':
                    base *= -1

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
    Parse a clean ISO 8601 style or separator free digits time value into epoch millis, or return None.
    '''
    if (info := _fastparse(text, None, chop)) is None:
        return None

    dt, base, tlen = info
    return int((dt - EPOCH).total_seconds() * 1000 + base)

def _rawparse(text, base=None, chop=False):

    if (info := _fastparse(text, base, chop)) is not None:
        return info

    otext = text
    text = text.strip().lstrip('\ufeff').lower()

    # any run of whitespace is a single space, and only one between two digits is kept, as a field boundary
    parts = text.split()
    if len(parts) > 1:
        text = parts[0]
        for part in parts[1:]:
            if text[-1].isdigit() and part[0].isdigit():
                text += ' '

            text += part

    parsed_tz = False
    if base is None:
        text, base = parsetz(text)
        if base != 0:
            parsed_tz = True

    # regex match is ~10x faster than strptime, so optimize
    # for the case that *most* datetimes will not be RFC822
    rfc822_match = rfc822_re.match(text)
    if rfc822_match is not None:

        # strptime takes the rfc822 text without spaces
        text = text.replace(' ', '')

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
        text = text[:17]

    tlen = len(text)
    if tlen not in (4, 6, 8, 10, 12, 14) and not 15 <= tlen <= 20:
        raise s_exc.BadTypeValu(valu=otext, name='time', mesg=f'Unknown time format for {otext}')

    if parsed_tz and tlen < 12:
        raise s_exc.BadTypeValu(mesg=f'Not enough information to parse timezone properly for {otext}.', valu=otext)

    # each field is read at its fixed width, so an invalid one is rejected rather than re-split
    try:
        dt = datetime.datetime(int(text[:4]), int(text[4:6] or 1), int(text[6:8] or 1), int(text[8:10] or 0),
                               int(text[10:12] or 0), int(text[12:14] or 0), int(text[14:].ljust(6, '0')))
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

    try:
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
    except (ValueError, OverflowError):
        mesg = f'Time wild card range exceeds the maximum time for {text}'
        raise s_exc.BadTypeValu(mesg=mesg, valu=text) from None

    tick = int((dttick - EPOCH).total_seconds() * 1000 + base)
    tock = int((dttock - EPOCH).total_seconds() * 1000 + base)
    return (tick, tock)

def _matchtz(text):
    if (match := tz_re.search(text)) is not None:
        return match

    if (match := tzhour_re.search(text)) is not None:
        return match

    return tzdigits_re.match(text)

def parsetz(text):
    '''
    Parse timezone from time string, with UTC as the default.

    Args:
        text (str): Time string

    Returns:
        tuple: A tuple of text with tz chars removed and base milliseconds to offset time.
    '''

    # a trailing precision marker ( 2021-06-07T02:03:04Z* ) is set aside and returned with the remaining text
    mark = ''
    if text.endswith(('?', '*')):
        mark = text[-1]
        text = text[:-1]

    match = None
    if text.endswith(')') and (cmnt := tzcomment_re.search(text)) is not None:
        # a comment is dropped when a numeric offset precedes it, which then applies
        head = text[:cmnt.start()]
        match = _matchtz(head)
        if match is not None and match['tzrel'] is not None:
            text = head
        else:
            match = None

    if match is None:
        match = _matchtz(text)

    if match is None:
        return text + mark, 0

    offs, ends = match.span('tzstr')
    rest = text[:offs] + text[ends:] + mark

    tzrel = match['tzrel']
    if tzrel is not None:

        base = onehour * int(match['tzhr'])
        if (tzmin := match.groupdict().get('tzmin')) is not None:
            base += onemin * int(tzmin)
        if tzrel == '+':
            base *= -1

        if abs(base) >= oneday:
            raise s_exc.BadTypeValu(mesg=f'Timezone offset must be between +/- 24 hours for {text}',
                                    valu=text, name='time')

        return rest, base

    offset, _ = s_l_timezones.getTzOffset(match['tzname'])
    if offset is None:  # pragma: no cover
        raise s_exc.BadTypeValu(mesg=f'Unknown timezone for {text}', valu=text, name='time') from None

    base = offset * -1

    return rest, base

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

    try:
        size = int(sizetext, 0)
    except ValueError:
        mesg = f'invalid time delta size: {sizetext} for {otext}'
        raise s_exc.BadTypeValu(name='time', valu=otext, mesg=mesg) from None

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

    base = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=tick)
    try:
        localized = tz.localize(base, is_dst=None)
    except pytz.exceptions.AmbiguousTimeError as e:
        mesg = f'Ambiguous time: {base} {fromzone}'
        raise s_exc.BadArg(mesg=mesg) from e

    return int(localized.astimezone(pytz.UTC).timestamp() * 1000)
