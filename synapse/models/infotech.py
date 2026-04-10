import copy
import string
import logging

import regex

import synapse.exc as s_exc
import synapse.lib.types as s_types
import synapse.lib.scrape as s_scrape
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

# This is the regular expression pattern for CPE 2.2. It's kind of a hybrid
# between compatible binding and preferred binding. Differences are here:
# - Use only the list of percent encoded values specified by preferred binding.
#   This is to ensure it converts properly to CPE 2.3.
# - Add tilde (~) to the UNRESERVED list which removes the need to specify the
#   PACKED encoding specifically.
ALPHA = '[A-Za-z]'
DIGIT = '[0-9]'
UNRESERVED = r'[A-Za-z0-9\-\.\_~]'
SPEC1 = '%01'
SPEC2 = '%02'
# This is defined in the ABNF but not actually referenced
# SPECIAL = f'(?:{SPEC1}|{SPEC2})'
SPEC_CHRS = f'(?:{SPEC1}+|{SPEC2})'
PCT_ENCODED = '%(?:21|22|23|24|25|26|27|28|28|29|2a|2b|2c|2f|3a|3b|3c|3d|3e|3f|40|5b|5c|5d|5e|60|7b|7c|7d|7e)'
STR_WO_SPECIAL = f'(?:{UNRESERVED}|{PCT_ENCODED})*'
STR_W_SPECIAL = f'{SPEC_CHRS}? (?:{UNRESERVED}|{PCT_ENCODED})+ {SPEC_CHRS}?'
STRING = f'(?:{STR_W_SPECIAL}|{STR_WO_SPECIAL})'
REGION = f'(?:{ALPHA}{{2}}|{DIGIT}{{3}})'
LANGTAG = rf'(?:{ALPHA}{{2,3}}(?:\-{REGION})?)'
PART = '[hoa]?'
VENDOR = STRING
PRODUCT = STRING
VERSION = STRING
UPDATE = STRING
EDITION = STRING
LANG = f'{LANGTAG}?'
COMPONENT_LIST = f'''
    (?:
        {PART}:{VENDOR}:{PRODUCT}:{VERSION}:{UPDATE}:{EDITION}:{LANG} |
        {PART}:{VENDOR}:{PRODUCT}:{VERSION}:{UPDATE}:{EDITION} |
        {PART}:{VENDOR}:{PRODUCT}:{VERSION}:{UPDATE} |
        {PART}:{VENDOR}:{PRODUCT}:{VERSION} |
        {PART}:{VENDOR}:{PRODUCT} |
        {PART}:{VENDOR} |
        {PART}
    )
'''

cpe22_regex = regex.compile(f'cpe:/{COMPONENT_LIST}', regex.VERBOSE | regex.IGNORECASE)
cpe23_regex = regex.compile(s_scrape._cpe23_regex, regex.VERBOSE | regex.IGNORECASE)

def isValidCpe22(text):
    rgx = cpe22_regex.fullmatch(text)
    return rgx is not None

def isValidCpe23(text):
    rgx = cpe23_regex.fullmatch(text)
    return rgx is not None

def cpesplit(text):
    part = ''
    parts = []

    genr = iter(text)
    try:
        while True:

            c = next(genr)

            if c == '\\':
                c += next(genr)

            if c == ':':
                parts.append(part)
                part = ''
                continue

            part += c

    except StopIteration:
        parts.append(part)

    return [part.strip() for part in parts]

# Formatted String Binding characters that need to be escaped
FSB_ESCAPE_CHARS = [
    '!', '"', '#', '$', '%', '&', "'", '(', ')',
    '+', ',', '/', ':', ';', '<', '=', '>', '@',
    '[', ']', '^', '`', '{', '|', '}', '~',
    '\\', '?', '*'
]

FSB_VALID_CHARS = ['-', '.', '_']
FSB_VALID_CHARS.extend(string.ascii_letters)
FSB_VALID_CHARS.extend(string.digits)
FSB_VALID_CHARS.extend(FSB_ESCAPE_CHARS)

