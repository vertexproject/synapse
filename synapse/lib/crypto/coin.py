import logging
import binascii

import cbor2  # cardano
import regex
import bech32  # cardano
import base58  # btc and cardano
import Crypto.Hash.keccak as c_keccak
import bitcoin  # btc
import bitcoin.bech32 as bitcoin_b32  # btc
import synapse.vendor.cashaddress.convert as cashaddr_convert  # BCH support
import synapse.vendor.xrpl.core.addresscodec as xrp_addresscodec  # xrp support
import synapse.vendor.substrateinterface.utils.ss58 as substrate_ss58  # polkadot support

logger = logging.getLogger(__name__)

'''
synapse.lib.crypto.coin contains functions for verifying whether or not a given
regex match containing a valu is valid for a given type of coin.

these functions are intended to be used with synapse.lib.scrape.
'''

# CAIP-2 (https://chainagnostic.org/CAIPs/caip-2) chain definitions for the
# crypto currency chains recognized by the scrape callbacks below. Each entry
# maps a chain key to the (symbol, CAIP-2 chain id) pair used to construct a
# crypto:currency:chain guid constructor. Bitcoin networks are kept distinct
# since the bech32 prefix identifies the network; Bitcoin Cash is treated as
# mainnet since its testnet has no distinct CAIP-2 chain id.
caip2_chains = {
    'btc':         ('btc', 'bip122:000000000019d6689c085ae165831e93'),
    'btc:testnet': ('btc', 'bip122:000000000933ea01ad0ee984209779ba'),
    'btc:regtest': ('btc', 'bip122:0f9188f13cb7b2c71f2a335e3a4fc328'),
    'bch':         ('bch', 'bip122:000000000000000000651ef99cb9fcbe'),
    'eth':         ('eth', 'eip155:1'),
    'xrp':         ('xrp', 'xrpl:0'),
    'dot':         ('dot', 'polkadot:91b171bb158e2d3848fa23a9f1c25182'),
    'ksm':         ('ksm', 'polkadot:b0a8d493285c2df73290dfb7e61f870f'),
    'ada':         ('ada', 'cip34:1-764824073'),
}

def chain(key):
    '''
    Return a crypto:currency:chain guid constructor for a caip2_chains key.
    '''
    (symbol, chainid) = caip2_chains[key]
    return {'symbol': symbol, 'id': chainid}

def btc_bech32_check(match: regex.Match):
    text = match.groupdict().get('valu')
    prefix, _ = text.split('1', 1)
    prefix = prefix.lower()
    if prefix == 'bc':
        bitcoin.SelectParams('mainnet')
        chainkey = 'btc'
    elif prefix == 'tb':
        bitcoin.SelectParams('testnet')
        chainkey = 'btc:testnet'
    elif prefix == 'bcrt':
        bitcoin.SelectParams('regtest')
        chainkey = 'btc:regtest'
    else:  # pragma: no cover
        raise ValueError(f'Unknown prefix {text}')
    try:
        _ = bitcoin_b32.CBech32Data(text)
    except bitcoin_b32.Bech32Error:
        return None, {}
    # The proper form of a bech32 address is lowercased. We do not want to verify
    # a mixed case form, so lowercase it prior to returning.
    return (chain(chainkey), text.lower()), {}

def btc_base58_check(match: regex.Match):
    text = match.groupdict().get('valu')
    try:
        base58.b58decode_check(text)
    except ValueError:
        return None, {}
    return (chain('btc'), text), {}

def ether_eip55(body: str):
    # From EIP-55 reference implementation
    hex_addr = body.lower()
    checksummed_buffer = ""
    hashed_address = c_keccak.new(data=hex_addr.encode(), digest_bits=256).hexdigest()

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

def eth_check(match: regex.Match):
    text = match.groupdict().get('valu')  # type: str
    body = text[2:]

    ret = ether_eip55(body)
    if ret is None:
        return None, {}

    # Checksum if we're mixed case or not
    if not body.isupper() and not body.islower():
        if ret != text:
            return None, {}
        return (chain('eth'), text), {}

    # any valid 0x<40 character> hex string is possibly a ETH address.
    return (chain('eth'), ret), {}

def bch_check(match: regex.Match):
    text = match.groupdict().get('valu')
    # Checksum if we're mixed case or not
    prefix, body = text.split(':', 1)
    if not body.isupper() and not body.islower():
        return None, {}
    try:
        cashaddr_convert.Address._cash_string(text)
    except:
        return None, {}
    text = text.lower()
    return (chain('bch'), text), {}

def xrp_check(match: regex.Match):
    text = match.groupdict().get('valu')
    if xrp_addresscodec.is_valid_classic_address(text) or xrp_addresscodec.is_valid_xaddress(text):
        return (chain('xrp'), text), {}
    return None, {}

def substrate_check(match: regex.Match):
    text = match.groupdict().get('valu')
    prefix = text[0]  # str
    if prefix == '1' and substrate_ss58.is_valid_ss58_address(text, valid_ss58_format=0):
        # polkadot
        return (chain('dot'), text), {}
    elif prefix.isupper() and substrate_ss58.is_valid_ss58_address(text, valid_ss58_format=2):
        # kusuma
        return (chain('ksm'), text), {}
    else:
        # Do nothing with generic substrate matches
        # Generic substrate addresses are checked with valid_ss58_format=42
        return None, {}

def cardano_byron_check(match: regex.Match):
    text = match.groupdict().get('valu')
    # Try a base58 / cbor decoding
    try:
        decoded_text = base58.b58decode(text)
        message = cbor2.loads(decoded_text)
        if not isinstance(message, list) or len(message) != 2:
            return None, {}
        csum = message[1]
        computed_checksum = binascii.crc32(message[0].value)
        if csum == computed_checksum:
            return (chain('ada'), text), {}
    except (ValueError, cbor2.CBORError):
        pass
    return None, {}

def cardano_shelly_check(match: regex.Match):
    text = match.groupdict().get('valu')
    # Bech32 decoding
    ret = bech32.bech32_decode(text)
    if ret == (None, None):
        return None, {}
    return (chain('ada'), text), {}
