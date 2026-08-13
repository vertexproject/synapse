'''
Synapse utilites for dealing with Semvar versioning.
This includes the Synapse version information.
'''
import string

import regex

import packaging.version as p_version
import packaging.specifiers as p_specifiers

# This module is imported during synapse.__init__.  As such, we can't pull
# arbitrary modules from Synapse here. synapse.exc is currently safe,
# but we should not add other modules to this module.
import synapse.exc as s_exc

vseps = ('.', '-', '_', '+')
mask4 = 0xF
mask20 = 0xFFFFF
mask32 = 0xFFFFFFFF
mask60 = 0xFFFFFFFFFFFFFFF
# Ordered pre/release ranks used to build a sortable version integer. The values
# are ordered so that a final release sorts strictly *above* all of its
# pre-releases within the same major.minor.patch band, and a post-release sorts
# above the release. dev is the floor so a dev release sorts below alpha.
# RANK_PRE_NUMERIC is for a purely-numeric pre-release identifier (e.g. the
# '0.3.7' in '1.0.0-0.3.7'); per SemVer precedence numeric identifiers sort
# below alphanumeric ones, so it ranks below alpha. RANK_PRE_OTHER is for a
# pre-release tag that doesn't match any recognized tier (e.g. '-z'); it sorts
# above rc (closest to release, since we don't know any better).
RANK_DEV = 0x1
RANK_PRE_NUMERIC = 0x2
RANK_ALPHA = 0x3
RANK_BETA = 0x4
RANK_RC = 0x5
RANK_PRE_OTHER = 0x6
RANK_RELEASE = 0x7
RANK_POST = 0x8

# SemVer major.minor.patch with the codebase's long-standing PEP 440 a|b|rc pre-release extension
# (e.g. "3.0.0b2"; not strictly SemVer, but accepted here). No epoch. Used by parseSemver, which
# backs the it:semver type and version/EOL parsing -- it:semver does NOT accept a PEP 440 epoch.
semverstr = r'''^(?P<maj>(0(?![0-9])|[1-9][0-9]*))\.(?P<min>(0(?![0-9])|[1-9][0-9]*))\.(?P<pat>(0(?![0-9])|[1-9][0-9]*))(?P<pep>(a|b|rc)[0-9]+)?(\-(?P<pre>([0-9A-Za-z\-\.]+)))?(\+(?P<bld>([0-9A-Za-z\.\-]+)))?$'''
semver_re = regex.compile(semverstr)

# The package-version pattern: semverstr plus an OPTIONAL leading PEP 440 epoch prefix (e.g.
# "3!1.2.3"), so power-ups on the Synapse 3.x line sort above their legacy 2.x.x counterparts. Used
# by synapse.lib.schemas to validate both a Storm package's ``version`` field and its
# ``build:synapse:version`` stamp. The epoch stays optional (not mandatory): the synapse:version
# stamp, the platform packages (synapse-enterprise, optic), and third-party power-ups all carry
# plain, un-epoch'd versions that must continue to validate.
verstr = r'^(?:(?P<epoch>[0-9]+)!)?' + semverstr[1:]
ver_re = regex.compile(verstr)

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
    maj = d.get('maj')
    min_ = d.get('min')
    pat = d.get('pat')
    if maj is None or min_ is None or pat is None:  # pragma: no cover
        return None

    ret['major'] = int(maj)
    ret['minor'] = int(min_)
    ret['patch'] = int(pat)

    pre = d.get('pre')
    pep = d.get('pep')
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
    elif pep:
        ret['pre'] = pep

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

def packVersionCore(major, minor=0, patch=0, rank=RANK_RELEASE):
    '''
    Pack major/minor/patch plus a pre/release rank into a single sortable int.

    The layout (high to low) is [ major:20 ][ minor:20 ][ patch:20 ][ rank:4 ]
    so that integer ordering matches SemVer 2.0.0 precedence, including that a
    final release sorts above its pre-releases (see the RANK_* constants). The
    result fits in an unsigned 64 bit integer.
    '''
    ret = rank & mask4
    ret |= (patch & mask20) << 4
    ret |= (minor & mask20) << 24
    ret |= (major & mask20) << 44
    return ret

def unpackVersionCore(valu):
    '''
    Unpack a packVersionCore() integer into a (major, minor, patch, rank) tuple.
    '''
    rank = valu & mask4
    patch = (valu >> 4) & mask20
    minor = (valu >> 24) & mask20
    major = (valu >> 44) & mask20
    return major, minor, patch, rank

