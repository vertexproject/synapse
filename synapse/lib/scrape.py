import string
import asyncio
import logging
import pathlib
import functools
import collections

import idna
import regex
import unicodedata

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.msgpack as s_msgpack

import synapse.lib.crypto.coin as s_coin

ipaddress = s_common.ipaddress

logger = logging.getLogger(__name__)

urilist = set(s_data.get('iana.uris'))
urilist.update([
    'aha',
    'ftps',
    'mysql',
    'postgresql',
    'slack',
    'socks4',
    'socks4a',
    'socks5',
    'socks5h',
    'tcp',
    'unk',
    'webpack'
])

tldlist = list(s_data.get('iana.tlds'))
tldlist.extend([
    'bit',
    'bazar',
    'onion',
])

tldlist.sort(key=lambda x: len(x))
tldlist.reverse()

tldcat = '|'.join(tldlist)
fqdn_re = regex.compile(r'((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))' % tldcat)

idna_disallowed = r'\$+<->\^`|~\u00A8\u00AF\u00B4\u00B8\u02D8-\u02DD\u037A\u0384\u0385\u1FBD\u1FBF-\u1FC1\u1FCD-\u1FCF\u1FDD-\u1FDF\u1FED-\u1FEF\u1FFD\u1FFE\u207A\u207C\u208A\u208C\u2100\u2101\u2105\u2106\u2474-\u24B5\u2A74-\u2A76\u2FF0-\u2FFB\u309B\u309C\u3200-\u321E\u3220-\u3243\u33C2\u33C7\u33D8\uFB29\uFC5E-\uFC63\uFDFA\uFDFB\uFE62\uFE64-\uFE66\uFE69\uFE70\uFE72\uFE74\uFE76\uFE78\uFE7A\uFE7C\uFE7E\uFF04\uFF0B\uFF1C-\uFF1E\uFF3E\uFF40\uFF5C\uFF5E\uFFE3\uFFFC\uFFFD\U0001F100-\U0001F10A\U0001F110-\U0001F129\U000E0100-\U000E01EF'

udots = regex.compile(r'[\u3002\uff0e\uff61]')

# avoid thread safety issues due to uts46_remap() importing uts46data
idna.encode('init', uts46=True)

inverse_prefixs = {
    '[': ']',
    '<': '>',
    '{': '}',
    '(': ')',
}

cve_dashes = ''.join(('-',) + s_chop.unicode_dashes)

def fqdn_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')

    nval = unicodedata.normalize('NFKC', valu)
    nval = regex.sub(udots, '.', nval)
    nval = nval.strip().strip('.')

    try:
        idna.encode(nval, uts46=True).decode('utf8')
    except idna.IDNAError:
        try:
            nval.encode('idna').decode('utf8').lower()
        except UnicodeError:
            return None, {}
    return valu, {}

def inet_server_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')
    port = mnfo.get('port')
    ipv6 = mnfo.get('v6addr')

    port = int(port)
    if port < 1 or port > 2**16 - 1:
        return None, {}

    if ipv6 is not None:
        try:
            addr = ipaddress.IPv6Address(ipv6)
        except ipaddress.AddressValueError:
            return None, {}

    return valu, {}

def ipv6_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')

    try:
        addr = ipaddress.IPv6Address(valu)
    except ipaddress.AddressValueError:
        return None, {}

    return valu, {}

def cve_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')  # type: str
    cbfo = {}

    valu = s_chop.replaceUnicodeDashes(valu)
    return valu, cbfo

# Reference NIST 7695
# Common Platform Enumeration: Naming Specification Version 2.3
# Figure 6-3. ABNF for Formatted String Binding
_cpe23_regex = r'''(?P<valu>cpe:2\.3:[aho\*-]
(?::(([?]+|\*)?([a-z0-9-._]|\\[\\?*!"#$%&\'()+,/:;<=>@\[\]^`{|}~])+([?]+|\*)?|[*-])){5}
:([*-]|(([a-z]{2,3}){1}(-([0-9]{3}|[a-z]{2}))?))
(?::(([?]+|\*)?([a-z0-9-._]|\\[\\?*!"#$%&\'()+,/:;<=>@\[\]^`{|}~])+([?]+|\*)?|[*-])){4})
'''

path_parts_limit = 1024

linux_path_regex = r'''
(?<![\w\d]+)
(?P<valu>
    (?:/[^\x00\n]+)+
)
'''

linux_path_rootdirs = (
    'bin', 'boot', 'cdrom', 'dev', 'etc', 'home',
    'lib', 'lib64', 'lib32', 'libx32', 'media', 'mnt',
    'opt', 'proc', 'root', 'run', 'sbin', 'srv',
    'sys', 'tmp', 'usr', 'var'
)

