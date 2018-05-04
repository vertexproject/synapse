import binascii

import synapse.exc as s_exc
import synapse.common as s_common

'''
Shared primitive routines for chopping up strings and values.
'''
def intstr(text):
    return int(text, 0)

def intrange(text):
    mins, maxs = text.split(':', 1)
    return intstr(mins), intstr(maxs)

def digits(text):
    return ''.join([c for c in text if c.isdigit()])

def mergeRanges(x, y):
    '''
    Merge two ranges into one.
    '''
    minv = min(*x, *y)
    maxv = max(*x, *y)
    return (minv, maxv)

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
        raise s_exc.BadTypeValu(valu=text,
                                mesg='No string left after stripping')

    try:
        # checks for valid hex width and does character
        # checking in C without using regex
        s_common.uhex(text)
    except binascii.Error as e:
        raise s_exc.BadTypeValu(valu=text, mesg=str(e))
    return text
