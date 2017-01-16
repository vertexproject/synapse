import base64

import synapse.compat as s_compat

from synapse.common import *

def _de_base64(item,**opts):

    # transparently handle the strings/bytes issue...
    wasstr = s_compat.isstr(item)
    if wasstr:
        item = item.encode('utf8')

    item = base64.b64decode(item)

    if wasstr:
        item = item.decode('utf8')

    return item

def _en_base64(byts,**opts):
    return base64.b64encode(byts)

def _en_utf8(text,**opts):
    return text.encode('utf8')

def _de_utf8(byts,**opts):
    return byts.decode('utf8')

decoders = {
    'utf8':_de_utf8,
    'base64':_de_base64,
}

encoders = {
    'utf8':_en_utf8,
    'base64':_en_base64,
}

def decode(name, byts, **opts):
    '''
    Decode the given byts with the named decoder.
    If name is a comma separated list of decoders,
    loop through and do them all.

    Example:

        byts = s_encoding.decode('base64',byts)

    Note: Decoder names may also be prefixed with +
          to *encode* for that name/layer.

    '''
    for name in name.split(','):

        if name.startswith('+'):
            byts = encode(name[1:], byts, **opts)
            continue

        func = decoders.get(name)
        if func == None:
            raise NoSuchDecoder(name=name)

        byts = func(byts,**opts)

    return byts

def encode(name, item, **opts):

    for name in name.split(','):

        if name.startswith('-'):
            item = decode(name[1:], item, **opts)
            continue

        func = encoders.get(name)
        if func == None:
            raise NoSuchEncoder(name=name)

        item = func(item,**opts)

    return item