# https://docs.kernel.org/filesystems/path-lookup.html#the-symlink-stack
linux_path_limit = 4096

def linux_path_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')

    if len(valu) > linux_path_limit:
        return None, {}

    path = pathlib.PurePosixPath(valu)
    parts = path.parts

    if parts[0] != '/':
        return None, {}

    if len(parts) < 2 or len(parts) > path_parts_limit:
        return None, {}

    if parts[1] not in linux_path_rootdirs:
        return None, {}

    return valu, {}

windows_path_regex = r'''
(?P<valu>
    [a-zA-Z]+:\\
    (?:[^<>:"/|\?\*\n\x00]+)+
)
'''

windows_path_reserved = (
    'CON', 'PRN', 'AUX', 'NUL',
    'COM0', 'COM1', 'COM2', 'COM3', 'COM4',
    'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
    'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
)

windows_drive_paths = [f'{letter}:\\' for letter in string.ascii_lowercase]

# https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation
windows_path_limit = 32_767

# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
def windows_path_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')

    if len(valu) > windows_path_limit:
        return None, {}

    path = pathlib.PureWindowsPath(valu)
    parts = path.parts

    if parts[0].lower() not in windows_drive_paths:
        return None, {}

    if len(parts) > path_parts_limit:
        return None, {}

    for part in parts:
        if part in windows_path_reserved:
            return None, {}

        if part.endswith('.'):
            return None, {}

    return valu, {}

ipv4_match = r'(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)'
ipv4_regex = fr'''
(?P<valu>
    (?<!\d|\d\.|[0-9a-f:]:)
    ({ipv4_match})
    (?!\d|\.\d)
)
'''

# Simplified IPv6 regex based on RFC3986, will have false positives and
# requires validating matches.
H16 = r'[0-9a-f]{1,4}'
ipv6_match = fr'''
(?: (?:{H16}:){{1,7}}
    (?:(?:
            :?
            (?:{H16}:){{0,5}}
            (?:{ipv4_match}|{H16})
        ) |
        :
    )
) |
(?: ::
    ({H16}:){{0,6}}
    (?:{ipv4_match}|{H16})
)
'''
ipv6_regex = fr'''
(?P<valu>
    (?<![0-9a-f]:|:[0-9a-f]|::|\d\.)
    ({ipv6_match})
    (?![0-9a-f:]|\.\d)
)
'''

# https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/62e862f4-2a51-452e-8eeb-dc4ff5ee33cc
def unc_path_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')

    try:
        valu = s_chop.uncnorm(valu)
    except s_exc.BadTypeValu:
        return None, {}

    return valu, {}

def url_scheme_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')
    prefix = mnfo.get('prefix')

    cbfo = {}
    if prefix is not None:
        new_valu = valu.rstrip(inverse_prefixs.get(prefix))
        if new_valu != valu:
            valu = new_valu
            cbfo['match'] = valu

    scheme = valu.split('://')[0].lower()
    if scheme not in urilist:
        return None, {}

    return valu, cbfo

