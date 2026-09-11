'''
Helpers for identifying Synapse as the client on outbound HTTP(S) requests.

This is the client-side sibling of synapse.lib.httpapi -- that module serves
inbound HTTP; this one formats the default User-Agent Synapse cells present
when *making* outbound HTTP(S) requests.

This module is imported by synapse.lib.cell, so -- like synapse.lib.version,
which is imported during synapse.__init__ -- it must stay light on imports to
avoid import cycles. Only synapse.lib.version is pulled in here.
'''
import functools

import synapse.lib.version as s_version

VERTEX_URL = 'https://vertex.link'

@functools.cache
def getUserAgent(prod, vers):
    '''
    Format (and cache) a default Synapse outbound HTTP User-Agent string.

    Args:
        prod (str): The product token, e.g. "Synapse-Cortex" or "Synapse-Enterprise-Maxmind".
        vers (str): The product's own version string (not necessarily the synapse version).

    Returns:
        str: A User-Agent string of the form "<prod>/<vers> (Synapse/<synver>; https://vertex.link)".

    Notes:
        The result is cached forever for the lifetime of the process, keyed on
        the exact (prod, vers) pair. Only call this with a small, bounded set
        of values (e.g. a class's own product token and version) -- never
        with a caller- or user-controlled string, which would grow the cache
        without bound.
    '''
    return f'{prod}/{vers} (Synapse/{s_version.version}; {VERTEX_URL})'

def setDefaultUserAgent(headers, useragent):
    '''
    Return headers as a list of pairs with a default User-Agent set, unless one
    is already present.

    Args:
        headers: None, a dict of header name -> value, or a list/tuple of
                 (name, value) pairs -- the shapes synapse.lib.stormtypes.strifyHttpArg()
                 may produce. Header name matching against an existing
                 User-Agent is case-insensitive, since strifyHttpArg() does
                 no case folding of its own.
        useragent (str): The default User-Agent to set when one is absent.

    Returns:
        list: The headers as a list of (name, value) pairs, with a 'User-Agent'
              pair appended if none was already present in any casing.

    Notes:
        A dict input is converted rather than preserved so there is a single
        return shape to reason about -- aiohttp accepts either, and the list of
        pairs is the more general of the two (it can carry a repeated header
        name, which a dict cannot). The input is never mutated in place.
    '''
    if headers is None:
        return [('User-Agent', useragent)]

    if isinstance(headers, dict):
        headers = list(headers.items())
    else:
        headers = list(headers)

    if any(name.lower() == 'user-agent' for name, valu in headers):
        return headers

    return [*headers, ('User-Agent', useragent)]