def fsb_escape(text):
    ret = ''
    if text in ('*', '-'):
        return text

    # Check validity of text first
    if (invalid := [char for char in text if char not in FSB_VALID_CHARS]):
        badchars = ', '.join(invalid)
        mesg = f'Invalid CPE 2.3 character(s) ({badchars}) detected.'
        raise s_exc.BadTypeValu(mesg=mesg, valu=text)

    textlen = len(text)

    for idx, char in enumerate(text):
        if char not in FSB_ESCAPE_CHARS:
            ret += char
            continue

        escchar = f'\\{char}'

        # The only character in the string
        if idx == 0 and idx == textlen - 1:
            ret += escchar
            continue

        # Handle the backslash as a special case
        if char == '\\':
            if idx == 0:
                # Its the first character and escaping another special character
                if text[idx + 1] in FSB_ESCAPE_CHARS:
                    ret += char
                else:
                    ret += escchar

                continue

            if idx == textlen - 1:
                # Its the last character and being escaped
                if text[idx - 1] == '\\':
                    ret += char
                else:
                    ret += escchar

                continue

            # The backslash is in the middle somewhere

            # It's already escaped or it's escaping a special char
            if text[idx - 1] == '\\' or text[idx + 1] in FSB_ESCAPE_CHARS:
                ret += char
                continue

            # Lone backslash, escape it and move on
            ret += escchar
            continue

        # First char, no look behind
        if idx == 0:
            # Escape the first character and go around
            ret += escchar
            continue

        escaped = text[idx - 1] == '\\'

        if not escaped:
            ret += escchar
            continue

        ret += char

    return ret

def fsb_unescape(text):
    ret = ''
    textlen = len(text)

    for idx, char in enumerate(text):
        # The last character so we can't look ahead
        if idx == textlen - 1:
            ret += char
            continue

        if char == '\\' and text[idx + 1] in FSB_ESCAPE_CHARS:
            continue

        ret += char

    return ret

# URI Binding characters that can be encoded in percent format
URI_PERCENT_CHARS = [
    # Do the percent first so we don't double encode by accident
    ('%25', '%'),
    ('%21', '!'), ('%22', '"'), ('%23', '#'), ('%24', '$'), ('%26', '&'), ('%27', "'"),
    ('%28', '('), ('%29', ')'), ('%2a', '*'), ('%2b', '+'), ('%2c', ','), ('%2f', '/'), ('%3a', ':'),
    ('%3b', ';'), ('%3c', '<'), ('%3d', '='), ('%3e', '>'), ('%3f', '?'), ('%40', '@'), ('%5b', '['),
    ('%5c', '\\'), ('%5d', ']'), ('%5e', '^'), ('%60', '`'), ('%7b', '{'), ('%7c', '|'), ('%7d', '}'),
    ('%7e', '~'),
]

def uri_quote(text):
    for (pct, char) in URI_PERCENT_CHARS:
        text = text.replace(char, pct)
    return text

def uri_unquote(text):
    # iterate backwards so we do the % last to avoid double unquoting
    # example: "%2521" would turn into "%21" which would then replace into "!"
    for (pct, char) in URI_PERCENT_CHARS[::-1]:
        text = text.replace(pct, char)
    return text

UNSPECIFIED = ('', '*')
def uri_pack(edition, sw_edition, target_sw, target_hw, other):
    # If the four extended attributes are unspecified, only return the edition value
    if (sw_edition in UNSPECIFIED and target_sw in UNSPECIFIED and target_hw in UNSPECIFIED and other in UNSPECIFIED):
        return edition

    ret = [edition, '', '', '', '']

    if sw_edition not in UNSPECIFIED:
        ret[1] = sw_edition

    if target_sw not in UNSPECIFIED:
        ret[2] = target_sw

    if target_hw not in UNSPECIFIED:
        ret[3] = target_hw

    if other not in UNSPECIFIED:
        ret[4] = other

    return '~' + '~'.join(ret)

def uri_unpack(edition):
    if edition.startswith('~') and edition.count('~') == 5:
        return edition[1:].split('~', 5)
    return None

class Cpe22Str(s_types.Str):
    '''
    CPE 2.2 Formatted String
    https://cpe.mitre.org/files/cpe-specification_2.2.pdf
    '''
    def postTypeInit(self):
        self.opts['lower'] = True
        s_types.Str.postTypeInit(self)
        self.setNormFunc(list, self._normPyList)
        self.setNormFunc(tuple, self._normPyList)

    async def _normPyStr(self, valu, view=None):

        text = valu.lower()

        if text.startswith('cpe:/'):

            if not isValidCpe22(text):
                mesg = 'CPE 2.2 string appears to be invalid.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu)

            parts = chopCpe22(text)
        elif text.startswith('cpe:2.3:'):

            if not isValidCpe23(text):
                mesg = 'CPE 2.3 string appears to be invalid.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu)

            parts = cpesplit(text[8:])
        else:
            mesg = 'CPE 2.2 string is expected to start with "cpe:/"'
            raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

        v2_2 = zipCpe22(parts)

        if not isValidCpe22(v2_2): # pragma: no cover
            mesg = 'CPE 2.2 string appears to be invalid.'
            raise s_exc.BadTypeValu(mesg=mesg, valu=valu)

        return v2_2, {}

    async def _normPyList(self, parts, view=None):
        return zipCpe22(parts), {}