# these must be ordered from most specific to least specific to allow first=True to work
scrape_types = [  # type: ignore
    ('file:path', linux_path_regex, {'callback': linux_path_check, 'flags': regex.VERBOSE}),
    ('file:path', windows_path_regex, {'callback': windows_path_check, 'flags': regex.VERBOSE}),
    ('inet:url', r'(?P<prefix>[\\{<\(\[]?)(?P<valu>[a-zA-Z][a-zA-Z0-9]*://(?(?=[,.]+[ \'\"\t\n\r\f\v])|[^ \'\"\t\n\r\f\v])+)',
     {'callback': url_scheme_check}),
    ('inet:url', r'(["\'])?(?P<valu>\\[^\n]+?)(?(1)\1|\s)', {'callback': unc_path_check}),
    ('inet:email', r'(?=(?:[^a-z0-9_.+-]|^)(?P<valu>[a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
    ('inet:server', fr'(?P<valu>(?:(?<!\d|\d\.|[0-9a-f:]:)((?P<addr>{ipv4_match})|\[(?P<v6addr>{ipv6_match})\]):(?P<port>\d{{1,5}})(?!\d|\.\d)))',
     {'callback': inet_server_check, 'flags': regex.VERBOSE}),
    ('inet:ipv4', ipv4_regex, {'flags': regex.VERBOSE}),
    ('inet:ipv6', ipv6_regex, {'callback': ipv6_check, 'flags': regex.VERBOSE}),
    ('inet:fqdn', r'(?=(?:[^\p{L}\p{M}\p{N}\p{S}\u3002\uff0e\uff61_.-]|^|[' + idna_disallowed + '])(?P<valu>(?:((?![' + idna_disallowed + r'])[\p{L}\p{M}\p{N}\p{S}_-]){1,63}[\u3002\uff0e\uff61\.]){1,10}(?:' + tldcat + r'))(?:[^\p{L}\p{M}\p{N}\p{S}\u3002\uff0e\uff61_.-]|[\u3002\uff0e\uff61.]([\p{Z}\p{Cc}]|$)|$|[' + idna_disallowed + r']))', {'callback': fqdn_check}),
    ('hash:md5', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha1', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))', {}),
    ('it:sec:cve', fr'(?:[^a-z0-9]|^)(?P<valu>CVE[{cve_dashes}][0-9]{{4}}[{cve_dashes}][0-9]{{4,}})(?:[^a-z0-9]|$)', {'callback': cve_check}),
    ('it:sec:cwe', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>CWE-[0-9]{1,8})(?:[^A-Za-z0-9]|$))', {}),
    ('it:sec:cpe', _cpe23_regex, {'flags': regex.VERBOSE}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[1][a-zA-HJ-NP-Z0-9]{25,39})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.btc_base58_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>3[a-zA-HJ-NP-Z0-9]{33})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.btc_base58_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>(bc|bcrt|tb)1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{3,71})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.btc_bech32_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>0x[A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.eth_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>(bitcoincash|bchtest):[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{42})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.bch_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[xr][a-zA-HJ-NP-Z0-9]{25,46})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.xrp_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[1a-z][a-zA-HJ-NP-Z0-9]{46,47})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.substrate_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>(DdzFF|Ae2td)[a-zA-HJ-NP-Z0-9]{54,99})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.cardano_byron_check}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>addr1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{53,})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.cardano_shelly_check}),
]

_regexes = collections.defaultdict(list)
for (name, rule, opts) in scrape_types:
    blob = (regex.compile(rule, regex.IGNORECASE | opts.get('flags', 0)), opts)
    _regexes[name].append(blob)

def getForms():
    '''
    Get a list of forms recognized by the scrape APIs.

    Returns:
        list: A list of form values.
    '''
    return sorted(_regexes.keys())

FANGS = {
    'fxp:': 'ftp:',
    'fxps:': 'ftps:',
    'hxxp:': 'http:',
    'hxxps:': 'https:',
    'fxp[s]:': 'ftps:',
    'hxxp[s]:': 'https:'
}

for fang in ('[:]', '[://]', '[:', '(:)'):
    for scheme in ('ftp', 'fxp', 'ftps', 'fxps', 'http', 'hxxp', 'https', 'hxxps'):
        fanged = f'{scheme}{fang}'
        defanged = regex.sub(r'[\[\]\(\)]', '', fanged.replace('x', 't'))
        FANGS[fanged] = defanged

FANGS.update({
    '[.]': '.',
    '.]': '.',
    '[.': '.',
    '[．]': '．',
    '[。]': '。',
    '[｡]': '｡',
    '(.)': '.',
    '(．)': '．',
    '(。)': '。',
    '(｡)': '｡',
    '[dot]': '.',
    '[:]': ':',
    '[at]': '@',
    '[@]': '@',
    '\\.': '.',
})

def genFangRegex(fangs, flags=regex.IGNORECASE):
    # Fangs must be matches of equal or smaller length in order for the
    # contextScrape API to function.
    for src, dst in fangs.items():
        if len(dst) > len(src):
            raise s_exc.BadArg(mesg=f'fang dst[{dst}] must be <= in length to src[{src}]',
                               src=src, dst=dst)
    restr = "|".join(map(regex.escape, fangs.keys()))
    re = regex.compile(restr, flags)
    return re

re_fang = genFangRegex(FANGS)

def refang_text(txt):
    '''
    Remove address de-fanging in text blobs, .e.g. example[.]com to example.com

    Matches to keys in FANGS is case-insensitive, but replacement will always be
    with the lowercase version of the re-fanged value.
    For example, HXXP://FOO.COM will be returned as http://FOO.COM

    Returns:
        (str): Re-fanged text blob
    '''
    return re_fang.sub(lambda match: FANGS[match.group(0).lower()], txt)

