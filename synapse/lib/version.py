'''
Synapse utilites for dealing with Semvar versioning.
This includes the Synapse version information.
'''
import string

import regex

# This module is imported during synapse.__init__.  As such, we can't pull
# arbitrary modules from Synapse here. synapse.exc is currently safe,
# but we should not add other modules to this module.
import synapse.exc as s_exc

vseps = ('.', '-', '_', '+')
mask20 = 0xFFFFF
mask60 = 0xFFFFFFFFFFFFFFF
semver_re = regex.compile(r'''^(?P<maj>(0(?![0-9])|[1-9][0-9]*))\.(?P<min>(0(?![0-9])|[1-9][0-9]*))\.(?P<pat>(0(?![0-9])|[1-9][0-9]*))(\-(?P<pre>([0-9A-Za-z\-\.]+)))?(\+(?P<bld>([0-9A-Za-z\.\-]+)))?$''')

def parseSemver(text):
    '''
    Parse a Semantic Version string into is component parts.

    Args:
        text (str): A text string to parse into semver components. This string has whitespace and leading 'v'
        characters stripped off of it.

    Examples:
        Parse a string into it semvar parts::

            parts = parseSemver('v1.2.3')

    Returns:
        dict: The dictionary will contain the keys 'major', 'minor' and 'patch' pointing to integer values.
        The dictionary may also contain keys for 'build' and 'pre' information if that data is parsed out
        of a semver string. None is returned if the string is not a valid Semver string.
    '''
    # eat whitespace and leading chars common on version strings
    txt = text.strip().lstrip('vV')
    ret = {}

    m = semver_re.match(txt)
    if not m:
        return None
    d = m.groupdict()
    ret['major'] = int(d.get('maj'))
    ret['minor'] = int(d.get('min'))
    ret['patch'] = int(d.get('pat'))

    pre = d.get('pre')
    bld = d.get('bld')

    if pre:
        # Validate pre
        parts = pre.split('.')
        for part in parts:
            if not part:
                return None
            try:
                int(part)
            except ValueError:
                continue
            else:
                if part[0] == '0' and len(part) > 1:
                    return None
        ret['pre'] = pre

    if bld:
        # Validate bld
        parts = bld.split('.')
        for part in parts:
            if not part:
                return None
        ret['build'] = bld

    return ret

def packVersion(major, minor=0, patch=0):
    '''
    Pack a set of major/minor/patch integers into a single integer for storage.

    Args:
        major (int): Major version level integer.
        minor (int): Minor version level integer.
        patch (int): Patch version level integer.

    Returns:
        int:  System normalized integer value to represent a software version.
    '''

    ret = patch & mask20
    ret = ret | (minor & mask20) << 20
    ret = ret | (major & mask20) << 20 * 2
    return ret

def unpackVersion(ver):
    '''
    Unpack a system normalized integer representing a softare version into its component parts.

    Args:
        ver (int): System normalized integer value to unpack into a tuple.

    Returns:
        (int, int, int): A tuple containing the major, minor and patch values shifted out of the integer.
    '''
    major = (ver >> 20 * 2) & mask20
    minor = (ver >> 20) & mask20
    patch = ver & mask20
    return major, minor, patch

def fmtVersion(*vsnparts):
    '''
    Join a string of parts together with a . separator.

    Args:
        *vsnparts:

    Returns:

    '''
    if len(vsnparts) < 1:
        raise s_exc.BadTypeValu('Not enough version parts to form a version string with.',
                                vsnparts=vsnparts)
    ret = '.'.join([str(part).lower() for part in vsnparts])
    return ret

def parseVersionParts(text, seps=vseps):
    '''
    Extract a list of major/minor/version integer strings from a string.

    Args:
        text (str): String to parse
        seps (tuple): A tuple or list of separators to use when parsing the version string.

    Examples:
        Parse a simple version string into a major and minor parts::

            parts = parseVersionParts('1.2')

        Parse a complex version string into a major and minor parts::

            parts = parseVersionParts('wowsoft_1.2')

        Parse a simple version string into a major, minor and patch parts.  Parts after the "3." are dropped from the
        results::

            parts = parseVersionParts('1.2.3.4.5')

    Notes:
        This attempts to brute force out integers from the version string by stripping any leading ascii letters and
        part separators, and then regexing out numeric parts optionally followed by part separators.  It will stop at
        the first mixed-character part encountered.  For example, "1.2-3a" would only parse out the "1" and "2" from
        the string.

    Returns:
        dict: Either a empty dictionary or dictionary containing up to three keys, 'major', 'minor' and 'patch'.
    '''
    # Join seps together
    seps = ''.join(seps)
    # Strip whitespace
    text = text.strip()
    # Strip off leading chars
    text = text.lstrip(string.ascii_letters)
    # Strip off any leading separator which may be present
    text = text.lstrip(seps)
    pattern = r'^(\d+)([{}]+|$)'.format(regex.escape(seps))
    parts = []
    ret = {}
    off = 0
    while True:
        m = regex.search(pattern, text[off:])
        if not m:
            break
        off += m.end()
        p, s = m.groups()
        parts.append(int(p))
    if not parts:
        return None
    keys = ('major', 'minor', 'patch')
    ret.update(zip(keys, parts))
    return ret


##############################################################################
# The following are touched during the release process by bumpversion.
# Do not modify these directly.
version = (0, 0, 46)
verstring = '.'.join([str(x) for x in version])
