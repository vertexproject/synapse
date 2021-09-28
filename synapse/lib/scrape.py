import regex

import synapse.data as s_data

tldlist = list(s_data.get('iana.tlds'))

tldlist.sort(key=lambda x: len(x))
tldlist.reverse()

tldcat = '|'.join(tldlist)
fqdn_re = regex.compile(r'((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))' % tldcat)

FANGS = {
    'hxxp:': 'http:',
    'hxxps:': 'https:',
    'hxxp[:]': 'http:',
    'hxxps[:]': 'https:',
    'hxxp(:)': 'http:',
    'hxxps(:)': 'https:',
    '[.]': '.',
    '(.)': '.',
    '[:]': ':',
    'fxp': 'ftp',
    'fxps': 'ftps',
    '[at]': '@',
    '[@]': '@',
}

inverse_prefixs = {
    '[': ']',
    '<': '>',
    '{': '}',
    '(': ')',
}


re_fang = regex.compile("|".join(map(regex.escape, FANGS.keys())), regex.IGNORECASE)

# these must be ordered from most specific to least specific to allow first=True to work
scrape_types = [  # type: ignore
    ('inet:url', r'(?P<prefix>[\\{<\(\[]?)(?P<valu>[a-zA-Z][a-zA-Z0-9]*://(?(?=[,.]+[ \'\"\t\n\r\f\v])|[^ \'\"\t\n\r\f\v])+)', {}),
    ('inet:email', r'(?=(?:[^a-z0-9_.+-]|^)(?P<valu>[a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
    ('inet:server', r'(?P<valu>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5})', {}),
    ('inet:ipv4', r'(?P<valu>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))', {}),
    ('inet:fqdn', r'(?=(?:[^a-z0-9_.-]|^)(?P<valu>(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
    ('hash:md5', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha1', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))', {}),
]

regexes = {name: regex.compile(rule, regex.IGNORECASE) for (name, rule, opts) in scrape_types}

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

def scrape(text, ptype=None, refang=True, first=False):
    '''
    Scrape types from a blob of text and return node tuples.

    Args:
        text (str): Text to scrape.
        ptype (str): Optional ptype to scrape. If present, only scrape rules which match the provided type.
        refang (bool): Whether to remove de-fanging schemes from text before scraping.

    Returns:
        (str, str): Yield tuples of type, valu strings.
    '''

    if refang:
        text = refang_text(text)

    for ruletype, _, _ in scrape_types:
        if ptype and ptype != ruletype:
            continue

        regx = regexes.get(ruletype)
        for valu in regx.finditer(text):  # type: regex.Match
            mnfo = valu.groupdict()
            valu = mnfo.get('valu')
            prefix = mnfo.get('prefix')
            if prefix is not None:
                valu = valu.rstrip(inverse_prefixs.get(prefix))
            yield (ruletype, valu)
            if first:
                return