def zipCpe22(parts):
    parts = list(parts)
    while parts and parts[-1] in ('', '*'):
        parts.pop()
    text = ':'.join(parts[:7])
    return f'cpe:/{text}'

def chopCpe22(text):
    '''
    CPE 2.2 Formatted String
    https://cpe.mitre.org/files/cpe-specification_2.2.pdf
    '''
    if not text.startswith('cpe:/'): # pragma: no cover
        mesg = 'CPE 2.2 string is expected to start with "cpe:/"'
        raise s_exc.BadTypeValu(valu=text, mesg=mesg)

    _, text = text.split(':/', 1)
    parts = cpesplit(text)
    if len(parts) > 7:
        mesg = f'CPE 2.2 string has {len(parts)} parts, expected <= 7.'
        raise s_exc.BadTypeValu(valu=text, mesg=mesg)

    return parts

PART_IDX_PART = 0
PART_IDX_VENDOR = 1
PART_IDX_PRODUCT = 2
PART_IDX_VERSION = 3
PART_IDX_UPDATE = 4
PART_IDX_EDITION = 5
PART_IDX_LANG = 6
PART_IDX_SW_EDITION = 7
PART_IDX_TARGET_SW = 8
PART_IDX_TARGET_HW = 9
PART_IDX_OTHER = 10

class Cpe23Str(s_types.Str):
    '''
    CPE 2.3 Formatted String

    ::

        https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf

        (Section 6.2)

        cpe:2.3: part : vendor : product : version : update : edition :
            language : sw_edition : target_sw : target_hw : other

        * = "any"
        - = N/A
    '''
    def postTypeInit(self):
        self.opts['lower'] = True
        s_types.Str.postTypeInit(self)

        self.cpe22 = self.modl.type('it:sec:cpe:v2_2')
        self.strtype = self.modl.type('str').clone({'lower': True})
        self.metatype = self.modl.type('meta:name')

    async def _normPyStr(self, valu, view=None):
        text = valu.lower()
        if text.startswith('cpe:2.3:'):

            # Validate the CPE 2.3 string immediately
            if not isValidCpe23(text):
                mesg = 'CPE 2.3 string appears to be invalid.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu)

            parts = cpesplit(text[8:])
            if len(parts) > 11:
                mesg = f'CPE 2.3 string has {len(parts)} fields, expected up to 11.'
                raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

            extsize = 11 - len(parts)
            parts.extend(['*' for _ in range(extsize)])

            v2_3 = 'cpe:2.3:' + ':'.join(parts)

            v2_2 = copy.copy(parts)
            for idx, part in enumerate(v2_2):
                if part == '*':
                    v2_2[idx] = ''
                    continue

                if idx in (PART_IDX_PART, PART_IDX_LANG) and part == '-':
                    v2_2[idx] = ''
                    continue

                part = fsb_unescape(part)
                v2_2[idx] = uri_quote(part)

            v2_2[PART_IDX_EDITION] = uri_pack(
                v2_2[PART_IDX_EDITION],
                v2_2[PART_IDX_SW_EDITION],
                v2_2[PART_IDX_TARGET_SW],
                v2_2[PART_IDX_TARGET_HW],
                v2_2[PART_IDX_OTHER]
            )

            v2_2 = zipCpe22(v2_2[:7])

            # Now validate the downconvert
            if not isValidCpe22(v2_2): # pragma: no cover
                mesg = 'Invalid CPE 2.3 to CPE 2.2 conversion.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu, v2_2=v2_2)

            parts = [fsb_unescape(k) for k in parts]

        elif text.startswith('cpe:/'):

            # Validate the CPE 2.2 string immediately
            if not isValidCpe22(text):
                mesg = 'CPE 2.2 string appears to be invalid.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu)

            v2_2 = text
            # automatically normalize CPE 2.2 format to CPE 2.3
            parts = chopCpe22(text)

            # Account for blank fields
            for idx, part in enumerate(parts):
                if not part:
                    parts[idx] = '*'

            extsize = 11 - len(parts)
            parts.extend(['*' for _ in range(extsize)])

            # URI bindings can pack extended attributes into the
            # edition field, handle that here.
            unpacked = uri_unpack(parts[PART_IDX_EDITION])
            if unpacked:
                (edition, sw_edition, target_sw, target_hw, other) = unpacked

                if edition:
                    parts[PART_IDX_EDITION] = edition
                else:
                    parts[PART_IDX_EDITION] = '*'

                if sw_edition:
                    parts[PART_IDX_SW_EDITION] = sw_edition

                if target_sw:
                    parts[PART_IDX_TARGET_SW] = target_sw

                if target_hw:
                    parts[PART_IDX_TARGET_HW] = target_hw

                if other:
                    parts[PART_IDX_OTHER] = other

            parts = [uri_unquote(part) for part in parts]

            # This feels a little uninuitive to escape parts for "escaped" and
            # unescape parts for "parts" but values in parts could be incorrectly
            # escaped or incorrectly unescaped so just do both.
            escaped = [fsb_escape(part) for part in parts]
            parts = [fsb_unescape(part) for part in parts]

            v2_3 = 'cpe:2.3:' + ':'.join(escaped)

            # Now validate the upconvert
            if not isValidCpe23(v2_3): # pragma: no cover
                mesg = 'Invalid CPE 2.2 to CPE 2.3 conversion.'
                raise s_exc.BadTypeValu(mesg=mesg, valu=valu, v2_3=v2_3)

        else:
            mesg = 'CPE 2.3 string is expected to start with "cpe:2.3:"'
            raise s_exc.BadTypeValu(valu=valu, mesg=mesg)

        styp = self.strtype.typehash

        subs = {
            'part': (styp, parts[PART_IDX_PART], {}),
            'vendor': (self.metatype.typehash, parts[PART_IDX_VENDOR], {}),
            'product': (styp, parts[PART_IDX_PRODUCT], {}),
            'version': (styp, parts[PART_IDX_VERSION], {}),
            'update': (styp, parts[PART_IDX_UPDATE], {}),
            'edition': (styp, parts[PART_IDX_EDITION], {}),
            'language': (styp, parts[PART_IDX_LANG], {}),
            'sw_edition': (styp, parts[PART_IDX_SW_EDITION], {}),
            'target_sw': (styp, parts[PART_IDX_TARGET_SW], {}),
            'target_hw': (styp, parts[PART_IDX_TARGET_HW], {}),
            'other': (styp, parts[PART_IDX_OTHER], {}),
            'v2_2': (self.cpe22.typehash, v2_2, {}),
        }

        return v2_3, {'subs': subs}