def packVersionFull(epoch, major, minor=0, patch=0, rank=RANK_RELEASE):
    '''
    Pack a PEP 440 subset (epoch + major/minor/patch + rank) into a sortable int.

    The epoch is prepended above the packVersionCore() value so that integer
    ordering matches PEP 440 precedence for the encoded fields. The result fits
    in an unsigned 128 bit integer. Finer PEP 440 details (numeric pre-release
    sub-identifiers, dev/post ordinals, local versions) are intentionally not
    encoded here -- they are resolved by the version-aware filter pass.
    '''
    return ((epoch & mask32) << 64) | packVersionCore(major, minor, patch, rank)

_semver_pre_tiers = (
    (('a', 'alpha'), RANK_ALPHA),
    (('b', 'beta'), RANK_BETA),
    (('rc', 'c', 'pre', 'preview'), RANK_RC),
)

def semverRank(pre):
    '''
    Derive an ordered rank from a SemVer pre-release string (as kept by
    parseSemver, e.g. 'a20260617', 'alpha.1', 'rc2'). A missing pre-release is a
    final release. A purely-numeric first identifier (e.g. '0.3.7') buckets at
    RANK_PRE_NUMERIC (numeric identifiers sort below alphanumeric ones per SemVer
    precedence). Any other unrecognized pre-release string is still a
    pre-release, so it buckets at RANK_PRE_OTHER (below release, above rc);
    intra-tier ordering is not encoded.
    '''
    if pre is None:
        return RANK_RELEASE

    # rstrip drops a trailing numeric sub-id (e.g. 'a20260617' -> 'a'); if the
    # first identifier was all digits this leaves an empty head, i.e. a numeric
    # pre-release identifier.
    head = pre.split('.', 1)[0].rstrip('0123456789').lower()
    if head == '':
        return RANK_PRE_NUMERIC

    for names, rank in _semver_pre_tiers:
        if head in names:
            return rank

    return RANK_PRE_OTHER

def pep440Rank(ver):
    '''
    Derive an ordered rank from a packaging.version.Version. A version with a
    pre-release (a/b/rc) ranks at that tier; a post-release ranks above release;
    a dev release (without pre/post) is the floor; otherwise it is a release.
    '''
    if ver.pre is not None:
        return {'a': RANK_ALPHA, 'b': RANK_BETA, 'rc': RANK_RC}[ver.pre[0]]

    if ver.post is not None:
        return RANK_POST

    if ver.dev is not None:
        return RANK_DEV

    return RANK_RELEASE

def fmtVersion(*vsnparts):
    '''
    Join a string of parts together with a . separator.

    Args:
        *vsnparts:

    Returns:

    '''
    if len(vsnparts) < 1:
        raise s_exc.BadTypeValu(valu=repr(vsnparts), name='fmtVersion',
                                mesg='Not enough version parts to form a version string with.',)
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


def parse(valu):
    '''
    Return a packaging.version.Version for a PEP 440 string or a legacy int tuple/list.

    Accepts:
      - str: any PEP 440 version string (e.g. "3.0.0", "3.0.0a20260617")
      - tuple/list: legacy int triple (e.g. (3, 0, 0)) -- joined with "." first
    '''
    if isinstance(valu, (tuple, list)):
        valu = '.'.join(str(x) for x in valu)
    return p_version.Version(str(valu))


def release(verstr=None):
    '''
    Return the (major, minor, patch) integer triple for a version string.

    If verstr is None, uses the module-level version string.
    Accepts PEP 440 strings or dot-separated int strings.
    '''
    if verstr is None:
        verstr = version
    if isinstance(verstr, (tuple, list)):
        parts = list(verstr)
    else:
        parts = list(p_version.Version(str(verstr)).release)
    # Pad or truncate to exactly 3
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def matches(vers, cmprvers):
    '''
    Check if a version string matches a version comparison string.
    Accepts a PEP 440 string or a legacy int tuple/list for vers.
    '''
    spec = p_specifiers.SpecifierSet(cmprvers)
    return parse(vers) in spec


def reqVersion(valu, reqver,
               exc=s_exc.BadVersion,
               mesg='Provided version does not match required version.'):
    '''
    Require a given version tuple is valid for a given requirements string.

    Args:
        valu: Version to check. May be a PEP 440 string or a legacy int tuple.
        reqver (str): A requirements version string.
        exc (s_exc.SynErr): The synerr class to raise.
        mesg (str): The message to pass in the exception.

    Returns:
        None: If the value is in bounds of minver and maxver.

    Raises:
        s_exc.BadVersion: If a precondition is incorrect or a version value is out of bounds.
    '''
    if valu is None:
        mesg = 'Version value is missing.  ' + mesg
        raise exc(mesg=mesg, valu=valu, reqver=reqver)

    spec = p_specifiers.SpecifierSet(reqver)
    vers = parse(valu)

    if vers not in spec:
        raise exc(mesg=mesg, valu=valu, verstr=str(vers), reqver=reqver)

##############################################################################
# The following are touched during the release process.
# Edit version; commit is set during release.
version = '3.0.0'
commit = ''
