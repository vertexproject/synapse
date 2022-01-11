import logging
import functools
import collections

import idna
import regex
import unicodedata

import synapse.data as s_data

import synapse.lib.crypto.coin as s_coin


logger = logging.getLogger(__name__)

tldlist = list(s_data.get('iana.tlds'))
tldlist.extend([
    'bit',
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

FANGS = {
    'hxxp:': 'http:',
    'hxxps:': 'https:',
    'hxxp[:]': 'http:',
    'hxxps[:]': 'https:',
    'hxxp(:)': 'http:',
    'hxxps(:)': 'https:',
    '[.]': '.',
    '[．]': '．',
    '[。]': '。',
    '[｡]': '｡',
    '(.)': '.',
    '(．)': '．',
    '(。)': '。',
    '(｡)': '｡',
    '[:]': ':',
    'fxp': 'ftp',
    'fxps': 'ftps',
    '[at]': '@',
    '[@]': '@',
}

# FANGs must be compression matches
for src, dst in FANGS.items():
    assert len(dst) <= len(src)

inverse_prefixs = {
    '[': ']',
    '<': '>',
    '{': '}',
    '(': ')',
}


def fqdn_prefix_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')
    prefix = mnfo.get('prefix')
    cbfo = {}
    if prefix is not None:
        new_valu = valu.rstrip(inverse_prefixs.get(prefix))
        if new_valu != valu:
            valu = new_valu
            cbfo['raw_valu'] = valu
    return valu, cbfo

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

re_fang = regex.compile("|".join(map(regex.escape, FANGS.keys())), regex.IGNORECASE)

# these must be ordered from most specific to least specific to allow first=True to work
scrape_types = [  # type: ignore
    ('inet:url', r'(?P<prefix>[\\{<\(\[]?)(?P<valu>[a-zA-Z][a-zA-Z0-9]*://(?(?=[,.]+[ \'\"\t\n\r\f\v])|[^ \'\"\t\n\r\f\v])+)',
     {'callback': fqdn_prefix_check}),
    ('inet:email', r'(?=(?:[^a-z0-9_.+-]|^)(?P<valu>[a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
    ('inet:server', r'(?P<valu>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5})', {}),
    ('inet:ipv4', r'(?P<valu>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))', {}),
    ('inet:fqdn', r'(?=(?:[^\p{L}\p{M}\p{N}\p{S}\u3002\uff0e\uff61_.-]|^|[' + idna_disallowed + '])(?P<valu>(?:((?![' + idna_disallowed + r'])[\p{L}\p{M}\p{N}\p{S}_-]){1,63}[\u3002\uff0e\uff61\.]){1,10}(?:' + tldcat + r'))(?:[^\p{L}\p{M}\p{N}\p{S}\u3002\uff0e\uff61_.-]|[\u3002\uff0e\uff61.]([\p{Z}\p{Cc}]|$)|$|[' + idna_disallowed + r']))', {'callback': fqdn_check}),
    ('hash:md5', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha1', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))', {}),
    ('it:sec:cve', r'(?:[^a-z0-9]|^)(?P<valu>CVE-[0-9]{4}-[0-9]{4,})(?:[^a-z0-9]|$)', {}),
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
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>addr1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{53})(?:[^A-Za-z0-9]|$))',
     {'callback': s_coin.cardano_shelly_check}),
]

_regexes = collections.defaultdict(list)
for (name, rule, opts) in scrape_types:
    blob = (regex.compile(rule, regex.IGNORECASE), opts)
    _regexes[name].append(blob)

def getPtypes():
    '''
    Get a list of ptypes recognized by the scrape APIs.

    Returns:
        list: A list of ptype values.
    '''
    return sorted(_regexes.keys())

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

def _refang_func(match: regex.Match, offsets: dict):
    group = match.group(0)
    ret = FANGS[group.lower()]
    rlen = len(ret)
    mlen = len(group)
    if rlen != mlen:
        # WE have a remap to handle
        span = match.span(0)
        consumed = offsets['_consumed']
        offs = span[0] - consumed
        nv = mlen - rlen
        offsets[offs] = nv + 1
        offsets['_consumed'] = consumed + nv

    return ret

def refang_text2(txt: str):
    # The _consumed key is a offset used to track how many chars have been
    # consumed while the cb is called. This is because the match group
    # span values are based on their original string locations, and will not
    # produce values which can be cleanly mapped backwards.
    offsets = {'_consumed': 0}
    cb = functools.partial(_refang_func, offsets=offsets)
    # Start applying FANGs and modifying the info to match the output
    ret = re_fang.sub(cb, txt)

    # Remove the _consumed key since it is no longer useful for later use.
    offsets.pop('_consumed')
    return ret, offsets

def _rewriteRawValu(text, offsets, info):

    # Our match offset
    offset = info.get('offset')
    baseoff = 0
    # We need to see if there are values in the offsets which are less
    # than our match offset and increment our actual offset by theem.
    keys = sorted(list(offsets.keys()))
    for k in keys:
        if k < offset:
            baseoff = baseoff + offsets[k] - 1

    eoffs = offset

    # If our valu is not a str, then base our text recovery
    # on the regex reported valu.
    valu = info.get('valu')
    if not isinstance(valu, str):
        valu = info.get('raw_valu')

    for i, c in enumerate(valu, start=offset):
        v = offsets.get(i, 1)
        # print(f'{i=} {v=} {eoffs+v=} {text[offset: eoffs + v]}')
        eoffs = eoffs + v
    raw_valu = text[baseoff + offset: baseoff + eoffs]
    info['raw_valu'] = raw_valu
    info['offset'] = baseoff + offset

def genMatches(text: str, regx: regex.Regex, opts: dict):
    '''
    Generate regular expression matches for a blob of text.

    Args:
        text (str): The text to generate matches for.
        regx (regex.Regex): A compiled regex object. The regex must contained a named match for ``valu``.
        opts (dict): XXX

    Yields:
        dict: A dictionary of match results.
    '''
    cb = opts.get('callback')

    for valu in regx.finditer(text):  # type: regex.Match
        raw_span = valu.span('valu')
        raw_valu = valu.group('valu')

        info = {
            'raw_valu': raw_valu,
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

def contextScrape(text, ptype=None, refang=True, first=False):

    scrape_text = text
    offsets = {}
    if refang:
        scrape_text, offsets = refang_text2(text)

    for ruletype, blobs in _regexes.items():
        if ptype and ptype != ruletype:
            continue

        for (regx, opts) in blobs:

            for info in genMatches(scrape_text, regx, opts):

                info['form'] = ruletype

                if refang:
                    _rewriteRawValu(text, offsets, info)

                yield info

                if first:
                    return

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

    for info in contextScrape(text, ptype=ptype, refang=refang, first=first):
        yield info.get('form'), info.get('valu')
