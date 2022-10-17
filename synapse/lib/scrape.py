import logging
import functools
import collections

import idna
import regex
import unicodedata

import synapse.exc as s_exc
import synapse.data as s_data

import synapse.lib.chop as s_chop

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

inverse_prefixs = {
    '[': ']',
    '<': '>',
    '{': '}',
    '(': ')',
}

cve_dashes = ''.join(('-',) + s_chop.unicode_dashes)

def fqdn_prefix_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')
    prefix = mnfo.get('prefix')
    cbfo = {}
    if prefix is not None:
        new_valu = valu.rstrip(inverse_prefixs.get(prefix))
        if new_valu != valu:
            valu = new_valu
            cbfo['match'] = valu
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

def cve_check(match: regex.Match):
    mnfo = match.groupdict()
    valu = mnfo.get('valu')  # type: str
    cbfo = {}

    valu = s_chop.replaceUnicodeDashes(valu)
    return valu, cbfo

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
    ('it:sec:cve', fr'(?:[^a-z0-9]|^)(?P<valu>CVE[{cve_dashes}][0-9]{{4}}[{cve_dashes}][0-9]{{4,}})(?:[^a-z0-9]|$)', {'callback': cve_check}),
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

def getForms():
    '''
    Get a list of forms recognized by the scrape APIs.

    Returns:
        list: A list of form values.
    '''
    return sorted(_regexes.keys())

FANGS = {
    'hxxp:': 'http:',
    'hxxps:': 'https:',
    'http[:]': 'http:',
    'hxxp[:]': 'http:',
    'https[:]': 'https:',
    'hxxps[:]': 'https:',
    'http[://]': 'http://',
    'hxxp[://]': 'http://',
    'https[://]': 'https://',
    'hxxps[://]': 'https://',
    'http(:)': 'http:',
    'hxxp(:)': 'http:',
    'https(:)': 'https:',
    'hxxps(:)': 'https:',
    'hxxp[s]:': 'https:',
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
    '\\.': '.',
}

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
    scrape_text = text
    offsets = {}
    if refang:
        scrape_text, offsets = refang_text2(text)

    for ruletype, blobs in _regexes.items():
        if form and form != ruletype:
            continue

        for (regx, opts) in blobs:

            for info in genMatches(scrape_text, regx, opts):

                info['form'] = ruletype

                if refang and offsets:
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

    for info in contextScrape(text, form=ptype, refang=refang, first=first):
        yield info.get('form'), info.get('valu')
