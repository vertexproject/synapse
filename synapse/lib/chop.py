import binascii

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache

TagMatchRe = regex.compile(r'([\w*]+\.)*[\w*]+')

'''
Shared primitive routines for chopping up strings and values.
'''
def intstr(text):
    return int(text, 0)

def digits(text):
    return ''.join([c for c in text if c.isdigit()])

def printables(text):
    return ''.join([c for c in text if c.isprintable()])

def hexstr(text):
    '''
    Ensure a string is valid hex.

    Args:
        text (str): String to normalize.

    Examples:
        Norm a few strings:

            hexstr('0xff00')
            hexstr('ff00')

    Notes:
        Will accept strings prefixed by '0x' or '0X' and remove them.

    Returns:
        str: Normalized hex string.
    '''
    text = text.strip().lower()
    if text.startswith(('0x', '0X')):
        text = text[2:]

    if not text:
        raise s_exc.BadTypeValu(valu=text, name='hexstr',
                                mesg='No string left after stripping')

    try:
        # checks for valid hex width and does character
        # checking in C without using regex
        s_common.uhex(text)
    except (binascii.Error, ValueError) as e:
        raise s_exc.BadTypeValu(valu=text, name='hexstr', mesg=str(e)) from None
    return text

def onespace(text):
    return ' '.join(text.split())

@s_cache.memoize(size=10000)
def tag(text):
    return '.'.join(tagpath(text))

@s_cache.memoize(size=10000)
def tagpath(text):
    text = text.lower().strip('#').strip()
    return [onespace(t) for t in text.split('.')]

@s_cache.memoize(size=10000)
def tags(norm):
    '''
    Divide a normalized tag string into hierarchical layers.
    '''
    # this is ugly for speed....
    parts = norm.split('.')
    return ['.'.join(parts[:i]) for i in range(1, len(parts) + 1)]

@s_cache.memoize(size=10000)
def stormstring(s):
    '''
    Make a string storm safe by escaping backslashes and double quotes.

    Args:
        s (str): String to make storm safe.

    Notes:
        This does not encapsulate a string in double quotes.

    Returns:
        str: A string which can be embedded directly into a storm query.

    '''
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    return s

def validateTagMatch(tag):
    '''
    Raises an exception if tag is not a valid tagmatch (i.e. a tag that might have globs)
    '''

    if TagMatchRe.fullmatch(tag) is None:
        raise s_exc.BadTag(mesg='Invalid tag match')

unicode_dashes = (
    '\u2011',  # non-breaking hyphen
    '\u2012',  # figure dash
    '\u2013',  # endash
    '\u2014',  # emdash
)
unicode_dashes_replace = tuple([(char, '-') for char in unicode_dashes])

def replaceUnicodeDashes(valu):
    '''
    Replace unicode dashes in a string with regular dashes.

    Args:
        valu (str): A string.

    Returns:
        str: A new string with replaced dashes.
    '''
    for dash in unicode_dashes:
        valu = valu.replace(dash, '-')
    return valu
