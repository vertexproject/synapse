import json
import regex

import synapse.data as s_data
import synapse.common as s_common

tldlist = list(s_data.get('iana.tlds'))

tldlist.sort(key=lambda x: len(x))
tldlist.reverse()

tldcat = '|'.join(tldlist)
fqdn_re = regex.compile(r'((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))' % tldcat)

scrape_types = [
    ('hash:md5', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha1', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))', {}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))', {}),

    ('inet:url', r'\w+://[^ \'"\t\n\r\f\v]+', {}),
    ('inet:ipv4', r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', {}),
    ('inet:server', r'((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5})', {}),
    ('inet:fqdn', r'(?:[^a-z0-9_.-]|^)((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|$)' % tldcat, {}),
    ('inet:email', r'(?:[^a-z0-9_.+-]|^)([a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|$)' % tldcat, {}),
]

regexes = {name: regex.compile(rule, regex.IGNORECASE) for (name, rule, opts) in scrape_types}

def scrape(text):
    '''
    Scrape types from a blob of text and return node tuples.
    '''
    for ptype, rule, info in scrape_types:
        regx = regexes.get(ptype)
        for valu in regx.findall(text):
            yield (ptype, valu)