class SemVer(s_types.Int):
    '''
    Provides support for parsing a semantic version string into its component
    parts. This normalizes a version string into an integer to allow version
    ordering.  Prerelease information is disregarded for integer comparison
    purposes, as we cannot map an arbitrary pre-release version into a integer
    value

    Major, minor and patch levels are represented as integers, with a max
    width of 20 bits.  The comparable integer value representing the semver
    is the bitwise concatenation of the major, minor and patch levels.

    Prerelease and build information will be parsed out and available as
    strings if that information is present.
    '''
    def postTypeInit(self):
        s_types.Int.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    async def _normPyStr(self, valu, view=None):
        valu = valu.strip()
        if not valu:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='No text left after stripping whitespace')

        info = s_version.parseSemver(valu)
        if info is None:
            info = s_version.parseVersionParts(valu)
            if info is None:
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg='Unable to parse string as a semver.')

        valu = s_version.packVersion(info.get('major'), info.get('minor', 0), info.get('patch', 0))

        return valu, {}

    async def _normPyInt(self, valu, view=None):
        if valu < 0:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Cannot norm a negative integer as a semver.')
        if valu > s_version.mask60:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Cannot norm a integer larger than 1152921504606846975 as a semver.')
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.packVersion(major, minor, patch)
        return valu, {}

    def repr(self, valu):
        major, minor, patch = s_version.unpackVersion(valu)
        valu = s_version.fmtVersion(major, minor, patch)
        return valu

class ItVersion(s_types.Str):

    def postTypeInit(self):

        s_types.Str.postTypeInit(self)
        self.semver = self.modl.type('it:semver')

        self.virtindx |= {
            'semver': 'semver',
        }

        self.virts |= {
            'semver': (self.semver, self._getSemVer),
        }

    def _getSemVer(self, valu):

        if (virts := valu[2]) is None:
            return None

        if (valu := virts.get('semver')) is None: # pragma: no cover
            return None

        return valu[0]

    async def _normPyStr(self, valu, view=None):

        norm, info = await s_types.Str._normPyStr(self, valu)

        try:
            semv, semvinfo = await self.semver.norm(norm)
            subs = info.setdefault('subs', {})
            virts = info.setdefault('virts', {})
            subs['semver'] = (self.semver.typehash, semv, semvinfo)
            virts['semver'] = (semv, self.semver.stortype)
        except s_exc.BadTypeValu:
            # It's ok for a version to not be semver compatible.
            pass

        return norm, info
