import binascii

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache

import synapse.lookup.cvss as s_cvss

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

    text = text.replace(' ', '').replace(':', '')

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

def cvss2_normalize(vect):
    '''
    Helper function to normalize CVSS2 vectors
    '''
    vdict = cvss_validate(vect, s_cvss.cvss2)
    return cvss_normalize(vdict, s_cvss.cvss2)

def cvss3x_normalize(vect):
    '''
    Helper function to normalize CVSS3.X vectors
    '''
    vdict = cvss_validate(vect, s_cvss.cvss3_1)
    return cvss_normalize(vdict, s_cvss.cvss3_1)

def cvss_normalize(vdict, vers):
    '''
    Normalize CVSS vectors
    '''
    metrics = s_cvss.metrics[vers]
    undefined = s_cvss.undefined[vers]

    vals = []
    for key in metrics:
        valu = vdict.get(key, undefined)
        if valu != undefined:
            vals.append(f'{key}:{valu}')

    return '/'.join(vals)

def cvss_validate(vect, vers):
    '''
    Validate (as best as possible) the CVSS vector string. Look for issues such as:
        - No duplicated metrics
        - Invalid metrics
        - Invalid metric values
        - Missing mandatory metrics

    Returns a dictionary with the parsed metric:value pairs.
    '''

    missing = []
    badvals = []
    invalid = []

    tag = s_cvss.tags[vers]
    METRICS = s_cvss.metrics[vers]

    # Do some canonicalization of the vector for easier parsing
    _vect = vect
    _vect = _vect.strip('(')
    _vect = _vect.strip(')')

    if _vect.startswith(tag):
        _vect = _vect[len(tag):]

    if vers == s_cvss.cvss3_0 and _vect.startswith(_tag := s_cvss.tags[s_cvss.cvss3_1]):
        _vect = _vect[len(_tag):]

    if vers == s_cvss.cvss3_1 and _vect.startswith(_tag := s_cvss.tags[s_cvss.cvss3_0]):
        _vect = _vect[len(_tag):]

    try:
        # Parse out metrics
        mets_vals = [k.split(':') for k in _vect.split('/')]

        # Convert metrics into a dictionary
        vdict = dict(mets_vals)

    except ValueError:
        raise s_exc.BadDataValu(mesg=f'Provided vector {vect} malformed')

    # Check that each metric is only specified once
    if len(mets_vals) != len(set(k[0] for k in mets_vals)):
        seen = []
        repeated = []

        for met, val in mets_vals:
            if met in seen:
                repeated.append(met)

            seen.append(met)

        repeated = ', '.join(repeated)
        raise s_exc.BadDataValu(mesg=f'Provided vectors {vect} contains duplicate metrics: {repeated}')

    invalid = []
    for metric in vdict:
        # Check that provided metrics are valid
        if metric not in METRICS:
            invalid.append(metric)

    if invalid:
        invalid = ', '.join(invalid)
        raise s_exc.BadDataValu(mesg=f'Provided vector {vect} contains invalid metrics: {invalid}')

    missing = []
    badvals = []
    for metric, (valids, mandatory, _) in METRICS.items():
        # Check for mandatory metrics
        if mandatory and metric not in vdict:
            missing.append(metric)

        # Check if metric value is valid
        val = vdict.get(metric, None)
        if metric in vdict and val not in valids:
            badvals.append(f'{metric}:{val}')

    if missing:
        missing = ', '.join(missing)
        raise s_exc.BadDataValu(mesg=f'Provided vector {vect} missing mandatory metric(s): {missing}')

    if badvals:
        badvals = ', '.join(badvals)
        raise s_exc.BadDataValu(mesg=f'Provided vector {vect} contains invalid metric value(s): {badvals}')

    return vdict
