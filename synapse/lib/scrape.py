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

re_fang = regex.compile("|".join(map(regex.escape, FANGS.keys())), regex.IGNORECASE)

scrape_types = [  # type: ignore
    ('hash:md5', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha1', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))', {}),

    ('inet:url', r'[a-zA-Z][a-zA-Z0-9]*://[^ \'\"\t\n\r\f\v]+', {}),
    ('inet:ipv4', r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', {}),
    ('inet:server', r'((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5})', {}),
    ('inet:fqdn', r'(?=(?:[^a-z0-9_.-]|^)((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
    ('inet:email', r'(?=(?:[^a-z0-9_.+-]|^)([a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|[.\s]|$))' % tldcat, {}),
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

def scrape(text, ptype=None, refang=True):
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
        for valu in regx.findall(text):
            yield (ruletype, valu)