def _refang2_func(match: regex.Match, offsets: dict, fangs: dict):
    # This callback exploits the fact that known de-fanging strategies either
    # do in-place transforms, or transforms which increase the target string
    # size. By re-fanging, we are compressing the old string into a new string
    # of potentially a smaller size. We record the offset where any transform
    # affects the contents of the string. This means, downstream, we can avoid
    # have to go back to the source text if there were **no** transforms done.
    # This relies on the prior assertions of refang sizing.
    group = match.group(0)
    ret = fangs[group.lower()]
    rlen = len(ret)
    mlen = len(group)

    span = match.span(0)
    consumed = offsets.get('_consumed', 0)
    offs = span[0] - consumed
    nv = mlen - rlen
    # For offsets, we record the nv + 1 since the now-compressed string
    # has one character represented by mlen - rlen + 1 characters in the
    # original string.
    offsets[offs] = nv + 1
    offsets['_consumed'] = consumed + nv

    return ret

def refang_text2(txt: str, re: regex.Regex =re_fang, fangs: dict =FANGS):
    '''
    Remove address de-fanging in text blobs, .e.g. example[.]com to example.com

    Notes:
        Matches to keys in FANGS is case-insensitive, but replacement will
        always be with the lowercase version of the re-fanged value.
        For example, ``HXXP://FOO.COM`` will be returned as ``http://FOO.COM``

    Args:
        txt (str): The text to re-fang.

    Returns:
        tuple(str, dict): A tuple containing the new text, and a dictionary
        containing offset information where the new text was altered with
        respect to the original text.
    '''
    # The _consumed key is a offset used to track how many chars have been
    # consumed while the cb is called. This is because the match group
    # span values are based on their original string locations, and will not
    # produce values which can be cleanly mapped backwards.
    offsets = {'_consumed': 0}
    cb = functools.partial(_refang2_func, offsets=offsets, fangs=fangs)
    # Start applying FANGs and modifying the info to match the output
    ret = re.sub(cb, txt)

    # Remove the _consumed key since it is no longer useful for later use.
    offsets.pop('_consumed')
    return ret, offsets

def _rewriteRawValu(text: str, offsets: dict, info: dict):

    # Our match offset. This is the match offset value into the refanged text.
    offset = info.get('offset')

    # We need to see if there are values in the offsets which are less than our
    # match offset and increment our base offset by them. This gives us a
    # shift into the original string where we would find the actual offset.
    # This can be represented as a a comprehension but I find that the loop
    # below is easier to read.
    baseoff = 0
    for k, v in offsets.items():
        if k < offset:
            baseoff = baseoff + offsets[k] - 1

    # If our return valu is not a str, then base our text recovery on the
    # original regex matched valu.
    valu = info.get('valu')
    if not isinstance(valu, str):
        valu = info.get('match')

    # Start enumerating each character in our valu, incrementing the end_offset
    # by 1, or the recorded offset difference in offsets dictionary.
    end_offset = offset
    for i, c in enumerate(valu, start=offset):
        end_offset = end_offset + offsets.get(i, 1)

    # Extract a new match and push the match and new offset into info
    match = text[baseoff + offset: baseoff + end_offset]
    info['match'] = match
    info['offset'] = baseoff + offset

def _genMatchList(text: str, regx: regex.Regex, opts: dict):
    return [info for info in _genMatches(text, regx, opts)]

def _genMatches(text: str, regx: regex.Regex, opts: dict):

    cb = opts.get('callback')

    for valu in regx.finditer(text):  # type: regex.Match
        raw_span = valu.span('valu')
        raw_valu = valu.group('valu')

        info = {
            'match': raw_valu,
            'offset': raw_span[0]
        }

        if cb:
            # CB is expected to return a tufo of <new valu, info>
            valu, cbfo = cb(valu)
            if valu is None:
                continue
            # Smash cbfo into our info dict
            info.update(**cbfo)
        else:
            valu = raw_valu

        info['valu'] = valu

        yield info

def genMatches(text: str, regx: regex.Regex, opts: dict):
    '''
    Generate regular expression matches for a blob of text.

    Args:
        text (str): The text to generate matches for.
        regx (regex.Regex): A compiled regex object. The regex must contained a named match group for ``valu``.
        opts (dict): An options dictionary.

    Notes:
        The dictionaries yielded by this function contains the following keys:

            raw_valu
                The raw matching text found in the input text.

            offset
                The offset into the text where the match was found.

            valu
                The resulting value - this may be altered by callbacks.

        The options dictionary can contain a ``callback`` key. This function is expected to take a single argument,
        a regex.Match object, and return a tuple of the new valu and info dictionary. The new valu is used as the
        ``valu`` key in the returned dictionary, and any other information in the info dictionary is pushed into
        the return dictionary as well.

    Yields:
        dict: A dictionary of match results.
    '''
    for match in _genMatches(text, regx, opts):
        yield match

