import logging
import collections

import regex
import base58
import _pysha3  # do not import the sha3 library directly.
import bitcoin
import bitcoin.bech32 as bitcoin_b32


import synapse.data as s_data
import synapse.common as s_common

logger = logging.getLogger(__name__)

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


def btc_bech32(text):
    prefix, _ = text.split('1', 1)
    prefix = prefix.lower()
    if prefix == 'bc':
        bitcoin.SelectParams('mainnet')
    elif prefix == 'tb':
        bitcoin.SelectParams('testnet')
    elif prefix == 'bcrt':
        bitcoin.SelectParams('regtest')
    else:  # pragma: no cover
        raise ValueError(f'Unknown prefix {text}')
    try:
        _ = bitcoin_b32.CBech32Data(text)
    except bitcoin_b32.Bech32Error:
        return None
    # The proper form of a bech32 address is lowercased. We do not want to verify
    # a mixed case form, so lowercase it prior to returning.
    return ('btc', text.lower())

def btc_base58(text):
    # FIXME - Replace this with base58 decoding from bitcoin library
    try:
        base58.b58decode_check(text)
    except ValueError:
        return None
    return ('btc', text)

def ether_eip55(body: str):
    # From EIP-55 reference implementation
    addr_byts = s_common.uhex(body)
    hex_addr = addr_byts.hex()
    checksummed_buffer = ""
    hashed_address = _pysha3.keccak_256(hex_addr.encode()).hexdigest()

    for nibble_index, character in enumerate(hex_addr):
        if character in "0123456789":
            # We can't upper-case the decimal digits
            checksummed_buffer += character
        elif character in "abcdef":
            # Check if the corresponding hex digit (nibble) in the hash is 8 or higher
            hashed_address_nibble = int(hashed_address[nibble_index], 16)
            if hashed_address_nibble > 7:
                checksummed_buffer += character.upper()
            else:
                checksummed_buffer += character
        else:
            return None

    return "0x" + checksummed_buffer

def eth_check(text: str):
    prefix, body = text.split('x')  # type: str, str
    # Checksum if we're mixed case or not
    if not body.isupper() and not body.islower():

        logger.info(f'Checksumming {text=}')

        ret = ether_eip55(body)
        if ret is None:
            return None

        if ret != text:
            return None

        return ('eth', text)

    return ('eth', text.lower())


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
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>[1][a-zA-HJ-NP-Z0-9]{25,39})(?:[^A-Za-z0-9]|$))',
     {'callback': btc_base58}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>3[a-zA-HJ-NP-Z0-9]{33})(?:[^A-Za-z0-9]|$))',
     {'callback': btc_base58}),
    ('crypto:currency:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>(bc|bcrt|tb)1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{3,71})(?:[^A-Za-z0-9]|$))',
     {'callback': btc_bech32}),
    # The following ethererum address can look like a SHA256 but must have
    # a leading 0x and may require checksum validation for mixed case.
    ('crypto:current:address', r'(?=(?:[^A-Za-z0-9]|^)(?P<valu>0x[A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))',
     {'callback': eth_check})
]

_regexes = collections.defaultdict(list)
for (name, rule, opts) in scrape_types:
    blob = (regex.compile(rule, regex.IGNORECASE), opts)
    _regexes[name].append(blob)


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

    for ruletype, blobs in _regexes.items():
        if ptype and ptype != ruletype:
            continue

        for (regx, opts) in blobs:
            cb = opts.get('callback')

            for valu in regx.finditer(text):  # type: regex.Match
                mnfo = valu.groupdict()
                valu = mnfo.get('valu')
                prefix = mnfo.get('prefix')
                if prefix is not None:
                    valu = valu.rstrip(inverse_prefixs.get(prefix))

                if cb:
                    valu = cb(valu)
                    if valu is None:
                        continue

                yield (ruletype, valu)
                if first:
                    return