async def genMatchesAsync(text: str, regx: regex.Regex, opts: dict):
    '''
    Generate regular expression matches for a blob of text, using the shared forked process pool.

    Args:
        text (str): The text to generate matches for.
        regx (regex.Regex): A compiled regex object. The regex must contained a named match group for ``valu``.
        opts (dict): An options dictionary.

    Notes:
        The dictionaries yielded by this function contains the following keys:

            raw_valu
                The raw matching text found in the input text.

            offset
                The offset into the text where the match was found.

            valu
                The resulting value - this may be altered by callbacks.

        The options dictionary can contain a ``callback`` key. This function is expected to take a single argument,
        a regex.Match object, and return a tuple of the new valu and info dictionary. The new valu is used as the
        ``valu`` key in the returned dictionary, and any other information in the info dictionary is pushed into
        the return dictionary as well.

    Yields:
        dict: A dictionary of match results.
    '''
    matches = await s_coro.semafork(_genMatchList, text, regx, opts)
    for info in matches:
        yield info

def _contextMatches(scrape_text, text, ruletype, refang, offsets):

        for (regx, opts) in _regexes[ruletype]:

            for info in genMatches(scrape_text, regx, opts):

                info['form'] = ruletype

                if refang and offsets:
                    _rewriteRawValu(text, offsets, info)

                yield info

def _contextScrapeList(text, form=None, refang=True, first=False):
    return [info for info in _contextScrape(text, form=form, refang=refang, first=first)]

def _contextScrape(text, form=None, refang=True, first=False):
    scrape_text = text
    offsets = {}
    if refang:
        scrape_text, offsets = refang_text2(text)

    for ruletype, blobs in _regexes.items():
        if form and form != ruletype:
            continue

        for info in _contextMatches(scrape_text, text, ruletype, refang, offsets):

            yield info

            if first:
                return

def contextScrape(text, form=None, refang=True, first=False):
    '''
    Scrape types from a blob of text and yield info dictionaries.

    Args:
        text (str): Text to scrape.
        form (str): Optional form to scrape. If present, only scrape items which match the provided form.
        refang (bool): Whether to remove de-fanging schemes from text before scraping.
        first (bool): If true, only yield the first item scraped.

    Notes:
        The dictionaries yielded by this function contains the following keys:

            match
                The raw matching text found in the input text.

            offset
                The offset into the text where the match was found.

            valu
                The resulting value.

            form
                The corresponding form for the valu.

    Returns:
        (dict): Yield info dicts of results.
    '''
    for info in _contextScrape(text, form=form, refang=refang, first=first):
        yield info

def scrape(text, ptype=None, refang=True, first=False):
    '''
    Scrape types from a blob of text and return node tuples.

    Args:
        text (str): Text to scrape.
        ptype (str): Optional ptype to scrape. If present, only scrape items which match the provided type.
        refang (bool): Whether to remove de-fanging schemes from text before scraping.
        first (bool): If true, only yield the first item scraped.

    Returns:
        (str, object): Yield tuples of node ndef values.
    '''
    for info in _contextScrape(text, form=ptype, refang=refang, first=first):
        yield info.get('form'), info.get('valu')

async def contextScrapeAsync(text, form=None, refang=True, first=False):
    '''
    Scrape types from a blob of text and yield info dictionaries, using the shared forked process pool.

    Args:
        text (str): Text to scrape.
        form (str): Optional form to scrape. If present, only scrape items which match the provided form.
        refang (bool): Whether to remove de-fanging schemes from text before scraping.
        first (bool): If true, only yield the first item scraped.

    Notes:
        The dictionaries yielded by this function contains the following keys:

            match
                The raw matching text found in the input text.

            offset
                The offset into the text where the match was found.

            valu
                The resulting value.

            form
                The corresponding form for the valu.

    Returns:
        (dict): Yield info dicts of results.
    '''
    matches = await s_coro.semafork(_contextScrapeList, text, form=form, refang=refang, first=first)
    for info in matches:
        yield info

async def scrapeAsync(text, ptype=None, refang=True, first=False):
    '''
    Scrape types from a blob of text and return node tuples, using the shared forked process pool.

    Args:
        text (str): Text to scrape.
        ptype (str): Optional ptype to scrape. If present, only scrape items which match the provided type.
        refang (bool): Whether to remove de-fanging schemes from text before scraping.
        first (bool): If true, only yield the first item scraped.

    Returns:
        (str, object): Yield tuples of node ndef values.
    '''
    matches = await s_coro.semafork(_contextScrapeList, text, form=ptype, refang=refang, first=first)
    for info in matches:
        yield info.get('form'), info.get('valu')
